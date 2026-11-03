"""OpenTruck - PGN (Parameter Group Number) -> name lookup table.

Maps J1939 PGNs (standardized identifier numbers) to their canonical names,
used to label raw frames and as the reference for the live-data decoders in
livedata.py. PGN numbers and their group names are standardized facts.
"""
from __future__ import annotations

# PGN -> human name (complete list). Sorted numerically.
PGN_NAMES: dict[int, str] = {
    0x00100: "Transmission Control 1",   # 256
    0x00200: "Electronic Brake System #1/1",   # 512
    0x00300: "Electronic Brake System #2/1",   # 768
    0x00400: "External Brake Request",   # 1024
    0x00500: "CANopen Application Message #1/1",   # 1280
    0x00600: "CANopen Application Message #2/1",   # 1536
    0x00700: "General Purpose Valve Pressure",   # 1792
    0x00800: "Auxiliary Input/Output Status 5",   # 2048
    0x00900: "Static Roll Angle Sensor Information",   # 2304
    0x00A00: "Cruise Control / Vehicle Speed 2",   # 2560
    0x00B00: "Advanced Emergency Braking System 2",   # 2816
    0x00C00: "Electronic Engine Controller 16",   # 3072
    0x00D00: "Transmission Control 2",   # 3328
    0x00E00: "Safety Header Message",   # 3584
    0x00F00: "High Voltage Energy Storage Pack 11 Control 1",   # 3840
    0x01000: "High Voltage Energy Storage Pack 12 Control 1",   # 4096
    0x01100: "High Voltage Energy Storage Pack 13 Control 1",   # 4352
    0x01200: "High Voltage Energy Storage Pack 14 Control 1",   # 4608
    0x01300: "High Voltage Energy Storage Pack 15 Control 1",   # 4864
    0x01400: "High Voltage Energy Storage Pack 16 Control 1",   # 5120
    0x01500: "High Voltage Energy Storage Pack 17 Control 1",   # 5376
    0x01600: "High Voltage Energy Storage Pack 18 Control 1",   # 5632
    0x01700: "High Voltage Energy Storage Pack 19 Control 1",   # 5888
    0x01800: "High Voltage Energy Storage Pack 20 Control 1",   # 6144
    0x01900: "High Voltage Energy Storage Pack 21 Control 1",   # 6400
    0x01A00: "High Voltage Energy Storage Pack 22 Control 1",   # 6656
    0x01B00: "High Voltage Energy Storage 1 Control 1",   # 6912
    0x01C00: "Transmission Control 3",   # 7168
    0x01D00: "Engine Ignition Controller",   # 7424
    0x01E00: "Alternator Control",   # 7680
    0x01F00: "High Voltage Energy Storage Pack 23 Control 1",   # 7936
    0x02000: "High Voltage Energy Storage Pack 24 Control 1",   # 8192
    0x02100: "High Voltage Energy Storage Pack 25 Control 1",   # 8448
    0x02200: "High Voltage Energy Storage Pack 26 Control 1",   # 8704
    0x02300: "Tractor Implement Management (TIM) Server to TIM Client",   # 8960
    0x02400: "Tractor Implement Management (TIM) Client to TIM Server",   # 9216
    0x02500: "CiA 602-2 Multi-PDU",   # 9472
    0x02600: "Motor/Generator 1 Inverter Control",   # 9728
    0x02700: "Motor/Generator 2 Inverter Control",   # 9984
    0x02800: "Motor/Generator 1 Inverter Rate Limits Request 1",   # 10240
    0x02900: "Motor/Generator 2 Inverter Rate Limits Request 1",   # 10496
    0x02A00: "High Voltage Energy Storage Pack 1 Control 1",   # 10752
    0x02B00: "High Voltage Energy Storage Pack 2 Control 1",   # 11008
    0x02C00: "High Voltage Energy Storage Pack 3 Control 1",   # 11264
    0x02D00: "High Voltage Energy Storage Pack 4 Control 1",   # 11520
    0x02E00: "High Voltage Energy Storage Pack 5 Control 1",   # 11776
    0x02F00: "High Voltage Energy Storage Pack 6 Control 1",   # 12032
    0x03000: "High Voltage Energy Storage Pack 7 Control 1",   # 12288
    0x03100: "High Voltage Energy Storage Pack 8 Control 1",   # 12544
    0x03200: "High Voltage Energy Storage Pack 9 Control 1",   # 12800
    0x03300: "High Voltage Energy Storage Pack 10 Control 1",   # 13056
    0x04C00: "Electrified Accessory Engine Coolant Pump Command",   # 19456
    0x04F00: "Data Transfer Support",   # 20224
    0x05000: "Monthly Data Transfer",   # 20480
    0x05100: "Weekly Data Transfer",   # 20736
    0x05200: "Daily Data Transfer",   # 20992
    0x05300: "EVSE 1 Control 1",   # 21248
    0x05400: "Winch Information 3",   # 21504
    0x05500: "Air Suspension Control 8",   # 21760
    0x05600: "Motor/Generator 2 Inverter Control 2",   # 22016
    0x05700: "Motor/Generator 1 Inverter Control 2",   # 22272
    0x05800: "Hoist Command Information",   # 22528
    0x05900: "Motor/Generator 2 Inverter Isolation Integrity Request",   # 22784
    0x05A00: "Motor/Generator 1 Inverter Isolation Integrity Request",   # 23040
    0x05B00: "Motor/Generator 2 Inverter Limits Request Power",   # 23296
    0x05C00: "Motor/Generator 2 Inverter Limits Request Mechanical",   # 23552
    0x05D00: "Motor/Generator 2 Inverter Limits Request DC Side",   # 23808
    0x05E00: "Motor/Generator 1 Inverter Limits Request DC Side",   # 24064
    0x05F00: "Motor/Generator 1 Inverter Limits Request Mechanical",   # 24320
    0x06000: "Motor/Generator 1 Inverter Limits Request Power",   # 24576
    0x06100: "Personnel Detect Interlock",   # 24832
    0x06200: "Engine Cylinder Combustion Configuration Feedback",   # 25088
    0x06300: "Engine Cylinder Combustion Configuration",   # 25344
    0x06400: "Engine Cylinder Pressure Timing Feedback",   # 25600
    0x06500: "Engine Cylinder Pressure Timing Configuration",   # 25856
    0x06600: "Electrified Accessory Generator Coolant Pump Command",   # 26112
    0x06700: "Electrified Accessory Generator Coolant Fan Command",   # 26368
    0x06800: "On Board Programming 1",   # 26624
    0x06900: "Marine Control Information Configuration 1",   # 26880
    0x06A00: "Marine Control Information 2",   # 27136
    0x06B00: "Well Stimulation Pump Sensor Calibration Command",   # 27392
    0x06C00: "CiA 602-2 XCP",   # 27648
    0x06D00: "Well Stimulation Pump System Configuration Command",   # 27904
    0x06E00: "Configurable Receive SPNs Command",   # 28160
    0x06F00: "Authentication Client to Authentication Server",   # 28416
    0x07000: "Authentication Server to Authentication Client",   # 28672
    0x07100: "Configurable Transmit PGNs Command",   # 28928
    0x07200: "Oil Debris Monitor Configuration Command",   # 29184
    0x07300: "Electrified Accessory Propulsion Motor Coolant Fan 3 Command",   # 29440
    0x07400: "Electrified Accessory Propulsion Motor Coolant Fan 2 Command",   # 29696
    0x07500: "Electrified Accessory Propulsion Motor Coolant Fan 1 Command",   # 29952
    0x07600: "Electrified Accessory Power Electronics Coolant Fan 3 Command",   # 30208
    0x07700: "Electrified Accessory Power Electronics Coolant Fan 2 Command",   # 30464
    0x07800: "Electrified Accessory Power Electronics Coolant Fan 1 Command",   # 30720
    0x07900: "Electrified Accessory Propulsion Motor Oil Pump Command",   # 30976
    0x07A00: "Electrified Accessory Propulsion Motor Coolant Pump Command",   # 31232
    0x07B00: "Electrified Accessory Power Electronics Coolant Pump Command",   # 31488
    0x07D00: "Electrified Accessory Motor Command",   # 32000
    0x07E00: "Engine Speed Ramp Rate Boundary Request",   # 32256
    0x07F00: "Tire Sensor Identification Command",   # 32512
    0x08000: "Hybrid System Control 1",   # 32768
    0x08100: "Aftertreatment System Control",   # 33024
    0x08200: "Tire Configuration Command Information",   # 33280
    0x08300: "Payload Calibration Information Command",   # 33536
    0x08400: "Aftertreatment 1 Particulate Sensor Control",   # 33792
    0x08500: "Cab Message 2",   # 34048
    0x08600: "Switched Power Outputs Command",   # 34304
    0x08700: "Engine State Requests",   # 34560
    0x08800: "Radio Beacon Request",   # 34816
    0x08900: "Running Gear Equipment #2/4",   # 35072
    0x08A00: "Running Gear Equipment #1/2",   # 35328
    0x08B00: "CCP Data Transmission Object",   # 35584
    0x08C00: "CCP Command Receive Object",   # 35840
    0x08D00: "Sequence Control Client-to-Sequence Control Master",   # 36096
    0x08E00: "Sequence Control Master-to-Sequence Control Client",   # 36352
    0x08F00: "Engine Configuration Commands",   # 36608
    0x09000: "Supplemental Fan Command",   # 36864
    0x09100: "Vehicle/Chassis Lubrication System 1",   # 37120
    0x09200: "Aftertreatment 1 Hydrocarbon Doser Information 1",   # 37376
    0x09300: "NAME Management Message",   # 37632
    0x09400: "Aftertreatment 1 Diesel Particulate Filter Soot Sensor Calibration",   # 37888
    0x09500: "Aftertreatment 2 Diesel Particulate Filter Soot Sensor Calibration",   # 38144
    0x09600: "Low Voltage Disconnect Set Operating Mode",   # 38400
    0x09700: "Noise Control Status",   # 38656
    0x09800: "Noise Control 1",   # 38912
    0x09900: "Joystick Lamp Command Message",   # 39168
    0x09A00: "General Purpose Message #1/8",   # 39424
    0x09B00: "Proprietary Method Identification",   # 39680
    0x09C00: "Auxiliary Input/Output Status 7",   # 39936
    0x09D00: "Auxiliary Input/Output Status 6",   # 40192
    0x09E00: "DTC Counts",   # 40448
    0x09F00: "Immediate Fault Status",   # 40704
    0x0A000: "NTE Status",   # 40960
    0x0A100: "Emission Increasing Auxiliary Emission Control Device Active Time",   # 41216
    0x0A200: "Regulated Exhaust Emission Level Exceedance",   # 41472
    0x0A300: "DTC To Lamp Association",   # 41728
    0x0A400: "Scaled Test Results",   # 41984
    0x0A500: "Auxiliary Input/Output Status 4",   # 42240
    0x0A600: "Auxiliary Input/Output Status 3",   # 42496
    0x0A700: "Auxiliary Input/Output Status 2",   # 42752
    0x0A800: "Text Display",   # 43008
    0x0A900: "Forward Lane Image Command",   # 43264
    0x0AA00: "Client (ECU) to File Server message",   # 43520
    0x0AB00: "File Server to Client (ECU) message",   # 43776
    0x0AC00: "Agricultural Guidance Machine Info",   # 44032
    0x0AD00: "Agricultural Guidance System command",   # 44288
    0x0AE00: "Tire Pressure Reference Setting",   # 44544
    0x0AF00: "Parameter Locate Message",   # 44800
    0x0B000: "Configuration Identification Message",   # 45056
    0x0B100: "Proprietarily Configurable Message #1",   # 45312
    0x0B200: "Proprietarily Configurable Message #2",   # 45568
    0x0B300: "Proprietarily Configurable Message #3",   # 45824
    0x0B400: "Proprietarily Configurable Message #4",   # 46080
    0x0B500: "Proprietarily Configurable Message #5",   # 46336
    0x0B600: "Proprietarily Configurable Message #6",   # 46592
    0x0B700: "Proprietarily Configurable Message #7",   # 46848
    0x0B800: "Proprietarily Configurable Message #8",   # 47104
    0x0B900: "Proprietarily Configurable Message #9",   # 47360
    0x0BA00: "Proprietarily Configurable Message #10",   # 47616
    0x0BB00: "Proprietarily Configurable Message #11",   # 47872
    0x0BC00: "Proprietarily Configurable Message #12",   # 48128
    0x0BD00: "Proprietarily Configurable Message #13",   # 48384
    0x0BE00: "Proprietarily Configurable Message #14",   # 48640
    0x0BF00: "Proprietarily Configurable Message #15",   # 48896
    0x0C000: "Proprietarily Configurable Message #16",   # 49152
    0x0C100: "Diagnostic Readiness 2",   # 49408
    0x0C200: "Monitor Performance Ratio",   # 49664
    0x0C300: "Individual Clear/Reset Of Active And Previously Active DTC",   # 49920
    0x0C400: "General Purpose Valve command",   # 50176
    0x0C500: "General Purpose Valve measured flow",   # 50432
    0x0C600: "General Purpose Valve estimated flow",   # 50688
    0x0C700: "Extended Transport Protocol - Data Transfer",   # 50944
    0x0C800: "Extended Transport Protocol - Connection Management",   # 51200
    0x0C900: "Request 2",   # 51456
    0x0CA00: "Transfer",   # 51712
    0x0CB00: "Process Data Message",   # 51968
    0x0CC00: "Request for Repetition Rate",   # 52224
    0x0CD00: "Reserved for ISO 15765-2",   # 52480
    0x0CE00: "Reserved for ISO 15765-2",   # 52736
    0x0CF00: "Continuous Torque & Speed Limit Request",   # 52992
    0x0D000: "Background lighting level command",   # 53248
    0x0D100: "Air Suspension Control 6",   # 53504
    0x0D200: "Air Suspension Control 2",   # 53760
    0x0D300: "Calibration Information",   # 54016
    0x0D400: "Data Security",   # 54272
    0x0D500: "Time/Date Adjust",   # 54528
    0x0D600: "Boot Load Data",   # 54784
    0x0D700: "Binary Data Transfer",   # 55040
    0x0D800: "Memory Access Response",   # 55296
    0x0D900: "Memory Access Request",   # 55552
    0x0DA00: "Reserved for ISO 15765-2",   # 55808
    0x0DB00: "Reserved for ISO 15765-2",   # 56064
    0x0DC00: "Anti-theft Status",   # 56320
    0x0DD00: "Anti-theft Request",   # 56576
    0x0DE00: "Reset",   # 56832
    0x0DF00: "Stop Start Broadcast",   # 57088
    0x0E000: "Cab Message 1",   # 57344
    0x0E100: "General Purpose Message #2/1",   # 57600
    0x0E200: "General Purpose Message #1/1",   # 57856
    0x0E300: "Command Non-continuously Monitored Test",   # 58112
    0x0E400: "Running Gear Equipment #1/1",   # 58368
    0x0E500: "Running Gear Equipment #2/1",   # 58624
    0x0E600: "Virtual Terminal-to-Node",   # 58880
    0x0E700: "Node-to-Virtual Terminal",   # 59136
    0x0E800: "ISO Acknowledgment",   # 59392
    0x0EA00: "ISO Request",   # 59904
    0x0EB00: "ISO Transport Protocol, Data Transfer",   # 60160
    0x0EC00: "Transport Protocol - Connection Mgmt",   # 60416
    0x0ED00: "Network Layer",   # 60672
    0x0EE00: "ISO Address Claim",   # 60928
    0x0EF00: "Proprietary A",   # 61184
    0x0F000: "Electronic Retarder Controller 1",   # 61440
    0x0F001: "Electronic Brake Controller 1",   # 61441
    0x0F002: "Electronic Transmission Controller 1",   # 61442
    0x0F003: "Electronic Engine Controller 2",   # 61443
    0x0F004: "Electronic Engine Controller 1",   # 61444
    0x0F005: "Electronic Transmission Controller 2",   # 61445
    0x0F006: "Electronic Axle Controller 1",   # 61446
    0x0F007: "Forward Lane Image 1",   # 61447
    0x0F008: "Hydraulic Pressure Governor Info",   # 61448
    0x0F009: "Vehicle Dynamic Stability Control 2",   # 61449
    0x0F00A: "Engine Gas Flow Rate",   # 61450
    0x0F00B: "Electronic Steering Control",   # 61451
    0x0F00C: "Electronic Transmission Controller #8",   # 61452
    0x0F00D: "Land Leveling System Operational Information",   # 61453
    0x0F00E: "Aftertreatment 1 Intake Gas 1",   # 61454
    0x0F00F: "Aftertreatment 1 Outlet Gas 1",   # 61455
    0x0F010: "Aftertreatment 2 Intake Gas 1",   # 61456
    0x0F011: "Aftertreatment 2 Outlet Gas 1",   # 61457
    0x0F012: "Fifth Wheel Smart Systems 1",   # 61458
    0x0F013: "Slope Sensor Information",   # 61459
    0x0F014: "Blade Information",   # 61460
    0x0F015: "Requested Generator Total AC Reactive Power",   # 61461
    0x0F016: "Cylinder Combustion Status",   # 61462
    0x0F017: "Engine Knock Level #1",   # 61463
    0x0F018: "Engine Knock Level #2",   # 61464
    0x0F019: "Engine Knock Level #3",   # 61465
    0x0F01A: "Engine Throttle / Fuel Actuator Control Command",   # 61466
    0x0F01B: "General Purpose Message #1/7",   # 61467
    0x0F01C: "Requested Generator Average Basic AC Quantities",   # 61468
    0x0F01D: "Steering Angle Sensor Information",   # 61469
    0x0F01E: "Generator Control 2",   # 61470
    0x0F01F: "Electronic Brake System #2/6",   # 61471
    0x0F020: "Electronic Brake System #2/5",   # 61472
    0x0F021: "Engine Speed Sensor Information 1",   # 61473
    0x0F022: "Machine Selected Speed",   # 61474
    0x0F023: "Aftertreatment 1 SCR Dosing System Information 1",   # 61475
    0x0F024: "Aftertreatment 1 SCR Dosing System Requests 1",   # 61476
    0x0F025: "Aftertreatment 1 SCR Ammonia Information",   # 61477
    0x0F026: "Aftertreatment 2 SCR Dosing System Information 1",   # 61478
    0x0F027: "Aftertreatment 2 SCR Dosing System Requests 1",   # 61479
    0x0F028: "Aftertreatment 2 SCR Ammonia Information",   # 61480
    0x0F029: "Slope Sensor Information 2",   # 61481
    0x0F02A: "Angular Rate Information",   # 61482
    0x0F02B: "Crash Notification",   # 61483
    0x0F02C: "Magnet Status Information 2",   # 61484
    0x0F02D: "Acceleration Sensor",   # 61485
    0x0F02E: "Engine Turbocharger Control",   # 61486
    0x0F02F: "Advanced Emergency Braking System 1",   # 61487
    0x0F030: "Wireless Status",   # 61488
    0x0F031: "Wand Sensor",   # 61489
    0x0F032: "Linear Displacement Sensor",   # 61490
    0x0F033: "Aftertreatment 1 SCR Ammonia Information 2",   # 61491
    0x0F034: "Aftertreatment 2 SCR Ammonia Information 2",   # 61492
    0x0F036: "High Voltage Energy Storage 1 Status 2",   # 61494
    0x0F037: "Engine Turbocharger Blowoff Actuator 1",   # 61495
    0x0F038: "Engine Torque / Fuel Request",   # 61496
    0x0F039: "Engine Air System Information",   # 61497
    0x0F03A: "Engine Cylinder 1 Combustion Information",   # 61498
    0x0F03B: "Engine Cylinder 2 Combustion Information",   # 61499
    0x0F03C: "Engine Cylinder 3 Combustion Information",   # 61500
    0x0F03D: "Engine Cylinder 4 Combustion Information",   # 61501
    0x0F03E: "Engine Cylinder 5 Combustion Information",   # 61502
    0x0F03F: "Engine Cylinder 6 Combustion Information",   # 61503
    0x0F040: "Engine Cylinder 7 Combustion Information",   # 61504
    0x0F041: "Engine Cylinder 8 Combustion Information",   # 61505
    0x0F042: "Engine Cylinder 9 Combustion Information",   # 61506
    0x0F043: "Engine Cylinder 10 Combustion Information",   # 61507
    0x0F044: "Engine Cylinder 11 Combustion Information",   # 61508
    0x0F045: "Engine Cylinder 12 Combustion Information",   # 61509
    0x0F046: "Engine Cylinder 13 Combustion Information",   # 61510
    0x0F047: "Engine Cylinder 14 Combustion Information",   # 61511
    0x0F048: "Engine Cylinder 15 Combustion Information",   # 61512
    0x0F049: "Engine Cylinder 16 Combustion Information",   # 61513
    0x0F04A: "Engine Cylinder 17 Combustion Information",   # 61514
    0x0F04B: "Engine Cylinder 18 Combustion Information",   # 61515
    0x0F04C: "Engine Cylinder 19 Combustion Information",   # 61516
    0x0F04D: "Engine Cylinder 20 Combustion Information",   # 61517
    0x0F04E: "Engine Cylinder 1 Combustion Average Information",   # 61518
    0x0F04F: "Engine Cylinder 2 Combustion Average Information",   # 61519
    0x0F050: "Engine Cylinder 3 Combustion Average Information",   # 61520
    0x0F051: "Engine Cylinder 4 Combustion Average Information",   # 61521
    0x0F052: "Engine Cylinder 5 Combustion Average Information",   # 61522
    0x0F053: "Engine Cylinder 6 Combustion Average Information",   # 61523
    0x0F054: "Engine Cylinder 7 Combustion Average Information",   # 61524
    0x0F055: "Engine Cylinder 8 Combustion Average Information",   # 61525
    0x0F056: "Engine Cylinder 9 Combustion Average Information",   # 61526
    0x0F057: "Engine Cylinder 10 Combustion Average Information",   # 61527
    0x0F058: "Engine Cylinder 11 Combustion Average Information",   # 61528
    0x0F059: "Engine Cylinder 12 Combustion Average Information",   # 61529
    0x0F05A: "Engine Cylinder 13 Combustion Average Information",   # 61530
    0x0F05B: "Engine Cylinder 14 Combustion Average Information",   # 61531
    0x0F05C: "Engine Cylinder 15 Combustion Average Information",   # 61532
    0x0F05D: "Engine Cylinder 16 Combustion Average Information",   # 61533
    0x0F05E: "Engine Cylinder 17 Combustion Average Information",   # 61534
    0x0F05F: "Engine Cylinder 18 Combustion Average Information",   # 61535
    0x0F060: "Engine Cylinder 19 Combustion Average Information",   # 61536
    0x0F061: "Engine Cylinder 20 Combustion Average Information",   # 61537
    0x0F062: "Electronic Transmission Controller #12",   # 61538
    0x0F063: "Fuel Information 5 (Gaseous)",   # 61539
    0x0F064: "Engine Gaseous Fuel Valve Duration Command 1",   # 61540
    0x0F065: "Engine Gaseous Fuel Valve Duration Command 2",   # 61541
    0x0F066: "Engine Gaseous Fuel Valve Duration Command 3",   # 61542
    0x0F067: "Engine Gaseous Fuel Valve Duration Command 4",   # 61543
    0x0F068: "Engine Gaseous Fuel Valve Duration Command 5",   # 61544
    0x0F069: "Engine Gaseous Fuel Valve Start of Actuation Command 1",   # 61545
    0x0F06A: "Engine Gaseous Fuel Valve Start of Actuation Command 2",   # 61546
    0x0F06B: "Engine Gaseous Fuel Valve Start of Actuation Command 3",   # 61547
    0x0F06C: "Engine Gaseous Fuel Valve Start of Actuation Command 4",   # 61548
    0x0F06D: "Engine Gaseous Fuel Valve Start of Actuation Command 5",   # 61549
    0x0F06E: "Fuel Pump Actuator Control Command",   # 61550
    0x0F06F: "Power Converter 1 Control 1",   # 61551
    0x0F070: "Power Converter 2 Control 1",   # 61552
    0x0F071: "Power Converter 1 Rate Limits Request 1",   # 61553
    0x0F072: "Power Converter 2 Rate Limits Request 1",   # 61554
    0x0F073: "Power Converter 2 Control 2",   # 61555
    0x0F074: "Power Converter 1 Control 2",   # 61556
    0x0F075: "Power Converter 1 Mode Feedback 1",   # 61557
    0x0F076: "Power Converter 1 Limits Active Power",   # 61558
    0x0F077: "Power Converter 1 Limits Active Electrical",   # 61559
    0x0F078: "Power Converter 1 Limits Active DC Energy Source 1",   # 61560
    0x0F079: "Power Converter 1 Low Voltage",   # 61561
    0x0F07A: "Power Converter 2 Mode Feedback 1",   # 61562
    0x0F07B: "Power Converter 2 Limits Active Power",   # 61563
    0x0F07C: "Power Converter 2 Limits Active Electrical",   # 61564
    0x0F07D: "Power Converter 2 Limits Active DC Energy Source 1",   # 61565
    0x0F07E: "Power Converter 2 Low Voltage",   # 61566
    0x0F07F: "Power Converter 1 Status 2",   # 61567
    0x0F080: "Power Converter 1 Rate Limits Active 1",   # 61568
    0x0F081: "Power Converter 2 Status 2",   # 61569
    0x0F082: "Power Converter 2 Rate Limits Active 1",   # 61570
    0x0F083: "Power Converter 2 Isolation Integrity",   # 61571
    0x0F084: "Power Converter 1 Isolation Integrity",   # 61572
    0x0F085: "Power Converter 2 Status 1",   # 61573
    0x0F086: "Power Converter 1 Status 1",   # 61574
    0x0F090: "High Voltage Energy Storage 1 Data 1",   # 61584
    0x0F091: "High Voltage Energy Storage 1 Data 2",   # 61585
    0x0F092: "High Voltage Energy Storage 1 Data 3",   # 61586
    0x0F093: "High Voltage Energy Storage 1 Data 4",   # 61587
    0x0F094: "High Voltage Energy Storage 1 Data 5",   # 61588
    0x0F095: "High Voltage Energy Storage 1 Data 6",   # 61589
    0x0F096: "High Voltage Energy Storage 1 Status 1",   # 61590
    0x0F0A0: "High Voltage Energy Storage 1 Data 7",   # 61600
    0x0F0C8: "DC/AC Accessory Inverter 1 Status 2",   # 61640
    0x0F0C9: "DC/AC Accessory Inverter 1 Voltage",   # 61641
    0x0F0CA: "DC/AC Accessory Inverter 1 Feedback 2",   # 61642
    0x0F0CB: "DC/AC Accessory Inverter 2 Status 2",   # 61643
    0x0F0CC: "DC/AC Accessory Inverter 2 Voltage",   # 61644
    0x0F0CD: "DC/AC Accessory Inverter 2 Feedback 2",   # 61645
    0x0F0D0: "Engine Cylinder Combustion Request",   # 61648
    0x0F0D1: "Engine Cylinder Head Bypass Actuator 1",   # 61649
    0x0F0D2: "Engine Electronic Controller 18",   # 61650
    0x0F0D3: "Predictive Cruise Control 1",   # 61651
    0x0F0D6: "DC/AC Accessory Inverter 1 Command",   # 61654
    0x0F0D7: "DC/AC Accessory Inverter 1 Feedback",   # 61655
    0x0F0DA: "DC/AC Accessory Inverter 2 Command",   # 61658
    0x0F0DB: "DC/AC Accessory Inverter 2 Feedback",   # 61659
    0x0F0DE: "DC/AC Accessory Inverter 3 Command",   # 61662
    0x0F0DF: "DC/AC Accessory Inverter 3 Feedback",   # 61663
    0x0F0E2: "DC/AC Accessory Inverter 4 Command",   # 61666
    0x0F0E3: "DC/AC Accessory Inverter 4 Feedback",   # 61667
    0x0F0E4: "Heartbeat Message",   # 61668
    0x0F0E5: "Engine Ignition Timing Offset 1",   # 61669
    0x0F0E6: "Engine Ignition Timing Offset 2",   # 61670
    0x0F0E7: "Engine Ignition Timing Offset 3",   # 61671
    0x0F0E8: "Engine Throttle / Fuel Actuator Control Command 2",   # 61672
    0x0F0E9: "Aftertreatment 1 Intake Gas 3",   # 61673
    0x0F0EA: "Aftertreatment 1 Outlet Gas 3",   # 61674
    0x0F0EB: "Aftertreatment 2 Intake Gas Sensor 2",   # 61675
    0x0F0EC: "Aftertreatment 2 Outlet Gas Sensor 2",   # 61676
    0x0F0ED: "Engine Start Control",   # 61677
    0x0F0F5: "Engine Start Arbitrator",   # 61685
    0x0F0F6: "Advanced Driver Assistance Systems Interface Specification 1",   # 61686
    0x0F0F7: "Advanced Driver Assistance Systems Interface Specification 2",   # 61687
    0x0F0F8: "Advanced Driver Assistance Systems Interface Specification 3",   # 61688
    0x0F0F9: "Engine Valve Controller",   # 61689
    0x0F0FA: "Electronic Transmission Controller 13",   # 61690
    0x0F0FB: "Aftertreatment 1 SCR Dosing System Requests 3",   # 61691
    0x0F0FC: "Aftertreatment 2 SCR Dosing System Requests 3",   # 61692
    0x0F0FD: "Aftertreatment 1 SCR Dosing System Information 4",   # 61693
    0x0F0FE: "Aftertreatment 2 SCR Dosing System Information 4",   # 61694
    0x0F0FF: "Secondary or Front Hitch Roll and Pitch",   # 61695
    0x0F100: "Secondary or Front Hitch Roll and Pitch command",   # 61696
    0x0F101: "Primary or Rear Hitch Roll and Pitch",   # 61697
    0x0F102: "Primary or Rear Hitch Roll and Pitch command",   # 61698
    0x0F103: "Generator Trip Energy",   # 61699
    0x0F104: "Engine Speed Sensor Information 2",   # 61700
    0x0F105: "Hydraulic Pressure Displacement",   # 61701
    0x0F106: "Well Stimulation Pump System 1",   # 61702
    0x0F107: "Well Stimulation Pump System 2",   # 61703
    0x0F108: "High Voltage Energy Storage 1 Module Status 1",   # 61704
    0x0F109: "High Voltage Energy Storage 1 Thermal Management System Status 1",   # 61705
    0x0F10A: "High Voltage Energy Storage 1 Data 8",   # 61706
    0x0F10B: "High Voltage Energy Storage 1 Data 9",   # 61707
    0x0F10C: "High Voltage Energy Storage 1 Data 10",   # 61708
    0x0F10D: "Fuel Information 6 (Gaseous)",   # 61709
    0x0F10E: "Dump Truck Body Information",   # 61710
    0x0F10F: "Engine Operating Information 2",   # 61711
    0x0F110: "Brakes 2",   # 61712
    0x0F111: "Gaseous Fuel Pressure 3",   # 61713
    0x0F112: "DC/DC Converter 1 Control",   # 61714
    0x0F113: "DC/DC Converter 1 Operating Status",   # 61715
    0x0F114: "DC/DC Converter 1 Voltage and Current",   # 61716
    0x0F115: "DC/DC Converter 1 SLI Battery Status",   # 61717
    0x0F116: "Well Stimulation Pump System 3",   # 61718
    0x0F117: "DC/DC Converter 1 Status 2",   # 61719
    0x0F118: "DC/DC Converter 2 Control",   # 61720
    0x0F119: "DC/DC Converter 2 Operating Status",   # 61721
    0x0F11A: "DC/DC Converter 2 Voltage and Current",   # 61722
    0x0F11B: "DC/DC Converter 2 SLI Battery Status",   # 61723
    0x0F11C: "DC/DC Converter 2 Status 2",   # 61724
    0x0F11D: "DC/DC Converter 3 Control",   # 61725
    0x0F11E: "DC/DC Converter 3 Operating Status",   # 61726
    0x0F11F: "DC/DC Converter 3 Voltage and Current",   # 61727
    0x0F120: "DC/DC Converter 3 SLI Battery Status",   # 61728
    0x0F121: "DC/DC Converter 3 Status 2",   # 61729
    0x0F122: "DC/DC Converter 4 Control",   # 61730
    0x0F123: "DC/DC Converter 4 Operating Status",   # 61731
    0x0F124: "DC/DC Converter 4 Voltage and Current",   # 61732
    0x0F125: "DC/DC Converter 4 SLI Battery Status",   # 61733
    0x0F126: "DC/DC Converter 4 Status 2",   # 61734
    0x0F127: "Slope Sensor Information 3",   # 61735
    0x0F128: "DC/AC Accessory Inverter 3 Status 2",   # 61736
    0x0F129: "DC/AC Accessory Inverter 3 Voltage",   # 61737
    0x0F12A: "DC/AC Accessory Inverter 3 Feedback 2",   # 61738
    0x0F12B: "DC/AC Accessory Inverter 4 Status 2",   # 61739
    0x0F12C: "DC/AC Accessory Inverter 4 Voltage",   # 61740
    0x0F12D: "DC/AC Accessory Inverter 4 Feedback 2",   # 61741
    0x0F12E: "DC/AC Accessory Inverter 5 Command",   # 61742
    0x0F12F: "DC/AC Accessory Inverter 5 Feedback",   # 61743
    0x0F130: "DC/AC Accessory Inverter 5 Status 2",   # 61744
    0x0F131: "DC/AC Accessory Inverter 5 Voltage",   # 61745
    0x0F132: "DC/AC Accessory Inverter 5 Feedback 2",   # 61746
    0x0F133: "Engine Pre-Chamber Fuel Valve Duration Command 1",   # 61747
    0x0F134: "Engine Pre-Chamber Fuel Valve Duration Command 2",   # 61748
    0x0F135: "Engine Pre-Chamber Fuel Valve Duration Command 3",   # 61749
    0x0F136: "Engine Pre-Chamber Fuel Valve Duration Command 4",   # 61750
    0x0F137: "Engine Pre-Chamber Fuel Valve Duration Command 5",   # 61751
    0x0F138: "Engine Pre-Chamber Fuel Valve Start of Actuation Command 1",   # 61752
    0x0F139: "Engine Pre-Chamber Fuel Valve Start of Actuation Command 2",   # 61753
    0x0F13A: "Engine Pre-Chamber Fuel Valve Start of Actuation Command 3",   # 61754
    0x0F13B: "Engine Pre-Chamber Fuel Valve Start of Actuation Command 4",   # 61755
    0x0F13C: "Engine Pre-Chamber Fuel Valve Start of Actuation Command 5",   # 61756
    0x0F13D: "Active Steering System Controls 1",   # 61757
    0x0F13E: "Secondary or Front Hitch Yaw command",   # 61758
    0x0F13F: "Primary or Rear Hitch Yaw command",   # 61759
    0x0F140: "Stationary Inverter Average Basic AC Quantities",   # 61760
    0x0F141: "Stationary Inverter Total AC Reactive Power",   # 61761
    0x0F142: "Stationary Inverter Total AC Power",   # 61762
    0x0F143: "Stationary Inverter Control",   # 61763
    0x0F144: "Stationary Inverter to Bus Sync Check Status",   # 61764
    0x0F145: "Engine Cylinder 1 Combustion Pressures",   # 61765
    0x0F146: "Engine Cylinder 2 Combustion Pressures",   # 61766
    0x0F147: "Engine Cylinder 3 Combustion Pressures",   # 61767
    0x0F148: "Engine Cylinder 4 Combustion Pressures",   # 61768
    0x0F149: "Engine Cylinder 5 Combustion Pressures",   # 61769
    0x0F14A: "Engine Cylinder 6 Combustion Pressures",   # 61770
    0x0F14B: "Engine Cylinder 7 Combustion Pressures",   # 61771
    0x0F14C: "Engine Cylinder 8 Combustion Pressures",   # 61772
    0x0F14D: "Engine Cylinder 9 Combustion Pressures",   # 61773
    0x0F14E: "Engine Cylinder 10 Combustion Pressures",   # 61774
    0x0F14F: "Engine Cylinder 11 Combustion Pressures",   # 61775
    0x0F150: "Engine Cylinder 12 Combustion Pressures",   # 61776
    0x0F151: "Engine Cylinder 13 Combustion Pressures",   # 61777
    0x0F152: "Engine Cylinder 14 Combustion Pressures",   # 61778
    0x0F153: "Engine Cylinder 15 Combustion Pressures",   # 61779
    0x0F154: "Engine Cylinder 16 Combustion Pressures",   # 61780
    0x0F155: "Engine Cylinder 17 Combustion Pressures",   # 61781
    0x0F156: "Engine Cylinder 18 Combustion Pressures",   # 61782
    0x0F157: "Engine Cylinder 19 Combustion Pressures",   # 61783
    0x0F158: "Engine Cylinder 20 Combustion Pressures",   # 61784
    0x0F159: "Engine Cylinder 1 Combustion Timing",   # 61785
    0x0F15A: "Engine Cylinder 2 Combustion Timing",   # 61786
    0x0F15B: "Engine Cylinder 3 Combustion Timing",   # 61787
    0x0F15C: "Engine Cylinder 4 Combustion Timing",   # 61788
    0x0F15D: "Engine Cylinder 5 Combustion Timing",   # 61789
    0x0F15E: "Engine Cylinder 6 Combustion Timing",   # 61790
    0x0F15F: "Engine Cylinder 7 Combustion Timing",   # 61791
    0x0F160: "Engine Cylinder 8 Combustion Timing",   # 61792
    0x0F161: "Engine Cylinder 9 Combustion Timing",   # 61793
    0x0F162: "Engine Cylinder 10 Combustion Timing",   # 61794
    0x0F163: "Engine Cylinder 11 Combustion Timing",   # 61795
    0x0F164: "Engine Cylinder 12 Combustion Timing",   # 61796
    0x0F165: "Engine Cylinder 13 Combustion Timing",   # 61797
    0x0F166: "Engine Cylinder 14 Combustion Timing",   # 61798
    0x0F167: "Engine Cylinder 15 Combustion Timing",   # 61799
    0x0F168: "Engine Cylinder 16 Combustion Timing",   # 61800
    0x0F169: "Engine Cylinder 17 Combustion Timing",   # 61801
    0x0F16A: "Engine Cylinder 18 Combustion Timing",   # 61802
    0x0F16B: "Engine Cylinder 19 Combustion Timing",   # 61803
    0x0F16C: "Engine Cylinder 20 Combustion Timing",   # 61804
    0x0F16D: "Engine Cylinder 1 Combustion Metrics",   # 61805
    0x0F16E: "Engine Cylinder 2 Combustion Metrics",   # 61806
    0x0F16F: "Engine Cylinder 3 Combustion Metrics",   # 61807
    0x0F170: "Engine Cylinder 4 Combustion Metrics",   # 61808
    0x0F171: "Engine Cylinder 5 Combustion Metrics",   # 61809
    0x0F172: "Engine Cylinder 6 Combustion Metrics",   # 61810
    0x0F173: "Engine Cylinder 7 Combustion Metrics",   # 61811
    0x0F174: "Engine Cylinder 8 Combustion Metrics",   # 61812
    0x0F175: "Engine Cylinder 9 Combustion Metrics",   # 61813
    0x0F176: "Engine Cylinder 10 Combustion Metrics",   # 61814
    0x0F177: "Engine Cylinder 11 Combustion Metrics",   # 61815
    0x0F178: "Engine Cylinder 12 Combustion Metrics",   # 61816
    0x0F179: "Engine Cylinder 13 Combustion Metrics",   # 61817
    0x0F17A: "Engine Cylinder 14 Combustion Metrics",   # 61818
    0x0F17B: "Engine Cylinder 15 Combustion Metrics",   # 61819
    0x0F17C: "Engine Cylinder 16 Combustion Metrics",   # 61820
    0x0F17D: "Engine Cylinder 17 Combustion Metrics",   # 61821
    0x0F17E: "Engine Cylinder 18 Combustion Metrics",   # 61822
    0x0F17F: "Engine Cylinder 19 Combustion Metrics",   # 61823
    0x0F180: "Engine Cylinder 20 Combustion Metrics",   # 61824
    0x0F181: "Motor/Generator 1 Inverter Mode Feedback 1",   # 61825
    0x0F182: "Motor/Generator 1 Inverter Limits Active Power",   # 61826
    0x0F183: "Motor/Generator 1 Inverter Limits Active Mechanical",   # 61827
    0x0F184: "Motor/Generator 1 Inverter Limits Active DC Side",   # 61828
    0x0F185: "Motor/Generator 1 Inverter Low Voltage",   # 61829
    0x0F186: "Motor/Generator 2 Inverter Mode Feedback 1",   # 61830
    0x0F187: "Motor/Generator 2 Inverter Limits Active Power",   # 61831
    0x0F188: "Motor/Generator 2 Inverter Limits Active Mechanical",   # 61832
    0x0F189: "Motor/Generator 2 Inverter Limits Active DC Side",   # 61833
    0x0F18A: "Motor/Generator 2 Inverter Low Voltage",   # 61834
    0x0F18B: "Motor/Generator 1 Inverter Status 2",   # 61835
    0x0F18C: "Motor/Generator 1 Inverter Rate Limits Active 1",   # 61836
    0x0F18D: "Motor/Generator 2 Inverter Status 2",   # 61837
    0x0F18E: "Motor/Generator 2 Inverter Rate Limits Active 1",   # 61838
    0x0F18F: "Impostor PG Alert",   # 61839
    0x0F190: "High Voltage Energy Storage Pack 1 Status 2",   # 61840
    0x0F191: "High Voltage Energy Storage Pack 1 Data 1",   # 61841
    0x0F192: "High Voltage Energy Storage Pack 1 Data 2",   # 61842
    0x0F193: "High Voltage Energy Storage Pack 1 Data 3",   # 61843
    0x0F194: "High Voltage Energy Storage Pack 1 Data 4",   # 61844
    0x0F195: "High Voltage Energy Storage Pack 1 Data 5",   # 61845
    0x0F196: "High Voltage Energy Storage Pack 1 Data 6",   # 61846
    0x0F197: "High Voltage Energy Storage Pack 1 Status 1",   # 61847
    0x0F198: "High Voltage Energy Storage Pack 1 Data 7",   # 61848
    0x0F199: "High Voltage Energy Storage Pack 1 Module Status 1",   # 61849
    0x0F19A: "High Voltage Energy Storage Pack 1 Thermal Management System Status 1",   # 61850
    0x0F19B: "High Voltage Energy Storage Pack 1 Data 8",   # 61851
    0x0F19C: "High Voltage Energy Storage Pack 1 Data 9",   # 61852
    0x0F19D: "High Voltage Energy Storage Pack 1 Data 10",   # 61853
    0x0F19E: "High Voltage Energy Storage Pack 1 Data 11",   # 61854
    0x0F19F: "High Voltage Energy Storage Pack 2 Status 2",   # 61855
    0x0F1A0: "High Voltage Energy Storage Pack 2 Data 1",   # 61856
    0x0F1A1: "High Voltage Energy Storage Pack 2 Data 2",   # 61857
    0x0F1A2: "High Voltage Energy Storage Pack 2 Data 3",   # 61858
    0x0F1A3: "High Voltage Energy Storage Pack 2 Data 4",   # 61859
    0x0F1A4: "High Voltage Energy Storage Pack 2 Data 5",   # 61860
    0x0F1A5: "High Voltage Energy Storage Pack 2 Data 6",   # 61861
    0x0F1A6: "High Voltage Energy Storage Pack 2 Status 1",   # 61862
    0x0F1A7: "High Voltage Energy Storage Pack 2 Data 7",   # 61863
    0x0F1A8: "High Voltage Energy Storage Pack 2 Module Status 1",   # 61864
    0x0F1A9: "High Voltage Energy Storage Pack 2 Thermal Management System Status 1",   # 61865
    0x0F1AA: "High Voltage Energy Storage Pack 2 Data 8",   # 61866
    0x0F1AB: "High Voltage Energy Storage Pack 2 Data 9",   # 61867
    0x0F1AC: "High Voltage Energy Storage Pack 2 Data 10",   # 61868
    0x0F1AD: "High Voltage Energy Storage Pack 2 Data 11",   # 61869
    0x0F1AE: "High Voltage Energy Storage Pack 3 Status 2",   # 61870
    0x0F1AF: "High Voltage Energy Storage Pack 3 Data 1",   # 61871
    0x0F1B0: "High Voltage Energy Storage Pack 3 Data 2",   # 61872
    0x0F1B1: "High Voltage Energy Storage Pack 3 Data 3",   # 61873
    0x0F1B2: "High Voltage Energy Storage Pack 3 Data 4",   # 61874
    0x0F1B3: "High Voltage Energy Storage Pack 3 Data 5",   # 61875
    0x0F1B4: "High Voltage Energy Storage Pack 3 Data 6",   # 61876
    0x0F1B5: "High Voltage Energy Storage Pack 3 Status 1",   # 61877
    0x0F1B6: "High Voltage Energy Storage Pack 3 Data 7",   # 61878
    0x0F1B7: "High Voltage Energy Storage Pack 3 Module Status 1",   # 61879
    0x0F1B8: "High Voltage Energy Storage Pack 3 Thermal Management System Status 1",   # 61880
    0x0F1B9: "High Voltage Energy Storage Pack 3 Data 8",   # 61881
    0x0F1BA: "High Voltage Energy Storage Pack 3 Data 9",   # 61882
    0x0F1BB: "High Voltage Energy Storage Pack 3 Data 10",   # 61883
    0x0F1BC: "High Voltage Energy Storage Pack 3 Data 11",   # 61884
    0x0F1BD: "High Voltage Energy Storage Pack 4 Status 2",   # 61885
    0x0F1BE: "High Voltage Energy Storage Pack 4 Data 1",   # 61886
    0x0F1BF: "High Voltage Energy Storage Pack 4 Data 2",   # 61887
    0x0F1C0: "High Voltage Energy Storage Pack 4 Data 3",   # 61888
    0x0F1C1: "High Voltage Energy Storage Pack 4 Data 4",   # 61889
    0x0F1C2: "High Voltage Energy Storage Pack 4 Data 5",   # 61890
    0x0F1C3: "High Voltage Energy Storage Pack 4 Data 6",   # 61891
    0x0F1C4: "High Voltage Energy Storage Pack 4 Status 1",   # 61892
    0x0F1C5: "High Voltage Energy Storage Pack 4 Data 7",   # 61893
    0x0F1C6: "High Voltage Energy Storage Pack 4 Module Status 1",   # 61894
    0x0F1C7: "High Voltage Energy Storage Pack 4 Thermal Management System Status 1",   # 61895
    0x0F1C8: "High Voltage Energy Storage Pack 4 Data 8",   # 61896
    0x0F1C9: "High Voltage Energy Storage Pack 4 Data 9",   # 61897
    0x0F1CA: "High Voltage Energy Storage Pack 4 Data 10",   # 61898
    0x0F1CB: "High Voltage Energy Storage Pack 4 Data 11",   # 61899
    0x0F1CC: "High Voltage Energy Storage Pack 5 Status 2",   # 61900
    0x0F1CD: "High Voltage Energy Storage Pack 5 Data 1",   # 61901
    0x0F1CE: "High Voltage Energy Storage Pack 5 Data 2",   # 61902
    0x0F1CF: "High Voltage Energy Storage Pack 5 Data 3",   # 61903
    0x0F1D0: "High Voltage Energy Storage Pack 5 Data 4",   # 61904
    0x0F1D1: "High Voltage Energy Storage Pack 5 Data 5",   # 61905
    0x0F1D2: "High Voltage Energy Storage Pack 5 Data 6",   # 61906
    0x0F1D3: "High Voltage Energy Storage Pack 5 Status 1",   # 61907
    0x0F1D4: "High Voltage Energy Storage Pack 5 Data 7",   # 61908
    0x0F1D5: "High Voltage Energy Storage Pack 5 Module Status 1",   # 61909
    0x0F1D6: "High Voltage Energy Storage Pack 5 Thermal Management System Status 1",   # 61910
    0x0F1D7: "High Voltage Energy Storage Pack 5 Data 8",   # 61911
    0x0F1D8: "High Voltage Energy Storage Pack 5 Data 9",   # 61912
    0x0F1D9: "High Voltage Energy Storage Pack 5 Data 10",   # 61913
    0x0F1DA: "High Voltage Energy Storage Pack 5 Data 11",   # 61914
    0x0F1DB: "High Voltage Energy Storage Pack 6 Status 2",   # 61915
    0x0F1DC: "High Voltage Energy Storage Pack 6 Data 1",   # 61916
    0x0F1DD: "High Voltage Energy Storage Pack 6 Data 2",   # 61917
    0x0F1DE: "High Voltage Energy Storage Pack 6 Data 3",   # 61918
    0x0F1DF: "High Voltage Energy Storage Pack 6 Data 4",   # 61919
    0x0F1E0: "High Voltage Energy Storage Pack 6 Data 5",   # 61920
    0x0F1E1: "High Voltage Energy Storage Pack 6 Data 6",   # 61921
    0x0F1E2: "High Voltage Energy Storage Pack 6 Status 1",   # 61922
    0x0F1E3: "High Voltage Energy Storage Pack 6 Data 7",   # 61923
    0x0F1E4: "High Voltage Energy Storage Pack 6 Module Status 1",   # 61924
    0x0F1E5: "High Voltage Energy Storage Pack 6 Thermal Management System Status 1",   # 61925
    0x0F1E6: "High Voltage Energy Storage Pack 6 Data 8",   # 61926
    0x0F1E7: "High Voltage Energy Storage Pack 6 Data 9",   # 61927
    0x0F1E8: "High Voltage Energy Storage Pack 6 Data 10",   # 61928
    0x0F1E9: "High Voltage Energy Storage Pack 6 Data 11",   # 61929
    0x0F1EA: "Motor/Generator 3 Inverter Mode Feedback 1",   # 61930
    0x0F1EB: "Motor/Generator 3 Inverter Limits Active Power",   # 61931
    0x0F1EC: "Motor/Generator 3 Inverter Limits Active Mechanical",   # 61932
    0x0F1ED: "Motor/Generator 3 Inverter Limits Active DC Side",   # 61933
    0x0F1EE: "Motor/Generator 3 Inverter Low Voltage",   # 61934
    0x0F1EF: "Motor/Generator 3 Inverter Status 2",   # 61935
    0x0F1F0: "Motor/Generator 3 Inverter Rate Limits Active 1",   # 61936
    0x0F1F1: "Motor/Generator 4 Inverter Mode Feedback 1",   # 61937
    0x0F1F2: "Motor/Generator 4 Inverter Limits Active Power",   # 61938
    0x0F1F3: "Motor/Generator 4 Inverter Limits Active Mechanical",   # 61939
    0x0F1F4: "Motor/Generator 4 Inverter Limits Active DC Side",   # 61940
    0x0F1F5: "Motor/Generator 4 Inverter Low Voltage",   # 61941
    0x0F1F6: "Motor/Generator 4 Inverter Status 2",   # 61942
    0x0F1F7: "Motor/Generator 4 Inverter Rate Limits Active 1",   # 61943
    0x0F1F8: "Motor/Generator 5 Inverter Mode Feedback 1",   # 61944
    0x0F1F9: "Motor/Generator 5 Inverter Limits Active Power",   # 61945
    0x0F1FA: "Motor/Generator 5 Inverter Limits Active Mechanical",   # 61946
    0x0F1FB: "Motor/Generator 5 Inverter Limits Active DC Side",   # 61947
    0x0F1FC: "Motor/Generator 5 Inverter Low Voltage",   # 61948
    0x0F1FD: "Motor/Generator 5 Inverter Status 2",   # 61949
    0x0F1FE: "Motor/Generator 5 Inverter Rate Limits Active 1",   # 61950
    0x0F1FF: "Motor/Generator 6 Inverter Mode Feedback 1",   # 61951
    0x0F200: "Motor/Generator 6 Inverter Limits Active Power",   # 61952
    0x0F201: "Motor/Generator 6 Inverter Limits Active Mechanical",   # 61953
    0x0F202: "Motor/Generator 6 Inverter Limits Active DC Side",   # 61954
    0x0F203: "Motor/Generator 6 Inverter Low Voltage",   # 61955
    0x0F204: "Motor/Generator 6 Inverter Status 2",   # 61956
    0x0F205: "Motor/Generator 6 Inverter Rate Limits Active 1",   # 61957
    0x0F206: "Blind Spot Detection 1",   # 61958
    0x0F207: "Winch Information 1",   # 61959
    0x0F208: "Motor/Generator 3 Inverter Control",   # 61960
    0x0F209: "Motor/Generator 3 Inverter Rate Limits Request 1",   # 61961
    0x0F20A: "Motor/Generator 4 Inverter Control",   # 61962
    0x0F20B: "Motor/Generator 4 Inverter Rate Limits Request 1",   # 61963
    0x0F20C: "Motor/Generator 5 Inverter Control",   # 61964
    0x0F20D: "Motor/Generator 5 Inverter Rate Limits Request 1",   # 61965
    0x0F20E: "Motor/Generator 6 Inverter Control",   # 61966
    0x0F20F: "Motor/Generator 6 Inverter Rate Limits Request 1",   # 61967
    0x0F214: "High Voltage Energy Storage Pack 7 Status 2",   # 61972
    0x0F215: "High Voltage Energy Storage Pack 7 Data 1",   # 61973
    0x0F216: "High Voltage Energy Storage Pack 7 Data 2",   # 61974
    0x0F217: "High Voltage Energy Storage Pack 7 Data 3",   # 61975
    0x0F218: "High Voltage Energy Storage Pack 7 Data 4",   # 61976
    0x0F219: "High Voltage Energy Storage Pack 7 Data 5",   # 61977
    0x0F21A: "High Voltage Energy Storage Pack 7 Data 6",   # 61978
    0x0F21B: "High Voltage Energy Storage Pack 7 Status 1",   # 61979
    0x0F21C: "High Voltage Energy Storage Pack 7 Data 7",   # 61980
    0x0F21D: "High Voltage Energy Storage Pack 7 Module Status 1",   # 61981
    0x0F21E: "High Voltage Energy Storage Pack 7 Thermal Management System Status 1",   # 61982
    0x0F21F: "High Voltage Energy Storage Pack 7 Data 8",   # 61983
    0x0F220: "High Voltage Energy Storage Pack 7 Data 9",   # 61984
    0x0F221: "High Voltage Energy Storage Pack 7 Data 10",   # 61985
    0x0F222: "High Voltage Energy Storage Pack 7 Data 11",   # 61986
    0x0F223: "High Voltage Energy Storage Pack 8 Status 2",   # 61987
    0x0F224: "High Voltage Energy Storage Pack 8 Data 1",   # 61988
    0x0F225: "High Voltage Energy Storage Pack 8 Data 2",   # 61989
    0x0F226: "High Voltage Energy Storage Pack 8 Data 3",   # 61990
    0x0F227: "High Voltage Energy Storage Pack 8 Data 4",   # 61991
    0x0F228: "High Voltage Energy Storage Pack 8 Data 5",   # 61992
    0x0F229: "High Voltage Energy Storage Pack 8 Data 6",   # 61993
    0x0F22A: "High Voltage Energy Storage Pack 8 Status 1",   # 61994
    0x0F22B: "High Voltage Energy Storage Pack 8 Data 7",   # 61995
    0x0F22C: "High Voltage Energy Storage Pack 8 Module Status 1",   # 61996
    0x0F22D: "High Voltage Energy Storage Pack 8 Thermal Management System Status 1",   # 61997
    0x0F22E: "High Voltage Energy Storage Pack 8 Data 8",   # 61998
    0x0F22F: "High Voltage Energy Storage Pack 8 Data 9",   # 61999
    0x0F230: "High Voltage Energy Storage Pack 8 Data 10",   # 62000
    0x0F231: "High Voltage Energy Storage Pack 8 Data 11",   # 62001
    0x0F232: "High Voltage Energy Storage Pack 9 Status 2",   # 62002
    0x0F233: "High Voltage Energy Storage Pack 9 Data 1",   # 62003
    0x0F234: "High Voltage Energy Storage Pack 9 Data 2",   # 62004
    0x0F235: "High Voltage Energy Storage Pack 9 Data 3",   # 62005
    0x0F236: "High Voltage Energy Storage Pack 9 Data 4",   # 62006
    0x0F237: "High Voltage Energy Storage Pack 9 Data 5",   # 62007
    0x0F238: "High Voltage Energy Storage Pack 9 Data 6",   # 62008
    0x0F239: "High Voltage Energy Storage Pack 9 Status 1",   # 62009
    0x0F23A: "High Voltage Energy Storage Pack 9 Data 7",   # 62010
    0x0F23B: "High Voltage Energy Storage Pack 9 Module Status 1",   # 62011
    0x0F23C: "High Voltage Energy Storage Pack 9 Thermal Management System Status 1",   # 62012
    0x0F23D: "High Voltage Energy Storage Pack 9 Data 8",   # 62013
    0x0F23E: "High Voltage Energy Storage Pack 9 Data 9",   # 62014
    0x0F23F: "High Voltage Energy Storage Pack 9 Data 10",   # 62015
    0x0F240: "High Voltage Energy Storage Pack 9 Data 11",   # 62016
    0x0F241: "High Voltage Energy Storage Pack 10 Status 2",   # 62017
    0x0F242: "High Voltage Energy Storage Pack 10 Data 1",   # 62018
    0x0F243: "High Voltage Energy Storage Pack 10 Data 2",   # 62019
    0x0F244: "High Voltage Energy Storage Pack 10 Data 3",   # 62020
    0x0F245: "High Voltage Energy Storage Pack 10 Data 4",   # 62021
    0x0F246: "High Voltage Energy Storage Pack 10 Data 5",   # 62022
    0x0F247: "High Voltage Energy Storage Pack 10 Data 6",   # 62023
    0x0F248: "High Voltage Energy Storage Pack 10 Status 1",   # 62024
    0x0F249: "High Voltage Energy Storage Pack 10 Data 7",   # 62025
    0x0F24A: "High Voltage Energy Storage Pack 10 Module Status 1",   # 62026
    0x0F24B: "High Voltage Energy Storage Pack 10 Thermal Management System Status 1",   # 62027
    0x0F24C: "High Voltage Energy Storage Pack 10 Data 8",   # 62028
    0x0F24D: "High Voltage Energy Storage Pack 10 Data 9",   # 62029
    0x0F24E: "High Voltage Energy Storage Pack 10 Data 10",   # 62030
    0x0F24F: "High Voltage Energy Storage Pack 10 Data 11",   # 62031
    0x0F250: "Electronic Auxiliary Transmission Controller 1",   # 62032
    0x0F251: "High Voltage Energy Storage Pack 11 Status 2",   # 62033
    0x0F252: "High Voltage Energy Storage Pack 11 Data 1",   # 62034
    0x0F253: "High Voltage Energy Storage Pack 11 Data 2",   # 62035
    0x0F254: "High Voltage Energy Storage Pack 11 Data 3",   # 62036
    0x0F255: "High Voltage Energy Storage Pack 11 Data 4",   # 62037
    0x0F256: "High Voltage Energy Storage Pack 11 Data 5",   # 62038
    0x0F257: "High Voltage Energy Storage Pack 11 Data 6",   # 62039
    0x0F258: "High Voltage Energy Storage Pack 11 Status 1",   # 62040
    0x0F259: "High Voltage Energy Storage Pack 11 Data 7",   # 62041
    0x0F25A: "High Voltage Energy Storage Pack 11 Module Status 1",   # 62042
    0x0F25B: "High Voltage Energy Storage Pack 11 Thermal Management System Status 1",   # 62043
    0x0F25C: "High Voltage Energy Storage Pack 11 Data 8",   # 62044
    0x0F25D: "High Voltage Energy Storage Pack 11 Data 9",   # 62045
    0x0F25E: "High Voltage Energy Storage Pack 11 Data 10",   # 62046
    0x0F25F: "High Voltage Energy Storage Pack 11 Data 11",   # 62047
    0x0F260: "High Voltage Energy Storage Pack 12 Status 2",   # 62048
    0x0F261: "High Voltage Energy Storage Pack 12 Data 1",   # 62049
    0x0F262: "High Voltage Energy Storage Pack 12 Data 2",   # 62050
    0x0F263: "High Voltage Energy Storage Pack 12 Data 3",   # 62051
    0x0F264: "High Voltage Energy Storage Pack 12 Data 4",   # 62052
    0x0F265: "High Voltage Energy Storage Pack 12 Data 5",   # 62053
    0x0F266: "High Voltage Energy Storage Pack 12 Data 6",   # 62054
    0x0F267: "High Voltage Energy Storage Pack 12 Status 1",   # 62055
    0x0F268: "High Voltage Energy Storage Pack 12 Data 7",   # 62056
    0x0F269: "High Voltage Energy Storage Pack 12 Module Status 1",   # 62057
    0x0F26A: "High Voltage Energy Storage Pack 12 Thermal Management System Status 1",   # 62058
    0x0F26B: "High Voltage Energy Storage Pack 12 Data 8",   # 62059
    0x0F26C: "High Voltage Energy Storage Pack 12 Data 9",   # 62060
    0x0F26D: "High Voltage Energy Storage Pack 12 Data 10",   # 62061
    0x0F26E: "High Voltage Energy Storage Pack 12 Data 11",   # 62062
    0x0F26F: "High Voltage Energy Storage Pack 13 Status 2",   # 62063
    0x0F270: "High Voltage Energy Storage Pack 13 Data 1",   # 62064
    0x0F271: "High Voltage Energy Storage Pack 13 Data 2",   # 62065
    0x0F272: "High Voltage Energy Storage Pack 13 Data 3",   # 62066
    0x0F273: "High Voltage Energy Storage Pack 13 Data 4",   # 62067
    0x0F274: "High Voltage Energy Storage Pack 13 Data 5",   # 62068
    0x0F275: "High Voltage Energy Storage Pack 13 Data 6",   # 62069
    0x0F276: "High Voltage Energy Storage Pack 13 Status 1",   # 62070
    0x0F277: "High Voltage Energy Storage Pack 13 Data 7",   # 62071
    0x0F278: "High Voltage Energy Storage Pack 13 Module Status 1",   # 62072
    0x0F279: "High Voltage Energy Storage Pack 13 Thermal Management System Status 1",   # 62073
    0x0F27A: "High Voltage Energy Storage Pack 13 Data 8",   # 62074
    0x0F27B: "High Voltage Energy Storage Pack 13 Data 9",   # 62075
    0x0F27C: "High Voltage Energy Storage Pack 13 Data 10",   # 62076
    0x0F27D: "High Voltage Energy Storage Pack 13 Data 11",   # 62077
    0x0F27E: "High Voltage Energy Storage Pack 14 Status 2",   # 62078
    0x0F27F: "High Voltage Energy Storage Pack 14 Data 1",   # 62079
    0x0F280: "High Voltage Energy Storage Pack 14 Data 2",   # 62080
    0x0F281: "High Voltage Energy Storage Pack 14 Data 3",   # 62081
    0x0F282: "High Voltage Energy Storage Pack 14 Data 4",   # 62082
    0x0F283: "High Voltage Energy Storage Pack 14 Data 5",   # 62083
    0x0F284: "High Voltage Energy Storage Pack 14 Data 6",   # 62084
    0x0F285: "High Voltage Energy Storage Pack 14 Status 1",   # 62085
    0x0F286: "High Voltage Energy Storage Pack 14 Data 7",   # 62086
    0x0F287: "High Voltage Energy Storage Pack 14 Module Status 1",   # 62087
    0x0F288: "High Voltage Energy Storage Pack 14 Thermal Management System Status 1",   # 62088
    0x0F289: "High Voltage Energy Storage Pack 14 Data 8",   # 62089
    0x0F28A: "High Voltage Energy Storage Pack 14 Data 9",   # 62090
    0x0F28B: "High Voltage Energy Storage Pack 14 Data 10",   # 62091
    0x0F28C: "High Voltage Energy Storage Pack 14 Data 11",   # 62092
    0x0F28D: "High Voltage Energy Storage Pack 15 Status 2",   # 62093
    0x0F28E: "High Voltage Energy Storage Pack 15 Data 1",   # 62094
    0x0F28F: "High Voltage Energy Storage Pack 15 Data 2",   # 62095
    0x0F290: "High Voltage Energy Storage Pack 15 Data 3",   # 62096
    0x0F291: "High Voltage Energy Storage Pack 15 Data 4",   # 62097
    0x0F292: "High Voltage Energy Storage Pack 15 Data 5",   # 62098
    0x0F293: "High Voltage Energy Storage Pack 15 Data 6",   # 62099
    0x0F294: "High Voltage Energy Storage Pack 15 Status 1",   # 62100
    0x0F295: "High Voltage Energy Storage Pack 15 Data 7",   # 62101
    0x0F296: "High Voltage Energy Storage Pack 15 Module Status 1",   # 62102
    0x0F297: "High Voltage Energy Storage Pack 15 Thermal Management System Status 1",   # 62103
    0x0F298: "High Voltage Energy Storage Pack 15 Data 8",   # 62104
    0x0F299: "High Voltage Energy Storage Pack 15 Data 9",   # 62105
    0x0F29A: "High Voltage Energy Storage Pack 15 Data 10",   # 62106
    0x0F29B: "High Voltage Energy Storage Pack 15 Data 11",   # 62107
    0x0F29C: "High Voltage Energy Storage Pack 16 Status 2",   # 62108
    0x0F29D: "High Voltage Energy Storage Pack 16 Data 1",   # 62109
    0x0F29E: "High Voltage Energy Storage Pack 16 Data 2",   # 62110
    0x0F29F: "High Voltage Energy Storage Pack 16 Data 3",   # 62111
    0x0F2A0: "High Voltage Energy Storage Pack 16 Data 4",   # 62112
    0x0F2A1: "High Voltage Energy Storage Pack 16 Data 5",   # 62113
    0x0F2A2: "High Voltage Energy Storage Pack 16 Data 6",   # 62114
    0x0F2A3: "High Voltage Energy Storage Pack 16 Status 1",   # 62115
    0x0F2A4: "High Voltage Energy Storage Pack 16 Data 7",   # 62116
    0x0F2A5: "High Voltage Energy Storage Pack 16 Module Status 1",   # 62117
    0x0F2A6: "High Voltage Energy Storage Pack 16 Thermal Management System Status 1",   # 62118
    0x0F2A7: "High Voltage Energy Storage Pack 16 Data 8",   # 62119
    0x0F2A8: "High Voltage Energy Storage Pack 16 Data 9",   # 62120
    0x0F2A9: "High Voltage Energy Storage Pack 16 Data 10",   # 62121
    0x0F2AA: "High Voltage Energy Storage Pack 16 Data 11",   # 62122
    0x0F2AB: "High Voltage Energy Storage Pack 17 Status 2",   # 62123
    0x0F2AC: "High Voltage Energy Storage Pack 17 Data 1",   # 62124
    0x0F2AD: "High Voltage Energy Storage Pack 17 Data 2",   # 62125
    0x0F2AE: "High Voltage Energy Storage Pack 17 Data 3",   # 62126
    0x0F2AF: "High Voltage Energy Storage Pack 17 Data 4",   # 62127
    0x0F2B0: "High Voltage Energy Storage Pack 17 Data 5",   # 62128
    0x0F2B1: "High Voltage Energy Storage Pack 17 Data 6",   # 62129
    0x0F2B2: "High Voltage Energy Storage Pack 17 Status 1",   # 62130
    0x0F2B3: "High Voltage Energy Storage Pack 17 Data 7",   # 62131
    0x0F2B4: "High Voltage Energy Storage Pack 17 Module Status 1",   # 62132
    0x0F2B5: "High Voltage Energy Storage Pack 17 Thermal Management System Status 1",   # 62133
    0x0F2B6: "High Voltage Energy Storage Pack 17 Data 8",   # 62134
    0x0F2B7: "High Voltage Energy Storage Pack 17 Data 9",   # 62135
    0x0F2B8: "High Voltage Energy Storage Pack 17 Data 10",   # 62136
    0x0F2B9: "High Voltage Energy Storage Pack 17 Data 11",   # 62137
    0x0F2BA: "High Voltage Energy Storage Pack 18 Status 2",   # 62138
    0x0F2BB: "High Voltage Energy Storage Pack 18 Data 1",   # 62139
    0x0F2BC: "High Voltage Energy Storage Pack 18 Data 2",   # 62140
    0x0F2BD: "High Voltage Energy Storage Pack 18 Data 3",   # 62141
    0x0F2BE: "High Voltage Energy Storage Pack 18 Data 4",   # 62142
    0x0F2BF: "High Voltage Energy Storage Pack 18 Data 5",   # 62143
    0x0F2C0: "High Voltage Energy Storage Pack 18 Data 6",   # 62144
    0x0F2C1: "High Voltage Energy Storage Pack 18 Status 1",   # 62145
    0x0F2C2: "High Voltage Energy Storage Pack 18 Data 7",   # 62146
    0x0F2C3: "High Voltage Energy Storage Pack 18 Module Status 1",   # 62147
    0x0F2C4: "High Voltage Energy Storage Pack 18 Thermal Management System Status 1",   # 62148
    0x0F2C5: "High Voltage Energy Storage Pack 18 Data 8",   # 62149
    0x0F2C6: "High Voltage Energy Storage Pack 18 Data 9",   # 62150
    0x0F2C7: "High Voltage Energy Storage Pack 18 Data 10",   # 62151
    0x0F2C8: "High Voltage Energy Storage Pack 18 Data 11",   # 62152
    0x0F2C9: "High Voltage Energy Storage Pack 19 Status 2",   # 62153
    0x0F2CA: "High Voltage Energy Storage Pack 19 Data 1",   # 62154
    0x0F2CB: "High Voltage Energy Storage Pack 19 Data 2",   # 62155
    0x0F2CC: "High Voltage Energy Storage Pack 19 Data 3",   # 62156
    0x0F2CD: "High Voltage Energy Storage Pack 19 Data 4",   # 62157
    0x0F2CE: "High Voltage Energy Storage Pack 19 Data 5",   # 62158
    0x0F2CF: "High Voltage Energy Storage Pack 19 Data 6",   # 62159
    0x0F2D0: "High Voltage Energy Storage Pack 19 Status 1",   # 62160
    0x0F2D1: "High Voltage Energy Storage Pack 19 Data 7",   # 62161
    0x0F2D2: "High Voltage Energy Storage Pack 19 Module Status 1",   # 62162
    0x0F2D3: "High Voltage Energy Storage Pack 19 Thermal Management System Status 1",   # 62163
    0x0F2D4: "High Voltage Energy Storage Pack 19 Data 8",   # 62164
    0x0F2D5: "High Voltage Energy Storage Pack 19 Data 9",   # 62165
    0x0F2D6: "High Voltage Energy Storage Pack 19 Data 10",   # 62166
    0x0F2D7: "High Voltage Energy Storage Pack 19 Data 11",   # 62167
    0x0F2D8: "High Voltage Energy Storage Pack 20 Status 2",   # 62168
    0x0F2D9: "High Voltage Energy Storage Pack 20 Data 1",   # 62169
    0x0F2DA: "High Voltage Energy Storage Pack 20 Data 2",   # 62170
    0x0F2DB: "High Voltage Energy Storage Pack 20 Data 3",   # 62171
    0x0F2DC: "High Voltage Energy Storage Pack 20 Data 4",   # 62172
    0x0F2DD: "High Voltage Energy Storage Pack 20 Data 5",   # 62173
    0x0F2DE: "High Voltage Energy Storage Pack 20 Data 6",   # 62174
    0x0F2DF: "High Voltage Energy Storage Pack 20 Status 1",   # 62175
    0x0F2E0: "High Voltage Energy Storage Pack 20 Data 7",   # 62176
    0x0F2E1: "High Voltage Energy Storage Pack 20 Module Status 1",   # 62177
    0x0F2E2: "High Voltage Energy Storage Pack 20 Thermal Management System Status 1",   # 62178
    0x0F2E3: "High Voltage Energy Storage Pack 20 Data 8",   # 62179
    0x0F2E4: "High Voltage Energy Storage Pack 20 Data 9",   # 62180
    0x0F2E5: "High Voltage Energy Storage Pack 20 Data 10",   # 62181
    0x0F2E6: "High Voltage Energy Storage Pack 20 Data 11",   # 62182
    0x0F2E7: "High Voltage Energy Storage Pack 21 Status 2",   # 62183
    0x0F2E8: "High Voltage Energy Storage Pack 21 Data 1",   # 62184
    0x0F2E9: "High Voltage Energy Storage Pack 21 Data 2",   # 62185
    0x0F2EA: "High Voltage Energy Storage Pack 21 Data 3",   # 62186
    0x0F2EB: "High Voltage Energy Storage Pack 21 Data 4",   # 62187
    0x0F2EC: "High Voltage Energy Storage Pack 21 Data 5",   # 62188
    0x0F2ED: "High Voltage Energy Storage Pack 21 Data 6",   # 62189
    0x0F2EE: "High Voltage Energy Storage Pack 21 Status 1",   # 62190
    0x0F2EF: "High Voltage Energy Storage Pack 21 Data 7",   # 62191
    0x0F2F0: "High Voltage Energy Storage Pack 21 Module Status 1",   # 62192
    0x0F2F1: "High Voltage Energy Storage Pack 21 Thermal Management System Status 1",   # 62193
    0x0F2F2: "High Voltage Energy Storage Pack 21 Data 8",   # 62194
    0x0F2F3: "High Voltage Energy Storage Pack 21 Data 9",   # 62195
    0x0F2F4: "High Voltage Energy Storage Pack 21 Data 10",   # 62196
    0x0F2F5: "High Voltage Energy Storage Pack 21 Data 11",   # 62197
    0x0F2F6: "High Voltage Energy Storage Pack 22 Status 2",   # 62198
    0x0F2F7: "High Voltage Energy Storage Pack 22 Data 1",   # 62199
    0x0F2F8: "High Voltage Energy Storage Pack 22 Data 2",   # 62200
    0x0F2F9: "High Voltage Energy Storage Pack 22 Data 3",   # 62201
    0x0F2FA: "High Voltage Energy Storage Pack 22 Data 4",   # 62202
    0x0F2FB: "High Voltage Energy Storage Pack 22 Data 5",   # 62203
    0x0F2FC: "High Voltage Energy Storage Pack 22 Data 6",   # 62204
    0x0F2FD: "High Voltage Energy Storage Pack 22 Status 1",   # 62205
    0x0F2FE: "High Voltage Energy Storage Pack 22 Data 7",   # 62206
    0x0F2FF: "High Voltage Energy Storage Pack 22 Module Status 1",   # 62207
    0x0F300: "High Voltage Energy Storage Pack 22 Thermal Management System Status 1",   # 62208
    0x0F301: "High Voltage Energy Storage Pack 22 Data 8",   # 62209
    0x0F302: "High Voltage Energy Storage Pack 22 Data 9",   # 62210
    0x0F303: "High Voltage Energy Storage Pack 22 Data 10",   # 62211
    0x0F304: "High Voltage Energy Storage Pack 22 Data 11",   # 62212
    0x0F305: "High Voltage Energy Storage Pack 23 Status 2",   # 62213
    0x0F306: "High Voltage Energy Storage Pack 23 Data 1",   # 62214
    0x0F307: "High Voltage Energy Storage Pack 23 Data 2",   # 62215
    0x0F308: "High Voltage Energy Storage Pack 23 Data 3",   # 62216
    0x0F309: "High Voltage Energy Storage Pack 23 Data 4",   # 62217
    0x0F30A: "High Voltage Energy Storage Pack 23 Data 5",   # 62218
    0x0F30B: "High Voltage Energy Storage Pack 23 Data 6",   # 62219
    0x0F30C: "High Voltage Energy Storage Pack 23 Status 1",   # 62220
    0x0F30D: "High Voltage Energy Storage Pack 23 Data 7",   # 62221
    0x0F30E: "High Voltage Energy Storage Pack 23 Module Status 1",   # 62222
    0x0F30F: "High Voltage Energy Storage Pack 23 Thermal Management System Status 1",   # 62223
    0x0F310: "High Voltage Energy Storage Pack 23 Data 8",   # 62224
    0x0F311: "High Voltage Energy Storage Pack 23 Data 9",   # 62225
    0x0F312: "High Voltage Energy Storage Pack 23 Data 10",   # 62226
    0x0F313: "High Voltage Energy Storage Pack 23 Data 11",   # 62227
    0x0F314: "High Voltage Energy Storage Pack 24 Status 2",   # 62228
    0x0F315: "High Voltage Energy Storage Pack 24 Data 1",   # 62229
    0x0F316: "High Voltage Energy Storage Pack 24 Data 2",   # 62230
    0x0F317: "High Voltage Energy Storage Pack 24 Data 3",   # 62231
    0x0F318: "High Voltage Energy Storage Pack 24 Data 4",   # 62232
    0x0F319: "High Voltage Energy Storage Pack 24 Data 5",   # 62233
    0x0F31A: "High Voltage Energy Storage Pack 24 Data 6",   # 62234
    0x0F31B: "High Voltage Energy Storage Pack 24 Status 1",   # 62235
    0x0F31C: "High Voltage Energy Storage Pack 24 Data 7",   # 62236
    0x0F31D: "High Voltage Energy Storage Pack 24 Module Status 1",   # 62237
    0x0F31E: "High Voltage Energy Storage Pack 24 Thermal Management System Status 1",   # 62238
    0x0F31F: "High Voltage Energy Storage Pack 24 Data 8",   # 62239
    0x0F320: "High Voltage Energy Storage Pack 24 Data 9",   # 62240
    0x0F321: "High Voltage Energy Storage Pack 24 Data 10",   # 62241
    0x0F322: "High Voltage Energy Storage Pack 24 Data 11",   # 62242
    0x0F323: "High Voltage Energy Storage Pack 25 Status 2",   # 62243
    0x0F324: "High Voltage Energy Storage Pack 25 Data 1",   # 62244
    0x0F325: "High Voltage Energy Storage Pack 25 Data 2",   # 62245
    0x0F326: "High Voltage Energy Storage Pack 25 Data 3",   # 62246
    0x0F327: "High Voltage Energy Storage Pack 25 Data 4",   # 62247
    0x0F328: "High Voltage Energy Storage Pack 25 Data 5",   # 62248
    0x0F329: "High Voltage Energy Storage Pack 25 Data 6",   # 62249
    0x0F32A: "High Voltage Energy Storage Pack 25 Status 1",   # 62250
    0x0F32B: "High Voltage Energy Storage Pack 25 Data 7",   # 62251
    0x0F32C: "High Voltage Energy Storage Pack 25 Module Status 1",   # 62252
    0x0F32D: "High Voltage Energy Storage Pack 25 Thermal Management System Status 1",   # 62253
    0x0F32E: "High Voltage Energy Storage Pack 25 Data 8",   # 62254
    0x0F32F: "High Voltage Energy Storage Pack 25 Data 9",   # 62255
    0x0F330: "High Voltage Energy Storage Pack 25 Data 10",   # 62256
    0x0F331: "High Voltage Energy Storage Pack 25 Data 11",   # 62257
    0x0F332: "High Voltage Energy Storage Pack 26 Status 2",   # 62258
    0x0F333: "High Voltage Energy Storage Pack 26 Data 1",   # 62259
    0x0F334: "High Voltage Energy Storage Pack 26 Data 2",   # 62260
    0x0F335: "High Voltage Energy Storage Pack 26 Data 3",   # 62261
    0x0F336: "High Voltage Energy Storage Pack 26 Data 4",   # 62262
    0x0F337: "High Voltage Energy Storage Pack 26 Data 5",   # 62263
    0x0F338: "High Voltage Energy Storage Pack 26 Data 6",   # 62264
    0x0F339: "High Voltage Energy Storage Pack 26 Status 1",   # 62265
    0x0F33A: "High Voltage Energy Storage Pack 26 Data 7",   # 62266
    0x0F33B: "High Voltage Energy Storage Pack 26 Module Status 1",   # 62267
    0x0F33C: "High Voltage Energy Storage Pack 26 Thermal Management System Status 1",   # 62268
    0x0F33D: "High Voltage Energy Storage Pack 26 Data 8",   # 62269
    0x0F33E: "High Voltage Energy Storage Pack 26 Data 9",   # 62270
    0x0F33F: "High Voltage Energy Storage Pack 26 Data 10",   # 62271
    0x0F340: "High Voltage Energy Storage Pack 26 Data 11",   # 62272
    0x0F341: "External Steering Request",   # 62273
    0x0F342: "Active Steering System Controller 2",   # 62274
    0x0F343: "Electronic Park Brake Controller 1",   # 62275
    0x0F344: "Electronic Park Brake Controller 2",   # 62276
    0x0F345: "Genset Frequency Limitation",   # 62277
    0x0F346: "Genset Power Limitation",   # 62278
    0x0F347: "Genset Real Power Control",   # 62279
    0x0F34A: "Genset Real Power Setpoint Demand",   # 62282
    0x0F34B: "Genset Real Power Control 2",   # 62283
    0x0F34C: "High Voltage Energy Storage Pack 1 Data 12",   # 62284
    0x0F34D: "High Voltage Energy Storage Pack 1 Data 13",   # 62285
    0x0F34E: "High Voltage Energy Storage Pack 2 Data 12",   # 62286
    0x0F34F: "High Voltage Energy Storage Pack 2 Data 13",   # 62287
    0x0F350: "High Voltage Energy Storage Pack 3 Data 12",   # 62288
    0x0F351: "High Voltage Energy Storage Pack 3 Data 13",   # 62289
    0x0F352: "High Voltage Energy Storage Pack 4 Data 12",   # 62290
    0x0F353: "High Voltage Energy Storage Pack 4 Data 13",   # 62291
    0x0F354: "High Voltage Energy Storage Pack 5 Data 12",   # 62292
    0x0F355: "High Voltage Energy Storage Pack 5 Data 13",   # 62293
    0x0F356: "High Voltage Energy Storage Pack 6 Data 12",   # 62294
    0x0F357: "High Voltage Energy Storage Pack 6 Data 13",   # 62295
    0x0F358: "High Voltage Energy Storage Pack 7 Data 12",   # 62296
    0x0F359: "High Voltage Energy Storage Pack 7 Data 13",   # 62297
    0x0F35A: "High Voltage Energy Storage Pack 8 Data 12",   # 62298
    0x0F35B: "High Voltage Energy Storage Pack 8 Data 13",   # 62299
    0x0F35C: "High Voltage Energy Storage Pack 9 Data 12",   # 62300
    0x0F35D: "High Voltage Energy Storage Pack 9 Data 13",   # 62301
    0x0F35E: "High Voltage Energy Storage Pack 10 Data 12",   # 62302
    0x0F35F: "High Voltage Energy Storage Pack 10 Data 13",   # 62303
    0x0F360: "High Voltage Energy Storage Pack 11 Data 12",   # 62304
    0x0F361: "High Voltage Energy Storage Pack 11 Data 13",   # 62305
    0x0F362: "High Voltage Energy Storage Pack 12 Data 12",   # 62306
    0x0F363: "High Voltage Energy Storage Pack 12 Data 13",   # 62307
    0x0FA24: "High Voltage Energy Storage System Data 12",   # 64036
    0x0FA25: "High Voltage Energy Storage System Data 13",   # 64037
    0x0FA26: "High Voltage Energy Storage System Data 14",   # 64038
    0x0FA27: "High Voltage Energy Storage Pack 1 Internal Status 1",   # 64039
    0x0FA28: "High Voltage Energy Storage Pack 2 Internal Status 1",   # 64040
    0x0FA29: "High Voltage Energy Storage Pack 3 Internal Status 1",   # 64041
    0x0FA2A: "High Voltage Energy Storage Pack 4 Internal Status 1",   # 64042
    0x0FA2B: "High Voltage Energy Storage Pack 5 Internal Status 1",   # 64043
    0x0FA2C: "High Voltage Energy Storage Pack 6 Internal Status 1",   # 64044
    0x0FA2D: "High Voltage Energy Storage Pack 7 Internal Status 1",   # 64045
    0x0FA2E: "High Voltage Energy Storage Pack 8 Internal Status 1",   # 64046
    0x0FA2F: "High Voltage Energy Storage Pack 9 Internal Status 1",   # 64047
    0x0FA30: "High Voltage Energy Storage Pack 10 Internal Status 1",   # 64048
    0x0FA31: "High Voltage Energy Storage Pack 11 Internal Status 1",   # 64049
    0x0FA32: "High Voltage Energy Storage Pack 12 Internal Status 1",   # 64050
    0x0FA35: "Refuse Truck Body Information",   # 64053
    0x0FA36: "Engine Fluid Level/Pressure 14",   # 64054
    0x0FA37: "Well Stimulation Transmission Control Configuration",   # 64055
    0x0FA38: "Well Stimulation Pump Protection System Configuration Command 1",   # 64056
    0x0FA39: "Well Stimulation Pump Protection System Configuration Command 2",   # 64057
    0x0FA3A: "Electric PTO Drive Engagement 1",   # 64058
    0x0FA3B: "Electric PTO 1 Information",   # 64059
    0x0FA3C: "Engine Exhaust O2 Sensor Information",   # 64060
    0x0FA3D: "Gaseous Fuel Supply Pressure 3",   # 64061
    0x0FA3E: "Traffic Signage",   # 64062
    0x0FA3F: "Engine Configuration 4",   # 64063
    0x0FA44: "Engine Speed/Load Factor Information 2",   # 64068
    0x0FA45: "Generator Trip Energy 2",   # 64069
    0x0FA46: "Security System Machine Operation Information",   # 64070
    0x0FA47: "Engine Fuel Actuator Service Mode",   # 64071
    0x0FA48: "Steering Wheel Controls",   # 64072
    0x0FA49: "Park Assist",   # 64073
    0x0FA4B: "Aftertreatment 2 SCR Dosing System Information 5",   # 64075
    0x0FA4C: "Aftertreatment 1 SCR Dosing System Information 5",   # 64076
    0x0FA4D: "EV Economy Information",   # 64077
    0x0FA4E: "Automated Driving System Status 2",   # 64078
    0x0FA4F: "Automated Driving System Control 3",   # 64079
    0x0FA50: "Aftercooler Valve",   # 64080
    0x0FA51: "Engine Radiator 1",   # 64081
    0x0FA52: "Engine Radiator 2",   # 64082
    0x0FA53: "Genset Enclosure Ventilation",   # 64083
    0x0FA54: "Heat Exchanger 1",   # 64084
    0x0FA55: "Heat Exchanger 2",   # 64085
    0x0FA56: "Heat Exchanger 3",   # 64086
    0x0FA57: "Heat Exchanger 4",   # 64087
    0x0FA58: "Engine Exhaust Gas Heat Exchanger",   # 64088
    0x0FA59: "Genset Enclosure Ventilation Louver",   # 64089
    0x0FA5A: "Genset External Coolant System",   # 64090
    0x0FA5B: "EV DC Status 1",   # 64091
    0x0FA5C: "EVSE 1 DC Charging Limits 3",   # 64092
    0x0FA5D: "EVSE 1 Power Max Schedule",   # 64093
    0x0FA5E: "EV Charge Profile",   # 64094
    0x0FA5F: "EV DC Charging Limits 2",   # 64095
    0x0FA60: "EV DC Charging In Progress",   # 64096
    0x0FA62: "Lighting Data 2",   # 64098
    0x0FA63: "Lighting Command 2",   # 64099
    0x0FA64: "Aftertreatment System Information 5",   # 64100
    0x0FA65: "Aftertreatment System Information 4",   # 64101
    0x0FA66: "Aftertreatment System Information 3",   # 64102
    0x0FA67: "Fluid Resistance 1",   # 64103
    0x0FA68: "Power Converter 2 Isolation Integrity Request",   # 64104
    0x0FA69: "Power Converter 1 Isolation Integrity Request",   # 64105
    0x0FA6A: "Power Converter 2 Limits Request Power",   # 64106
    0x0FA6B: "Power Converter 2 Limits Request Electrical",   # 64107
    0x0FA6C: "Power Converter 2 Limits Request DC Energy Source 1",   # 64108
    0x0FA6D: "Power Converter 1 Limits Request DC Energy Source 1",   # 64109
    0x0FA6E: "Power Converter 1 Limits Request Electrical",   # 64110
    0x0FA6F: "Power Converter 1 Limits Request Power",   # 64111
    0x0FA70: "Inverter 1 Lifetime Data",   # 64112
    0x0FA71: "Inverter 2 Lifetime Data",   # 64113
    0x0FA72: "Power Converter 2 Active Power Limits",   # 64114
    0x0FA73: "Power Converter 1 Active Power Limits",   # 64115
    0x0FA74: "Power Converter 2 Reference 1",   # 64116
    0x0FA75: "Power Converter 2 Reference 2",   # 64117
    0x0FA76: "Power Converter 2 Temperature",   # 64118
    0x0FA77: "Power Converter 1 Temperature",   # 64119
    0x0FA78: "Power Converter 1 Reference 2",   # 64120
    0x0FA79: "Power Converter 1 Reference 1",   # 64121
    0x0FA7A: "Power Converter 1 Phase Current",   # 64122
    0x0FA7B: "Power Converter 2 Phase Current",   # 64123
    0x0FA7C: "Power Converter 1 Phase Voltage",   # 64124
    0x0FA7D: "Power Converter 2 Phase Voltage",   # 64125
    0x0FA7E: "Power Converter Power Module Switch Temperatures",   # 64126
    0x0FA7F: "Power Converter 1 Power Module Switch Power Supply Voltage",   # 64127
    0x0FA80: "Power Converter 2 Power Module Switch Power Supply Voltage",   # 64128
    0x0FA81: "Power Converter Totals 1",   # 64129
    0x0FA82: "Transformer Temperatures",   # 64130
    0x0FA83: "Electrified Accessory Engine Coolant Pump Status",   # 64131
    0x0FA84: "High Voltage Energy Storage Pack 11 History",   # 64132
    0x0FA85: "High Voltage Energy Storage Pack 11 Configuration",   # 64133
    0x0FA86: "High Voltage Energy Storage Pack 12 History",   # 64134
    0x0FA87: "High Voltage Energy Storage Pack 12 Configuration",   # 64135
    0x0FA88: "High Voltage Energy Storage Pack 13 History",   # 64136
    0x0FA89: "High Voltage Energy Storage Pack 13 Configuration",   # 64137
    0x0FA8A: "High Voltage Energy Storage Pack 14 History",   # 64138
    0x0FA8B: "High Voltage Energy Storage Pack 14 Configuration",   # 64139
    0x0FA8C: "High Voltage Energy Storage Pack 15 History",   # 64140
    0x0FA8D: "High Voltage Energy Storage Pack 15 Configuration",   # 64141
    0x0FA8E: "High Voltage Energy Storage Pack 16 History",   # 64142
    0x0FA8F: "High Voltage Energy Storage Pack 16 Configuration",   # 64143
    0x0FA90: "High Voltage Energy Storage Pack 17 History",   # 64144
    0x0FA91: "High Voltage Energy Storage Pack 17 Configuration",   # 64145
    0x0FA92: "High Voltage Energy Storage Pack 18 History",   # 64146
    0x0FA93: "High Voltage Energy Storage Pack 18 Configuration",   # 64147
    0x0FA94: "High Voltage Energy Storage Pack 19 History",   # 64148
    0x0FA95: "High Voltage Energy Storage Pack 19 Configuration",   # 64149
    0x0FA96: "High Voltage Energy Storage Pack 20 History",   # 64150
    0x0FA97: "High Voltage Energy Storage Pack 20 Configuration",   # 64151
    0x0FA98: "High Voltage Energy Storage Pack 21 History",   # 64152
    0x0FA99: "High Voltage Energy Storage Pack 21 Configuration",   # 64153
    0x0FA9A: "High Voltage Energy Storage Pack 22 History",   # 64154
    0x0FA9B: "High Voltage Energy Storage Pack 22 Configuration",   # 64155
    0x0FA9C: "High Voltage Energy Storage Pack 23 History",   # 64156
    0x0FA9D: "High Voltage Energy Storage Pack 23 Configuration",   # 64157
    0x0FA9E: "High Voltage Energy Storage Pack 24 History",   # 64158
    0x0FA9F: "High Voltage Energy Storage Pack 24 Configuration",   # 64159
    0x0FAA0: "High Voltage Energy Storage Pack 25 History",   # 64160
    0x0FAA1: "High Voltage Energy Storage Pack 25 Configuration",   # 64161
    0x0FAA2: "High Voltage Energy Storage Pack 26 History",   # 64162
    0x0FAA3: "High Voltage Energy Storage Pack 26 Configuration",   # 64163
    0x0FAA4: "Automated Driving System Control 2",   # 64164
    0x0FAA5: "Duel Fuel Mode 3",   # 64165
    0x0FAA6: "Duel Fuel Mode 2",   # 64166
    0x0FAA7: "Dual Fuel Mode 1",   # 64167
    0x0FAA8: "Transmission 1 History",   # 64168
    0x0FAA9: "Transmission Shaft Twist Information",   # 64169
    0x0FAAA: "Electronic Auxiliary Transmission Controller 2",   # 64170
    0x0FAAB: "High Voltage Energy Storage Pack 10 Configuration",   # 64171
    0x0FAAC: "High Voltage Energy Storage Pack 10 History",   # 64172
    0x0FAAD: "High Voltage Energy Storage Pack 9 Configuration",   # 64173
    0x0FAAE: "High Voltage Energy Storage Pack 9 History",   # 64174
    0x0FAAF: "High Voltage Energy Storage Pack 8 Configuration",   # 64175
    0x0FAB0: "High Voltage Energy Storage Pack 8 History",   # 64176
    0x0FAB1: "High Voltage Energy Storage Pack 7 Configuration",   # 64177
    0x0FAB2: "High Voltage Energy Storage Pack 7 History",   # 64178
    0x0FAB4: "EV DC Charging Limits 1",   # 64180
    0x0FAB5: "EVSE 1 DC Charging Limits 1",   # 64181
    0x0FAB6: "EVSE 1 DC Charging Limits 2",   # 64182
    0x0FAB7: "EV DC Charging Target",   # 64183
    0x0FAB8: "EVSE 1 DC Status 1",   # 64184
    0x0FAB9: "EVSE 1 Contactor Cmd 1",   # 64185
    0x0FABA: "EVSE 1 Contactor Status 1",   # 64186
    0x0FABB: "Direct Lamp Control Command 3",   # 64187
    0x0FABC: "Direct Lamp Control Data 3",   # 64188
    0x0FABD: "Motor/Generator 1 Lifetime Data",   # 64189
    0x0FABE: "Motor/Generator 2 Lifetime Data",   # 64190
    0x0FABF: "Motor/Generator 3 Lifetime Data",   # 64191
    0x0FAC0: "Motor/Generator 4 Lifetime Data",   # 64192
    0x0FAC1: "Motor/Generator 5 Lifetime Data",   # 64193
    0x0FAC2: "Motor/Generator 6 Lifetime Data",   # 64194
    0x0FAC3: "Air Supply Pressure 3",   # 64195
    0x0FAC4: "EVSE 1 AC Supply Voltage",   # 64196
    0x0FAC5: "EVSE1 AC 3-Phase Load",   # 64197
    0x0FAC6: "Electronic Retarder Controller 3",   # 64198
    0x0FAC8: "Electronic Transmission Controller 14",   # 64200
    0x0FACD: "Aftertreatment 1 SCR Exhaust Gas Pressures 2",   # 64205
    0x0FACE: "PTO Information 2",   # 64206
    0x0FACF: "EVCC1 Diagnostic Data 1",   # 64207
    0x0FAD0: "Cab Door Control 2",   # 64208
    0x0FAD1: "Engine Average Information 2",   # 64209
    0x0FAD2: "Turbocharger Information 9",   # 64210
    0x0FAD3: "Automated Driving System Control 1",   # 64211
    0x0FAD4: "EVSE 1 AC Status 2",   # 64212
    0x0FAD5: "EVSE 1 AC Status 1",   # 64213
    0x0FAD6: "EVSE 1 Status 1",   # 64214
    0x0FAED: "Temperature Sensing Module 1",   # 64237
    0x0FAEE: "Temperature Sensing Module 2",   # 64238
    0x0FAEF: "Aftertreatment 2 SCR Service Information 3",   # 64239
    0x0FAF0: "Aftertreatment 1 SCR Service Information 3",   # 64240
    0x0FAF1: "PSA Times Lifetime Hours",   # 64241
    0x0FAF2: "PSA Times Stored 100 Hours",   # 64242
    0x0FAF3: "PSA Times Active 100 Hours",   # 64243
    0x0FAF4: "Hybrid Charge Depleting or Increasing Operation Lifetime Hours",   # 64244
    0x0FAF5: "Hybrid Charge Depleting or Increasing Operation Stored 100 Hours",   # 64245
    0x0FAF6: "Hybrid Charge Depleting or Increasing Operation Active 100 Hours",   # 64246
    0x0FAF7: "Aftertreatment 1 Historical Information 3",   # 64247
    0x0FAF9: "Aftertreatment 1 SCR 2 NOx Mass and NH3 Storage",   # 64249
    0x0FAFA: "Aftertreatment 1 SCR 1 NOx Mass and NH3 Storage",   # 64250
    0x0FAFB: "Evaporative System Pressure and Control",   # 64251
    0x0FAFC: "GHG Tracking Lifetime Array Data",   # 64252
    0x0FAFD: "GHG Tracking Stored 100 Hour Array Data",   # 64253
    0x0FAFE: "GHG Tracking Active 100 Hour Array Data",   # 64254
    0x0FB02: "NOx Tracking Engine Activity Lifetime Fuel Consumption Bins",   # 64258
    0x0FB03: "NOx Tracking Engine Activity Lifetime Engine Run Time Bins",   # 64259
    0x0FB04: "NOx Tracking Engine Activity Lifetime Vehicle Distance Bins",   # 64260
    0x0FB05: "NOx Tracking Engine Activity Lifetime Engine Output Energy Bins",   # 64261
    0x0FB06: "NOx Tracking Valid NOx Lifetime Fuel Consumption Bins",   # 64262
    0x0FB07: "NOx Tracking Valid NOx Lifetime Engine Run Time Bins",   # 64263
    0x0FB08: "NOx Tracking Valid NOx Lifetime Vehicle Distance Bins",   # 64264
    0x0FB09: "NOx Tracking Valid NOx Lifetime Engine Output Energy Bins",   # 64265
    0x0FB0A: "NOx Tracking Valid NOx Lifetime Engine Out NOx Mass Bins",   # 64266
    0x0FB0B: "NOx Tracking Valid NOx Lifetime System Out NOx Mass Bins",   # 64267
    0x0FB0C: "NOx Tracking Stored 100 Hour Fuel Consumption Bins",   # 64268
    0x0FB0D: "NOx Tracking Stored 100 Hour Engine Run Time Bins",   # 64269
    0x0FB0E: "NOx Tracking Stored 100 Hour Vehicle Distance Bins",   # 64270
    0x0FB0F: "NOx Tracking Stored 100 Hour Engine Output Energy Bins",   # 64271
    0x0FB10: "NOx Tracking Stored 100 Hour Engine Out NOx Mass Bins",   # 64272
    0x0FB11: "NOx Tracking Stored 100 Hour System Out NOx Mass Bins",   # 64273
    0x0FB12: "NOx Tracking Active 100 Hour Fuel Consumption Bins",   # 64274
    0x0FB13: "NOx Tracking Active 100 Hour Engine Run Time Bins",   # 64275
    0x0FB14: "NOx Tracking Active 100 Hour Vehicle Distance Bins",   # 64276
    0x0FB15: "NOx Tracking Active 100 Hour Engine Output Energy Bins",   # 64277
    0x0FB16: "NOx Tracking Active 100 Hour Engine Out NOx Mass Bins",   # 64278
    0x0FB17: "NOx Tracking Active 100 Hour System Out NOx Mass Bins",   # 64279
    0x0FB18: "Motor/Generator 6 Inverter Control 2",   # 64280
    0x0FB19: "Motor/Generator 6 Inverter Limits Request Power",   # 64281
    0x0FB1A: "Motor/Generator 6 Inverter Limits Request Mechanical",   # 64282
    0x0FB1B: "Motor/Generator 6 Inverter Limits Request DC Side",   # 64283
    0x0FB1C: "Motor/Generator 6 Inverter Isolation Integrity Request",   # 64284
    0x0FB1D: "Motor/Generator 5 Inverter Control 2",   # 64285
    0x0FB1E: "Motor/Generator 5 Inverter Limits Request Power",   # 64286
    0x0FB1F: "Motor/Generator 5 Inverter Limits Request Mechanical",   # 64287
    0x0FB20: "Motor/Generator 5 Inverter Limits Request DC Side",   # 64288
    0x0FB21: "Motor/Generator 5 Inverter Isolation Integrity Request",   # 64289
    0x0FB22: "Motor/Generator 4 Inverter Control 2",   # 64290
    0x0FB23: "Motor/Generator 4 Inverter Limits Request Power",   # 64291
    0x0FB24: "Motor/Generator 4 Inverter Limits Request Mechanical",   # 64292
    0x0FB25: "Motor/Generator 4 Inverter Limits Request DC Side",   # 64293
    0x0FB26: "Motor/Generator 4 Inverter Isolation Integrity Request",   # 64294
    0x0FB27: "Motor/Generator 3 Inverter Control 2",   # 64295
    0x0FB28: "Motor/Generator 3 Inverter Limits Request Power",   # 64296
    0x0FB29: "Motor/Generator 3 Inverter Limits Request Mechanical",   # 64297
    0x0FB2A: "Motor/Generator 3 Inverter Limits Request DC Side",   # 64298
    0x0FB2B: "Motor/Generator 3 Inverter Isolation Integrity Request",   # 64299
    0x0FB2D: "Turbocharger Information 8",   # 64301
    0x0FB2E: "Winch Information 2",   # 64302
    0x0FB2F: "Motor/Generator 6 Inverter Reference 1",   # 64303
    0x0FB30: "Motor/Generator 6 Inverter Status 1",   # 64304
    0x0FB31: "Motor/Generator 6 Inverter Reference 2",   # 64305
    0x0FB32: "Motor/Generator 6 Inverter Temperature",   # 64306
    0x0FB33: "Motor/Generator 6 Inverter Motor Temperature",   # 64307
    0x0FB34: "Motor/Generator 6 Inverter Isolation Integrity",   # 64308
    0x0FB35: "Motor/Generator 6 Inverter Active Power Limits",   # 64309
    0x0FB36: "Motor/Generator 5 Inverter Reference 1",   # 64310
    0x0FB37: "Motor/Generator 5 Inverter Status 1",   # 64311
    0x0FB38: "Motor/Generator 5 Inverter Reference 2",   # 64312
    0x0FB39: "Motor/Generator 5 Inverter Temperature",   # 64313
    0x0FB3A: "Motor/Generator 5 Inverter Motor Temperature",   # 64314
    0x0FB3B: "Motor/Generator 5 Inverter Isolation Integrity",   # 64315
    0x0FB3C: "Motor/Generator 5 Inverter Active Power Limits",   # 64316
    0x0FB3D: "Motor/Generator 4 Inverter Reference 1",   # 64317
    0x0FB3E: "Motor/Generator 4 Inverter Status 1",   # 64318
    0x0FB3F: "Motor/Generator 4 Inverter Reference 2",   # 64319
    0x0FB40: "Motor/Generator 4 Inverter Temperature",   # 64320
    0x0FB41: "Motor/Generator 4 Inverter Motor Temperature",   # 64321
    0x0FB42: "Motor/Generator 4 Inverter Isolation Integrity",   # 64322
    0x0FB43: "Motor/Generator 4 Inverter Active Power Limits",   # 64323
    0x0FB44: "Motor/Generator 3 Inverter Reference 1",   # 64324
    0x0FB45: "Motor/Generator 3 Inverter Status 1",   # 64325
    0x0FB46: "Motor/Generator 3 Inverter Reference 2",   # 64326
    0x0FB47: "Motor/Generator 3 Inverter Temperature",   # 64327
    0x0FB48: "Motor/Generator 3 Inverter Motor Temperature",   # 64328
    0x0FB49: "Motor/Generator 3 Inverter Isolation Integrity",   # 64329
    0x0FB4A: "Motor/Generator 3 Inverter Active Power Limits",   # 64330
    0x0FB4B: "Automated Driving System Status 1",   # 64331
    0x0FB4C: "Cab Climate System Information 2",   # 64332
    0x0FB4D: "Maintenance Information",   # 64333
    0x0FB4E: "Hoist Control Information",   # 64334
    0x0FB4F: "High Voltage Energy Storage Pack 6 History",   # 64335
    0x0FB50: "High Voltage Energy Storage Pack 6 Configuration",   # 64336
    0x0FB51: "High Voltage Energy Storage Pack 5 History",   # 64337
    0x0FB52: "High Voltage Energy Storage Pack 5 Configuration",   # 64338
    0x0FB53: "High Voltage Energy Storage Pack 4 History",   # 64339
    0x0FB54: "High Voltage Energy Storage Pack 4 Configuration",   # 64340
    0x0FB55: "High Voltage Energy Storage Pack 3 History",   # 64341
    0x0FB56: "High Voltage Energy Storage Pack 3 Configuration",   # 64342
    0x0FB57: "High Voltage Energy Storage Pack 2 History",   # 64343
    0x0FB58: "High Voltage Energy Storage Pack 2 Configuration",   # 64344
    0x0FB59: "High Voltage Energy Storage Pack 1 History",   # 64345
    0x0FB5A: "High Voltage Energy Storage Pack 1 Configuration",   # 64346
    0x0FB5B: "Vehicle Fire Suppression System Module 1 Detector Data",   # 64347
    0x0FB5C: "Vehicle Fire Suppression System Module 2 Detector Data",   # 64348
    0x0FB5D: "Vehicle Fire Suppression System Module 3 Detector Data",   # 64349
    0x0FB5E: "Vehicle Fire Suppression System Module 4 Detector Data",   # 64350
    0x0FB5F: "Vehicle Fire Suppression System Module 1 Auxilliary Data",   # 64351
    0x0FB60: "Vehicle Fire Suppression System Module 2 Auxilliary Data",   # 64352
    0x0FB61: "Vehicle Fire Suppression System Module 3 Auxilliary Data",   # 64353
    0x0FB62: "Vehicle Fire Suppression System Module 4 Auxilliary Data",   # 64354
    0x0FB63: "Vehicle Fire Suppression System Module 1 Names",   # 64355
    0x0FB64: "Vehicle Fire Suppression System Module 2 Names",   # 64356
    0x0FB65: "Vehicle Fire Suppression System Module 3 Names",   # 64357
    0x0FB66: "Vehicle Fire Suppression System Module 4 Names",   # 64358
    0x0FB67: "Motor/Generator 2 Inverter Active Power Limits",   # 64359
    0x0FB68: "Motor/Generator 2 Inverter Isolation Integrity",   # 64360
    0x0FB69: "Motor/Generator 1 Inverter Active Power Limits",   # 64361
    0x0FB6A: "Motor/Generator 1 Inverter Isolation Integrity",   # 64362
    0x0FB6B: "High Voltage Bus Information",   # 64363
    0x0FB6C: "Motor/Generator 2 Inverter Reference 1",   # 64364
    0x0FB6D: "Motor/Generator 2 Inverter Status 1",   # 64365
    0x0FB6E: "Motor/Generator 2 Inverter Reference 2",   # 64366
    0x0FB6F: "Motor/Generator 2 Inverter Temperature",   # 64367
    0x0FB70: "Motor/Generator 2 Inverter Motor Temperature",   # 64368
    0x0FB71: "Motor/Generator 1 Inverter Motor Temperature",   # 64369
    0x0FB72: "Motor/Generator 1 Inverter Temperature",   # 64370
    0x0FB73: "Motor/Generator 1 Inverter Reference 2",   # 64371
    0x0FB74: "Motor/Generator 1 Inverter Status 1",   # 64372
    0x0FB75: "Motor/Generator 1 Inverter Reference 1",   # 64373
    0x0FB76: "Personnel Detect Status",   # 64374
    0x0FB77: "Engine Cylinder Pressure Gamma 1",   # 64375
    0x0FB78: "Engine Cylinder Pressure Gamma 2",   # 64376
    0x0FB79: "Engine Cylinder Pressure Gamma 3",   # 64377
    0x0FB7A: "Engine Cylinder Pressure Gamma 4",   # 64378
    0x0FB7B: "Engine Cylinder Pressure Gamma 5",   # 64379
    0x0FB7C: "Reserved for Network Operation Mode",   # 64380
    0x0FB7D: "Electrified Accessory Generator Coolant Pump Status",   # 64381
    0x0FB7E: "Electrified Accessory Generator Coolant Fan Status",   # 64382
    0x0FB7F: "Well Stimulation Pump System Filter Information",   # 64383
    0x0FB80: "PTO Governor Configuration",   # 64384
    0x0FB81: "On Board Programming 2",   # 64385
    0x0FB82: "Primary or Rear Hitch Yaw",   # 64386
    0x0FB83: "Secondary or Front Hitch Yaw",   # 64387
    0x0FB84: "Operator Status",   # 64388
    0x0FB85: "Engine Idle Management Information",   # 64389
    0x0FB86: "Alcohol Interlock To Vehicle",   # 64390
    0x0FB87: "Vehicle To Alcohol Interlock",   # 64391
    0x0FB88: "Marine Control Information 3",   # 64392
    0x0FB89: "Engine Fluid Level/Pressure 13",   # 64393
    0x0FB8A: "High Voltage Energy Storage 1 Data 11",   # 64394
    0x0FB8B: "Economy Mode Inactive Hours",   # 64395
    0x0FB8C: "Economy Mode Estimated Instantaneous Fuel Savings Rate",   # 64396
    0x0FB8D: "Economy Mode Active Hours",   # 64397
    0x0FB8E: "Economy Mode Fuel Used",   # 64398
    0x0FB8F: "Economy Mode Estimated Fuel Savings",   # 64399
    0x0FB90: "DC/DC Converter 4 Voltage",   # 64400
    0x0FB91: "DC/DC Converter 3 Voltage",   # 64401
    0x0FB92: "DC/DC Converter 2 Voltage",   # 64402
    0x0FB93: "DC/DC Converter 1 Voltage",   # 64403
    0x0FB94: "Electronic Engine Controller 22",   # 64404
    0x0FB95: "Engine Hours 2",   # 64405
    0x0FB96: "Engine Information 3",   # 64406
    0x0FB97: "Vehicle Electrical Power 15",   # 64407
    0x0FB98: "Exhaust Oxygen 2",   # 64408
    0x0FB99: "DC/AC Accessory Inverter 1 Temperatures",   # 64409
    0x0FB9A: "DC/AC Accessory Inverter 1 DC Side Limits",   # 64410
    0x0FB9B: "DC/AC Accessory Inverter 1 AC Side Limits",   # 64411
    0x0FB9C: "DC/AC Accessory Inverter 1 Configuration 1",   # 64412
    0x0FB9D: "DC/AC Accessory Inverter 1 Lifetime Data",   # 64413
    0x0FB9E: "DC/AC Accessory Inverter 2 Temperatures",   # 64414
    0x0FB9F: "DC/AC Accessory Inverter 2 DC Side Limits",   # 64415
    0x0FBA0: "DC/AC Accessory Inverter 2 AC Side Limits",   # 64416
    0x0FBA1: "DC/AC Accessory Inverter 2 Configuration 1",   # 64417
    0x0FBA2: "DC/AC Accessory Inverter 2 Lifetime Data",   # 64418
    0x0FBA3: "DC/AC Accessory Inverter 3 Temperatures",   # 64419
    0x0FBA4: "DC/AC Accessory Inverter 3 DC Side Limits",   # 64420
    0x0FBA5: "DC/AC Accessory Inverter 3 AC Side Limits",   # 64421
    0x0FBA6: "DC/AC Accessory Inverter 3 Configuration 1",   # 64422
    0x0FBA7: "DC/AC Accessory Inverter 3 Lifetime Data",   # 64423
    0x0FBA8: "DC/AC Accessory Inverter 4 Temperatures",   # 64424
    0x0FBA9: "DC/AC Accessory Inverter 4 DC Side Limits",   # 64425
    0x0FBAA: "DC/AC Accessory Inverter 4 AC Side Limits",   # 64426
    0x0FBAB: "DC/AC Accessory Inverter 4 Configuration 1",   # 64427
    0x0FBAC: "DC/AC Accessory Inverter 4 Lifetime Data",   # 64428
    0x0FBAD: "DC/AC Accessory Inverter 5 Temperatures",   # 64429
    0x0FBAE: "DC/AC Accessory Inverter 5 DC Side Limits",   # 64430
    0x0FBAF: "DC/AC Accessory Inverter 5 AC Side Limits",   # 64431
    0x0FBB0: "DC/AC Accessory Inverter 5 Configuration 1",   # 64432
    0x0FBB1: "DC/AC Accessory Inverter 5 Lifetime Data",   # 64433
    0x0FBB2: "Well Stimulation Pump Sensor Calibration Status",   # 64434
    0x0FBB3: "Well Stimulation Pump Fluid Volume",   # 64435
    0x0FBB4: "Well Stimulation Pump Serial Number",   # 64436
    0x0FBB5: "Well Stimulation Pump Trip Hours",   # 64437
    0x0FBB6: "Aftertreatment 1 Outlet Gas 4",   # 64438
    0x0FBB7: "Aftertreatment 1 Intake Gas 4",   # 64439
    0x0FBB8: "DC/DC Converter 4 Lifetime Data",   # 64440
    0x0FBB9: "DC/DC Converter 4 Configuration 1",   # 64441
    0x0FBBA: "DC/DC Converter 4 SLI Battery Limits",   # 64442
    0x0FBBB: "DC/DC Converter 4 Temperatures",   # 64443
    0x0FBBC: "DC/DC Converter 4 Low Side Limits",   # 64444
    0x0FBBD: "DC/DC Converter 4 High Side Limits",   # 64445
    0x0FBBE: "DC/DC Converter 3 Lifetime Data",   # 64446
    0x0FBBF: "DC/DC Converter 3 Configuration 1",   # 64447
    0x0FBC0: "DC/DC Converter 3 SLI Battery Limits",   # 64448
    0x0FBC1: "DC/DC Converter 3 Temperatures",   # 64449
    0x0FBC2: "DC/DC Converter 3 Low Side Limits",   # 64450
    0x0FBC3: "DC/DC Converter 3 High Side Limits",   # 64451
    0x0FBC4: "DC/DC Converter 2 Lifetime Data",   # 64452
    0x0FBC5: "DC/DC Converter 2 Configuration 1",   # 64453
    0x0FBC6: "DC/DC Converter 2 SLI Battery Limits",   # 64454
    0x0FBC7: "DC/DC Converter 2 Temperatures",   # 64455
    0x0FBC8: "DC/DC Converter 2 Low Side Limits",   # 64456
    0x0FBC9: "DC/DC Converter 2 High Side Limits",   # 64457
    0x0FBCA: "CiA 602-2 Autosar CAN-NM",   # 64458
    0x0FBCB: "Engine Exhaust Particulate Control System Info",   # 64459
    0x0FBCC: "Well Stimulation Pump Hours",   # 64460
    0x0FBCD: "Well Stimulation Pump System Configuration Status",   # 64461
    0x0FBCE: "Configurable Receive SPNs Status",   # 64462
    0x0FBCF: "DC/DC Converter 1 Lifetime Data",   # 64463
    0x0FBD0: "DC/DC Converter 1 Configuration 1",   # 64464
    0x0FBD1: "DC/DC Converter 1 SLI Battery Limits",   # 64465
    0x0FBD2: "Pump Oil Message",   # 64466
    0x0FBD3: "Well Stimulation Pump System Lifetime Totals",   # 64467
    0x0FBD4: "Well Stimulation Pump System Configuration",   # 64468
    0x0FBD5: "Aftercooler and Oil Cooler Fluids 2",   # 64469
    0x0FBD6: "Electronic Engine Controller 21",   # 64470
    0x0FBD7: "Configurable Transmit PGNs Status",   # 64471
    0x0FBD8: "DC/DC Converter 1 Temperatures",   # 64472
    0x0FBD9: "DC/DC Converter 1 Low Side Limits",   # 64473
    0x0FBDA: "DC/DC Converter 1 High Side Limits",   # 64474
    0x0FBDB: "Reserved for Diagnostic Message",   # 64475
    0x0FBDC: "Door Control 4",   # 64476
    0x0FBDD: "Door Control 3",   # 64477
    0x0FBDE: "Engine Temperature 6",   # 64478
    0x0FBDF: "Intake/Exhaust Conditions 3",   # 64479
    0x0FBE0: "Aftercooler and Oil Cooler Fluids 1",   # 64480
    0x0FBE1: "Diode Temperature 2",   # 64481
    0x0FBE2: "Diode Temperature 1",   # 64482
    0x0FBE3: "Alternator Temperature 2",   # 64483
    0x0FBE4: "Fuel Information 7 (Gaseous)",   # 64484
    0x0FBE5: "High Voltage Energy Storage Fan Status",   # 64485
    0x0FBE6: "High Voltage Energy Storage Fan Commands",   # 64486
    0x0FBE7: "SCR Operator Inducement Information 5",   # 64487
    0x0FBE8: "Aftertreatment System Information 2",   # 64488
    0x0FBE9: "Ethernet 1 Connection Information 2",   # 64489
    0x0FBEA: "Ethernet 1 Connection Information 1",   # 64490
    0x0FBEB: "Oil Debris Monitor Counts Ferrous Bins 1 & 2",   # 64491
    0x0FBEC: "Oil Debris Monitor Counts Ferrous Bins 3 & 4",   # 64492
    0x0FBED: "Oil Debris Monitor Counts Ferrous Bins 5 & 6",   # 64493
    0x0FBEE: "Oil Debris Monitor Counts Non-Ferrous Bins 1 & 2",   # 64494
    0x0FBEF: "Oil Debris Monitor Counts Non-Ferrous Bins 3 & 4",   # 64495
    0x0FBF0: "Oil Debris Monitor Counts Non-Ferrous Bins 5 & 6",   # 64496
    0x0FBF1: "Oil Debris Monitoring System Status",   # 64497
    0x0FBF3: "Cruise Control / Vehicle Speed 5",   # 64499
    0x0FBF4: "Aftertreatment 2 Diesel Oxidation Catalyst 2",   # 64500
    0x0FBF5: "Aftertreatment 1 Diesel Oxidation Catalyst 2",   # 64501
    0x0FBF6: "Vehicle Position 2",   # 64502
    0x0FBF7: "Electrified Accessory Propulsion Motor Coolant Fan 3 Status",   # 64503
    0x0FBF8: "Electrified Accessory Propulsion Motor Coolant Fan 2 Status",   # 64504
    0x0FBF9: "Electrified Accessory Propulsion Motor Coolant Fan 1 Status",   # 64505
    0x0FBFA: "Electrified Accessory Power Electronics Coolant Fan 3 Status",   # 64506
    0x0FBFB: "Electrified Accessory Power Electronics Coolant Fan 2 Status",   # 64507
    0x0FBFC: "Electrified Accessory Power Electronics Coolant Fan 1 Status",   # 64508
    0x0FBFD: "Electrified Accessory Propulsion Motor Oil Pump Status",   # 64509
    0x0FBFE: "Electrified Accessory Propulsion Motor Coolant Pump Status",   # 64510
    0x0FBFF: "Electrified Accessory Power Electronics Coolant Pump Status",   # 64511
    0x0FC01: "Electrified Accessory Motor Status",   # 64513
    0x0FC02: "SCR System Information",   # 64514
    0x0FC03: "Vehicle Electrical Power 14",   # 64515
    0x0FC04: "Vehicle Electrical Power 13",   # 64516
    0x0FC05: "Vehicle Electrical Power 12",   # 64517
    0x0FC06: "Vehicle Electrical Power 11",   # 64518
    0x0FC07: "Vehicle Electrical Power 10",   # 64519
    0x0FC08: "Vehicle Electrical Power 9",   # 64520
    0x0FC09: "Vehicle Electrical Power 8",   # 64521
    0x0FC0A: "Vehicle Electrical Power 7",   # 64522
    0x0FC0B: "Electronic Engine Controller 20",   # 64523
    0x0FC0C: "Evaporative Systems",   # 64524
    0x0FC0D: "Fire Pump Statistics 1",   # 64525
    0x0FC0E: "Primary or Rear Hitch Roll and Pitch Sensitivity",   # 64526
    0x0FC0F: "Secondary or Front Hitch Roll and Pitch Sensitivity",   # 64527
    0x0FC10: "Ambient Conditions 3",   # 64528
    0x0FC11: "Total Gaseous Fuel Information",   # 64529
    0x0FC12: "Cab Door Control",   # 64530
    0x0FC13: "Door Latch Status",   # 64531
    0x0FC14: "Vehicle Electrical Power 3 (obsolete, use PGN 65106)",   # 64532
    0x0FC15: "Vehicle Electrical Power 6",   # 64533
    0x0FC16: "Payload Temperature 2",   # 64534
    0x0FC17: "Payload Temperature 1",   # 64535
    0x0FC18: "Payload System Totals 2",   # 64536
    0x0FC19: "Payload System Totals 1",   # 64537
    0x0FC1A: "HVESS Thermal Management System Control 1",   # 64538
    0x0FC1B: "HVESS Thermal Management System Control 2",   # 64539
    0x0FC1C: "Refrigeration Compartment Information 1",   # 64540
    0x0FC1D: "Refrigeration Compartment Information 2",   # 64541
    0x0FC22: "Electronic Engine Controller 19",   # 64546
    0x0FC23: "Fuel Consumption (Liquid) 2",   # 64547
    0x0FC24: "Aftertreatment 2 Diesel Exhaust Fluid Tank 1 Information 2",   # 64548
    0x0FC25: "Aftertreatment 1 Diesel Exhaust Fluid Tank 1 Information 2",   # 64549
    0x0FC26: "Aftertreatment 2 Diesel Exhaust Fluid Information 2",   # 64550
    0x0FC27: "Aftertreatment 1 Diesel Exhaust Fluid Information 2",   # 64551
    0x0FC29: "Forward Lane Image 3",   # 64553
    0x0FC2A: "Operator Inducement Information",   # 64554
    0x0FC2B: "Cruise Control / Vehicle Speed 4",   # 64555
    0x0FC2C: "Brake Caliper Lining Clearance",   # 64556
    0x0FC2D: "Alternate Fuel 5",   # 64557
    0x0FC2E: "Engine Turbocharger Control 3",   # 64558
    0x0FC2F: "Fire Suppression Agent Status",   # 64559
    0x0FC30: "SCR Operator Inducement Information 4",   # 64560
    0x0FC31: "Aftertreatment System Information 1",   # 64561
    0x0FC32: "Aftertreatment 1 Particulate Sensor Information 3",   # 64562
    0x0FC33: "Engine Fuel Injector Metering Rail Pressure Information 3",   # 64563
    0x0FC34: "Engine Fuel Injector Metering Rail Pressure Information 2",   # 64564
    0x0FC35: "Aftertreatment 2 Diesel Exhaust Fluid Pump 1 Information",   # 64565
    0x0FC36: "Gaseous Fuel Supply Valve Information",   # 64566
    0x0FC37: "Engine Oil Mist Detection Information 2",   # 64567
    0x0FC38: "Engine Oil Mist Detection Information 1",   # 64568
    0x0FC39: "Gaseous Fuel Supply Pressure 2",   # 64569
    0x0FC3A: "Gaseous Fuel Supply Pressure 1",   # 64570
    0x0FC3B: "Engine End Bearing Temperature 3",   # 64571
    0x0FC3C: "Engine End Bearing Temperature 2",   # 64572
    0x0FC3D: "Engine End Bearing Temperature 1",   # 64573
    0x0FC3E: "Heat Exchanger Debris Purge Information",   # 64574
    0x0FC3F: "Engine Turbocharger Control 2",   # 64575
    0x0FC40: "Engine Hydraulic Fuel 2 Pump Status",   # 64576
    0x0FC41: "Alternate Fuel 4",   # 64577
    0x0FC42: "Tire Condition Message 2",   # 64578
    0x0FC43: "Tire Configuration Status Information",   # 64579
    0x0FC45: "Tire Wireless Signal Strength Indicator",   # 64581
    0x0FC46: "Tire Sensor Identification Status",   # 64582
    0x0FC47: "Monitored Tire Information",   # 64583
    0x0FC48: "Aftertreatment 2 Historical Information 2",   # 64584
    0x0FC49: "Aftertreatment 1 Historical Information 2",   # 64585
    0x0FC4A: "SCR System Cleaning",   # 64586
    0x0FC4B: "Electronic Engine Controller 17",   # 64587
    0x0FC4C: "SCR Operator Inducement Information 3",   # 64588
    0x0FC4D: "Aftertreatment 2 SCR Dosing System Information 3",   # 64589
    0x0FC4E: "Aftertreatment 1 SCR Dosing System Information 3",   # 64590
    0x0FC4F: "Payload Weight Sensor Information",   # 64591
    0x0FC50: "Payload System Status",   # 64592
    0x0FC51: "Air Suspension Control 7",   # 64593
    0x0FC52: "Bin Weight and Lift Count",   # 64594
    0x0FC53: "Engine Gaseous Leakage Information",   # 64595
    0x0FC54: "Driving and Rest Times Driver 2",   # 64596
    0x0FC55: "Driving and Rest Times Driver 1",   # 64597
    0x0FC56: "SCR Operator Inducement Information 2",   # 64598
    0x0FC57: "SCR Operator Inducement Information 1",   # 64599
    0x0FC58: "Turbocharger Information 7",   # 64600
    0x0FC59: "Engine Load Sharing Information",   # 64601
    0x0FC5D: "High Voltage Energy Storage 1 Configuration",   # 64605
    0x0FC5E: "High Voltage Energy Storage 1 History",   # 64606
    0x0FC69: "EV Operator Indicators 1",   # 64617
    0x0FC85: "Fuel Cell Auxiliary Heater Control",   # 64645
    0x0FC89: "Fuel Cell Coolant Pump 1 Status",   # 64649
    0x0FC8B: "Aftertreatment 1 Particulate Sensor Information 2",   # 64651
    0x0FC8C: "Aftertreatment 1 Particulate Sensor Information 1",   # 64652
    0x0FC8D: "Product Identification Information",   # 64653
    0x0FC8E: "Control Function Functionalities",   # 64654
    0x0FC8F: "Alternate Fuel 3",   # 64655
    0x0FC90: "Engine Fuel Injector Metering Rail Pressure Information 1",   # 64656
    0x0FC91: "Engine Exhaust NOx",   # 64657
    0x0FC92: "Air Fuel Ratio",   # 64658
    0x0FC93: "Gaseous Fuel Pressure 2",   # 64659
    0x0FC94: "Aftertreatment System Abuse Information",   # 64660
    0x0FC95: "Engine Cylinder Pressure Monitor Status Information",   # 64661
    0x0FC96: "Engine Information 2",   # 64662
    0x0FC97: "Electronic Steering Control 2",   # 64663
    0x0FC98: "Vehicle Speed Limiter",   # 64664
    0x0FC99: "Assembly Unit Identification",   # 64665
    0x0FC9A: "Joystick 3 Lamp Status",   # 64666
    0x0FC9B: "Joystick 2 Lamp Status",   # 64667
    0x0FC9C: "Joystick 1 Lamp Status",   # 64668
    0x0FC9D: "Engine Timing Actuator Position Command",   # 64669
    0x0FC9E: "Engine Timing Actuator Position",   # 64670
    0x0FC9F: "Dash Display 2",   # 64671
    0x0FCA0: "Multi-fuel Engine Hours",   # 64672
    0x0FCA1: "Engine Spark Misfire Rate 3",   # 64673
    0x0FCA2: "Engine Spark Misfire Rate 2",   # 64674
    0x0FCA3: "Engine Spark Misfire Rate 1",   # 64675
    0x0FCA4: "Engine Spark Maximum Voltage 6",   # 64676
    0x0FCA5: "Engine Spark Maximum Voltage 5",   # 64677
    0x0FCA6: "Engine Spark Maximum Voltage 4",   # 64678
    0x0FCA7: "Engine Spark Maximum Voltage 3",   # 64679
    0x0FCA8: "Engine Spark Maximum Voltage 2",   # 64680
    0x0FCA9: "Engine Spark Maximum Voltage 1",   # 64681
    0x0FCAA: "Engine Spark Minimum Voltage 6",   # 64682
    0x0FCAB: "Engine Spark Minimum Voltage 5",   # 64683
    0x0FCAC: "Engine Spark Minimum Voltage 4",   # 64684
    0x0FCAD: "Engine Spark Minimum Voltage 3",   # 64685
    0x0FCAE: "Engine Spark Minimum Voltage 2",   # 64686
    0x0FCAF: "Engine Spark Minimum Voltage 1",   # 64687
    0x0FCB0: "Engine Ignition Controller Maintenance Hours",   # 64688
    0x0FCB1: "Engine Ignition Control Module Status",   # 64689
    0x0FCB2: "Switched Power Output Current",   # 64690
    0x0FCB3: "Fused Power Output Current",   # 64691
    0x0FCB4: "Switched Power Output Status",   # 64692
    0x0FCB5: "Fused Power Output Status",   # 64693
    0x0FCB6: "Vehicle Electrical Power 5",   # 64694
    0x0FCB7: "Hybrid System Status 2",   # 64695
    0x0FCB8: "Aftertreatment 2 Service 2",   # 64696
    0x0FCB9: "Aftertreatment 1 Service 2",   # 64697
    0x0FCBA: "Aftertreatment 2 SCR Electronic Control Module Information",   # 64698
    0x0FCBB: "Aftertreatment 1 SCR Electronic Control Module Information",   # 64699
    0x0FCBC: "Aftertreatment 2 SCR Service Information 2",   # 64700
    0x0FCBD: "Aftertreatment 1 SCR Service Information 2",   # 64701
    0x0FCBE: "Electronic Transmission Controller #9",   # 64702
    0x0FCBF: "Electronic Transmission Controller #10",   # 64703
    0x0FCC0: "Electronic Transmission Controller #11",   # 64704
    0x0FCC1: "Transmission Fluids 3",   # 64705
    0x0FCC2: "Hybrid System Status 1",   # 64706
    0x0FCC3: "Fuel Information 4 (Gaseous)",   # 64707
    0x0FCC4: "Aftertreatment 2 SCR Exhaust Gas Temperature 2",   # 64708
    0x0FCC5: "Aftertreatment 1 SCR Exhaust Gas Temperature 2",   # 64709
    0x0FCC6: "OBD Information",   # 64710
    0x0FCC7: "Model Year and Certification Engine Family",   # 64711
    0x0FCC8: "Electronic Engine Controller 13",   # 64712
    0x0FCC9: "Engine Fuel/Throttle Valve Information 2",   # 64713
    0x0FCCA: "Engine Exhaust Gas Recirculation 2 Actuator",   # 64714
    0x0FCCB: "Engine Exhaust Gas Recirculation 1 Actuator",   # 64715
    0x0FCCC: "Electronic Engine Controller 12",   # 64716
    0x0FCCD: "Drive Strategy Status",   # 64717
    0x0FCCE: "Drive Strategy command",   # 64718
    0x0FCCF: "NOx Sensor Self-Diagnosis Request",   # 64719
    0x0FCD0: "Engine Particulate Sensor Information",   # 64720
    0x0FCD1: "Active Service Only DTCs",   # 64721
    0x0FCD2: "Previously Active Service Only DTCs",   # 64722
    0x0FCD3: "Diagnostic Data Clear/Reset for All Service Only DTCs",   # 64723
    0x0FCD4: "XCP Get Slave ID",   # 64724
    0x0FCD5: "Aftertreatment 1 Diesel Exhaust Fluid Pump 1 Information",   # 64725
    0x0FCD6: "Aftertreatment 1 Diesel Particulate Filter 2 Soot 5",   # 64726
    0x0FCD7: "Aftertreatment 1 Diesel Particulate Filter 2 Soot 4",   # 64727
    0x0FCD8: "Aftertreatment 1 Diesel Particulate Filter 2 Soot 3",   # 64728
    0x0FCD9: "Aftertreatment 1 Diesel Particulate Filter 1 Soot 5",   # 64729
    0x0FCDA: "Aftertreatment 1 Diesel Particulate Filter 1 Soot 4",   # 64730
    0x0FCDB: "Aftertreatment 1 Diesel Particulate Filter 1 Soot 3",   # 64731
    0x0FCDC: "Cruise Control / Vehicle Speed 3",   # 64732
    0x0FCDD: "Aftertreatment 2 Air Control 3",   # 64733
    0x0FCDE: "Aftertreatment 1 Air Control 3",   # 64734
    0x0FCDF: "Engine Fluid Level/Pressure 12",   # 64735
    0x0FCE0: "Diesel Particulate Filter Control 2",   # 64736
    0x0FCE1: "Fuel Economy 2 (Liquid)",   # 64737
    0x0FCE2: "Supplemental Fan Status",   # 64738
    0x0FCE3: "Engine Exhaust Brake Control",   # 64739
    0x0FCE4: "Engine Fuel Properties",   # 64740
    0x0FCE5: "Hydraulic Oil Properties",   # 64741
    0x0FCE6: "Vehicle/Chassis Lubrication System 2",   # 64742
    0x0FCE7: "Engine Configuration 3",   # 64743
    0x0FCE8: "Intake Valve Actuation Control",   # 64744
    0x0FCE9: "Armrest Switch Matrix Commands",   # 64745
    0x0FCEA: "Vehicle Electrical Power 4 (obsolete, use PGN 64695)",   # 64746
    0x0FCEB: "Aftertreatment 2 NOx Adsorber Information",   # 64747
    0x0FCEC: "Aftertreatment 1 NOx Adsorber Information",   # 64748
    0x0FCED: "Aftertreatment 2 Warm Up Diesel Oxidation Catalyst Information",   # 64749
    0x0FCEE: "Land Leveling System Reference Elevation Data",   # 64750
    0x0FCEF: "Engine Fluid Level/Pressure 11",   # 64751
    0x0FCF0: "Engine Fuel/Lube Systems 2",   # 64752
    0x0FCF1: "Engine Turbocharger Wastegate Actuator and Exhaust Back Pressure Regulator Information",   # 64753
    0x0FCF2: "Engine Fuel/Throttle Valve Information 1",   # 64754
    0x0FCF3: "Engine Turbocharger Compressor Bypass Information",   # 64755
    0x0FCF4: "Charge Air Cooler 2",   # 64756
    0x0FCF5: "Charge Air Cooler 2 Precooler",   # 64757
    0x0FCF6: "Charge Air Cooler 1",   # 64758
    0x0FCF7: "Charge Air Cooler 1 Precooler",   # 64759
    0x0FCF8: "Diesel Particulate Filter 2 Soot 2",   # 64760
    0x0FCF9: "Diesel Particulate Filter 1 Soot 2",   # 64761
    0x0FCFA: "Electronic Engine Controller 11",   # 64762
    0x0FCFB: "Engine Manifold Actuator Position",   # 64763
    0x0FCFC: "Engine Manifold Actuator Control",   # 64764
    0x0FCFD: "Electronic Engine Controller 9",   # 64765
    0x0FCFE: "Electronic Engine Controller 10",   # 64766
    0x0FCFF: "Engine Temperature 5",   # 64767
    0x0FD00: "Engine Fluid Level/Pressure 10",   # 64768
    0x0FD01: "Low Voltage Disconnect Status",   # 64769
    0x0FD02: "All implements stop operations switch state",   # 64770
    0x0FD03: "Implement Operating state command",   # 64771
    0x0FD04: "Direct Lamp Control Data 2",   # 64772
    0x0FD05: "Direct Lamp Control Data 1",   # 64773
    0x0FD06: "Direct Lamp Control Command 2",   # 64774
    0x0FD07: "Direct Lamp Control Command 1",   # 64775
    0x0FD08: "Engine oil message",   # 64776
    0x0FD09: "High Resolution Fuel Consumption (Liquid)",   # 64777
    0x0FD0A: "Aftertreatment 2 Outlet Gas NOx Sensor Correction Data 2",   # 64778
    0x0FD0B: "Aftertreatment 2 Outlet Gas NOx Sensor Correction Data 1",   # 64779
    0x0FD0C: "Aftertreatment 2 Intake Gas NOx Sensor Correction Data 2",   # 64780
    0x0FD0D: "Aftertreatment 2 Intake Gas NOx Sensor Correction Data 1",   # 64781
    0x0FD0E: "Aftertreatment 1 Outlet Gas NOx Sensor Correction Data 2",   # 64782
    0x0FD0F: "Aftertreatment 1 Outlet Gas NOx Sensor Correction Data 1",   # 64783
    0x0FD10: "Aftertreatment 1 Intake Gas NOx Sensor Correction Data 2",   # 64784
    0x0FD11: "Aftertreatment 1 Intake Gas NOx Sensor Correction Data 1",   # 64785
    0x0FD12: "Magnet Status Information 1",   # 64786
    0x0FD13: "Magnet System Configuration Information",   # 64787
    0x0FD14: "Battery Charger 2",   # 64788
    0x0FD15: "Battery Charger 1",   # 64789
    0x0FD16: "Occupant Classification System Information",   # 64790
    0x0FD17: "Beltlock and Airbag Deactivation Switch Information",   # 64791
    0x0FD18: "Collision Sensor Information",   # 64792
    0x0FD19: "Ignitor Loop Information",   # 64793
    0x0FD1A: "Aftertreatment 1 Warm Up Diesel Oxidation Catalyst Information",   # 64794
    0x0FD1B: "Diesel Particulate Filter 2 Soot",   # 64795
    0x0FD1C: "Diesel Particulate Filter 1 Soot",   # 64796
    0x0FD1D: "Aftertreatment Differential Temperature 2",   # 64797
    0x0FD1E: "Aftertreatment Differential Temperature 1",   # 64798
    0x0FD1F: "Aftertreatment 2 Diesel Oxidation Catalyst 1",   # 64799
    0x0FD20: "Aftertreatment 1 Diesel Oxidation Catalyst 1",   # 64800
    0x0FD21: "Aftertreatment 2 Gas Oxidation Catalyst",   # 64801
    0x0FD22: "Aftertreatment 1 Gas Oxidation Catalyst",   # 64802
    0x0FD23: "Extended Joystick Message 10",   # 64803
    0x0FD24: "Basic Joystick Message 10",   # 64804
    0x0FD25: "Extended Joystick Message 9",   # 64805
    0x0FD26: "Basic Joystick Message 9",   # 64806
    0x0FD27: "Extended Joystick Message 8",   # 64807
    0x0FD28: "Basic Joystick Message 8",   # 64808
    0x0FD29: "Extended Joystick Message 7",   # 64809
    0x0FD2A: "Basic Joystick Message 7",   # 64810
    0x0FD2B: "Extended Joystick Message 6",   # 64811
    0x0FD2C: "Basic Joystick Message 6",   # 64812
    0x0FD2D: "Extended Joystick Message 5",   # 64813
    0x0FD2E: "Basic Joystick Message 5",   # 64814
    0x0FD2F: "Extended Joystick Message 4",   # 64815
    0x0FD30: "Basic Joystick Message 4",   # 64816
    0x0FD31: "Fan Drive #2",   # 64817
    0x0FD32: "ECU diagnostic protocol",   # 64818
    0x0FD33: "Aftertreatment 2 Diesel Exhaust Fluid Supply Information",   # 64819
    0x0FD34: "Aftertreatment 2 SCR Reagant Tank 2 Information",   # 64820
    0x0FD35: "Aftertreatment 2 Diesel Exhaust Fluid Tank 1 Information 1",   # 64821
    0x0FD36: "Aftertreatment 2 Diesel Exhaust Fluid Information 1",   # 64822
    0x0FD37: "Aftertreatment 2 SCR Service Information 1",   # 64823
    0x0FD38: "Aftertreatment 2 SCR Exhaust Gas Temperature 1",   # 64824
    0x0FD39: "Aftertreatment 2 SCR Exhaust Gas Pressures",   # 64825
    0x0FD3A: "Aftertreatment 2 SCR Dosing System Requests 2",   # 64826
    0x0FD3B: "Aftertreatment 2 SCR Dosing System Information 2",   # 64827
    0x0FD3C: "Aftertreatment 1 Diesel Exhaust Fluid Supply Information",   # 64828
    0x0FD3D: "Aftertreatment 1 SCR Reagant Tank 2 Information",   # 64829
    0x0FD3E: "Aftertreatment 1 SCR Exhaust Gas Temperature 1",   # 64830
    0x0FD3F: "Aftertreatment 1 SCR Exhaust Gas Pressures",   # 64831
    0x0FD40: "Aftertreatment 1 SCR Dosing System Requests 2",   # 64832
    0x0FD41: "Aftertreatment 1 SCR Dosing System Information 2",   # 64833
    0x0FD42: "ISOBUS compliance certification",   # 64834
    0x0FD43: "Machine Selected Speed command",   # 64835
    0x0FD44: "Aftertreatment 2 Fuel Control 2",   # 64836
    0x0FD45: "Aftertreatment 2 Three Way Catalyst",   # 64837
    0x0FD46: "Aftertreatment 1 Three Way Catalyst",   # 64838
    0x0FD47: "Transmission Mode Labels",   # 64839
    0x0FD48: "Engine Exhaust Bank 2 O2 Fuel Trim",   # 64840
    0x0FD49: "Engine Exhaust Bank 1 O2 Fuel Trim",   # 64841
    0x0FD4A: "General Purpose Message #2/11",   # 64842
    0x0FD4B: "General Purpose Message #2/10",   # 64843
    0x0FD4C: "General Purpose Message #2/9",   # 64844
    0x0FD4D: "General Purpose Message #2/8",   # 64845
    0x0FD4E: "General Purpose Message #2/7",   # 64846
    0x0FD4F: "General Purpose Message #2/6",   # 64847
    0x0FD50: "General Purpose Message #1/9",   # 64848
    0x0FD51: "Aftercooler Coolant Control Valve Command",   # 64849
    0x0FD52: "Engine Coolant Control Valve Command",   # 64850
    0x0FD53: "Engine Average Information",   # 64851
    0x0FD54: "DTCs - C, Previously Active",   # 64852
    0x0FD55: "DTCs - C, Confirmed and Active",   # 64853
    0x0FD56: "DTCs - C, Pending",   # 64854
    0x0FD57: "DTCs - B2, Previously Active",   # 64855
    0x0FD58: "DTCs - B2, Confirmed and Active",   # 64856
    0x0FD59: "DTCs - B2, Pending",   # 64857
    0x0FD5A: "DTCs - B1, Previously Active",   # 64858
    0x0FD5B: "DTCs - B1, Confirmed and Active",   # 64859
    0x0FD5C: "DTCs - B1, Pending",   # 64860
    0x0FD5D: "DTCs - A, Previously Active",   # 64861
    0x0FD5E: "DTCs - A, Confirmed and Active",   # 64862
    0x0FD5F: "DTCs - A, Pending",   # 64863
    0x0FD60: "Harmonized B1 Failure Counts",   # 64864
    0x0FD61: "Harmonized Cumulative Continuous Malfunction Indicator – System",   # 64865
    0x0FD62: "Harmonized Global Regulation Description",   # 64866
    0x0FD63: "Harmonized Roadworthiness – System",   # 64867
    0x0FD64: "Harmonized Roadworthiness - Vehicle",   # 64868
    0x0FD65: "Aftertreatment 1 Fuel Control 2",   # 64869
    0x0FD66: "Engine Temperature 4",   # 64870
    0x0FD67: "Zero Net Vehicle Weight Change",   # 64871
    0x0FD68: "Gross Combination Vehicle Weight",   # 64872
    0x0FD69: "Axle Group Calibration Weights",   # 64873
    0x0FD6A: "Axle Group Weight",   # 64874
    0x0FD6B: "Available Axle Group Weights",   # 64875
    0x0FD6C: "Aftertreatment 2 Air Control 2",   # 64876
    0x0FD6D: "Aftertreatment 1 Air Control 2",   # 64877
    0x0FD6E: "Aftertreatment 1 SCR Service Information 1",   # 64878
    0x0FD6F: "Electronic Engine Controller 8",   # 64879
    0x0FD70: "Door ramp control",   # 64880
    0x0FD71: "Brake actuator stroke status",   # 64881
    0x0FD72: "Engine Spark Voltage 6",   # 64882
    0x0FD73: "Engine Spark Voltage 5",   # 64883
    0x0FD74: "Engine Spark Voltage 4",   # 64884
    0x0FD75: "Engine Spark Voltage 3",   # 64885
    0x0FD76: "Engine Spark Voltage 2",   # 64886
    0x0FD77: "Engine Spark Voltage 1",   # 64887
    0x0FD78: "Aftertreatment 2 Trip Information",   # 64888
    0x0FD79: "Aftertreatment 1 Trip Information",   # 64889
    0x0FD7A: "Aftertreatment 2 Service 1",   # 64890
    0x0FD7B: "Aftertreatment 1 Service 1",   # 64891
    0x0FD7C: "Diesel Particulate Filter Control 1",   # 64892
    0x0FD7D: "Reserved for FMS Telltale status",   # 64893
    0x0FD7E: "Adaptive Front-Lighting System Status",   # 64894
    0x0FD7F: "Engine Configuration 2",   # 64895
    0x0FD80: "Emission-Related Permanent Diagnostic Trouble Codes",   # 64896
    0x0FD81: "EGR Cooler Bypass",   # 64897
    0x0FD82: "All Pending DTCs",   # 64898
    0x0FD83: "Transfer Case Information",   # 64899
    0x0FD84: "Engine Fluid Level/Pressure 9",   # 64900
    0x0FD85: "Engine Fluid Level/Pressure 8",   # 64901
    0x0FD86: "Engine Fluid Level/Pressure 7",   # 64902
    0x0FD87: "Engine Fluid Level/Pressure 6",   # 64903
    0x0FD88: "Engine Fluid Level/Pressure 5",   # 64904
    0x0FD89: "Vehicle Direction/Speed 2",   # 64905
    0x0FD8A: "SAE J2012 DTC Display",   # 64906
    0x0FD8B: "Aftertreatment 2 Gas Parameters",   # 64907
    0x0FD8C: "Aftertreatment 1 Gas Parameters",   # 64908
    0x0FD8D: "Utility Total AC Reactive Energy",   # 64909
    0x0FD8E: "Generator Total AC Reactive Energy",   # 64910
    0x0FD8F: "Generator Total AC Percent Power",   # 64911
    0x0FD90: "Advertised Engine Torque Curve",   # 64912
    0x0FD91: "AC Switching Device Status",   # 64913
    0x0FD92: "Engine Operating Information",   # 64914
    0x0FD93: "Generator Control 1",   # 64915
    0x0FD94: "Electronic Engine Controller 7",   # 64916
    0x0FD95: "Transmission Fluids 2",   # 64917
    0x0FD96: "Fuel Information 2 (Liquid)",   # 64918
    0x0FD97: "Fuel Information 3 (Liquid)",   # 64919
    0x0FD98: "Aftertreatment 1 Historical Information 1",   # 64920
    0x0FD99: "Aftertreatment 2 Historical information 1",   # 64921
    0x0FD9A: "Electronic Brake System #2/4",   # 64922
    0x0FD9B: "Aftertreatment 1 Diesel Exhaust Fluid Information 1",   # 64923
    0x0FD9C: "Sensor Electrical Power #2",   # 64924
    0x0FD9D: "Sensor Electrical Power #1",   # 64925
    0x0FD9E: "Aftertreatment 2 Air Control 1",   # 64926
    0x0FD9F: "Aftertreatment 1 Air Control 1",   # 64927
    0x0FDA0: "Aftertreatment 2 Fuel Control 1",   # 64928
    0x0FDA1: "Aftertreatment 1 Fuel Control 1",   # 64929
    0x0FDA2: "Fuel Information 3 (Gaseous)",   # 64930
    0x0FDA3: "Electronic Engine Controller 6",   # 64931
    0x0FDA4: "PTO Drive Engagement",   # 64932
    0x0FDA5: "Door Control 2",   # 64933
    0x0FDA6: "Voltage Regulator Excitation Status",   # 64934
    0x0FDA7: "Voltage Regulator Operating Mode",   # 64935
    0x0FDA8: "Wireless Communications Message 2",   # 64936
    0x0FDA9: "Wireless Communications Message 1",   # 64937
    0x0FDAA: "Engine Fluid Level/Pressure 4",   # 64938
    0x0FDAB: "Request For Complete Configurable Message Set (no longer used)",   # 64939
    0x0FDAC: "Engine Fuel Information",   # 64940
    0x0FDAD: "Request For Complete Configurable Message Set",   # 64941
    0x0FDAE: "Fifth Wheel Smart Systems 2",   # 64942
    0x0FDAF: "Aftertreatment 2 Intermediate Gas",   # 64943
    0x0FDB0: "Aftertreatment 2 Outlet Gas 2",   # 64944
    0x0FDB1: "Aftertreatment 2 Intake Gas 2",   # 64945
    0x0FDB2: "Aftertreatment 1 Intermediate Gas",   # 64946
    0x0FDB3: "Aftertreatment 1 Outlet Gas 2",   # 64947
    0x0FDB4: "Aftertreatment 1 Intake Gas 2",   # 64948
    0x0FDB5: "Emission-Related Previously MIL-On Diagnostic Trouble Codes",   # 64949
    0x0FDB6: "SPN Support",   # 64950
    0x0FDB7: "Expanded Freeze Frame",   # 64951
    0x0FDB8: "Diagnostic Readiness 3",   # 64952
    0x0FDB9: "Tire Pressure Reference Information",   # 64953
    0x0FDBA: "Farebox Status",   # 64954
    0x0FDBB: "Farebox Point of Sale",   # 64955
    0x0FDBC: "Farebox Service Detail",   # 64956
    0x0FDBD: "Signal Preemption",   # 64957
    0x0FDBE: "Transit Route",   # 64958
    0x0FDBF: "Transit Milepost",   # 64959
    0x0FDC0: "Passenger Counter",   # 64960
    0x0FDC1: "Engine Fluid Level/Pressure 3",   # 64961
    0x0FDC2: "Electronic Engine Controller 14",   # 64962
    0x0FDC3: "Electronic Engine Controller 15",   # 64963
    0x0FDC4: "Electronic Brake Controller 5",   # 64964
    0x0FDC5: "ECU Identification Information",   # 64965
    0x0FDC6: "Cold Start Aids",   # 64966
    0x0FDC7: "Off-Highway Engine Control Selection States",   # 64967
    0x0FDC8: "Operator Primary Intermediate Speed Control state",   # 64968
    0x0FDC9: "Electronic Control Module Information",   # 64969
    0x0FDCA: "Intermediate Speed Control",   # 64970
    0x0FDCB: "Off-Highway Engine Control Selection",   # 64971
    0x0FDCC: "Operators External Light Controls Message",   # 64972
    0x0FDCD: "Operator Wiper and Washer Controls Message",   # 64973
    0x0FDCE: "Working Set Member Message (Obsolete - See PGN 65088)",   # 64974
    0x0FDCF: "Working Set Master Message (Obsolete - See PGN 65089)",   # 64975
    0x0FDD0: "Intake/Exhaust Conditions 2",   # 64976
    0x0FDD1: "FMS-standard Interface Identity/Capabilities",   # 64977
    0x0FDD2: "ECU Performance",   # 64978
    0x0FDD3: "Turbocharger Information 6",   # 64979
    0x0FDD4: "Cab Message 3",   # 64980
    0x0FDD5: "Electronic Engine Controller 5",   # 64981
    0x0FDD6: "Basic Joystick Message 1",   # 64982
    0x0FDD7: "Extended Joystick Message 1",   # 64983
    0x0FDD8: "Basic Joystick Message 2",   # 64984
    0x0FDD9: "Extended Joystick Message 2",   # 64985
    0x0FDDA: "Basic Joystick Message 3",   # 64986
    0x0FDDB: "Extended Joystick Message 3",   # 64987
    0x0FDDC: "Marine Control Information",   # 64988
    0x0FDDD: "Military Application Message #1/1",   # 64989
    0x0FDDE: "Military Application Message #2/1",   # 64990
    0x0FDDF: "Front Wheel Drive Status",   # 64991
    0x0FDE0: "Ambient Conditions 2",   # 64992
    0x0FDE1: "Cab A/C Climate System Information",   # 64993
    0x0FDE2: "Supply Pressure Demand",   # 64994
    0x0FDE3: "Equipment Operation and Control",   # 64995
    0x0FDE4: "Equipment Performance Data",   # 64996
    0x0FDE5: "Maximum Vehicle Speed Limit Status",   # 64997
    0x0FDE6: "Hydraulic Braking System",   # 64998
    0x0FDE7: "Bus #1/Utility Sync Check Status",   # 64999
    0x0FDE8: "Bus #1/Generator Sync Check Status",   # 65000
    0x0FDE9: "Bus #1 Phase C Basic AC Quantities",   # 65001
    0x0FDEA: "Bus #1 Phase B Basic AC Quantities",   # 65002
    0x0FDEB: "Bus #1 Phase A Basic AC Quantities",   # 65003
    0x0FDEC: "Bus #1 Average Basic AC Quantities",   # 65004
    0x0FDED: "Utility Total AC Energy",   # 65005
    0x0FDEE: "Utility Phase C AC Reactive Power",   # 65006
    0x0FDEF: "Utility Phase C AC Power",   # 65007
    0x0FDF0: "Utility Phase C AC Basic Quantities",   # 65008
    0x0FDF1: "Utility Phase B AC Reactive Power",   # 65009
    0x0FDF2: "Utility Phase B AC Power",   # 65010
    0x0FDF3: "Utility Phase B AC Basic Quantities",   # 65011
    0x0FDF4: "Utility Phase A AC Reactive Power",   # 65012
    0x0FDF5: "Utility Phase A AC Power",   # 65013
    0x0FDF6: "Utility Phase A Basic AC Quantities",   # 65014
    0x0FDF7: "Utility Total AC Reactive Power",   # 65015
    0x0FDF8: "Utility Total AC Power",   # 65016
    0x0FDF9: "Utility Average Basic AC Quantities",   # 65017
    0x0FDFA: "Generator Total AC Energy",   # 65018
    0x0FDFB: "Generator Phase C AC Reactive Power",   # 65019
    0x0FDFC: "Generator Phase C AC Power",   # 65020
    0x0FDFD: "Generator Phase C Basic AC Quantities",   # 65021
    0x0FDFE: "Generator Phase B AC Reactive Power",   # 65022
    0x0FDFF: "Generator Phase B AC Power",   # 65023
    0x0FE00: "Generator Phase B Basic AC Quantities",   # 65024
    0x0FE01: "Generator Phase A AC Reactive Power",   # 65025
    0x0FE02: "Generator Phase A AC Power",   # 65026
    0x0FE03: "Generator Phase A Basic AC Quantities",   # 65027
    0x0FE04: "Generator Total AC Reactive Power",   # 65028
    0x0FE05: "Generator Total AC Power",   # 65029
    0x0FE06: "Generator Average Basic AC Quantities",   # 65030
    0x0FE07: "Exhaust Temperature",   # 65031
    0x0FE08: "Required Tractor Facilities message",   # 65032
    0x0FE09: "Tractor Facilities response message",   # 65033
    0x0FE0A: "Implement Remote Control Command Tractor Response",   # 65034
    0x0FE0B: "Tractor control mode command",   # 65035
    0x0FE0C: "Working Set Member",   # 65036
    0x0FE0D: "Working Set Master",   # 65037
    0x0FE0E: "Response for Repetition Rate",   # 65038
    0x0FE0F: "Language command",   # 65039
    0x0FE10: "Auxiliary valve 0 estimated flow",   # 65040
    0x0FE11: "Auxiliary valve 1 estimated flow",   # 65041
    0x0FE12: "Auxiliary valve 2 estimated flow",   # 65042
    0x0FE13: "Auxiliary valve 3 estimated flow",   # 65043
    0x0FE14: "Auxiliary valve 4 estimated flow",   # 65044
    0x0FE15: "Auxiliary valve 5 estimated flow",   # 65045
    0x0FE16: "Auxiliary valve 6 estimated flow",   # 65046
    0x0FE17: "Auxiliary valve 7 estimated flow",   # 65047
    0x0FE18: "Auxiliary valve 8 estimated flow",   # 65048
    0x0FE19: "Auxiliary valve 9 estimated flow",   # 65049
    0x0FE1A: "Auxiliary valve 10 estimated flow",   # 65050
    0x0FE1B: "Auxiliary valve 11 estimated flow",   # 65051
    0x0FE1C: "Auxiliary valve 12 estimated flow",   # 65052
    0x0FE1D: "Auxiliary valve 13 estimated flow",   # 65053
    0x0FE1E: "Auxiliary valve 14 estimated flow",   # 65054
    0x0FE1F: "Auxiliary valve 15 estimated flow",   # 65055
    0x0FE20: "Auxiliary valve 0 measured flow",   # 65056
    0x0FE21: "Auxiliary valve 1 measured flow",   # 65057
    0x0FE22: "Auxiliary valve 2 measured flow",   # 65058
    0x0FE23: "Auxiliary valve 3 measured flow",   # 65059
    0x0FE24: "Auxiliary valve 4 measured flow",   # 65060
    0x0FE25: "Auxiliary valve 5 measured flow",   # 65061
    0x0FE26: "Auxiliary valve 6 measured flow",   # 65062
    0x0FE27: "Auxiliary valve 7 measured flow",   # 65063
    0x0FE28: "Auxiliary valve 8 measured flow",   # 65064
    0x0FE29: "Auxiliary valve 9 measured flow",   # 65065
    0x0FE2A: "Auxiliary valve 10 measured flow",   # 65066
    0x0FE2B: "Auxiliary valve 11 measured flow",   # 65067
    0x0FE2C: "Auxiliary valve 12 measured flow",   # 65068
    0x0FE2D: "Auxiliary valve 13 measured flow",   # 65069
    0x0FE2E: "Auxiliary valve 14 measured flow",   # 65070
    0x0FE2F: "Auxiliary valve 15 measured flow",   # 65071
    0x0FE30: "Auxiliary valve 0 command",   # 65072
    0x0FE31: "Auxiliary valve 1 command",   # 65073
    0x0FE32: "Auxiliary valve 2 command",   # 65074
    0x0FE33: "Auxiliary valve 3 command",   # 65075
    0x0FE34: "Auxiliary valve 4 command",   # 65076
    0x0FE35: "Auxiliary valve 5 command",   # 65077
    0x0FE36: "Auxiliary valve 6 command",   # 65078
    0x0FE37: "Auxiliary valve 7 command",   # 65079
    0x0FE38: "Auxiliary valve 8 command",   # 65080
    0x0FE39: "Auxiliary valve 9 command",   # 65081
    0x0FE3A: "Auxiliary valve 10 command",   # 65082
    0x0FE3B: "Auxiliary valve 11 command",   # 65083
    0x0FE3C: "Auxiliary valve 12 command",   # 65084
    0x0FE3D: "Auxiliary valve 13 command",   # 65085
    0x0FE3E: "Auxiliary valve 14 command",   # 65086
    0x0FE3F: "Auxiliary valve 15 command",   # 65087
    0x0FE40: "Lighting Data",   # 65088
    0x0FE41: "Lighting command",   # 65089
    0x0FE42: "Hitch and PTO commands",   # 65090
    0x0FE43: "Primary or Rear Power Take off Output Shaft",   # 65091
    0x0FE44: "Secondary or Front Power Take off Output Shaft",   # 65092
    0x0FE45: "Primary or Rear Hitch Status",   # 65093
    0x0FE46: "Secondary or Front Hitch Status",   # 65094
    0x0FE47: "Maintain Power",   # 65095
    0x0FE48: "Wheel-based Speed and Distance",   # 65096
    0x0FE49: "Ground-based Speed and Distance",   # 65097
    0x0FE4A: "Electronic Transmission Controller 7",   # 65098
    0x0FE4B: "Transmission Configuration 2",   # 65099
    0x0FE4C: "Military Lighting Command",   # 65100
    0x0FE4D: "Total Averaged Information",   # 65101
    0x0FE4E: "Door Control 1",   # 65102
    0x0FE4F: "Vehicle Dynamic Stability Control 1",   # 65103
    0x0FE50: "Battery Temperature",   # 65104
    0x0FE51: "Adaptive Cruise Control, Operator Input",   # 65105
    0x0FE52: "Vehicle Electrical Power 3",   # 65106
    0x0FE53: "Retarder Continuous Torque & Speed Limit",   # 65107
    0x0FE54: "Engine Continuous Torque & Speed Limit",   # 65108
    0x0FE55: "Gaseous Fuel Properties",   # 65109
    0x0FE56: "Aftertreatment 1 Diesel Exhaust Fluid Tank 1 Information 1",   # 65110
    0x0FE57: "Air Suspension Control 5",   # 65111
    0x0FE58: "Air Suspension Control 4",   # 65112
    0x0FE59: "Air Suspension Control 3",   # 65113
    0x0FE5A: "Air Suspension Control 1",   # 65114
    0x0FE5B: "Forward Lane Image 2",   # 65115
    0x0FE5C: "Running Gear Equipment #2/2",   # 65116
    0x0FE5D: "General Purpose Message #1/2",   # 65117
    0x0FE5E: "Running Gear Equipment #2/3",   # 65118
    0x0FE5F: "General Purpose Message #1/3",   # 65119
    0x0FE60: "General Purpose Message #2/3",   # 65120
    0x0FE61: "General Purpose Message #1/4",   # 65121
    0x0FE62: "General Purpose Message #2/4",   # 65122
    0x0FE63: "General Purpose Message #1/5",   # 65123
    0x0FE64: "General Purpose Message #2/5",   # 65124
    0x0FE65: "General Purpose Message #1/6",   # 65125
    0x0FE66: "Battery Main Switch Information",   # 65126
    0x0FE67: "Climate Control Configuration",   # 65127
    0x0FE68: "Vehicle Fluids",   # 65128
    0x0FE69: "Engine Temperature 3",   # 65129
    0x0FE6A: "Engine Fuel/Lube Systems",   # 65130
    0x0FE6B: "Driver's Identification",   # 65131
    0x0FE6C: "Tachograph",   # 65132
    0x0FE6D: "Heater Information",   # 65133
    0x0FE6E: "High Resolution Wheel Speed",   # 65134
    0x0FE6F: "Adaptive Cruise Control 1",   # 65135
    0x0FE70: "Combination Vehicle Weight",   # 65136
    0x0FE71: "Laser Tracer Position",   # 65137
    0x0FE72: "Laser Leveling System Blade Control",   # 65138
    0x0FE73: "Laser Receiver Mast Position",   # 65139
    0x0FE74: "Modify Leveling System Control Set Point",   # 65140
    0x0FE75: "Laser Leveling System Vertical Deviation",   # 65141
    0x0FE76: "Laser Leveling System Vertical Position Display Data",   # 65142
    0x0FE77: "Auxiliary Pressures",   # 65143
    0x0FE78: "Tire Pressure Control Unit Mode and Status",   # 65144
    0x0FE79: "Tire Pressure Control Unit Target Pressures",   # 65145
    0x0FE7A: "Tire Pressure Control Unit Current Pressures",   # 65146
    0x0FE7B: "Combustion Time 1",   # 65147
    0x0FE7C: "Combustion Time 2",   # 65148
    0x0FE7D: "Combustion Time 3",   # 65149
    0x0FE7E: "Combustion Time 4",   # 65150
    0x0FE7F: "Combustion Time 5",   # 65151
    0x0FE80: "Combustion Time 6",   # 65152
    0x0FE81: "Fuel Information 2 (Gaseous)",   # 65153
    0x0FE82: "Ignition Timing 1",   # 65154
    0x0FE83: "Ignition Timing 2",   # 65155
    0x0FE84: "Ignition Timing 3",   # 65156
    0x0FE85: "Ignition Timing 4",   # 65157
    0x0FE86: "Ignition Timing 5",   # 65158
    0x0FE87: "Ignition Timing 6",   # 65159
    0x0FE88: "Ignition Transformer Secondary Output 1",   # 65160
    0x0FE89: "Ignition Transformer Secondary Output 2",   # 65161
    0x0FE8A: "Ignition Transformer Secondary Output 3",   # 65162
    0x0FE8B: "Gaseous Fuel Pressure 1",   # 65163
    0x0FE8C: "Auxiliary Analog Information",   # 65164
    0x0FE8D: "Vehicle Electrical Power 2",   # 65165
    0x0FE8E: "Service 2",   # 65166
    0x0FE8F: "Supply Pressure 2",   # 65167
    0x0FE90: "Engine Torque History",   # 65168
    0x0FE91: "Fuel Leakage",   # 65169
    0x0FE92: "Engine Information 1",   # 65170
    0x0FE93: "Engine Electrical System/Module Information",   # 65171
    0x0FE94: "Engine Auxiliary Coolant",   # 65172
    0x0FE95: "Rebuild Information",   # 65173
    0x0FE96: "Turbocharger Wastegate",   # 65174
    0x0FE97: "Turbocharger Information 5",   # 65175
    0x0FE98: "Turbocharger Information 4",   # 65176
    0x0FE99: "Turbocharger Information 3",   # 65177
    0x0FE9A: "Turbocharger Information 2",   # 65178
    0x0FE9B: "Turbocharger Information 1",   # 65179
    0x0FE9C: "Main Bearing Temperature 3",   # 65180
    0x0FE9D: "Main Bearing Temperature 2",   # 65181
    0x0FE9E: "Main Bearing Temperature 1",   # 65182
    0x0FE9F: "Exhaust Port Temperature 5",   # 65183
    0x0FEA0: "Exhaust Port Temperature 4",   # 65184
    0x0FEA1: "Exhaust Port Temperature 3",   # 65185
    0x0FEA2: "Exhaust Port Temperature 2",   # 65186
    0x0FEA3: "Exhaust Port Temperature 1",   # 65187
    0x0FEA4: "Engine Temperature 2",   # 65188
    0x0FEA5: "Intake Manifold Information 2",   # 65189
    0x0FEA6: "Intake Manifold Information 1",   # 65190
    0x0FEA7: "Alternator Temperature 1",   # 65191
    0x0FEA8: "Articulation Control",   # 65192
    0x0FEA9: "Exhaust Oxygen 1",   # 65193
    0x0FEAA: "Alternate Fuel 2",   # 65194
    0x0FEAB: "Electronic Transmission Controller 6",   # 65195
    0x0FEAC: "Wheel Brake Lining Remaining Information",   # 65196
    0x0FEAD: "Wheel Application Pressure High Range Information",   # 65197
    0x0FEAE: "Air Supply Pressure",   # 65198
    0x0FEAF: "Fuel Consumption (Gaseous)",   # 65199
    0x0FEB0: "Trip Time Information 2",   # 65200
    0x0FEB1: "ECU History",   # 65201
    0x0FEB2: "Fuel Information 1 (Gaseous)",   # 65202
    0x0FEB3: "Fuel Information 1 (Liquid)",   # 65203
    0x0FEB4: "Trip Time Information 1",   # 65204
    0x0FEB5: "Trip Shutdown Information",   # 65205
    0x0FEB6: "Trip Vehicle Speed/Cruise Distance Information",   # 65206
    0x0FEB7: "Engine Speed/Load Factor Information",   # 65207
    0x0FEB8: "Trip Fuel Information (Gaseous)",   # 65208
    0x0FEB9: "Trip Fuel Information (Liquid)",   # 65209
    0x0FEBA: "Trip Distance Information",   # 65210
    0x0FEBB: "Trip Fan Information",   # 65211
    0x0FEBC: "Compression/Service Brake Information",   # 65212
    0x0FEBD: "Fan Drive #1",   # 65213
    0x0FEBE: "Electronic Engine Controller 4",   # 65214
    0x0FEBF: "Wheel Speed Information",   # 65215
    0x0FEC0: "Service Information",   # 65216
    0x0FEC1: "High Resolution Vehicle Distance",   # 65217
    0x0FEC2: "Electronic Retarder Controller 2",   # 65218
    0x0FEC3: "Electronic Transmission Controller 5",   # 65219
    0x0FEC4: "Electronic Brake System #2/2",   # 65220
    0x0FEC5: "Electronic Transmission Controller 4",   # 65221
    0x0FEC6: "Electronic Brake System #2/3",   # 65222
    0x0FEC7: "Electronic Transmission Controller 3",   # 65223
    0x0FEC8: "General Purpose Message #2/2",   # 65224
    0x0FEC9: "Electronic Brake System #1/2",   # 65225
    0x0FECA: "Active Diagnostic Trouble Codes",   # 65226
    0x0FECB: "Previously Active Diagnostic Trouble Codes",   # 65227
    0x0FECC: "Diagnostic Data Clear/Reset for Previously Active DTCs",   # 65228
    0x0FECD: "Freeze Frame Parameters",   # 65229
    0x0FECE: "Diagnostic Readiness 1",   # 65230
    0x0FECF: "Emission-Related Pending Diagnostic Trouble Codes",   # 65231
    0x0FED0: "Test Results for Non-continuously Monitored Systems",   # 65232
    0x0FED1: "Oxygen Sensor Test Results",   # 65233
    0x0FED2: "Non-Continuously Monitored Systems Test Identifiers Support",   # 65234
    0x0FED3: "Diagnostic Data Clear/Reset for Active DTCs",   # 65235
    0x0FED4: "Emission-Related MIL-On Diagnostic Trouble Codes",   # 65236
    0x0FED5: "Alternator Information",   # 65237
    0x0FED6: "Hybrid System Inputs 1",   # 65238
    0x0FED8: "ISO Commanded Address",   # 65240
    0x0FED9: "Auxiliary Input/Output Status 1",   # 65241
    0x0FEDA: "Software Identification",   # 65242
    0x0FEDB: "Engine Fluid Level/Pressure 2",   # 65243
    0x0FEDC: "Idle Operation",   # 65244
    0x0FEDD: "Turbocharger",   # 65245
    0x0FEDE: "Engine Air Start Pressure",   # 65246
    0x0FEDF: "Electronic Engine Controller 3",   # 65247
    0x0FEE0: "Vehicle Distance",   # 65248
    0x0FEE1: "Retarder Configuration",   # 65249
    0x0FEE2: "Transmission Configuration",   # 65250
    0x0FEE3: "Engine Configuration 1",   # 65251
    0x0FEE4: "Shutdown",   # 65252
    0x0FEE5: "Engine Hours, Revolutions",   # 65253
    0x0FEE6: "Time/Date",   # 65254
    0x0FEE7: "Vehicle Hours",   # 65255
    0x0FEE8: "Vehicle Direction/Speed",   # 65256
    0x0FEE9: "Fuel Consumption (Liquid) 1",   # 65257
    0x0FEEA: "Vehicle Weight",   # 65258
    0x0FEEB: "Component Identification",   # 65259
    0x0FEEC: "Vehicle Identification",   # 65260
    0x0FEED: "Cruise Control/Vehicle Speed Setup",   # 65261
    0x0FEEE: "Engine Temperature 1",   # 65262
    0x0FEEF: "Engine Fluid Level/Pressure 1",   # 65263
    0x0FEF0: "Power Takeoff Information",   # 65264
    0x0FEF1: "Cruise Control/Vehicle Speed 1",   # 65265
    0x0FEF2: "Fuel Economy (Liquid)",   # 65266
    0x0FEF3: "Vehicle Position 1",   # 65267
    0x0FEF4: "Tire Condition Message 1",   # 65268
    0x0FEF5: "Ambient Conditions",   # 65269
    0x0FEF6: "Intake/Exhaust Conditions 1",   # 65270
    0x0FEF7: "Vehicle Electrical Power 1",   # 65271
    0x0FEF8: "Transmission Fluids 1",   # 65272
    0x0FEF9: "Axle Information",   # 65273
    0x0FEFA: "Brakes 1",   # 65274
    0x0FEFB: "Retarder fluids",   # 65275
    0x0FEFC: "Dash Display 1",   # 65276
    0x0FEFD: "Alternate Fuel 1",   # 65277
    0x0FEFE: "Auxiliary Water Pump Pressure",   # 65278
    0x0FEFF: "Operator indicators",   # 65279
    0x0FF00: "Proprietary B (first entry)",   # 65280
    0x0FF01: "Proprietary B",   # 65281
    0x0FF02: "Proprietary B",   # 65282
    0x0FF03: "Proprietary B",   # 65283
    0x0FF05: "Proprietary B",   # 65285
    0x0FF08: "Proprietary B",   # 65288
    0x0FF09: "Proprietary B",   # 65289
    0x0FF0A: "Proprietary B",   # 65290
    0x0FF0B: "Proprietary B",   # 65291
    0x0FF0C: "Proprietary B",   # 65292
    0x0FF0D: "Proprietary B",   # 65293
    0x0FF0E: "Proprietary B",   # 65294
    0x0FF0F: "Proprietary B",   # 65295
    0x0FF10: "Proprietary B",   # 65296
    0x0FF11: "Proprietary B",   # 65297
    0x0FF12: "Proprietary B",   # 65298
    0x0FF13: "Proprietary B",   # 65299
    0x0FF14: "Proprietary B",   # 65300
    0x0FF15: "Proprietary B",   # 65301
    0x0FF16: "Proprietary B",   # 65302
    0x0FF17: "Proprietary B",   # 65303
    0x0FF18: "Proprietary B",   # 65304
    0x0FF19: "Proprietary B",   # 65305
    0x0FF1A: "Proprietary B",   # 65306
    0x0FF1B: "Proprietary B",   # 65307
    0x0FF1C: "Proprietary B",   # 65308
    0x0FF1D: "Proprietary B",   # 65309
    0x0FF1E: "Proprietary B",   # 65310
    0x0FF1F: "Proprietary B",   # 65311
    0x0FF20: "Proprietary B",   # 65312
    0x0FF21: "Proprietary B",   # 65313
    0x0FF22: "Proprietary B",   # 65314
    0x0FF23: "Proprietary B",   # 65315
    0x0FF24: "Proprietary B",   # 65316
    0x0FF25: "Proprietary B",   # 65317
    0x0FF26: "Proprietary B",   # 65318
    0x0FF27: "Proprietary B",   # 65319
    0x0FF28: "Proprietary B",   # 65320
    0x0FF29: "Proprietary B",   # 65321
    0x0FF2A: "Proprietary B",   # 65322
    0x0FF2B: "Proprietary B",   # 65323
    0x0FF2C: "Proprietary B",   # 65324
    0x0FF2D: "Proprietary B",   # 65325
    0x0FF2E: "Proprietary B",   # 65326
    0x0FF2F: "Proprietary B",   # 65327
    0x0FF30: "Proprietary B",   # 65328
    0x0FF31: "Proprietary B",   # 65329
    0x0FF32: "Proprietary B",   # 65330
    0x0FF33: "Proprietary B",   # 65331
    0x0FF34: "Proprietary B",   # 65332
    0x0FF35: "Proprietary B",   # 65333
    0x0FF36: "Proprietary B",   # 65334
    0x0FF37: "Proprietary B",   # 65335
    0x0FF38: "Proprietary B",   # 65336
    0x0FF39: "Proprietary B",   # 65337
    0x0FF3A: "Proprietary B",   # 65338
    0x0FF3B: "Proprietary B",   # 65339
    0x0FF3C: "Proprietary B",   # 65340
    0x0FF3D: "Proprietary B",   # 65341
    0x0FF3E: "Proprietary B",   # 65342
    0x0FF3F: "Proprietary B",   # 65343
    0x0FF40: "Proprietary B",   # 65344
    0x0FF41: "Proprietary B",   # 65345
    0x0FF42: "Proprietary B",   # 65346
    0x0FF43: "Proprietary B",   # 65347
    0x0FF44: "Proprietary B",   # 65348
    0x0FF45: "Proprietary B",   # 65349
    0x0FF46: "Proprietary B",   # 65350
    0x0FF47: "Proprietary B",   # 65351
    0x0FF48: "Proprietary B",   # 65352
    0x0FF49: "Proprietary B",   # 65353
    0x0FF4A: "Proprietary B",   # 65354
    0x0FF4B: "Proprietary B",   # 65355
    0x0FF4C: "Proprietary B",   # 65356
    0x0FF4D: "Proprietary B",   # 65357
    0x0FF4E: "Proprietary B",   # 65358
    0x0FF4F: "Proprietary B",   # 65359
    0x0FF52: "Proprietary B",   # 65362
    0x0FF53: "Proprietary B",   # 65363
    0x0FF54: "Proprietary B",   # 65364
    0x0FF55: "Proprietary B",   # 65365
    0x0FF56: "Proprietary B",   # 65366
    0x0FF57: "Proprietary B",   # 65367
    0x0FF58: "Proprietary B",   # 65368
    0x0FF59: "Proprietary B",   # 65369
    0x0FF5A: "Proprietary B",   # 65370
    0x0FF5B: "Proprietary B",   # 65371
    0x0FF5C: "Proprietary B",   # 65372
    0x0FF5D: "Proprietary B",   # 65373
    0x0FF5E: "Proprietary B",   # 65374
    0x0FF5F: "Proprietary B",   # 65375
    0x0FF60: "Proprietary B",   # 65376
    0x0FF61: "Proprietary B",   # 65377
    0x0FF62: "Proprietary B",   # 65378
    0x0FF63: "Proprietary B",   # 65379
    0x0FF64: "Proprietary B",   # 65380
    0x0FF65: "Proprietary B",   # 65381
    0x0FF66: "Proprietary B",   # 65382
    0x0FF67: "Proprietary B",   # 65383
    0x0FF68: "Proprietary B",   # 65384
    0x0FF69: "Proprietary B",   # 65385
    0x0FF6A: "Proprietary B",   # 65386
    0x0FF6B: "Proprietary B",   # 65387
    0x0FF6C: "Proprietary B",   # 65388
    0x0FF6D: "Proprietary B",   # 65389
    0x0FF6E: "Proprietary B",   # 65390
    0x0FF6F: "Proprietary B",   # 65391
    0x0FF70: "Proprietary B",   # 65392
    0x0FF71: "Proprietary B",   # 65393
    0x0FF72: "Proprietary B",   # 65394
    0x0FF73: "Proprietary B",   # 65395
    0x0FF74: "Proprietary B",   # 65396
    0x0FF75: "Proprietary B",   # 65397
    0x0FF76: "Proprietary B",   # 65398
    0x0FF77: "Proprietary B",   # 65399
    0x0FF78: "Proprietary B",   # 65400
    0x0FF79: "Proprietary B",   # 65401
    0x0FF7A: "Proprietary B",   # 65402
    0x0FF7B: "Proprietary B",   # 65403
    0x0FF7C: "Proprietary B",   # 65404
    0x0FF7D: "Proprietary B",   # 65405
    0x0FF7E: "Proprietary B",   # 65406
    0x0FF7F: "Proprietary B",   # 65407
    0x0FF80: "Proprietary B",   # 65408
    0x0FF82: "Proprietary B",   # 65410
    0x0FF83: "Proprietary B",   # 65411
    0x0FF84: "Proprietary B",   # 65412
    0x0FF85: "Proprietary B",   # 65413
    0x0FF86: "Proprietary B",   # 65414
    0x0FF87: "Proprietary B",   # 65415
    0x0FF88: "Proprietary B",   # 65416
    0x0FF89: "Proprietary B",   # 65417
    0x0FF8A: "Proprietary B",   # 65418
    0x0FF8B: "Proprietary B",   # 65419
    0x0FF8C: "Proprietary B",   # 65420
    0x0FF8D: "Proprietary B",   # 65421
    0x0FF8E: "Proprietary B",   # 65422
    0x0FF8F: "Proprietary B",   # 65423
    0x0FF90: "Proprietary B",   # 65424
    0x0FF91: "Proprietary B",   # 65425
    0x0FF92: "Proprietary B",   # 65426
    0x0FF93: "Proprietary B",   # 65427
    0x0FF94: "Proprietary B",   # 65428
    0x0FF95: "Proprietary B",   # 65429
    0x0FF96: "Proprietary B",   # 65430
    0x0FF97: "Proprietary B",   # 65431
    0x0FF98: "Proprietary B",   # 65432
    0x0FF99: "Proprietary B",   # 65433
    0x0FF9A: "Proprietary B",   # 65434
    0x0FF9B: "Proprietary B",   # 65435
    0x0FF9C: "Proprietary B",   # 65436
    0x0FF9D: "Proprietary B",   # 65437
    0x0FF9E: "Proprietary B",   # 65438
    0x0FF9F: "Proprietary B",   # 65439
    0x0FFA0: "Proprietary B",   # 65440
    0x0FFA1: "Proprietary B",   # 65441
    0x0FFA2: "Proprietary B",   # 65442
    0x0FFA3: "Proprietary B",   # 65443
    0x0FFA4: "Proprietary B",   # 65444
    0x0FFA5: "Proprietary B",   # 65445
    0x0FFA6: "Proprietary B",   # 65446
    0x0FFA7: "Proprietary B",   # 65447
    0x0FFA8: "Proprietary B",   # 65448
    0x0FFA9: "Proprietary B",   # 65449
    0x0FFAA: "Proprietary B",   # 65450
    0x0FFAB: "Proprietary B",   # 65451
    0x0FFAC: "Proprietary B",   # 65452
    0x0FFAD: "Proprietary B",   # 65453
    0x0FFAE: "Proprietary B",   # 65454
    0x0FFAF: "Proprietary B",   # 65455
    0x0FFB0: "Proprietary B",   # 65456
    0x0FFB1: "Proprietary B",   # 65457
    0x0FFB2: "Proprietary B",   # 65458
    0x0FFB3: "Proprietary B",   # 65459
    0x0FFB4: "Proprietary B",   # 65460
    0x0FFB5: "Proprietary B",   # 65461
    0x0FFB6: "Proprietary B",   # 65462
    0x0FFB7: "Proprietary B",   # 65463
    0x0FFB8: "Proprietary B",   # 65464
    0x0FFB9: "Proprietary B",   # 65465
    0x0FFBA: "Proprietary B",   # 65466
    0x0FFBB: "Proprietary B",   # 65467
    0x0FFBC: "Proprietary B",   # 65468
    0x0FFBD: "Proprietary B",   # 65469
    0x0FFBE: "Proprietary B",   # 65470
    0x0FFBF: "Proprietary B",   # 65471
    0x0FFC0: "Proprietary B",   # 65472
    0x0FFC1: "Proprietary B",   # 65473
    0x0FFC2: "Proprietary B",   # 65474
    0x0FFC3: "Proprietary B",   # 65475
    0x0FFC4: "Proprietary B",   # 65476
    0x0FFC5: "Proprietary B",   # 65477
    0x0FFC6: "Proprietary B",   # 65478
    0x0FFC7: "Proprietary B",   # 65479
    0x0FFC8: "Proprietary B",   # 65480
    0x0FFC9: "Proprietary B",   # 65481
    0x0FFCA: "Proprietary B",   # 65482
    0x0FFCB: "Proprietary B",   # 65483
    0x0FFCC: "Proprietary B",   # 65484
    0x0FFCD: "Proprietary B",   # 65485
    0x0FFCE: "Proprietary B",   # 65486
    0x0FFCF: "Proprietary B",   # 65487
    0x0FFD0: "Proprietary B",   # 65488
    0x0FFD1: "Proprietary B",   # 65489
    0x0FFD2: "Proprietary B",   # 65490
    0x0FFD3: "Proprietary B",   # 65491
    0x0FFD4: "Proprietary B",   # 65492
    0x0FFD5: "Proprietary B",   # 65493
    0x0FFD6: "Proprietary B",   # 65494
    0x0FFD7: "Proprietary B",   # 65495
    0x0FFD8: "Proprietary B",   # 65496
    0x0FFD9: "Proprietary B",   # 65497
    0x0FFDA: "Proprietary B",   # 65498
    0x0FFDB: "Proprietary B",   # 65499
    0x0FFDC: "Proprietary B",   # 65500
    0x0FFDD: "Proprietary B",   # 65501
    0x0FFDE: "Proprietary B",   # 65502
    0x0FFDF: "Proprietary B",   # 65503
    0x0FFE0: "Proprietary B",   # 65504
    0x0FFE1: "Proprietary B",   # 65505
    0x0FFE2: "Proprietary B",   # 65506
    0x0FFE3: "Proprietary B",   # 65507
    0x0FFE4: "Proprietary B",   # 65508
    0x0FFE5: "Proprietary B",   # 65509
    0x0FFE6: "Proprietary B",   # 65510
    0x0FFE7: "Proprietary B",   # 65511
    0x0FFE8: "Proprietary B",   # 65512
    0x0FFE9: "Proprietary B",   # 65513
    0x0FFEA: "Proprietary B",   # 65514
    0x0FFEB: "Proprietary B",   # 65515
    0x0FFEC: "Proprietary B",   # 65516
    0x0FFED: "Proprietary B",   # 65517
    0x0FFEE: "Proprietary B",   # 65518
    0x0FFEF: "Proprietary B",   # 65519
    0x0FFF0: "Proprietary B",   # 65520
    0x0FFF1: "Proprietary B",   # 65521
    0x0FFF2: "Proprietary B",   # 65522
    0x0FFF3: "Proprietary B",   # 65523
    0x0FFF4: "Proprietary B",   # 65524
    0x0FFF5: "Proprietary B",   # 65525
    0x0FFF6: "Proprietary B",   # 65526
    0x0FFF7: "Proprietary B",   # 65527
    0x0FFF8: "Proprietary B",   # 65528
    0x0FFF9: "Proprietary B",   # 65529
    0x0FFFA: "Proprietary B",   # 65530
    0x0FFFB: "Proprietary B",   # 65531
    0x0FFFC: "Proprietary B",   # 65532
    0x0FFFD: "Proprietary B",   # 65533
    0x0FFFE: "Proprietary B",   # 65534
    0x0FFFF: "Proprietary B (last entry)",   # 65535
    0x1ED00: "NMEA - Request/Command/Acknowledge group function",   # 126208
    0x1EF00: "Proprietary A2",   # 126720
    0x1F007: "Alert",   # 126983
    0x1F008: "Alert Response",   # 126984
    0x1F009: "Alert Text",   # 126985
    0x1F00A: "Alert Configuration",   # 126986
    0x1F00B: "Alert Threshold",   # 126987
    0x1F00C: "Alert Value",   # 126988
    0x1F010: "System Time",   # 126992
    0x1F011: "Heartbeat",   # 126993
    0x1F014: "Product Information",   # 126996
    0x1F101: "Man Overboard Notification(MOB)",   # 127233
    0x1F105: "Heading/Track Control",   # 127237
    0x1F10D: "Rudder",   # 127245
    0x1F112: "Vessel Heading",   # 127250
    0x1F113: "Rate of Turn",   # 127251
    0x1F114: "Heave",   # 127252
    0x1F119: "Attitude",   # 127257
    0x1F11A: "Magnetic Variation",   # 127258
    0x1F200: "Engine Parameters, Rapid Update",   # 127488
    0x1F201: "Engine Parameters, Dynamic",   # 127489
    0x1F205: "Transmission Parameters, Dynamic",   # 127493
    0x1F208: "Trip Fuel Consumption, Vessel",   # 127496
    0x1F209: "Trip Fuel Consumption, Engine",   # 127497
    0x1F20A: "Engine Parameters, Static",   # 127498
    0x1F20C: "Load Controller Connection State / Control",   # 127500
    0x1F20D: "Switch Bank Status",   # 127501
    0x1F20E: "Switch Bank Control - DEPRICATED",   # 127502
    0x1F20F: "AC Input Status -DEPRECATED",   # 127503
    0x1F210: "AC Output Status -DEPRECATED",   # 127504
    0x1F211: "Fluid Level",   # 127505
    0x1F212: "DC Detailed Status",   # 127506
    0x1F213: "Charger Status- DEPRECATED",   # 127507
    0x1F214: "Battery Status",   # 127508
    0x1F215: "Inverter Status- DEPRECATED",   # 127509
    0x1F216: "Charger Configuration Status",   # 127510
    0x1F217: "Inverter Configuration Status",   # 127511
    0x1F218: "AGS Configuration Status",   # 127512
    0x1F219: "Battery Configuration Status",   # 127513
    0x1F21A: "AGS Status",   # 127514
    0x1F300: "AC Power / Current- Phase A",   # 127744
    0x1F301: "AC Power / Current- Phase B",   # 127745
    0x1F302: "AC Power / Current- Phase C",   # 127746
    0x1F303: "AC Voltage / Frequency-Phase A",   # 127747
    0x1F304: "AC Voltage / Frequency-Phase B",   # 127748
    0x1F305: "AC Voltage / Frequency-Phase C",   # 127749
    0x1F306: "Converter (Inverter/Charger) Status",   # 127750
    0x1F307: "DC Voltage / Current",   # 127751
    0x1F400: "Nautical Leeway Angle",   # 128000
    0x1F401: "Vessel Acceleration",   # 128001
    0x1F406: "Thruster Control Status",   # 128006
    0x1F407: "Thruster Information",   # 128007
    0x1F408: "Thruster Motor Status",   # 128008
    0x1F503: "Speed, Water Referenced",   # 128259
    0x1F50B: "Water Depth",   # 128267
    0x1F513: "Distance Log",   # 128275
    0x1F608: "Tracked Target Data",   # 128520
    0x1F61A: "Elevator Car Status",   # 128538
    0x1F700: "Elevator Motor Control",   # 128768
    0x1F701: "Elevator Deck Push Button",   # 128769
    0x1F708: "Windlass Control Status",   # 128776
    0x1F709: "Anchor Windlass Operating Status",   # 128777
    0x1F70A: "Anchor Windlass Monitoring Status",   # 128778
    0x1F70C: "Linear Actuator Control/Status",   # 128780
    0x1F801: "Position, Rapid Update",   # 129025
    0x1F802: "COG & SOG, Rapid Update",   # 129026
    0x1F803: "Position Delta, High Precision Rapid Update",   # 129027
    0x1F804: "Altitude Delta, High Precision Rapid Update",   # 129028
    0x1F805: "GNSS Position Data",   # 129029
    0x1F809: "Local Time Offset",   # 129033
    0x1F80E: "AIS Class A Position Report",   # 129038
    0x1F80F: "AIS Class B Position Report",   # 129039
    0x1F810: "AIS Class B Extended Position Report",   # 129040
    0x1F811: "AIS Aids to Navigation (AtoN) Report",   # 129041
    0x1F814: "Datum",   # 129044
    0x1F903: "Cross Track Error",   # 129283
    0x1F904: "Navigation Data",   # 129284
    0x1F905: "Navigation - Route/WP information",   # 129285
    0x1F90B: "Set & Drift, Rapid Update",   # 129291
    0x1F915: "Time to/from Mark",   # 129301
    0x1F916: "Bearing and Distance between two Marks",   # 129302
    0x1FA02: "GNSS Control Status",   # 129538
    0x1FA03: "GNSS DOPs",   # 129539
    0x1FA04: "GNSS Sats in View",   # 129540
    0x1FA05: "GPS Almanac Data",   # 129541
    0x1FA06: "GNSS Pseudorange Noise Statistics",   # 129542
    0x1FA09: "GNSS RAIM Output",   # 129545
    0x1FA0A: "GNSS RAIM Settings",   # 129546
    0x1FA0B: "GNSS Pseudorange Error Statistics",   # 129547
    0x1FA0D: "DGNSS Corrections",   # 129549
    0x1FA0E: "GNSS Differential Correction Receiver Interface",   # 129550
    0x1FA0F: "GNSS Differential Correction Receiver Signal",   # 129551
    0x1FA14: "GLONASS Almanac Data",   # 129556
    0x1FB00: "AIS DGNSS Broadcast Binary Message",   # 129792
    0x1FB01: "AIS UTC and Date Report",   # 129793
    0x1FB02: "AIS Class A Static and Voyage Related Data",   # 129794
    0x1FB03: "AIS Addressed Binary Message",   # 129795
    0x1FB04: "AIS Acknowledge - DEPRECATED",   # 129796
    0x1FB05: "AIS Binary Broadcast Message",   # 129797
    0x1FB06: "AIS SAR Aircraft Position Report",   # 129798
    0x1FB07: "Radio Frequency/Mode/Power",   # 129799
    0x1FB08: "AIS UTC/Date Inquiry",   # 129800
    0x1FB09: "AIS Addressed Safety Related Message",   # 129801
    0x1FB0A: "AIS Safety Related Broadcast Message",   # 129802
    0x1FB0B: "AIS Interrogation",   # 129803
    0x1FB0C: "AIS Assignment Mode Command",   # 129804
    0x1FB0D: "AIS Data Link Management Message",   # 129805
    0x1FB0E: "AIS Channel Management",   # 129806
    0x1FB0F: "AIS Group Assignment",   # 129807
    0x1FB10: "DSC Call Information",   # 129808
    0x1FB11: "AIS Static Data Report, Part A",   # 129809
    0x1FB12: "AIS Static Data Report, Part B",   # 129810
    0x1FB13: "AIS Single Slot Binary Message - DEPRECATED",   # 129811
    0x1FB14: "AIS Multi Slot Binary Message - DEPRECATED",   # 129812
    0x1FB15: "AIS Long-Range Broadcast Message",   # 129813
    0x1FB16: "AIS Single Slot Binary Message",   # 129814
    0x1FB17: "AIS Multi Slot Binary Message",   # 129815
    0x1FB18: "AIS Acknowledge",   # 129816
    0x1FC04: "Loran-C TD Data",   # 130052
    0x1FC05: "Loran-C Range Data",   # 130053
    0x1FC06: "Loran-C Signal Data",   # 130054
    0x1FC0C: "Label",   # 130060
    0x1FC0D: "Channel Source Configuration",   # 130061
    0x1FC10: "Route and WP Service - Database List",   # 130064
    0x1FC11: "Route and WP Service - Route List",   # 130065
    0x1FC12: "Route and WP Service - Route/WP-List Attributes",   # 130066
    0x1FC13: "Route and WP Service - Route - WP Name & Position",   # 130067
    0x1FC14: "Route and WP Service - Route - WP Name",   # 130068
    0x1FC15: "Route and WP Service - XTE Limit & Navigation Method",   # 130069
    0x1FC16: "Route and WP Service - WP Comment",   # 130070
    0x1FC17: "Route and WP Service - Route Comment",   # 130071
    0x1FC18: "Route and WP Service - Database Comment",   # 130072
    0x1FC19: "Route and WP Service - Radius of Turn",   # 130073
    0x1FC1A: "Route and WP Service - WP List - WP Name & Position",   # 130074
    0x1FD02: "Wind Data",   # 130306
    0x1FD06: "Environmental Parameters - DEPRECATED",   # 130310
    0x1FD07: "Environmental Parameters- DEPRECATED",   # 130311
    0x1FD08: "Temperature - DEPRECATED",   # 130312
    0x1FD09: "Humidity",   # 130313
    0x1FD0A: "Actual Pressure",   # 130314
    0x1FD0B: "Set Pressure",   # 130315
    0x1FD0C: "Temperature, Extended Range",   # 130316
    0x1FD10: "Tide Station Data",   # 130320
    0x1FD11: "Salinity Station Data",   # 130321
    0x1FD12: "Current Station Data",   # 130322
    0x1FD13: "Meteorological Station Data",   # 130323
    0x1FD14: "Moored Buoy Station Data",   # 130324
    0x1FD1A: "Lighting System Settings",   # 130330
    0x1FE00: "Payload Mass",   # 130560
    0x1FE01: "Lighting Zone",   # 130561
    0x1FE02: "Lighting Scene",   # 130562
    0x1FE03: "Lighting Device",   # 130563
    0x1FE04: "Lighting Device Enumeration",   # 130564
    0x1FE05: "Lighting Color Sequence",   # 130565
    0x1FE06: "Lighting Program",   # 130566
    0x1FE07: "Watermaker Input Setting and Status",   # 130567
    0x1FE08: "Entertainment - Diagnostic Status",   # 130568
    0x1FE09: "Entertainment - Current File and Status",   # 130569
    0x1FE0A: "Entertainment - Library Data File",   # 130570
    0x1FE0B: "Entertainment - Library Data Group",   # 130571
    0x1FE0C: "Entertainment - Library Data Search",   # 130572
    0x1FE0D: "Entertainment - Supported Source Data",   # 130573
    0x1FE0E: "Entertainment - Supported Zone Data",   # 130574
    0x1FE0F: "Entertainment - Parental Control Status",   # 130575
    0x1FE10: "Trim Tab Status",   # 130576
    0x1FE11: "Direction Data",   # 130577
    0x1FE12: "Vessel Speed Components",   # 130578
    0x1FE13: "Entertainment - System Configuration",   # 130579
    0x1FE14: "Entertainment - System Configuration Status - DEPRECATED",   # 130580
    0x1FE15: "Entertainment - Zone Configuration Status - DEPRECATED",   # 130581
    0x1FE16: "Entertainment - Zone Volume",   # 130582
    0x1FE17: "Entertainment - Available Audio EQ Presets",   # 130583
    0x1FE18: "Entertainment - Bluetooth Devices",   # 130584
    0x1FE19: "Entertainment - Bluetooth Source Status",   # 130585
    0x1FE1A: "Entertainment - Zone Configuration Status",   # 130586
    0x1FF01: "Proprietary B - Page 1",   # 130817
    0x1FF02: "Proprietary B - Page 1",   # 130818
    0x1FF03: "Proprietary B - Page 1",   # 130819
    0x1FF04: "Proprietary B - Page 1",   # 130820
    0x1FF05: "Proprietary B - Page 1",   # 130821
    0x1FF06: "Proprietary B - Page 1",   # 130822
    0x1FF07: "Proprietary B - Page 1",   # 130823
    0x1FF08: "Proprietary B - Page 1",   # 130824
    0x1FF09: "Proprietary B - Page 1",   # 130825
    0x1FF0A: "Proprietary B - Page 1",   # 130826
    0x1FF0B: "Proprietary B - Page 1",   # 130827
    0x1FF0C: "Proprietary B - Page 1",   # 130828
    0x1FF0D: "Proprietary B - Page 1",   # 130829
    0x1FF0E: "Proprietary B - Page 1",   # 130830
    0x1FF0F: "Proprietary B - Page 1",   # 130831
    0x1FF10: "Proprietary B - Page 1",   # 130832
    0x1FF11: "Proprietary B - Page 1",   # 130833
    0x1FF12: "Proprietary B - Page 1",   # 130834
    0x1FF13: "Proprietary B - Page 1",   # 130835
    0x1FF16: "Proprietary B - Page 1",   # 130838
    0x1FF17: "Proprietary B - Page 1",   # 130839
    0x1FF18: "Proprietary B - Page 1",   # 130840
    0x1FF19: "Proprietary B - Page 1",   # 130841
    0x1FF1A: "Proprietary B - Page 1",   # 130842
    0x1FF1B: "Proprietary B - Page 1",   # 130843
    0x1FF1C: "Proprietary B - Page 1",   # 130844
    0x1FF1D: "Proprietary B - Page 1",   # 130845
    0x1FF1E: "Proprietary B - Page 1",   # 130846
    0x1FF1F: "Proprietary B - Page 1",   # 130847
    0x1FF20: "Proprietary B - Page 1",   # 130848
    0x1FF21: "Proprietary B - Page 1",   # 130849
    0x1FF22: "Proprietary B - Page 1",   # 130850
    0x1FF23: "Proprietary B - Page 1",   # 130851
    0x1FF24: "Proprietary B - Page 1",   # 130852
    0x1FF25: "Proprietary B - Page 1",   # 130853
    0x1FF26: "Proprietary B - Page 1",   # 130854
    0x1FF27: "Proprietary B - Page 1",   # 130855
    0x1FF28: "Proprietary B - Page 1",   # 130856
    0x1FF29: "Proprietary B - Page 1",   # 130857
    0x1FF2A: "Proprietary B - Page 1",   # 130858
    0x1FF2B: "Proprietary B - Page 1",   # 130859
    0x1FF2C: "Proprietary B - Page 1",   # 130860
    0x1FF2D: "Proprietary B - Page 1",   # 130861
    0x1FF2E: "Proprietary B - Page 1",   # 130862
    0x1FF2F: "Proprietary B - Page 1",   # 130863
    0x1FF30: "Proprietary B - Page 1",   # 130864
    0x1FF31: "Proprietary B - Page 1",   # 130865
    0x1FF32: "Proprietary B - Page 1",   # 130866
    0x1FF33: "Proprietary B - Page 1",   # 130867
    0x1FF34: "Proprietary B - Page 1",   # 130868
    0x1FF35: "Proprietary B - Page 1",   # 130869
    0x1FF36: "Proprietary B - Page 1",   # 130870
    0x1FF37: "Proprietary B - Page 1",   # 130871
    0x1FF38: "Proprietary B - Page 1",   # 130872
    0x1FF39: "Proprietary B - Page 1",   # 130873
    0x1FF3A: "Proprietary B - Page 1",   # 130874
    0x1FF3B: "Proprietary B - Page 1",   # 130875
    0x1FF3C: "Proprietary B - Page 1",   # 130876
    0x1FF3D: "Proprietary B - Page 1",   # 130877
    0x1FF3E: "Proprietary B - Page 1",   # 130878
    0x1FF3F: "Proprietary B - Page 1",   # 130879
    0x1FF40: "Proprietary B - Page 1",   # 130880
    0x1FF41: "Proprietary B - Page 1",   # 130881
    0x1FF42: "Proprietary B - Page 1",   # 130882
    0x1FF43: "Proprietary B - Page 1",   # 130883
    0x1FF44: "Proprietary B - Page 1",   # 130884
    0x1FF45: "Proprietary B - Page 1",   # 130885
    0x1FF46: "Proprietary B - Page 1",   # 130886
    0x1FF47: "Proprietary B - Page 1",   # 130887
    0x1FF48: "Proprietary B - Page 1",   # 130888
    0x1FF49: "Proprietary B - Page 1",   # 130889
    0x1FF4A: "Proprietary B - Page 1",   # 130890
    0x1FF4B: "Proprietary B - Page 1",   # 130891
    0x1FF4C: "Proprietary B - Page 1",   # 130892
    0x1FF4D: "Proprietary B - Page 1",   # 130893
    0x1FF4E: "Proprietary B - Page 1",   # 130894
    0x1FF4F: "Proprietary B - Page 1",   # 130895
    0x1FF50: "Proprietary B - Page 1",   # 130896
    0x1FF51: "Proprietary B - Page 1",   # 130897
    0x1FF52: "Proprietary B - Page 1",   # 130898
    0x1FF53: "Proprietary B - Page 1",   # 130899
    0x1FF54: "Proprietary B - Page 1",   # 130900
    0x1FF55: "Proprietary B - Page 1",   # 130901
    0x1FF56: "Proprietary B - Page 1",   # 130902
    0x1FF57: "Proprietary B - Page 1",   # 130903
    0x1FF58: "Proprietary B - Page 1",   # 130904
    0x1FF59: "Proprietary B - Page 1",   # 130905
    0x1FF5A: "Proprietary B - Page 1",   # 130906
    0x1FF5B: "Proprietary B - Page 1",   # 130907
    0x1FF5C: "Proprietary B - Page 1",   # 130908
    0x1FF5D: "Proprietary B - Page 1",   # 130909
    0x1FF5E: "Proprietary B - Page 1",   # 130910
    0x1FF5F: "Proprietary B - Page 1",   # 130911
    0x1FF60: "Proprietary B - Page 1",   # 130912
    0x1FF61: "Proprietary B - Page 1",   # 130913
    0x1FF62: "Proprietary B - Page 1",   # 130914
    0x1FF63: "Proprietary B - Page 1",   # 130915
    0x1FF64: "Proprietary B - Page 1",   # 130916
    0x1FF65: "Proprietary B - Page 1",   # 130917
    0x1FF66: "Proprietary B - Page 1",   # 130918
    0x1FF67: "Proprietary B - Page 1",   # 130919
    0x1FF68: "Proprietary B - Page 1",   # 130920
    0x1FF69: "Proprietary B - Page 1",   # 130921
    0x1FF6A: "Proprietary B - Page 1",   # 130922
    0x1FF6B: "Proprietary B - Page 1",   # 130923
    0x1FF6C: "Proprietary B - Page 1",   # 130924
    0x1FF6D: "Proprietary B - Page 1",   # 130925
    0x1FF6E: "Proprietary B - Page 1",   # 130926
    0x1FF6F: "Proprietary B - Page 1",   # 130927
    0x1FF70: "Proprietary B - Page 1",   # 130928
    0x1FF71: "Proprietary B - Page 1",   # 130929
    0x1FF72: "Proprietary B - Page 1",   # 130930
    0x1FF73: "Proprietary B - Page 1",   # 130931
    0x1FF74: "Proprietary B - Page 1",   # 130932
    0x1FF75: "Proprietary B - Page 1",   # 130933
    0x1FF76: "Proprietary B - Page 1",   # 130934
    0x1FF77: "Proprietary B - Page 1",   # 130935
    0x1FF78: "Proprietary B - Page 1",   # 130936
    0x1FF79: "Proprietary B - Page 1",   # 130937
    0x1FF7A: "Proprietary B - Page 1",   # 130938
    0x1FF7B: "Proprietary B - Page 1",   # 130939
    0x1FF7C: "Proprietary B - Page 1",   # 130940
    0x1FF7D: "Proprietary B - Page 1",   # 130941
    0x1FF7E: "Proprietary B - Page 1",   # 130942
    0x1FF7F: "Proprietary B - Page 1",   # 130943
    0x1FF80: "Proprietary B - Page 1",   # 130944
    0x1FF81: "Proprietary B - Page 1",   # 130945
    0x1FF82: "Proprietary B - Page 1",   # 130946
    0x1FF83: "Proprietary B - Page 1",   # 130947
    0x1FF84: "Proprietary B - Page 1",   # 130948
    0x1FF85: "Proprietary B - Page 1",   # 130949
    0x1FF86: "Proprietary B - Page 1",   # 130950
    0x1FF87: "Proprietary B - Page 1",   # 130951
    0x1FF88: "Proprietary B - Page 1",   # 130952
    0x1FF89: "Proprietary B - Page 1",   # 130953
    0x1FF8A: "Proprietary B - Page 1",   # 130954
    0x1FF8B: "Proprietary B - Page 1",   # 130955
    0x1FF8C: "Proprietary B - Page 1",   # 130956
    0x1FF8D: "Proprietary B - Page 1",   # 130957
    0x1FF8E: "Proprietary B - Page 1",   # 130958
    0x1FF8F: "Proprietary B - Page 1",   # 130959
    0x1FF90: "Proprietary B - Page 1",   # 130960
    0x1FF91: "Proprietary B - Page 1",   # 130961
    0x1FF92: "Proprietary B - Page 1",   # 130962
    0x1FF93: "Proprietary B - Page 1",   # 130963
    0x1FF94: "Proprietary B - Page 1",   # 130964
    0x1FF95: "Proprietary B - Page 1",   # 130965
    0x1FF96: "Proprietary B - Page 1",   # 130966
    0x1FF97: "Proprietary B - Page 1",   # 130967
    0x1FF98: "Proprietary B - Page 1",   # 130968
    0x1FF99: "Proprietary B - Page 1",   # 130969
    0x1FF9A: "Proprietary B - Page 1",   # 130970
    0x1FF9B: "Proprietary B - Page 1",   # 130971
    0x1FF9C: "Proprietary B - Page 1",   # 130972
    0x1FF9D: "Proprietary B - Page 1",   # 130973
    0x1FF9E: "Proprietary B - Page 1",   # 130974
    0x1FF9F: "Proprietary B - Page 1",   # 130975
    0x1FFA0: "Proprietary B - Page 1",   # 130976
    0x1FFA1: "Proprietary B - Page 1",   # 130977
    0x1FFA2: "Proprietary B - Page 1",   # 130978
    0x1FFA3: "Proprietary B - Page 1",   # 130979
    0x1FFA4: "Proprietary B - Page 1",   # 130980
    0x1FFA5: "Proprietary B - Page 1",   # 130981
    0x1FFA6: "Proprietary B - Page 1",   # 130982
    0x1FFA7: "Proprietary B - Page 1",   # 130983
    0x1FFA8: "Proprietary B - Page 1",   # 130984
    0x1FFA9: "Proprietary B - Page 1",   # 130985
    0x1FFAA: "Proprietary B - Page 1",   # 130986
    0x1FFAB: "Proprietary B - Page 1",   # 130987
    0x1FFAC: "Proprietary B - Page 1",   # 130988
    0x1FFAD: "Proprietary B - Page 1",   # 130989
    0x1FFAE: "Proprietary B - Page 1",   # 130990
    0x1FFAF: "Proprietary B - Page 1",   # 130991
    0x1FFB0: "Proprietary B - Page 1",   # 130992
    0x1FFB1: "Proprietary B - Page 1",   # 130993
    0x1FFB2: "Proprietary B - Page 1",   # 130994
    0x1FFB3: "Proprietary B - Page 1",   # 130995
    0x1FFB4: "Proprietary B - Page 1",   # 130996
    0x1FFB5: "Proprietary B - Page 1",   # 130997
    0x1FFB6: "Proprietary B - Page 1",   # 130998
    0x1FFB7: "Proprietary B - Page 1",   # 130999
    0x1FFB8: "Proprietary B - Page 1",   # 131000
    0x1FFB9: "Proprietary B - Page 1",   # 131001
    0x1FFBA: "Proprietary B - Page 1",   # 131002
    0x1FFBB: "Proprietary B - Page 1",   # 131003
    0x1FFBC: "Proprietary B - Page 1",   # 131004
    0x1FFBD: "Proprietary B - Page 1",   # 131005
    0x1FFBE: "Proprietary B - Page 1",   # 131006
    0x1FFBF: "Proprietary B - Page 1",   # 131007
    0x1FFC0: "Proprietary B - Page 1",   # 131008
    0x1FFC1: "Proprietary B - Page 1",   # 131009
    0x1FFC2: "Proprietary B - Page 1",   # 131010
    0x1FFC3: "Proprietary B - Page 1",   # 131011
    0x1FFC4: "Proprietary B - Page 1",   # 131012
    0x1FFC5: "Proprietary B - Page 1",   # 131013
    0x1FFC6: "Proprietary B - Page 1",   # 131014
    0x1FFC7: "Proprietary B - Page 1",   # 131015
    0x1FFC8: "Proprietary B - Page 1",   # 131016
    0x1FFC9: "Proprietary B - Page 1",   # 131017
    0x1FFCA: "Proprietary B - Page 1",   # 131018
    0x1FFCB: "Proprietary B - Page 1",   # 131019
    0x1FFCC: "Proprietary B - Page 1",   # 131020
    0x1FFCD: "Proprietary B - Page 1",   # 131021
    0x1FFCE: "Proprietary B - Page 1",   # 131022
    0x1FFCF: "Proprietary B - Page 1",   # 131023
    0x1FFD0: "Proprietary B - Page 1",   # 131024
    0x1FFD1: "Proprietary B - Page 1",   # 131025
    0x1FFD2: "Proprietary B - Page 1",   # 131026
    0x1FFD3: "Proprietary B - Page 1",   # 131027
    0x1FFD4: "Proprietary B - Page 1",   # 131028
    0x1FFD5: "Proprietary B - Page 1",   # 131029
    0x1FFD6: "Proprietary B - Page 1",   # 131030
    0x1FFD7: "Proprietary B - Page 1",   # 131031
    0x1FFD8: "Proprietary B - Page 1",   # 131032
    0x1FFD9: "Proprietary B - Page 1",   # 131033
    0x1FFDA: "Proprietary B - Page 1",   # 131034
    0x1FFDB: "Proprietary B - Page 1",   # 131035
    0x1FFDC: "Proprietary B - Page 1",   # 131036
    0x1FFDD: "Proprietary B - Page 1",   # 131037
    0x1FFDE: "Proprietary B - Page 1",   # 131038
    0x1FFDF: "Proprietary B - Page 1",   # 131039
    0x1FFE0: "Proprietary B - Page 1",   # 131040
    0x1FFE1: "Proprietary B - Page 1",   # 131041
    0x1FFE2: "Proprietary B - Page 1",   # 131042
    0x1FFE3: "Proprietary B - Page 1",   # 131043
    0x1FFE4: "Proprietary B - Page 1",   # 131044
    0x1FFE5: "Proprietary B - Page 1",   # 131045
    0x1FFE6: "Proprietary B - Page 1",   # 131046
    0x1FFE7: "Proprietary B - Page 1",   # 131047
    0x1FFE8: "Proprietary B - Page 1",   # 131048
    0x1FFE9: "Proprietary B - Page 1",   # 131049
    0x1FFEA: "Proprietary B - Page 1",   # 131050
    0x1FFEB: "Proprietary B - Page 1",   # 131051
    0x1FFEC: "Proprietary B - Page 1",   # 131052
    0x1FFED: "Proprietary B - Page 1",   # 131053
    0x1FFEE: "Proprietary B - Page 1",   # 131054
    0x1FFEF: "Proprietary B - Page 1",   # 131055
    0x1FFF0: "Proprietary B - Page 1",   # 131056
    0x1FFF1: "Proprietary B - Page 1",   # 131057
    0x1FFF2: "Proprietary B - Page 1",   # 131058
    0x1FFF3: "Proprietary B - Page 1",   # 131059
    0x1FFF4: "Proprietary B - Page 1",   # 131060
    0x1FFF5: "Proprietary B - Page 1",   # 131061
    0x1FFF6: "Proprietary B - Page 1",   # 131062
    0x1FFF7: "Proprietary B - Page 1",   # 131063
    0x1FFF8: "Proprietary B - Page 1",   # 131064
    0x1FFF9: "Proprietary B - Page 1",   # 131065
    0x1FFFA: "Proprietary B - Page 1",   # 131066
    0x1FFFB: "Proprietary B - Page 1",   # 131067
    0x1FFFC: "Proprietary B - Page 1",   # 131068
    0x1FFFD: "Proprietary B - Page 1",   # 131069
    0x1FFFE: "Proprietary B - Page 1",   # 131070
    0x1FFFF: "Proprietary B - Page 1 (last entry)",   # 131071
}


def pgn_name(pgn: int) -> str:
    return PGN_NAMES.get(pgn, f"PGN 0x{pgn:05X}")
