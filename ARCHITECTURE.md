# OpenTruck — architecture overview

A short, public-facing summary of how the code fits together. The full
internal handoff notes live outside the repository.

## Big picture

OpenTruck is a Windows desktop tool (Python 3, PySide6) that speaks SAE J1939
and J1708/J1587 to heavy-duty vehicle and off-highway machine ECUs through any
RP1210 diagnostic adapter. It is read-mostly: it discovers modules, decodes
fault codes, shows live data, and performs the standard DM11/DM3 and J1587
PID-195 fault-code clears. It does not touch proprietary programming, ECM
security, or calibration.

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
        |   J1939Session + J1708Session merged via CombinedSession
        v
decoders  (modules/)                      j1939.py, j1708.py, livedata.py
        |   PGN/PID -> (name, value, unit), DM1/DM2 -> SPN+FMI
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
- **Dual bus support.** A live connect opens J1939 and J1708 at once.
  J1708 module keys are offset (`0x4000 + MID`) so they can share one
  session/state model without colliding with J1939 source addresses.
- **Layered code resolution.** Fault codes and live parameters resolve
  OEM-specific tables first, then the generic SAE tables, falling back to
  "Refer to OEM". OEM tables contain only short factual names; verbatim OEM
  prose is deliberately kept out of the repository.
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

Decode tables cover standardized SAE J1939 / J1587 identifiers plus
manufacturer-published fault-code listings for Bendix, Caterpillar, Cummins,
Haldex, John Deere and WABCO. The code is licensed under the PolyForm
Noncommercial License 1.0.0 (free for noncommercial use; commercial use
requires a separate license from the author); the SAE identifiers used are
publicly standardized values.
