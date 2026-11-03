"""OpenTruck - CAN2 / dual-datalink probe (one-off live-test tool).

Opens TWO RP1210 clients on the SAME adapter/device at once:

  * client A: ``J1939:Baud=Auto``  - the known-good reference (full J1939
    parse; proves the bus and gives the detected baud).
  * client B: ``CAN:Baud=Auto``    - RAW CAN. The buffer layout the driver
    returns for the raw-CAN protocol is NOT documented in our notes, so this
    probe logs every byte verbatim and, at the end, tries the plausible
    layouts (LE / BE 29-bit ID at offset 4, J1939-style header) against the
    capture so the real layout can be identified.

Everything is written to ``raw captures/can2_probe_<date>.log`` in the same
``TAG <hex>`` style the replay source understands, so a session can be
re-analysed offline.

Usage:
    python can2_probe.py                     # 30 s on the first usable adapter
    python can2_probe.py --adapter CA3rp32 --seconds 60
"""
from __future__ import annotations

import argparse
import datetime
import time
from collections import Counter

from rp1210 import RP1210Source, BridgedRP1210Source, RP1210Error
from modules.j1939 import Frame

PROTOCOL_J1939 = "J1939:Baud=Auto"
PROTOCOL_CAN = "CAN:Baud=Auto"


def pick_adapter(wanted: str | None):
    """Return the first enumerated adapter with a usable DLL (or the wanted one)."""
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


def make_source(a, protocol: str,
                passive: bool = True) -> RP1210Source | BridgedRP1210Source:
    """In-process source for matching-bitness DLLs, bridge for 32-bit-only.

    Probe clients are listen-only (passive): filters open, no address claim.
    """
    if a.dll_path:
        return RP1210Source(dll_path=a.dll_path, protocol=protocol,
                            device_id=a.device_id, passive=passive)
    return BridgedRP1210Source(dll_path=a.bridge_dll, protocol=protocol,
                               device_id=a.device_id, passive=passive)


def drain(source) -> list[bytes]:
    """Read every currently-available message; return raw buffers as hex."""
    out = []
    for _ in range(64):                      # bounded so one client can't starve
        try:
            raw = source.read_raw_hex()
        except Exception:
            break
        if not raw:
            break
        out.append(raw)
    return out


def analyse_can(buffers: list[bytes]) -> None:
    """Try the plausible raw-CAN buffer layouts against the capture."""
    if not buffers:
        print("\n[CAN] no raw frames captured - nothing to analyse")
        return
    print(f"\n[CAN] {len(buffers)} raw frames captured; lengths seen: "
          f"{sorted({len(b) for b in buffers})}")

    candidates = {
        "LE 29-bit id @ [4:8]":   lambda b: int.from_bytes(b[4:8], "little") & 0x1FFFFFFF if len(b) >= 9 else None,
        "BE 29-bit id @ [4:8]":   lambda b: int.from_bytes(b[4:8], "big") & 0x1FFFFFFF if len(b) >= 9 else None,
        "LE 32-bit id @ [5:9]":   lambda b: int.from_bytes(b[5:9], "little") & 0x1FFFFFFF if len(b) >= 10 else None,
        "J1939-style @ [4:7]":    lambda b: int.from_bytes(b[4:7], "little") & 0x3FFFF if len(b) >= 11 else None,
    }
    for name, fn in candidates.items():
        ids = Counter(fn(b) for b in buffers if fn(b) is not None)
        if not ids:
            continue
        j1939_like = sum(1 for i in ids if (i >> 24) in (0x18, 0x1C)) * 100 // len(ids)
        print(f"  candidate '{name}': {len(ids)} distinct ids, "
              f"{j1939_like}% look like 29-bit J1939 ids")
        for i, n in ids.most_common(8):
            print(f"      id 0x{i:08X}  x{n}")


def main() -> int:
    ap = argparse.ArgumentParser(description="CAN2 / raw-CAN probe")
    ap.add_argument("--adapter", help="RP1210 vendor code (default: first usable)")
    ap.add_argument("--seconds", type=float, default=30)
    ap.add_argument("--device", type=int, default=None,
                    help="device id (default: the adapter's own)")
    ap.add_argument("--cdl", action="store_true",
                    help="also open the adapter's Cat Data Link (CDL) "
                         "protocol client (CA3: protocol string 'CAT')")
    args = ap.parse_args()

    a = pick_adapter(args.adapter)
    dev = args.device or a.device_id
    print(f"Adapter: {a.code}  ({a.name})  device {dev}  "
          f"({'in-process' if a.dll_path else '32-bit bridge'})")

    # --- reference J1939 client ------------------------------------------ #
    j1939 = make_source(a, PROTOCOL_J1939)
    try:
        j1939.connect()
        print("J1939 client: connected")
    except RP1210Error as e:
        print(f"J1939 client FAILED: {e}")
        return 1

    # --- raw CAN client --------------------------------------------------- #
    can = make_source(a, PROTOCOL_CAN)
    try:
        can.connect()
        print("CAN client: connected")
    except RP1210Error as e:
        print(f"CAN client FAILED: {e}")
        j1939.close()
        return 1

    # --- optional CDL client (CA3: 'CAT' = Cat Data Link) ------------------ #
    cdl = None
    if args.cdl:
        try:
            cdl = make_source(a, "CAT")
            cdl.connect()
            print("CDL (CAT protocol) client: connected")
        except RP1210Error as e:
            print(f"CDL client FAILED: {e} (continuing without it)")
            cdl = None

    stamp = datetime.datetime.now().strftime("%d-%m-%Y_%H.%M.%S")
    path = f"raw captures/can2_probe_{stamp}.log"
    fh = open(path, "w", encoding="utf-8")
    print(f"Logging to {path} for {args.seconds}s ...")

    clients = [("J1939", j1939, j_bufs), ("CAN", can, c_bufs)]
    d_bufs: list[bytes] = []
    if cdl is not None:
        clients.append(("CDL", cdl, d_bufs))

    counts = {"J1939": 0, "CAN": 0, "CDL": 0}
    t0 = time.time()
    last_report = t0
    try:
        while time.time() - t0 < args.seconds:
            for tag, src, sink in clients:
                for raw in drain(src):
                    raw_b = bytes.fromhex(raw)
                    sink.append(raw_b)
                    fh.write(f"{tag} RX {raw}\n")
                    counts[tag] += 1
            if time.time() - last_report >= 5:
                last_report = time.time()
                print(f"  {time.time() - t0:4.0f}s  "
                      + "   ".join(f"{t}: {counts[t]}" for t in counts))
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("interrupted")
    finally:
        fh.close()
        for tag, src, _sink in clients:
            src.close()

    print("\nDone. " + "   ".join(f"{t}: {counts[t]}" for t in counts)
          + f"   log: {path}")
    analyse_can(c_bufs)
    if d_bufs:
        # CDL buffer layout is unknown - CDL is J1708-derived, so the likely
        # shape is [timestamp][MID][data...]; log the length histogram and
        # samples to identify it from a live session.
        from collections import Counter
        print(f"\n[CDL] {len(d_bufs)} raw frames; lengths: "
              f"{sorted({len(b) for b in d_bufs})}")
        for b in d_bufs[:5]:
            print(f"    {b.hex().upper()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())