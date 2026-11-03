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
    handled by the identity extractor.

Names and resolutions come from public Caterpillar service documentation:
SEBU7014 (CCM Operation and Maintenance, tables 31/33 - the resolution
column), the CCM Owners Manual (3500B / EMCP II parameter tables) and the
Caterpillar "CCM Parameter Identifiers" comparison list compiled from
SEBU6874-04 and REHS0806-02. Values below that are marked LIVE were also
confirmed on a running C6.6 (2026-11-19, engine idling) by cross-checking
against the same quantity on J1939: atmospheric 0x0053 = 95.5 kPa equals the
idle absolute boost reading, and 0x005A absolute oil pressure = 0x0054 gauge
plus atmospheric within a few kPa."""

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
    # --- added 2026-11-19 from the published engine PID tables (LIVE =
    # confirmed answering on the idling C6.6 with a cross-checked value).
    0x0047: ("First Desired Timing", (2,), 0.1, 0.0, "\u00b0"),
    0x0053: ("Atmospheric Pressure", (2,), 0.5, 0.0, "kPa"),        # LIVE
    0x0055: ("Boost Pressure (gauge)", (2,), 0.5, 0.0, "kPa"),
    0x005A: ("Filtered Oil Pressure (abs)", (2,), 0.5, 0.0, "kPa"),  # LIVE
    0x005B: ("Boost Pressure (absolute)", (2,), 0.5, 0.0, "kPa"),    # LIVE
    0x005C: ("Left Turbo Inlet Pressure", (2,), 0.5, 0.0, "kPa"),
    0x005F: ("Right Turbo Inlet Pressure", (2,), 0.5, 0.0, "kPa"),   # LIVE
    # 4-byte running total; the PID table publishes no resolution for it, so
    # the raw count is shown rather than a confidently wrong number of litres.
    0x00C8: ("Total Fuel (raw count)", (4,), 1.0, 0.0, "count"),     # LIVE
    0xF118: ("Engine Load Factor", (1,), 1.0, 0.0, "%"),            # LIVE
    0xF189: ("Engine Power Derate", (1,), 0.5, 0.0, "%"),           # LIVE
    0xF509: ("Crankcase Pressure", (2,), 0.1, 0.0, "kPa"),
    0xF50E: ("Fuel Pressure (absolute)", (2,), 0.5, 0.0, "kPa"),
    0xF510: ("Low Idle Speed", (2,), 0.5, 0.0, "RPM"),              # LIVE
    0xF511: ("Intake Manifold Air Temperature", (2,), 0.1, 0.0, "\u00b0C"),
    0xF419: ("Unfiltered Oil Pressure (abs)", (2,), 0.5, 0.0, "kPa"),
    0xF51D: ("Fuel Temperature", (2,), 0.1, 0.0, "\u00b0C"),
    # Total operating TIME in seconds, 4 bytes - proven on two machines: the
    # 2026-11-13 loader replied 0x021B86D0 = 35,360,464 s = 9822.4 h against
    # a 9821 h hourmeter, and the C6.6 replied 10,201,210 s = 2833.7 h
    # against 2833.3 h. Published name: "Total Operating Hours" (0xFC2D).
    0xFC2D: ("Total Operating Time", (4,), 1.0 / 3600.0, 0.0, "h"),
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
CAT_CDL_SIGNED: frozenset[int] = frozenset((0x0044, 0x0054, 0xF509))

# Fault-Identifier ranges that apply to EVERY unsigned 1-2 byte parameter,
# not just the few listed in CAT_CDL_FID: the engine PID sections reserve
# $8000-$801F (e.g. engine speed, coolant) and $FFE0-$FFFF (e.g. oil
# pressure differential) as fault identifiers instead of data. Measured on
# the idling C6.6 (2026-11-19): 0xF50E replied FFF4 and 0xF51D/F53E replied
# 8014 - parameters the ECM has but with no valid sensor value. Signed PIDs
# are excluded because those ranges ARE their negative data range.
CAT_CDL_FID_ANY: tuple[tuple[int, int], ...] = ((0x8000, 0x801F),
                                                (0xFFE0, 0xFFFF))

# PIDs whose published data range IS the whole 16-bit word, so the generic
# fault-identifier ranges above must not apply to them. The hourmeter is
# documented "$0000-$FFFF is the valid data range (0 through 65535 hours)":
# 0xFFFE really is 65534 h, not a sensor fault.
CAT_CDL_FULL_RANGE: frozenset[int] = frozenset((0x005E,))

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
    # Wire-proven answering on the C6.6 (2026-11-19). The set is deliberately
    # machine-agnostic: an ECM that stays silent on a PID is not removed,
    # because another machine answers it (the loader answered none of 0x0016 /
    # 0x005D / 0xF40E while this engine answers 0x005B and 0xF118).
    0x005B,   # Boost Pressure (absolute)
    0xF118,   # Engine Load Factor
)

# CAT MIDs whose published name marks them as an engine controller (Engine
# Control #1..#10, Backup Engine Control). Live engine PIDs are requested only
# from these; asking a display or transmission for an engine sensor wastes bus
# time and teaches us nothing.
ENGINE_MID_NAMES = tuple(
    "Engine Control #%d" % n for n in range(1, 11)
) + ("Backup Engine Control",)

# --- CDL <-> J1939 diagnostic-code cross-reference
# Key is the CDL code (CID, FMI); value is every J1939 (SPN, FMI) paired
# with it. 1836-3/1836-4 appear against two J1939 codes in different engine
# contexts, so both candidates are kept.
CAT_CDL_TO_J1939: dict[tuple[int, int], tuple[tuple[int, int], ...]] = {
    (1, 5): ((651, 5),),
    (1, 6): ((651, 6),),
    (2, 5): ((652, 5),),
    (2, 6): ((652, 6),),
    (3, 5): ((653, 5),),
    (3, 6): ((653, 6),),
    (4, 5): ((654, 5),),
    (4, 6): ((654, 6),),
    (5, 5): ((655, 5),),
    (5, 6): ((655, 6),),
    (6, 5): ((656, 5),),
    (6, 6): ((656, 6),),
    (41, 3): ((678, 3),),
    (41, 4): ((678, 4),),
    (91, 2): ((91, 2),),
    (91, 3): ((91, 3),),
    (91, 4): ((91, 4),),
    (91, 8): ((91, 8),),
    (100, 3): ((100, 3),),
    (100, 4): ((100, 4),),
    (101, 3): ((101, 3),),
    (101, 4): ((101, 4),),
    (101, 13): ((101, 13),),
    (110, 3): ((110, 3),),
    (110, 4): ((110, 4),),
    (168, 3): ((168, 3),),
    (168, 4): ((168, 4),),
    (171, 3): ((171, 3),),
    (171, 4): ((171, 4),),
    (174, 3): ((174, 3),),
    (174, 4): ((174, 4),),
    (175, 3): ((175, 3),),
    (175, 4): ((175, 4),),
    (190, 8): ((190, 8),),
    (246, 14): ((625, 14),),
    (247, 9): ((639, 9),),
    (247, 14): ((639, 14),),
    (253, 2): ((631, 2),),
    (261, 11): ((637, 11),),
    (261, 13): ((637, 13),),
    (262, 3): ((3509, 3),),
    (262, 4): ((3509, 4),),
    (267, 3): ((4215, 3),),
    (267, 4): ((4215, 4),),
    (268, 2): ((630, 2),),
    (289, 3): ((5578, 3),),
    (289, 4): ((5578, 4),),
    (289, 21): ((5578, 21),),
    (291, 5): ((4212, 5),),
    (291, 6): ((4212, 6),),
    (298, 3): ((597, 3),),
    (298, 4): ((597, 4),),
    (342, 8): ((723, 8),),
    (444, 5): ((677, 5),),
    (444, 6): ((677, 6),),
    (460, 3): ((5580, 3),),
    (460, 4): ((5580, 4),),
    (460, 21): ((5580, 21),),
    (485, 5): ((4214, 5),),
    (485, 6): ((4214, 6),),
    (486, 3): ((486, 3),),
    (486, 4): ((486, 4),),
    (544, 2): ((544, 2),),
    (544, 8): ((544, 8),),
    (774, 2): ((29, 2),),
    (774, 3): ((29, 3),),
    (774, 4): ((29, 4),),
    (774, 8): ((29, 8),),
    (1076, 5): ((1076, 5),),
    (1076, 6): ((1076, 6),),
    (1090, 5): ((3697, 5),),
    (1090, 6): ((3697, 6),),
    (1091, 5): ((3698, 5),),
    (1091, 6): ((3698, 6),),
    (1551, 13): ((4212, 13),),
    (1779, 5): ((1347, 5),),
    (1779, 6): ((1347, 6),),
    (1780, 5): ((1348, 5),),
    (1780, 6): ((1348, 6),),
    (1785, 3): ((3563, 3),),
    (1785, 4): ((3563, 4),),
    (1785, 13): ((3563, 13),),
    (1785, 21): ((3563, 21),),
    (1797, 3): ((157, 3),),
    (1797, 4): ((157, 4),),
    (1835, 3): ((1387, 3),),
    (1835, 4): ((1387, 4),),
    (1836, 3): ((441, 3), (1385, 3)),
    (1836, 4): ((441, 4), (1385, 4)),
    (1901, 5): ((2950, 5),),
    (1901, 6): ((2950, 6),),
    (1901, 7): ((2950, 7),),
    (1902, 5): ((2951, 5),),
    (1902, 6): ((2951, 6),),
    (1902, 7): ((2951, 7),),
    (1903, 5): ((2952, 5),),
    (1903, 6): ((2952, 6),),
    (1903, 7): ((2952, 7),),
    (1904, 5): ((2953, 5),),
    (1904, 6): ((2953, 6),),
    (1904, 7): ((2953, 7),),
    (1905, 5): ((2954, 5),),
    (1905, 6): ((2954, 6),),
    (1905, 7): ((2954, 7),),
    (1906, 5): ((2955, 5),),
    (1906, 6): ((2955, 6),),
    (1906, 7): ((2955, 7),),
    (1922, 5): ((2949, 5),),
    (1922, 6): ((2949, 6),),
    (1922, 7): ((2949, 7),),
    (1924, 3): ((2948, 3),),
    (1924, 4): ((2948, 4),),
    (1937, 2): ((1937, 2),),
    (2131, 3): ((3510, 3),),
    (2131, 4): ((3510, 4),),
    (2232, 5): ((1074, 5),),
    (2232, 6): ((1074, 6),),
    (2302, 3): ((109, 3),),
    (2302, 4): ((109, 4),),
    (2348, 9): ((1231, 9),),
    (2348, 14): ((1231, 14),),
    (2417, 5): ((626, 5),),
    (2417, 6): ((626, 6),),
    (2452, 3): ((3242, 3),),
    (2452, 4): ((3242, 4),),
    (2458, 2): ((3251, 2),),
    (2458, 3): ((3251, 3),),
    (2458, 4): ((3251, 4),),
    (2458, 13): ((3251, 13),),
    (2460, 3): ((3480, 3),),
    (2460, 4): ((3480, 4),),
    (2461, 5): ((3479, 5),),
    (2461, 6): ((3479, 6),),
    (2465, 5): ((3484, 5),),
    (2465, 6): ((3484, 6),),
    (2489, 5): ((3487, 5),),
    (2489, 6): ((3487, 6),),
    (2489, 13): ((3487, 13),),
    (2490, 3): ((3488, 3),),
    (2490, 4): ((3488, 4),),
    (2497, 3): ((4077, 3),),
    (2497, 4): ((4077, 4),),
    (2526, 3): ((172, 3),),
    (2526, 4): ((172, 4),),
    (2533, 5): ((1072, 5),),
    (2533, 6): ((1072, 6),),
    (2535, 5): ((1073, 5),),
    (2535, 6): ((1073, 6),),
    (2602, 5): ((3659, 5),),
    (2602, 6): ((3659, 6),),
    (2604, 5): ((3660, 5),),
    (2604, 6): ((3660, 6),),
    (2606, 5): ((3661, 5),),
    (2606, 6): ((3661, 6),),
    (2608, 5): ((3662, 5),),
    (2608, 6): ((3662, 6),),
    (2610, 5): ((3663, 5),),
    (2610, 6): ((3663, 6),),
    (2612, 5): ((3664, 5),),
    (2612, 6): ((3664, 6),),
    (2738, 3): ((1176, 3),),
    (2738, 4): ((1176, 4),),
    (2853, 9): ((2853, 9),),
    (3090, 3): ((4334, 3),),
    (3090, 4): ((4334, 4),),
    (3090, 7): ((4334, 7),),
    (3096, 8): ((4337, 8),),
    (3100, 12): ((3516, 12),),
    (3105, 3): ((4360, 3),),
    (3105, 4): ((4360, 4),),
    (3110, 5): ((4354, 5),),
    (3110, 6): ((4354, 6),),
    (3111, 5): ((4355, 5),),
    (3111, 6): ((4355, 6),),
    (3112, 5): ((4356, 5),),
    (3112, 6): ((4356, 6),),
    (3118, 5): ((4374, 5),),
    (3118, 6): ((4374, 6),),
    (3118, 8): ((4374, 8),),
    (3126, 5): ((3363, 5),),
    (3126, 6): ((3363, 6),),
    (3126, 7): ((3363, 7),),
    (3130, 3): ((1761, 3),),
    (3130, 4): ((1761, 4),),
    (3134, 3): ((3031, 3),),
    (3134, 4): ((3031, 4),),
    (3180, 5): ((4265, 5),),
    (3182, 3): ((4301, 3),),
    (3182, 4): ((4301, 4),),
    (3182, 5): ((4301, 5),),
    (3182, 6): ((4301, 6),),
    (3183, 2): ((3696, 2),),
    (3184, 2): ((3695, 2),),
    (3239, 5): ((2813, 5),),
    (3239, 6): ((2813, 6),),
    (3372, 3): ((2630, 3),),
    (3372, 4): ((2630, 4),),
    (3385, 3): ((3358, 3),),
    (3385, 4): ((3358, 4),),
    (3385, 13): ((3358, 13),),
    (3385, 21): ((3358, 21),),
    (3386, 3): ((412, 3),),
    (3386, 4): ((412, 4),),
    (3387, 3): ((411, 3),),
    (3387, 4): ((411, 4),),
    (3387, 13): ((411, 13),),
    (3391, 5): ((5425, 5),),
    (3391, 6): ((5425, 6),),
    (3405, 5): ((2791, 5),),
    (3405, 6): ((2791, 6),),
    (3409, 5): ((5276, 5),),
    (3409, 6): ((5276, 6),),
    (3413, 5): ((5424, 5),),
    (3413, 6): ((5424, 6),),
    (3427, 5): ((5423, 5),),
    (3427, 6): ((5423, 6),),
    (3464, 3): ((3609, 3),),
    (3464, 4): ((3609, 4),),
    (3464, 13): ((3609, 13),),
    (3464, 21): ((3609, 21),),
    (3468, 2): ((5576, 2),),
    (3468, 8): ((5576, 8),),
    (3468, 14): ((5576, 14),),
    (3469, 2): ((5577, 2),),
    (3469, 8): ((5577, 8),),
    (3469, 14): ((5577, 14),),
    (3482, 11): ((3511, 11),),
    (3485, 3): ((3241, 3),),
    (3485, 4): ((3241, 4),),
    (3493, 3): ((3837, 3),),
    (3493, 4): ((3837, 4),),
    (3493, 13): ((3837, 13),),
    (3493, 21): ((3837, 21),),
    (3528, 3): ((108, 3),),
    (3528, 4): ((108, 4),),
    (3547, 3): ((97, 3),),
    (3609, 11): ((3226, 11),),
    (3609, 12): ((3226, 12),),
    (3619, 11): ((5759, 11),),
    (3621, 11): ((5758, 11),),
    (3655, 11): ((3216, 11),),
    (3655, 12): ((3216, 12),),
    (3683, 3): ((442, 3),),
    (3683, 4): ((442, 4),),
    (3820, 3): ((3360, 3),),
    (3820, 4): ((3360, 4),),
    (3820, 9): ((3360, 9),),
    (3820, 12): ((3360, 12),),
    (3821, 5): ((3361, 5),),
    (3821, 6): ((3361, 6),),
    (3821, 7): ((3361, 7),),
    (3821, 11): ((3361, 11),),
    (3821, 12): ((3361, 12),),
    (3821, 14): ((3361, 14),),
    (3822, 5): ((5491, 5),),
    (3822, 6): ((5491, 6),),
    (3838, 5): ((5965, 5),),
    (3838, 6): ((5965, 6),),
    (3862, 5): ((4376, 5),),
    (3862, 6): ((4376, 6),),
    (3862, 7): ((4376, 7),),
    (3965, 5): ((5966, 5),),
    (3965, 6): ((5966, 6),),
    (3966, 6): ((6309, 6),),
    (5856, 9): ((1235, 9),),
    (5856, 14): ((1235, 14),),
}

# Reverse view: first J1939 code listed for each pair (the document is CDL-first).
CAT_J1939_TO_CDL: dict[tuple[int, int], tuple[int, int]] = {
    j: c for c, cs in CAT_CDL_TO_J1939.items() for j in cs
}


def cat_cdl_family(model: str | None) -> str | None:
    """C13 / C15 / C18 only (the codes we carry are for that engine set)."""
    m = (model or '').upper()
    return 'c13_c18' if any(t in m for t in ('C13', 'C15', 'C18')) else None


def j1939_candidates_for_cdl(cid: int, fmi: int,
                              model: str | None = None) -> tuple[tuple[int, int], ...]:
    """Every J1939 (SPN, FMI) the CAT document pairs with this CDL code.

    Empty when the engine model does not identify C13/C15/C18.
    """
    if cat_cdl_family(model) != 'c13_c18':
        return ()
    return CAT_CDL_TO_J1939.get((cid, fmi), ())


def j1939_for_cdl(cid: int, fmi: int, model: str | None = None):
    """First J1939 (SPN, FMI) for a CDL code, or None (see candidates)."""
    c = j1939_candidates_for_cdl(cid, fmi, model)
    return c[0] if c else None
