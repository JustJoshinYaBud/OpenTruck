"""OpenTruck - SAE J1587 PID lookup tables.

Deliberately SEPARATE from the J1939 SPN table in ``spn.py``. J1587 (the
application layer carried on J1708) identifies parameters with a one-byte PID
(0..255), while J1939 uses 19-bit SPNs - different namespaces. Name lookups in
``j1708.py`` consult *this* table first and then fall back to the J1939 SPN
table (``spn.SPN_NAMES``) so a number present in either registry still resolves
to a human-readable name.

Source: SAE J1587 (Revised FEB2002), Table 2 (PID assignment list) for names
and Appendix A for scaling. These are standardized facts (the same way the SPN
names in ``spn.py`` are). Values are decoded straight into canonical SI/metric
units (kPa, degC, km/h, L, L/h, kg/h, ...) so the shared ``units.convert``
display converter works for J1587 live data exactly as it does for J1939.

DISCLAIMER: The data in this file is a compilation assembled from sources
found through ordinary internet search (standards documents, public service
documentation and similar material). It is not an official publication of
SAE International, ISO or any vehicle, engine or component manufacturer,
and the OpenTruck project has no affiliation with, sponsorship from, or
endorsement by any of them; all brand names are the property of their
respective owners. The contents may be inaccurate, incomplete or out of
date and are provided as-is, without warranty of any kind.
"""
from __future__ import annotations

from typing import Optional


# J1587 PID -> parameter name (SAE J1587-2002, Table 2). Auto-extracted from the standard.
PID_NAMES = {
    0: "Request Parameter",
    1: "Invalid Data Parameter",
    2: "Transmitter System Status",
    3: "Transmitter System Diagnostic",
    4: "Reserved",
    5: "Underrange Warning Condition",
    6: "Overrange Warning Condition",
    7: "Axle #2 Lift Air Pressure",
    8: "Brake System Air Pressure Low Warning Switch Status",
    9: "Axle Lift Status",
    10: "Axle Slider Status",
    11: "Cargo Securement",
    12: "Brake Stroke Status",
    13: "Entry Assist Position/Deployment",
    14: "Entry Assist Motor Current",
    15: "Fuel Supply Pump Inlet Pressure",
    16: "Suction Side Fuel Filter Differential Pressure",
    17: "Engine Oil Level Remote Reservoir",
    18: "Extended Range Fuel Pressure",
    19: "Extended Range Engine Oil Pressure",
    20: "Extended Range Engine Coolant Pressure",
    21: "Engine ECU Temperature",
    22: "Extended Engine Crankcase Blow-by Pressure",
    23: "Generator Oil Pressure",
    24: "Generator Coolant Temperature",
    25: "Air Conditioner System Status #2",
    26: "Estimated Percent Fan Speed",
    27: "Percent Exhaust Gas Recirculation Valve #1 Position",
    28: "Percent Accelerator Position #3",
    29: "Percent Accelerator Position #2",
    30: "Crankcase Blow-by Pressure",
    31: "Transmission Range Position",
    32: "Transmission Splitter Position",
    33: "Clutch Cylinder Position",
    34: "Clutch Cylinder Actuator Status",
    35: "Shift Finger Actuator Status #2",
    36: "Clutch Plates Wear Condition",
    37: "Transmission Tank Air Pressure",
    38: "Second Fuel Level (Right Side)",
    39: "Tire Pressure Check Interval",
    40: "Engine Retarder Switches Status",
    41: "Cruise Control Switches Status",
    42: "Pressure Switch Status",
    43: "Ignition Switch Status",
    44: "Attention/Warning Indicator Lamps Status",
    45: "Inlet Air Heater Status",
    46: "Vehicle Wet Tank Pressure",
    47: "Retarder Status",
    48: "Extended Range Barometric Pressure",
    49: "ABS Control Status",
    50: "Air Conditioner System Clutch Status/Command #1",
    51: "Throttle Position",
    52: "Engine Intercooler Temperature",
    53: "Transmission Synchronizer Clutch Value",
    54: "Transmission Synchronizer Brake Value",
    55: "Shift Finger Positional Status",
    56: "Transmission Range Switch Status",
    57: "Transmission Actuator Status #2",
    58: "Shift Finger Actuator Status",
    59: "Shift Finger Gear Position",
    60: "Shift Finger Rail Position",
    61: "Parking Brake Actuator Status",
    62: "Retarder Inhibit Status",
    63: "Transmission Actuator Status #1",
    64: "Direction Switch Status",
    65: "Service Brake Switch Status",
    66: "Vehicle Enabling Component Status",
    67: "Shift Request Switch Status",
    68: "Torque Limiting Factor",
    69: "Two Speed Axle Switch Status",
    70: "Parking Brake Switch Status",
    71: "Idle Shutdown Timer Status",
    72: "Blower Bypass Value Position",
    73: "Auxiliary Water Pump Pressure",
    74: "Maximum Road Speed Limit",
    75: "Steering Axle Temperature",
    76: "Axle #1 Lift Air Pressure",
    77: "Forward Rear Drive Axle Temperature",
    78: "Rear Rear-Drive Axle Temperature",
    79: "Road Surface Temperature",
    80: "Washer Fluid Level",
    81: "Particulate Trap Inlet Pressure",
    82: "Air Start Pressure",
    83: "Road Speed Limit Status",
    84: "Road Speed",
    85: "Cruise Control Status",
    86: "Cruise Control Set Speed",
    87: "Cruise Control High-Set Limit Speed",
    88: "Cruise Control Low-Set Limit Speed",
    89: "Power Takeoff Status",
    90: "PTO Oil Temperature",
    91: "Percent Accelerator Pedal Position",
    92: "Percent Engine Load",
    93: "Output Torque",
    94: "Fuel Delivery Pressure",
    95: "Fuel Filter Differential Pressure",
    96: "Fuel Level",
    97: "Water in Fuel Indicator",
    98: "Engine Oil Level",
    99: "Engine Oil Filter Differential Pressure",
    100: "Engine Oil Pressure",
    101: "Crankcase Pressure",
    102: "Boost Pressure",
    103: "Turbo Speed",
    104: "Turbo Oil Pressure",
    105: "Intake Manifold Temperature",
    106: "Air Inlet Pressure",
    107: "Air Filter Differential Pressure",
    108: "Barometric Pressure",
    109: "Coolant Pressure",
    110: "Engine Coolant Temperature",
    111: "Coolant Level",
    112: "Coolant Filter Differential Pressure",
    113: "Governor Droop",
    114: "Net Battery Current",
    115: "Alternator Current",
    116: "Brake Application Pressure",
    117: "Brake Primary Pressure",
    118: "Brake Secondary Pressure",
    119: "Hydraulic Retarder Pressure",
    120: "Hydraulic Retarder Oil Temperature",
    121: "Engine Retarder Status",
    122: "Engine Retarder Percent",
    123: "Clutch Pressure",
    124: "Transmission Oil Level",
    125: "Transmission Oil Level High/Low",
    126: "Transmission Filter Differential Pressure",
    127: "Transmission Oil Pressure",
    128: "Component-specific request",
    129: "Injector Metering Rail #2 Pressure",
    130: "Power Specific Fuel Economy",
    131: "Exhaust Back Pressure",
    132: "Mass Air Flow",
    133: "Average Fuel Rate",
    134: "Wheel Speed Sensor Status",
    135: "Extended Range Fuel Delivery Pressure (Absolute)",
    136: "Auxiliary Vacuum Pressure Reading",
    137: "Auxiliary Gage Pressure Reading #1",
    138: "Auxiliary Absolute Pressure Reading",
    139: "Tire Pressure Control System Channel Functional Mode",
    140: "Tire Pressure Control System Solenoid Status",
    141: "Trailer #1, Tag #1, or Push Channel #1 Tire Pressure Target",
    142: "Drive Channel Tire Pressure Target",
    143: "Steer Channel Tire Pressure Target",
    144: "Trailer #1, Tag #1, or Push Channel #1 Tire Pressure",
    145: "Drive Channel Tire Pressure",
    146: "Steer Channel Tire Pressure",
    147: "Average Fuel Economy (Natural Gas)",
    148: "Instantaneous Fuel Economy (Natural Gas)",
    149: "Fuel Mass Flow Rate (Natural Gas)",
    150: "PTO Engagement Control Status",
    151: "ATC Control Status",
    152: "Number of ECU Resets",
    153: "Crankcase Pressure",
    154: "Auxiliary Input and Output Status #2",
    155: "Auxiliary Input and Output Status #1",
    156: "Injector Timing Rail Pressure",
    157: "Injector Metering Rail Pressure",
    158: "Battery Potential (Voltage)—Switched",
    159: "Gas Supply Pressure",
    160: "Main Shaft Speed",
    161: "Input Shaft Speed",
    162: "Transmission Range Selected",
    163: "Transmission Range Attained",
    164: "Injection Control Pressure",
    165: "Compass Bearing",
    166: "Rated Engine Power",
    167: "Alternator Potential (Voltage)",
    168: "Battery Potential (Voltage)",
    169: "Cargo Ambient Temperature",
    170: "Cab Interior Temperature",
    171: "Ambient Air Temperature",
    172: "Air Inlet Temperature",
    173: "Exhaust Gas Temperature",
    174: "Fuel Temperature",
    175: "Engine Oil Temperature",
    176: "Turbo Oil Temperature",
    177: "Transmission #1 Oil Temperature",
    178: "Front Axle Weight",
    179: "Rear Axle Weight",
    180: "Trailer Weight",
    181: "Cargo Weight",
    182: "Trip Fuel",
    183: "Fuel Rate (Instantaneous)",
    184: "Instantaneous Fuel Economy",
    185: "Average Fuel Economy",
    186: "Power Takeoff Speed",
    187: "Power Takeoff Set Speed",
    188: "Idle Engine Speed",
    189: "Rated Engine Speed",
    190: "Engine Speed",
    191: "Transmission Output Shaft Speed",
    192: "Multisection Parameter",
    193: "Transmitter System Diagnostic Table",
    194: "Transmitter System Diagnostic Code and Occurrence Count Table",
    195: "Diagnostic Data Request/Clear Count",
    196: "Diagnostic Data/Count Clear Response",
    197: "Connection Management",
    198: "Connection Mode Data Transfer",
    199: "Traction Control Disable State",
    209: "ABS Control Status, Trailer",
    210: "Tire Temperature (By Sequence Number)",
    211: "Tire Pressure (By Sequence Number)",
    212: "Tire Pressure Target (By Sequence Number)",
    213: "Wheel End Assembly Vibration Level",
    214: "Vehicle Wheel Speeds",
    215: "Brake Temperature",
    216: "Wheel Bearing Temperature",
    217: "Fuel Tank/Nozzle Identification",
    218: "State Line Crossing",
    219: "Current State and Country",
    220: "Engine Torque History",
    221: "Anti-theft Request",
    222: "Anti-theft Status",
    223: "Auxiliary A/D Counts",
    224: "Immobilizer Security Code",
    225: "Reserved for Text Message Acknowledged",
    226: "Reserved for Text Message to Display",
    227: "Reserved for Text Message Display Type",
    228: "Speed Sensor Calibration",
    229: "Total Fuel Used (Natural Gas)",
    230: "Total Idle Fuel Used (Natural Gas)",
    231: "Trip Fuel (Natural Gas)",
    232: "DGPS Differential Correction",
    233: "Unit Number (Power Unit)",
    234: "Software Identification",
    235: "Total Idle Hours",
    236: "Total Idle Fuel Used",
    237: "Vehicle Identification Number",
    238: "Velocity Vector",
    239: "Vehicle Position",
    240: "Change Reference Number",
    241: "Tire Pressure by Position",
    242: "Tire Temperature by Position",
    243: "Component Identification",
    244: "Trip Distance",
    245: "Total Vehicle Distance",
    246: "Total Vehicle Hours",
    247: "Total Engine Hours",
    248: "Total PTO Hours",
    249: "Total Engine Revolutions",
    250: "Total Fuel Used",
    251: "Clock",
    252: "Date",
    253: "Elapsed Time",
    254: "Data Link Escape",
    255: "Extension",
    # --- Page 2 (PIDs 256-511, transmitted behind extension PID 255) ---------
    # Only the assigned PIDs are listed; the standard's reserved ranges
    # (260-361, 385-405, 451-497) have no entry. Scaling for page 2 is added
    # incrementally; an entry with no PID_SCALE shows its raw value.
    256: "Request Parameter",
    257: "Cold Restart of Specific Component",
    258: "Warm Restart of Specific Component",
    259: "Component Restart Response",
    362: "Percent Exhaust Gas Recirculation Valve #2 Position",
    363: "Hydraulic Retarder Control Air Pressure",
    364: "HVAC Unit Discharge Temperature",
    365: "Weighing System Status Command",
    366: "Engine Oil Level High/Low",
    367: "Lane Tracking System Status",
    368: "Lane Departure Indication",
    369: "Distance to Rear Object (Reverse)",
    370: "Trailer Pneumatic Brake Control Line Pressure",
    371: "Trailer Pneumatic Supply Line Pressure",
    372: "Remote Accelerator",
    373: "Center Rear Drive Axle Temperature",
    374: "Alternator AC Voltage",
    375: "Fuel Return Pressure",
    376: "Fuel Pump Inlet Vacuum",
    377: "Compression Unbalance",
    378: "Fare Collection Unit Status",
    379: "Door Status",
    380: "Articulation Angle",
    381: "Vehicle Use Status",
    382: "Transit Silent Alarm Status",
    383: "Vehicle Acceleration",
    384: "Component-specific request",
    406: "HVAC Blower Motor Speed",
    407: "Axle Group Full Weight Calibration",
    408: "Axle Group Empty Weight Calibration",
    409: "Axle Group Weight",
    410: "Extended Range Road Surface Temperature",
    411: "Recirculated Engine Exhaust Gas Differential Pressure",
    412: "Recirculated Engine Exhaust Gas Temperature",
    413: "Net Vehicle Weight Change",
    414: "Air Conditioner Refrigerant Low Side Pressure",
    415: "Air Conditioner Refrigerant High Side Pressure",
    416: "Evaporator Temperature",
    417: "Gross Vehicle Weight",
    418: "Transmission # 2 Oil Temperature",
    419: "Starter Circuit Resistance",
    420: "Starter Current (Average)",
    421: "Alternator/Generator Negative Cable Voltage",
    422: "Auxiliary Current",
    423: "Extended Range Net Battery Current",
    424: "DC Voltage",
    425: "Auxiliary Frequency",
    426: "Alternator/Generator Field Voltage",
    427: "Battery Resistance Change",
    428: "Battery Internal Resistance",
    429: "Starter Current Peak",
    430: "Starter Solenoid Voltage",
    431: "Starter Negative Cable Voltage",
    432: "Starter Motor Voltage",
    433: "Fuel Shutoff Solenoid Voltage",
    434: "AC Voltage",
    435: "Cargo Ambient Temperature (By location)",
    436: "Trip Sudden Decelerations",
    437: "Trailer #2, Tag #2, or Push Channel #2 Tire Pressure Target",
    438: "Trailer #2, Tag #2, or Push Channel #2 Tire Pressure",
    439: "Extended Range Boost Pressure #1",
    440: "Extended Range Boost Pressure #2",
    441: "Auxiliary Temperature #1",
    442: "Auxiliary Temperature #2",
    443: "Auxiliary Gage Pressure Reading #2",
    444: "Battery #2 Potential (Voltage)",
    445: "Cylinder  Head Temperature Bank B (right bank)",
    446: "Cylinder Head Temperature Bank A (left bank)",
    447: "Passenger Counter",
    448: "Page 2 Multisection Parameter",
    449: "Reporting Interval Request",
    450: "Bridge Filter Control",
    498: "Send Keypress Command",
    499: "Driver Interface Unit (DIU) Object/Form Command",
    500: "Intersection Preemption Status and Configuration",
    501: "Signage Message",
    502: "Fare Collection Unit\u2014Point of Sale",
    503: "Fare Collection Unit\u2014Service Detail",
    504: "Annunciator Voice Message",
    505: "Vehicle Control Head Keyboard Message",
    506: "Vehicle Control Head Display Message",
    507: "Driver Identification",
    508: "Transit Route Identification",
    509: "Mile Post Identification",
    510: "Page 2 Data Link Escape",
    511: "Page 2 Extension",
}

# --- PID scaling, raw -> canonical SI/metric --------------------------------- #
# pid -> (scale, offset, unit, signed). ``signed`` selects two's-complement
# decoding (J1587 sends signed integers two's-complement, LSB first). Only PIDs
# whose Appendix-A scaling is known are listed; a PID without an entry is shown
# as its raw integer value with no unit (e.g. bit-mapped status PIDs), so
# nothing is silently invented.
#
# J1587 transmits temperatures in degrees Fahrenheit, so the linear map to the
# canonical degC used by units.py is  C = raw*scale_F*(5/9) - 32*(5/9).
_F = 5.0 / 9.0                 # degF per-bit -> degC per-bit factor
_F_OFF = -32.0 * (5.0 / 9.0)   # -17.777... : the -32 degF offset expressed in degC

PID_SCALE: dict[int, tuple[float, float, str, bool]] = {
    21:  (2.5 * _F, _F_OFF, "\u00b0C", True),   # Engine ECU temperature
    27:  (0.5, 0.0, "%", False),
    # J1587 A.29: percent accelerator position #2, 1 char, 0.4%/bit, 0-102%.
    29:  (0.4, 0.0, "%", False),
    51:  (0.4, 0.0, "%", False),
    52:  (1.0 * _F, _F_OFF, "\u00b0C", False),  # Engine intercooler temperature
    68:  (0.5, 0.0, "%", False),                 # Torque limiting factor
    77:  (1.2 * _F, _F_OFF, "\u00b0C", False),
    78:  (1.2 * _F, _F_OFF, "\u00b0C", False),
    84:  (0.805, 0.0, "km/h", False),            # Road speed
    86:  (0.805, 0.0, "km/h", False),            # Cruise control set speed
    90:  (1.2 * _F, _F_OFF, "\u00b0C", False),  # PTO oil temperature
    91:  (0.4, 0.0, "%", False),
    92:  (0.5, 0.0, "%", False),
    94:  (3.45, 0.0, "kPa", False),
    95:  (1.724, 0.0, "kPa", False),
    96:  (0.5, 0.0, "%", False),
    98:  (0.5, 0.0, "%", False),
    99:  (0.431, 0.0, "kPa", False),
    100: (3.45, 0.0, "kPa", False),
    101: (0.862, 0.0, "kPa", True),
    102: (0.862, 0.0, "kPa", False),
    103: (500.0, 0.0, "rpm", False),             # Turbo speed
    104: (4.14, 0.0, "kPa", False),
    105: (1.0 * _F, _F_OFF, "\u00b0C", False),  # Intake manifold temperature
    106: (1.724, 0.0, "kPa", False),
    107: (0.0498, 0.0, "kPa", False),
    108: (0.431, 0.0, "kPa", False),
    109: (0.862, 0.0, "kPa", False),
    110: (1.0 * _F, _F_OFF, "\u00b0C", False),  # Engine coolant temperature
    111: (0.5, 0.0, "%", False),
    113: (2.0, 0.0, "rpm", False),
    114: (1.2, 0.0, "A", True),                  # Net battery current
    115: (1.2, 0.0, "A", False),
    116: (4.14, 0.0, "kPa", False),
    117: (4.14, 0.0, "kPa", False),
    118: (4.14, 0.0, "kPa", False),
    120: (2.0 * _F, _F_OFF, "\u00b0C", False),
    122: (0.5, 0.0, "%", False),
    124: (0.5, 0.0, "%", False),
    125: (0.473, 0.0, "L", True),                # Transmission oil level hi/lo
    126: (1.724, 0.0, "kPa", False),
    127: (13.8, 0.0, "kPa", False),
    129: (0.689, 0.0, "kPa", False),             # Injector metering rail #2
    131: (0.006733, 0.0, "kPa", False),          # Exhaust back pressure
    132: (7.5, 0.0, "kg/h", False),              # Mass air flow (0.125 kg/min)
    133: (0.0591408, 0.0, "L/h", False),         # Average fuel rate
    135: (0.689, 0.0, "kPa", False),
    136: (0.689, 0.0, "kPa", False),
    137: (0.689, 0.0, "kPa", False),
    138: (0.689, 0.0, "kPa", False),
    149: (0.125, 0.0, "kg/h", False),            # NG fuel mass flow
    158: (0.05, 0.0, "V", False),
    160: (0.25, 0.0, "rpm", False),
    161: (0.25, 0.0, "rpm", False),
    164: (3.90625, 0.0, "kPa", False),           # Injection control (1/256 MPa)
    166: (0.745, 0.0, "kW", False),              # Rated engine power
    167: (0.05, 0.0, "V", False),
    168: (0.05, 0.0, "V", False),
    169: (0.25 * _F, _F_OFF, "\u00b0C", True),
    170: (0.25 * _F, _F_OFF, "\u00b0C", True),
    171: (0.25 * _F, _F_OFF, "\u00b0C", True),
    172: (0.25 * _F, _F_OFF, "\u00b0C", True),  # Air inlet temperature
    173: (0.25 * _F, _F_OFF, "\u00b0C", True),
    174: (0.25 * _F, _F_OFF, "\u00b0C", True),
    175: (0.25 * _F, _F_OFF, "\u00b0C", True),  # Engine oil temperature
    176: (0.25 * _F, _F_OFF, "\u00b0C", True),
    177: (0.25 * _F, _F_OFF, "\u00b0C", True),  # Transmission #1 oil temperature
    183: (0.0591408, 0.0, "L/h", False),         # Fuel rate (instantaneous)
    184: (0.00166072, 0.0, "km/L", False),       # Instantaneous fuel economy
    185: (0.00166072, 0.0, "km/L", False),       # Average fuel economy
    186: (0.25, 0.0, "rpm", False),
    187: (0.25, 0.0, "rpm", False),
    188: (0.25, 0.0, "rpm", False),
    189: (0.25, 0.0, "rpm", False),
    190: (0.25, 0.0, "rpm", False),              # Engine speed
    191: (0.25, 0.0, "rpm", False),              # Transmission output shaft speed
    236: (0.473, 0.0, "L", False),               # Total idle fuel used
    244: (0.16, 0.0, "km", False),               # Trip distance
    245: (0.161, 0.0, "km", False),              # Total vehicle distance
    246: (0.05, 0.0, "h", False),                # Total vehicle hours
    247: (0.05, 0.0, "h", False),                # Total engine hours
    248: (0.05, 0.0, "h", False),                # Total PTO hours
    249: (1000.0, 0.0, "rev", False),            # Total engine revolutions
    250: (0.473, 0.0, "L", False),                # Total fuel used
    # --- Page 2 scaling (PIDs 256-511; SAE J1587 Appendix A.256-511) ------
    # Temperatures are in degF: converted to canonical degC via _F/_F_OFF.
    # Pressures/vacuum given in psi/inHg by the standard are converted to kPa
    # so the shared units.convert() display path works. Bit-mapped status,
    # ASCII, and command PIDs are intentionally omitted (raw with a name).
    362: (0.5, 0.0, "%", False),                  # EGR valve #2 position
    363: (4.13725, 0.0, "kPa", False),            # Hydraulic retarder control air pressure
    364: (2.5 * _F, _F_OFF, "\u00b0C", True),     # HVAC unit discharge temperature
    366: (0.473333, 0.0, "L", True),              # Engine oil level high/low
    369: (0.0980392, 0.0, "m", False),            # Distance to rear object
    370: (4.13725, 0.0, "kPa", False),            # Trailer pneumatic brake control line pressure
    371: (4.13725, 0.0, "kPa", False),            # Trailer pneumatic supply line pressure
    372: (0.4, 0.0, "%", False),                  # Remote accelerator
    373: (1.2 * _F, _F_OFF, "\u00b0C", False),    # Center rear drive axle temperature
    374: (0.125, 0.0, "V", False),                # Alternator AC voltage
    375: (3.44738, 0.0, "kPa", False),            # Fuel return pressure (0.5 psi)
    376: (0.677278, 0.0, "kPa", False),           # Fuel pump inlet vacuum (0.2 inHg)
    377: (0.5, 0.0, "%", False),                  # Compression unbalance
    406: (0.25, 0.0, "rpm", False),               # HVAC blower motor speed
    410: (0.25 * _F, _F_OFF, "\u00b0C", True),    # Extended range road surface temperature
    411: (0.00765991, 0.0, "kPa", True),         # Recirculated EGR differential pressure
    412: (0.25 * _F, _F_OFF, "\u00b0C", True),    # Recirculated EGR temperature
    414: (1.37894, 0.0, "kPa", True),            # AC refrigerant low side pressure
    415: (1.37894, 0.0, "kPa", True),            # AC refrigerant high side pressure
    416: (0.25 * _F, _F_OFF, "\u00b0C", True),    # Evaporator temperature
    418: (0.25 * _F, _F_OFF, "\u00b0C", True),    # Transmission #2 oil temperature
    420: (0.125, 0.0, "A", False),                # Starter current (average)
    421: (0.0001, 0.0, "V", False),               # Alt/gen negative cable voltage
    422: (0.125, 0.0, "A", True),                 # Auxiliary current
    423: (0.125, 0.0, "A", True),                 # Extended range net battery current
    424: (0.05, 0.0, "V", False),                 # DC voltage
    425: (0.1, 0.0, "Hz", False),                 # Auxiliary frequency
    426: (0.05, 0.0, "V", False),                 # Alt/gen field voltage
    429: (0.125, 0.0, "A", False),                # Starter current peak
    430: (0.05, 0.0, "V", False),                 # Starter solenoid voltage
    431: (0.0001, 0.0, "V", False),               # Starter negative cable voltage
    432: (0.05, 0.0, "V", False),                 # Starter motor voltage
    433: (0.05, 0.0, "V", False),                 # Fuel shutoff solenoid voltage
    434: (0.125, 0.0, "V", False),                # AC voltage
    437: (0.689, 0.0, "kPa", False),              # Trailer #2 tire pressure target
    438: (0.689, 0.0, "kPa", False),              # Trailer #2 tire pressure
    439: (0.125, 0.0, "kPa", False),              # Extended range boost pressure #1
    440: (0.125, 0.0, "kPa", False),              # Extended range boost pressure #2
    441: (0.1 * _F, _F_OFF, "\u00b0C", True),     # Auxiliary temperature #1
    442: (0.1 * _F, _F_OFF, "\u00b0C", True),     # Auxiliary temperature #2
    443: (0.689, 0.0, "kPa", False),              # Auxiliary gauge pressure reading #2
    445: (0.25 * _F, _F_OFF, "\u00b0C", True),    # Cylinder head temperature bank B
    446: (0.25 * _F, _F_OFF, "\u00b0C", True),    # Cylinder head temperature bank A
    # --- Appendix A numeric scalings (generated + max-range validated) -----
    # scale/offset derived from each PID's Appendix-A max range and bit width;
    # degF->degC via _F/_F_OFF, psi/inHg->kPa, mph->km/h, N->kg, N.m->Nm.
    # Multi-field records (210-213,215,216,238,241,242) are NOT here (they need
    # a per-field decoder, not a single linear scale).
    7: (4.13725, 0, "kPa", False),  # Axle #2 Lift Air Pressure
    13: (0.4, 0, "%", False),  # Entry Assist Position/Deployment
    14: (0.04, 0, "A", False),  # Entry Assist Motor Current
    15: (1.72353, 0, "kPa", False),  # Fuel Supply Pump Inlet Pressure
    16: (1.72353, 0, "kPa", False),  # Suction Side Fuel Filter Differential
    17: (0.5, 0, "%", False),  # Engine Oil Level Remote Reservoir
    18: (4, 0, "kPa", False),  # Extended Range Fuel Pressure
    19: (4, 0, "kPa", False),  # Extended Range Engine Oil Pressure
    20: (2, 0, "kPa", False),  # Extended Range Engine Coolant Pressure
    22: (0.0292749, 0, "kPa", False),  # Extended Engine Crankcase Blow-by
    23: (3.44706, 0, "kPa", False),  # Generator Oil Pressure
    24: (0.555556, -17.7778, "\u00b0C", False),  # Generator Coolant Temperature
    26: (0.4, 0, "%", False),  # Estimated Percent Fan Speed
    28: (0.4, 0, "%", False),  # Percent Accelerator Position #3
    30: (0.860784, 0.180392, "kPa", True),  # Crankcase Blow-by Pressure
    31: (0.4, 0, "%", False),  # Transmission Range Position
    32: (0.4, 0, "%", False),  # Transmission Splitter Position
    33: (0.4, 0, "%", False),  # Clutch Cylinder Position
    36: (0.4, 0, "%", False),  # Clutch Plates Wear Condition
    37: (6.8902, 0, "kPa", False),  # Transmission Tank Air Pressure
    38: (0.5, 0, "%", False),  # Second Fuel Level (Right Side)
    39: (1, 0, "min", False),  # Tire Pressure Check Interval
    46: (6.8902, 0, "kPa", False),  # Vehicle Wet Tank Pressure
    48: (0.6, 0, "kPa", False),  # Extended Range Barometric Pressure
    53: (0.4, 0, "%", False),  # Transmission Synchronizer Clutch Value
    54: (0.4, 0, "%", False),  # Transmission Synchronizer Brake Value
    59: (0.4, 0, "%", False),  # Shift Finger Gear Position
    60: (0.4, 0, "%", False),  # Shift Finger Rail Position
    72: (0.4, 0, "%", False),  # Blower Bypass Value Position
    73: (13.7882, 0, "kPa", False),  # Auxiliary Water Pump Pressure
    74: (0.804706, 0, "km/h", False),  # Maximum Road Speed Limit
    75: (0.666667, -17.7778, "\u00b0C", False),  # Steering Axle Temperature
    76: (4.13725, 0, "kPa", False),  # Axle #1 Lift Air Pressure
    79: (1.38889, -17.7778, "\u00b0C", True),  # Road Surface Temperature
    80: (0.5, 0, "%", False),  # Washer Fluid Level
    81: (0.16902, 0, "kPa", False),  # Particulate Trap Inlet Pressure
    82: (4.13725, 0, "kPa", False),  # Air Start Pressure
    87: (0.804706, 0, "km/h", False),  # Cruise Control High-Set Limit Speed
    88: (0.804706, 0, "km/h", False),  # Cruise Control Low-Set Limit Speed
    93: (27.1176, 0.0588235, "Nm", True),  # Output Torque
    112: (0.43098, 0, "kPa", False),  # Coolant Filter Differential Pressure
    119: (4.13725, 0, "kPa", False),  # Hydraulic Retarder Pressure
    123: (13.7882, 0, "kPa", False),  # Clutch Pressure
    141: (0.689, 0, "kPa", False),  # Trailer #1/Tag #1/Push Ch#1 Tire Pressure Target
    142: (0.689, 0, "kPa", False),  # Drive Channel Tire Pressure Target
    143: (0.689, 0, "kPa", False),  # Steer Channel Tire Pressure Target
    144: (0.689, 0, "kPa", False),  # Trailer #1/Tag #1/Push Ch#1 Tire Pressure
    145: (0.689, 0, "kPa", False),  # Drive Channel Tire Pressure
    146: (0.689, 0, "kPa", False),  # Steer Channel Tire Pressure
    153: (0.00781247, -0.00109377, "kPa", True),  # Crankcase Pressure
    156: (0.689, 0, "kPa", False),  # Injector Timing Rail Pressure
    157: (0.689, 0, "kPa", False),  # Injector Metering Rail Pressure
    159: (0.345, 0, "kPa", False),  # Gas Supply Pressure
    165: (0.01, 0, "deg", False),  # Compass Bearing
    178: (0.453592, 0, "kg", False),  # Front Axle Weight
    179: (0.453592, 0, "kg", False),  # Rear Axle Weight
    180: (1.81437, 0, "kg", False),  # Trailer Weight
    181: (1.81437, 0, "kg", False),  # Cargo Weight
    182: (0.473176, 0, "L", False),  # Trip Fuel
    235: (0.05, 0, "h", False),  # Total Idle Hours
    380: (1, 0, "deg", True),  # Articulation Angle
    407: (1.81437, 0, "kg", False),  # Axle Group Full Weight Calibration
    408: (1.81437, 0, "kg", False),  # Axle Group Empty Weight Calibration
    409: (1.81437, 0, "kg", False),  # Axle Group Weight
    413: (1.81437, 1.78414, "kg", True),  # Net Vehicle Weight Change
    417: (1.81437, 0, "kg", False),  # Gross Vehicle Weight
}


def pid_name(pid: int) -> Optional[str]:
    """Name for a J1587 PID from the J1587 table, or ``None`` if unknown."""
    return PID_NAMES.get(pid)


def pid_scale(pid: int) -> Optional[tuple[float, float, str, bool]]:
    """``(scale, offset, unit, signed)`` for a J1587 PID, or ``None``."""
    return PID_SCALE.get(pid)


# ============================================================================
_STATUS2 = {0: "off", 1: "on", 2: "error", 3: "not avail"}

PID_BITS = {
    # J1587 A.25 "Air Conditioner System Status #2": four 2-bit state
    # fields, each with its own 00/01 wording (10 = error, 11 = not
    # available). Uses the ('states', w0, w1, w2, w3) kind because the
    # standard's words differ per field (not the generic off/on).
    25: [
        (0, 0xC0, 6, 'Compressor discharge high pressure',
         ('states', 'not at high pressure', 'at high pressure',
          'error', 'not available')),
        (0, 0x30, 4, 'Compressor discharge very high pressure',
         ('states', 'not at very high pressure', 'at very high pressure',
          'error', 'not available')),
        (0, 0x0C, 2, 'Compressor suction low pressure',
         ('states', 'not at low pressure', 'at low pressure',
          'error', 'not available')),
        (0, 0x03, 0, 'Evaporator temperature',
         ('states', 'above low-temp set point', 'below low-temp set point',
          'error', 'not available')),
    ],
    # J1587 A.70: bit 8 = parking brake switch (1=active, 0=inactive);
    # bits 7-1 undefined.
    70: [
        (0, 0x80, 7, 'Parking brake switch', ('bool', 'Active', 'Inactive')),
    ],
    # J1587 A.40 "Engine Retarder Switches Status": bits 6-3 are a 4-bit
    # retarder level (0-8 = number of retarded cylinders, 9-13 reserved,
    # 14 = error, 15 = not available); bits 2-1 are a 2-bit switch status.
    40: [
        (0, 0x3C, 2, 'Engine retarder level switch',
         ('map', ('0 cylinders', '1 cylinder', '2 cylinders', '3 cylinders',
                  '4 cylinders', '5 cylinders', '6 cylinders', '7 cylinders',
                  '8 cylinders', None, None, None, None, None,
                  'error', 'not available'))),
        (0, 3, 0, 'Engine retarder switch', 'status'),
    ],
    41: [
        (0, 48, 4, 'Cruise on/off switch', 'status'),
        (0, 12, 2, 'Cruise set switch', 'status'),
        (0, 3, 0, 'Cruise resume switch', 'status'),
    ],
    42: [
        (0, 3, 0, 'Tire pressure supply switch', 'status'),
    ],
    43: [
        (0, 192, 6, 'Start aid contacts', 'status'),
        (0, 48, 4, 'Crank contacts', 'status'),
        (0, 12, 2, 'Run contacts', 'status'),
        (0, 3, 0, 'Accessory contacts', 'status'),
    ],
    44: [
        (0, 48, 4, 'Protect lamp', 'status'),
        (0, 12, 2, 'Amber lamp', 'status'),
        (0, 3, 0, 'Red lamp', 'status'),
    ],
    45: [
        (0, 48, 4, 'Wait to Start lamp', 'status'),
        (0, 12, 2, 'Heater 2', 'status'),
        (0, 3, 0, 'Heater 1', 'status'),
    ],
    47: [
        (0, 3, 0, 'Transmission output retarder', 'status'),
    ],
    49: [
        (0, 192, 6, 'ABS off-road switch', 'status'),
        (0, 48, 4, 'ABS retarder control', 'status'),
        (0, 12, 2, 'ABS brake control', 'status'),
        (0, 3, 0, 'ABS warning lamp', 'status'),
    ],
    50: [
        (0, 192, 6, 'Engine fan request', 'status'),
        (0, 48, 4, 'A/C request input', 'status'),
        (0, 12, 2, 'Temporary clutch disengage', 'status'),
    ],
    55: [
        (0, 48, 4, 'Center rail sense', 'status'),
        (0, 3, 0, 'Neutral sense', 'status'),
    ],
    56: [
        (0, 12, 2, 'Low range', 'status'),
        (0, 3, 0, 'High range', 'status'),
    ],
    57: [
        (0, 192, 6, 'Inertia brake actuator', 'status'),
        (0, 48, 4, 'Defuel actuator', 'status'),
        (0, 12, 2, 'Lockup clutch actuator', 'status'),
        (0, 3, 0, 'Clutch actuator', 'status'),
    ],
    61: [
        (0, 12, 2, 'Parking brake off actuator', 'status'),
        (0, 3, 0, 'Parking brake on actuator', 'status'),
    ],
    62: [
        (0, 3, 0, 'Retarder inhibit', 'status'),
    ],
    63: [
        (0, 192, 6, 'Splitter indirect actuator', 'status'),
        (0, 48, 4, 'Splitter direct actuator', 'status'),
        (0, 12, 2, 'Range low actuator', 'status'),
        (0, 3, 0, 'Range high actuator', 'status'),
    ],
    64: [
        (0, 48, 4, 'Forward switch', 'status'),
        (0, 12, 2, 'Neutral switch', 'status'),
        (0, 3, 0, 'Reverse switch', 'status'),
    ],
    65: [
        (0, 12, 2, 'Brake system switch', 'status'),
        (0, 3, 0, 'Service brake switch', 'status'),
    ],
    66: [
        (0, 48, 4, 'Power connect device', 'status'),
        (0, 12, 2, 'Start enable device', 'status'),
        (0, 3, 0, 'Ignition switch', 'status'),
    ],
    67: [
        (0, 12, 2, 'Downshift switch', 'status'),
        (0, 3, 0, 'Upshift switch', 'status'),
    ],
    69: [
        (0, 128, 7, 'Two Speed Axle', ('bool', 'low range', 'high range')),
    ],
    71: [
        (0, 128, 7, 'Idle shutdown timer', ('bool', 'active', 'inactive')),
        (0, 8, 3, 'Idle shutdown function', ('bool', 'enabled in cal', 'disabled')),
        (0, 4, 2, 'Idle shutdown override', ('bool', 'active', 'inactive')),
        (0, 2, 1, 'Engine shutdown by idle timer', ('bool', 'yes', 'no')),
        (0, 1, 0, 'Driver alert mode', ('bool', 'active', 'inactive')),
    ],
    83: [
        (0, 128, 7, 'Road speed limit', ('bool', 'active', 'not active')),
    ],
    85: [
        (0, 128, 7, 'Cruise mode', ('bool', 'active', 'not active')),
        (0, 64, 6, 'Clutch switch', ('bool', 'on', 'off')),
        (0, 32, 5, 'Brake switch', ('bool', 'on', 'off')),
        (0, 16, 4, 'Accel switch', ('bool', 'on', 'off')),
        (0, 8, 3, 'Resume switch', ('bool', 'on', 'off')),
        (0, 4, 2, 'Coast switch', ('bool', 'on', 'off')),
        (0, 2, 1, 'Set switch', ('bool', 'on', 'off')),
        (0, 1, 0, 'Cruise control switch', ('bool', 'on', 'off')),
    ],
    89: [
        (0, 128, 7, 'PTO mode', ('bool', 'active', 'not active')),
        (0, 64, 6, 'Clutch switch', ('bool', 'on', 'off')),
        (0, 32, 5, 'Brake switch', ('bool', 'on', 'off')),
        (0, 16, 4, 'Accel switch', ('bool', 'on', 'off')),
        (0, 8, 3, 'Resume switch', ('bool', 'on', 'off')),
        (0, 4, 2, 'Coast switch', ('bool', 'on', 'off')),
        (0, 2, 1, 'Set switch', ('bool', 'on', 'off')),
        (0, 1, 0, 'PTO control switch', ('bool', 'on', 'off')),
    ],
    97: [
        (0, 128, 7, 'Water in fuel', ('bool', 'yes', 'no')),
    ],
    121: [
        (0, 128, 7, 'Engine retarder', ('bool', 'on', 'off')),
        (0, 16, 4, '8 cyl active', ('bool', 'yes', 'no')),
        (0, 8, 3, '6 cyl active', ('bool', 'yes', 'no')),
        (0, 4, 2, '4 cyl active', ('bool', 'yes', 'no')),
        (0, 2, 1, '3 cyl active', ('bool', 'yes', 'no')),
        (0, 1, 0, '2 cyl active', ('bool', 'yes', 'no')),
    ],
    134: [
        (0, 192, 6, 'Axle1 left', 'status'),
        (0, 48, 4, 'Axle2 left', 'status'),
        (0, 12, 2, 'Axle3 left', 'status'),
        (0, 3, 0, 'Axle4 left', 'status'),
        (1, 192, 6, 'Axle1 right', 'status'),
        (1, 48, 4, 'Axle2 right', 'status'),
        (1, 12, 2, 'Axle3 right', 'status'),
        (1, 3, 0, 'Axle4 right', 'status'),
    ],
    139: [
        (0, 15, 0, 'Steer channel mode', 'mode'),
        (1, 240, 4, 'Drive channel mode', 'mode'),
        (1, 15, 0, 'Trailer/tag channel mode', 'mode'),
    ],
    140: [
        (0, 12, 2, 'PCU steer solenoid', 'status'),
        (0, 3, 0, 'PCU drive solenoid', 'status'),
        (1, 192, 6, 'PCU trailer/tag solenoid', 'status'),
        (1, 48, 4, 'PCU supply solenoid', 'status'),
        (1, 12, 2, 'PCU control solenoid', 'status'),
        (1, 3, 0, 'PCU deflate solenoid', 'status'),
    ],
    150: [
        (0, 12, 2, 'PTO#2 engage control switch', 'status'),
        (0, 3, 0, 'PTO#1 engage control switch', 'status'),
        (1, 12, 2, 'PTO#2 engage actuator', 'status'),
        (1, 3, 0, 'PTO#1 engage actuator', 'status'),
    ],
    151: [
        (0, 192, 6, 'ATC spin-out detect', 'status'),
        (0, 48, 4, 'ATC engine control', 'status'),
        (0, 12, 2, 'ATC brake control', 'status'),
        (0, 3, 0, 'ATC status lamp', 'status'),
        (1, 3, 0, 'ATC deep snow/mud switch', 'status'),
    ],
    154: [
        (0, 192, 6, 'Aux input #8', 'status'),
        (0, 48, 4, 'Aux input #7', 'status'),
        (0, 12, 2, 'Aux input #6', 'status'),
        (0, 3, 0, 'Aux input #5', 'status'),
        (1, 192, 6, 'Aux output #8', 'status'),
        (1, 48, 4, 'Aux output #7', 'status'),
        (1, 12, 2, 'Aux output #6', 'status'),
        (1, 3, 0, 'Aux output #5', 'status'),
    ],
    155: [
        (0, 192, 6, 'Aux input #4', 'status'),
        (0, 48, 4, 'Aux input #3', 'status'),
        (0, 12, 2, 'Aux input #2', 'status'),
        (0, 3, 0, 'Aux input #1', 'status'),
        (1, 192, 6, 'Aux output #4', 'status'),
        (1, 48, 4, 'Aux output #3', 'status'),
        (1, 12, 2, 'Aux output #2', 'status'),
        (1, 3, 0, 'Aux output #1', 'status'),
    ],
}


def decode_bits(pid, data):
    """Decode a J1587 bit-mapped PID to readable text.

    Returns a comma-joined ``label: value`` string, or None when the PID has no
    known bit layout. 2-bit status fields use the SAE J1587 nomenclature
    (00 off / 01 on / 10 error / 11 not available); PIDs whose standard wording
    differs per field use the ('states', w0, w1, w2, w3) kind with the exact
    words from the standard; explicit 1-bit flags use the on/off (or yes/no,
    active/not active) words given in the standard.
    """
    fields = PID_BITS.get(pid)
    if not fields or not data:
        return None
    out = []
    for byte_i, mask, shift, label, kind in fields:
        b = data[byte_i] if byte_i < len(data) else 0
        v = (b & mask) >> shift
        if kind == "status":
            # Defensive .get(): a wider-than-2-bit mask must not crash the
            # live-data view, it just shows the raw field value.
            t = _STATUS2.get(v, str(v))
        elif kind == "mode":
            t = str(v)
        elif isinstance(kind, tuple) and kind[0] == "states":
            # ("states", word00, word01, word10, word11)
            t = kind[1 + v] if 0 <= v <= 3 else _STATUS2[3]
        elif isinstance(kind, tuple) and kind[0] == "map":
            # ("map", (word per field value, ...)); None = reserved/unknown
            words = kind[1]
            t = words[v] if v < len(words) and words[v] is not None \
                else f"reserved ({v})"
        else:  # ("bool", on_text, off_text)
            t = kind[1] if v else kind[2]
        out.append(f"{label}: {t}")
    return ", ".join(out)


# --- SID names (SAE J1587 Table 6, common SIDs 151-255) ------------------- #
# SIDs 151-255 are the common "universal" set: the same meaning on every
# module type. SIDs 1-150 are controller-class specific and live below, one
# table per controller class (engine / transmission / brakes), keyed by MID.
SID_NAMES = {
    151: "System Diagnostic Code #1",
    152: "System Diagnostic Code #2",
    153: "System Diagnostic Code #3",
    154: "System Diagnostic Code #4",
    155: "System Diagnostic Code #5",
    207: "Battery #1 Temperature",
    208: "Battery #2 Temperature",
    209: "Start Enable Device #2",
    210: "Oil Temperature Sensor",
    211: "Sensor Supply Voltage #2 (+5V DC)",
    212: "Sensor Supply Voltage #1 (+5V DC)",
    213: "PLC Data Link",
    214: "ECU Backup Battery",
    215: "Cab Interior Temperature Thermostat",
    216: "Other ECUs Have Reported Fault Codes Affecting Operation",
    217: "Anti-theft Start Inhibit (Password Valid Indicator)",
    218: "ECM Main Relay",
    219: "Start Signal Indicator",
    220: "Electronic Tractor/Trailer Interface (ISO 11992)",
    221: "Internal Sensor Voltage Supply",
    222: "Protect Lamp",
    223: "Ambient Light Sensor",
    224: "Audible Alarm",
    225: "Green Lamp",
    226: "Transmission Neutral Switch",
    227: "Auxiliary Analog Input #1",
    228: "High Side Refrigerant Pressure Switch",
    229: "Kickdown Switch",
    230: "Idle Validation Switch",
    231: "SAE J1939 Data Link",
    232: "5 Volts DC Supply",
    233: "Controller #2",
    234: "Parking Brake On Actuator",
    235: "Parking Brake Off Actuator",
    236: "Power Connect Device",
    237: "Start Enable Device",
    238: "Diagnostic Lamp—Red",
    239: "Diagnostic Light—Amber",
    240: "Program Memory",
    241: "Set aside for Systems Diagnostics",
    242: "Cruise Control Resume Switch",
    243: "Cruise Control Set Switch",
    244: "Cruise Control Enable Switch",
    245: "Clutch Pedal Switch #1",
    246: "Brake Pedal Switch #1",
    247: "Brake Pedal Switch #2",
    248: "Proprietary Data Link",
    249: "SAE J1922 Data Link",
    250: "SAE J1708 (J1587) Data Link",
    251: "Power Supply",
    252: "Calibration Module",
    253: "Calibration Memory",
    254: "Controller #1",
    255: "Reserved",
}


# --- Per-controller-class SID tables (SAE J1587 Table 6, SIDs 1-150) -------- #
# The same SID number means a different component depending on which module
# (MID) reported it, so each controller class gets its own table, selected by
# MID. Names are the SAE J1587-2002 standard wording (factual; no OEM text).

# Engine controller class, SIDs 1-150.
_ENGINE_SIDS = {
    1: "Injector Cylinder #1",
    2: "Injector Cylinder #2",
    3: "Injector Cylinder #3",
    4: "Injector Cylinder #4",
    5: "Injector Cylinder #5",
    6: "Injector Cylinder #6",
    7: "Injector Cylinder #7",
    8: "Injector Cylinder #8",
    9: "Injector Cylinder #9",
    10: "Injector Cylinder #10",
    11: "Injector Cylinder #11",
    12: "Injector Cylinder #12",
    13: "Injector Cylinder #13",
    14: "Injector Cylinder #14",
    15: "Injector Cylinder #15",
    16: "Injector Cylinder #16",
    17: "Fuel Shutoff Valve",
    18: "Fuel Control Valve",
    19: "Throttle Bypass Valve",
    20: "Timing Actuator",
    21: "Engine Position Sensor",
    22: "Timing Sensor",
    23: "Rack Actuator",
    24: "Rack Position Sensor",
    25: "External Engine Protection Input",
    26: "Auxiliary Output Device Driver #1",
    27: "Variable Geometry Turbocharger Actuator #1",
    28: "Variable Geometry Turbocharger Actuator #2",
    29: "External Fuel Command Input",
    30: "External Speed Command Input",
    31: "Tachometer Signal Output",
    32: "Turbocharger #1 Wastegate Drive",
    33: "Fan Clutch Output Device Driver",
    34: "Exhaust Back Pressure Sensor",
    35: "Exhaust Back Pressure Regulator Solenoid",
    36: "Glow Plug Lamp",
    37: "Electronic Drive Unit Power Relay",
    38: "Glow Plug Relay",
    39: "Engine Starter Motor Relay",
    40: "Auxiliary Output Device Driver #2",
    41: "ECM 8 Volts DC Supply",
    42: "Injection Control Pressure Regulator",
    43: "Autoshift High Gear Actuator",
    44: "Autoshift Low Gear Actuator",
    45: "Autoshift Neutral Actuator",
    46: "Autoshift Common Low Side (Return)",
    47: "Injector Cylinder #17",
    48: "Injector Cylinder #18",
    49: "Injector Cylinder #19",
    50: "Injector Cylinder #20",
    51: "Auxiliary Output Device Driver #3",
    52: "Auxiliary Output Device Driver #4",
    53: "Auxiliary Output Device Driver #5",
    54: "Auxiliary Output Device Driver #6",
    55: "Auxiliary Output Device Driver #7",
    56: "Auxiliary Output Device Driver #8",
    57: "Auxiliary PWM Driver #1",
    58: "Auxiliary PWM Driver #2",
    59: "Auxiliary PWM Driver #3",
    60: "Auxiliary PWM Driver #4",
    61: "Variable Swirl System Valve",
    62: "Prestroke Sensor",
    63: "Prestroke Actuator",
    64: "Engine Speed Sensor #2",
    65: "Heated Oxygen Sensor",
    66: "Ignition Control Mode Signal",
    67: "Ignition Control Timing Signal",
    68: "Secondary Turbo Inlet Pressure",
    69: "After Cooler-Oil Cooler Coolant Temperature",
    70: "Inlet Air Heater Driver #1",
    71: "Inlet Air Heater Driver #2",
    72: "Injector Cylinder #21",
    73: "Injector Cylinder #22",
    74: "Injector Cylinder #23",
    75: "Injector Cylinder #24",
    76: "Knock Sensor",
    77: "Gas Metering Valve",
    78: "Fuel Supply Pump Actuator",
    79: "Engine (Compression) Brake Output #1",
    80: "Engine (Compression) Brake Output #2",
    81: "Engine (Exhaust) Brake Output",
    82: "Engine (Compression) Brake Output #3",
    83: "Fuel Control Valve #2",
    84: "Timing Actuator #2",
    85: "Engine Oil Burn Valve",
    86: "Engine Oil Replacement Valve",
    87: "Idle Shutdown Vehicle Accessories Relay Driver",
    88: "Turbocharger #2 Wastegate Drive",
    89: "Air Compressor Actuator Circuit",
    90: "Engine Cylinder #1 Knock Sensor",
    91: "Engine Cylinder #2 Knock Sensor",
    92: "Engine Cylinder #3 Knock Sensor",
    93: "Engine Cylinder #4 Knock Sensor",
    94: "Engine Cylinder #5 Knock Sensor",
    95: "Engine Cylinder #6 Knock Sensor",
    96: "Engine Cylinder #7 Knock Sensor",
    97: "Engine Cylinder #8 Knock Sensor",
    98: "Engine Cylinder #9 Knock Sensor",
    99: "Engine Cylinder #10 Knock Sensor",
    100: "Engine Cylinder #11 Knock Sensor",
    101: "Engine Cylinder #12 Knock Sensor",
    102: "Engine Cylinder #13 Knock Sensor",
    103: "Engine Cylinder #14 Knock Sensor",
    104: "Engine Cylinder #15 Knock Sensor",
    105: "Engine Cylinder #16 Knock Sensor",
    106: "Engine Cylinder #17 Knock Sensor",
    107: "Engine Cylinder #18 Knock Sensor",
    108: "Engine Cylinder #19 Knock Sensor",
    109: "Engine Cylinder #20 Knock Sensor",
    110: "Engine Cylinder #21 Knock Sensor",
    111: "Engine Cylinder #22 Knock Sensor",
    112: "Engine Cylinder #23 Knock Sensor",
    113: "Engine Cylinder #24 Knock Sensor",
    114: "Multiple Unit Synchronization Switch",
    115: "Engine Oil Change Interval",
    116: "Engine was Shut Down Hot",
    117: "Engine has been Shut Down from Data Link Information",
    118: "Injector Needle Lift Sensor #1",
    119: "Injector Needle Lift Sensor #2",
    120: "Coolant System Thermostat",
    121: "Engine Automatic Start Alarm",
    122: "Engine Automatic Start Lamp",
    123: "Engine Automatic Start Safety Interlock Circuit",
    124: "Engine Automatic Start Failed (Engine)",
    125: "Fuel Heater Driver Signal",
    126: "Fuel Pump Pressurizing Assembly #1",
    127: "Fuel Pump Pressurizing Assembly #2",
    128: "Starter Solenoid Lockout Relay Driver Circuit",
    129: "Cylinder #1 Exhaust Gas Port Temperature",
    130: "Cylinder #2 Exhaust Gas Port Temperature",
    131: "Cylinder #3 Exhaust Gas Port Temperature",
    132: "Cylinder #4 Exhaust Gas Port Temperature",
    133: "Cylinder #5 Exhaust Gas Port Temperature",
    134: "Cylinder #6 Exhaust Gas Port Temperature",
    135: "Cylinder #7 Exhaust Gas Port Temperature",
    136: "Cylinder #8 Exhaust Gas Port Temperature",
    137: "Cylinder #9 Exhaust Gas Port Temperature",
    138: "Cylinder #10 Exhaust Gas Port Temperature",
    139: "Cylinder #11 Exhaust Gas Port Temperature",
    140: "Cylinder #12 Exhaust Gas Port Temperature",
    141: "Cylinder #13 Exhaust Gas Port Temperature",
    142: "Cylinder #14 Exhaust Gas Port Temperature",
    143: "Cylinder #15 Exhaust Gas Port Temperature",
    144: "Cylinder #16 Exhaust Gas Port Temperature",
    145: "Adaptive Cruise Control Mode",
    146: "Exhaust Gas Re-Circulation (EGR) Valve Mechanism",
    147: "Variable Nozzle Turbocharger (VNT) Mechanism",
    148: "Engine (Compression) Brake Output #4",
    149: "Engine (Compression) Brake Output #5",
    150: "Engine (Compression) Brake Output #6",
}

# Transmission controller class, SIDs 1-64 (65-150 reserved).
_TRANSMISSION_SIDS = {
    1: "C1 Solenoid Valve",
    2: "C2 Solenoid Valve",
    3: "C3 Solenoid Valve",
    4: "C4 Solenoid Valve",
    5: "C5 Solenoid Valve",
    6: "C6 Solenoid Valve",
    7: "Lockup Solenoid Valve",
    8: "Forward Solenoid Valve",
    9: "Low Signal Solenoid Valve",
    10: "Retarder Enable Solenoid Valve",
    11: "Retarder Modulation Solenoid Valve",
    12: "Retarder Response Solenoid Valve",
    13: "Differential Lock Solenoid Valve",
    14: "Engine/Transmission Match",
    15: "Retarder Modulation Request Sensor",
    16: "Neutral Start Output",
    17: "Turbine Speed Sensor",
    18: "Primary Shift Selector",
    19: "Secondary Shift Selector",
    20: "Special Function Inputs",
    21: "C1 Clutch Pressure Indicator",
    22: "C2 Clutch Pressure Indicator",
    23: "C3 Clutch Pressure Indicator",
    24: "C4 Clutch Pressure Indicator",
    25: "C5 Clutch Pressure Indicator",
    26: "C6 Clutch Pressure Indicator",
    27: "Lockup Clutch Pressure Indicator",
    28: "Forward Range Pressure Indicator",
    29: "Neutral Range Pressure Indicator",
    30: "Reverse Range Pressure Indicator",
    31: "Retarder Response System Pressure Indicator",
    32: "Differential Lock Clutch Pressure Indicator",
    33: "Multiple Pressure Indicators",
    34: "Reverse Switch",
    35: "Range High Actuator",
    36: "Range Low Actuator",
    37: "Splitter Direct Actuator",
    38: "Splitter Indirect Actuator",
    39: "Shift Finger Rail Actuator 1",
    40: "Shift Finger Gear Actuator 1",
    41: "Upshift Request Switch",
    42: "Downshift Request Switch",
    43: "Torque Converter Interrupt Actuator",
    44: "Torque Converter Lockup Actuator",
    45: "Range High Indicator",
    46: "Range Low Indicator",
    47: "Shift Finger Neutral Indicator",
    48: "Shift Finger Engagement Indicator",
    49: "Shift Finger Center Rail Indicator",
    50: "Shift Finger Rail Actuator 2",
    51: "Shift Finger Gear Actuator 2",
    52: "Hydraulic System",
    53: "Defuel Actuator",
    54: "Inertia Brake Actuator",
    55: "Clutch Actuator",
    56: "Auxiliary Range Mechanical System",
    57: "Shift Console Data Link",
    58: "Main Box Shift Engagement System",
    59: "Main Box Rail Selection System",
    60: "Main Box Shift Neutralization System",
    61: "Auxiliary Splitter Mechanical System",
    62: "Transmission Controller Power Relay",
    63: "Output Shaft Speed Sensor",
    64: "Throttle Position Device",
}

# Brake controller class, SIDs 1-97 (98-150 reserved).
_BRAKE_SIDS = {
    1: "Wheel Sensor ABS Axle 1 Left",
    2: "Wheel Sensor ABS Axle 1 Right",
    3: "Wheel Sensor ABS Axle 2 Left",
    4: "Wheel Sensor ABS Axle 2 Right",
    5: "Wheel Sensor ABS Axle 3 Left",
    6: "Wheel Sensor ABS Axle 3 Right",
    7: "Pressure Modulation Valve ABS Axle 1 Left",
    8: "Pressure Modulation Valve ABS Axle 1 Right",
    9: "Pressure Modulation Valve ABS Axle 2 Left",
    10: "Pressure Modulation Valve ABS Axle 2 Right",
    11: "Pressure Modulation Valve ABS Axle 3 Left",
    12: "Pressure Modulation Valve ABS Axle 3 Right",
    13: "Retarder Control Relay",
    14: "Relay Diagonal 1",
    15: "Relay Diagonal 2",
    16: "Mode Switch ABS",
    17: "Mode Switch ASR",
    18: "DIF 1 - ASR Valve",
    19: "DIF 2 - ASR Valve",
    20: "Pneumatic Engine Control",
    21: "Electronic Engine Control (Servomotor)",
    22: "Speed Signal Input",
    23: "Tractor ABS Warning Light Bulb",
    24: "ASR Light Bulb",
    25: "Wheel Sensor, ABS Axle 1 Average",
    26: "Wheel Sensor, ABS Axle 2 Average",
    27: "Wheel Sensor, ABS Axle 3 Average",
    28: "Pressure Modulator, Drive Axle Relay Valve",
    29: "Pressure Transducer, Drive Axle Relay Valve",
    30: "Master Control Relay",
    31: "Trailer Brake Slack Out of Adjustment Forward Axle Left",
    32: "Trailer Brake Slack Out of Adjustment Forward Axle Right",
    33: "Trailer Brake Slack Out of Adjustment Rear Axle Left",
    34: "Trailer Brake Slack Out of Adjustment Rear Axle Right",
    35: "Tractor Brake Slack Out of Adjustment Axle 1 Left",
    36: "Tractor Brake Slack Out of Adjustment Axle 1 Right",
    37: "Tractor Brake Slack Out of Adjustment Axle 2 Left",
    38: "Tractor Brake Slack Out of Adjustment Axle 2 Right",
    39: "Tractor Brake Slack Out of Adjustment Axle 3 Left",
    40: "Tractor Brake Slack Out of Adjustment Axle 3 Right",
    41: "Ride Height Relay",
    42: "Hold Modulator Valve Solenoid Axle 1 Left",
    43: "Hold Modulator Valve Solenoid Axle 1 Right",
    44: "Hold Modulator Valve Solenoid Axle 2 Left",
    45: "Hold Modulator Valve Solenoid Axle 2 Right",
    46: "Hold Modulator Valve Solenoid Axle 3 Left",
    47: "Hold Modulator Valve Solenoid Axle 3 Right",
    48: "Dump Modulator Valve Solenoid Axle 1 Left",
    49: "Dump Modulator Valve Solenoid Axle 1 Right",
    50: "Dump Modulator Valve Solenoid Axle 2 Left",
    51: "Dump Modulator Valve Solenoid Axle 2 Right",
    52: "Dump Modulator Valve Solenoid Axle 3 Left",
    53: "Dump Modulator Valve Solenoid Axle 3 Right",
    54: "Hydraulic Pump Motor",
    55: "Brake Light Switch 1",
    56: "Brake Light Switch 2",
    57: "Electronic Pressure Control, Axle 1",
    58: "Pneumatic Back-up Pressure Control, Axle 1",
    59: "Brake Pressure Sensing, Axle 1",
    60: "Electronic Pressure Control, Axle 2",
    61: "Pneumatic Back-up Pressure Control, Axle 2",
    62: "Brake Pressure Sensing, Axle 2",
    63: "Electronic Pressure Control, Axle 3",
    64: "Pneumatic Back-up Pressure Control, Axle 3",
    65: "Brake Pressure Sensing, Axle 3",
    66: "Electronic Pressure Control, Trailer Control",
    67: "Pneumatic Back-up Pressure Control, Trailer Control",
    68: "Brake Pressure Sensing, Trailer Control",
    69: "Axle Load Sensor",
    70: "Lining Wear Sensor, Axle 1 Left",
    71: "Lining Wear Sensor, Axle 1 Right",
    72: "Lining Wear Sensor, Axle 2 Left",
    73: "Lining Wear Sensor, Axle 2 Right",
    74: "Lining Wear Sensor, Axle 3 Left",
    75: "Lining Wear Sensor, Axle 3 Right",
    76: "Brake Signal Transmitter",
    77: "Brake Signal Sensor 1",
    78: "Brake Signal Sensor 2",
    79: "Tire Dimension Supervision",
    80: "Vehicle Deceleration Control",
    81: "Trailer ABS Warning Light Bulb",
    82: "Brake Torque Output Axle 1 Left",
    83: "Brake Torque Output Axle 1 Right",
    84: "Brake Torque Output Axle 2 Left",
    85: "Brake Torque Output Axle 2 Right",
    86: "Brake Torque Output Axle 3 Left",
    87: "Brake Torque Output Axle 3 Right",
    88: "Vehicle Dynamic Stability Control System (VDC)",
    89: "Steering Angle Sensor",
    90: "Voltage Supply for Stability Control System",
    91: "Brake Lining Display",
    92: "Pressure Limitation Valve",
    93: "Auxiliary Valve",
    94: "Hill holder System",
    95: "Voltage Supply, Lining Wear Sensors, Axle 1",
    96: "Voltage Supply, Lining Wear Sensors, Axle 2",
    97: "Voltage Supply, Lining Wear Sensors, Axle 3",
}

# MID -> MID-specific SID name table (SAE J1587 Table 6, per-controller).
MID_SID_NAMES = {
    128: _ENGINE_SIDS,          # Engine #1
    175: _ENGINE_SIDS,          # Engine #2
    183: _ENGINE_SIDS,          # Engine #3
    184: _ENGINE_SIDS,          # Engine #4
    185: _ENGINE_SIDS,          # Engine #5
    186: _ENGINE_SIDS,          # Engine #6
    130: _TRANSMISSION_SIDS,    # Transmission
    176: _TRANSMISSION_SIDS,    # Transmission, Additional
    136: _BRAKE_SIDS,           # Brakes, Power Unit
    137: _BRAKE_SIDS,           # Brakes, Trailer #1
    138: _BRAKE_SIDS,           # Brakes, Trailer #2
    139: _BRAKE_SIDS,           # Brakes, Trailer #3
    246: _BRAKE_SIDS,           # Brakes (additional)
    247: _BRAKE_SIDS,           # Brakes (additional)
}
