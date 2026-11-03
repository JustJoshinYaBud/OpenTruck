"""OpenTruck - Bendix ABS/ATC fault-code table.

J1587 SID -> Bendix-specific component name for the brake controller
(MID 136).

DISCLAIMER: The data in this file is a compilation assembled from sources
found through ordinary internet search (public service documentation,
fault-code lists and similar material). It is not an official publication
of Bendix, and the OpenTruck project has no affiliation with, sponsorship
from, or endorsement by Bendix or any vehicle, engine or component
manufacturer; all brand names are the property of their respective owners.
The contents may be inaccurate, incomplete or out of date and are provided
as-is, without warranty of any kind.

Only the short, factual component name is kept here (e.g. "Left Steer Wheel
Speed Sensor"); no verbatim OEM failure-mode wording is redistributed. The
FMI failure phrase is supplied generically at display time from ``spn.FMI``
(SAE J1939-73).

Resolution goes through ``oem.resolve_sid_name`` (OEM override first, then the
per-controller J1587 SID table, then the generic SAE table), so these names
apply ONLY to a controller identified as Bendix and can never leak into another
maker's brake module.

Bendix assigns one component per SID; the failure mode is the FMI. Note that
the published blink-code table distinguishes the hold vs. release solenoid of
a modulator valve only by blink code - both share the same SID and FMI, so
that detail is not recoverable from a J1587 (SID, FMI) pair.

SIDs 5/6 and 11/12 are the second rear-axle positions, present only on 6S/6M
configurations; the naming follows the same harness-chart convention
("Left Rear Rear" / "Right Rear Rear")."""

BENDIX_SID: dict[int, str] = {
    # --- wheel speed sensors ------------------------------------------------ #
    1: "Left Steer Wheel Speed Sensor",
    2: "Right Steer Wheel Speed Sensor",
    3: "Left Rear Wheel Speed Sensor",
    4: "Right Rear Wheel Speed Sensor",
    5: "Left Rear-Rear Wheel Speed Sensor",      # 6S/6M only
    6: "Right Rear-Rear Wheel Speed Sensor",     # 6S/6M only
    # --- pressure modulator valves (hold + release solenoids) --------------- #
    7: "Left Steer Axle Pressure Modulator Valve",
    8: "Right Steer Axle Pressure Modulator Valve",
    9: "Left Rear Axle Pressure Modulator Valve",
    10: "Right Rear Axle Pressure Modulator Valve",
    11: "Left Rear-Rear Axle Pressure Modulator Valve",   # 6S/6M only
    12: "Right Rear-Rear Axle Pressure Modulator Valve",  # 6S/6M only
    # --- valves, lamps and ECU --------------------------------------------- #
    13: "Retarder Control Relay",
    14: "Pressure Modulator Valve Common Circuit",
    18: "ATC (Traction Control) Valve",
    23: "ABS Indicator Lamp Circuit",
    151: "Wheel Speed Sensor Memory Flag",   # cleared by driving after a repair
    # --- power / data link / ECU ------------------------------------------- #
    231: "J1922/J1939 Data Link",
    249: "J1922/J1939 Data Link",
    251: "ECU / Valve Power Supply Circuit",
    253: "ECU Internal / Configuration Parameter",
    254: "ECU Internal",
}