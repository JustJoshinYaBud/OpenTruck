"""OpenTruck - UDS module discovery sweep (enhanced diagnostics groundwork).

Generic OBD-II (Mode 01-09) only emissions ECUs answer - ABS / body / chassis
controllers stay silent even though they sit on the same DLC bus. This probe
discovers them EMPIRICALLY: it unicasts a standard UDS TesterPresent
(0x3E 0x00, ISO 14229) to every 11-bit address in a range and records which
addresses respond. The resulting per-brand module map feeds the enhanced
UDS layer (module naming, ReadDTCInformation 0x19 enhanced codes, Mode 22
DIDs) - all standard ISO 14229 services, no vendor secrets.

Usage:
    python uds_sweep.py --adapter NULN3R32
    python uds_sweep.py --start 0x600 --end 0x7FF --dtcs
"""
from __future__ import annotations

import argparse
import datetime
import time

from rp1210 import RP1210Source, BridgedRP1210Source, RP1210Error

TX_FLAG_STD = 0x00
CAN_PAYLOAD = 8


def make_source(a, protocol: str):
    if a.dll_path:
        return RP1210Source(dll_path=a.dll_path, protocol=protocol,
                            device_id=a.device_id, passive=True)
    return BridgedRP1210Source(dll_path=a.bridge_dll, protocol=protocol,
                               device_id=a.device_id, passive=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="UDS module discovery sweep")
    ap.add_argument("--adapter", help="RP1210 vendor code")
    ap.add_argument("--start", type=lambda x: int(x, 0), default=0x600)
    ap.add_argument("--end", type=lambda x: int(x, 0), default=0x7FF)
    ap.add_argument("--baud", default="500")
    ap.add_argument("--dtcs", action="store_true",
                    help="after discovery, read UDS DTCs (0x19 02) from every "
                         "responder")
    args = ap.parse_args()

    from rp1210 import list_adapters
    a = None
    for cand in list_adapters():
        if args.adapter and cand.code.upper() != args.adapter.upper():
            continue
        if cand.dll_path or cand.bridge_dll:
            a = cand
            break
    if a is None:
        raise SystemExit("No usable adapter found")

    src = make_source(a, f"CAN:Baud={args.baud}")
    src.connect()
    print(f"Adapter {a.code} connected ({args.baud}, 11-bit)")

    stamp = datetime.datetime.now().strftime("%d-%m-%Y_%H.%M.%S")
    path = f"raw captures/uds_sweep_{stamp}.log"
    fh = open(path, "w", encoding="utf-8")
    print(f"Sweeping 0x{args.start:X}-0x{args.end:X}, logging to {path} ...")

    def drain(seconds: float) -> dict[int, list[bytes]]:
        got: dict[int, list[bytes]] = {}
        t0 = time.time()
        while time.time() - t0 < seconds:
            raw = src.read_raw_hex()
            if not raw:
                time.sleep(0.003)
                continue
            b = bytes.fromhex(raw)
            if len(b) < 9 or b[4] != TX_FLAG_STD:
                continue
            cid = int.from_bytes(b[5:7], "big")
            got.setdefault(cid, []).append(b[7:])
            fh.write(f"RX {raw}\n")
        return got

    responders: dict[int, bytes] = {}
    for can_id in range(args.start, args.end + 1):
        payload = bytes([0x02, 0x3E, 0x00]) + bytes(CAN_PAYLOAD - 3)
        buf = bytes([TX_FLAG_STD]) + can_id.to_bytes(2, "big") + payload
        rc = src.send_raw_message(buf)
        fh.write(f"TX 0x{can_id:X} rc={rc} {buf.hex().upper()}\n")
        replies = drain(0.06)
        # A module answering OUR probe: a reply shortly after our unicast.
        # Background chatter is continuous, so only reply frames arriving
        # within this drain window are candidates; correlate by expecting a
        # positive response id (request id is module-specific on CAN - most
        # makers answer on request_id + 0x40... but responses also come from
        # the module's own RX id). Log everything; the summary prints the
        # addresses that answered with a UDS positive/negative response
        # (0x7E / 0x7F first payload byte).
        for cid, frames in replies.items():
            for f in frames:
                # ISO-TP: the first payload byte is the PCI (frame type); a
                # single-frame reply has the UDS SID at f[1].
                if len(f) >= 2 and (f[0] >> 4) == 0 and f[1] in (0x7E, 0x7F):
                    responders[can_id] = bytes(f)
                    fh.write(f"HIT 0x{can_id:X} <- 0x{cid:X} {f.hex().upper()}\n")

    print(f"\n{len(responders)} module(s) answered TesterPresent:")
    for can_id in sorted(responders):
        f = responders[can_id]
        kind = "positive" if f[0] == 0x7E else "negative (NRC 0x%02X)" % f[1]
        print(f"  request 0x{can_id:X}  reply: {f.hex().upper()}  ({kind})")

    if args.dtcs and responders:
        print("\nEnhanced session + DTC read (UDS 0x10 03, then 0x19 02 09) ...")
        for can_id in sorted(responders):
            # Extended diagnostic session (0x10 03) - standard ISO 14229.
            sess_buf = bytes([TX_FLAG_STD]) + can_id.to_bytes(2, "big") + \
                bytes([0x02, 0x10, 0x03]) + bytes(CAN_PAYLOAD - 3)
            src.send_raw_message(sess_buf)
            replies = drain(0.15)
            in_session = any(
                len(f) >= 2 and (f[0] >> 4) == 0 and f[1] == 0x50
                for frames in replies.values() for f in frames)
            if not in_session:
                fh.write(f"SESSION 0x{can_id:X} refused\n")
                print(f"  0x{can_id:X}: session refused")
                continue
            print(f"  0x{can_id:X}: extended session OK")
            # ReadDTCInformation reportDTCByStatusMask (0x19 02 09 = confirmed
            # + pending + permanent mask).
            payload = bytes([0x03, 0x19, 0x02, 0x09]) + bytes(CAN_PAYLOAD - 4)
            buf = bytes([TX_FLAG_STD]) + can_id.to_bytes(2, "big") + payload
            src.send_raw_message(buf)
            replies = drain(0.4)
            saw = False
            for cid, frames in replies.items():
                for f in frames:
                    if len(f) >= 2 and (f[0] >> 4) in (0, 1) and f[1] == 0x59:
                        saw = True
                        fh.write(f"DTCS 0x{can_id:X} <- {f.hex().upper()}\n")
                        print(f"  0x{can_id:X} DTC data: {f.hex().upper()}")
            if not saw:
                print(f"  0x{can_id:X}: no 0x59 response")
            # Leave the module back in the default session.
            src.send_raw_message(bytes([TX_FLAG_STD]) + can_id.to_bytes(2, "big")
                                 + bytes([0x02, 0x10, 0x01])
                                 + bytes(CAN_PAYLOAD - 3))
            drain(0.1)

    fh.close()
    src.close()
    print(f"\nLog: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())