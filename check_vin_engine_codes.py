"""OpenTruck - verify the offline VIN engine-code table against reference.

Run from the project root:  python check_vin_engine_codes.py

Why this exists: the engine line on the OBD-II vehicle panel resolves
fully offline from the VIN (positions 1-3 WMI + position 8 engine code +
model year + positions 4-7 / 10-17 context where a code is shared across
vehicle lines) via lookup/vin_engine_codes.py, compiled from the NHTSA
vPIC standalone database (vPICList_lite_2026_10). On 2026-11-15 the first
pure-code table was verified 40/40 against the live DecodeVinValues API;
when the table gained VIN-context disambiguation (shared codes such as
1FT "R" = 5.4 F-150 vs 6.4 Super Duty), the reference set was re-verified
against the API. The samples are kept here so a future table edit that
drifts from the public dataset fails loudly.

Behavioral checks cover the honest fallbacks: unsupported WMI, malformed
VIN, unknown code or context (raw code shown, never a guess) and the
1996-2027 window; structural checks cover the table's context tuples,
fact tuples and year ranges.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lookup.vin_engine_codes import (
    ENGINE_CODES, ANY4, ANY8, _FUEL, engine_for_vin,
)
from lookup.vin import model_year

_ALPHA = "ABCDEFGHJKLMNPRSTVWXYZ"


def _mkvin(wmi: str, code: str, year: int) -> str:
    """Synthetic 17-char VIN for (wmi, code, year); check digit is filler."""
    if 2001 <= year <= 2009:
        yc = str(year - 2000)
    elif year >= 2010:
        yc = _ALPHA[(year - 2010) % 30]
    else:
        yc = _ALPHA[(year - 1980) % 21]
    p7 = "1" if 1981 <= year <= 2009 else "A"   # digit -> 1980-2009 cycle
    return f"{wmi}AAA{p7}{code}X{yc}1234567"


# (WMI, code, year, displacement L, cylinders, fuel-or-None)
# Pure-position-8 rows: verified against the live vPIC API 2026-11-15.
REF = [
    ("1G6", "H", 2005, 2.2, 4, None),
    ("2G1", "B", 2004, 1.4, 4, None),
    ("1G4", "H", 2005, 2.2, 4, None),
    ("1GB", "P", 2012, 5.3, 8, "Gasoline"),
    ("2G4", "R", 2011, 2.4, 4, "Gasoline"),
    ("1GA", "C", 2011, 2.4, 4, "Gasoline"),
    ("1C3", "G", 2017, 3.6, 6, "Gasoline"),
    ("2G4", "2", 2005, 3.8, 6, "Gasoline"),
    ("2C3", "1", 2009, 3.8, 6, "Gasoline"),
    ("1GJ", "B", 2011, 6.0, 8, "Compressed Natural Gas (CNG)"),
    ("2GN", "9", 2012, 2.9, 4, "Gasoline"),
    ("1A4", "0", 2008, 2.0, 4, "Gasoline"),
    ("1G6", "W", 1996, 4.3, 8, "Gasoline"),
    ("1GK", "L", 2016, 6.6, 8, "Diesel"),
    ("1A4", "D", 2007, 5.7, 8, "Gasoline"),
    ("1GT", "4", 2012, 5.3, 8, "Gasoline"),
    ("3GB", "4", 2016, 5.3, 8, "Gasoline"),
    ("1C3", "5", 2012, 2.8, 4, "Diesel"),
    ("1A4", "X", 2008, 4.0, 6, "Gasoline"),
    ("1GY", "T", 2010, 2.8, 4, "Diesel"),
    ("2G4", "T", 1997, 2.4, 4, None),
    ("2D4", "J", 2002, 4.7, 8, "Gasoline"),
    ("2D4", "A", 2004, 2.7, 4, "Diesel"),
    ("2G4", "C", 1998, 4.0, 8, "Gasoline"),
    ("1D7", "G", 2005, 2.4, 4, "Gasoline"),
    ("3D7", "H", 2004, 8.3, 10, "Gasoline"),
    ("1D4", "X", 2000, 3.9, 6, "Gasoline"),
    ("4M2", "9", 2002, 5.4, 8, "Gasoline"),
    ("3GN", "E", 2012, 1.8, 4, None),
    ("2D4", "D", 2011, 2.7, 6, "Gasoline"),
    ("1GD", "5", 2013, 3.0, 6, "Gasoline"),
    ("1G6", "R", 2000, 3.0, 6, None),
    ("1J4", "A", 2003, 2.7, 4, "Diesel"),
    ("2GN", "W", 2011, 2.2, 4, "Flexible Fuel Vehicle (FFV)"),
    ("2C3", "A", 2016, 2.0, 4, "Gasoline"),
    ("6G3", "L", 2014, 2.5, 4, "Gasoline"),
    ("3GY", "R", 2016, 5.3, 8, "Gasoline"),
    ("3G1", "H", 1998, 3.5, 6, "Gasoline"),
    ("1D4", "S", 2008, 3.5, 6, "Gasoline"),
]

# Context rows (full VINs): the same engine code resolving to DIFFERENT
# engines by VIN positions 4-7 - the reason the table carries context.
# (vin, expect displacement L, expect cylinders, expect fuel word or None)
REF_CTX = [
    ("1FTAW42RX81234567", 6.4, 8, "diesel"),    # 2008 Super Duty 6.4 PSD
    ("1FTAN08RX21123456", 5.4, 8, "gasoline"),  # 2002 F-150 5.4 Triton
    ("1FTFW1C5XJF123456", 5.0, 8, "gasoline"),  # 2018 F-150 5.0 (code 5)
]

FUEL_SHORT = {"Gasoline": "gasoline", "Diesel": "diesel",
              "Compressed Natural Gas (CNG)": "CNG",
              "Flexible Fuel Vehicle (FFV)": "FFV",
              "Liquefied Petroleum Gas (propane or LPG)": "LPG"}

failures = []


def fail(msg):
    failures.append(msg)
    print("  FAIL:", msg)


def _assert_facts(desc, displ, cyl, fuel, label):
    m = re.match(r"(\d+(?:\.\d+)?)", desc or "")
    got_displ = float(m.group(1)) if m else None
    if got_displ is None or abs(got_displ - displ) > 0.05:
        fail(f"{label}: displacement {got_displ} != {displ} ({desc!r})")
    m = re.search(r"(\d+)-?cyl|\bV(\d+)\b|\bI(\d+)\b|\bW(\d+)\b", desc or "")
    digits = [g for g in m.groups() if g] if m else []
    got_cyl = int(digits[0]) if digits else None
    if got_cyl != cyl:
        fail(f"{label}: cylinders {got_cyl} != {cyl} ({desc!r})")
    if fuel and fuel not in (desc or "").lower():
        fail(f"{label}: fuel {fuel!r} missing from {desc!r}")


# --- 1. pure reference rows --------------------------------------------- #
print(f"reference rows: {len(REF)}")
for wmi, code, year, displ, cyl, fuel in REF:
    vin = _mkvin(wmi, code, year)
    assert len(vin) == 17
    assert model_year(vin) == year, (vin, model_year(vin), year)
    desc = engine_for_vin(vin)
    if not desc:
        fail(f"{wmi} code={code} year={year}: no description")
        continue
    # Fuel: assert the claim only when the table makes one; a dropped fuel
    # field is the honest resolution of disagreeing vPIC variants.
    short = FUEL_SHORT.get(fuel or "", (fuel or "").lower())
    desc_fuel = [w for w in ("gasoline", "diesel", "CNG", "FFV", "LPG")
                if w.lower() in desc.lower()]
    if desc_fuel and short.lower() not in desc.lower():
        fail(f"{wmi} code={code} year={year}: fuel {short!r} != "
             f"{desc_fuel!r} in {desc!r}")
    if not desc_fuel and fuel:
        print(f"  note: {wmi} code={code} year={year}: "
              f"fuel honestly omitted ({desc!r})")
    _assert_facts(desc, displ, cyl, None, f"{wmi}/{code}/{year}")

# --- 2. context reference rows ------------------------------------------ #
print(f"context rows: {len(REF_CTX)}")
for vin, displ, cyl, fuel in REF_CTX:
    assert len(vin) == 17
    desc = engine_for_vin(vin)
    if not desc:
        fail(f"{vin}: no description")
        continue
    _assert_facts(desc, displ, cyl, fuel, vin)

# --- 3. honest fallbacks -------------------------------------------------- #
print("fallbacks:")
vin = _mkvin("1FT", "R", 2018)   # no 2018 data for 1FT "R": code 5 is the
r = engine_for_vin(vin)           # 2018 5.0; the raw code must show
if r != 'VIN engine code "R"':
    fail(f"1FT/R/2018 should show the raw code, got {r!r}")
if engine_for_vin("XXXXXXXXXXXXXXXXX") is not None:
    fail("unsupported WMI must return None")
if engine_for_vin("1GB") is not None:
    fail("malformed VIN must return None")
if engine_for_vin("") is not None:
    fail("empty VIN must return None")

# --- 4. window boundary ---------------------------------------------------- #
print("window boundary:")
# Before 1996 (pre-OBD-II): must not resolve to a 1996+ entry.
r1995 = engine_for_vin(_mkvin("1C3", "G", 1995))
r2017 = engine_for_vin(_mkvin("1C3", "G", 2017))
if r1995 and r1995 == r2017:
    fail("1995 VIN must not reuse the 2017 3.6 entry")

# --- 5. table structure ------------------------------------------------------ #
print("structure:")
valid_chars = set("0123456789ABCDEFGHJKLMNPRSTUVWXYZ")
n_checks = 0
for wmi, chars in ENGINE_CODES.items():
    if len(wmi) != 3 or not wmi.isalnum():
        fail(f"bad WMI key {wmi!r}")
    for c, entries in chars.items():
        if c not in valid_chars and c != "?":
            fail(f"{wmi}: bad code char {c!r}")
        seen = {}   # (lctx, rctx, facts) -> last yt
        for entry in entries:
            n_checks += 1
            if len(entry) != 5:
                fail(f"{wmi}/{c}: entry is not a 5-tuple")
                continue
            yf, yt, lctx, rctx, facts = entry
            if not (1996 <= yf <= yt <= 2027):
                fail(f"{wmi}/{c}: bad year range {yf}-{yt}")
            if len(lctx) != 4 or len(rctx) != 8:
                fail(f"{wmi}/{c}: bad ctx lengths {len(lctx)}/{len(rctx)}")
            for tok in lctx + rctx:
                if tok and not set(tok) <= valid_chars:
                    fail(f"{wmi}/{c}: bad ctx token {tok!r}")
            if len(facts) != 6:
                fail(f"{wmi}/{c}: bad facts arity")
            d, cy, conf, fuel, turbo, em = facts
            if d is not None and not isinstance(d, (int, float)):
                fail(f"{wmi}/{c}: displacement not numeric: {d!r}")
            if cy is not None and not isinstance(cy, int):
                fail(f"{wmi}/{c}: cylinders not int: {cy!r}")
            if conf is not None and conf not in ("V", "I", "W", "U"):
                fail(f"{wmi}/{c}: bad configuration {conf!r}")
            if fuel is not None and not (fuel in _FUEL
                                         or (isinstance(fuel, str) and len(fuel) > 1)):
                fail(f"{wmi}/{c}: bad fuel code {fuel!r}")
            if turbo is not None and not isinstance(turbo, bool):
                fail(f"{wmi}/{c}: bad turbo {turbo!r}")
            if em is not None and not isinstance(em, str):
                fail(f"{wmi}/{c}: bad engine model {em!r}")
            key = (lctx, rctx, facts)
            if key in seen and yf <= seen[key]:
                fail(f"{wmi}/{c}: overlapping ranges for identical entry at {yf}")
            seen[key] = max(yt, seen.get(key, 0))

# ANY constants must be the all-any tuples the generator emits
if ANY4 != ("", "", "", "") or ANY8 != ("",) * 8:
    fail("ANY4/ANY8 are not the all-any tuples")

# --- 6. WMI / WMC / vPIC engine-model tables (2026-11-17) --------------- #
# The frame-stamped identification layer, generated from public data by
# the project's table generator: WMI -> make (NHTSA vPIC, public domain),
# WMC -> maker (AEM ISO 10261 list), VIN -> engine model (vPIC element-18
# pattern chain). Reference rows below were verified against the live vPIC
# DecodeVinValues API on 2026-11-17: 1HTWGAAT6FH608218 -> Make INTERNATIONAL
# / EngineModel "DT466/Maxxforce DT"; 3FRPF75A28V691335 -> Make FORD /
# EngineModel empty.
from lookup.vin import (WMI_NAMES, WMC_NAMES, ident_make,   # noqa: E402
                        engine_model_for_vin, vehicle_model_for_vin,
                        WMI_SCHEMAS)

print(f"\nWMI/WMC/engine tables: {len(WMI_NAMES)} WMI, {len(WMC_NAMES)} WMC")


def _chk(cond, msg):
    global n_checks
    n_checks += 1
    if not cond:
        fail(msg)


_chk(len(WMI_NAMES) >= 12000, f"WMI table too small: {len(WMI_NAMES)}")
_chk(len(WMC_NAMES) >= 1200, f"WMC table too small: {len(WMC_NAMES)}")
_chk(WMI_NAMES.get("3FR") == "Ford", f"3FR -> {WMI_NAMES.get('3FR')!r}")
_chk((WMI_NAMES.get("1HT") or "").lower().startswith("international"),
     f"1HT -> {WMI_NAMES.get('1HT')!r}")
_chk(WMC_NAMES.get("1E0") == "Deere & Company",
     f"1E0 -> {WMC_NAMES.get('1E0')!r}")
_chk("caterpillar" in (WMC_NAMES.get("CAT") or "").lower(),
     f"CAT -> {WMC_NAMES.get('CAT')!r}")
# Collision policy: 1XP is Peterbilt (WMI) AND a Deere WMC - context decides.
_chk((ident_make("1XP00000000000000", machine=False) or "").lower()
     .startswith("peterbilt"), "1XP on a truck bus should be Peterbilt")
_chk(ident_make("1XP00000000000000", machine=True) == "Deere & Company",
     "1XP on a machine bus should be Deere & Company")
_chk(engine_model_for_vin("1HTWGAAT6FH608218") == "DT466/Maxxforce DT",
     f"engine intl -> {engine_model_for_vin('1HTWGAAT6FH608218')!r}")
_chk(engine_model_for_vin("3FRPF75A28V691335") is None,
     "F-750 has no vPIC engine model; must stay None")
# vPIC model/series chain (API-verified 2026-11-17: Model/Series values).
_chk(vehicle_model_for_vin("3FRPF75A28V691335") == ("F-750", "F-Series Super Duty"),
     f"F-750 model -> {vehicle_model_for_vin('3FRPF75A28V691335')!r}")
_chk(vehicle_model_for_vin("1HTWGAAT6FH608218") == ("SF625", "WorkStar 7400"),
     f"WorkStar model -> {vehicle_model_for_vin('1HTWGAAT6FH608218')!r}")
# vPIC displacement/cylinders/fuel fallback (API-verified: 6.7 L, 6 cyl,
# Diesel for the 2008 F-750, whose schema declares no engine MODEL).
from lookup.vin import engine_spec_for_vin   # noqa: E402
_chk(engine_spec_for_vin("3FRPF75A28V691335") == "6.7 L 6-cyl diesel",
     f"F-750 spec -> {engine_spec_for_vin('3FRPF75A28V691335')!r}")
# Spec is no longer limited to schemas with no engine model: vPIC carries
# displacement/cylinders for the ISX, MBE-900 and even the F-350 (whose
# schema has engine rows that do not match this VIN's pattern).
_chk(engine_spec_for_vin("1NKXX4EX0CJ123456") == "15 L 6-cyl diesel",
     f"ISX spec -> {engine_spec_for_vin('1NKXX4EX0CJ123456')!r}")
_chk(engine_spec_for_vin("2FZACGCT37AY10461") == "6.4 L 6-cyl diesel",
     f"MBE-900 spec -> {engine_spec_for_vin('2FZACGCT37AY10461')!r}")
_chk(engine_spec_for_vin("1FDWF36R28EC71345") == "6.4 L 8-cyl diesel",
     f"F-350 spec -> {engine_spec_for_vin('1FDWF36R28EC71345')!r}")

# --- 7. truck/bus VIN engine tables + heavy-truck model year ------------- #
# vPIC covers heavy trucks at manufacturer-specific VIN positions (NOT the
# light-duty position 8), so the engine/model/series chains above are the
# truck decode. 2026-11-17 broadened the curated set to the North American
# commercial-vehicle makers (truck JVs/chassis, bus/coach body builders,
# fire/emergency chassis) on top of the highway-truck and ag Set A.
from lookup.vin import model_year   # noqa: E402
_chk((WMI_NAMES.get("3HA") or "").lower().startswith("blue diamond"),
     f"3HA -> {WMI_NAMES.get('3HA')!r}")
_chk(WMI_NAMES.get("4DR") == "Ic Bus", f"4DR -> {WMI_NAMES.get('4DR')!r}")
_chk(WMI_NAMES.get("5KJ") == "Daimler Truck North America",
     f"5KJ -> {WMI_NAMES.get('5KJ')!r}")
_chk(WMI_NAMES.get("1BA") == "Blue Bird Body",
     f"1BA -> {WMI_NAMES.get('1BA')!r}")
for _w in ("3HA", "3HB", "3HC", "4DR", "5KJ", "1BA", "10T", "15G",
           "2FY", "1T7", "4P1"):
    _chk(bool(WMI_SCHEMAS.get(_w)), f"no vPIC schemas for commercial WMI {_w}")
# Blue Diamond / IC Bus (International-based) engine chains resolve.
_chk(engine_model_for_vin("3HAXXAAX0A1234567") == "International DT466/Maxxforce DT",
     f"3HA engine -> {engine_model_for_vin('3HAXXAAX0A1234567')!r}")
_chk(engine_model_for_vin("4DRXXAAX0A1234567") == "International DT466/Maxxforce DT",
     f"4DR engine -> {engine_model_for_vin('4DRXXAAX0A1234567')!r}")
# New Flyer transit bus: electric-drive chain (2012-2023 schema).
_chk(engine_model_for_vin("2FYXXXJX0D1234567") == "Electric Drive",
     f"2FY engine -> {engine_model_for_vin('2FYXXXJX0D1234567')!r}")
# Heavy-truck model year: the 7th-position rule is a passenger-car convention.
# Real 2007 Sterling 2FZACGCT37AY10461 (letter at position 7) used to resolve
# to 2037; the vPIC schema year ranges now correct it (TODO archive item).
_chk(model_year("2FZACGCT37AY10461") == 2007,
     f"Sterling year -> {model_year('2FZACGCT37AY10461')!r}")
_chk(engine_model_for_vin("2FZACGCT37AY10461") == "MBE-900",
     f"Sterling engine -> {engine_model_for_vin('2FZACGCT37AY10461')!r}")
_chk(vehicle_model_for_vin("2FZACGCT37AY10461") == ("Acterra", None),
     f"Sterling model -> {vehicle_model_for_vin('2FZACGCT37AY10461')!r}")
# Light-duty model years must be unchanged by the heavy-truck correction.
_chk(model_year("1FTFW1EF7BKD90291") == 2011,
     f"F-150 year -> {model_year('1FTFW1EF7BKD90291')!r}")
_chk(model_year("1HTWGAAT6FH608218") == 2015,
     f"WorkStar year -> {model_year('1HTWGAAT6FH608218')!r}")
_chk(model_year("1NKXX4EX0CJ123456") == 2012,
     f"Kenworth year -> {model_year('1NKXX4EX0CJ123456')!r}")
_chk(engine_model_for_vin("1NKXX4EX0CJ123456") == "ISX",
     f"Kenworth engine -> {engine_model_for_vin('1NKXX4EX0CJ123456')!r}")
# Scope floor: the generated tables stop at 2001 (heavy-duty fleet scope).
from lookup.vin_engine_models import MIN_MODEL_YEAR   # noqa: E402
_chk(MIN_MODEL_YEAR == 2001, f"scope floor -> {MIN_MODEL_YEAR!r}")
_chk(all(a >= MIN_MODEL_YEAR for rows in WMI_SCHEMAS.values()
         for _vs, a, _b in rows),
     "WMI_SCHEMAS still carries a pre-2001 year range")
# A pre-2001 VIN must not be shifted forward into the 2001+ window.
_chk(model_year("1G6AAA1WXT1234567") == 1996,
     f"old VIN year -> {model_year('1G6AAA1WXT1234567')!r}")

# --- 8. no per-unit overrides in the identification path ----------------- #
# The Vehicle panel must be a pure function of the wire (VIN/CI/NAME) and the
# shared tables. A hard-coded VIN in runtime code would hide table defects
# from field testing, so flag any VIN-shaped string LITERAL in the display
# path. Docstrings and comments are allowed (they only document examples).
import ast   # noqa: E402
import os    # noqa: E402

_VIN_LITERAL = re.compile(r"^[1-5][A-HJ-NPR-Z0-9]{16}$")
_runtime_files = ("app.py", "reader.py", "lookup/vin.py",
                  "lookup/manufacturers.py")
_overrides = []
for _rel in _runtime_files:
    _path = os.path.join(os.path.dirname(os.path.abspath(__file__)), _rel)
    with open(_path, encoding="utf-8") as _fh:
        _tree = ast.parse(_fh.read(), filename=_rel)
    _docs = set()
    for _node in ast.walk(_tree):
        if isinstance(_node, (ast.Module, ast.FunctionDef,
                              ast.AsyncFunctionDef, ast.ClassDef)):
            _d = ast.get_docstring(_node, clean=False)
            if _d:
                _docs.add(_d)
    for _node in ast.walk(_tree):
        if (isinstance(_node, ast.Constant)
                and isinstance(_node.value, str)
                and _VIN_LITERAL.match(_node.value.strip())
                and _node.value not in _docs):
            _overrides.append(f"{_rel}:{_node.lineno} {_node.value}")
_chk(not _overrides,
     f"per-unit VIN literal in identification path: {_overrides}")

print()
if failures:
    print(f"FAILED: {len(failures)}")
    sys.exit(1)
print("FAILED: none - all pass")
print(f"checks run: {len(REF) + len(REF_CTX) + 5 + n_checks}")