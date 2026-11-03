"""OpenTruck - aftertreatment EGT sensor position names, per OEM/engine.

J1939 SPNs 3241/3249/3245 ("Aftertreatment 1 Exhaust Gas Temperature 1/2/3")
and SPN 1737 ("Exhaust Gas Temperature", IC1) are OEM-APPLICATION-SPECIFIC:
the SPN proves a sensor exists, never where it sits. One OEM's EGT 1 is a DOC
inlet thermocouple; another's is an aftertreatment burner flame sensor; a
DPF-only truck has no SCR-position sensor at all. There is NO universal
mapping - applying one WILL show values under the wrong component.

Design:
  * DEFAULT (no confirmed data): neutral labels naming the SPN -
    "Exhaust Temperature 1 (SPN 3241)" - so a tech can cross-reference the
    SPN against OEM documentation without being misled.
  * ENGINE_POSITIONS below lists every major North-American highway engine
    family. Entries start UNCONFIRMED (empty positions); a position label is
    filled ONLY from confirmed field data (a technician's confirmation on
    that exact engine, or OEM documentation). `confirmed` marks the state.
  * Matching: the engine's CI make + model strings (maker substring, model
    substring). Never guess a mapping for an unconfirmed engine.

Regenerate/extend per engine as field confirmations come in.
"""
from __future__ import annotations

from typing import Optional

# Which SPN is which EGT sensor number (per our decoders in livedata.py).
SPN_EGT_NUMBER = {1737: None, 3241: 1, 3249: 2, 3245: 3}


def neutral_egt_label(spn: int) -> str:
    """Neutral, SPN-identified label (the default when nothing is confirmed)."""
    n = SPN_EGT_NUMBER.get(spn)
    if n is None:
        return f"Exhaust Temperature (SPN {spn})"
    return f"Exhaust Temperature {n} (SPN {spn})"


class EngineEGTEntry:
    __slots__ = ("maker", "models", "positions", "confirmed", "note")

    def __init__(self, maker: str, models: list[str],
                 positions: Optional[dict[int, str]] = None,
                 confirmed: bool = False, note: str = "") -> None:
        self.maker = maker
        self.models = [m.upper() for m in models]
        self.positions = positions or {}
        self.confirmed = confirmed
        self.note = note

    def matches(self, make: str, model: str) -> bool:
        mk = (make or "").upper()
        md = (model or "").upper()
        if self.maker not in mk:
            return False
        return any(m in md for m in self.models)


# Every major North-American highway engine family. Entries whose `positions`
# are empty are UNCONFIRMED: they exist so the framework is complete and the
# confirmation work is enumerable - they contribute NOTHING to labels until
# confirmed. Fill `positions` (SPN -> position label) only from confirmed
# data and set confirmed=True.
ENGINE_POSITIONS: list[EngineEGTEntry] = [
    # --- confirmed entries ------------------------------------------------ #
    #
    # ARD = the Caterpillar Aftertreatment Regeneration Device (the burner/
    # igniter "ARD head" on CAT engines). It is a CAT term only: it does NOT
    # describe any Navistar/International aftertreatment hardware. Do not
    # apply "flame temperature / ARD" wording to a non-CAT engine.
    EngineEGTEntry(
        "CATERPILLAR",
        ["C13"],
        positions={3245: "Flame Temperature"},
        confirmed=True,
        note="Field-confirmed during a live regeneration on a C13 ACERT "
             "(2007: DOC+DPF, no SCR). Settled decision: (1) SPN 3245 is "
             "the ARD flame temperature - the highest reading of the cycle - "
             "and is the ONLY position named for this engine; (2) SPNs 1737 "
             "and 3241 are the same sensor, the exhaust temperature at the "
             "turbo, deliberately LEFT UNNAMED (neutral SPN labels) - do not "
             "give them a position name; (3) DPF inlet / outlet "
             "(SPN 3242 / 3246, PGN 0xFDB4 / 0xFDB2) already report "
             "correctly and are left exactly as the standard decoders show "
             "them; (4) SPNs 3249/3250 (intermediate) are not fitted."),

    # --- awaiting field confirmation (framework complete, data pending) --- #
    EngineEGTEntry("NAVISTAR",
                   ["MAXXFORCE", "DT", "N9", "N10", "N13", "S13"],
                   note="UNCONFIRMED. An earlier claim that these sensors are "
                        "ARD flame temperatures was wrong: ARD is the "
                        "Caterpillar device, not a Navistar one. Neutral SPN "
                        "labels apply until the "
                        "real MaxxForce sensor positions are confirmed."),
    EngineEGTEntry("INTERNATIONAL",
                   ["MAXXFORCE", "DT", "N9", "N10", "N13", "S13"],
                   note="UNCONFIRMED - same entry as NAVISTAR (International "
                        "is Navistar). See the NAVISTAR note."),
    EngineEGTEntry("CATERPILLAR",
                   ["C7", "C9", "C10", "C12", "C15", "C16", "C18"],
                   note="ACERT families differ: some report a flame temp, "
                        "fuel-dosed ones only have a DOC outlet / DPF inlet. "
                        "Confirm per engine family. LEAD: CAT's own ARD "
                        "documentation lists ARD intake / intermediate / "
                        "outlet temperature sensors (SPNs 2478/2479/2480) - "
                        "on an ARD-equipped engine the EGT SPNs are likely "
                        "those three positions; still confirm per family."),
    EngineEGTEntry("CUMMINS",
                   ["ISB", "B6.7", "ISC", "L8.9", "ISL", "ISM", "ISX",
                    "X12", "X15", "QSX"]),
    EngineEGTEntry("DETROIT",
                   ["SERIES 60", "DD8", "DD13", "DD15", "DD16"],
                   note="Detroit OneBox: DOC+DPF+SCR in one unit."),
    EngineEGTEntry("MACK", ["VED", "MP7", "MP8", "MP10"]),
    EngineEGTEntry("VOLVO", ["VED", "D11", "D13", "D16"]),
    EngineEGTEntry("PACCAR", ["PX-6", "PX-7", "PX-8", "MX-11", "MX-13"]),
    EngineEGTEntry("MERCEDES", ["OM904", "OM906", "OM926", "OM460", "OM471"]),
    EngineEGTEntry("HINO", ["J05", "J08"]),
    EngineEGTEntry("ISUZU", ["4HK1", "6HK1"]),
    EngineEGTEntry("FORD", ["6.7L", "POWER STROKE"],   # F-650/750 (J1939)
                   note="Pickups speak OBD-II, not these J1939 SPNs."),
    EngineEGTEntry("DURAMAX", ["L5P", "L5D", "LGH"],   # GM medium duty
                   note="GM medium-duty (Silverado 5500HD etc.)."),
]


def egt_positions(make: Optional[str],
                  model: Optional[str]) -> tuple[dict[int, str], bool]:
    """Curated EGT positions for this engine.

    Returns (positions, confirmed). Empty positions -> caller shows the
    neutral SPN-identified labels.
    """
    for entry in ENGINE_POSITIONS:
        if entry.matches(make or "", model or ""):
            return dict(entry.positions), entry.confirmed
    return {}, False


# --- per-OEM panel wording (makers rename standard systems) ---------------- #
# (maker-key, model-key or None) -> {substring in label: replacement}.
# Applied to the aftertreatment PANEL row labels only; the live-data table
# keeps the SAE/SPN vocabulary.
PARAM_LABELS: dict[tuple[str, str | None], dict[str, str]] = {
    # Caterpillar calls cooled EGR "Clean Gas Induction" (CGI) on ACERT and
    # later engines - field-confirmed on a C13 ACERT.
    ("CATERPILLAR", None): {
        "EGR": "Clean Gas Induction (CGI)",
    },
}


def label_overrides(make: Optional[str],
                    model: Optional[str]) -> dict[str, str]:
    """Curated panel-label wording overrides for this engine, or {}."""
    for (maker_key, model_key), overrides in PARAM_LABELS.items():
        if maker_key in (make or "").upper() and \
                (model_key is None or model_key in (model or "").upper()):
            return overrides
    return {}