"""OpenTruck - Vehicle Identification Number (VIN) and Product Identification
Number (PIN) decoding.

Decodes the standardised, public parts of a 17-character identifier:

  * World Manufacturer Identifier / World Manufacturer Code (positions 1-3)
    -> vehicle or machine make.
  * Model year (position 10), using the "7th-position rule" to pick the
    1980-2009 vs 2010-2039 cycle.

On-highway vehicles carry a VIN (ISO 3779 / NHTSA 49 CFR 565) whose first
three characters are a WMI. Off-highway machines (construction, mining,
agriculture) carry a PIN (ISO 10261) whose first three characters are a World
Manufacturer Code (WMC) issued by AEM (not NHTSA). A PIN is also 17
characters and structurally parallel to a VIN, so `wmi_make()` and
`model_year()` work on both.

WMI_NAMES therefore holds both registries. The two registries are NOT
interchangeable and can collide (e.g. "1XP" is Peterbilt on-highway but also
John Deere off-highway), so on-highway assignments win and colliding WMC codes
are deliberately omitted. The J1939 NAME manufacturer code (see
`manufacturers.py`) stays the authoritative identifier for off-highway
machines; the WMC below is only a convenience fallback.

The vehicle/machine-descriptor section (positions 4-8) and plant (11) are
manufacturer-specific and are NOT decoded here. The model-year cycle heuristic
is an on-highway VIN rule and may be off for some PINs (see TODO).

Sources: NHTSA vPIC + OEM VIN manuals (on-highway); AEM World Manufacturer
Code list / ISO 10261 (off-highway, https://www.aem.org/safety-product-
leadership/world-manufacturer-code).
"""
from __future__ import annotations

from typing import Optional

# WMI (positions 1-3) -> manufacturer. North-American truck OEM subset.
WMI_NAMES = {
    "1FB": "Ford",
    "1FD": "Ford",
    "1FT": "Ford",
    "1FU": "Freightliner",
    "1FV": "Freightliner",
    "1HA": "International",
    "1HC": "International",
    "1HP": "International",
    "1HS": "International",
    "1HT": "International",
    "1HV": "International",
    "1M1": "Mack",
    "1M2": "Mack",
    "1M3": "Mack",
    "1M4": "Mack",
    "1NK": "Kenworth",
    "1NP": "Peterbilt",
    "1XK": "Kenworth",
    "1XP": "Peterbilt",
    "2FU": "Freightliner",
    "2FV": "Freightliner",
    "2FZ": "Sterling",
    "2NK": "Kenworth",
    "2NP": "Peterbilt",
    "2WK": "Western Star",
    "2WL": "Western Star",
    "2WM": "Western Star",
    "2XK": "Kenworth",
    "2XP": "Peterbilt",
    "3AK": "Freightliner",
    "3AL": "Freightliner",
    "3HA": "International",
    "3HS": "International",
    "4V1": "Volvo",
    "4V2": "Volvo",
    "4V3": "Volvo",
    "4V4": "Volvo",
    "4V5": "Volvo",
    "4V6": "Volvo",
    "4VG": "Volvo",
    "4VL": "Volvo",
    "4VM": "Volvo",
    "4VZ": "Volvo",
    "VG6": "Mack",
    "YV2": "Volvo",

    # ---- Light-duty North America (NHTSA vPIC WMI assignments). ------------
    # Chrysler / Stellantis (FCA US, FCA Canada, Chrysler de Mexico). Verified
    # against vPIC's decodewmi endpoint 2026-11-06; every one of these reports
    # CommonName "Chrysler", which is what `lookup.obd_dtcs_mfg` needs to scope
    # Mopar DTC text. Found by the first live OBD test: a 2013 Ram (WMI 1C6)
    # decoded to brand None because no Mopar prefix was listed at all.
    "1B3": "Dodge", "1B4": "Dodge", "1B7": "Dodge", "1D3": "Dodge",
    "1C3": "Chrysler", "1C6": "Ram", "1C8": "Chrysler",
    "1C4": "Jeep", "1J4": "Jeep", "1J8": "Jeep",
    "2C3": "Chrysler", "2C4": "Jeep",
    "3C4": "Jeep", "3C6": "Ram", "3D3": "Dodge",

    # ---- Light-duty North America: Ford / Lincoln / Mercury ----------------
    # Verified against vPIC's decodewmi endpoint (2026-11-06). Only prefixes
    # vPIC actually returned are listed - "1FZ" decodes to nothing and is
    # deliberately absent. 1FB/1FD/1FT are already in the heavy-truck block
    # above; a duplicate key would silently win here, so they are not repeated.
    "1FA": "Ford", "1FC": "Ford", "1FM": "Ford",
    "1LN": "Lincoln", "1ME": "Mercury",
    "2FM": "Ford", "2FT": "Ford",
    "3FA": "Ford", "3FB": "Ford", "3FD": "Ford",

    # ---- Light-duty North America: General Motors --------------------------
    # vPIC reports CommonName "General Motors" for all of these; the Make field
    # is the division. Every one maps to GM in MAKE_TO_BRAND.
    "1G1": "Chevrolet", "1G4": "Buick", "1G6": "Cadillac",
    "1G8": "Saturn", "1GA": "Chevrolet", "1GB": "Chevrolet",
    "1GC": "Chevrolet", "1GD": "GMC", "1GK": "GMC",
    "1GN": "Chevrolet", "1GT": "GMC", "1GY": "Cadillac",
    "2G1": "Chevrolet", "2G4": "Buick", "2GC": "Chevrolet",
    "2GK": "GMC", "2GT": "GMC",
    "3G1": "Chevrolet", "3GC": "Chevrolet", "3GT": "GMC",

    # ---- Off-highway / agricultural WMC prefixes (ISO 10261, via AEM). -----
    # A PIN's first three characters identify the machine OEM. Only codes that
    # do NOT collide with an on-highway WMI above are listed (see module note
    # re "1XP"); the J1939 NAME manufacturer code remains the primary lookup.
    # Construction / mining
    "CAT": "Caterpillar",         # Cat 17-char PIN (legacy 8-char SNP not decoded)
    "KMT": "Komatsu",
    "VCE": "Volvo Construction",
    "ROK": "Volvo CE (Rokbak)",
    "HCM": "Hitachi Construction Machinery",
    "HHB": "Hyundai Construction Equipment",
    "JCB": "JCB",
    "GE0": "JCB",
    "LMD": "Liebherr",
    "LME": "Liebherr",
    "ZTN": "Terex",
    "YCG": "Yanmar (Compact)",
    "100": "Dynapac",
    # CNH / Case / New Holland / Kobelco
    "FAB": "CNH Industrial",
    "LMU": "CNH Industrial",
    "HHA": "CNH Industrial",
    "FCE": "New Holland Kobelco",
    "JJA": "Case",
    "ZARH": "Case",
    "HHJ": "CNH Industrial",
    "HHL": "New Holland",
    "ZARN": "New Holland",
    "NEH": "New Holland Construction",
    "FNH": "New Holland Construction",
    # AGCO
    "VFM": "Fendt (AGCO)",
    "AGC": "AGCO",
    "MFG": "Massey Ferguson (AGCO)",
    "AGCV": "Valtra (AGCO)",
    "AGCH": "Challenger (AGCO)",
    # Agriculture / compact
    "KBR": "Kubota",
    "KBT": "Kubota",
    "CAA": "Claas",
    "W90": "Claas",
    "SDF": "Same Deutz-Fahr",
    "WS9": "Same Deutz-Fahr",
    # John Deere — Deere holds many WMC codes; this is a representative set.
    "1RW": "John Deere", "1BZ": "John Deere", "1LV": "John Deere",
    "1L0": "John Deere", "RW6": "John Deere", "1T0": "John Deere",
    "DW2": "John Deere", "17N": "John Deere", "1JD": "John Deere",
    "1AT": "John Deere", "1AZ": "John Deere", "1BE": "John Deere",
    "1BH": "John Deere", "1DE": "John Deere", "1DW": "John Deere",
    "1EJ": "John Deere", "1EK": "John Deere", "1EL": "John Deere",
    "1F9": "John Deere", "1GX": "John Deere", "1H0": "John Deere",
    "1JF": "John Deere", "1JL": "John Deere", "1JZ": "John Deere",
    "1KK": "John Deere", "1KM": "John Deere", "1PC": "John Deere",
    "1PE": "John Deere", "1PF": "John Deere", "1PH": "John Deere",
    "1PY": "John Deere", "1RA": "John Deere", "1UT": "John Deere",
    "1V6": "John Deere", "1WJ": "John Deere", "1WY": "John Deere",
    "1XC": "John Deere", "1XF": "John Deere", "1XG": "John Deere",
    "1XJ": "John Deere", "1XS": "John Deere", "1XU": "John Deere",
    "1Y8": "John Deere", "2DE": "John Deere", "2JD": "John Deere",
    "5JD": "John Deere", "8DE": "John Deere", "8JD": "John Deere",
}

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
    """Vehicle make from the first three VIN characters (the WMI), or None."""
    if len(vin) >= 3:
        return WMI_NAMES.get(vin[:3].upper())
    return None


def _vpic_text(value) -> Optional[str]:
    """Normalise a vPIC field: '' / '0' / 'Not Applicable' mean unknown."""
    text = (value or "").strip() if isinstance(value, str) else value
    if text in ("", "0", "Not Applicable", None):
        return None
    return str(text)


def decode_vin_vpic(vin: str, timeout: float = 8.0) -> Optional[dict]:
    """Full VIN decode via NHTSA's public vPIC API (free government data).

    Returns {make, model, series, year} or None on any failure (offline,
    unknown VIN, rate limit). The WMI table above remains the offline
    fallback. Positions 5-7 (the model/line encoding) are manufacturer-
    specific, so chassis model identification genuinely needs this - or a
    licensed per-maker table, which vPIC replaces at zero cost.
    """
    import json as _json
    from urllib.request import urlopen
    from urllib.error import URLError
    if not vin or len(vin) < 11:
        return None
    try:
        url = ("https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/"
               f"{vin}?format=json")
        with urlopen(url, timeout=timeout) as r:
            data = _json.loads(r.read().decode("utf-8", "ignore"))
        res = (data.get("Results") or [{}])[0]
        out = {
            "make": (res.get("Make") or "").strip() or None,
            "model": (res.get("Model") or "").strip() or None,
            "series": (res.get("Series") or "").strip() or None,
            "year": (res.get("ModelYear") or "").strip() or None,
            # Identity beyond make/model. These are ordinary vPIC fields (free
            # NHTSA data): the engine description is what a mechanic wants, and
            # a VIN alone cannot give it offline - position 8 is a maker-specific
            # engine code, not a standard displacement.
            "trim": _vpic_text(res.get("Trim")),
            "drive_type": _vpic_text(res.get("DriveType")),
            "body_class": _vpic_text(res.get("BodyClass")),
            "plant": _vpic_text(res.get("PlantCity")),
            "displacement_l": _vpic_text(res.get("DisplacementL")),
            "cylinders": _vpic_text(res.get("EngineCylinders")),
            "fuel": _vpic_text(res.get("FuelTypePrimary")),
            "engine_model": _vpic_text(res.get("EngineModel")),
            "engine_info": _vpic_text(res.get("OtherEngineInfo")),
            "error_text": _vpic_text(res.get("ErrorText")),
        }
        return out if any(out.values()) else None
    except (URLError, OSError, ValueError, KeyError):
        return None


def model_year(vin: str) -> Optional[int]:
    """Model year from VIN position 10, or None if it can't be determined.

    Uses the 7th-position rule: numeric position 7 -> 1980-2009 cycle, else
    2010-2039 cycle.
    """
    if len(vin) < 10:
        return None
    code = vin[9].upper()
    if code not in _YEAR_OFFSET:
        return None
    base = 1980 if (len(vin) >= 7 and vin[6].isdigit()) else 2010
    return base + _YEAR_OFFSET[code]
