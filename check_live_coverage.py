"""OpenTruck - live-data PGN coverage audit.

Reads OpenTruck capture/replay logs and reports, per transmitting module
(source address), WHICH live-data PGNs appeared and whether
``modules.livedata.decode_live`` already decodes them.

Purpose: this shows exactly where the live-data coverage gap is for a real
truck, so a new PGN decoder can be added for the parameters that are actually
broadcast (see ``modules.livedata.PGN_FIELDS`` - add a scalar PGN as a few table
rows, or a ``_SPECIAL`` handler for bit/status/conditional logic). Undecoded
PGNs listed as coverage gaps are the ones to add next.

Accepts OpenTruck's raw capture format (``<arbid_hex>:<data_hex>`` and the
tabular ``rel_ms  arbid  data  src=..  dst=..  pgn=..`` layout) and J1939 replay
logs (auto-detected). Control frames (address claim, DM1/2, CI/VI identity,
transport protocol) are skipped; only periodic live-data broadcasts are counted.

Usage:
    python check_live_coverage.py "raw captures/<capture>.log" [more ...]
"""
from __future__ import annotations

import re
import sys

from modules.j1939 import PGN
from modules.livedata import pgn_name, PGN_FIELDS, _SPECIAL

# A PGN is "decoded" (coverage) if we have a handler for it, even when a given
# frame's values are all error/not-available sentinels (which decode_live skips).
_has_decoder = lambda pgn: pgn in PGN_FIELDS or pgn in _SPECIAL


def _is_proprietary(pgn: int) -> bool:
    """Whether the PGN is in a J1939 manufacturer-proprietary range (no public
    standard layout exists): proprietary A (0xEF00 block) and proprietary B
    (0xFF00-0xFFFF)."""
    return (pgn & 0xFF00) == 0xEF00 or pgn >= 0xFF00

# PGNs handled by the transport / identity / diagnostics layers, not live data.
_SKIP = (PGN.DM1, PGN.DM2, PGN.TP_CM, PGN.TP_DT, PGN.CI, PGN.VI,
         PGN.SOFTWARE_ID, PGN.ECU_ID, 0xEE00)

_HEX = re.compile(r"[0-9A-Fa-f]+")


def _raw_frames(path: str) -> list:
    """Parse raw-capture lines into ``(pgn, source, data)`` tuples, or [] if
    the file is not a raw format (caller falls back to the J1939 replay path)."""
    frames: list[tuple[int, int, bytes]] = []
    try:
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        raise
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        # Session logs prefix every frame with its direction. TX frames are our
        # own transmissions (requests/replies), not vehicle live data.
        first = s.split()[0] if s else ""
        if first == "TX":
            continue
        if first == "RX":
            s = s[3:].strip()
        arbid = None
        data = None
        # colon form: "<arbid>:<data>"  e.g. 0CF00400:F07D86731700FF86
        if ":" in s and not s.split()[0].startswith("0.") and \
                len(s.split(":", 1)) == 2:
            left, right = s.split(":", 1)
            left, right = left.strip(), right.strip()
            if _HEX.fullmatch(left) and _HEX.fullmatch(right):
                try:
                    arbid = int(left, 16)
                    data = bytes.fromhex(right)
                except ValueError:
                    arbid = data = None
        if arbid is None:
            # tabular form: rel_ms  arbid  data  src=..  dst=..  pgn=..
            toks = s.split()
            if len(toks) >= 3 and _HEX.fullmatch(toks[1]) and \
                    _HEX.fullmatch(toks[2]):
                try:
                    arbid = int(toks[1], 16)
                    data = bytes.fromhex(toks[2])
                except ValueError:
                    arbid = data = None
        if arbid is None or data is None:
            continue
        if arbid <= 0x7FF:                    # 11-bit / non-J1939 frame
            continue
        # Correct J1939 PDU1/PDU2 handling. PDU1 (PF < 240) is peer-to-peer:
        # the PS byte is the DESTINATION, not part of the PGN - and a directed
        # frame is a request/reply (diagnostic traffic), not periodic live data.
        # PDU2 (PF >= 240): PS is part of the PGN (broadcast).
        pf = (arbid >> 16) & 0xFF
        if pf < 240:
            dst = (arbid >> 8) & 0xFF
            if dst not in (0xFF, 0x00):
                continue
            frames.append(((arbid >> 8) & 0x3FF00, arbid & 0xFF, data))
        else:
            frames.append(((arbid >> 8) & 0x3FFFF, arbid & 0xFF, data))
    return frames


def audit_raw(path: str) -> dict:
    counts: dict[tuple[int, int], tuple[int, bool]] = {}
    for pgn, source, data in _raw_frames(path):
        if source in (0xFF, 0xFE, 0xF9) or pgn in _SKIP:
            continue
        key = (source, pgn)
        n, _d = counts.get(key, (0, False))
        counts[key] = (n + 1, _has_decoder(pgn))
    return counts


def audit_replay(path: str) -> dict:
    """Fallback: J1939 replay logs via ReplaySource."""
    from framesource import ReplaySource
    src = ReplaySource(path)
    counts: dict[tuple[int, int], tuple[int, bool]] = {}
    while True:
        frame = src.read_frame()
        if frame is None:
            break
        pgn, source, data = frame.pgn, frame.source, frame.data
        if source in (0xFF, 0xFE, 0xF9) or pgn in _SKIP:
            continue
        key = (source, pgn)
        n, _d = counts.get(key, (0, False))
        counts[key] = (n + 1, _has_decoder(pgn))
    return counts


def report(counts: dict, path: str) -> None:
    print(f"\n=== Live-data PGN coverage: {path} ===")
    per_source: dict[int, list] = {}
    raw_total = 0
    for (s, pgn), (n, decoded) in counts.items():
        per_source.setdefault(s, []).append((pgn, n, decoded))
        raw_total += n

    for s in sorted(per_source):
        rows = sorted(per_source[s], key=lambda r: -r[1])
        print(f"  SA {s:#04x}:")
        for pgn, n, decoded in rows:
            mark = "  " if decoded else "!! UNDECODED"
            print(f"      {pgn_name(pgn):<44} x{n:<5} {mark}")

    undecoded = {p for (_s, p), (_n, d) in counts.items() if not d}
    decoded = len(counts) - len(undecoded)
    print(f"\n  summary: {len(counts):>4} unique (module,PGN) pairs, "
          f"{decoded} decoded, {len(undecoded)} undecoded, {raw_total} live frames")
    if undecoded:
        std = [p for p in undecoded if not _is_proprietary(p)]
        prop = [p for p in undecoded if _is_proprietary(p)]
        if std:
            print("  coverage gaps - standard PGNs (add these to modules.livedata):")
            for p in sorted(std):
                print(f"      PGN 0x{p:04X}  {pgn_name(p)}")
        if prop:
            print("  proprietary PGNs (manufacturer-specific - NOT decodable from")
            print("  public standards; needs OEM documentation):")
            for p in sorted(prop):
                print(f"      PGN 0x{p:04X}  {pgn_name(p)}")


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    for path in argv:
        counts = audit_raw(path)
        if not counts:
            try:
                counts = audit_replay(path)
            except OSError as exc:
                print(f"cannot open {path}: {exc}", file=sys.stderr)
                return 1
        report(counts, path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
