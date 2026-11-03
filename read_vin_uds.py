"""Live UDS identification probe (diagnostic tool).

Reads the VIN (DID 0xF190 / 0xF194) and supplier/part/serial identifiers
(DID 0xF18A / 0xF187 / 0xF18C) from J1939 modules over UDS-on-J1939
(0x18DA<DA><SA> + ISO-TP). Many modern engines answer a UDS VIN even when they
NACK the J1939 VI PGN (65260).

Usage:
    python read_vin_uds.py                # probe 0x00 (engine), 0x03, 0x0F
    python read_vin_uds.py --targets 00 03 0F
"""
from __future__ import annotations

import argparse

from modules.j1939 import PGN
from rp1210 import RP1210Source
from modules import uds

# Identification DIDs to try per module.
_DIDS = [
    ("VIN", uds.DID_VIN),
    ("VIN(alt)", uds.DID_VIN_ALT),
    ("Supplier", uds.DID_SUPPLIER),
    ("SparePart", uds.DID_SPARE_PART),
    ("Serial", uds.DID_SERIAL),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="UDS VIN / identification probe")
    ap.add_argument("--targets", nargs="+", default=["00", "03", "0F"],
                    help="hex source addresses to probe (default 00 03 0F)")
    ap.add_argument("--timeout", type=float, default=0.8)
    args = ap.parse_args()

    targets = [int(t, 16) for t in args.targets]
    src = RP1210Source()
    print("Connecting to RP1210 adapter (J1939, baud=Auto)...")
    try:
        src.connect()
    except Exception as exc:  # noqa: BLE001
        print(f"CONNECT FAILED: {exc}")
        return 2
    print("Connected.\n")

    found_vin = None
    for target in targets:
        client = uds.UdsClient(src, target)
        sess = uds.open_extended_session(client)
        print(f"=== ECU 0x{target:02X}  (extended session: {'OK' if sess else 'no response'}) ===")
        any_reply = False
        for label, did in _DIDS:
            data = client.read_did(did, timeout=args.timeout)
            if data:
                any_reply = True
                text = data.decode("ascii", "replace").replace("\x00", "").strip()
                printable = text.isprintable() and len(text) >= 2
                shown = f"{text!r}" if printable else data.hex().upper()
                print(f"    {label:<10} DID 0x{did:04X} -> {shown}")
                if label.startswith("VIN") and len(text) >= 17 and not found_vin:
                    found_vin = (text[:17], target)
            else:
                nrc = client.negative_response(did, timeout=args.timeout)
                if nrc:
                    any_reply = True
                    print(f"    {label:<10} DID 0x{did:04X} -> NRC {nrc}")
        if not any_reply:
            print("    (no UDS responses - module does not speak UDS here)")
        print()

    src.close()
    print("================ SUMMARY ================")
    if found_vin:
        print(f"VIN: {found_vin[0]}  (from ECU 0x{found_vin[1]:02X})")
    else:
        print("VIN: NOT available via UDS on the probed modules")
    return 0 if found_vin else 1


if __name__ == "__main__":
    raise SystemExit(main())
