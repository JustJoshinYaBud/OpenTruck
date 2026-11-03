"""OpenTruck - SAE J1939 protocol decoding (J1939-21, -71, -73, -81).

Hardware-agnostic: everything here operates on decoded 29-bit CAN frames, so
the same code works whether frames come from an RP1210 adapter, a raw CAN
dongle, or a replay log.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Callable, Optional


class PGN(IntEnum):
    ADDRESS_CLAIMED = 0x00EE00   # 60928  NAME broadcast (J1939-81)
    REQUEST         = 0x00EA00   # 59904  "request" (e.g. re-claim addresses)
    TP_CM           = 0x00EC00   # 60416  Transport Protocol - Connection Mgmt
    TP_DT           = 0x00EB00   # 60160  Transport Protocol - Data Transfer
    DM1             = 0xFECA     # 65226  Active DTCs (+ lamp status)
    DM2             = 0xFECB     # 65227  Previously active DTCs
    DM3             = 0xFECC     # 65228  DTC clear request/response
    DM11            = 0xFED3     # 65235  Diagnostic Data Clear/Reset for ACTIVE DTCs
    DM55            = 0xFCD3     # 64723  Diagnostic Data Clear/Reset for SERVICE-ONLY DTCs
    DM22            = 0xC300     # 49920  Individual Clear/Reset of one Active/Previously-Active DTC
    CI              = 0xFEEB     # 65259  Component Identification (make/model/serial)
    VI              = 0xFEEC     # 65260  Vehicle Identification (VIN)
    SOFTWARE_ID     = 0xFEDA     # 65242  Software Identification (SPN 234)
    ECU_ID          = 0xFDC5     # 64965  ECU Identification Information (part/serial/location/type)
    # NOTE: 65005 (0xFDED) is "Utility Total AC Energy", NOT ECU ID - a
    # long-standing wrong constant here meant the tool requested/parsed the
    # wrong PGN and never saw real ECU part/serial. Guarded by check_j1939.
    ACK             = 0x00E800   # 59392  Acknowledgement (J1939-73)
    # --- live data examples (for later) ---
    EEC1            = 0xF004     # 61444  engine speed / driver demand torque
    EEC4            = 0xFEBE     # 65214  rated engine power / rated speed
    ECT1            = 0xFEEE     # 65262  coolant temp / fuel rate
    VDH             = 0xFEF1     # 65265  vehicle distance / road speed
    AMB             = 0xFEF5     # 65269  ambient air temp / baro pressure
    EBC1            = 0xF001     # 61441  brakes/ABS status + brake pedal position
    WHEEL_SPEED     = 0xFEBF     # 65215  wheel speed information (SPN 904)
    TC1             = 0x00100    # 256    transmission control 1 (requests)
    ETC7            = 0xFE4A     # transmission warning/service indicators
    PTO             = 0xFEF0     # power takeoff speed / oil temp
    BRAKES1         = 0xFEFA     # brake application pressure etc.
    AIR_SUPPLY      = 0xFEAE     # pneumatic / service-brake air pressure
    VEHICLE_HOURS   = 0xFEE7     # total vehicle + PTO hours
    RC              = 0xFEE1     # retarder config: reference retarder torque
    EC1             = 0xFEE3     # engine config: idle speed, reference torque
    AT1TI           = 0xFD79     # 64889  DPF regeneration trip statistics
    # SCR gas sensors. Both are BROADCAST PGNs but no captured truck has ever
    # emitted them, so they ride the request rotation: asking costs one frame
    # and is the only way to learn whether an SCR-equipped chassis answers.
    AT1IG1          = 0xF00E     # 61454  aftertreatment 1 intake gas 1 (NOx / O2)
    AT1OG1          = 0xF00F     # 61455  aftertreatment 1 outlet gas 1 (NOx / O2)


# J1939-73 Acknowledgement (PGN 0x00E800) control bytes. An ECU answers a
# request with one of these: a plain ACK, or a NACK reporting that the answer is
# merely late ("response pending"), refused, or impossible. They matter in
# practice: an ECU that cannot answer a VIN / DM2 request within one poll sends
# "response pending" first and the data afterwards, so a tool that ignores the
# acknowledgement reports "no data" for a controller that is about to reply.
ACK_CONTROL = {
    0: "ACK",
    1: "NACK - response pending",
    2: "NACK - access denied",
    3: "NACK - cannot respond",
}
ACK_RESPONSE_PENDING = 1


def decode_ack(data: bytes) -> Optional[dict]:
    """Decode an Acknowledgement payload.

    J1939-73 layout: ``[0]`` control byte, ``[1]`` group-function value,
    ``[2:5]`` reserved (0xFF), ``[5:8]`` the acknowledged PGN (little-endian).
    Returns ``{"control", "name", "pgn"}`` or None for a short frame.
    """
    if len(data) < 8:
        return None
    control = data[0]
    return {
        "control": control,
        "name": ACK_CONTROL.get(control, f"control {control}"),
        "pgn": int.from_bytes(data[5:8], "little"),
    }


@dataclass
class Frame:
    pgn: int                 # Parameter Group Number (18-bit)
    data: bytes
    source: int = 0          # source address (the ECU that sent it)
    destination: int = 0xFF  # destination address (0xFF = broadcast)
    priority: int = 6
    timestamp: float = 0.0

    @classmethod
    def from_arbid(cls, arbid: int, data: bytes, timestamp: float = 0.0) -> "Frame":
        """Build a Frame from a raw 29-bit CAN identifier."""
        return cls(
            pgn=pgn_from_id(arbid),
            data=data,
            source=arbid & 0xFF,
            destination=(arbid >> 8) & 0xFF,
            priority=(arbid >> 26) & 0x07,
            timestamp=timestamp,
        )

    def to_arbid(self) -> int:
        """Reconstruct the 29-bit CAN identifier (inverse of `from_arbid`)."""
        pgn = self.pgn
        edp = (pgn >> 17) & 0x01
        dp = (pgn >> 16) & 0x01
        pf = (pgn >> 8) & 0xFF
        ps = pgn & 0xFF
        # PDU1 (pf < 0xF0): PS field is actually the destination address.
        mid = (self.destination & 0xFF) if pf < 0xF0 else ps
        return ((self.priority & 0x07) << 26) | (edp << 25) | (dp << 24) \
               | (pf << 16) | (mid << 8) | (self.source & 0xFF)

    def to_log_line(self) -> str:
        """Serialize for the replay/log format: ``<arbid_hex>:<data_hex>``."""
        return f"{self.to_arbid():08X}:{self.data.hex().upper()}"


def pgn_from_id(arbid: int) -> int:
    """Extract the 18-bit Parameter Group Number from a 29-bit CAN id.

    The identifier is priority(3) | EDP(1) | DP(1) | PF(8) | PS(8) | SA(8), so
    a PGN is 18 bits: EDP (bit 17), DP (bit 16), PF, PS. J1939 requires EDP to
    be 0, but it is carried through rather than masked away - a non-conforming
    frame then round-trips honestly instead of collapsing into the standard PGN
    that happens to share its DP/PF/PS bits.
    """
    pf = (arbid >> 16) & 0xFF
    ps = (arbid >> 8) & 0xFF
    edp = (arbid >> 25) & 0x01
    dp = (arbid >> 24) & 0x01
    if pf < 0xF0:                        # PDU1: destination-specific (PS == DA)
        return (edp << 17) | (dp << 16) | (pf << 8)
    return (edp << 17) | (dp << 16) | (pf << 8) | ps   # PDU2: broadcast


# --------------------------------------------------------------------------- #
# NAME decoding (J1939-81): what kind of ECU is on each address               #
# --------------------------------------------------------------------------- #

@dataclass
class Name:
    identity: int
    manufacturer: int
    ecu_instance: int
    function_instance: int
    function: int
    vehicle_system: int
    industry_group: int
    arbitrary_addr_capable: bool


def decode_name(data: bytes) -> Name:
    """Decode a 64-bit J1939 NAME (8 bytes little-endian) from an Address
    Claimed message payload."""
    n = int.from_bytes(data[:8], "little")
    return Name(
        identity               = n & 0x1FFFFF,
        manufacturer           = (n >> 21) & 0x7FF,
        ecu_instance           = (n >> 32) & 0x07,
        function_instance      = (n >> 35) & 0x1F,
        function               = (n >> 40) & 0xFF,
        vehicle_system         = (n >> 49) & 0x0F,
        industry_group         = (n >> 58) & 0x1F,
        arbitrary_addr_capable = bool((n >> 63) & 0x01),
    )


# NAME "Function" field (SPN 2841), global range (values 0-127).
# Source: SAE J1939-71 Appendix B Table B11 / SAE J1939DA, cross-checked
# against the Wireshark/ISOBUS tables (GPL-2.0-or-later, generated from the
# isobus.net public listings). Values 0-94 are the currently-assigned global
# functions. Values 128-254 are industry-group/vehicle-system specific
# (Table B12) and are NOT resolvable from the function byte alone, so
# function_name() leaves them unknown rather than guess.
FUNCTION_NAMES = {
    0: 'Engine',
    1: 'Auxiliary Power Unit (APU)',
    2: 'Electric Propulsion Control',
    3: 'Transmission',
    4: 'Battery Pack Monitor',
    5: 'Shift Control/Console',
    6: 'Power TakeOff - (Main or Rear)',
    7: 'Axle - Steering',
    8: 'Axle - Drive',
    9: 'Brakes - System Controller',
    10: 'Brakes - Steer Axle',
    11: 'Brakes - Drive axle',
    12: 'Retarder - Engine',
    13: 'Retarder - Driveline',
    14: 'Cruise Control',
    15: 'Fuel System',
    16: 'Steering Controller',
    17: 'Suspension - Steer Axle',
    18: 'Suspension - Drive Axle',
    19: 'Instrument Cluster',
    20: 'Trip Recorder',
    21: 'Cab Climate Control',
    22: 'Aerodynamic Control',
    23: 'Vehicle Navigation',
    24: 'Vehicle Security',
    25: 'Network Interconnect ECU',
    26: 'Body Controller',
    27: 'Power TakeOff (Secondary or Front)',
    28: 'Off Vehicle Gateway',
    29: 'Virtual Terminal (in cab)',
    30: 'Management Computer',
    31: 'Propulsion Battery Charger',
    32: 'Headway Controller',
    33: 'System Monitor',
    34: 'Hydraulic Pump Controller',
    35: 'Suspension - System Controller',
    36: 'Pneumatic - System Controller',
    37: 'Cab Controller',
    38: 'Tire Pressure Control',
    39: 'Ignition Control Module',
    40: 'Seat Control',
    41: 'Lighting - Operator Controls',
    42: 'Water Pump Control',
    43: 'Transmission Display',
    44: 'Exhaust Emission Control',
    45: 'Vehicle Dynamic Stability Control',
    46: 'Oil Sensor Unit',
    47: 'Information System Controller',
    48: 'Ramp Control',
    49: 'Clutch/Converter Control',
    50: 'Auxiliary Heater',
    51: 'Forward-Looking Collision Warning System',
    52: 'Chassis Controller',
    53: 'Alternator/Charging System',
    54: 'Communications Unit, Cellular',
    55: 'Communications Unit, Satellite',
    56: 'Communications Unit, Radio',
    57: 'Steering Column Unit',
    58: 'Fan Drive Control',
    59: 'Starter',
    60: 'Cab Display',
    61: 'File Server / Printer',
    62: 'On-Board Diagnostic Unit',
    63: 'Engine Valve Controller',
    64: 'Endurance Braking',
    65: 'Gas Flow Measurement',
    66: 'I/O Controller',
    67: 'Electrical System Controller',
    68: 'Aftertreatment system gas measurement',
    69: 'Engine Emission Aftertreatment System',
    70: 'Auxiliary Regeneration Device',
    71: 'Transfer Case Control',
    72: 'Coolant Valve Controller',
    73: 'Rollover Detection Control',
    74: 'Lubrication System',
    75: 'Supplemental Fan',
    76: 'Temperature Sensor',
    77: 'Fuel Properties Sensor',
    78: 'Fire Suppression System',
    79: 'Power Systems Manager',
    80: 'Electric Powertrain',
    81: 'Hydraulic Powertrain',
    82: 'File Server',
    83: 'Printer',
    84: 'Start Aid Device',
    85: 'Engine Injection Control Module',
    86: 'EV Communication Controller',
    87: 'Driver Impairment Device',
    88: 'Electric Power Converter',
    89: 'Supply Equipment Communication Controller (SECC)',
    90: 'Vehicle Adapter Communication Controller (VACC)',
    91: 'Accessory Electric Motor Controller',
    92: 'Current Sensor',
    93: 'Fuel Cell System',
    94: 'Auxiliary Display',
}


# J1939 Table B12: industry-group/vehicle-system specific NAME functions
# (values 128-254). Key = (industry_group << 16) | (vehicle_system << 8) |
# function, the same compound key the source uses; entries with key < 256
# are the IG 0 / VS 0 ("applies to all industries", non-specific system)
# assignments. Lookup is EXACT - the same number means different things per
# vehicle system (IG1/VS0 129 = Door Controller, IG1/VS1 129 = Fifth Wheel
# Smart System), so there is no cross-system fallback. Source: SAE J1939-81 /
# J1939DA via the Wireshark ISOBUS tables (GPL-2.0-or-later, generated from
# the isobus.net public listings).
IG_SPECIFIC_NAME_FUNCTIONS = {
    128: 'Reserved',
    129: 'Off-board diagnostic-service tool',
    130: 'On-board data logger',
    131: 'PC Keyboard',
    132: 'Safety Restraint System',
    133: 'Turbocharger',
    134: 'Ground based speed sensor',
    135: 'Keypad',
    136: 'Humidity sensor',
    137: 'Thermal Management System Controller',
    138: 'Brake Stroke Alert',
    139: 'On-board axle group scale',
    140: 'On-board axle group display',
    141: 'Battery Charger',
    142: 'Turbocharger Compressor Bypass',
    143: 'Turbocharger Wastegate',
    144: 'Throttle',
    145: 'Inertial Sensor',
    146: 'Fuel Actuator',
    147: 'Engine Exhaust Gas Recirculation',
    148: 'Engine Exhaust Backpressure',
    149: 'On-board bin weighing scale',
    150: 'On-board bin weighing scale display',
    151: 'Engine Cylinder Pressure Monitoring System',
    152: 'Object Detection',
    153: 'Object Detection Display',
    154: 'Object Detection Sensor',
    155: 'Personnel Detection Device',
    255: 'Not Available',
    32767: 'Not Available',
    65664: 'Tachograph',
    65665: 'Door Controller',
    65666: 'Articulation Turntable Control',
    65667: 'Body-to-Vehicle Interface Control',
    65668: 'Slope Sensor',
    65670: 'Retarder Display',
    65671: 'Differential Lock Controller',
    65672: 'Low-Voltage Disconnect',
    65673: 'Roadway Information',
    65674: 'Automated Driving',
    65791: 'Not Available',
    65920: 'Forward Road Image Processing',
    65921: 'Fifth Wheel Smart System',
    65922: 'Catalyst Fluid Sensor',
    65923: 'Adaptive Front Lighting System',
    65924: 'Idle Control System',
    65925: 'User Interface System',
    66047: 'Not Available',
    66303: 'Not Available',
    98303: 'Not Available',
    131200: 'Non Virtual Terminal Display',
    131201: 'Operator Controls - Machine Specific',
    131202: 'Task Controller (Mapping Computer)',
    131203: 'Position Control',
    131204: 'Machine Control',
    131205: 'Foreign Object Detection',
    131206: 'Tractor ECU',
    131207: 'Sequence Control Master',
    131208: 'Product Dosing',
    131209: 'Product Treatment',
    131210: 'reserved',
    131211: 'Data Logger',
    131212: 'Decision Support',
    131213: 'Lighting Controller',
    131214: 'TIM Server',
    131327: 'Not Available',
    131457: 'Auxiliary Valve Control',
    131458: 'Rear Hitch Control',
    131459: 'Front Hitch Control',
    131460: 'Tractor Machine Control',
    131462: 'Center Hitch Control',
    131583: 'Not Available',
    131716: 'Tillage Machine Control',
    131719: 'Tillage Depth Control',
    131720: 'Frame Control',
    131839: 'Not Available',
    131972: 'Secondary Tillage Machine Control',
    131975: 'Secondary Tillage Depth Control',
    131976: 'Frame Control',
    132095: 'Not Available',
    132224: 'Seed Rate Control',
    132225: 'Section On/Off Control',
    132227: 'Position Control',
    132228: 'Planters/ Seeders Machine Control',
    132229: 'Product Flow',
    132230: 'Product Level',
    132231: 'Depth Control',
    132232: 'Frame Control',
    132233: 'Down Pressure',
    132351: 'Not Available',
    132480: 'Fertilize Rate Control',
    132481: 'Section On/Off Control',
    132482: 'Product Pressure',
    132483: 'Position Control',
    132484: 'Fertilizers Machine Control',
    132485: 'Product Flow',
    132486: 'Product Level',
    132487: 'Height/Depth Control',
    132488: 'Frame Control',
    132607: 'Not Available',
    132736: 'Spray Rate Control',
    132737: 'Section On/Off Control',
    132738: 'Product Pressure',
    132739: 'Position Control',
    132740: 'Sprayers Machine Control',
    132741: 'Product Flow',
    132742: 'Product Level',
    132743: 'Boom Height Control',
    132744: 'Frame Control',
    132863: 'Not Available',
    132992: 'Tailing Monitor',
    132993: 'Header Control',
    132994: 'Product Loss Monitor',
    132995: 'Product Moisture',
    132996: 'Harvester Machine Control',
    132997: 'Product Flow',
    132998: 'Product Level',
    132999: 'Header Height Control',
    133119: 'Not Available',
    133252: 'Root Harvesters Machine Control',
    133253: 'Product Flow',
    133254: 'Product Level',
    133255: 'Depth Control',
    133375: 'Not Available',
    133504: 'Twine Wrapper Control',
    133505: 'Product Packaging Control',
    133507: 'Product Moisture',
    133508: 'Forage Machine Control',
    133509: 'Product Flow',
    133511: 'Working Height Control',
    133631: 'Not Available',
    133887: 'Not Available',
    134020: 'Transport Machine Control',
    134024: 'Unload Control',
    134143: 'Not Available',
    134399: 'Not Available',
    134532: 'Powered Devices Machine Control',
    134655: 'Not Available',
    134788: 'Special Crop Machine Control',
    134911: 'Not Available',
    135040: 'Material Rate Control',
    135044: 'Earthworks Machine Control',
    135045: 'Material Flow',
    135046: 'Material Level',
    135047: 'Depth Control',
    135167: 'Not Available',
    135300: 'Skidder Machine Control',
    135423: 'Not Available',
    135552: 'Guidance Feeler',
    135553: 'Camera System',
    135554: 'Crop Scouting ',
    135555: 'Material Properties Sensing',
    135556: 'Inertial Measurement Unit (IMU)',
    135557: 'Product flow',
    135558: 'Product Level ',
    135559: 'Product Mass',
    135560: 'Vibration/Knock',
    135561: 'Weather Instruments',
    135562: 'Soil Scouting',
    135563: 'Transmission Shaft',
    136068: 'Timber Harvestors Machine Control',
    136324: 'Forwarders Machine Control',
    136580: 'Timber Loaders Machine Control',
    136836: 'Timber Processing Machine Control',
    137092: 'Mulcher Machine Control',
    137348: 'Utility Machine Control',
    137600: 'Slurry/Manure Rate Control',
    137601: 'Section On/Off Control',
    137602: 'Product Pressure',
    137604: 'Slurry/Manure Machine Control',
    137605: 'Product Flow',
    137606: 'Product Level',
    137607: 'Boom Height Control',
    137856: 'Feeder/Mixer Rate Control',
    137857: 'Section On/Off Control',
    137858: 'Product Pressure',
    137860: 'Feeder/Mixer Machine Control',
    137861: 'Product Flow',
    137862: 'Product Level',
    137863: 'Boom Height Control',
    138116: 'Weeder Machine Control',
    138372: 'Turf and Lawn Care Mowers Machine Control',
    138628: 'Product/Material Handling Machine Control',
    138629: 'Product/Material Handling Product Flow',
    138630: 'Product/Material Handling Product Level',
    163839: 'Not Available',
    196736: 'Supplemental Engine Control Sensing',
    196737: 'Laser Receiver',
    196738: 'Land Leveling System Operator Interface',
    196739: 'Land Leveling Electric Mast',
    196740: 'Single Land Leveling System Supervisor',
    196741: 'Land Leveling System Display',
    196742: 'Laser Tracer',
    196743: 'Loader Control',
    196744: 'Slope Sensor',
    196745: 'Liftarm Control',
    196746: 'Supplemental Sensor Processing Units',
    196747: 'Hydraulic System Planner',
    196748: 'Hydraulic Valve Controller',
    196749: 'Joystick Control',
    196750: 'Rotation Sensor',
    196751: 'Sonic Sensor',
    196752: 'Survey Total Station Target',
    196753: 'Heading Sensor',
    196754: 'Alarm device',
    196863: 'Not Available',
    196992: 'Main Controller',
    197119: 'Not Available',
    197375: 'Not Available',
    197631: 'Not Available',
    197760: 'Blade Controller',
    197887: 'Not Available',
    198016: 'Slope Sensor',
    198143: 'Not Available',
    198399: 'Not Available',
    198655: 'Not Available',
    198784: 'HFWD Controller',
    198911: 'Not Available',
    199167: 'Not Available',
    199423: 'Not Available',
    199679: 'Not Available',
    199935: 'Not Available',
    200191: 'Not Available',
    200447: 'Not Available',
    200703: 'Not Available',
    200959: 'Not Available',
    201215: 'Not Available',
    229375: 'Not Available',
    262272: 'Alarm System Control for Marine Engines',
    262273: 'Protection System for Marine Engines',
    262274: 'Display for Protection System for Marine Engines',
    262399: 'Not Available',
    264959: 'Not Available',
    267519: 'Not Available',
    268674: '',
    269954: 'Switch ',
    269964: 'Load ',
    272514: 'Follow-up Controller',
    272524: 'Mode Controller',
    272534: 'Automatic Steering Controller',
    272544: 'Heading Sensors',
    275074: 'Engineroom monitoring',
    275084: 'Engine Interface',
    275094: 'Engine Controller',
    275104: 'Engine Gateway',
    275114: 'Control Head',
    275124: 'Actuator',
    275134: 'Gauge Interface',
    275144: 'Gauge Large',
    275154: 'Gauge Small',
    275164: 'Propulsion Sensors & Gateway',
    277634: 'Sounder, depth   ',
    277644: '',
    277649: 'Global Navigation Satellite System (GNSS)',
    277654: 'Loran C',
    277659: 'Speed Sensors',
    277664: 'Turn Rate Indicator',
    277674: 'Integrated Navigation   ',
    277704: 'Radar and/or Radar Plotting',
    277709: 'Electronic Chart Display & Information System (ECDIS)',
    277714: 'Electronic Chart System (ECS)',
    277724: 'Direction Finder',
    280194: 'Emergency Position Indicating Beacon (EPIRB)',
    280204: 'Automatic Identification System',
    280214: 'Digital Selective Calling (DSC)',
    280224: 'Data Receiver',
    280234: 'Satellite',
    280244: 'Radio-Telephone (MF/HF)',
    280254: 'Radio-Telephone (VHF)',
    282754: 'Time/Date systems',
    282764: 'Voyage Data Recorder',
    282774: 'Integrated Instrumentation',
    282784: 'General Purpose Displays',
    282794: 'General Sensor Box',
    282804: 'Weather Instruments',
    282814: 'Transducer/general',
    282824: 'NMEA 0183 Converter',
    285439: 'Not Available',
    287999: 'Not Available',
    294911: 'Not Available',
    327808: 'Supplemental Engine Control Sensing',
    327809: 'Generator Set Controller',
    327810: 'Generator Voltage Regulator',
    327811: 'Choke Actuator',
    327812: 'Well Stimulation Pump',
    327935: 'Not Available',
    360447: 'Not Available',
}

# Values that resolve in the table but are not a usable module label.
_IG_NON_LABELS = {"Reserved", "Not Available"}


def function_name(function: int, industry_group: Optional[int] = None,
                  vehicle_system: Optional[int] = None) -> str:
    """Name for a NAME Function field value (SPN 2841).

    Global values (0-94 assigned in FUNCTION_NAMES) resolve on their own.
    Values 128-254 are industry-group / vehicle-system specific (Table B12)
    and only resolve when both context fields are supplied; 255 is the
    documented "Not Available". Anything else stays explicitly unknown -
    the same number means different things in different contexts, so this
    never guesses.
    """
    got = FUNCTION_NAMES.get(function)
    if got:
        return got
    if 128 <= function <= 254 and industry_group is not None:
        key = ((industry_group & 0x1F) << 16) | ((vehicle_system or 0) << 8) | function
        got = IG_SPECIFIC_NAME_FUNCTIONS.get(key)
        if got:
            return got
    if function == 255:
        return "Not Available"
    return f"Function {function} (unknown)"


def name_function_label(name) -> Optional[str]:
    """The module's true function label from its NAME, or None.

    Global functions resolve from FUNCTION_NAMES; 128-254 resolve via the
    NAME's own industry group + vehicle system. "Reserved" and "Not
    Available" are assignments, not labels - None makes the caller fall
    back to the preferred-address role instead of showing a non-answer.
    """
    if name is None:
        return None
    got = FUNCTION_NAMES.get(name.function)
    if not got and 128 <= name.function <= 254:
        key = (((name.industry_group & 0x1F) << 16)
               | ((name.vehicle_system & 0x7F) << 8) | name.function)
        got = IG_SPECIFIC_NAME_FUNCTIONS.get(key)
    if got is None or got in _IG_NON_LABELS:
        return None
    return got



def encode_name(identity: int, manufacturer: int = 0, ecu_instance: int = 0,
                function_instance: int = 0, function: int = 0,
                vehicle_system: int = 0, industry_group: int = 0,
                arbitrary_addr_capable: bool = True) -> bytes:
    """Build the 8-byte J1939 NAME (inverse of :func:`decode_name`)."""
    n = ((identity & 0x1FFFFF)
         | ((manufacturer & 0x7FF) << 21)
         | ((ecu_instance & 0x07) << 32)
         | ((function_instance & 0x1F) << 35)
         | ((function & 0xFF) << 40)
         | ((vehicle_system & 0x0F) << 49)
         | ((industry_group & 0x1F) << 58)
         | ((1 if arbitrary_addr_capable else 0) << 63))
    return n.to_bytes(8, "little")


def build_address_claim(source: int, name: bytes,
                        priority: int = 6) -> "Frame":
    """An Address Claimed frame (PGN 0x00EE00) for ``source`` (J1939-81)."""
    return Frame(pgn=PGN.ADDRESS_CLAIMED, data=bytes(name[:8]), source=source,
                 destination=0xFF, priority=priority)


# The tool's J1939-81 identity on the bus: ONE NAME, shared by everything
# that ever claims an address for OpenTruck (the RP1210 ProtectJ1939Address
# command AND the on-wire Address Claimed broadcast).
#
# J1939-81 section 4.1.2: "A CA claiming a preferred address in the range 0 to
# 127 and 248 to 253 must perform the function defined for that preferred
# address and specify that Function within its NAME. Other CAs may assume
# that to be the case." OpenTruck claims 0xF9 (249, "Off-Board Diagnostic
# Tool #1"), so the NAME must declare the tool function - for industry group
# 0 / vehicle system 0 that is function 129, "Off-board Service Tool" (the
# same function a Dearborn DPA service-tool node declares). Claiming 0xF9
# while declaring function 0 ("Engine") - an earlier bug here - breaks that
# rule, and a strict ECU that takes the standard at its word can react badly
# to an "engine" sitting at the tool address.
#
# Manufacturer code 0 is "experimental or developmental" - honest for a
# community tool, and it cannot collide with a real vendor's code. The
# arbitrary-address-capable bit is deliberately 0: that bit PROMISES the
# node will move to an address in 128..247 if it loses a claim, and this tool
# does not do that (a refused claim means receive-only), so setting it would
# be another lie on the bus.
TOOL_IDENTITY = 0x0F9001
TOOL_FUNCTION = 0x81          # 129 = "Off-board Service Tool" (IG 0 / VS 0)


def offboard_tool_name(identity: int = TOOL_IDENTITY) -> bytes:
    """The 8-byte J1939-81 NAME for this tool (see the notes above)."""
    return encode_name(identity=identity, manufacturer=0, ecu_instance=0,
                      function_instance=0, function=TOOL_FUNCTION,
                      vehicle_system=0, industry_group=0,
                      arbitrary_addr_capable=False)


# Preferred source addresses (SAE J1939-71 "Global Preferred Addresses").
# Used as a *fallback* label for a module whose NAME (address-claim) was
# never captured and that has no Component Identification - the NAME/CI
# identity always wins. Complete assigned set: 0-89, then 248-253 (tools/
# logger/reserved); 128-247 are arbitrary/dynamic addresses and 255 is the
# GLOBAL destination, so neither is a claimable source-address label.
#
# NOTE: these are preferences, not guarantees. ECUs may use any address and
# OEMs reuse them (one truck's 0x0F really is the engine retarder; another
# puts a brake controller there), which is why this is only a last resort.
PREFERRED_ADDRESS_NAMES = {
    0x00: 'Engine #1',
    0x01: 'Engine #2',
    0x02: 'Turbocharger',
    0x03: 'Transmission #1',
    0x04: 'Transmission #2',
    0x05: 'Shift Console - Primary',
    0x06: 'Shift Console - Secondary',
    0x07: 'Power TakeOff - (Main or Rear)',
    0x08: 'Axle - Steering',
    0x09: 'Axle - Drive #1',
    0x0A: 'Axle - Drive #2',
    0x0B: 'Brakes - System Controller',
    0x0C: 'Brakes - Steer Axle',
    0x0D: 'Brakes - Drive axle #1',
    0x0E: 'Brakes - Drive Axle #2',
    0x0F: 'Retarder - Engine',
    0x10: 'Retarder - Driveline',
    0x11: 'Cruise Control',
    0x12: 'Fuel System',
    0x13: 'Steering Controller',
    0x14: 'Suspension - Steer Axle',
    0x15: 'Suspension - Drive Axle #1',
    0x16: 'Suspension - Drive Axle #2',
    0x17: 'Instrument Cluster #1',
    0x18: 'Trip Recorder',
    0x19: 'Passenger-Operator Climate Control #1',
    0x1A: 'Alternator/Electrical Charging System',
    0x1B: 'Aerodynamic Control',
    0x1C: 'Vehicle Navigation',
    0x1D: 'Vehicle Security',
    0x1E: 'Electrical System',
    0x1F: 'Starter System',
    0x20: 'Tractor-Trailer Bridge #1',
    0x21: 'Body Controller',
    0x22: 'Auxiliary Valve Control or Engine Air System Valve Control',
    0x23: 'Hitch Control',
    0x24: 'Power TakeOff (Front or Secondary)',
    0x25: 'Off Vehicle Gateway',
    0x26: 'Virtual Terminal (in cab)',
    0x27: 'Management Computer #1',
    0x28: 'Cab Display #1',
    0x29: 'Retarder, Exhaust, Engine #1',
    0x2A: 'Headway Controller',
    0x2B: 'On-Board Diagnostic Unit',
    0x2C: 'Retarder, Exhaust, Engine #2',
    0x2D: 'Endurance Braking System',
    0x2E: 'Hydraulic Pump Controller',
    0x2F: 'Suspension - System Controller #1',
    0x30: 'Pneumatic - System Controller',
    0x31: 'Cab Controller - Primary',
    0x32: 'Cab Controller - Secondary',
    0x33: 'Tire Pressure Controller',
    0x34: 'Ignition Control Module #1',
    0x35: 'Ignition Control Module #2',
    0x36: 'Seat Control #1',
    0x37: 'Lighting - Operator Controls',
    0x38: 'Rear Axle Steering Controller #1',
    0x39: 'Water Pump Controller',
    0x3A: 'Passenger-Operator Climate Control #2',
    0x3B: 'Transmission Display - Primary',
    0x3C: 'Transmission Display - Secondary',
    0x3D: 'Exhaust Emission Controller',
    0x3E: 'Vehicle Dynamic Stability Controller',
    0x3F: 'Oil Sensor',
    0x40: 'Suspension - System Controller #2',
    0x41: 'Information System Controller #1',
    0x42: 'Ramp Control',
    0x43: 'Clutch/Converter Unit',
    0x44: 'Auxiliary Heater #1',
    0x45: 'Auxiliary Heater #2',
    0x46: 'Engine Valve Controller',
    0x47: 'Chassis Controller #1',
    0x48: 'Chassis Controller #2',
    0x49: 'Propulsion Battery Charger',
    0x4A: 'Communications Unit, Cellular',
    0x4B: 'Communications Unit, Satellite',
    0x4C: 'Communications Unit, Radio',
    0x4D: 'Steering Column Unit',
    0x4E: 'Fan Drive Controller',
    0x4F: 'Seat Control #2',
    0x50: 'Parking brake controller',
    0x51: 'Aftertreatment #1 system gas intake',
    0x52: 'Aftertreatment #1 system gas outlet',
    0x53: 'Safety Restraint System',
    0x54: 'Cab Display #2',
    0x55: 'Diesel Particulate Filter Controller',
    0x56: 'Aftertreatment #2 system gas intake',
    0x57: 'Aftertreatment #2 system gas outlet',
    0x58: 'Safety Restraint System #2',
    0x59: 'Atmospheric Sensor',
    0xF8: 'File Server / Printer',
    0xF9: 'Off Board Diagnostic-Service Tool #1',
    0xFA: 'Off Board Diagnostic-Service Tool #2',
    0xFB: 'On-Board Data Logger',
    0xFC: 'Reserved for Experimental Use',
    0xFD: 'Reserved for OEM',
    0xFE: 'Null Address',
}


def preferred_address_name(address: int) -> Optional[str]:
    """Common name for a fixed/preferred source address, or None."""
    return PREFERRED_ADDRESS_NAMES.get(address)


# --------------------------------------------------------------------------- #
# DTC decoding (J1939-73): DM1 / DM2 payload -> SPN + FMI list                #
# --------------------------------------------------------------------------- #

@dataclass
class DTC:
    spn: int                 # Suspect Parameter Number (19 bits)
    fmi: int                 # Failure Mode Identifier (5 bits)
    occurrence: int          # Occurrence Count (7 bits)
    conversion_method: int   # SPN Conversion Method (1 bit)


def decode_dtc(b: bytes) -> DTC:
    # J1939-73: SPN bits 16-18 are the TOP 3 bits of byte 2 (bits 7..5) and
    # FMI is the BOTTOM 5 bits (4..0). A previous revision had these swapped.
    spn = b[0] | (b[1] << 8) | ((b[2] >> 5) << 16)
    return DTC(
        spn=spn,
        fmi=b[2] & 0x1F,
        occurrence=b[3] & 0x7F,
        conversion_method=(b[3] >> 7) & 0x01,
    )


def decode_lamp_status(b: bytes) -> dict:
    """Decode the 2-byte Lamp Status / Flash field at the head of a DM1/DM2."""
    if len(b) < 2:
        return {}
    b0, b1 = b[0], b[1]
    # J1939-73: 2 bits per lamp. Byte 0 (LSB-first): bits 1-0 protect,
    # 3-2 amber, 5-4 red, 7-6 MIL; byte 1 = the matching "flash" fields.
    # Status: 0b01=on, 0b00=off, 0b10=error, 0b11=not-available.
    # Flash:  0b00=slow flash, 0b01=fast flash, 0b10=reserved, 0b11=n/a.
    on = lambda v: v == 0x01
    flash = lambda v: (v & 0x02) == 0
    return {
        "protect":       on(b0 & 0x03),
        "amber":         on((b0 >> 2) & 0x03),
        "red":           on((b0 >> 4) & 0x03),
        "mil":           on((b0 >> 6) & 0x03),
        "protect_flash": flash(b1 & 0x03),
        "amber_flash":   flash((b1 >> 2) & 0x03),
        "red_flash":     flash((b1 >> 4) & 0x03),
        "mil_flash":     flash((b1 >> 6) & 0x03),
    }


def is_null_dtc(dtc: DTC) -> bool:
    """True for the J1939-73 "no active DTC" placeholder (SPN & FMI all-ones)
or the SPN=0/FMI=0 convention. These mean "no fault", not a real fault."""
    return (dtc.spn == 0x7FFFF and dtc.fmi == 31) or (dtc.spn == 0 and dtc.fmi == 0)


def parse_dm_payload(data: bytes) -> tuple[dict, list[DTC]]:
    """Parse a DM1/DM2 payload -> (lamps, [DTC, ...]) (null DTCs dropped)."""
    lamps = decode_lamp_status(data[:2])
    dtcs = [
        d
        for i in range(2, len(data) - 3, 4)
        for d in [decode_dtc(data[i:i + 4])]
        if not is_null_dtc(d)
    ]
    return lamps, dtcs


# --------------------------------------------------------------------------- #
# Transport Protocol (J1939-21): reassemble multi-frame messages              #
# --------------------------------------------------------------------------- #

# TP.CM control bytes (first data byte of a Connection-Management frame).
TP_RTS   = 0x10   # Request To Send  (peer-to-peer; receiver answers with CTS)
TP_CTS   = 0x11   # Clear To Send    (we SEND this)
TP_EOMA  = 0x13   # End Of Message Acknowledgement
TP_BAM   = 0x20   # Broadcast Announce Message (no handshake)
TP_ABORT = 0xFF   # session abort

# A session that stops receiving DT frames is dropped after this long, so a
# half-finished transfer cannot block the source address for ever.
TP_SESSION_TIMEOUT = 12.0


class TransportProtocol:
    """Reassembles multi-packet J1939 messages (J1939-21).

    DM1/DM2 with many DTCs, VIN, component ID and long live-data groups all
    exceed one 8-byte frame. J1939-21 defines two transfer modes:

    * **BAM** (control 0x20) - broadcast, no handshake. Works from a bus tap or
      a replay log, because nothing has to be transmitted.
    * **RTS/CTS** (control 0x10) - peer-to-peer, used whenever a *directed*
      request produces a multi-frame answer. The receiver must answer the
      sender's Request-To-Send with a Clear-To-Send before any data flows, and
      acknowledge completion with an End-Of-Message-ACK. Adapters that
      reassemble in firmware hide all of this; a raw-CAN path does not, and
      without it a directed VIN / component-ID / long-DM2 reply can never be
      collected at all.

    ``send`` is an optional callable used for the two frames a receiver must
    transmit. When it is None (replay, simulator, passive capture) BAM still
    reassembles and RTS sessions are tracked but left unanswered.
    """

    def __init__(self, source_address: Optional[int] = None,
                 send: Optional[Callable[["Frame"], None]] = None) -> None:
        self.source_address = source_address
        self.send = send
        self._sessions: dict[int, dict] = {}

    # -- inbound ---------------------------------------------------------- #
    def feed(self, frame: Frame) -> Optional[tuple[int, bytes]]:
        """Feed TP.CM / TP.DT frames.

        Returns (pgn, full_payload) when a message is complete, else None.
        """
        if frame.pgn == PGN.TP_CM:
            return self._connection_management(frame)
        if frame.pgn == PGN.TP_DT:
            return self._data_transfer(frame)
        return None

    def _connection_management(self, frame: Frame) -> Optional[tuple[int, bytes]]:
        """An RTS or BAM announce opens a session; CTS/EOMA/abort do not."""
        data = frame.data
        if len(data) < 8:
            return None
        ctrl = data[0]
        if ctrl in (TP_BAM, TP_RTS):
            size    = int.from_bytes(data[1:3], "little")
            packets = data[3]
            pgn     = int.from_bytes(data[5:8], "little")
            self._sessions[frame.source] = {
                "pgn": pgn, "size": size, "packets": packets,
                "chunks": {}, "started": time.monotonic(),
                "rts": ctrl == TP_RTS,
            }
            if ctrl == TP_RTS:
                self._send_cts(frame)
            return None
        if ctrl == TP_ABORT:
            self._sessions.pop(frame.source, None)
        return None

    def _send_cts(self, rts: Frame) -> None:
        """Answer a Request-To-Send with a Clear-To-Send for the whole message.

        A J1939-21 message is at most 255 packets, which fits the single
        "number of packets that can be sent" byte, so one CTS is enough - no
        windowed flow control is needed.
        """
        session = self._sessions.get(rts.source)
        if self.send is None or session is None:
            return
        # Reply from the address the RTS was addressed to: that is us.
        source = self.source_address
        if source is None:
            source = rts.destination if rts.destination not in (0xFE, 0xFF) else 0xF9
        allowed = min(session["packets"], 0xFF)
        frame = Frame(
            pgn=PGN.TP_CM, source=source, destination=rts.source, priority=6,
            data=bytes([TP_CTS, allowed, 1, 0xFF, 0xFF])
                 + session["pgn"].to_bytes(3, "little"),
        )
        try:
            self.send(frame)
        except Exception:          # noqa: BLE001 - a failed CTS is never fatal
            pass

    def _data_transfer(self, frame: Frame) -> Optional[tuple[int, bytes]]:
        session = self._sessions.get(frame.source)
        if session is None:
            return None
        if time.monotonic() - session["started"] > TP_SESSION_TIMEOUT:
            del self._sessions[frame.source]
            return None
        seq = frame.data[0]
        session["chunks"][seq] = frame.data[1:]
        if len(session["chunks"]) < session["packets"]:
            return None
        payload = bytearray()
        for i in range(1, session["packets"] + 1):
            payload += session["chunks"].get(i, b"")
        del self._sessions[frame.source]
        if session.get("rts"):
            self._send_eoma(frame.source, session)
        return session["pgn"], bytes(payload[:session["size"]])

    def _send_eoma(self, destination: int, session: dict) -> None:
        """Acknowledge a completed RTS/CTS message (End Of Message ACK)."""
        if self.send is None:
            return
        frame = Frame(
            pgn=PGN.TP_CM, source=self.source_address or 0xF9,
            destination=destination, priority=6,
            data=bytes([TP_EOMA])
                 + session["size"].to_bytes(2, "little")
                 + bytes([session["packets"], 0xFF])
                 + session["pgn"].to_bytes(3, "little"),
        )
        try:
            self.send(frame)
        except Exception:          # noqa: BLE001
            pass
