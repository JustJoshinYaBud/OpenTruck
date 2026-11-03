"""OpenTruck - Cat Data Link (CDL) capture (one-off live-test tool).

The 'CAT' protocol in a CAT-family vendor INI (CA3rp32.INI among them) is the
Cat Data Link: the proprietary link that carries the machine controllers of a
CAT machine (hydraulics, implement, transmission, payload - and on some
machines the engine too), which never appear on J1939.

The CDL wire format is CAT-proprietary and the RP1210 receive-buffer layout
for the 'CAT' protocol has never been verified here, so this tool captures
EVERY buffer verbatim and interprets NOTHING. One capture answers:

  * is there CDL traffic on this machine's diagnostic connector at all?
  * the buffer layout (leading 4-byte timestamp or not),
  * the message-identifier distribution (CDL frames carry a one-byte
    IID/MID-style header - the histogram below reveals it),
  * frame lengths and broadcast periods (every line is timestamped).

ONE client, listen-only, nothing else - so it works on single-session
adapters like the CA3 by construction. Nothing is transmitted: CDL has
request/broadcast messages (e.g. the documented "IID 82 - Request to
Broadcast Diagnostic Codes"), but nothing goes out until the format is
verified from a real capture.

Output: ``raw captures/cdl_<date>.log`` with one ``<elapsed_ms> <HEX>`` line
per received buffer (elapsed milliseconds from capture start, then the whole
RP1210 buffer as hex), plus a summary printed and written to the connection
log.

Usage:
    python cdl_capture.py                          # CA3 if present, 60 s
    python cdl_capture.py --adapter CA3rp32 --seconds 120
"""
from __future__ import annotations

import argparse
import datetime
import os
import time
from collections import Counter

import connectlog
from rp1210 import list_adapters, protocol_options
from adapter_check import make_source


def cat_protocol(a) -> str | None:
    """The vendor INI's Cat Data Link protocol string for this device, if any.

    Only CAT-family adapters declare 'CAT' (see rp1210.protocol_options),
    and only for the devices their INI says speak it.
    """
    return next((p for p in protocol_options(a.ini_path, a.device_id)
                 if p.split(":", 1)[0].strip().upper() == "CAT"), None)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--adapter", help="vendor code, e.g. CA3rp32 "
                                      "(default: CA3rp32 if installed)")
    ap.add_argument("--seconds", type=float, default=60.0,
                    help="capture duration (default 60 s)")
    ap.add_argument("--out", help="output folder (default: <cwd>/raw captures)")
    args = ap.parse_args()

    adapters = list_adapters()
    a = None
    if args.adapter:
        a = next((x for x in adapters if x.code.upper() == args.adapter.upper()),
                 None)
        if a is None:
            raise SystemExit("Adapter %r not found. Installed: %s"
                             % (args.adapter, [x.code for x in adapters]))
    else:
        a = next((x for x in adapters if x.code.upper() == "CA3RP32"), None) \
            or (adapters[0] if adapters else None)
    if a is None:
        raise SystemExit("No RP1210 adapter with a driver is installed.")
    cat = cat_protocol(a)
    if cat is None:
        raise SystemExit(
            "Adapter %s does not declare a Cat Data Link ('CAT') protocol - "
            "CDL is only spoken by CAT-family adapters." % a.code)

    print(f"=== CDL capture: {a.name} [{a.code}] protocol {cat!r}, "
          f"{args.seconds:.0f} s, listen-only ===")
    src = make_source(a, cat, claim=False)
    try:
        src.connect()
    except Exception as exc:                     # noqa: BLE001
        raise SystemExit(f"Could not open the Cat Data Link client:\n{exc}")

    base = args.out or os.path.join(os.getcwd(), "raw captures")
    os.makedirs(base, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%d-%m-%Y_%H.%M.%S")
    path = os.path.join(base, f"cdl_{stamp}.log")

    buffers: list[tuple[int, bytes]] = []
    started = time.monotonic()
    deadline = started + args.seconds
    try:
        while time.monotonic() < deadline:
            try:
                raw = src.read_raw_hex()
            except Exception:                     # noqa: BLE001 - keep going
                continue
            if raw:
                buffers.append((int((time.monotonic() - started) * 1000),
                                bytes.fromhex(raw)))
            else:
                time.sleep(0.01)
    finally:
        try:
            src.close()
        except Exception:                         # noqa: BLE001
            pass

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# OpenTruck Cat Data Link capture (listen-only, raw "
                 "RP1210 buffers)\n")
        fh.write("# adapter: %s [%s]  protocol: %s\n" % (a.name, a.code, cat))
        fh.write("# <elapsed_ms> <HEX of the whole receive buffer>\n")
        for ms, b in buffers:
            fh.write(f"{ms} {b.hex().upper()}\n")

    # Summary: enough to identify the framing without leaving the truck.
    print(f"\ncaptured {len(buffers)} buffer(s) -> {path}")
    connectlog.write("CDL capture: %d buffer(s) in %.0f s -> %s"
                     % (len(buffers), args.seconds, path))
    if not buffers:
        print("No CDL bytes received - either the machine's CDL is not wired "
              "to this connector or it is idle. Try with the key ON and a "
              "function active (hydraulics moving, engine running).")
        return

    lengths = Counter(len(b) for _, b in buffers)
    print("buffer lengths:", dict(sorted(lengths.items())))
    # Candidate header bytes at the two plausible layouts: [ts][msg...] puts
    # the message header at offset 4; a bare [msg...] puts it at offset 0.
    for offset, label in ((4, "byte[4] (assuming a 4-byte timestamp)"),
                           (0, "byte[0] (assuming no timestamp)")):
        hist = Counter(b[offset] for _, b in buffers if len(b) > offset)
        top = ", ".join("0x%02X x%d" % (v, n)
                        for v, n in hist.most_common(8))
        print(f"{label}: {top}")
    first = buffers[:5]
    print("first buffers:")
    for ms, b in first:
        print(f"  {ms:6d} {b.hex().upper()}")


if __name__ == "__main__":
    main()