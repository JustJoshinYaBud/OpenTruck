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

# Fuel system status codes (PID 0x03), J1979 Table 2.
_FUEL_SYSTEM = {
    0: "invalid", 1: "open loop (cold)", 2: "closed loop",
    4: "open loop (load/decels)", 8: "open loop (fault)",
    16: "closed loop (feedback fault)",
}

# Commanded secondary air status (PID 0x12).
_SECONDARY_AIR = {0: "not available", 1: "upstream", 2: "downstream of cat",
                  4: "atmosphere", 8: "off"}


def _fuel_system(a: int, b: int) -> str:
    """'closed loop' or 'closed loop / open loop (cold)' (PID 0x03)."""
    first = _FUEL_SYSTEM.get(a, f"code {a}")
    if b == 0:
        return first
    return f"{first} / {_FUEL_SYSTEM.get(b, f'code {b}')}"


def _signed16(raw: int) -> int:
    """Two's-complement 16-bit value (EVAP pressures are signed)."""
    return raw - 65536 if raw >= 0x8000 else raw


def _o2_trim_pair(name_a: str, name_b: str, a: int, b: int) -> str:
    """Secondary O2 trim text: 'B1 +1.6%, B3 -0.8%' (0xFF = not used)."""
    out = []
    for name, raw in ((name_a, a), (name_b, b)):
        if raw != 0xFF:
            out.append(f"{name} {(raw * 100 / 128) - 100:+.1f}%")
    return ", ".join(out) or "not used"


def _supported_temps(support: int, temps, unit: str = "\u00b0C") -> str:
    """'1: 96 C, 2: 94 C' - a support byte then 1-byte offset-40 readings."""
    out, idx = [], 0
    for n in range(8):
        if support & (1 << n):
            if idx >= len(temps):
                break
            out.append(f"{n + 1}: {temps[idx] + -40} {unit}")
            idx += 1
    return ", ".join(out) or "none"


def _o2_present(bits: int) -> str:
    """'B1S1, B1S2, B2S1' from the PID 0x13 presence bitmap."""
    names = [f"B1S{i + 1}" for i in range(4) if bits & (1 << i)]
    names += [f"B2S{i + 1}" for i in range(4) if bits & (1 << (i + 4))]
    return ", ".join(names) or "none"


def _o2_present_4bank(bits: int) -> str:
    """'B1S1, B1S2, B2S1, B2S2, B3S1...' from the PID 0x1D bitmap.

    Bit 0 is bank 1 sensor 1 and the sequence walks banks before sensors:
    bit 5 is B3S2, bit 6 is B4S1 (per J1979's PID 1D bit table).
    """
    names = [f"B{i // 2 + 1}S{i % 2 + 1}" for i in range(8) if bits & (1 << i)]
    return ", ".join(names) or "none"


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
    0x14: ("O2 sensor voltage (bank 1, sensor 1)", lambda A, B, C, D: (A / 200, "V")),
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
    0x1D: ("O2 sensors present (4 banks)",
           lambda A, B, C, D: (_o2_present_4bank(A), "")),
    # Two fuel-pressure PIDs, deliberately NOT given the same label: the live
    # store is keyed by label, and a vehicle that reports both (diesels with a
    # lift pump and a common rail) would flip-flop between 4 bar and 600 bar.
    # The gas/diesel wording is deliberately gone - "rail" says which sensor
    # without naming a fuel type.
    0x23: ("Fuel rail pressure",
           lambda A, B, C, D: ((A * 256 + B) * 10, "kPa")),
    # EVAP pressures are decoded in kPa (the canonical pressure unit here),
    # NOT the J1979 native Pa: the display layer then converts them like every
    # other pressure (metric kPa, Canadian/US psi). PID 0x32 is SIGNED - using
    # 0x54's formula here produced values
    # like 30176 Pa on a 2013 Ram where the real answer is -648 Pa (a slight
    # EVAP vacuum).
    0x32: ("EVAP system vapor pressure",
           lambda A, B, C, D: (_signed16(A * 256 + B) / 4 / 1000, "kPa")),
    0x34: ("Lambda (wideband, sensor 1)", lambda A, B, C, D: ((A * 256 + B) / 32768, "")),
    # J1979 table B27 orders these sensor-major: 3C/3D are *sensor 1* on bank
    # 1/2 and 3E/3F are *sensor 2* on bank 1/2 (3D/3E were once swapped here).
    #
    # One row per catalyst: a V engine with an exhaust per bank has two cats,
    # and 3C/3D are how the PCM reports them. The labels carry the BANK only -
    # "sensor 1/2" is the PCM's temperature-sensor index, not a position, and
    # saying "sensor 1" next to a downstream sensor only misleads.
    #
    # Expect the two values to be identical on a vehicle that infers the
    # temperature (a 2013 Ram returns the same bytes for both banks): that is
    # the PCM publishing one modelled number for two cats, not the app
    # duplicating a row. Splitting them is still right - it is the vehicle's
    # layout, and a vehicle that does measure per bank shows two values.
    0x3C: ("Catalyst temperature (bank 1)", lambda A, B, C, D: ((A * 256 + B) / 10 - 40, "°C")),
    0x3D: ("Catalyst temperature (bank 2)", lambda A, B, C, D: ((A * 256 + B) / 10 - 40, "°C")),
    0x3E: ("Catalyst temperature 2 (bank 1)", lambda A, B, C, D: ((A * 256 + B) / 10 - 40, "°C")),
    0x3F: ("Catalyst temperature 2 (bank 2)", lambda A, B, C, D: ((A * 256 + B) / 10 - 40, "°C")),

    # --- Wide-range O2 lambda family (0x34-0x3B): sensors 1-8, each 4 bytes:
    # AB = lambda (1/32768), CD = current ((256C+D)/256 - 128 mA, not decoded).
    0x35: ("O2 sensor 2 lambda (wide range)", lambda A, B, C, D: ((A * 256 + B) / 32768, "")),
    0x36: ("O2 sensor 3 lambda (wide range)", lambda A, B, C, D: ((A * 256 + B) / 32768, "")),
    0x37: ("O2 sensor 4 lambda (wide range)", lambda A, B, C, D: ((A * 256 + B) / 32768, "")),
    0x38: ("O2 sensor 5 lambda (wide range)", lambda A, B, C, D: ((A * 256 + B) / 32768, "")),
    0x39: ("O2 sensor 6 lambda (wide range)", lambda A, B, C, D: ((A * 256 + B) / 32768, "")),
    0x3A: ("O2 sensor 7 lambda (wide range)", lambda A, B, C, D: ((A * 256 + B) / 32768, "")),
    0x3B: ("O2 sensor 8 lambda (wide range)", lambda A, B, C, D: ((A * 256 + B) / 32768, "")),

    # --- Remaining standard Mode 01 PIDs --------------------------------
    # Bitfields come out as short text: the live table has one value column
    # and a bare bitmask tells a mechanic nothing.
    0x01: ("Monitor status since DTCs cleared",
           lambda A, B, C, D: (f"MIL {'on' if A & 0x80 else 'off'}, "
                               f"{A & 0x7F} DTC(s)", "")),
    0x03: ("Fuel system status", lambda A, B, C, D: (_fuel_system(A, B), "")),
    0x12: ("Commanded secondary air status",
           lambda A, B, C, D: (_SECONDARY_AIR.get(A, f"code {A}"), "")),
    0x13: ("O2 sensors present", lambda A, B, C, D: (_o2_present(A), "")),
    0x15: ("O2 sensor voltage (bank 1, sensor 2)", lambda A, B, C, D: (A / 200, "V")),
    0x16: ("O2 sensor voltage (bank 1, sensor 3)", lambda A, B, C, D: (A / 200, "V")),
    0x17: ("O2 sensor voltage (bank 1, sensor 4)", lambda A, B, C, D: (A / 200, "V")),
    0x18: ("O2 sensor voltage (bank 2, sensor 1)", lambda A, B, C, D: (A / 200, "V")),
    0x19: ("O2 sensor voltage (bank 2, sensor 2)", lambda A, B, C, D: (A / 200, "V")),
    0x1A: ("O2 sensor voltage (bank 2, sensor 3)", lambda A, B, C, D: (A / 200, "V")),
    0x1B: ("O2 sensor voltage (bank 2, sensor 4)", lambda A, B, C, D: (A / 200, "V")),
    0x1E: ("Auxiliary input status",
           lambda A, B, C, D: ("PTO active" if A & 0x01 else "PTO off", "")),
    0x22: ("Fuel rail pressure (relative to manifold)",
           lambda A, B, C, D: ((A * 256 + B) * 0.079, "kPa")),
    0x24: ("O2 sensor 1 lambda", lambda A, B, C, D: ((A * 256 + B) * 2 / 65536, "")),
    0x25: ("O2 sensor 2 lambda", lambda A, B, C, D: ((A * 256 + B) * 2 / 65536, "")),
    0x26: ("O2 sensor 3 lambda", lambda A, B, C, D: ((A * 256 + B) * 2 / 65536, "")),
    0x27: ("O2 sensor 4 lambda", lambda A, B, C, D: ((A * 256 + B) * 2 / 65536, "")),
    0x28: ("O2 sensor 5 lambda", lambda A, B, C, D: ((A * 256 + B) * 2 / 65536, "")),
    0x29: ("O2 sensor 6 lambda", lambda A, B, C, D: ((A * 256 + B) * 2 / 65536, "")),
    0x2A: ("O2 sensor 7 lambda", lambda A, B, C, D: ((A * 256 + B) * 2 / 65536, "")),
    0x2B: ("O2 sensor 8 lambda", lambda A, B, C, D: ((A * 256 + B) * 2 / 65536, "")),
    0x2C: ("Commanded EGR", lambda A, B, C, D: (A * 100 / 255, "%")),
    0x2D: ("EGR error", lambda A, B, C, D: ((A - 128) * 100 / 128, "%")),
    0x2E: ("Commanded evaporative purge", lambda A, B, C, D: (A * 100 / 255, "%")),
    0x41: ("Monitor status this drive cycle",
           lambda A, B, C, D: (f"{A & 0x7F} DTC(s)", "")),
    0x48: ("Absolute throttle position C", lambda A, B, C, D: (A * 100 / 255, "%")),
    0x4B: ("Accelerator pedal position F", lambda A, B, C, D: (A * 100 / 255, "%")),
    0x52: ("Ethanol fuel %", lambda A, B, C, D: (A * 100 / 255, "%")),
    0x53: ("Absolute EVAP vapor pressure",
           lambda A, B, C, D: ((A * 256 + B) / 200, "kPa")),
    0x54: ("EVAP vapor pressure",
           lambda A, B, C, D: (((A * 256 + B) - 32768) / 1000, "kPa")),

    # --- Later J1979 PIDs (0x4F-0xA6). Multi-byte/bitrfield blocks whose
    # layouts are NOT publicly formulable (0x65, 0x69-0x77, 0x7A/0x7B/0x7D/
    # 0x7E, 0x8F, 0x90-0x9A, 0x9D-0x9F, 0xA1, 0xA3-0xA5, 0xA7/0xA8) are
    # deliberately left out until their SAE J1979-DA layouts are verified.
    0x4F: ("Maximum values",
           lambda A, B, C, D: (f"lambda {A}, O2 {B} V, I {C} mA, "
                               f"MAP {D * 10} kPa", "")),
    0x50: ("Maximum MAF", lambda A, B, C, D: (A * 10, "g/s")),
    0x55: ("Secondary O2 trim (short term, banks 1/3)",
           lambda A, B, C, D: (_o2_trim_pair("B1", "B3", A, B), "")),
    0x56: ("Secondary O2 trim (long term, banks 1/3)",
           lambda A, B, C, D: (_o2_trim_pair("B1", "B3", A, B), "")),
    0x57: ("Secondary O2 trim (short term, banks 2/4)",
           lambda A, B, C, D: (_o2_trim_pair("B2", "B4", A, B), "")),
    0x58: ("Secondary O2 trim (long term, banks 2/4)",
           lambda A, B, C, D: (_o2_trim_pair("B2", "B4", A, B), "")),
    0x61: ("Demanded engine torque", lambda A, B, C, D: (A - 125, "%")),
    0x67: ("Engine coolant temperature (sensors 2/3)",
           lambda A, B, C, D: (_supported_temps(A, (B, C)), "")),
    0x68: ("Intake air temperature (sensors 2/3)",
           lambda A, B, C, D: (_supported_temps(A, (B, C)), "")),
    0x8D: ("Throttle position G", lambda A, B, C, D: (A * 100 / 255, "%")),
    0x8E: ("Engine friction torque", lambda A, B, C, D: (A - 125, "%")),
    0x9B: ("Diesel exhaust fluid level", lambda A, B, C, D: (D * 100 / 255, "%")),
    0xA2: ("Cylinder fuel rate", lambda A, B, C, D: ((A * 256 + B) / 32, "mg/stroke")),
    0xA6: ("Odometer",
           lambda A, B, C, D: ((A * 2 ** 24 + B * 2 ** 16 + C * 2 ** 8 + D) / 10, "km")),

    # Variable-length blocks: decoded by special cases in decode_pid (the
    # lambda below is never called; the entry exists so the PID is known).
    0x64: ("Engine percent torque data", lambda A, B, C, D: None),
    0x66: ("Mass air flow (sensors B-E)", lambda A, B, C, D: None),
    0x78: ("Exhaust gas temperature (bank 1)", lambda A, B, C, D: None),
    0x79: ("Exhaust gas temperature (bank 2)", lambda A, B, C, D: None),
    0x7F: ("Engine run time (extended)", lambda A, B, C, D: None),
    0x59: ("Fuel rail absolute pressure",
           lambda A, B, C, D: ((A * 256 + B) * 10, "kPa")),
    0x5B: ("Hybrid battery remaining life", lambda A, B, C, D: (A * 100 / 255, "%")),
    0x5D: ("Fuel injection timing",
           lambda A, B, C, D: ((A * 256 + B) / 128 - 210, "°")),
    0x5F: ("Emission requirements",
           lambda A, B, C, D: (OBD_STANDARDS.get(A, f"code {A}"), "")),
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
    # Variable-length / long blocks that the (A,B,C,D) lambda signature cannot
    # carry. Each is verified against the J1979 layout documented in
    # check_pids.py; the placeholder lambda in PIDS is never called.
    if pid == 0x64:   # engine percent torque: idle + 4 points, each -125
        names = ("idle", "pt1", "pt2", "pt3", "pt4")
        return (label, ", ".join(f"{n} {b - 125}%"
                                 for n, b in zip(names, data[:5])), "")
    if pid == 0x66:   # MAF sensors B-E: support bits, then 16-bit /32 g/s
        support, out, i = data[0], [], 1
        for n in range(4):
            if support & (1 << n):
                if len(data) < i + 2:
                    break
                out.append(f"{chr(66 + n)} {(data[i] * 256 + data[i + 1]) / 32:.1f} g/s")
                i += 2
        return (label, ", ".join(out) or "none", "")
    if pid in (0x78, 0x79):   # EGT bank: support bits, then 2-byte /10-40 C
        support, out, i = data[0], [], 1
        for n in range(8):
            if support & (1 << n):
                if len(data) < i + 2:
                    break
                out.append(f"EGT{n + 1} {(data[i] * 256 + data[i + 1]) / 10 - 40:.0f} C")
                i += 2
        return (label, ", ".join(out) or "no sensors", "")
    if pid == 0x7F:   # extended run time: layout byte, then 32-bit seconds
        if len(data) < 5:
            return None
        return (label, f"{int.from_bytes(data[1:5], 'big')} s", "")
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