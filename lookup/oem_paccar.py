"""OpenTruck - PACCAR (Kenworth / Peterbilt) source-address map.

Source documents:
  * Kenworth T680/T880 Body Builder Manual (2017, 2024 updates)
  * Peterbilt Programming Guide PG034-006v6.7 (2019)
  * NHTSA-mirrored IK0800351 J1939 Source Address Information

This map records addresses explicitly documented in official PACCAR body builder
manuals and programming guides. The VECU/CECU Multiplex architecture (introduced
October 2018) uses additional chassis modules beyond the traditional setup.

Key modules:
  * **0x31 - CECU** (Cab Electronic Control Unit): Documented throughout Kenworth
    and Peterbilt manuals for J1939 signals to engine over VCAN
  * **0x21 - Body Controller**: PTO checklist requires configuration as SA 0x21
    (also referenced as 0x7D in some documentation)
  * **0x11 - VECU** (Vehicle Electronic Control Unit): Newer architecture trucks
    (post-Oct 2018) with MX engines use VECU for chassis control
  * **0x00 / 0x03 / 0x0B** are standard J1939 preferred addresses

Chassis Modules (CMP/CMS):
  * CMP (Chassis Module Primary): Standard on all VECU system trucks, controls
    exterior lighting, fuel level, electric-over-air functions
  * CMS (Chassis Module Secondary/SCM/OCM): Optional on trucks with lift axles,
    snow plow, or Body Builder CAN (B-CAN)

Deliberately NOT included: addresses that could not be pointed at specific
official documentation. Unknown addresses fall back to the generic J1939-71
table.

Only used when the chassis is identified as PACCAR/Kenworth/Peterbilt and the
module never claims an address of its own.
"""

PACCAR_ADDRESSES: dict[int, str] = {
    0x00: "Engine Control Module (ECM)",
    0x03: "Transmission Control Module (TCM)",
    0x05: "Gear Shift Electronic Control Unit (GSECU)",
    0x0B: "ABS / EBS controller",
    0x0F: "Engine Brake (EB)",
    0x11: "Vehicle Electronic Control Unit (VECU)",
    0x17: "Instrument Cluster (IC)",
    0x21: "Body Controller",
    0x31: "Cab Electronic Control Unit (CECU)",
}
