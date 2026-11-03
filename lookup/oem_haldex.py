"""OpenTruck - Haldex trailer ABS fault-code table.

J1587 SID+FMI -> Haldex-specific short component name, keyed from the Haldex
PLC Select 1M/2M trailer ABS "SAE J1587/J1708 Fault Codes" tables in the
PLC Select Installation/Service Guide (document L30041). The table covers the
PLC Select 1M (2S/1M) and 2M (2S/2M and 4S/2M) trailer ABS ECU family.

Only the short, factual component name is kept here; the OEM's verbatim
failure-mode wording is intentionally NOT redistributed. The FMI failure
phrase is supplied generically at display time from ``spn.FMI``
(SAE J1939-73), so the rendered description stays correct.

The guide's sensor-position notes (curb/road side) and modulator channel
(Red/Blue/Yellow) depend on the configured variant and conflict between the
1M and 2M tables for shared SIDs, so the names here are channel-neutral.
"""

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
}