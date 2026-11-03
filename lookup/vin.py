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
