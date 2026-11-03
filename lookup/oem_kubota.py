"""OpenTruck - Kubota engine fault-code table.

SPN+FMI -> short description, taken from the OEM-derived **Kubota DTC list for
V3800-CR-T-E4 / V3307-CR-T-E4 / V2607-CR-T-E4** (12 V system, common rail).
The list is printed as "P-code | SPN | FMI | J1939 name", which is exactly the
mapping we need: the bus carries the SPN/FMI pair, so the P-code column is only
used to cross-check.

Only short factual descriptions are stored; the FMI failure phrase is added
generically at display time (SAE J1939-73), so no authored prose is copied.

Most of these SPNs are standard SAE numbers (Kubota's wording is close to the
generic name). The real value is Kubota's **proprietary 52xxxx band**, which the
generic tables cannot name at all - EGR actuator faults, the air-heater relay,
the "pump seizing" pair, the CAN frame-error family and the parked-regeneration
timeout.

Scoped to Kubota only (manufacturer code 416), so it never leaks.
"""

# (SPN, FMI) -> short description
KUBOTA_SPN_FMI: dict[tuple[int, int], str] = {
    # --- standard SPNs, Kubota wording ------------------------------------
    (91, 2): "Accelerator pedal sensor 1/2 correlation",
    (100, 1): "Oil pressure switch",
    (102, 3): "Boost pressure sensor - high",
    (102, 4): "Boost pressure sensor - low",
    (108, 3): "Barometric pressure sensor - high",
    (108, 4): "Barometric pressure sensor - low",
    (110, 0): "Engine coolant temperature - overheat",
    (157, 3): "Rail pressure sensor - high",
    (157, 4): "Rail pressure sensor - low",
    (168, 3): "Battery voltage - high",
    (168, 4): "Battery voltage - low",
    (174, 0): "Fuel temperature - high",
    (174, 4): "Fuel temperature sensor - low",
    (190, 0): "Engine speed - overrun",
    (628, 2): "ECU flash ROM (program memory) error",
    (636, 2): "Engine position sensor - NE pulse count error",
    (636, 7): "Engine position sensor - NE/G phase shift",
    (636, 8): "Engine position sensor - no NE pulse",
    (651, 3): "Injector cylinder #1 - open circuit",
    (652, 3): "Injector cylinder #2 - open circuit",
    (653, 3): "Injector cylinder #3 - open circuit",
    (654, 3): "Injector cylinder #4 - open circuit",
    (723, 2): "Camshaft position sensor - pulse count error",
    (723, 8): "Camshaft position sensor - no pulse",
    (1077, 2): "ECU fuel injection pump controller (CPU fault)",
    (1239, 1): "Fuel leakage (high-pressure fuel system)",
    (1347, 4): "SCV drive system (fuel pump pressurising assembly)",
    (3242, 3): "DPF intake gas temperature sensor - high",
    (3242, 4): "DPF intake gas temperature sensor - low",
    (3246, 3): "DPF outlet gas temperature sensor - high",
    (3246, 4): "DPF outlet gas temperature sensor - low",
    (3509, 3): "Sensor supply voltage 1 - high",
    (3509, 4): "Sensor supply voltage 1 - low",
    (3510, 4): "Sensor supply voltage 2 - low",
    (3701, 0): "DPF status - PM accumulation level 5",
    (3701, 15): "DPF status - PM accumulation level 3",
    (3701, 16): "DPF status - PM accumulation level 4",
    (4765, 3): "DOC intake gas temperature sensor - high",
    (4765, 4): "DOC intake gas temperature sensor - low",
    (1485, 2): "ECM main relay - stuck closed",
    # --- Kubota proprietary band (52xxxx) ---------------------------------
    (523523, 3): "Injector circuit - short to +B (cylinders 1&4)",
    (523523, 4): "Injector circuit - short to ground (cylinders 1&4)",
    (523524, 2): "Injector circuit - open (cylinders 2&3)",
    (523524, 4): "Injector circuit - short to ground (cylinders 2&3)",
    (523525, 1): "Injector charge voltage - low",
    (523527, 2): "ECU CPU monitoring IC fault",
    (523538, 2): "ECU QR data read error",
    (523539, 2): "High-pressure pump seizing 1",
    (523540, 2): "High-pressure pump seizing 2",
    (523543, 2): "Accelerator position sensor - CAN signal error",
    (523544, 4): "Air heater relay drive circuit - ground short",
    (523547, 2): "CAN2 bus off",
    (523548, 2): "CAN-KBT frame error",
    (523572, 4): "EGR position sensor failure",
    (523574, 3): "EGR actuator - open circuit",
    (523575, 7): "EGR actuator - valve stuck",
    (523576, 2): "EGR DC motor - overheat",
    (523577, 2): "EGR DC motor temperature sensor failure",
    (523578, 2): "No communication with EGR",
    (523580, 2): "Intake throttle feedback error",
    (523590, 16): "Parked regeneration - time out (low DPF temperature)",
    (523591, 2): "CAN CCVS frame error (parking switch / vehicle speed)",
    (523592, 2): "CAN CM1 frame error (regeneration switch)",
    (523593, 2): "CAN DDC1 frame error (transmission)",
    (523594, 2): "CAN ETC2 frame error (neutral switch)",
    (523595, 2): "CAN ETC5 frame error (neutral switch)",
    (523596, 2): "CAN TSC1 frame error",
    (523598, 2): "CAN EBC1 frame error",
    (523599, 0): "All exhaust temperature sensors failed",
    (523601, 0): "Exhaust gas temperature - high after emergency high-temp DTC",
    (523604, 2): "CAN1 bus off",
}
