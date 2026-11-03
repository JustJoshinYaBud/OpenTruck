"""OpenTruck - Vehicle Identification Number (VIN) and Product Identification
Number (PIN) decoding.

Decodes the standardised, public parts of a 17-character identifier:

  * World Manufacturer Identifier / World Manufacturer Code (positions 1-3)
    -> vehicle or machine make.
  * Model year (position 10), using the "7th-position rule" to pick the
    1980-2009 vs 2010-2039 cycle.
  * Engine model, from the NHTSA vPIC VIN-descriptor patterns (the engine a
    VIN was built with, e.g. "DT466/Maxxforce DT").

On-highway vehicles carry a VIN (ISO 3779 / NHTSA 49 CFR 565) whose first
three characters are a WMI. Off-highway machines (construction, mining,
agriculture) carry a PIN (ISO 10261) whose first three characters are a World
Manufacturer Code (WMC) issued by AEM (SAE issues the ORV sister list). A PIN
is also 17 characters and structurally parallel to a VIN, so `wmi_make()` and
`model_year()` work on both.

The two registries are NOT interchangeable and can collide (e.g. "1XP" is
Peterbilt on-highway but also a Deere WMC), so they are kept in separate
generated tables (`vin_wmi.py`, `vin_wmc.py`) and chosen by context:
`ident_make(machine=True)` prefers the WMC (a machine bus - see
reader.Session.is_machine_bus), otherwise the WMI. The J1939 NAME
manufacturer code (see `manufacturers.py`) stays the authoritative identifier
when an ECU claims it; these tables are the frame-stamped fallback.

Everything is OFFLINE: no network requests (owner decision 2026-11-15). The
tables are generated from public sources by the project's table generator:

  vin_wmi.py          NHTSA vPIC standalone database (public domain)
  vin_wmc.py          AEM ISO 10261 WMC Public Record List
  vin_engine_models.py  NHTSA vPIC element-18 "Engine Model" patterns
"""
import re
from datetime import date
from typing import Optional

from lookup.vin_wmi import WMI_NAMES      # generated: WMI -> make
from lookup.vin_wmc import WMC_NAMES      # generated: WMC -> maker
from lookup.vin_engine_models import (ENGINE_SCHEMAS, MODEL_SCHEMAS,
                                      SERIES_SCHEMAS, CYLINDERS_SCHEMAS,
                                      DISPLACEMENT_SCHEMAS, FUEL_SCHEMAS,
                                      WMI_SCHEMAS, MIN_MODEL_YEAR)

# Model-year code (position 10) -> offset from the cycle start. The code
# sequence skips I, O, Q, U and Z (30 codes = 21 letters + digits 1..9).
_YEAR_OFFSET = {
    "A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "G": 6, "H": 7,
    "J": 8, "K": 9, "L": 10, "M": 11, "N": 12, "P": 13, "R": 14, "S": 15,
    "T": 16, "V": 17, "W": 18, "X": 19, "Y": 20,
    "1": 21, "2": 22, "3": 23, "4": 24, "5": 25, "6": 26, "7": 27,
    "8": 28, "9": 29,
}


def wmi_make(vin: str) -> Optional[str]:
    """Make from the first three characters: WMI first, WMC as a fallback.

    Context-free convenience (used where the bus classification is unknown);
    prefer :func:`ident_make` when the machine/truck context is known.
    """
    if len(vin) >= 3:
        code = vin[:3].upper()
        return WMI_NAMES.get(code) or WMC_NAMES.get(code)
    return None


def ident_make(identifier: str, machine: bool = False) -> Optional[str]:
    """Make from the identifier's first three characters, using the registry
    that matches the vehicle world.

    ``machine=True`` (the bus is an off-highway machine, see
    reader.Session.is_machine_bus) prefers the AEM WMC registry, because a
    machine PIN's positions 1-3 are a WMC - the two 3-character spaces collide
    (1XP is Peterbilt on-highway and a Deere WMC). On-highway prefers the NHTSA
    WMI. Either registry falls back to the other when the code is only defined
    there.
    """
    if len(identifier) < 3:
        return None
    code = identifier[:3].upper()
    if machine:
        return WMC_NAMES.get(code) or WMI_NAMES.get(code)
    return WMI_NAMES.get(code) or WMC_NAMES.get(code)


def model_year(vin: str) -> Optional[int]:
    """Model year from VIN position 10, or None if it can't be determined.

    Uses the 7th-position rule first: numeric position 7 -> 1980-2009 cycle,
    else 2010-2039 cycle. The rule is a passenger-car convention and fails on
    heavy trucks (a 2007 Sterling 2FZACGCT37AY10461 has a letter at position 7
    and would land in 2037). When the WMI has vPIC schema year ranges (the
    offline engine/model tables) and the heuristic year falls outside every
    range while the other 30-year-cycle year does not, use the covered year.
    That keeps the documented rule for cars and corrects pre-2010 trucks.

    The generated tables cover model years >= MIN_MODEL_YEAR (2001), so a
    pre-2001 VIN must never be shifted forward into that window: the cycle
    swap only applies when the heuristic year itself is >= MIN_MODEL_YEAR.
    For an out-of-scope VIN whose heuristic year is in the future (a letter
    at position 7 on an old truck), the plausible past year is returned.
    """
    if len(vin) < 10:
        return None
    code = vin[9].upper()
    if code not in _YEAR_OFFSET:
        return None
    base = 1980 if (len(vin) >= 7 and vin[6].isdigit()) else 2010
    year = base + _YEAR_OFFSET[code]
    ranges = WMI_SCHEMAS.get(vin[:3].upper())
    if ranges:
        if any(a <= year <= b for _vs, a, b in ranges):
            return year
        alt = year + 30 if year < 2010 else year - 30
        if (year >= MIN_MODEL_YEAR
                and any(a <= alt <= b for _vs, a, b in ranges)):
            return alt
        # Out of scope (pre-2001 or beyond the table): never show a year
        # past the next model year when the other cycle is plausible.
        latest = date.today().year + 1
        if year > latest >= alt:
            return alt
    return year


def _class_chars(body: str) -> set[str]:
    """Characters in a vPIC key class body, e.g. 'FWX' or 'A-C1'."""
    chars: set[str] = set()
    i = 0
    while i < len(body):
        if i + 2 < len(body) and body[i + 1] == "-":
            chars.update(chr(c) for c in range(ord(body[i].upper()),
                                               ord(body[i + 2].upper()) + 1))
            i += 3
        else:
            chars.add(body[i].upper())
            i += 1
    return chars


def _keys_match(keys: str, tail: str) -> bool:
    """Does the vPIC key pattern match the VIN tail (position 4 onward)?

    Keys are positional: '*' = any character, '[ABC]' / '[A-C]' = a character
    set, anything else = a literal. (vPIC's own matcher uses the same
    syntax; e.g. key '*[FWX]75' matched the F-750 VIN 3FRPF75A...)
    """
    k = p = 0
    while k < len(keys):
        if p >= len(tail):
            return False
        ch = keys[k]
        if ch == "*":
            k += 1
            p += 1
        elif ch == "[":
            end = keys.find("]", k)
            if end < 0:
                return False
            if tail[p].upper() not in _class_chars(keys[k + 1:end]):
                return False
            k = end + 1
            p += 1
        else:
            if tail[p].upper() != ch.upper():
                return False
            k += 1
            p += 1
    return True


def _schema_value(vin: str, year: Optional[int], table) -> Optional[str]:
    """First value from a vPIC schema table that matches ``vin`` (exact chain)."""
    vin = (vin or "").strip().upper()
    if len(vin) < 8:
        return None
    yr = year if year is not None else model_year(vin)
    if yr is None:
        return None
    for schema_id, year_from, year_to in WMI_SCHEMAS.get(vin[:3], ()):
        if not (year_from <= yr <= year_to):
            continue
        for keys, value in table.get(schema_id, ()):
            if _keys_match(keys, vin[3:]):
                return value
    return None


def engine_model_for_vin(vin: str, year: Optional[int] = None) -> Optional[str]:
    """Engine model the VIN was built with (vPIC pattern chain), or None.

    WMI + model year select candidate vPIC VIN schemas; each schema's
    pattern rows are a key over VIN positions 4+ ('*' = any) whose value is
    the engine model name (e.g. "DT466/Maxxforce DT"). Exact-match chain,
    first match wins; a VIN whose pattern has no engine declared (common for
    heavy chassis) yields None and the caller keeps the ECM's own CI string.
    """
    return _schema_value(vin, year, ENGINE_SCHEMAS)


def engine_spec_for_vin(vin: str,
                        year: Optional[int] = None) -> Optional[str]:
    """Engine description from vPIC's displacement/cylinders/fuel patterns.

    Works whenever the VIN schema carries the data, whether or not it also
    declares an engine MODEL (heavy chassis often declare no model at all -
    the 2008 F-750 has zero Engine-Model rows in vPIC). Turns "6.7 L,
    6 cylinders, Diesel" into "6.7 L 6-cyl diesel"; the panel shows it as
    context beside the engine name and never as a guess.
    """
    disp = _schema_value(vin, year, DISPLACEMENT_SCHEMAS)
    cyl = _schema_value(vin, year, CYLINDERS_SCHEMAS)
    fuel = _schema_value(vin, year, FUEL_SCHEMAS) or ""
    if not (disp or cyl):
        return None          # fuel alone ("diesel") says nothing - keep CI
    parts = []
    if disp:
        try:                 # vPIC stores '6.40' and '15' as strings
            disp = f"{float(disp):g}"
        except (TypeError, ValueError):
            pass
        parts.append(f"{disp} L")
    if cyl:
        parts.append(f"{cyl}-cyl")
    if fuel:
        # "Flexible Fuel Vehicle (FFV)" -> "ffv"; "Diesel" -> "diesel".
        m = re.search(r"\((.*?)\)", fuel)
        parts.append((m.group(1) if m else fuel).lower())
    return " ".join(parts) or None


def vehicle_model_for_vin(vin: str,
                          year: Optional[int] = None) -> Optional[tuple[str, Optional[str]]]:
    """(model, series) the VIN was built as (vPIC pattern chain), or None.

    Same exact chain as the engine model: vPIC element 28 "Model" and
    element 34 "Series" (e.g. ("F-750", "F-Series Super Duty")). Either may
    be missing; returns None when no model is declared for the VIN.
    """
    model = _schema_value(vin, year, MODEL_SCHEMAS)
    if not model:
        return None
    return model, _schema_value(vin, year, SERIES_SCHEMAS)
