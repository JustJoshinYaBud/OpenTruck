"""Live VIN probe (diagnostic tool).

Connects to the RP1210 adapter and works out *how* the VIN (Vehicle
Identification, PGN 65260 / 0xFEEC) can be resolved on this particular truck:

  1. passively listens briefly, to catch any periodic VI/CI broadcast;
  2. sends a single GLOBAL Vehicle Identification request (DA = 0xFF);
  3. runs the same "trickle" sweep the GUI uses: VI / CI / Software-ID / ECU-ID
     requests directed to every J1939 source address 0x00..0xFD, one address
     per --tick-ms (default 20 ms), to find "silent" ECUs that only answer a
     request addressed to them;
  4. drains passively again to catch late replies.

Every received frame is written to ``raw captures/probe_vin_<ts>.log`` and the
end prints which source addresses answered which identification PGN, plus any
17-character VINs found. This is read-only with respect to the vehicle (it only
sends standard Request messages).
"""
from __future__ import annotations

import argparse
import datetime
import os
import time
from collections import defaultdict

from modules.j1939 import Frame, PGN, TransportProtocol
from reader import _decode_ascii_fields
from rp1210 import RP1210Source

TOOL = 0xF9
IDENT_PGNS = (PGN.VI, PGN.CI, PGN.SOFTWARE_ID, PGN.ECU_ID)
PGN_NAMES = {
    PGN.VI: "VI(VIN)",
    PGN.CI: "CI",
    PGN.SOFTWARE_ID: "SW-ID",
    PGN.ECU_ID: "ECU-ID",
}


def _request(src: RP1210Source, dest: int, pgn: int, fh) -> None:
    frame = Frame(pgn=PGN.REQUEST, source=TOOL, destination=dest,
                  priority=6, data=int(pgn).to_bytes(3, "little"))
    try:
        src.write_frame(frame)
        fh.write(f"TX {frame.to_log_line()}\n")
    except Exception:  # noqa: BLE001 - keep probing even if one TX fails
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Live J1939 VIN probe")
    ap.add_argument("--passive", type=float, default=2.0,
                    help="initial passive listen, seconds (default 2)")
    ap.add_argument("--global-wait", type=float, default=2.5,
                    help="listen after the global VI request, seconds (default 2.5)")
    ap.add_argument("--tick-ms", type=int, default=20,
                    help="delay between swept addresses, ms (default 20)")
    ap.add_argument("--drain", type=float, default=4.0,
                    help="final passive listen after the sweep, seconds (default 4)")
    args = ap.parse_args()

    src = RP1210Source()
    print("Connecting to RP1210 adapter (J1939, baud=Auto)...")
    try:
        src.connect()
    except Exception as exc:  # noqa: BLE001
        print(f"CONNECT FAILED: {exc}")
        return 2
    print("Connected.\n")

    raw_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw captures")
    os.makedirs(raw_dir, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%d-%m-%Y_%H.%M.%S")
    logpath = os.path.join(raw_dir, f"probe_vin_{stamp}.log")
    fh = open(logpath, "w", encoding="utf-8")
    fh.write("# probe_vin capture (RX = received, TX = our requests)\n")

    tp = TransportProtocol()
    seen_src: set[int] = set()
    ident_hits: dict[int, dict[int, list[str]]] = defaultdict(dict)
    vin_by_src: dict[int, str] = {}
    pgn_count: dict[int, int] = defaultdict(int)
    total = 0

    def handle_ident(addr: int, pgn: int, payload: bytes) -> None:
        nonlocal total
        fields = _decode_ascii_fields(payload)
        ident_hits[addr][pgn] = fields
        if pgn == PGN.VI and fields:
            vin = fields[0].replace("\x00", "").strip()
            if vin and vin != "0" * len(vin):
                vin_by_src[addr] = vin
                print(f"  ** VIN from src 0x{addr:02X}: {vin}")

    def record(frame: Frame) -> None:
        nonlocal total
        total += 1
        pgn_count[frame.pgn] += 1
        fh.write(f"RX {frame.to_log_line()}\n")
        if frame.source in (TOOL, 0xFF):
            return
        seen_src.add(frame.source)
        # Multi-frame ident (VI/CI are almost always BAM-transported) ...
        done = tp.feed(frame)
        if done:
            real_pgn, payload = done
            if real_pgn in IDENT_PGNS:
                handle_ident(frame.source, real_pgn, payload)
            else:
                pgn_count[real_pgn] += 1
        elif frame.pgn in IDENT_PGNS:
            # ... or delivered whole by an adapter that reassembles in hardware.
            handle_ident(frame.source, frame.pgn, frame.data)

    def listen(duration: float, label: str) -> None:
        start_total = total
        end = time.monotonic() + duration
        while time.monotonic() < end:
            f = src.read_frame()
            if f is None:
                time.sleep(0.003)
                continue
            record(f)
        print(f"[{label}] {total - start_total} frame(s)")

    # --- Phase 1: passive --------------------------------------------------- #
    print("Phase 1: passive listen (no requests)...")
    listen(args.passive, "passive")

    # --- Phase 2: global VI request ---------------------------------------- #
    print("\nPhase 2: GLOBAL Vehicle-Identification request (0xFEEC -> 0xFF)...")
    _request(src, 0xFF, PGN.VI, fh)
    listen(args.global_wait, "global VI")

    # --- Phase 3: trickle sweep -------------------------------------------- #
    addresses = [a for a in range(0x00, 0xFE) if a != TOOL]
    print(f"\nPhase 3: trickle sweep  {len(addresses)} addresses x "
          f"{len(IDENT_PGNS)} PGNs  @ {args.tick_ms} ms ...")
    t0 = time.monotonic()
    last_send = 0.0
    idx = 0
    while idx < len(addresses):
        now = time.monotonic()
        if now - last_send >= args.tick_ms / 1000.0:
            addr = addresses[idx]
            idx += 1
            for pgn in IDENT_PGNS:
                _request(src, addr, pgn, fh)
            last_send = now
        f = src.read_frame()
        if f is None:
            time.sleep(0.002)
        else:
            record(f)
    print(f"  sweep complete in {time.monotonic() - t0:.1f} s")

    # --- Phase 4: drain ---------------------------------------------------- #
    print("\nPhase 4: passive drain (late replies / periodic broadcasts)...")
    listen(args.drain, "drain")

    fh.close()
    try:
        src.close()
    except Exception:  # noqa: BLE001
        pass

    # --- Summary ----------------------------------------------------------- #
    print("\n================= SUMMARY =================")
    print(f"Frames received : {total}")
    print(f"Source addresses: {len(seen_src)}"
          + (" -> " + ", ".join(f"0x{a:02X}" for a in sorted(seen_src)) if seen_src else ""))
    print("\nIdentification responders:")
    if not ident_hits:
        print("  (none) - no ECU answered VI/CI/SW-ID/ECU-ID")
    for addr in sorted(ident_hits):
        items = ident_hits[addr]
        print(f"  0x{addr:02X}: "
              + ", ".join(PGN_NAMES.get(p, f"0x{p:X}") for p in items))
        for pgn, fields in items.items():
            if pgn == PGN.VI and fields:
                print(f"      VI -> {fields[0]!r}")
            elif pgn == PGN.CI and len(fields) >= 2:
                print(f"      CI -> make={fields[0]!r} model={fields[1]!r}")
    print(f"\nVINs found      : {dict((f'0x{a:02X}', v) for a, v in vin_by_src.items()) or 'NONE'}")
    print(f"Raw log         : {logpath}")
    print("==========================================")
    return 0 if vin_by_src else 1


if __name__ == "__main__":
    raise SystemExit(main())
