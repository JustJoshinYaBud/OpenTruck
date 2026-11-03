"""OpenTruck - wire-evidence OEM selection regression.

``lookup/oem.py`` resolves a fault code by selecting the OEM entry (or
entries) a module's identity claims: the CI (Component Identification) make
string and the NAME manufacturer code. Since 2026-11-18 each brand owns ONE
pure code table (``<BRAND>_SPN_FMI``) and per-family routing is GONE - the
only routing left is this selection, which is exactly what makes a code pick
Perkins instead of CAT, or Allison instead of nothing. This script replays the
raw captures through the same Session code path the app uses and asserts that
every CI identity on the wire selects the expected OEM entry.

What it guards:

* **selection misses** - a Perkins-built CAT C6.6 claims manufacturer 93
  while broadcasting the CAT make abbreviation "CTRPL": manufacturer 93 must
  keep selecting Perkins.
* **silent ECUs** - an Allison TCM answers a directed CI request without
  ever claiming an address, so the bare CI make abbreviation ("ALLSN") must
  select the OEM on its own.
* **the reserved manufacturer code** - mfr 0 means "experimental", not a
  vendor, so it must select no OEM.

Run:  python check_oem_selection.py [capture.log ...]
With no arguments every ``raw captures/*.log`` is replayed. Captures are
development data and are NOT required to exist - when none are found the
replay is skipped (nothing is asserted). ``check_j1939.py`` carries the
offline resolution assertions; this script adds only what the wire proves.

Unlisted identities: a CI make/model observed on the wire but not pinned in
EXPECTED below is printed for review, not failed - verify the selection is
right (or fix the make keys), then pin it in EXPECTED.
"""
from __future__ import annotations

import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from check_live_coverage import _raw_frames
from lookup.oem import select_oems
from modules.j1939 import Frame
from reader import Session

ok: list[tuple[str, bool]] = []


def check(name: str, cond) -> None:
    ok.append((name, bool(cond)))


class _Sink:
    """FrameSource stand-in: a replay never transmits."""

    def connect(self) -> None: ...

    def read_frame(self):  # noqa: ANN201 - FrameSource protocol
        return None

    def write_frame(self, frame) -> None: ...

    def close(self) -> None: ...


# (NAME mfr code, CI make, CI model prefix) -> expected OEM id (None = no OEM
# may be selected). ``mfr``/``make`` may be None (ECUs exist that answer a
# directed CI request but never claim an address). Models are matched on a
# PREFIX of the wire value because some ECUs pad with spaces or trail other
# data after the model.
EXPECTED: dict[tuple, str | None] = {
    # Oshkosh airport vehicle: a CAT ECM under the CAT make abbreviation.
    (8, "CTRPL", "EMY2007 CAT C13"): "caterpillar",
    (8, "CTRPL", "C18"): "caterpillar",
    # Perkins-built CAT C6.6 (CAT badge for the 1206E) claims mfr 93.
    (93, "CTRPL", "C6.6L"): "perkins",
    # The same CI with NO manufacturer code (a module that answers a directed
    # CI request but never claims an address): "CTRPL" deliberately selects NO
    # OEM. It is CAT's abbreviation for the MACHINE family, not the engine
    # maker - a Perkins-built C6.6 broadcasts it too - so without the NAME mfr
    # (8 = CAT, 93 = Perkins) there is nothing reliable to select and the
    # generic SAE tables are the honest answer. Pinned so nobody "fixes" it by
    # adding CTRPL to a make_keys list: that would double-select a CAT-badged
    # C13 by make and by mfr (lookup/oem.py's CAT entry says the same).
    (None, "CTRPL", "C6.6L"): None,
    # MaxxForce DT: the ECM's CI model is a part-number string.
    (42, "INT", "466224241311696"): "navistar",
    # Navistar ECU broadcasting a bare part number.
    (43, "INT", "3868370C97"): "navistar",
    # Allison TCM (transmission codes stay generic SAE until tables exist).
    (2, "ALLSN", "3500 RDS"): "allison",
    # Silent TCM: answers directed CI but never claims an address, so the
    # CI make abbreviation alone must select the OEM.
    (None, "ALLSN", "2500RDS"): "allison",
    (None, "ALLSN", "4000RDS"): "allison",
    # Daimler engine controllers that never claimed an address.
    (None, "MRCBN", "906"): "dtna",
    (79, "MRCBN", "906"): "dtna",
    # Bendix EC60 trailer ABS controller.
    (None, "BNDWS", "EC60"): "bendix",
    # John Deere engine - harvested table, no OEM-wide trust yet.
    (33, None, "6068HF"): "johndeere",
    # Manufacturer code 0 is "experimental/reserved" - no OEM may be picked.
    (0, "DCU17", "0281020182"): None,
}


def _norm(s: str | None) -> str | None:
    """Normalise a wire CI field: strip padding and NUL filler."""
    if s is None:
        return None
    return s.strip().strip("\x00").strip()


def _replay(path: str) -> dict[tuple, frozenset]:
    """Feed one capture through the real Session; return identity -> OEM ids."""
    sess = Session(_Sink())
    for pgn, src, data in _raw_frames(path):
        try:
            sess.handle(Frame(pgn=pgn, data=data, source=src, timestamp=0.0))
        except Exception:
            pass
    out: dict[tuple, frozenset] = {}
    for addr, m in sorted(sess.modules.items()):
        if not (m.make or m.model):
            continue
        mfr = m.name.manufacturer if m.name is not None else None
        key = (mfr, _norm(m.make), _norm(m.model))
        out[key] = frozenset(o.id for o in select_oems(make=m.make, mfr=mfr))
    return out


def main(argv: list[str]) -> int:
    paths = argv[1:]
    if not paths:
        pattern = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "raw captures", "*.log")
        paths = sorted(glob.glob(pattern))
    if not paths:
        print("no captures found - capture replay skipped "
              "(offline checks live in check_j1939.py)")
        print("checks run: 0")
        return 0

    # Every capture contributes its identities; one identity seen in many
    # captures is asserted once, against the same expectation.
    seen: dict[tuple, frozenset] = {}
    for path in paths:
        for key, ids in _replay(path).items():
            if key not in seen:
                seen[key] = ids
            elif ids != seen[key]:
                check(f"identity {key} selects consistently", False)

    unlisted = []
    for key, ids in sorted(seen.items(), key=repr):
        mfr, make, model = key
        exp_set = None
        for (e_mfr, e_make, e_prefix), e_id in EXPECTED.items():
            if e_mfr == mfr and e_make == make and \
                    (model or "").startswith(e_prefix):
                exp_set = frozenset((e_id,) if e_id else ())
                break
        if exp_set is None:
            unlisted.append((key, ids))
            continue
        name = f"{mfr}/{make}/{model[:24]}"
        check(f"{name} selects {sorted(ids) or 'no OEM'}", ids == exp_set)

    print(f"captures replayed: {len(paths)}")
    print("checks run:", len(ok))
    failed = [n for n, c in ok if not c]
    if unlisted:
        print()
        print("unlisted wire identities (verify the selection, then pin in "
              "EXPECTED):")
        for (mfr, make, model), ids in unlisted:
            print(f"    {mfr}  make={make!r}  model={model[:40]!r}  "
                  f"-> oem={sorted(ids) or 'NONE'}")
    print("FAILED:", failed if failed else "none - all pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))