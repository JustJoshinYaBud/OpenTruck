"""OpenTruck - OBD-II (J1962 / ISO 15765-4) probe for light-duty vehicles.

Twin of ``can2_probe.py`` for the 16-pin DLC. Two phases:

``--phase passive`` (default): open a raw ``CAN:Baud=500`` client on the 16-pin
connector and just listen. Confirms the cable/adapter/baud and shows whether
the vehicle chats on its own (network-management / periodic frames), plus the
11-bit vs 29-bit id split of whatever is there.

``--phase request``: additionally open the driver's ``ISO15765`` client and try
to send an OBD Mode 01 "supported PIDs" request (02 01 00) to the functional
broadcast id 0x7DF, trying the plausible TX buffer formats since the RP1210
raw-CAN/ISO15765 TX layout is not yet documented in our notes. Every RX byte
is logged verbatim for offline analysis.

Log: ``raw captures/obd2_probe_<date>.log``.

Usage:
    python obd2_probe.py                       # passive, 60 s
    python obd2_probe.py --phase request       # passive + Mode 01 requests
    python obd2_probe.py --adapter NULN3R32 --baud 500 --seconds 120
"""
from __future__ import annotations

import argparse
import datetime
import time
from collections import Counter

from rp1210 import RP1210Source, BridgedRP1210Source, RP1210Error

PROTOCOL_RAW = "CAN:Baud={baud}"
PROTOCOL_ISO15765 = "ISO15765:Baud={baud}"

OBD_FUNCTION_ID = 0x7DF       # functional broadcast (all ECUs)


def pick_adapter(wanted: str | None):
    from rp1210 import list_adapters
    adapters = list_adapters()
    for a in adapters:
        if wanted and a.code.upper() != wanted.upper():
            continue
        if a.dll_path or a.bridge_dll:
            return a
    if wanted:
        raise SystemExit(f"Adapter {wanted!r} not found or has no DLL. "
                         f"Installed: {[a.code for a in adapters]}")
    raise SystemExit(f"No usable RP1210 adapter found. Installed: "
                     f"{[a.code for a in adapters]}")


def make_source(a, protocol: str, passive: bool = True):
    if a.dll_path:
        return RP1210Source(dll_path=a.dll_path, protocol=protocol,
                            device_id=a.device_id, passive=passive)
    return BridgedRP1210Source(dll_path=a.bridge_dll, protocol=protocol,
                               device_id=a.device_id, passive=passive)


def drain(source) -> list[str]:
    out = []
    for _ in range(128):
        try:
            raw = source.read_raw_hex()
        except Exception:
            break
        if not raw:
            break
        out.append(raw)
    return out


def parse_raw(buf: bytes) -> dict:
    """Split a raw-CAN RX buffer using the observed layout:
    [0:4] timestamp ms LE | [4] flag | [5:9] id big-endian | [9:] payload.
    For 11-bit frames the id field holds the short id. Both endiannesses are
    returned so an empirical capture can confirm which one the driver uses."""
    if len(buf) < 9:
        return {}
    return {"flag": buf[4],
            "id_be": int.from_bytes(buf[5:9], "big"),
            "id_le": int.from_bytes(buf[5:9], "little"),
            "data": buf[9:]}


def analyse(buffers: list[bytes], tag: str) -> None:
    if not buffers:
        print(f"\n[{tag}] no frames captured")
        return
    print(f"\n[{tag}] {len(buffers)} frames; lengths: "
          f"{sorted({len(b) for b in buffers})}")
    flags = Counter(f"0x{parse_raw(b)['flag']:02X}" for b in buffers if len(b) >= 9)
    print(f"  flag byte [4]: {flags.most_common(4)}")
    ids = Counter(parse_raw(b)["id_be"] for b in buffers if len(b) >= 9)
    ext = sum(1 for i in ids if i > 0x7FF)
    print(f"  {len(ids)} distinct ids (BE read); {ext} ids look >11-bit "
          f"(extended/29-bit)")
    for cid, n in ids.most_common(12):
        kind = "EXT" if cid > 0x7FF else "STD"
        print(f"    id 0x{cid:08X} ({kind})  x{n}")
    # 11-bit OBD ids of interest
    obdish = {i: n for i, n in ids.items() if 0x600 <= i <= 0x7FF}
    if obdish:
        print(f"  OBD-range ids (0x600-0x7FF): "
              f"{ {hex(i): n for i, n in sorted(obdish.items())} }")


# Mode 01 supported-PID request: ISO-TP single frame = [PCI 02][01 00],
# conventionally padded to 8 CAN bytes.
OBD_SF = bytes([0x02, 0x01, 0x00])
OBD_SF_PAD8 = OBD_SF + bytes(5)
OBD_ID_BE = OBD_FUNCTION_ID.to_bytes(4, "big")
OBD_ID_LE = OBD_FUNCTION_ID.to_bytes(4, "little")

TX_CANDIDATES = {
    # name -> (client, buffer). The live log shows which framing (if any)
    # draws a real ECU response (a 0x41 positive-response byte).
    "id BE + SF padded8":      ("iso", OBD_ID_BE + OBD_SF_PAD8),
    "id LE + SF padded8":      ("iso", OBD_ID_LE + OBD_SF_PAD8),
    "flag + id BE + SF pad8":  ("iso", bytes([0x01]) + OBD_ID_BE + OBD_SF_PAD8),
    "id BE + SF unpadded":    ("iso", OBD_ID_BE + OBD_SF),
    "SF padded8 only":         ("iso", OBD_SF_PAD8),
    "id BE + SF padded8 RAW":  ("raw", OBD_ID_BE + OBD_SF_PAD8),
    "id BE + SF unpadded RAW": ("raw", OBD_ID_BE + OBD_SF),
}


def main() -> int:
    ap = argparse.ArgumentParser(description="OBD-II (J1962) probe")
    ap.add_argument("--adapter", help="RP1210 vendor code (default: first usable)")
    ap.add_argument("--phase", choices=["passive", "request"], default="passive")
    ap.add_argument("--iso-proto", default="ISO15765",
                    help="ISO client protocol string base: ISO15765/J2284/OBDII")
    ap.add_argument("--baud", default="500", help="CAN baud: 250/500/Auto")
    ap.add_argument("--seconds", type=float, default=60)
    args = ap.parse_args()

    a = pick_adapter(args.adapter)
    print(f"Adapter: {a.code} ({a.name})  "
          f"({'in-process' if a.dll_path else '32-bit bridge'})")

    src = make_source(a, PROTOCOL_RAW.format(baud=args.baud))
    iso = None
    try:
        src.connect()
        print(f"Raw CAN client connected ({args.baud})")
    except RP1210Error as e:
        print(f"Raw CAN client FAILED: {e}")
        return 1

    if args.phase == "request":
        try:
            # passive: ISO15765 has no J1939 address-claim concept - claiming
            # one invalidates the client (ERR_INVALID_CLIENT_ID on TX).
            iso = make_source(a, f"{args.iso_proto}:{args.baud}",
                              passive=True)
            iso.connect()
            print(f"{args.iso_proto} client connected")
        except RP1210Error as e:
            print(f"{args.iso_proto} client FAILED: {e} (continuing passive only)")
            iso = None

    stamp = datetime.datetime.now().strftime("%d-%m-%Y_%H.%M.%S")
    path = f"raw captures/obd2_probe_{stamp}.log"
    fh = open(path, "w", encoding="utf-8")
    print(f"Logging to {path} for {args.seconds}s ...")

    tx_done = False
    n_raw = 0
    raws: list[bytes] = []
    t0 = time.time()
    last = t0
    try:
        while time.time() - t0 < args.seconds:
            for tag, cl in (("RAW", src), ("ISO", iso)):
                if cl is None:
                    continue
                for raw in drain(cl):
                    raws.append(bytes.fromhex(raw))
                    fh.write(f"{tag} RX {raw}\n")
                    n_raw += 1
            if iso is not None and not tx_done and time.time() - t0 > 5:
                # Send the Mode 01 supported-PID request once per candidate TX
                # framing, draining BOTH clients after each so responses don't
                # interleave. Every byte is logged; a real ECU response will
                # contain the 0x41 positive-response byte.
                clients = {"raw": src, "iso": iso}
                for name, (ckey, payload) in TX_CANDIDATES.items():
                    client = clients[ckey]
                    try:
                        rc = client.send_raw_message(payload)
                        err = ""
                        if hasattr(client, "_error_text") and rc != 0:
                            try:
                                err = " " + client._error_text(rc)
                            except Exception:
                                pass
                        fh.write(f"TX try [{name}] {payload.hex()} -> rc {rc}{err}\n")
                        print(f"  TX try [{name}] rc={rc}{err}")
                        deadline = time.time() + 2.5
                        while time.time() < deadline:
                            for t2, cl2 in (("RAW", src), ("ISO", iso)):
                                for raw in drain(cl2):
                                    raws.append(bytes.fromhex(raw))
                                    fh.write(f"POSTTX {t2} RX {raw}\n")
                                    print(f"      {t2} RX {raw}")
                            time.sleep(0.05)
                    except Exception as exc:
                        fh.write(f"TX try [{name}] FAILED: {exc}\n")
                tx_done = True
            if time.time() - last >= 5:
                last = time.time()
                print(f"  {time.time() - t0:4.0f}s  frames: {n_raw}")
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("interrupted")
    finally:
        fh.close()
        if iso is not None:
            iso.close()
        src.close()

    print(f"\nDone. {n_raw} frames. log: {path}")
    analyse(raws, "RAW")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())