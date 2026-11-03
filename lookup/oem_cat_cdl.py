"""OpenTruck - Caterpillar CDL parameter identifiers (live data).

DISCLAIMER: The data in this file is a compilation assembled from sources
found through ordinary internet search (public service documentation,
fault-code lists and similar material). It is not an official publication
of Caterpillar, and the OpenTruck project has no affiliation with, sponsorship
from, or endorsement by Caterpillar or any vehicle, engine or component
manufacturer; all brand names are the property of their respective owners.
The contents may be inaccurate, incomplete or out of date and are provided
as-is, without warranty of any kind.

Wire form (verified from the 2026-11-13 C6.6 and wheel-loader captures; the
onboard display polls the engine with exactly these shapes):
  * PID high byte 0x00:  request  [MID 11][target][0x20][pid low]
                        reply    [target][MID 11][pid low][value...]
  * PID high byte != 0: request  [MID 11][target][0x60][pid high][pid low]
                        reply    [target][MID 11][pid high][pid low][value...]
  * PID 0x0082 (diagnostic codes) is handled separately by ``decode_codes``;
    the identity reads (0xF8 subs, 0x86) are text, not numbers, and are
    handled by the identity extractor."""

# pid -> (name, value lengths accepted, scale, offset, unit)
CAT_CDL_LIVE: dict[int, tuple[str, tuple[int, ...], float, float, str]] = {
    0x0040: ("Engine Speed", (2,), 0.5, 0.0, "RPM"),
    0x0041: ("Engine Timing", (2,), 0.1, 0.0, "\u00b0"),
    0x0044: ("Engine Coolant Temperature", (2,), 1.0, 0.0, "\u00b0C"),
    0x0046: ("Desired Engine Speed", (2,), 0.5, 0.0, "RPM"),
    0x004B: ("Rated Engine Speed", (2,), 0.5, 0.0, "RPM"),
    0x0054: ("Engine Oil Pressure", (2,), 0.5, 0.0, "kPa"),
    0x005D: ("Inlet Manifold Pressure", (2,), 1.0, 0.0, "kPa"),
    0x005E: ("Hourmeter", (2,), 1.0, 0.0, "h"),
    0x0016: ("Inlet Manifold Temperature", (1,), 1.0, 0.0, "\u00b0C"),
    0xF013: ("System Battery Voltage", (1, 2), 0.5, 0.0, "V"),
    0xF40E: ("Differential Oil Pressure", (2,), 0.5, 0.0, "kPa"),
}

# Raw-value ranges reserved as FAULT IDENTIFIERS, not data (engine
# PID sections: "Resolution: 0.5 rpm per bit ... $8000-$801F are Fault
# Identifiers", likewise for coolant and oil pressure; "Engine Oil Pressure
# Differential $F4 $0E ... $FFE0-$FFFF are Fault Identifiers"). A reply whose
# assembled raw value lands inside a PID's range is a sensor-fault report:
# never decoded as a number (the FID meaning itself needs the separate Fault
# Identifier tables - wire evidence first).
CAT_CDL_FID: dict[int, tuple[int, int]] = {
    0x0040: (0x8000, 0x801F),   # Engine Speed
    0x0044: (0x8000, 0x801F),   # Engine Coolant Temperature
    0x0054: (0x8000, 0x801F),   # Engine Oil Pressure
    0xF40E: (0xFFE0, 0xFFFF),   # Engine Oil Pressure Differential
}

# PIDs whose published data range includes NEGATIVE values, so the 16-bit
# value is signed (coolant "Data range -32736 through 32767 C" -
# the FID range $8000-$801F is the gap between the positive and negative
# halves; filtered oil pressure "-16368 through 16383.5 kPa"). Positive
# readings are identical either way; a negative bias would otherwise render
# as ~65000 - the other half of the "winter machine reads nonsense" bug.
CAT_CDL_SIGNED: frozenset[int] = frozenset((0x0044, 0x0054))

# Live parameters polled from an engine controller, fastest/most useful first.
# One request per CDL poll tick (400 ms), so the set refreshes every ~3 s.
CAT_CDL_LIVE_POLL: tuple[int, ...] = (
    0x0040,   # Engine Speed
    0x0044,   # Engine Coolant Temperature
    0x0054,   # Engine Oil Pressure
    0xF013,   # System Battery Voltage
    0x005E,   # Hourmeter
    0x0016,   # Inlet Manifold Temperature
    0x005D,   # Inlet Manifold Pressure
    0xF40E,   # Differential Oil Pressure
)

# CAT MIDs whose published name marks them as an engine controller (Engine
# Control #1..#10, Backup Engine Control). Live engine PIDs are requested only
# from these; asking a display or transmission for an engine sensor wastes bus
# time and teaches us nothing.
ENGINE_MID_NAMES = tuple(
    "Engine Control #%d" % n for n in range(1, 11)
) + ("Backup Engine Control",)
