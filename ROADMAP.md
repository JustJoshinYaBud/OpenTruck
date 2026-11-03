# OpenTruck — roadmap

What works, and what is planned. Highest value first.

## Done

- **Protocol support**
  - J1939 decode: PGNs, NAME / address-claimed module discovery, DM1/DM2 DTC
    (SPN+FMI) decode, transport-protocol (BAM) reassembly
  - J1708/J1587 decode: full PID name + scaling tables, PID 194 fault-code
    parser, bitmap status PIDs as readable text
  - Reads J1939 and J1708 simultaneously on one connection
- **Diagnostics**
  - Fault codes from all modules in one table (active before inactive)
  - Standard fault-code clearing (J1939 DM11 + DM3, J1587 PID 195), blocked
    while the engine is running
  - Live data for ~70 common parameters (engine, transmission, brakes, ABS,
    aftertreatment/DPF/SCR/DEF, PTO, air systems), incl. regen-inhibit and
    derate reasons
  - VIN / PIN decoding, engine make/model/serial and ECU identification
  - Printable PDF diagnostic report
- **Light-duty OBD-II (2008+ cars and pickups)**
  - Auto-detected on connect (no protocol knowledge needed)
  - Live data (SAE J1979 PIDs) with the graph and unit support, confirmed /
    pending / permanent DTCs with SAE J2012 descriptions, Mode 04 clear,
    VIN + chassis make/model decoding (NHTSA vPIC), per-ECU module list
  - Maker-specific code descriptions for Ford, GM and the Chrysler family,
    scoped by the vehicle's VIN
- **Connectivity**
  - Any RP1210 adapter, auto-enumerated; 32-bit-only drivers driven through a
    bundled 32-bit helper process
  - Auto-baud (`J1939:Baud=Auto`), raw bus sniff for dead-bus diagnosis
  - Raw-CAN capture channel: everything on the wire, undecoded
- **App**
  - PySide6 GUI with dark theme, live graph, resizable panes (layout
    remembered between runs), units (metric / US / Canadian)
  - CSV data logging and raw-frame capture with replay (J1939 + J1708 + a
    raw-CAN channel that records everything on the wire, undecoded)
  - Standalone Windows installer (no Python needed on the target PC)
  - Update check against GitHub Releases

## Planned

- DM4 freeze-frame, DM5 readiness and DM6 emissions-pending read-out
- Directed request-any-PGN tooling
- More OEM fault-code tables (contributions welcome — see
  [ARCHITECTURE.md](ARCHITECTURE.md) for the override-table pattern)
- Better handling of OEM-configured / application-specific J1587 parameters
- Code signing for the installer
- CAN2 (J1939-7) support once its layout is publicly documented
