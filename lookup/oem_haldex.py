"""OpenTruck - Haldex trailer ABS fault-code table.

J1587 SID+FMI -> Haldex-specific short component name for the trailer ABS
ECU family (PLC Select 1M (2S/1M) and 2M (2S/2M and 4S/2M)); the ITCM
family's codes are merged in where they use SIDs the PLC Select tables do
not define. SIDs reused with a different physical meaning by the two
families are intentionally left with the PLC Select interpretation, which
matches the table's channel-neutral naming.

DISCLAIMER: The data in this file is a compilation assembled from sources
found through ordinary internet search (public service documentation,
fault-code lists and similar material). It is not an official publication
of Haldex, and the OpenTruck project has no affiliation with, sponsorship
from, or endorsement by Haldex or any vehicle, engine or component
manufacturer; all brand names are the property of their respective owners.
The contents may be inaccurate, incomplete or out of date and are provided
as-is, without warranty of any kind.

Only the short, factual component name is kept here; no verbatim OEM
failure-mode wording is redistributed. The FMI failure phrase is supplied
generically at display time from ``spn.FMI`` (SAE J1939-73), so the rendered
description stays correct.

The published sensor-position notes (curb/road side) and modulator channel
(Red/Blue/Yellow) depend on the configured variant and conflict between the
1M and 2M tables for shared SIDs, so the names here are channel-neutral."""

HALDEX_SID_FMI = {
    # --- Wheel speed sensors (J1587 SIDs 1-6) ----------------------------- #
    (1, 2): "Wheel Speed Sensor ABS Axle 1 Left (S1A)",
    (1, 5): "Wheel Speed Sensor ABS Axle 1 Left (S1A)",
    (1, 13): "Wheel Speed Sensor ABS Axle 1 Left (S1A)",
    (2, 2): "Wheel Speed Sensor ABS Axle 1 Right (S1B)",
    (2, 5): "Wheel Speed Sensor ABS Axle 1 Right (S1B)",
    (2, 13): "Wheel Speed Sensor ABS Axle 1 Right (S1B)",
    (3, 2): "Wheel Speed Sensor ABS Axle 2 Left (S2A)",
    (3, 5): "Wheel Speed Sensor ABS Axle 2 Left (S2A)",
    (3, 13): "Wheel Speed Sensor ABS Axle 2 Left (S2A)",
    (4, 2): "Wheel Speed Sensor ABS Axle 2 Right (S2B)",
    (4, 5): "Wheel Speed Sensor ABS Axle 2 Right (S2B)",
    (4, 13): "Wheel Speed Sensor ABS Axle 2 Right (S2B)",
    (5, 2): "Wheel Speed Sensor ABS Axle 3 Left (S3A)",
    (5, 5): "Wheel Speed Sensor ABS Axle 3 Left (S3A)",
    (5, 13): "Wheel Speed Sensor ABS Axle 3 Left (S3A)",
    (6, 2): "Wheel Speed Sensor ABS Axle 3 Right (S3B)",
    (6, 5): "Wheel Speed Sensor ABS Axle 3 Right (S3B)",
    (6, 13): "Wheel Speed Sensor ABS Axle 3 Right (S3B)",
    # --- Modulator valves (pressure / hold / dump solenoids) -------------- #
    (7, 7): "Pressure Modulator Valve ABS Axle 1",
    (9, 7): "Pressure Modulator Valve ABS Axle 2",
    (42, 3): "Hold Modulator Valve ABS Axle 1",
    (42, 4): "Hold Modulator Valve ABS Axle 1",
    (42, 5): "Hold Modulator Valve ABS Axle 1",
    (44, 3): "Hold Modulator Valve ABS Axle 2",
    (44, 4): "Hold Modulator Valve ABS Axle 2",
    (44, 5): "Hold Modulator Valve ABS Axle 2",
    (48, 3): "Dump Modulator Valve ABS Axle 1",
    (48, 4): "Dump Modulator Valve ABS Axle 1",
    (48, 5): "Dump Modulator Valve ABS Axle 1",
    (50, 3): "Dump Modulator Valve ABS Axle 2",
    (50, 4): "Dump Modulator Valve ABS Axle 2",
    (50, 5): "Dump Modulator Valve ABS Axle 2",
    # --- ECU / power / memory --------------------------------------------- #
    (13, 11): "Retarder Control Relay (ABS internal relay)",
    (13, 12): "Retarder Control Relay (ABS internal relay)",
    (251, 1): "Power Supply",
    (251, 3): "Power Supply",
    (251, 4): "Power Supply",
    (253, 12): "Calibration Memory",
    # --- ITCM additions ----------------------------------------------------- #
    # The ITCM family reuses SID 45/51 for its second modulator channel and
    # SID 218 for the ECM main relay - SIDs absent from the PLC Select tables.
    # SIDs 44/50 are deliberately NOT re-added: PLC Select uses them for the
    # second axle while ITCM uses them for the first channel, so the existing
    # channel-neutral axle names stay authoritative.
    (45, 3): "Hold Modulator Valve (22 Channel)",
    (45, 4): "Hold Modulator Valve (22 Channel)",
    (45, 5): "Hold Modulator Valve (22 Channel)",
    (51, 3): "Dump Modulator Valve (22 Channel)",
    (51, 4): "Dump Modulator Valve (22 Channel)",
    (51, 5): "Dump Modulator Valve (22 Channel)",
    (218, 11): "ECM Main Relay",
    (251, 0): "Power Supply",
}