"""OpenTruck - SAE J1979 OBD-II PID definitions (light-duty diagnostic bus).

Standard, publicly documented Mode 01 parameter IDs. Values are computed from
the raw payload bytes A, B, C, D (per J1979) and returned in CANONICAL METRIC
units so the shared ``units.convert`` display layer applies, exactly like the
J1939/J1587 decoders.

Only the standard (SAE-assigned) PIDs live here; maker-specific PIDs are out
of scope for the generic layer.
"""
from __future__ import annotations

from typing import Callable, Optional, Tuple

# PID -> (label, formula(A,B,C,D) -> (value, unit) or None for N/A)
PIDS: dict[int, Tuple[str, Callable[[int, int, int, int], Optional[Tuple[float, str]]]]] = {
    0x04: ("Calculated engine load", lambda A, B, C, D: (A * 100 / 255, "%")),
    0x05: ("Coolant temperature", lambda A, B, C, D: (A - 40, "°C")),
    0x06: ("Short-term fuel trim (bank 1)", lambda A, B, C, D: ((A - 128) * 100 / 128, "%")),
    0x07: ("Long-term fuel trim (bank 1)", lambda A, B, C, D: ((A - 128) * 100 / 128, "%")),
    0x08: ("Short-term fuel trim (bank 2)", lambda A, B, C, D: ((A - 128) * 100 / 128, "%")),
    0x09: ("Long-term fuel trim (bank 2)", lambda A, B, C, D: ((A - 128) * 100 / 128, "%")),
    0x0A: ("Fuel pressure", lambda A, B, C, D: (A * 3, "kPa")),
    0x0B: ("Intake manifold absolute pressure", lambda A, B, C, D: (A, "kPa")),
    0x0C: ("Engine speed", lambda A, B, C, D: ((A * 256 + B) / 4, "RPM")),
    0x0D: ("Vehicle speed", lambda A, B, C, D: (A, "km/h")),
    0x0E: ("Timing advance", lambda A, B, C, D: (A / 2 - 64, "°")),
    0x0F: ("Intake air temperature", lambda A, B, C, D: (A - 40, "°C")),
    0x10: ("Mass air flow", lambda A, B, C, D: ((A * 256 + B) / 100, "g/s")),
    0x11: ("Throttle position", lambda A, B, C, D: (A * 100 / 255, "%")),
    0x14: ("O2 sensor 1 voltage", lambda A, B, C, D: (A / 200, "V")),
    0x1F: ("Run time since engine start", lambda A, B, C, D: (A * 256 + B, "s")),
    0x21: ("Distance with MIL on", lambda A, B, C, D: (A * 256 + B, "km")),
    0x2F: ("Fuel tank level", lambda A, B, C, D: (A * 100 / 255, "%")),
    0x30: ("Warm-ups since codes cleared", lambda A, B, C, D: (A, "")),
    0x31: ("Distance since codes cleared", lambda A, B, C, D: (A * 256 + B, "km")),
    0x33: ("Barometric pressure", lambda A, B, C, D: (A, "kPa")),
    0x42: ("Control module voltage", lambda A, B, C, D: ((A * 256 + B) / 1000, "V")),
    0x43: ("Absolute load value", lambda A, B, C, D: ((A * 256 + B) * 100 / 255, "%")),
    0x44: ("Equivalence ratio (commanded)", lambda A, B, C, D: ((A * 256 + B) / 32768, "")),
    0x45: ("Relative throttle position", lambda A, B, C, D: (A * 100 / 255, "%")),
    0x46: ("Ambient air temperature", lambda A, B, C, D: (A - 40, "°C")),
    0x47: ("Absolute throttle position B", lambda A, B, C, D: (A * 100 / 255, "%")),
    0x49: ("Accelerator pedal position D", lambda A, B, C, D: (A * 100 / 255, "%")),
    0x4A: ("Accelerator pedal position E", lambda A, B, C, D: (A * 100 / 255, "%")),
    0x4C: ("Commanded throttle actuator", lambda A, B, C, D: (A * 100 / 255, "%")),
    0x4D: ("Time run with MIL on", lambda A, B, C, D: (A * 256 + B, "min")),
    0x4E: ("Time since codes cleared", lambda A, B, C, D: (A * 256 + B, "min")),
    0x51: ("Fuel type", lambda A, B, C, D: (A, "")),
    0x5A: ("Relative accelerator pedal position", lambda A, B, C, D: (A * 100 / 255, "%")),
    0x5C: ("Engine oil temperature", lambda A, B, C, D: (A - 40, "°C")),
    0x5E: ("Engine fuel rate", lambda A, B, C, D: ((A * 256 + B) / 20, "L/h")),
    0x62: ("Actual engine torque", lambda A, B, C, D: (A - 125, "%")),
    0x63: ("Engine reference torque", lambda A, B, C, D: (A * 256 + B, "N·m")),
    0x1C: ("OBD standard", lambda A, B, C, D: (None, "")),   # text via OBD_STANDARDS
    0x1D: ("ECU sensors present", lambda A, B, C, D: (A, "")),
    0x23: ("Fuel rail pressure (diesel)", lambda A, B, C, D: ((A * 256 + B) * 10, "kPa")),
    0x32: ("EVAP system vapor pressure", lambda A, B, C, D: ((A * 256 + B) - 32768, "Pa")),
    0x34: ("Lambda (wideband, sensor 1)", lambda A, B, C, D: ((A * 256 + B) / 32768, "")),
    0x3C: ("Catalyst temperature (bank 1, sensor 1)", lambda A, B, C, D: ((A * 256 + B) / 10 - 40, "°C")),
    0x3D: ("Catalyst temperature (bank 1, sensor 2)", lambda A, B, C, D: ((A * 256 + B) / 10 - 40, "°C")),
    0x3E: ("Catalyst temperature (bank 2, sensor 1)", lambda A, B, C, D: ((A * 256 + B) / 10 - 40, "°C")),
    0x3F: ("Catalyst temperature (bank 2, sensor 2)", lambda A, B, C, D: ((A * 256 + B) / 10 - 40, "°C")),
}

# PID 0x1C "OBD standards the vehicle conforms to" (J1979 Table 2).
OBD_STANDARDS = {
    0: "OBD-II (CARB)", 1: "OBD-II (EPA)", 2: "OBD-II and OBD",
    3: "OBD-I", 4: "Not OBD compliant", 5: "EOBD (Europe)",
    6: "EOBD and OBD-II", 7: "EOBD and OBD", 8: "EOBD, OBD and OBD-II",
    9: "JOBD (Japan)", 0x0A: "JOBD and OBD-II", 0x0B: "JOBD and EOBD",
    0x0C: "JOBD, EOBD and OBD-II", 0x11: "Heavy-duty OBD (EU HD OBD)",
    0x12: "Heavy-duty OBD (US HD OBD)", 0x13: "Heavy-duty OBD (HD EOBD-1)",
}

# Human names for the well-known fuel-type codes (PID 0x51).
FUEL_TYPES = {
    0: "Not available", 1: "Gasoline", 2: "Methanol", 3: "Ethanol",
    4: "Diesel", 5: "LPG", 6: "CNG", 7: "Propane", 8: "Electric",
    9: "Bifuel (gas + electric)", 0x0A: "Bifuel (methanol + gas)",
    0x0B: "Bifuel (ethanol + gas)", 0x0C: "Bifuel (LPG + gas)",
    0x0D: "Bifuel (CNG + gas)", 0x0E: "Bifuel (propane + gas)",
}


def decode_pid(pid: int, data: bytes) -> Optional[Tuple[str, object, str]]:
    """Decode one Mode 01 response payload (bytes after ``41 <pid>``).

    Returns ``(label, value, unit)`` or None when the PID is unknown / the
    data is not-available.
    """
    entry = PIDS.get(pid)
    if entry is None or len(data) < 1:
        return None
    label, fn = entry
    A, B, C, D = (data + b"\x00\x00\x00")[:4]
    try:
        result = fn(A, B, C, D)
    except Exception:
        return None
    if result is None:
        return None
    value, unit = result
    if pid == 0x51:   # fuel type: show the name instead of the raw code
        return (label, FUEL_TYPES.get(A, f"code {A}"), "")
    if pid == 0x1C:   # OBD standard: show the conformance name
        return (label, OBD_STANDARDS.get(A, f"code {A}"), "")
    if value is None:
        return None
    return (label, value, unit)