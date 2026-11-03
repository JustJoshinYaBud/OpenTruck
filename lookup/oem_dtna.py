# DTNA (Daimler Trucks North America) - OpenTruck OEM lookup table
# 
# Source documents:
#   - MC-11008340 (2024): J1939 Data Link Source Address Information (NHTSA TSB)
#   - DDC-SVC-MAN-0193/0200 (2018): DD5/DD8 SPN/FMI Aftertreatment Codes (GHG17)
#   - S08327 (2010): Body Controller Diagnostic Trouble Codes (International)
#   - SS 1032728 (2016): Bulkhead Module Fault Codes 524280-524286 (NHTSA TSB)
#   - MM-0951 (2019): WABCO OnGuard Collision Mitigation System Manual
#
# Copyright: DTNA, Detroit Diesel Corporation, WABCO. Descriptions extracted from
# publicly available NHTSA-mirrored documents for diagnostic tool use only.
#
# FALLBACK POLICY: Codes not in this table fall back to generic SAE names for
# engine/transmission/brakes modules (standard parameters), or "Refer to OEM" for
# chassis/body/cab modules (proprietary codes). The rule is implemented once in
# ``lookup/oem.py`` (``_generic_name_trusted``) and applies to every maker.

# Data-only module - no imports from oem.py to avoid circular imports


# =============================================================================
# DTNA Source Address Map (MC-11008340 2024)
# =============================================================================
DTNA_ADDRESSES = {
    # Core powertrain
    0: "Engine ECM",
    3: "Transmission Control Module",
    5: "Transmission Shift Selector",
    
    # Brakes/ABS
    11: "ABS ECU",
    62: "Wabco ABS ECU",
    160: "Wabco OnGuard Radar Collision Mitigation",
    
    # Body/Chassis
    23: "Electronic Gauge Cluster (EGC/IPC)",
    33: "Body Controller / ESC MSM",
    39: "Powertrain Interface Module (PIM)",
    
    # HVAC/Climate
    25: "Front HVAC Control Head",
    58: "Rear HVAC",
    
    # Displays/Instrumentation
    40: "VID/DID - Vehicle/Driver Information Display",
    132: "Auxiliary Gauge Switch Pack (AGSP3)",
    167: "Secondary Instrument Cluster (SIC)",
    
    # Telematics/Gateway
    74: "Telematics (N2 module)",
    75: "Telematics (fallback address)",
    
    # Lighting
    55: "Lighting Control Module (LCM)",
    68: "Compass Module",
    
    # Aftertreatment/Emissions
    61: "Exhaust Emissions Controller (DCU - Doser Control Unit)",
    85: "Aftertreatment Control Module (ACM)",
    
    # Safety/Collision
    42: "Headway Controller (Bendix Wingman / Wabco OnGuard Radar)",
    
    # Comfort/Convenience
    76: "Cab Radio",
    84: "Sleeper Radio",
    
    # EV/Hybrid modules (typically not present on diesel trucks)
    26: "Smart Alternator",
    46: "Electric Power Steering",
    47: "Active Ride Height Control Module",
    48: "Electric Air Brake Compressor",
    90: "Vehicle Control Unit / Gateway (VCU)",
    128: "On Board Charging Interface (OCI)",
    129: "A/C Compressor Inverter Module",
    130: "Supervisory Control Unit (SCU)",
    176: "DC to DC Converter 2",
    179: "DC to DC Converter 1",
    
    # Door pods (500k Phase 2 only - Private J1939 125k Baud)
    223: "Door Motor Control Module 1 (Forward Entrance)",
    224: "Door Motor Control Module 2 (A Entrance)",
    233: "Left Rear Door Pod",
    234: "Right Rear Door Pod",
    236: "Driver Front Door Pod",
    237: "Passenger Front Door Pod",
    
    # Remote Power Modules (500k Phase 2 only)
    225: "Remote Power Module (RPM) #1",
    226: "Remote Power Module (RPM) #2",
    227: "Remote Power Module (RPM) #3",
    228: "Remote Power Module (RPM) #4",
    229: "Remote Power Module (RPM) #5",
    230: "Remote Power Module (RPM) #6",
    231: "Remote Power Module (RPM) #7",
    232: "Remote Power Module (RPM) #8",
    
    # Source document: IK0800351 J1939 Data Link Source Address Information
# NHTSA-mirrored (Transport Canada mirrors this document as well)
# Revision 21, Last Modified 9/27/2024
# 
# NOTE: This is the most comprehensive source address table available.
# Transport Canada uses the same document (listed as "Less Info Country"
# in the NHTSA header, meaning they mirror this data).
#
# Addresses are organized by system type. EV/Hybrid modules marked with
# "(EV)" are typically only present on electric/hybrid vehicles.
#
# 500k Phase 2 addresses use Private J1939 125k Baud data link.

# --- Core Powertrain (Standard J1939 preferred addresses) ---
    0: "Engine ECM",
    3: "Transmission Control Module",
    5: "Transmission Shift Selector",
    
# --- Brakes/ABS ---
    11: "ABS ECU",
    62: "Wabco ABS ECU",
    
# --- Retarder / Engine Brake ---
    15: "Retarder (ECM-generated, no physical module)",
    41: "Retarder, Exhaust, Engine #1 (ECM-generated)",
    
# --- Cruise Control / Driver Assistance ---
    17: "Cruise Control (PCC - Predictive Cruise Control)",
    19: "Lane Keep Assist ECU",
    
# --- Body/Chassis ---
    23: "Electronic Gauge Cluster (EGC/IPC)",
    33: "Body Controller / ESC MSM (PayStar and RE/FE Bus only)",
    39: "Powertrain Interface Module (PIM) (S13 vehicles only)",
    
# --- HVAC/Climate ---
    25: "Front HVAC Control Head",
    58: "Rear HVAC (Private BodyBuilder data link; moved to 250k Cab on 500k Phase 2)",
    
# --- Displays/Instrumentation ---
    40: "VID/DID - Vehicle Information Display / Driver Information Display",
    132: "Auxiliary Gauge Switch Pack (AGSP3) (Private J1939 125k Baud)",
    167: "Secondary Instrument Cluster (SIC) (Above center panel)",
    
# --- Telematics/Gateway ---
    74: "Telematics (N2 module)",
    75: "Telematics (fallback if N2 cannot claim 74)",
    128: "Omnitracks/Samsara Devices (Aftermarket telematics)",
    
# --- Lighting ---
    55: "Lighting Control Module (LCM) (500k Phase 2 only)",
    68: "Compass Module",
    168: "Forward Lighting Module Left (Smart LED headlight, first used on 2022MY MV)",
    169: "Forward Lighting Module Right (Smart LED headlight, first used on 2022MY MV)",
    
# --- Aftertreatment/Emissions ---
    61: "Exhaust Emissions Controller (DCU - Doser Control Unit) (N9/N10 engines only)",
    85: "Aftertreatment Control Module (ACM)",
    
# --- Safety/Collision Systems ---
    42: "Headway Controller (Bendix Wingman / Wabco OnGuard Radar)",
    80: "Dash Electronic Control Unit (DECU) (Bendix Intellipark system)",
    83: "Air Bag Module (SRS)",
    144: "Blindspot Radar",
    148: "DASCM module (Blind Spot Detection Module)",
    209: "Safety Direct Processor (SDP) Module (Bendix Fusion System, headliner above windshield camera)",
    
# --- Comfort/Convenience ---
    76: "Radio - Cab Radio",
    84: "Sleeper Radio - Sleeper Audio Control",
    
# --- EV/Hybrid Modules (typically not present on diesel trucks) ---
    26: "Smart Alternator (EV)",
    46: "Electric Power Steering (EV)",
    47: "Active Ride Height Control Module (EV)",
    48: "Electric Air Brake Compressor (EV)",
    90: "Vehicle Control Unit / Gateway (VCU) (EV)",
    129: "A/C Compressor Inverter Module (EV)",
    130: "Supervisory Control Unit (SCU) (EV)",
    176: "DC to DC Converter 2 (EV)",
    179: "DC to DC Converter 1 (EV)",
    181: "Electric Motor Pump - Coolant Pump 1 (EV)",
    182: "Electric Motor Pump - Coolant Pump 2 (EV)",
    186: "High Voltage Distribution Module (HVDM) - Static Trac on Power Inverter / TPIM-SCE (EV)",
    187: "High Voltage Distribution Module (HVDM) - Static High Voltage Power Distribution Unit / HVDU-SCE (EV)",
    188: "High Voltage Distribution Module (HVDM) - Static DC/Charge DCFC-SCE (EV)",
    189: "High Voltage Distribution Module (HVDM) - Static A/C Compressor Module Variable Speed Front AC-F (VFD)-SCE (EV)",
    190: "High Voltage Distribution Module (HVDM) - Static A/C Compressor Module Variable Speed Rear AC-R (VFD)-SCE (EV)",
    202: "Battery Thermal Management System (BTMS) (EV)",
    239: "Transmission Power Inverter Module (TPIM) (EV)",
    243: "Battery Management System (BMS) (EV)",
    
# --- Door Pods (500k Phase 2 only - Private J1939 125k Baud) ---
    223: "Door Motor Control Module 1 (Forward Entrance Door Motor Control on CE Bus with electric entrance door)",
    224: "Door Motor Control Module 2 (A Entrance Door Motor Control on CE Bus with electric entrance door)",
    233: "Left Rear Door Pod",
    234: "Right Rear Door Pod",
    236: "Driver Front Door Pod",
    237: "Passenger Front Door Pod",
    
# --- Remote Power Modules (500k Phase 2 only) ---
    225: "Remote Power Module (RPM) #1",
    226: "Remote Power Module (RPM) #2",
    227: "Remote Power Module (RPM) #3",
    228: "Remote Power Module (RPM) #4",
    229: "Remote Power Module (RPM) #5",
    230: "Remote Power Module (RPM) #6",
    231: "Remote Power Module (RPM) #7",
    232: "Remote Power Module (RPM) #8",
    
# --- Center Panel MUX Switch Packs (500k Phase 2 only - Private J1939 125k Baud) ---
    151: "Center Panel MUX Switch Pack #1",
    152: "Center Panel MUX Switch Pack #2",
    153: "Center Panel MUX Switch Pack #3",
    154: "Center Panel MUX Switch Pack #4",
    155: "Center Panel MUX Switch Pack #5",
    
# --- Specialized / Other ---
    143: "Transmission Shift Actuator Module (TSA) (Allison 1000/2000 series with stalk shifter)",
    149: "Pyrometer/Ammeter Module (PAM)",
    150: "Stand Alone Real Time Clock (SART)",
    172: "Offboard Diagnostics (EzTech Laptop)",
    216: "Electronic Li Axle Module (ELAM)",
    249: "Service Tool (EzTech Laptop)",
    252: "Vehicle Road Grade Sensor",
}


# =============================================================================
# Detroit Diesel GHG17 Aftertreatment SPNs (DDC-SVC-MAN-0193/0200)
# =============================================================================
DTNA_SPN = {
    # NOx Outlet Sensor codes
    520355: "NOx Outlet Sensor Diagnosis",
    5713: "NOx Outlet Sensor Self-Diagnosis",
    5714: "NOx Raw Sensor Self-Diagnosis",
}


# =============================================================================
# Body Controller SPN+FMI codes (S08327 - International models)
# Source Address 33 = Body Controller / ESC MSM
# Also applies to Freightliner/Western Star body controllers
# =============================================================================
DTNA_SPN_FMI = {
    # Ambient air temperature (SA 23 - Gauge Cluster)
    (171, 3): "Ambient Air Temperature - Voltage above normal",
    (171, 4): "Ambient Air Temperature - Voltage below normal",
    
    # ABS/EBS warning lamps (SA 23)
    (1438, 5): "ABS/EBS Amber Warning Lamp State - Malfunction",
    (1439, 5): "EBS Red Warning Lamp State - Malfunction",
    
    # ESC communication loss (SA 23)
    (2023, 14): "Gauge Cluster lost communication with ESC (>10s)",
    (2033, 9): "Loss of data link from ESC (Abnormal update rate)",
    
    # Body Controller internal codes (SA 33)
    (1231, 9): "Body Address Claim/Message Timeout - Data link lost",
    (1231, 14): "Global broadcast messages unknown fault",
    
    # Brake switch circuits (SA 33)
    (597, 14): "Brake Switch - Inputs do not match",
    
    # HVAC compressor/clutch (SA 33)
    (876, 5): "HVAC Compressor Clutch Engagement Undercurrent",
    (876, 6): "HVAC Compressor Clutch Engagement Overcurrent",
    
    # HVAC evaporator temperature (SA 33)
    (1547, 0): "A/C Evaporator Temperature - Sensor reading above normal",
    (1547, 1): "A/C Evaporator Temperature - Sensor reading below normal",
    
    # HVAC duct temperature (SA 33)
    (1548, 0): "HVAC Duct Temperature - Sensor reading above normal",
    (1548, 1): "HVAC Duct Temperature - Sensor reading below normal",
    
    # HVAC actuator/motor faults (SA 33)
    (3981, 2): "Cab HVAC Mode Control Actuator - Motor jammed",
    (3982, 2): "Cab HVAC Rear Blower Speed Control Switch Error",
    (3983, 2): "Cab HVAC Rear Temperature Control Switch Error",
    (3984, 2): "Cab HVAC Recirculation Door Control Actuator - Motor jammed",
    (3985, 9): "Cab HVAC System Controller - Failed to communicate with BC",
    
    # HVAC pressure sensors (SA 33)
    (2609, 0): "Cab A/C Refrigerant Compressor Outlet Pressure - Above normal",
    (2609, 1): "Cab A/C Refrigerant Compressor Outlet Pressure - Below normal",
    (2609, 7): "AC - Service Now. Fan Problem/Clogged Pipe",
    (2609, 16): "HVAC Head Pressure exceeded 480 psi - Compressor shut off",
    
    # Horn (SA 33)
    (2641, 5): "Electric Horn Undercurrent - Open circuit",
    (2641, 6): "Electric Horn Overcurrent",
    
    # Fog lights (SA 33)
    (2388, 5): "Fog Light 1 command - Relay undercurrent or open circuit",
    
    # Fifth wheel locks (SA 33)
    (3313, 6): "Fifth Wheel Jaw Unlock Solenoid 1 - Overcurrent",
    
    # PTO controls (SA 33)
    (3452, 2): "Enable Switch - Transmission input shaft PTO - Switch error",
    (3461, 6): "Engagement Status - Transmission input shaft PTO - Solenoid overcurrent",
    
    # Air horn (SA 33)
    (3950, 5): "Air Horn Undercurrent - Open circuit",
    
    # Auxiliary pump inhibit (SA 33)
    (3961, 5): "Body Equipment Hydraulic Power Auxiliary Pump Inhibit - Relay undercurrent",
    (3961, 6): "Body Equipment Hydraulic Power Auxiliary Pump Inhibit - Relay overcurrent",
    
    # Bus signal lights (SA 33)
    (3971, 6): "Bus Red Signal Light 1 - Overcurrent",
    
    # Dome lights (SA 33)
    (3978, 2): "Cab Dome Light 2 Switch Error",
    
    # Compression brake indicator (SA 33)
    (3987, 5): "Compression Brake Enable Switch Indicator Lamp - Undercurrent or open circuit",
    
    # Exterior lamp check (SA 33)
    (4004, 2): "Exterior Lamp Check Switch Error",
    
    # Service brake circuit (SA 33)
    (4030, 5): "Service Brake Circuit 2 Air Tank Drain Valve - Undercurrent or open circuit",
    
    # Snow plow lights (SA 33)
    (4040, 2): "Snow Plow Lighting Mode Switch Error",
    (4041, 14): "Software Loop Time Exceeded - Internal fault",
    
    # Switch pack data link (SA 33)
    (520462, 9): "Switch 6-Pack #2 Data Link Comm. Failure",
    
    # HVAC multiple motor faults (SA 33)
    (520465, 2): "HVAC Control Head Multiple Motor Faults",
    
    # RPM channel switches (SA 33)
    (520482, 2): "RPM 2 Channel 2 Cab Switch Error",
    (520487, 6): "RPM 2 Channel 4 Overcurrent",
    (520491, 6): "RPM 2 Channel 6 Overcurrent",
    
    # RPM channel analog input (SA 33)
    (520511, 19): "RPM 4 Channel 4 Analog Input Invalid Data",
    
    # RPM channel overcurrent (SA 33)
    (520543, 19): "RPM 7 Channel 2 Overcurrent",
    
    # Air horn solenoid (SA 33)
    (520649, 5): "Air Horn Solenoid Command - Undercurrent or open circuit",
    (520649, 6): "Air Horn Solenoid Command - Overcurrent",
    
    # Auxiliary pump inhibit relay (SA 33)
    (520658, 5): "Body Equipment Hydraulic Power Auxiliary Pump Inhibit - Relay undercurrent",
    (520658, 6): "Body Equipment Hydraulic Power Auxiliary Pump Inhibit - Relay overcurrent",
    
    # Door pod module fault (SA 33)
    (520687, 12): "Defective Rear Passenger Door Pod Module",
    
    # Remote start command (SA 33)
    (520687, 5): "Engine Remote Start Command - Relay undercurrent or open circuit",
    
    # Headlamp high beam (SA 33)
    (520693, 5): "Headlamp High Beam Command 1 - Open circuit",
    (520693, 6): "Headlamp High Beam Command 1 - Short to ground",
    
    # HVAC actuator faults (SA 33)
    (520695, 2): "HVAC Mode Control Actuator - Motor jammed",
    (520696, 2): "HVAC Recirculation Door Control Actuator - Motor jammed",
    (520697, 9): "HVAC System Controller - Failed to communicate with BC",
    
    # Load shed relay (SA 33)
    (520706, 6): "Load Shed ON Relay Overcurrent",
    
    # BC internal fault (SA 33)
    (520707, 14): "Loop Time Exceeded - Internal fault, configuration too big",
    
    # Rear HVAC blower switch (SA 33)
    (520713, 2): "Rear HVAC Blower Speed Control Switch Error",
    (520714, 2): "Rear HVAC Temperature Control Switch Error",
    
    # Snow plow switch (SA 33)
    (520722, 2): "Snow Plow Lighting Mode Switch Error",
    
    # Transfer case solenoids (SA 33)
    (520736, 5): "Transfer Case Low Range Solenoid Command - Undercurrent or open circuit",
    (520742, 6): "Transfer Case Rear Driveline Solenoid Command - Overcurrent",
    
    # Wiper motor (SA 33)
    (520748, 5): "Wiper Motor Undercurrent - Open circuit",
    
    # Universal air solenoid relays (SA 33)
    (520754, 6): "Universal Air Solenoid Relay Driver 2 - Overcurrent",
    (520758, 5): "Universal Air Solenoid Relay Driver 6 - Undercurrent or open circuit",
    (520762, 6): "Universal Air Solenoid Relay Driver 10 - Overcurrent",
    (520766, 5): "Universal Air Solenoid Relay Driver 14 - Undercurrent or open circuit",
    
    # Spare relay driver (SA 33)
    (520769, 6): "BUS Spare Relay Driver One - Overcurrent",
    
    # Anti-theft switch (SA 33)
    (520777, 2): "Anti Theft Switch 0 Error",
    
    # TEG aux relay (SA 33)
    (520799, 6): "TEG Aux Relay Driver 2 - Overcurrent",
    
    # Sixth gear disable LED (SA 33)
    (520816, 5): "Sixth Gear Disable LED Relay Driver Output - Undercurrent or open circuit",
    
    # HEV ePTO pressure feedback (SA 33)
    (520818, 0): "HEV ePTO Pressure Feedback - Sensor reading above normal",
    
    # Remote condenser fan (SA 33)
    (520822, 5): "Remote Condenser Electric Fan Control A - Undercurrent or open circuit",
    (520822, 6): "Remote Condenser Electric Fan Control A - Short-circuit",
    
    # Transfer case odometer relay (SA 33)
    (520839, 6): "Transfer Case Output Shaft Odometer Shutoff Relay - Overcurrent",
    
    # HVAC condenser pusher fan (SA 33)
    (520868, 5): "HVAC Condenser Pusher Fan Relay - Undercurrent or open circuit",
    (520868, 6): "HVAC Condenser Pusher Fan Relay - Overcurrent",
    
    # NEC park brake command (SA 33)
    (520774, 6): "NEC Park Brake Command - Overcurrent",
    
    # Switch pack locations (SA 33) - FMI 13 = Out of calibration
    (520840, 13): "Switch 12-Pack Location 7 - Unexpected switch position",
    (520846, 13): "Switch 12-Pack Location 1 - Unexpected switch position",
    (520847, 13): "Switch 12-Pack Location 2 - Unexpected switch position",
    (520852, 13): "Switch 6-Pack #2 Location 1 - Unexpected switch position",
    (520853, 13): "Switch 6-Pack #2 Location 2 - Unexpected switch position",
    (520923, 13): "Switch 6-Pack #3 Location 2 - Unexpected switch position",
    (520929, 13): "AGSP Switch Location 1 - Unexpected switch position",
    (520936, 13): "Cluster Switch Location 2 - Unexpected switch position",
    
    # AGSP communication loss (SA 132)
    (2023, 14): "Auxiliary Gauge Switch Pack lost communication with ESC",
    (2033, 9): "Loss of data link from ESC (AGSP)",
    (2132, 11): "AGSP #3 - Accessory and switched accessory do not match",
    (2132, 12): "AGSP #3 - Non-volatile memory or checksum fault",
    
    # Rear HVAC communication (SA 58)
    (2058, 9): "Rear HVAC Data Link Communication Failure",
    (2058, 14): "Rear HVAC Data Link Communication Failure",
    
    # Rear HVAC evaporator sensor (SA 58)
    (1547, 1): "A/C Evaporator Temperature - Sensor reading below normal",
    (1548, 3): "HVAC Duct Temperature - Sensor voltage high",
    (1548, 4): "HVAC Duct Temperature - Sensor voltage low",
    
    # Rear HVAC blower output (SA 58)
    (520210, 3): "HVAC Blower Output - Over voltage",
    (520210, 4): "HVAC Blower Output - Under voltage",
    (520210, 6): "HVAC Blower Output - Short circuit",
    
    # Rear HVAC actuator position (SA 58)
    (520211, 7): "HVAC actuator position - Not responding",
    
    # Rear HVAC dimmer output (SA 58)
    (520212, 3): "HVAC Dimmer Output - Voltage high",
    (520212, 4): "HVAC Dimmer Output - Voltage low",
    
    # Rear HVAC evaporator sensor (SA 58)
    (520213, 3): "Evaporator Sensor High - Voltage above normal",
}


# =============================================================================
# Bulkhead Module SPN+FMI codes (SS 1032728 - Smart Switch/Bulkhead SA 33)
# =============================================================================
DTNA_SPN_FMI_BULKHEAD = {
    # Component ID mismatches (FMI 31 = Condition exists)
    (524280, 31): "Component ID mismatch - BHM in non-recoverable boot mode",
    
    # Application/parameter failures (FMI 31)
    (524281, 31): "Application to parameters fail - Reflash BHM",
    
    # Parameter data checksum failures (FMI 12 = Bad component)
    (524282, 12): "Parameter data fails checksum - Reflash BHM",
    (524283, 12): "Application code fails checksum - Reflash BHM",
    
    # Boot block checksum failure (FMI 12)
    (524284, 12): "Boot block checksum fail - Replace BHM",
    
    # Boot hold line active (FMI 4 = Voltage below normal)
    (524285, 4): "Boot hold line is active - Replace BHM",
    
    # RAM test failures (FMI 12)
    (524286, 12): "RAM test fails EOF Feedback - Replace BHM",
}


# =============================================================================
# Module-level documentation for the lookup tables
# =============================================================================
"""
Usage in OpenTruck:

1. Module identification uses DTNA_ADDRESSES when VIN WMI identifies a DTNA chassis
   and a module never claims an address (NAME/CI still take precedence).

2. Fault code resolution uses DTNA_SPN_FMI for Body Controller codes and
   DTNA_SPN_FMI_BULKHEAD for Bulkhead Module codes.

3. Detroit DD aftertreatment codes use DTNA_SPN with FMI-specific descriptions
   resolved in the main resolve_code_description() function.

See lookup/oem.py for integration with the global OEM registry.
"""
