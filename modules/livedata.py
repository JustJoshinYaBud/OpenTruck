"""OpenTruck - live J1939 parameter decoding (SAE J1939-71).

Turns live broadcast PGNs into human-readable ``(name, value, unit)`` triples.
Byte offsets, scaling factors and offsets below follow the published SAE
J1939-71 standard and public vendor documentation.

LAYOUT IS DATA-DRIVEN: the simple scalar fields live in ``PGN_FIELDS`` (one
table row per parameter - add a PGN by adding a few rows; no glue code).
PGNs that need bit/status/conditional logic (gears, status lamps, wheel-speed
math, DPF regen states, length checks) have a dedicated handler in ``_SPECIAL``
and are kept there because a fixed field list cannot express them. ``decode_live``
returns ``[]`` for anything it doesn't understand.

J1939 encodes "error" as 0xFE and "not available" as 0xFF (all-ones for the
field width); ``_u8``/``_i16`` return ``None`` for those so we skip them rather
than printing nonsense like 32739 kPa.
"""
from __future__ import annotations

from typing import Callable, Optional


def _u8(d: bytes, i: int) -> Optional[int]:
    """One-byte field, or None when it encodes error/not-available."""
    v = d[i]
    return None if v >= 0xFE else v


def _i16(d: bytes, i: int) -> Optional[int]:
    """Two-byte little-endian field, or None when the high byte is 0xFE/0xFF."""
    v = int.from_bytes(d[i:i + 2], "little")
    return None if (v >> 8) >= 0xFE else v


def _i32(d: bytes, i: int) -> Optional[int]:
    """Four-byte little-endian field, or None when the top byte is 0xFE/0xFF."""
    v = int.from_bytes(d[i:i + 4], "little")
    return None if (v >> 24) >= 0xFE else v


def _add(out: list, name: str, raw: Optional[int], scale: Optional[float] = 1.0,
         offset: float = 0.0, fmt: str = "{:.0f}", unit: str = "") -> None:
    """Append ``(name, value, unit)`` if the raw value is present.

    ``scale`` is optional: a ``None`` scale means "show the raw value" (a
    defensive fallback so a mis-scaled call site can never crash the live
    decoder - it would take down the whole GUI refresh loop).
    """
    if raw is not None:
        out.append((name, fmt.format(raw * (scale if scale is not None else 1.0) + offset), unit))


def _gear_name(v: int) -> str:
    """Name a gear byte (J1939 SPN 523/524 encoding)."""
    v &= 0xFF
    if v >= 0xFE:
        return "N/A"
    if v == 0xFB:
        return "Park"
    if v == 0x7C:
        return "Reverse"
    if v == 0x7D:
        return "Neutral"
    if 0x7E <= v <= 0x83:
        return f"Gear {v - 0x7D}"
    return f"({v})"


def _add_status(out: list, name: str, raw2: int, off: str = "Off",
                on: str = "On") -> None:
    """Append a 2-bit J1939 status field as a human word.

    J1939-71 encodes 2-bit status/lamp fields as 00=off, 01=on, 10=reserved,
    11=not-available. `off`/`on` let the caller use clearer labels for the
    signal (e.g. "Passive"/"Active" for ABS).
    """
    txt = {0: off, 1: on, 2: "Reserved", 3: "Not available"}.get(raw2 & 0x3, "?")
    out.append((name, txt, ""))


# =============================================================================
# Data-driven scalar field table
# =============================================================================
class _F:
    """One scalar live-data field: how to pull ``name = raw*scale+offset`` from
    a PGN payload. ``acc`` is "u8"/"i16"/"i32". Returns ``(name, value, unit)``
    or ``None`` when the field is absent/error. Adding a PGN is just adding rows."""
    __slots__ = ("name", "acc", "off", "scale", "offset", "fmt", "unit")

    def __init__(self, name: str, acc: str, off: int, scale: float = 1.0,
                 offset: float = 0.0, fmt: str = "{:.0f}", unit: str = ""):
        self.name = name
        self.acc = acc
        self.off = off
        self.scale = scale
        self.offset = offset
        self.fmt = fmt
        self.unit = unit

    def raw(self, data: bytes) -> Optional[int]:
        # Bounds-checked like the old per-PGN ``len(data) >= N`` guards: a short
        # CAN frame (DLC < 8) or a short transport-protocol payload must decode
        # to "nothing", never raise IndexError into the GUI refresh loop.
        width = {"u8": 1, "i16": 2, "i32": 4}.get(self.acc)
        if width is None or self.off + width > len(data):
            return None
        if self.acc == "u8":
            return _u8(data, self.off)
        if self.acc == "i16":
            return _i16(data, self.off)
        return _i32(data, self.off)

    def __call__(self, data: bytes) -> Optional[tuple[str, str, str]]:
        r = self.raw(data)
        if r is None:
            return None
        return (self.name, self.fmt.format(r * self.scale + self.offset), self.unit)


# PGN -> list of scalar fields. Extend this table to add standard live data
# without touching any glue code. Keep bit/status/conditional PGNs in _SPECIAL.
PGN_FIELDS: dict[int, list[_F]] = {
    # EEC1 (61444) engine
    0xF004: [
        _F("Engine Speed", "i16", 3, 0.125, 0, "{:.0f}", "RPM"),
        _F("Driver Demand Torque", "u8", 1, 1.0, -125, "{:.0f}", "%"),
        _F("Actual Engine Torque", "u8", 2, 1.0, -125, "{:.0f}", "%"),
    ],
    # EEC2 (61443) engine
    0xF003: [
        _F("Accelerator Pedal Position", "u8", 1, 0.4, 0, "{:.1f}", "%"),
        _F("Percent Load At Current Speed", "u8", 2, 1.0, 0, "{:.0f}", "%"),
    ],
    # ETC1 (61442) transmission
    0xF002: [
        _F("Transmission Output Shaft Speed", "i16", 1, 0.125, 0, "{:.0f}", "RPM"),
        _F("Transmission Input Shaft Speed", "i16", 5, 0.125, 0, "{:.0f}", "RPM"),
        _F("Percent Clutch Slip", "u8", 3, 0.4, 0, "{:.1f}", "%"),
    ],
    # ET1 (65262) temperatures
    0xFEEE: [
        _F("Engine Coolant Temp", "u8", 0, 1.0, -40, "{:.0f}", "\u00b0C"),
        _F("Engine Fuel Temp", "u8", 1, 1.0, -40, "{:.0f}", "\u00b0C"),
        _F("Engine Oil Temp", "i16", 2, 0.03125, -273, "{:.1f}", "\u00b0C"),
    ],
    # EFL/P1 (65263) fluids
    0xFEEF: [
        _F("Engine Oil Pressure", "u8", 3, 4.0, 0, "{:.0f}", "kPa"),
        _F("Fuel Delivery Pressure", "u8", 0, 4.0, 0, "{:.0f}", "kPa"),
    ],
    # LFE (65266) fuel economy
    0xFEF2: [
        _F("Engine Fuel Rate", "i16", 0, 0.05, 0, "{:.2f}", "L/h"),
        _F("Throttle Position", "u8", 5, 0.4, 0, "{:.1f}", "%"),
    ],
    # TF (65272) transmission fluids
    0xFEF8: [
        _F("Transmission Oil Temperature", "i16", 4, 0.03125, -273, "{:.1f}", "\u00b0C"),
    ],
    # AMB (65269) ambient
    0xFEF5: [
        _F("Barometric Pressure", "u8", 0, 0.5, 0, "{:.0f}", "kPa"),
        _F("Ambient Air Temperature", "i16", 3, 0.03125, -273, "{:.1f}", "\u00b0C"),
    ],
    # TCI (65178) turbocharger 1 compressor inlet temp
    0xFE9A: [
        _F("Turbocharger 1 Compressor Inlet Temp", "i16", 0, 0.03125, -273,
           "{:.1f}", "\u00b0C"),
    ],
    # LFC (65257) fuel consumption
    0xFEE9: [
        _F("Trip Fuel", "i32", 0, 0.5, 0, "{:.0f}", "L"),
        _F("Total Fuel Used", "i32", 4, 0.5, 0, "{:.0f}", "L"),
    ],
    # VEP1 (65271) electrical
    0xFEF7: [
        _F("Battery Voltage", "i16", 4, 0.05, 0, "{:.2f}", "V"),
        _F("Charging System Voltage", "i16", 6, 0.05, 0, "{:.2f}", "V"),
    ],
    # DD (65276) dash display / fuel level
    0xFEFC: [_F("Fuel Level", "u8", 1, 0.4, 0, "{:.0f}", "%")],
    # EEC3 (65247) engine control 3
    0xFEDF: [
        _F("Desired Operating Speed", "i16", 1, 0.125, 0, "{:.0f}", "RPM"),
        _F("Exhaust Gas Mass Flow", "i16", 5, 0.2, 0, "{:.1f}", "kg/h"),
    ],
    # ERC1 (61442) retarder / engine brake
    0xF000: [
        _F("Actual Retarder Torque", "u8", 1, 1.0, -125, "{:.0f}", "%"),
        _F("Intended Retarder Torque", "u8", 2, 1.0, -125, "{:.0f}", "%"),
        _F("Retarder Driver Demand", "u8", 5, 1.0, -125, "{:.0f}", "%"),
    ],
    # EGF1 (61450) gas flow
    0xF00A: [
        _F("EGR 1 Mass Flow", "i16", 0, 0.05, 0, "{:.1f}", "kg/h"),
        _F("Intake Air Mass Flow", "i16", 2, 0.05, 0, "{:.1f}", "kg/h"),
        _F("EGR 2 Mass Flow", "i16", 4, 0.05, 0, "{:.1f}", "kg/h"),
    ],
    # PTO (65264) power takeoff
    0xFEF0: [
        _F("PTO Oil Temp", "u8", 0, 1.0, -40, "{:.0f}", "\u00b0C"),
        _F("PTO Speed", "i16", 1, 0.125, 0, "{:.0f}", "RPM"),
        _F("PTO Set Speed", "i16", 3, 0.125, 0, "{:.0f}", "RPM"),
    ],
    # Air Supply (65262) air pressures
    0xFEAE: [
        _F("Pneumatic Supply Pressure", "u8", 0, 8.0, 0, "{:.0f}", "kPa"),
        _F("Parking/Trailer Air Pressure", "u8", 1, 8.0, 0, "{:.0f}", "kPa"),
        _F("Service Brake 1 Air Pressure", "u8", 2, 8.0, 0, "{:.0f}", "kPa"),
        _F("Service Brake 2 Air Pressure", "u8", 3, 8.0, 0, "{:.0f}", "kPa"),
        _F("Air Suspension Pressure", "u8", 5, 8.0, 0, "{:.0f}", "kPa"),
    ],
    # Vehicle Hours (65255)
    0xFEE7: [
        _F("Total Vehicle Hours", "i32", 0, 0.05, 0, "{:.1f}", "h"),
        _F("Total PTO Hours", "i32", 4, 0.05, 0, "{:.1f}", "h"),
    ],
    # Engine Hours (65253)
    0xFEE5: [
        _F("Total Engine Hours", "i32", 0, 0.05, 0, "{:.1f}", "h"),
        _F("Total Engine Revolutions", "i32", 4, 1000.0, 0, "{:.0f}", "rev"),
    ],
    # High-Resolution Vehicle Distance (65217)
    0xFEC1: [
        _F("Total Vehicle Distance", "i32", 0, 0.005, 0, "{:.1f}", "km"),
        _F("Trip Distance", "i32", 4, 0.005, 0, "{:.1f}", "km"),
    ],
    # Idle Operation (65244)
    0xFEDC: [
        _F("Total Idle Fuel Used", "i32", 0, 0.5, 0, "{:.1f}", "L"),
        _F("Total Idle Hours", "i32", 4, 0.05, 0, "{:.1f}", "h"),
    ],
    # Retarder Configuration (65249)
    0xFEE1: [
        _F("Reference Retarder Torque", "i16", 16, 1.0, 0, "{:.0f}", "Nm"),
    ],
    # Engine Configuration 1 (65251)
    0xFEE3: [
        _F("Engine Idle Speed", "i16", 0, 0.125, 0, "{:.0f}", "RPM"),
        _F("Engine Reference Torque", "i16", 19, 1.0, 0, "{:.0f}", "Nm"),
    ],
    # Aftertreatment 1 Trip Information (65209? AT1TI)
    0xFD79: [
        _F("DPF Trip Fuel Used", "i32", 0, 0.5, 0, "{:.1f}", "L"),
        _F("Active Regen Time", "i32", 4, 1 / 3600.0, 0, "{:.1f}", "h"),
        _F("Active Regens (trip)", "i32", 12, 1.0, 0, "{:.0f}", ""),
        _F("Passive Regens (trip)", "i32", 20, 1.0, 0, "{:.0f}", ""),
    ],
    # Aftertreatment 1 DEF Tank Info (65110)
    0xFE56: [
        _F("DEF Tank Level", "u8", 1, 0.4, 0, "{:.1f}%", ""),
        _F("DEF Temperature", "i16", 2, 0.03125, -40, "{:.1f}", "\u00b0C"),
    ],
    # Aftertreatment 1 DOC (64672)
    0xFD20: [
        _F("DOC Inlet Temp", "i16", 0, 0.03125, -273, "{:.0f}", "\u00b0C"),
        _F("DOC Outlet Temp", "i16", 2, 0.03125, -273, "{:.0f}", "\u00b0C"),
        _F("DOC Diff Pressure", "i16", 4, 0.1, 0, "{:.1f}", "kPa"),
    ],
    # Aftertreatment 1 Fuel Control 2 (64741)
    0xFD65: [
        _F("AFT Fuel Pressure 2", "i16", 0, 0.1, 0, "{:.1f}", "kPa"),
        _F("HC Doser Intake Temp", "u8", 5, 1.0, -40, "{:.0f}", "\u00b0C"),
    ],
    # Aftertreatment 1 Service / DPF load (64763)
    0xFD7B: [
        _F("DPF Soot Load", "u8", 0, 1.0, 0, "{:.0f}", "%"),
        _F("DPF Ash Load", "u8", 1, 1.0, 0, "{:.0f}", "%"),
    ],
    # Aftertreatment 1 Intake Gas (64948)
    0xFDB4: [
        _F("Exhaust Gas Temperature 1", "i16", 0, 0.03125, -273, "{:.0f}", "\u00b0C"),
        _F("DPF Intake Gas Temperature", "i16", 2, 0.03125, -273, "{:.0f}", "\u00b0C"),
    ],
    # Aftertreatment 1 Outlet Gas (64947)
    0xFDB3: [
        _F("Exhaust Gas Temperature 3", "i16", 0, 0.03125, -273, "{:.0f}", "\u00b0C"),
        _F("DPF Outlet Gas Temperature", "i16", 2, 0.03125, -273, "{:.0f}", "\u00b0C"),
    ],
    # Aftertreatment 1 DPF Pressure (64908)
    0xFD8C: [
        _F("DPF Intake Pressure", "i16", 0, 0.1, 0, "{:.1f}", "kPa"),
        _F("DPF Outlet Pressure", "i16", 2, 0.1, 0, "{:.1f}", "kPa"),
    ],
    # Tachograph (TCO1) - wheel/engine speed.
    0xFE6C: [
        _F("Vehicle Speed (Tachograph)", "i16", 0, 1 / 256.0, 0, "{:.1f}", "km/h"),
        _F("Engine Speed (Tachograph)", "i16", 2, 0.125, 0, "{:.0f}", "RPM"),
    ],
    # ETC8 (61452) transmission: torque-converter ratio + clutch/converter
    # input speed (J1939-71: bytes 1-2 SPN 3030, bytes 3-4 SPN 5052).
    0xF00C: [
        _F("Torque Converter Ratio", "i16", 0, 0.001, 0, "{:.3f}", ""),
        _F("Clutch/Converter Input Speed", "i16", 2, 0.125, 0, "{:.0f}", "RPM"),
    ],
    # AT1AC1 (64927) aftertreatment 1 air control (J1939-71: 16-bit air
    # pressures, 0.1 kPa/bit).
    0xFD9F: [
        _F("AFT Supply Air Pressure", "i16", 0, 0.1, 0, "{:.1f}", "kPa"),
        _F("AFT Purge Air Pressure", "i16", 2, 0.1, 0, "{:.1f}", "kPa"),
        _F("AFT Air Pressure Control", "i16", 4, 0.1, 0, "{:.1f}", "kPa"),
    ],
    # AT2IMG (64943) aftertreatment 2 intermediate gas (bank 2).
    0xFDAF: [
        _F("Exhaust Gas Temperature 2 (bank 2)", "i16", 0, 0.03125, -273,
           "{:.0f}", "\u00b0C"),
        _F("DPF Intermediate Gas Temperature (bank 2)", "i16", 2, 0.03125,
           -273, "{:.0f}", "\u00b0C"),
        _F("DPF Differential Pressure (bank 2)", "i16", 4, 0.1, 0,
           "{:.1f}", "kPa"),
    ],
    # AT2OG2 (64944) aftertreatment 2 outlet gas (bank 2).
    0xFDB0: [
        _F("Exhaust Gas Temperature 3 (bank 2)", "i16", 0, 0.03125, -273,
           "{:.0f}", "\u00b0C"),
        _F("DPF Outlet Gas Temperature (bank 2)", "i16", 2, 0.03125, -273,
           "{:.0f}", "\u00b0C"),
    ],
    # ACC1 (65135) adaptive cruise: forward-vehicle + set speeds (1 km/h/bit;
    # SPN 1587 distance scale is not verified, so that field is not decoded).
    0xFE6F: [
        _F("Speed of Forward Vehicle", "u8", 0, 1.0, 0, "{:.0f}", "km/h"),
        _F("Adaptive Cruise Set Speed", "u8", 2, 1.0, 0, "{:.0f}", "km/h"),
    ],
    # FD (65213) fan drive.
    0xFEBD: [
        _F("Estimated Fan Speed", "u8", 0, 0.4, 0, "{:.0f}", "%"),
        _F("Fan Speed", "i16", 2, 0.125, 0, "{:.0f}", "RPM"),
    ],
    # TFAC (61466) engine throttle / fuel actuator control command
    # (J1939-71: bytes 1-2 SPN 3464, 3-4 SPN 3465, 5-6 SPN 633, 7-8 SPN 1244;
    # actuator command SLOT 0.0025 %/bit).
    0xF01A: [
        _F("Throttle Actuator 1 Command", "i16", 0, 0.0025, 0, "{:.1f}", "%"),
        _F("Throttle Actuator 2 Command", "i16", 2, 0.0025, 0, "{:.1f}", "%"),
        _F("Fuel Actuator 1 Command", "i16", 4, 0.0025, 0, "{:.1f}", "%"),
        _F("Fuel Actuator 2 Command", "i16", 6, 0.0025, 0, "{:.1f}", "%"),
    ],
    # IC2 (64976) inlet/exhaust conditions 2: air filter 2/3/4 differential
    # pressures (J1939-71: SPN 2809/2810/2811, same 0.05 kPa/bit SLOT as IC1).
    0xFDD0: [
        _F("Air Filter 2 Differential Pressure", "u8", 0, 0.05, 0, "{:.1f}", "kPa"),
        _F("Air Filter 3 Differential Pressure", "u8", 1, 0.05, 0, "{:.1f}", "kPa"),
        _F("Air Filter 4 Differential Pressure", "u8", 2, 0.05, 0, "{:.1f}", "kPa"),
    ],
    # ET3 (65129) engine temperature 3 - high-resolution temps, all 2-byte
    # 0.03125 C/bit, -273 C offset (J1939-71: SPN 1636/1637/2986/2630).
    0xFE69: [
        _F("Intake Manifold Air Temperature (high-res)", "i16", 0, 0.03125,
           -273, "{:.1f}", "\u00b0C"),
        _F("Engine Coolant Temperature (high-res)", "i16", 2, 0.03125,
           -273, "{:.1f}", "\u00b0C"),
        _F("Intake Valve Actuation Oil Temperature", "i16", 4, 0.03125,
           -273, "{:.1f}", "\u00b0C"),
        _F("Charge Air Cooler Outlet Temperature", "i16", 6, 0.03125,
           -273, "{:.1f}", "\u00b0C"),
    ],
    # TCW (65174) turbocharger wastegate: wastegate drives 1-4 (SPN
    # 1188-1191, 1 byte, 0.4 %/bit percent SLOT). SPN 1192 actuator air
    # pressure scale is not verified, so that field is not decoded.
    0xFE96: [
        _F("Turbocharger 1 Wastegate Drive", "u8", 0, 0.4, 0, "{:.1f}", "%"),
        _F("Turbocharger 2 Wastegate Drive", "u8", 1, 0.4, 0, "{:.1f}", "%"),
        _F("Turbocharger 3 Wastegate Drive", "u8", 2, 0.4, 0, "{:.1f}", "%"),
        _F("Turbocharger 4 Wastegate Drive", "u8", 3, 0.4, 0, "{:.1f}", "%"),
    ],
    # EEC4 (65214) rated engine power/speed. J1939-71: SPN 166 is
    # 0.5 kW/bit (0-32,127.5 kW), SPN 189 the standard 0.125 rpm/bit speed SLOT.
    0xFEBE: [
        _F("Rated Engine Power", "i16", 0, 0.5, 0, "{:.1f}", "kW"),
        _F("Rated Engine Speed", "i16", 2, 0.125, 0, "{:.0f}", "RPM"),
    ],
}


# DPF regen inhibit reasons (SPN 3703-3711) in PGN 64892 (DPFC1). Each is a
# packed 2-bit field: 00 = not inhibiting, 01 = inhibiting, 1x = not available.
# (spn, byte_index, bit_shift, label); byte 3 (index 2) holds 3702 at bits 1-2
# then 3703 at bits 3-4; bytes 4-5 (indices 3-4) hold 3704-3711 two per byte.
_DPF_INHIBIT_REASONS = (
    (3703, 2, 2, "Inhibit switch"),
    (3704, 3, 0, "Clutch disengaged"),
    (3705, 3, 2, "Service brake active"),
    (3706, 3, 4, "PTO active"),
    (3707, 3, 6, "Accelerator pedal"),
    (3708, 4, 0, "System fault"),
    (3709, 4, 2, "Engine speed"),
    (3710, 4, 4, "Parking brake not set"),
    (3711, 4, 6, "Low exhaust temperature"),
)


def _dpf_inhibit_reasons(data: bytes) -> list:
    """Labels of the DPF regen inhibit reasons whose 2-bit field is 01 (active),
    from PGN 64892 DPFC1 bytes 3-5."""
    return [label for _spn, byte, shift, label in _DPF_INHIBIT_REASONS
            if byte < len(data) and ((data[byte] >> shift) & 0x3) == 1]


# =============================================================================
# Custom / bit / status / conditional handlers
# =============================================================================

def _h_etc2(data: bytes) -> list:
    # ETC2 (61445) gear
    out = []
    if len(data) >= 4:
        out.append(("Selected Gear", _gear_name(data[0]), ""))
        out.append(("Current Gear", _gear_name(data[3]), ""))
        _add(out, "Actual Gear Ratio", _i16(data, 1), 0.001, 0, "{:.3f}", "")
    return out


def _h_ccvs1(data: bytes) -> list:
    # CCVS1 (65265) road speed / cruise
    out = []
    if len(data) >= 8:
        _add(out, "Wheel-Based Vehicle Speed", _i16(data, 1), 1 / 256.0, 0,
             "{:.1f}", "km/h")
        _add(out, "Cruise Control Set Speed", _u8(data, 6), 1.0, 0, "{:.0f}", "km/h")
        _add_status(out, "Cruise Brake Switch", (data[7] >> 0) & 0x3, "Off", "On")
    return out


def _h_ic1(data: bytes) -> list:
    # IC1 (65270) inlet/exhaust. An ABSOLUTE manifold pressure of 0 kPa is not a
    # physical reading: the ECM leaves the field unpopulated; drop it.
    # (Old gate: 7 bytes.)
    out = []
    if len(data) >= 7:
        _add(out, "Particulate Trap Inlet Pressure", _u8(data, 0), 0.5, 0, "{:.1f}", "kPa")
        map_raw = _u8(data, 1)
        if map_raw:
            _add(out, "Intake Manifold Pressure", map_raw, 2.0, 0, "{:.0f}", "kPa")
        _add(out, "Intake Manifold Temperature", _u8(data, 2), 1.0, -40, "{:.0f}", "\u00b0C")
        _add(out, "Air Inlet Pressure", _u8(data, 3), 2.0, 0, "{:.0f}", "kPa")
        _add(out, "Air Filter Differential Pressure", _u8(data, 4), 0.05, 0, "{:.1f}", "kPa")
        _add(out, "Exhaust Gas Temperature", _i16(data, 5), 0.03125, -273, "{:.0f}", "\u00b0C")
    return out


def _h_ebc1(data: bytes) -> list:
    # EBC1 (61441) brakes/ABS
    out = []
    if len(data) >= 6:
        b0, b5, b3 = data[0], data[5], data[3]
        _add_status(out, "ASR Engine Control", (b0 >> 0) & 0x3)
        _add_status(out, "ASR Brake Control", (b0 >> 2) & 0x3)
        _add_status(out, "ABS Active", (b0 >> 4) & 0x3, "Passive", "Active")
        _add_status(out, "Brake Pedal Switch", (b0 >> 6) & 0x3, "Released", "Applied")
        _add(out, "Brake Pedal Position", _u8(data, 1), 0.4, 0, "{:.1f}", "%")
        _add_status(out, "ABS Fully Operational", (b5 >> 0) & 0x3, "No", "Yes")
        _add_status(out, "EBS Red Warning", (b5 >> 2) & 0x3)
        _add_status(out, "EBS Amber Warning", (b5 >> 4) & 0x3)
        out.append(("Trailer ABS Status",
                    {0: "Not active", 1: "Active", 2: "Reserved",
                     3: "Not available"}.get(b3 & 0x3, "?"), ""))
        _add_status(out, "Trailer ABS Warning", (b3 >> 2) & 0x3)
    return out


def _h_wheel(data: bytes) -> list:
    # Wheel Speed Info (65215). Front-axle speed base + relative per-wheel terms.
    out = []
    if len(data) >= 2:
        front_raw = _i16(data, 0)
        if front_raw is not None:
            base = front_raw / 256.0
            out.append(("Front Axle Speed", f"{base:.1f}", "km/h"))
            if len(data) >= 8:
                for name, i in (("Wheel Speed FL", 2), ("Wheel Speed FR", 3),
                                ("Wheel Speed R1L", 4), ("Wheel Speed R1R", 5),
                                ("Wheel Speed R2L", 6), ("Wheel Speed R2R", 7)):
                    b = data[i]
                    if b >= 0xFE:
                        continue
                    out.append((name, f"{base + b / 16.0 - 7.8125:.1f}", "km/h"))
    return out


def _h_tc1(data: bytes) -> list:
    # TC1 (256) transmission control / request
    out = []
    if len(data) >= 2:
        b0 = data[0]
        _add_status(out, "Gear Shift Inhibit", (b0 >> 0) & 0x3, "No", "Yes")
        _add_status(out, "Torque Conv. Lockup Disable", (b0 >> 2) & 0x3, "No", "Yes")
        _add_status(out, "Driveline Disengage", (b0 >> 4) & 0x3, "No", "Yes")
        _add(out, "Requested Clutch Slip", _u8(data, 1), 0.4, 0, "{:.1f}", "%")
    return out


def _h_at1fc1(data: bytes) -> list:
    # AT1FC1 (64785) DPF regen dosing (old gate: 8 bytes)
    out = []
    if len(data) >= 8:
        _add_status(out, "DPF Regeneration", (data[6] >> 4) & 0x3, "Inactive", "Active")
        _add(out, "DPF Dosing Fuel Rate", _i16(data, 2), 0.05, 0, "{:.2f}", "L/h")
        _add(out, "DPF Dosing Fuel Pressure", _i16(data, 0), 0.1, 0, "{:.1f}", "kPa")
    return out


def _h_dpfc1(data: bytes) -> list:
    # DPFC1 (64892) DPF regen status/inhibit
    out = []
    if len(data) >= 3:
        b0, b1, b2 = data[0], data[1], data[2]
        out.append(("DPF Regen Lamp Command",
                    {0: "Off", 1: "On (solid)", 4: "Fast blink",
                     7: "Not available"}.get(b0 & 0x7, "Reserved"), ""))
        _add_status(out, "Passive Regeneration", b1 & 0x3, "Inactive", "Active")
        out.append(("Active Regeneration",
                    {0: "Not active", 1: "Active", 2: "Regeneration needed",
                     3: "Not available"}.get((b1 >> 2) & 0x3, "?"), ""))
        dpf = (b1 >> 4) & 0x7
        if dpf != 0x7:
            out.append(("DPF Status", {0: "Level 0 (clean)", 1: "Level 1",
                                       2: "Level 2", 3: "Level 3", 4: "Level 4",
                                       5: "Level 5"}.get(dpf, f"Level {dpf}"), ""))
        _add_status(out, "Regeneration Inhibited", b2 & 0x3, "No", "Yes")
        if (b2 & 0x3) == 1:
            reasons = _dpf_inhibit_reasons(data)
            out.append(("Regen Inhibit Reason",
                        "; ".join(reasons) if reasons
                        else "Inhibited (reason not reported)", ""))
    return out


def _h_fdb2(data: bytes) -> list:
    # AT1 Intermediate Gas (64946): EGT2, DPF intermediate gas temp, diff pressure
    out = []
    if len(data) >= 4:
        _add(out, "Exhaust Gas Temperature 2", _i16(data, 0), 0.03125, -273,
             "{:.0f}", "\u00b0C")
        _add(out, "DPF Intermediate Gas Temperature", _i16(data, 2), 0.03125,
             -273, "{:.0f}", "\u00b0C")
        if len(data) >= 6:
            _add(out, "DPF Differential Pressure", _i16(data, 4), 0.1, 0,
                 "{:.1f}", "kPa")
    return out


def _h_etc7(data: bytes) -> list:
    # ETC7 (65226) transmission indicator/status
    out = []
    if len(data) >= 6:
        _add_status(out, "Trans Service Indicator", (data[0] >> 2) & 0x3)
        _add_status(out, "Trans Warning Indicator", (data[5] >> 2) & 0x3)
        _add_status(out, "Shift Inhibit", (data[1] >> 6) & 0x3, "No", "Yes")
    return out


def _h_brakes1(data: bytes) -> list:
    # Brakes 1 (65266? 0xFEFA) air pressures + parking brake
    out = []
    if len(data) >= 4:
        _add(out, "Brake Application Pressure", _u8(data, 0), 4.0, 0, "{:.0f}", "kPa")
        _add(out, "Brake Primary Pressure", _u8(data, 1), 4.0, 0, "{:.0f}", "kPa")
        _add(out, "Brake Secondary Pressure", _u8(data, 2), 4.0, 0, "{:.0f}", "kPa")
        _add_status(out, "Parking Brake", (data[3] >> 0) & 0x3, "Released", "Applied")
    return out


def _h_shutdown(data: bytes) -> list:
    # Shutdown (65252). (Old gate: 8 bytes.)
    out = []
    if len(data) >= 8:
        _add_status(out, "Engine Protection Shutdown", (_u8(data, 1) or 0) >> 1,
                    "Has not shutdown", "Has shutdown engine")
    return out


def _h_weight(data: bytes) -> list:
    # Vehicle Weight / Carrying (65258)
    out = []
    if len(data) >= 8:
        axle = data[0] & 0xF
        if axle != 0xF:
            out.append(("Axle Location", f"{axle}", ""))
        _add(out, "Vehicle Weight", _i32(data, 1), 1000.0, 0, "{:.0f}", "kg")
    return out


# PGN -> custom handler (for bit/status/conditional logic).
_SPECIAL: dict[int, Callable[[bytes], list]] = {
    0xF005: _h_etc2,      # ETC2 gear
    0xFEF1: _h_ccvs1,     # CCVS1 cruise/road speed
    0xFEF6: _h_ic1,       # IC1 inlet/exhaust (drop 0-kPa MAP)
    0xF001: _h_ebc1,      # EBC1 brakes/ABS
    0xFEBF: _h_wheel,     # wheel speeds
    0x00100: _h_tc1,      # TC1 transmission control
    0xFDA1: _h_at1fc1,    # AT1FC1 DPF dosing
    0xFD7C: _h_dpfc1,     # DPFC1 DPF regen status
    0xFDB2: _h_fdb2,      # AT1 intermediate gas
    0xFE4A: _h_etc7,      # ETC7 indicators
    0xFEFA: _h_brakes1,   # Brakes 1
    0xFEE4: _h_shutdown,  # Shutdown
    0xFEEA: _h_weight,    # Vehicle weight
}


# Minimum payload length per PGN before ANY of its fields decode - the
# exact gates the pre-refactor per-PGN handlers used (restored verbatim from
# the old code so short/truncated frames behave identically), with 8 for the
# PGNs added since (all standard 8-byte broadcast groups). Multipacket groups
# (AT1TI 0xFD79: 24, EC1 0xFEE3: 21, RC 0xFEE1: 18) only decode once the
# transport protocol delivers their full payload.
PGN_MIN_LEN: dict[int, int] = {
    0x00100: 2, 0xF000: 6, 0xF001: 6, 0xF002: 7, 0xF003: 3, 0xF004: 6,
    0xF005: 4, 0xF00A: 6, 0xF00C: 8, 0xF01A: 8, 0xFD20: 6, 0xFD65: 6,
    0xFD79: 24, 0xFD7B: 2, 0xFD7C: 3, 0xFD8C: 4, 0xFD94: 8, 0xFD95: 8,
    0xFD9F: 8, 0xFDA1: 8, 0xFDAF: 8, 0xFDB0: 8, 0xFDB2: 4, 0xFDB3: 4,
    0xFDB4: 4, 0xFDC1: 8, 0xFDD0: 8, 0xFE4A: 6, 0xFE56: 8, 0xFE69: 8,
    0xFE92: 8, 0xFE96: 8, 0xFE9A: 2, 0xFEAE: 6, 0xFEBD: 8, 0xFEBE: 8,
    0xFEBF: 2, 0xFEC1: 8, 0xFEDC: 8, 0xFEDF: 6, 0xFEE1: 18, 0xFEE3: 21,
    0xFEE4: 8, 0xFEE5: 8, 0xFEE7: 8, 0xFEE9: 8, 0xFEEA: 8, 0xFEEE: 5,
    0xFEEF: 4, 0xFEF0: 4, 0xFEF1: 8, 0xFEF2: 7, 0xFEF5: 5, 0xFEF6: 7,
    0xFEF7: 8, 0xFEF8: 6, 0xFEFA: 4, 0xFEFC: 2, 0xFE6C: 8, 0xFE6F: 8,
}


def decode_live(pgn: int, data: bytes) -> list[tuple[str, str, str]]:
    """Return ``[(name, value, unit), ...]`` for a known live-data PGN."""
    if data and all(b == 0xFF for b in data):
        return []

    handler = _SPECIAL.get(pgn)
    if handler is not None:
        return handler(data)

    if len(data) < PGN_MIN_LEN.get(pgn, 8):
        return []

    out: list[tuple[str, str, str]] = []
    for field in PGN_FIELDS.get(pgn, ()):
        r = field(data)
        if r:
            out.append(r)
    return out


# Common live-data PGN -> human name. Used for labelling raw/source traffic.
PGN_NAMES = {
    0xF000: "Electronic Retarder Controller 1 (ERC1)",
    0xF001: "Electronic Brake Controller 1 (EBC1)",
    0xF002: "Electronic Transmission Controller 1 (ETC1)",
    0xF003: "Electronic Engine Controller 2 (EEC2)",
    0xF004: "Electronic Engine Controller 1 (EEC1)",
    0xF005: "Electronic Transmission Controller 2 (ETC2)",
    0xF00C: "Electronic Transmission Controller 8 (ETC8)",
    0xFD9F: "Aftertreatment 1 Air Control 1 (AT1AC1)",
    0xFDAF: "Aftertreatment 2 Intermediate Gas (AT2IMG)",
    0xFDB0: "Aftertreatment 2 Outlet Gas 2 (AT2OG2)",
    0xFE6C: "Tachograph (TCO1)",
    0xFE6F: "Adaptive Cruise Control 1 (ACC1)",
    0xFEBD: "Fan Drive (FD)",
    0xFEBE: "Electronic Engine Controller 4 (EEC4)",
    0xF01A: "Engine Throttle / Fuel Actuator Control (TFAC)",
    0xFDD0: "Inlet/Exhaust Conditions 2 (IC2)",
    0xFE69: "Engine Temperature 3 (ET3)",
    0xFE96: "Turbocharger Wastegate (TCW)",
    0xFEEE: "Engine Temperature 1 (ET1)",
    0xFEEF: "Engine Fluid Level / Pressure 1 (EFL/P1)",
    0xFEF0: "Power Takeoff Information (PTO)",
    0xFEF1: "Cruise Control / Vehicle Speed 1 (CCVS1)",
    0xFEF2: "Fuel Economy (LFE)",
    0xFEF5: "Ambient Conditions (AMB)",
    0xFEE9: "Fuel Consumption (LFC/total fuel used)",
    0xFEF6: "Inlet/Exhaust Conditions 1 (IC1)",
    0xFEF7: "Vehicle Electrical Power 1 (VEP1)",
    0xFEF8: "Transmission Fluids 1 (TF)",
    0xFE4A: "Electronic Transmission Controller 7 (ETC7)",
    0xFE9A: "Turbocharger Information (TCI)",
    0x00100: "Transmission Control 1 (TC1)",
    0xFE56: "Aftertreatment 1 DEF Tank Info",
    0xF00A: "Engine Gas Flow Rate (EGF1)",
    0xFEBF: "Wheel Speed Information",
    0xFD20: "Aftertreatment 1 DOC (Diesel Oxidation Catalyst)",
    0xFD65: "Aftertreatment 1 Fuel Control 2",
    0xFD79: "Aftertreatment 1 Trip Information (AT1TI)",
    0xFD7B: "Aftertreatment 1 Service / DPF load",
    0xFD7C: "Aftertreatment 1 DPF Control (DPFC1)",
    0xFDB2: "Aftertreatment 1 Intermediate Gas",
    0xFD8C: "Aftertreatment 1 Diesel Particulate Filter Pressure",
    0xFDB3: "Aftertreatment 1 Outlet Gas",
    0xFDB4: "Aftertreatment 1 Intake Gas",
    0xFDA1: "Aftertreatment 1 Fuel Control 1 (DPF dosing)",
    0xFEE1: "Retarder Configuration (RC)",
    0xFEE3: "Engine Configuration 1 (EC1)",
    0xFEE4: "Shutdown",
    0xFEE5: "Engine Hours, Revolutions",
    0xFEE7: "Vehicle Hours",
    0xFEC1: "High Resolution Vehicle Distance (VDHR)",
    0xFEDC: "Idle Operation (total idle hours/fuel)",
    0xFEEA: "Vehicle Weight",
    0xFEAE: "Air Supply Pressure",
    0xFEFA: "Brakes 1",
}


def pgn_name(pgn: int) -> str:
    return PGN_NAMES.get(pgn, f"PGN 0x{pgn:05X}")
