"""OpenTruck - on-the-fly unit conversion for live-data display.

``livedata.py`` emits canonical SI/metric ``(value, unit)`` triplets (kPa,
°C, N·m, km/h, L, L/h, kg/h, kg). This module converts those values to the
user's chosen unit system at *display* time, leaving the canonical decoding
(and the CSV/report source of truth) unchanged.

Systems (mirrors the Preferences radio options):

  metric    - SI, unchanged:            kPa, °C, N·m, km/h, L, L/h, kg/h, kg
  standard  - US customary / imperial:  psi, °F, ft·lb, mph, gal, gal/h, lb/h, lb
  canadian  - metric everywhere except  torque (ft·lb) and pressure (psi)

The conversion is a pure function: ``convert(value, unit, system) ->
(value, unit)``. Non-numeric values and unitless / unrecognised units pass
through unchanged (RPM, %, V, h, rev, and status words like "Active").
"""
from __future__ import annotations

from typing import Tuple


def _fmt(v: float, decimals: int) -> str:
    """Format a converted value, trimming trailing zeros / the decimal point."""
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    s = f"{v:.{decimals}f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


# Canonical unit string -> (scale, offset, target unit, decimals). Matching is
# an exact string compare against the unit emitted by livedata.py's decoders.
# Temperature uses the degree sign (U+00B0) as its canonical unit.
_CONVERSIONS: dict[str, Tuple[float, float, str, int]] = {
    "kPa":        (0.1450377, 0.0, "psi", 1),          # pressure
    "\u00b0C":    (9 / 5, 32.0, "\u00b0F", 1),         # temperature
    "Nm":         (0.737562, 0.0, "ft\u00b7lb", 1),    # torque
    "L/h":        (0.264172, 0.0, "gal/h", 2),         # volumetric flow
    "L":          (0.264172, 0.0, "gal", 2),           # volume
    "km/h":       (0.621371, 0.0, "mph", 1),           # speed
    "km":         (0.621371, 0.0, "mi", 1),            # distance
    "kg/h":       (2.20462, 0.0, "lb/h", 1),           # mass flow
    "kg":         (2.20462, 0.0, "lb", 0),             # mass / weight
    "kW":         (1.34102, 0.0, "hp", 1),             # power
}

# Units the (hybrid) Canadian system converts, on top of its metric baseline.
_CANADIAN_CONVERTS = ("kPa", "Nm", "kW")


def convert(value: str, unit: str, system: str) -> Tuple[str, str]:
    """Convert a single live-data value for the requested unit system.

    ``system`` is one of ``"metric"``, ``"standard"`` or ``"canadian"``.
    Returns ``(value, unit)``; the value string is reformatted for the target
    unit, or returned untouched when no conversion applies.
    """
    # Fuel economy is inverse-scaled (L/100km <-> mpg), so handle it explicitly:
    # metric/Canadian keep L/100km; US standard switches to mpg.
    if unit == "L/100km":
        if system != "standard":
            return value, unit
        try:
            v = float(value)
        except (TypeError, ValueError):
            return value, unit
        if v <= 0:
            return value, unit
        return _fmt(235.215 / v, 1), "mpg"
    if unit not in _CONVERSIONS:
        return value, unit
    if system == "metric":
        return value, unit
    if system == "canadian" and unit not in _CANADIAN_CONVERTS:
        return value, unit

    try:
        v = float(value)
    except (ValueError, TypeError):
        return value, unit

    scale, offset, target, decimals = _CONVERSIONS[unit]
    return _fmt(v * scale + offset, decimals), target
