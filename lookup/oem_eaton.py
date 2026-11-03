"""OpenTruck - Eaton Fuller "Top 2" transmission fault overlay.

The Fuller Top-2 splitter/lockout system has **no controller of its own**: the
ENGINE ECM drives the solenoids and reports the resulting faults under its own
MID, using transmission-flavoured SIDs and PIDs. So on such a truck a
transmission fault genuinely arrives as, for example, ``SID 40 FMI 4`` from the
engine module.

That collides with the SAE engine-class meaning of the same numbers (SID 40 on
an engine is "Auxiliary Output Device Driver #2"), which is why these entries
live in an overlay rather than in the per-maker tables:

  * it is applied ONLY to engine-class MIDs, and
  * ONLY when a transmission module is also present on the bus (MID 130/176 on
    J1587, or a J1939 module whose function/CI says transmission). Without a
    gearbox in sight, the engine's own SID meaning wins.
  * the rendered description always starts with "Transmission (Eaton Fuller
    Top-2): ", so a code shown under the Engine module is unmistakable.

DISCLAIMER: The data in this file is a compilation assembled from sources
found through ordinary internet search (public service documentation,
fault-code lists and similar material). It is not an official publication
of Eaton, and the OpenTruck project has no affiliation with, sponsorship
from, or endorsement by Eaton or any vehicle, engine or component
manufacturer; all brand names are the property of their respective owners.
The contents may be inaccurate, incomplete or out of date and are provided
as-is, without warranty of any kind.

Only the short component/condition names are stored; no procedures are
redistributed.

Deliberately NOT included: the Mack row (SID 10/11 FMI 3/4). On an engine MID
SID 10/11 are "Injector Cylinder #10/#11" - a real and common engine fault -
so relabelling them as transmission faults would be worse than the alternative.

--- MODERN EATON CUMMINS ENDURANT (J1939) ---

The legacy Fuller Top-2 system above is engine-driven (no controller of its
own). Today's Eaton Cummins automated transmissions (Endurant family) instead
have their OWN Transmission Control Module (TCM) that reports faults over ``J1939``
under the transmission source address, using standard SAE ``SPN``/``FMI`` pairs;
the proprietary Mechatronic Transmission Module (MTM) SPNs (shift-rail position
4219/4220/5941/5942, rail/solenoid 5901-5910 & 6145-6148, clutch solenoids, oil
temperature/pressure, TCM operation...) are not in the generic SAE registry and
would otherwise degrade to "Refer to OEM".

``EATON_SPN`` below maps each modern fault code's SPN to its short component/
condition name, transcribed from the official Eaton Cummins Troubleshooting
Guides TRTS0950 (Endurant HD) and TRTS0960 (Endurant XD). The two share the
same SPN mapping for common codes; TRTS0960 adds the XD-specific Rail A
series, Split-Shaft PTO, auxiliary-transmission/2-speed-axle and TCM-protection
codes (noted inline). Each fault code is a distinct SPN with one description
shared by its listed FMIs, so an SPN->description table is the faithful shape.
It is applied through ``oem.py``'s ``resolve_code_description`` so it only ever
names a code on a module identified as Eaton/Eaton Cummins - never another
maker."""

from __future__ import annotations

from typing import Optional


# Modern Eaton Cummins Endurant J1939 fault codes: SPN -> short component /
# condition name (TRTS0950 troubleshooting guide). One entry per fault code;
# the FMI list that qualifies each code is intentionally dropped here because
# every listed FMI shares the same description. See resolution in oem.py.
EATON_SPN: dict[int, str] = {
    # Inputs / network data
    168: "Battery Voltage 1",
    444: "Battery Voltage 2",
    158: "Ignition Voltage",
    639: "Primary Data Link (J1939 A)",
    1231: "Secondary Data Link (J1939 B)",
    1321: "Start Enable Relay",
    3651: "Primary ADS",
    3654: "Secondary ADS",
    15250: "Source Address of Controlling Device for Automated Driving System (ADS)",
    20870: "Primary ADS Operation Status",
    20874: "Secondary ADS Operation Status",
    595: "Cruise Control Active",
    5604: "Cruise Control Resume Command",
    5605: "Cruise Control Pause Command",
    751: "Primary Shift Device (J1939)",
    3652: "Transmission Primary Shift Up Selector",
    11756: "Source Address of Controlling Device for TSC1 Control Purpose P7",
    2911: "Halt Brake Switch",
    2913: "Halt Brake Mode",
    1121: "EBS Brake Switch",
    15264: "XBR Brake Hold Mode",
    3653: "Transmission Primary Shift Down Selector",
    3656: "Transmission Secondary Shift Down Selector",
    752: "Secondary Shift Device (PWM)",
    4050: "Transmission Secondary Mode Switch",
    630: "Performance Goal Calibrations",
    561: "ASR Engine Control Active",
    562: "ASR Brake Control Active",
    563: "ABS Active",
    577: "ASR Hill Holder Switch",
    2912: "Hill Holder Mode",
    70: "Park Brake Switch",
    521: "Brake Pedal Position",
    2917: "XBR System State",
    2918: "XBR Active Control Mode",
    1088: "Service Brake Circuit 2",
    597: "Service Brake Switch",
    116: "Brake Application Pressure",
    118: "Brake Secondary Pressure",
    8484: "Demanded Brake Application Pressure",
    603: "Service Brake Switch 2",
    91: "Primary Accelerator Pedal Position",
    29: "Secondary Accelerator Pedal Position",
    559: "Accelerator Pedal Kickdown Switch",
    117: "Brake Primary Pressure",
    904: "Front Axle Speed",
    190: "Engine Speed",
    723: "Secondary Engine Speed",
    1846: "Engine Default Torque Limit",
    518: "Engine Requested Torque",
    188: "Engine Configuration Message",
    6395: "Engine Configuration Identification",
    10294: "Powertrain Adaptive Cruise Control",
    2432: "Engine Demand Percent Torque",
    512: "Driver Demanded Torque",
    7828: "Engine Default Idle Torque Limit",
    7830: "Idle Governor Fueling Inhibit",
    1483: "Source Address (SA) of Controlling Device for Engine Control",
    905: "Front Axle Left Wheel Speed",
    906: "Front Axle Right Wheel Speed",
    907: "Rear Axle 1 Left Wheel Speed",
    908: "Rear Axle 1 Right Wheel Speed",
    1571: "Direction Mismatch",
    # TCM / control module
    629: "TCM Operation 1",
    609: "TCM Operation 2",
    628: "TCM Program Memory",
    # Transmission pressures / temperatures / actuators
    127: "Transmission Oil Pressure",
    177: "Transmission Oil Temperature",
    37: "Transmission Air Supply Pressure Sensor",
    33: "Linear Clutch Actuator (LCA) Position",
    # Shift-rail positions (MTM)
    4219: "Rail B Position",
    4220: "Rail C Position",
    5941: "Rail D Position",
    5942: "Rail E Position",
    5052: "Engine (Over) Speed",
    # Speeds
    161: "Input Speed",
    160: "Countershaft Speed",
    191: "Output Speed",
    # Sensors
    583: "Grade Sensor",
    # Clutch actuators / solenoids
    5614: "Clutch Engage Solenoid 1 (C4)",
    5615: "Clutch Engage Solenoid 2 (C3)",
    5616: "Clutch Release Solenoid 1 (C5)",
    5617: "Clutch Release Solenoid 2 (C6)",
    787: "Inertia Brake Solenoid (A5)",
    # Shift-rail solenoids (MTM)
    5901: "Rail B Fore Solenoid (A5)",
    5909: "Rail B Aft Solenoid (A1)",
    5902: "Rail C Fore Solenoid (C1)",
    5910: "Rail C Aft Solenoid (B1)",
    5903: "Rail D Fore Solenoid (C2)",
    4216: "Rail D Aft Solenoid (B3)",
    768: "Rail E Fore Solenoid (A6)",
    769: "Rail E Aft Solenoid (A4)",
    # Clutch / driveline operation
    6150: "Clutch Operation",
    7847: "Clutch Engagement Status",
    560: "Driveline Engagement",
    788: "Transmission Clutch Actuator",
    2983: "Clutch Position Out of Range",
    # Gear state
    523: "Transmission Current Gear",
    524: "Transmission Selected Gear",
    525: "Transmission Requested Gear",
    # Rail operation / calibration
    6145: "Rail B Operation",
    6146: "Rail C Operation",
    6147: "Rail D Operation",
    6148: "Rail E Operation",
    5952: "Rail B Calibration",
    5953: "Rail C Calibration",
    5954: "Rail D Calibration",
    5955: "Rail E Calibration",
    5939: "Clutch Temperature",
    # PTO / neutral / misc
    3452: "PTO 1 Request",
    3453: "PTO 2 Request",
    3456: "PTO 1 Engage",
    3457: "PTO 2 Engage",
    3460: "PTO 1 Confirm",
    3461: "PTO 2 Confirm",
    3648: "Neutral Status 1",
    6159: "Neutral Status 2",
    7694: "Force Hold Neutral Output",
    7695: "Force Hold Neutral Input",
    604: "Neutral Output",
    767: "Reverse Output",
    6160: "Alternate Shift Schedule Selector",
    12939: "Rock Free Mode Switch",
    12949: "Rock Free Mode Message",
    5399: "DPF Thermal Management Active",
    5400: "SCR Thermal Management Active",
    # Endurant XD additions (TRTS0960) - codes not present in the HD guide:
    2000: "Engine Source Address",
    1087: "Service Brake Circuit 1",
    898: "Engine Requested Speed",
    1594: "Rear Axle Left Wheel Speed",
    1595: "Rear Axle Right Wheel Speed",
    21150: "TCM Protection 1",
    21151: "TCM Protection 2",
    4218: "Rail A Position",
    5900: "Rail A Fore Solenoid (A3)",
    5908: "Rail A Aft Solenoid (A2)",
    6144: "Rail A Operation",
    5951: "Rail A Calibration",
    3454: "Split Shaft PTO Request",
    3458: "Split Shaft PTO Engage",
    3462: "Split Shaft PTO Confirm",
    7941: "Railroad Mode Switch",
    3957: "Auxiliary Trans Constant Supply Actuator",
    3958: "Auxiliary Trans High Range Actuator",
    3959: "Auxiliary Trans Neutral Range Actuator",
    3960: "Auxiliary Trans Range Switch",
    15202: "Auxiliary Trans Selected Gear",
    69: "Two Speed Axle Message",
    4056: "Two Speed Axle Switch",
}

# --- Eaton Cummins UltraShift PLUS / Fuller Advantage (Gen4) ----------------
# These share one J1939+J1587 hybrid fault set (guides TRTS0940 / TRTS0980) and
# CONFLICT with the newer Endurant on shared SPNs (e.g. SPN 629 "No TECU
# Operation" vs Endurant "TCM Operation 1"; SPN 768/769 rail vs range). They are
# therefore kept in their own table and selected by MODEL (see eaton_family),
# never merged with EATON_SPN. Keyed (SPN, FMI) -> short component/condition
# name, because the same SPN carries several UltraShift meanings by FMI
# (e.g. SPN 751 has six). Only the J1939 SPN column is transcribed; the J1587
# PID/SID columns are the same logical faults on the J1708 path and are left to
# a future J1587 family table.
ULTRA_SHIFT_SPN_FMI: dict[tuple[int, int], str] = {
    (629, 12): "No TECU Operation",
    (629, 13): "Improper TECU Configuration",
    (629, 1): "No Faults Found",
    (751, 8): "J1939 Shift Control Device",
    (751, 11): "J1939 Shift Control Device",
    (751, 2): "Invalid Shift Lever Voltage",
    (751, 4): "Invalid Shift Lever Voltage",
    (751, 5): "Invalid Shift Lever Voltage",
    (751, 9): "HIL Shift Device Communication",
    (751, 14): "Invalid Shift Lever Position",
    (751, 13): "Shift Device Not Configured",
    (751, 12): "Shift Control Device Incompatible",
    (752, 2): "Invalid Shift Lever Voltage",
    (752, 4): "Invalid Shift Lever Voltage",
    (752, 5): "Invalid Shift Lever Voltage",
    (752, 14): "Invalid Shift Lever Voltage",
    (625, 2): "High Integrity Link (ECA)",
    (1321, 3): "Start Enable Relay",
    (1321, 4): "Start Enable Relay",
    (1321, 14): "Start Enable Relay",
    (520273, 9): "CAN ECA Message",
    (70, 14): "Auto-Neutral Park Brake Switch",
    (563, 9): "ABS CAN Message",
    (563, 14): "ABS CAN Message",
    (116, 9): "Urge to Move Brake Switch Signal",
    (116, 13): "Urge to Move Brake Switch Signal",
    (521, 9): "Urge to Move Brake Switch Signal",
    (521, 13): "Urge to Move Brake Switch Signal",
    (597, 9): "Urge to Move Brake Switch Signal",
    (597, 13): "Urge to Move Brake Switch Signal",
    (1121, 9): "Urge to Move Brake Switch Signal",
    (1121, 13): "Urge to Move Brake Switch Signal",
    (8484, 9): "Urge to Move Brake Switch Signal",
    (8484, 13): "Urge to Move Brake Switch Signal",
    (520215, 14): "Urge to Move Brake Switch Signal",
    (520216, 31): "Urge to Move Brake Switch Signal",
    (522, 10): "Clutch Slip",
    (522, 7): "Clutch Disengagement",
    (522, 13): "Clutch Disengagement",
    (969, 4): "Remote Throttle Enable",
    (969, 5): "Remote Throttle Enable",
    (168, 4): "Low Battery Voltage Supply",
    (168, 14): "Weak Battery Voltage Supply",
    (639, 2): "J1939 Communication Link",
    (639, 14): "J1939 Engine Message",
    (639, 12): "Shift Quality",
    (639, 13): "Shift Quality",
    (639, 11): "Neutral Coast Mode",
    (639, 31): "Neutral Coast Mode",
    (627, 5): "Power Connect",
    (768, 7): "Range Failed to Engage",
    (768, 3): "Range High Solenoid Valve",
    (768, 4): "Range High Solenoid Valve",
    (768, 5): "Range High Solenoid Valve",
    (768, 6): "Range High Solenoid Valve",
    (768, 8): "Range High Solenoid Valve",
    (768, 12): "Range High Solenoid Valve",
    (768, 18): "Range High Solenoid Valve",
    (769, 7): "Range Failed to Engage",
    (769, 3): "Range Low Solenoid Valve",
    (769, 4): "Range Low Solenoid Valve",
    (769, 5): "Range Low Solenoid Valve",
    (769, 6): "Range Low Solenoid Valve",
    (769, 8): "Range Low Solenoid Valve",
    (769, 12): "Range Low Solenoid Valve",
    (769, 18): "Range Low Solenoid Valve",
    (787, 7): "Inertia Brake Performance",
    (60, 2): "Rail Position Sensor",
    (60, 3): "Rail Position Sensor",
    (60, 4): "Rail Position Sensor",
    (60, 10): "Rail Position Sensor",
    (60, 11): "Rail Position Sensor",
    (59, 2): "Gear Position Sensor",
    (59, 3): "Gear Position Sensor",
    (59, 4): "Gear Position Sensor",
    (59, 7): "Gear Position Sensor",
    (59, 10): "Gear Position Sensor",
    (59, 11): "Gear Position Sensor",
    (161, 2): "Input Shaft Speed Sensor",
    (161, 3): "Input Shaft Speed Sensor",
    (161, 4): "Input Shaft Speed Sensor",
    (161, 5): "Input Shaft Speed Sensor",
    (160, 2): "Main Shaft Speed Sensor",
    (160, 3): "Main Shaft Speed Sensor",
    (160, 4): "Main Shaft Speed Sensor",
    (160, 5): "Main Shaft Speed Sensor",
    (191, 2): "Output Shaft Speed Sensor",
    (191, 5): "Output Shaft Speed Sensor",
    (191, 6): "Output Shaft Speed Sensor",
    (191, 8): "Output Shaft Speed Sensor",
    (191, 10): "Output Shaft Speed Sensor",
    (191, 11): "Output Shaft Speed Sensor",
    (772, 1): "Rail Motor Circuit",
    (772, 5): "Rail Motor Circuit",
    (772, 6): "Rail Motor Circuit",
    (772, 12): "Rail Motor Circuit",
    (772, 7): "Failed to Select Rail",
    (773, 1): "Gear Motor Circuit",
    (773, 5): "Gear Motor Circuit",
    (773, 6): "Gear Motor Circuit",
    (773, 12): "Gear Motor Circuit",
    (788, 2): "Electronic Clutch Actuator (ECA)",
    (788, 7): "Electronic Clutch Actuator (ECA)",
    (788, 12): "Electronic Clutch Actuator (ECA)",
    (5052, 2): "ECA Speed Sensor",
    (5052, 3): "ECA Speed Sensor",
    (5052, 4): "ECA Speed Sensor",
    (5052, 5): "ECA Speed Sensor",
    (520271, 3): "ECA Battery Voltage",
    (520271, 4): "ECA Battery Voltage",
    (520274, 3): "ECA Ignition Voltage",
    (520274, 4): "ECA Ignition Voltage",
    (520321, 13): "Grade Sensor",
    (520321, 14): "Grade Sensor",
    (560, 7): "Unable to Disengage Gear",
    (560, 11): "Unable to Disengage Gear",
    (560, 14): "Power Down in Gear",
    (781, 7): "Failed to Engage Gear",
    (781, 12): "Direction Mismatch",
    (781, 14): "Direction Mismatch",
    (518, 7): "Engine Torque Response Fault",
    (898, 7): "Engine Speed Response Fault",
    (780, 7): "Gear Engagement Detected",
}


def eaton_family(model: str | None) -> str | None:
    """Which Eaton automated-transmission family a CI model string belongs to,
    or ``None`` to use the entry's default tables.

    UltraShift PLUS and Fuller Advantage share the "Gen4" J1939+J1587 hybrid
    fault set (guides TRTS0940/TRTS0980); Endurant HD/XD are the newer J1939 SPN
    set. They conflict on shared SPNs, so this classifier keeps their tables
    apart. Unknown/empty models fall back to the default (Endurant).
    """
    m = (model or "").strip().upper()
    if any(m.startswith(p) for p in ("FOM-", "FM-", "FO-", "EO-", "F-")):
        return "ultrashift"
    if any(m.startswith(p) for p in ("EHD", "EXD", "EXDP", "EEO", "EE-", "EHD-")):
        return "endurant"
    return None

_PREFIX = "Transmission (Eaton Fuller Top-2): "

# (SID, FMI) -> short description, exactly the pairs from the source table.
EATON_SID_FMI: dict[tuple[int, int], str] = {
    # DDEC III: shift solenoid / lockout solenoid, electrical
    (26, 3): "Shift Solenoid or Lockout Solenoid - open circuit",
    (26, 4): "Shift Solenoid or Lockout Solenoid - shorted circuit",
    (40, 3): "Shift Solenoid or Lockout Solenoid - open circuit",
    (40, 4): "Shift Solenoid or Lockout Solenoid - shorted circuit",
    (53, 3): "Shift Solenoid or Lockout Solenoid - open circuit",
    (53, 4): "Shift Solenoid or Lockout Solenoid - shorted circuit",
    (54, 3): "Shift Solenoid or Lockout Solenoid - open circuit",
    (54, 4): "Shift Solenoid or Lockout Solenoid - shorted circuit",
    (55, 3): "Shift Solenoid or Lockout Solenoid - open circuit",
    (55, 4): "Shift Solenoid or Lockout Solenoid - shorted circuit",
    (56, 3): "Shift Solenoid or Lockout Solenoid - open circuit",
    (56, 4): "Shift Solenoid or Lockout Solenoid - shorted circuit",
    # Caterpillar: shift / lockout solenoid, electrical
    (40, 5): "Shift Solenoid or Lockout Solenoid - current below normal",
    (40, 6): "Shift Solenoid or Lockout Solenoid - current above normal",
    (51, 5): "Lockout Solenoid - current below normal",
    (51, 6): "Lockout Solenoid - current above normal",
    # Cummins: lockout solenoid / mechanical
    (40, 11): "Lockout Solenoid - mechanical system not responding",
    (51, 11): "Shift Solenoid or Lockout Solenoid - mechanical system not responding",
    # DDEC III: failed to complete the commanded split shift
    (26, 7): "Mechanical system not responding (shift not completed)",
    (40, 7): "Mechanical system not responding (shift not completed)",
}

# PID-based evidence of the same system (transmission output shaft speed not
# responding = the commanded shift did not take place).
EATON_PID_FMI: dict[tuple[int, int], str] = {
    (191, 7): "Mechanical system not responding (shift not completed)",
}

# Engine controller MIDs (SAE J1587 assigns these to engine ECUs).
ENGINE_MIDS = frozenset({128, 175, 183, 184, 185, 186})


def eaton_transmission_fault(is_sid: bool, number: int, fmi: int,
                             mid: int) -> Optional[str]:
    """Description for this record if it looks like a Fuller Top-2 fault.

    Returns ``None`` for anything not in the closed set, or for a non-engine
    MID (a real transmission controller names its own faults).
    """
    if mid not in ENGINE_MIDS:
        return None
    table = EATON_SID_FMI if is_sid else EATON_PID_FMI
    text = table.get((number, fmi))
    return f"{_PREFIX}{text}" if text else None
