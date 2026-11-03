# OpenTruck — architecture overview

A short, public-facing summary of how the code fits together. Field
observations about the wire protocols are collected in [`NOTES.md`](NOTES.md).

## Big picture

OpenTruck is a Windows desktop tool (Python 3, PySide6) that speaks SAE J1939
and J1708/J1587 to heavy-duty vehicle and off-highway machine ECUs, CAT's
proprietary Cat Data Link to CAT machine controllers, and light-duty OBD-II
(SAE J1979 over ISO 15765-4) to 2008+ cars and pickups, through any RP1210
diagnostic adapter (the buses are auto-detected on connect). It is
read-mostly: it discovers modules, decodes fault codes, shows live data,
and performs the standard DM11/DM3, J1587 PID-195 and OBD-II Mode 04
fault-code clears. On the Cat Data Link it sends read requests only
(identity and fault-code reads); CDL clearing is not supported. It does not
touch proprietary programming, ECM security, or calibration.

## Layers

```
RP1210 adapter (DLL, via ctypes)          rp1210.py
        |      (32-bit-only drivers go through OpenTruckBridge32.exe,
        |       an out-of-process helper:      rp1210_bridge.py)
        v
FrameSource (live / replay / simulator)   framesource.py, simsource.py
        |   decoded frames on a background thread
        v
Session (state: modules, DTCs, live data) reader.py
        |   J1939Session + J1708Session + CdlSession merged via
        |   CombinedSession (each bus keeps its own key range)
        v
decoders  (modules/)                      j1939.py, j1708.py, cdl.py,
        |                                 livedata.py
        |   PGN/PID -> (name, value, unit), DM1/DM2 -> SPN+FMI,
        |   CDL MID/IID -> module + identity, PID 0x0082 -> CID+FMI
        v
lookup tables  (lookup/)                  spn.py, pid1587.py, pgn.py,
        |                                 vin.py, manufacturers.py
        v
OEM overrides (optional, brand-specific)  lookup/oem.py + lookup/oem_*.py
        |
        v
GUI (PySide6, loads MainWindow.ui)        app.py
```

## Key points

- **Adapter-agnostic protocol layer.** `j1939.Frame` carries
  `pgn / source / destination / priority / data`, so decoding never depends on
  the adapter. Three interchangeable sources exist: live RP1210, replay of a
  captured `.log` file, and a built-in simulator (so development needs no
  hardware).
- **Every bus at once.** A live connect opens J1939, J1708 and — on
  CAT-family adapters — the Cat Data Link together (adapters that support
  only one connection at a time get a single client, J1939 first with J1708
  as the fallback). J1708 module keys are offset (`0x4000 + MID`) and CDL
  keys again (`0x8000 + MID`) so all three share one session/state model
  without colliding. A further receive-only raw-CAN channel exists purely
  so a capture can record the undecoded CAN wire; it opens on demand while a
  capture runs and is never used for decoding.
- **Cat Data Link.** `modules/cdl.py` decodes CDL traffic
  (`[MID][destination][IID][data]`), discovers controllers (MIDs), and —
  because most machines have no onboard poller to ask for anything — sends
  read requests itself: identity (model / serial / part number / build date)
  once per controller and the fault log (PID 0x0082) every 10 s, one
  request per 400 ms tick. The tool identifies itself as MID 11
  ("Communication Adapter"); fault codes decode against CAT's own CID and
  FMI tables (`lookup/oem_cat.py` — the CDL FMI vocabulary is deliberately
  separate from the J1939 FMI table). Unrecognized values are kept as raw
  entries rather than guessed; everything shipped was derived from real
  captures and hardware sessions.
- **Layered code resolution.** Fault codes and live parameters resolve
  OEM-specific tables first, then the generic SAE tables, falling back to
  "Refer to OEM". That fallback is decided by **module type**: engine,
  transmission, aftertreatment and brake controllers may use the generic SAE
  name (those parameters are standard on every brand), while body / chassis /
  cab controllers — where makers routinely reuse standard numbers for their own
  signals — report "Refer to OEM" unless the maker's table names the code. OEM
  tables contain only short factual names; verbatim OEM prose is deliberately
  kept out of the repository.
- **Live data overrides.** The `lookup/oem.py` registry includes a `live`
  dictionary per OEM that maps canonical parameter names to maker-specific
  display text. These are **display-only** — the canonical name remains the
  data key, CSV column header, and graph identifier. Only the GUI shows the
  OEM's preferred terminology.
- **Module naming.** A module is named from its address-claim NAME, then from
  its Component Identification, then from the chassis maker's own
  source-address map (published in body-builder documentation), and only then
  from the standard J1939 preferred-address table — so a controller that never
  identifies itself still gets a sensible role.
- **GUI state is external.** The window layout lives in `MainWindow.ui`
  (editable in Qt Designer, loaded at runtime) and `app.py` wires widgets by
  `objectName`. User preferences (connection, units, log folder, and saved
  GUI layout: splitter positions and table column widths) persist as JSON in
  `%APPDATA%\OpenTruck\config.json`.
- **No hardware needed to develop.** `python app.py` runs a simulator
  fabricating a small J1939 network; `--replay <file>` replays a capture.
- **Update check.** The GUI queries the GitHub Releases API (see
  `updater.py`) silently on launch and on demand.

## Scope and data sources

Decode tables cover standardized SAE J1939 / J1587 identifiers, the Cat
Data Link MID/CID/FMI identifiers (as published in CAT's diagnostic code
listings), plus manufacturer-published fault-code listings for Bendix,
Caterpillar, Cummins, Haldex, John Deere and WABCO. The code is licensed
under the PolyForm Noncommercial License 1.0.0 (free for noncommercial use;
commercial use requires a separate license from the author); the SAE
identifiers used are publicly standardized values.
