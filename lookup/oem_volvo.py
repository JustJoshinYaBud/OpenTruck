"""OpenTruck - Volvo / Mack engine ECM parameter cross-reference.

J1587 slot number (PID / PSID) -> short parameter name, keyed from the OFFICIAL
Volvo Group service publication "Service Information Trucks - Group 28 Engine
Control Module (ECM), Diagnostic Trouble Code (DTC) Guide, 2010 Emissions"
(Volvo Group North America publication 89046912, (c)2012 - covers the Volvo D13
and Mack MP7/MP8/MP10 ECM family). Regenerate rather than hand-editing.

This is the **cross-reference tier**, built from that publication's DTC index:
it maps each SPN to the J1587 slot the ECM reports it on, including Volvo's
private **PSID** namespace (which is NOT in the generic SAE J1587 PID table, so
a Volvo PSID would otherwise fall through to the J1939 SPN table and be named
wrongly). The parameter names are the standard SAE names of those SPNs.

Still to do: the FMI-level descriptions live on the guide's detail pages (each
entry is "Type of fault / FMI / Description / Fault Condition / Possible
Symptoms / Possible Cause") - extract those as a second pass and add them as
`spn_fmi` / `pid_fmi` overrides. Slots numbered above 255 cannot appear in a
one-byte J1587 slot and are excluded.

Resolution goes through ``oem.resolve_pid_name`` / ``resolve_sid_name`` (OEM
override first, then the generic J1587/J1939 tables), so these names apply ONLY
to a module identified as Volvo or Mack.
"""

# PID / PSID slot -> parameter name
VOLVO_PID: dict[int, str] = {
    8: 'Engine Piston Cooling Oil Pressure',
    25: 'Aftertreatment DPF Auxiliary Heater Mode',
    27: 'Engine Misfire for Multiple Cylinders',
    28: 'Aftertreatment DPF System',
    35: 'Engine Exhaust Gas Recirculation (EGR) Mass Flow Rate',
    45: 'Intake Air Heater (IAH) Relay',
    46: 'Aftertreatment SCR Operator Inducement Severity',
    47: 'Aftertreatment Regeneration Status',
    49: 'Battery Potential/Switched Voltage',
    52: 'Charge Air Cooler (CAC) Temperature',
    55: 'Engine Control Module (ECM) Temperature',
    72: 'Engine Oil Thermostat Bypass Valve Opening',
    75: 'Aftertreatment Diesel Exhaust Fluid (DEF) Tank Heater',
    77: 'Calibration Module',
    81: 'Aftertreatment DPF Differential Pressure',
    84: 'Wheel-Based Vehicle Speed',
    85: 'Cruise Control Status',
    87: 'Aftertreatment Diesel Exhaust Fluid (DEF) Pump Motor Speed',
    89: 'Engine Variable Geometry Turbocharger (VGT) Actuator 2',
    90: 'NOx Limits Exceeded Due to Insufficient Diesel Exhaust Fluid (DEF) Quality',
    91: 'Accelerator Pedal Position 1',
    94: 'Engine Fuel Delivery Pressure',
    97: 'Water in Fuel Indicator',
    98: 'Engine Oil Level',
    99: 'Aftertreatment Diesel Oxidation Catalyst (DOC) Conversion Efficiency',
    100: 'Engine Oil Pressure',
    102: 'Engine Intake Manifold 1 Pressure',
    103: 'Engine Turbocharger 1 Speed',
    105: 'Engine Intake Manifold 1 Temperature',
    108: 'Barometric Pressure',
    109: 'Engine Coolant System Thermostat',
    110: 'Engine Coolant Temperature',
    111: 'Engine Coolant Level',
    113: 'Sensor Supply Voltage 3',
    119: 'Aftertreatment Diesel Particulate Filter (DPF) Regeneration too Frequent',
    121: 'Aftertreatment Diesel Exhaust Fluid Pump (DEF) Drive Percentage',
    122: 'Estimated Percent Fan Speed | (MID 128 PID 26) | , page 436 Group 28 Engine Control Module (ECM) Diagnostic Trouble Codes (DTCs) SPN 1000|1999 | | ECM SPN 1072, Engine Compression Brake Output #1',
    126: 'Sensor Supply Voltage 4',
    153: 'Engine High Resolution Crankcase Pressure',
    158: 'Keyswitch Battery Potential',
    161: 'Vehicle Identification Number',
    171: 'Ambient Air Temperature',
    173: 'Engine Exhaust Gas Temperature (EGT)',
    175: 'Engine Oil Temperature 1',
    177: 'Transmission Oil Temperature',
    188: 'Engine Speed At Idle, Point 1 (Engine Configurations)',
    190: 'Engine Speed',
    201: 'Invalid or Missing Data from Vehicle ECU',
    205: 'Aftertreatment Diesel Exhaust Fluid (DEF) Tank Level | PPID 278 | , page 49 SPN 2000|2999 | | ECM SPN 2003, Transmission Control Module (TCM) Status',
    224: 'Anti|theft Random Number',
    228: 'Speed Sensor Calibration',
    229: 'SAE J1939 Data Link 2',
    245: 'Total Vehicle Distance',
    251: 'Time',
    252: 'Date',
}

# SID slot -> parameter name
VOLVO_SID: dict[int, str] = {
    1: 'Engine Injector Cylinder 1',
    2: 'Engine Injector Cylinder 2',
    3: 'Engine Injector Cylinder 3',
    4: 'Engine Injector Cylinder 4',
    5: 'Engine Injector Cylinder 5',
    6: 'Engine Injector Cylinder 6',
    18: 'Engine Fuel Actuator 1 Control Command',
    21: 'Camshaft Position Sensor (CMP)',
    22: 'Crankshaft Position Sensor (CKP)',
    27: 'Engine Variable Geometry Turbocharger (VGT) Actuator 1',
    33: 'Engine Fan Clutch Output Device Driver',
    39: 'Engine Starter Motor Relay',
    70: 'Intake Air Heater (IAH) 1',
    71: 'Intake Air Heater (IAH) 2',
    85: 'Engine Piston Cooling Oil Pressure Actuator',
    146: 'Engine Exhaust Gas Recirculation (EGR) Valve Control',
    211: 'Sensor Supply Voltage 2',
    230: 'Accelerator Pedal 1 Idle Validation Switch',
    231: 'SAE J1939 Data Link 1',
    232: 'Sensor Supply Voltage 1',
    240: 'Program Memory',
    253: 'Calibration Memory',
    254: 'Electronic Control Unit (ECU) 1',
}

# ---------------------------------------------------------------------------
# SPN -> short parameter name, in Volvo/Mack wording.
#
# Second pass over the SAME official guide's detail pages ("ECM SPN n,
# <name> - MID 128 <slot>"). These are the maker's own names for standard SPNs;
# they are useful where Volvo's wording is clearer than the generic SAE name
# (e.g. SPN 636 = "Camshaft Position Sensor (CMP)" rather than "Engine Position
# Sensor"). Short factual names only - the guide's fault-condition prose is NOT
# redistributed, and the FMI failure phrase still comes from the generic SAE
# table at display time.
# ---------------------------------------------------------------------------
VOLVO_SPN: dict[int, str] = {
    94: 'Engine Fuel Delivery Pressure',
    98: 'Engine Oil Level',
    100: 'Engine Oil Pressure',
    102: 'Engine Intake Manifold 1 Pressure',
    108: 'Barometric Pressure',
    110: 'Engine Coolant Temperature',
    111: 'Engine Coolant Level',
    153: 'Engine High Resolution Crankcase Pressure',
    175: 'Engine Oil Temperature 1',
    237: 'Vehicle Identification Number',
    411: 'Engine EGR Differential Pressure',
    558: 'Accelerator Pedal 1 Idle Validation Switch',
    631: 'Calibration Module',
    633: 'Engine Fuel Actuator 1 Control Command',
    636: 'Camshaft Position Sensor (CMP)',
    637: 'Crankshaft Position Sensor (CKP)',
    639: 'SAE J1939 Data Link 1',
    641: 'Engine Variable Geometry Turbocharger (VGT) Actuator 1',
    642: 'Engine Variable Geometry Turbocharger (VGT) Actuator 2',
    647: 'Engine Fan Clutch Output Device Driver',
    651: 'Engine Injector Cylinder 1',
    656: 'Engine Injector Cylinder 6',
    729: 'Intake Air Heater (IAH) 1',
    975: 'Estimated Percent Fan Speed',
    1136: 'Engine Control Module (ECM) Temperature',
    1231: 'SAE J1939 Data Link 2',
    1265: 'Engine Piston Cooling Oil Pressure Actuator',
    1322: 'Engine Misfire for Multiple Cylinders',
    1659: 'Engine Coolant System Thermostat',
    1761: 'Aftertreatment DEF Tank Level',
    2003: 'Transmission Control Module (TCM) Status',
    2017: 'Cruise Control Status',
    2629: 'Engine Turbocharger Compressor Outlet Temperature',
    2659: 'Engine EGR Mass Flow Rate',
    2791: 'Engine EGR Valve Control',
    2836: 'Battery Potential / Switched Voltage',
    3031: 'Aftertreatment DEF Tank Temperature',
    3216: 'Aftertreatment Intake NOx',
    3226: 'Aftertreatment Outlet NOx',
    3249: 'Aftertreatment DPF Intake Temperature',
    3251: 'Aftertreatment DPF Differential Pressure',
    3480: 'Aftertreatment DPF Fuel Pressure',
    3483: 'Aftertreatment Regeneration Status',
    3492: 'Aftertreatment 1 Air System Relay',
    3511: 'Sensor Supply Voltage 3',
    3512: 'Sensor Supply Voltage 4',
    3522: 'Aftertreatment Total Fuel Used',
    3556: 'Aftertreatment Hydrocarbon Doser',
    3597: 'Aftertreatment DPF Regeneration too Frequent',
    3675: 'Engine Turbocharger Compressor Bypass Valve Position',
    3936: 'Aftertreatment DPF System',
    4095: 'NOx Limits Exceeded due to Interrupted DEF Dosing',
    4339: 'Aftertreatment SCR Feedback Control Status',
    4354: 'Aftertreatment DEF Line Heater 1',
    4356: 'Aftertreatment DEF Line Heater 3',
    4374: 'Aftertreatment DEF Pump Motor Speed',
    4375: 'Aftertreatment DEF Pump Drive Percentage',
    4376: 'Aftertreatment DEF Return Valve',
    4813: 'Engine Oil Thermostat Bypass Valve Opening',
    5246: 'Aftertreatment SCR Operator Inducement Severity',
    5285: 'Charge Air Cooler (CAC) Temperature',
    5298: 'Aftertreatment DOC Conversion Efficiency',
    5394: 'Aftertreatment DEF Dosing Valve',
    5443: 'Aftertreatment 1 Hydrocarbon Dosing System',
    5485: 'Aftertreatment DEF Pump Orifice',
}

# ---------------------------------------------------------------------------
# J1939 source-address maps, per platform.
#
# These are PLATFORM-SPECIFIC: the Volvo map comes from the 2026 VN(4) Body
# Builder Instructions (Section 3, "Source Addresses and Unit Acronyms"), and
# the Mack map from the Mack MD Body Builder Instructions (9.2024, same table).
# Older platforms use the same core addresses (ECM 0x00, TCM 0x03, EBS/ABS 0x0B,
# cluster 0x17) but not necessarily the same ancillary modules, so these are
# only used as a fallback label when a module never identifies itself.
# ---------------------------------------------------------------------------
# Source document: Volvo Body Builder Instructions VNL Section 3
# USA184039858 Date 5.2025 - Electrical, Electronic Control Unit (ECU)
# Page 31-36: Message Source Address tables and Page 40: Summary table

VOLVO_ADDRESSES: dict[int, str] = {
    # Core Powertrain (Standard J1939 preferred addresses)
    0x00: "Engine Control Module (ECM)",
    0x03: "Transmission Control Module (TCM)",
    0x0B: "Electronically Controlled Brake System (EBS)",
    
    # Vehicle Control
    0x11: "Vehicle Master Control Unit (VMCU)",
    0x17: "Instrument Cluster (IC)",
    
    # Driver Assistance Systems
    0x2A: "Driver Assistance Control Unit (DACU) - Lane Departure / ACC",
    0xE8: "Driver Assistance Control Unit (DACU) - FLI messages",  # Same unit, different message types
    
    # Chassis/Body Modules
    0x2F: "Rear Chassis Input/Output Module (RCIOM)",
    0x31: "Security & Cab Interface Module (SCIM) - Primary",
    0x37: "Security & Cab Interface Module (SCIM) - Secondary",  # Same unit, different role
    
    # Telematics/Sensors
    0x33: "Wireless Sensor Gateway (WSGW) - TPMS / Tire Sensors",
    0x3D: "Aftertreatment Control Module (ACM)",
    0xEE: "Telematics Gateway (TGW)",
}

# Source document: Mack Body Builder Instructions MD Section 3
# USA182536242 Date 9.2024 and USA184783141 Date 2.2025
# Page 35-36: Source Addresses and Unit Acronyms table

MACK_ADDRESSES: dict[int, str] = {
    # Core Powertrain (Standard J1939 preferred addresses)
    0x00: "Engine Control Module (ECM)",
    0x03: "Transmission Electronic Control Unit / Control Module (TECU/TCM)",
    0x05: "Gear Shift Electronic Control Unit (GSECU)",
    0x0B: "Anti-lock Brake System (ABS)",
    
    # Engine Brake / Retarder
    0x0F: "Engine Brake (EB) - Mack EBS/Retarder Controller",
    
    # Vehicle Control
    0x11: "Vehicle Electronic Control Unit (VECU)",
    0x17: "Instrument Cluster (IC)",
}
