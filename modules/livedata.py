"""OpenTruck - live J1939 parameter decoding (SAE J1939-71).

Turns live broadcast PGNs into human-readable ``(name, value, unit)`` triples.
Byte offsets, scaling factors and offsets below follow the published SAE
J1939-71 standard and public vendor documentation. Add more PGNs
freely; ``decode_live`` returns ``[]`` for anything it doesn't understand.

J1939 encodes "error" as 0xFE and "not available" as 0xFF (all-ones for the
field width); ``_u8``/``_i16`` return ``None`` for those so we skip them rather
than printing nonsense like 32739 kPa.
"""
from __future__ import annotations

from typing import Optional


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
    decoder — it would take down the whole GUI refresh loop).
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


def _dpf_inhibit_reasons(data: bytes) -> list[str]:
    """Labels of the DPF regen inhibit reasons whose 2-bit field is 01 (active),
    from PGN 64892 DPFC1 bytes 3-5."""
    return [label for _spn, byte, shift, label in _DPF_INHIBIT_REASONS
            if byte < len(data) and ((data[byte] >> shift) & 0x3) == 1]


def decode_live(pgn: int, data: bytes) -> list[tuple[str, str, str]]:
    """Return ``[(name, value, unit), ...]`` for a known live-data PGN."""
    out: list[tuple[str, str, str]] = []

    # Some ECUs broadcast an all-0xFF placeholder frame (a blanked-out EBC1,
    # for example) which would otherwise decode into a pile of bogus
    # "Not available" rows attributed to the wrong module. Skip those outright:
    # 0xFF is J1939's "not available" sentinel in every field width.
    if data and all(b == 0xFF for b in data):
        return out

    if pgn == 0xF004 and len(data) >= 6:            # EEC1 (61444) engine
        _add(out, "Engine Speed", _i16(data, 3), 0.125, 0, "{:.0f}", "RPM")
        _add(out, "Driver Demand Torque", _u8(data, 1), 1.0, -125, "{:.0f}", "%")
        _add(out, "Actual Engine Torque", _u8(data, 2), 1.0, -125, "{:.0f}", "%")

    elif pgn == 0xF003 and len(data) >= 3:          # EEC2 (61443) engine
        _add(out, "Accelerator Pedal Position", _u8(data, 1), 0.4, 0, "{:.1f}", "%")
        _add(out, "Percent Load At Current Speed", _u8(data, 2), 1.0, 0, "{:.0f}", "%")

    elif pgn == 0xF002 and len(data) >= 7:          # ETC1 (61442) transmission
        _add(out, "Transmission Output Shaft Speed", _i16(data, 1), 0.125, 0,
             "{:.0f}", "RPM")
        _add(out, "Transmission Input Shaft Speed", _i16(data, 5), 0.125, 0,
             "{:.0f}", "RPM")
        _add(out, "Percent Clutch Slip", _u8(data, 3), 0.4, 0, "{:.1f}", "%")

    elif pgn == 0xF005 and len(data) >= 4:          # ETC2 (61445) gear
        out.append(("Selected Gear", _gear_name(data[0]), ""))
        out.append(("Current Gear", _gear_name(data[3]), ""))
        _add(out, "Actual Gear Ratio", _i16(data, 1), 0.001, 0, "{:.3f}", "")

    elif pgn == 0xFEEE and len(data) >= 5:          # ET1 (65262) temps
        _add(out, "Engine Coolant Temp", _u8(data, 0), 1.0, -40, "{:.0f}", "\u00b0C")
        _add(out, "Engine Fuel Temp", _u8(data, 1), 1.0, -40, "{:.0f}", "\u00b0C")
        _add(out, "Engine Oil Temp", _i16(data, 2), 0.03125, -273, "{:.1f}",
             "\u00b0C")

    elif pgn == 0xFEEF and len(data) >= 4:          # EFL/P1 (65263) fluids
        _add(out, "Engine Oil Pressure", _u8(data, 3), 4.0, 0, "{:.0f}", "kPa")
        _add(out, "Fuel Delivery Pressure", _u8(data, 0), 4.0, 0, "{:.0f}", "kPa")

    elif pgn == 0xFEF2 and len(data) >= 2:          # LFE (65266) fuel economy
        _add(out, "Engine Fuel Rate", _i16(data, 0), 0.05, 0, "{:.2f}", "L/h")

    elif pgn == 0xFEF8 and len(data) >= 6:          # TF (65272) trans fluids
        _add(out, "Transmission Oil Temperature", _i16(data, 4), 0.03125, -273,
             "{:.1f}", "\u00b0C")

    elif pgn == 0xFEF1 and len(data) >= 3:          # CCVS1 (65265) road speed
        _add(out, "Wheel-Based Vehicle Speed", _i16(data, 1), 1 / 256.0, 0,
             "{:.1f}", "km/h")

    elif pgn == 0xFEF5 and len(data) >= 5:          # AMB (65269) ambient
        _add(out, "Barometric Pressure", _u8(data, 0), 0.5, 0, "{:.0f}", "kPa")
        _add(out, "Ambient Air Temperature", _i16(data, 3), 0.03125, -273,
             "{:.1f}", "°C")

    elif pgn == 0xFEF6 and len(data) >= 7:          # IC1 (65270) inlet/exhaust
        _add(out, "Intake Manifold Pressure", _u8(data, 1), 2.0, 0, "{:.0f}", "kPa")
        _add(out, "Intake Manifold Temperature", _u8(data, 2), 1.0, -40,
             "{:.0f}", "°C")
        _add(out, "Exhaust Gas Temperature", _i16(data, 5), 0.03125, -273,
             "{:.0f}", "°C")

    elif pgn == 0xFE9A and len(data) >= 2:          # TCI (65178) turbocharger
        # SPN 1172 "Turbocharger 1 Compressor Inlet Temperature": 16-bit
        # little-endian, 0.03125 C/bit, -273 C offset. Only turbo-1 data is
        # broadcast (bytes 2+ = 0xFF).
        _add(out, "Turbocharger 1 Compressor Inlet Temp", _i16(data, 0), 0.03125,
             -273, "{:.1f}", "°C")

    elif pgn == 0xFEE9 and len(data) >= 8:          # LFC (65257) fuel consumption
        _add(out, "Trip Fuel", _i32(data, 0), 0.5, 0, "{:.0f}", "L")
        _add(out, "Total Fuel Used", _i32(data, 4), 0.5, 0, "{:.0f}", "L")

    elif pgn == 0xFEF7 and len(data) >= 8:          # VEP1 (65271) electrical
        # Battery potential (SPN 168, bytes 4-5) is the standard field, but
        # some ECUs (e.g. Mercedes) report voltage at bytes 6-7. Read both.
        _add(out, "Battery Voltage", _i16(data, 4), 0.05, 0, "{:.2f}", "V")
        _add(out, "Alternator Voltage", _i16(data, 6), 0.05, 0, "{:.2f}", "V")

    elif pgn == 0xF001 and len(data) >= 6:          # EBC1 (61441) brakes/ABS
        # Byte layout per the published J1939-71 standard.
        b0, b5 = data[0], data[5]
        _add_status(out, "ASR Engine Control", (b0 >> 0) & 0x3)
        _add_status(out, "ASR Brake Control", (b0 >> 2) & 0x3)
        _add_status(out, "ABS Active", (b0 >> 4) & 0x3, "Passive", "Active")
        _add_status(out, "Brake Pedal Switch", (b0 >> 6) & 0x3, "Released", "Applied")
        _add(out, "Brake Pedal Position", _u8(data, 1), 0.4, 0, "{:.1f}", "%")
        _add_status(out, "ABS Fully Operational", (b5 >> 0) & 0x3, "No", "Yes")
        _add_status(out, "EBS Red Warning", (b5 >> 2) & 0x3)
        _add_status(out, "EBS Amber Warning", (b5 >> 4) & 0x3)
        # Byte 4: SPN 1836 "Trailer ABS Status" (bits 1-2) and SPN 1792
        # "Tractor-Mounted Trailer ABS Warning Signal" (bits 3-4). The trailer's
        # ABS status is relayed to the tractor over PLC and re-broadcast here.
        b3 = data[3]
        out.append(("Trailer ABS Status",
                    {0: "Not active", 1: "Active", 2: "Reserved",
                     3: "Not available"}.get(b3 & 0x3, "?"), ""))
        _add_status(out, "Trailer ABS Warning", (b3 >> 2) & 0x3)

    elif pgn == 0xFEBF and len(data) >= 2:          # Wheel Speed Info (65215)
        # SPN 904 "Front Axle Speed" (average of the two front wheels), 16-bit
        # LE, 1/256 km/h. Bytes 3-8 are per-wheel *relative* speeds (SPN 905-910,
        # 1/16 km/h, -7.8125 km/h offset, 0xFE/0xFF = n/a). Absolute wheel speed
        # = front-axle speed + relative. Positions that report reveal how many
        # wheels are sensed (4S vs 2S).
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

    elif pgn == 0x00100 and len(data) >= 2:         # TC1 (256) transmission req
        b0 = data[0]
        _add_status(out, "Gear Shift Inhibit", (b0 >> 0) & 0x3, "No", "Yes")
        _add_status(out, "Torque Conv. Lockup Disable", (b0 >> 2) & 0x3, "No", "Yes")
        _add_status(out, "Driveline Disengage", (b0 >> 4) & 0x3, "No", "Yes")
        _add(out, "Requested Clutch Slip", _u8(data, 1), 0.4, 0, "{:.1f}", "%")

    elif pgn == 0xFEDF and len(data) >= 6:          # EEC3 (65247) engine ctrl 3
        _add(out, "Desired Operating Speed", _i16(data, 1), 0.125, 0, "{:.0f}", "RPM")
        _add(out, "Exhaust Gas Mass Flow", _i16(data, 5), 0.2, 0, "{:.1f}", "kg/h")

    elif pgn == 0xF000 and len(data) >= 6:          # ERC1 (61442) retarder/engine brake
        _add(out, "Actual Retarder Torque", _u8(data, 1), 1.0, -125, "{:.0f}", "%")
        _add(out, "Intended Retarder Torque", _u8(data, 2), 1.0, -125, "{:.0f}", "%")
        _add(out, "Retarder Driver Demand", _u8(data, 5), 1.0, -125, "{:.0f}", "%")

    elif pgn == 0xF00A and len(data) >= 6:          # EGF1 (61450) gas flow
        _add(out, "EGR 1 Mass Flow", _i16(data, 0), 0.05, 0, "{:.1f}", "kg/h")
        _add(out, "Intake Air Mass Flow", _i16(data, 2), 0.05, 0, "{:.1f}", "kg/h")
        _add(out, "EGR 2 Mass Flow", _i16(data, 4), 0.05, 0, "{:.1f}", "kg/h")

    elif pgn == 0xFDA1 and len(data) >= 8:          # AT1FC1 (64785) DPF regen dosing
        _add_status(out, "DPF Regeneration", (data[6] >> 4) & 0x3, "Inactive", "Active")
        _add(out, "DPF Dosing Fuel Rate", _i16(data, 2), 0.05, 0, "{:.2f}", "L/h")
        _add(out, "DPF Dosing Fuel Pressure", _i16(data, 0), 0.1, 0, "{:.1f}", "kPa")

    elif pgn == 0xFD65 and len(data) >= 6:          # AT1FC2 (64741) DPF dosing 2
        _add(out, "AFT Fuel Pressure 2", _i16(data, 0), 0.1, 0, "{:.1f}", "kPa")
        _add(out, "HC Doser Intake Temp", _u8(data, 5), 1.0, -40, "{:.0f}", "\u00b0C")

    elif pgn == 0xFD20 and len(data) >= 6:          # A1DOC (64672) DPF DOC catalyst
        _add(out, "DOC Inlet Temp", _i16(data, 0), 0.03125, -273, "{:.0f}", "\u00b0C")
        _add(out, "DOC Outlet Temp", _i16(data, 2), 0.03125, -273, "{:.0f}", "\u00b0C")
        _add(out, "DOC Diff Pressure", _i16(data, 4), 0.1, 0, "{:.1f}", "kPa")

    elif pgn == 0xFD7B and len(data) >= 2:          # AT1 Service (64763) DPF load
        _add(out, "DPF Soot Load", _u8(data, 0), 1.0, 0, "{:.0f}", "%")
        _add(out, "DPF Ash Load", _u8(data, 1), 1.0, 0, "{:.0f}", "%")

    elif pgn == 0xFD7C and len(data) >= 3:          # DPFC1 (64892) DPF regen status
        # "Diesel Particulate Filter Control 1". Bit positions follow the
        # published J1939-71 SPN list (SAE 1-based bits -> 0-based below).
        #   SPN 3697 lamp cmd (3-bit), 3699 passive (2-bit), 3700 active (2-bit),
        #   3701 DPF status (3-bit), 3702 regen inhibited (2-bit).
        # Inhibit REASONS: SPN 3703-3711 are packed 2-bit fields (00 = not
        # inhibiting, 01 = inhibiting, 1x = not available; per SAE J1939-71).
        # Byte 3 holds 3702 (bits 1-2) then 3703 (bits 3-4); bytes 4-5
        # hold 3704-3711 two per byte.
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
        if (b2 & 0x3) == 1:                     # only meaningful when inhibited
            reasons = _dpf_inhibit_reasons(data)
            out.append(("Regen Inhibit Reason",
                        "; ".join(reasons) if reasons
                        else "Inhibited (reason not reported)", ""))

    elif pgn == 0xFDB4 and len(data) >= 4:          # AT1 Intake Gas (64948, DPF inlet)
        # SPN 3241 exhaust temp (bytes 0-1) + SPN 3242 "DPF Intake Gas Temp"
        # (bytes 2-3), both 16-bit LE, 0.03125 C/bit, -273 C offset.
        _add(out, "Exhaust Gas Temperature 1", _i16(data, 0), 0.03125, -273,
             "{:.0f}", "°C")
        _add(out, "DPF Intake Gas Temperature", _i16(data, 2), 0.03125, -273,
             "{:.0f}", "°C")

    elif pgn == 0xFDB3 and len(data) >= 4:          # AT1 Outlet Gas (64947, DPF outlet)
        # SPN 3245 exhaust temp (bytes 0-1) + SPN 3246 "DPF Outlet Gas Temp" (bytes 2-3).
        _add(out, "Exhaust Gas Temperature 3", _i16(data, 0), 0.03125, -273,
             "{:.0f}", "°C")
        _add(out, "DPF Outlet Gas Temperature", _i16(data, 2), 0.03125, -273,
             "{:.0f}", "°C")

    elif pgn == 0xFDB2 and len(data) >= 4:          # AT1 Intermediate Gas (64946, DOC→DPF)
        # SPN 3249 exhaust temp (bytes 0-1) + SPN 3250 "DPF Intermediate Gas Temp" (bytes 2-3).
        _add(out, "Exhaust Gas Temperature 2", _i16(data, 0), 0.03125, -273,
             "{:.0f}", "°C")
        _add(out, "DPF Intermediate Gas Temperature", _i16(data, 2), 0.03125,
             -273, "{:.0f}", "°C")
        # SPN 3251 "Aftertreatment 1 DPF Differential Pressure" (bytes 5-6, 0.1 kPa/bit).
        if len(data) >= 6:
            _add(out, "DPF Differential Pressure", _i16(data, 4), 0.1, 0,
                 "{:.1f}", "kPa")

    elif pgn == 0xFD8C and len(data) >= 4:          # AT1 DPF Pressure (64908)
        # SPN 3609 "DPF Intake Pressure" (bytes 1-2) + SPN 3610 "DPF Outlet
        # Pressure" (bytes 3-4), unsigned 16-bit LE, 0.1 kPa/bit.
        _add(out, "DPF Intake Pressure", _i16(data, 0), 0.1, 0, "{:.1f}", "kPa")
        _add(out, "DPF Outlet Pressure", _i16(data, 2), 0.1, 0, "{:.1f}", "kPa")

    elif pgn == 0xFE4A and len(data) >= 6:          # ETC7 (0xFE4A) trans indicators
        _add_status(out, "Trans Service Indicator", (data[0] >> 2) & 0x3)
        _add_status(out, "Trans Warning Indicator", (data[5] >> 2) & 0x3)
        _add_status(out, "Shift Inhibit", (data[1] >> 6) & 0x3, "No", "Yes")

    elif pgn == 0xFEF0 and len(data) >= 4:          # PTO (0xFEF0) power takeoff
        _add(out, "PTO Oil Temp", _u8(data, 0), 1.0, -40, "{:.0f}", "\u00b0C")
        _add(out, "PTO Speed", _i16(data, 1), 0.125, 0, "{:.0f}", "RPM")
        _add(out, "PTO Set Speed", _i16(data, 3), 0.125, 0, "{:.0f}", "RPM")

    elif pgn == 0xFEFA and len(data) >= 4:          # Brakes 1 (0xFEFA) air pressures
        _add(out, "Brake Application Pressure", _u8(data, 0), 4.0, 0, "{:.0f}", "kPa")
        _add(out, "Brake Primary Pressure", _u8(data, 1), 4.0, 0, "{:.0f}", "kPa")
        _add(out, "Brake Secondary Pressure", _u8(data, 2), 4.0, 0, "{:.0f}", "kPa")
        _add_status(out, "Parking Brake", (data[3] >> 0) & 0x3, "Released", "Applied")

    elif pgn == 0xFEAE and len(data) >= 6:          # Air Supply (0xFEAE) air pressures
        _add(out, "Pneumatic Supply Pressure", _u8(data, 0), 8.0, 0, "{:.0f}", "kPa")
        _add(out, "Parking/Trailer Air Pressure", _u8(data, 1), 8.0, 0, "{:.0f}", "kPa")
        _add(out, "Service Brake 1 Air Pressure", _u8(data, 2), 8.0, 0, "{:.0f}", "kPa")
        _add(out, "Service Brake 2 Air Pressure", _u8(data, 3), 8.0, 0, "{:.0f}", "kPa")
        _add(out, "Air Suspension Pressure", _u8(data, 5), 8.0, 0, "{:.0f}", "kPa")

    elif pgn == 0xFEE7 and len(data) >= 8:          # Vehicle Hours (0xFEE7)
        _add(out, "Total Vehicle Hours", _i32(data, 0), 0.05, 0, "{:.1f}", "h")
        _add(out, "Total PTO Hours", _i32(data, 4), 0.05, 0, "{:.1f}", "h")

    elif pgn == 0xFEE5 and len(data) >= 8:          # Engine Hours (65253)
        # SPN 247 "Total Engine Hours" (bytes 0-3, 32-bit LE, 0.05 h/bit) and
        # SPN 249 "Total Engine Revolutions" (bytes 4-7, 1000 rev/bit).
        _add(out, "Total Engine Hours", _i32(data, 0), 0.05, 0, "{:.1f}", "h")
        _add(out, "Total Engine Revolutions", _i32(data, 4), 1000.0, 0,
             "{:.0f}", "rev")

    elif pgn == 0xFEC1 and len(data) >= 8:          # High-Res Vehicle Distance (65217)
        # SPN 917 "High Resolution Total Vehicle Distance" (bytes 0-3, 32-bit LE,
        # 5 m/bit) + SPN 918 "High Resolution Trip Distance" (bytes 4-7, 5 m/bit).
        # Emitted in km to match the J1587 "Total Vehicle Distance"/"Trip
        # Distance" names used by the report and Totals panel.
        _add(out, "Total Vehicle Distance", _i32(data, 0), 0.005, 0, "{:.1f}", "km")
        _add(out, "Trip Distance", _i32(data, 4), 0.005, 0, "{:.1f}", "km")

    elif pgn == 0xFEDC and len(data) >= 8:          # Idle Operation, IO (65244)
        # SPN 236 "Engine Total Idle Fuel Used" (bytes 0-3, 0.5 L/bit) + SPN 235
        # "Engine Total Idle Hours" (bytes 4-7, 0.05 h/bit).
        _add(out, "Total Idle Fuel Used", _i32(data, 0), 0.5, 0, "{:.1f}", "L")
        _add(out, "Total Idle Hours", _i32(data, 4), 0.05, 0, "{:.1f}", "h")

    elif pgn == 0xFEE1 and len(data) >= 18:         # RC (0xFEE1) retarder config
        _add(out, "Reference Retarder Torque", _i16(data, 16), 1.0, 0, "{:.0f}", "Nm")

    elif pgn == 0xFEE3 and len(data) >= 21:         # EC1 (0xFEE3) engine configuration
        _add(out, "Engine Idle Speed", _i16(data, 0), 0.125, 0, "{:.0f}", "RPM")
        _add(out, "Engine Reference Torque", _i16(data, 19), 1.0, 0, "{:.0f}", "Nm")

    elif pgn == 0xFD79 and len(data) >= 24:         # AT1TI (0xFD79) DPF regen trip info
        _add(out, "DPF Trip Fuel Used", _i32(data, 0), 0.5, 0, "{:.1f}", "L")
        _add(out, "Active Regen Time", _i32(data, 4), 1/3600.0, 0, "{:.1f}", "h")
        _add(out, "Active Regens (trip)", _i32(data, 12), 1.0, 0, "{:.0f}", "")
        _add(out, "Passive Regens (trip)", _i32(data, 20), 1.0, 0, "{:.0f}", "")

    elif pgn == 0xFEE4 and len(data) >= 8:  # Shutdown (65252)
        # SPN 1110 "Engine Protection System has Shutdown Engine" - 2-bit
        # status field (byte 1, bits 1-2 per J1939-71).
        _add_status(out, "Engine Protection Shutdown", (_u8(data, 1) or 0) >> 1,
                    "Has not shutdown", "Has shutdown engine")

    elif pgn == 0xFEEA and len(data) >= 8:  # Vehicle Weight/Carrying (65258)
        # SPN 522 "Axle Location" - 4-bit enum, 0xF = not available.
        axle = data[0] & 0xF
        if axle != 0xF:
            out.append(("Axle Location", f"{axle}", ""))
        _add(out, "Vehicle Weight", _i32(data, 1), 1000.0, 0, "{:.0f}", "kg")

    elif pgn == 0xFE56 and len(data) >= 8:  # Aftertreatment 1 DEF Tank (65110)
        # SPN 1761 "DEF Tank Level": 0.4 %/bit, offset 0, range 0-100 %.
        # (The previous `v/10.0` referenced an undefined `v` and raised
        # NameError whenever this PGN was decoded.)
        _add(out, "DEF Tank Level", _u8(data, 1), 0.4, 0, "{:.1f}%", "")
        _add(out, "DEF Temperature", _i16(data, 2), 0.03125, -40, "{:.1f}", "\u00b0C")

    return out



# Common live-data PGN -> human name. Used for labelling raw/source traffic.
PGN_NAMES = {
    0xF000: "Electronic Retarder Controller 1 (ERC1)",
    0xF001: "Electronic Brake Controller 1 (EBC1)",
    0xF002: "Electronic Transmission Controller 1 (ETC1)",
    0xF003: "Electronic Engine Controller 2 (EEC2)",
    0xF004: "Electronic Engine Controller 1 (EEC1)",
    0xF005: "Electronic Transmission Controller 2 (ETC2)",
    0xF00C: "Transmission Controller (vendor, 0xF00C)",
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
