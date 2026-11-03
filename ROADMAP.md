# OpenTruck — roadmap

What works, and what is planned. Highest value first.

## Done

- **Protocol support**
  - J1939 decode: PGNs, NAME / address-claimed module discovery, DM1/DM2 DTC
    (SPN+FMI) decode, transport-protocol (BAM) reassembly
  - J1708/J1587 decode: full PID name + scaling tables, PID 194 fault-code
    parser, bitmap status PIDs as readable text
  - **Cat Data Link (CDL) decode**: CAT's proprietary machine bus, built
    from real captures — module (MID) discovery, per-module traffic stats,
    and wire-read identity strings
  - Reads J1939, J1708/J1587 and the Cat Data Link simultaneously on one
    connection (every bus the machine speaks, at once)
- **Diagnostics**
  - Fault codes from all modules in one table (active before inactive)
  - **Maker-aware code descriptions**: engine/transmission/brake tables for
    Caterpillar, Cummins, Detroit Diesel, International, Volvo/Mack, Deutz,
    Kubota, Perkins, WABCO, Bendix and Haldex. A code the maker's table cannot
    name is shown as **"Refer to OEM"** rather than guessed under the generic
    SAE name — and that rule is applied by module type for every maker.
  - **Maker-aware module naming**: a manufacturer's own source-address map is
    used when the chassis is known (International, Volvo, Mack, Kenworth,
    Peterbilt), so silent controllers are named correctly.
  - **Transmission faults reported by the engine** (Eaton Fuller Top-2) are
    labelled as transmission faults even though the engine reports them.
  - **CAT machines: identity and fault codes on demand over the Cat Data
    Link.** Each CDL controller is asked for its model, serial number,
    part number and build date (the same reads a service tool uses), and
    its fault log is read on a timer and decoded into the shared
    fault-code table with CAT's own component (CID) and failure-mode
    (FMI) vocabularies — a CDL FMI is a different table from the J1939
    one, so CAT codes are labeled correctly. Reading is request-and-
    listen only; CDL clearing is not supported (J1939-equipped machines
    use the standard clear)
  - Standard fault-code clearing (J1939 DM11 + DM3, J1587 PID 195), blocked
    while the engine is running
  - Live data for ~70+ common parameters (engine, transmission, brakes, ABS,
    aftertreatment/DPF/SCR/DEF, PTO, air systems), incl. regen-inhibit and
    derate reasons
  - **Live data parameter overrides**: OEM-specific terminology for standard
    parameters (Cummins/Detroit "ICP", Volvo/Mack "Retarder Torque",
    PACCAR "Compression Brake Torque", etc.)
  - **NOx sensor placeholders** in aftertreatment panel (SCR Inlet/Outlet NOx)
    pending proprietary ACM PGN identification
  - VIN / PIN decoding, engine make/model/serial and ECU identification
  - Printable PDF diagnostic report
- **Light-duty OBD-II (2008+ cars and pickups)**
  - Auto-detected on connect (no protocol knowledge needed)
  - Live data (SAE J1979 PIDs) with the graph and unit support, confirmed /
    pending / permanent DTCs with SAE J2012 descriptions, Mode 04 clear,
    VIN + chassis make/model decoding (NHTSA vPIC), per-ECU module list
  - Maker-specific code descriptions for Ford, GM and the Chrysler family,
    scoped by the vehicle's VIN
  - **Every standard mode 01 PID decoded**, with an offline checker
    (`check_pids.py`) that verifies each decoder against the published J1979
    scale/offset values
  - **Module identification over UDS**: after connecting, the standard
    diagnostic addresses are asked to identify themselves (read-only), and
    modules that only answer UDS are listed with their serial/part number
  - Engine identification on the Vehicle panel (displacement, cylinders,
    fuel, maker's engine code) from the VIN
- **Connectivity**
  - Any RP1210 adapter, auto-enumerated; 32-bit-only drivers driven through a
    bundled 32-bit helper process
  - Auto-baud (`J1939:Baud=Auto`) with a refusal ladder (plain / 250 / 500 /
    1 Mbit/s) and an automatic retry at each standard rate when a bus stays
    silent; adapters that support only one connection at a time (such as the
    CAT Comm Adapter 3) are detected and given exactly one, with J1708 as the
    fallback for older vehicles
  - **Connection failures are readable**: every driver return code is shown
    with its standard meaning, the adapter maker's own description and a
    plain-language hint, and a rotating error log (Help ▸ Error logs) makes
    any failure reportable by email
  - **Check Adapter** (Developer ▸ Check Adapter): opens every protocol the
    adapter's driver declares, one connection at a time, and reports which
    ones opened, what each received, and a verdict — the built-in way to tell
    a rate problem from a wiring problem from an adapter held by other
    software
  - **Windows 11 Memory-Integrity detection**: the CA3's 2016 USB driver
    is refused by Windows 11's Memory Integrity (Core Isolation) on clean
    24H2 installs; the connect error and Check Adapter say exactly which
    setting to change instead of blaming the cable
  - **Serial ELM327-class OBD-II adapters**: every present serial port is
    offered in the Connect window, the adapter is identified and its baud rate
    found automatically; FTDI/CP210x/CH340-class bridges and Bluetooth SPP are
    recognised
  - Wire-view capture channels, opened on demand while a capture runs: raw
    CAN (everything on the wire, undecoded) and, on CAT-family adapters, the
    Cat Data Link captured byte-for-byte
- **App**
  - PySide6 GUI with dark theme, live graph, resizable panes (layout
    remembered between runs), units (metric / US / Canadian)
  - **Live activity line**: what the program is doing right now — connect
    phases (which buses answered), module-identification progress, live
    buses, the CDL poll and the silent-ECU sweep, pipe-separated at the
    bottom of the window
  - CSV data logging and raw-frame capture with replay (J1939 + J1708 + the
    on-demand wire-view channels above)
  - Standalone Windows installer (no Python needed on the target PC)
  - Update check against GitHub Releases

## Planned

- **Cat Data Link: live parameters** — CDL broadcasts continuous parameter
  data that is not decoded yet; decoders will be derived from real
  captures, family by family, not guessed
- **Cat Data Link: fault-code clearing** — the documented clear command is
  not verified on enough hardware to ship; reading codes works
- DM4 freeze-frame, DM5 readiness and DM6 emissions-pending read-out
- Directed request-any-PGN tooling
- More OEM fault-code tables (contributions welcome — see
  [ARCHITECTURE.md](ARCHITECTURE.md) for the override-table pattern); most
  wanted: a DTNA body/chassis code dictionary (their source-address map and
  aftertreatment codes are already in), Allison, Meritor, PACCAR MX, Isuzu
- Better handling of OEM-configured / application-specific J1587 parameters
- Code signing for the installer
- CAN2 (J1939-7) support once its layout is publicly documented
