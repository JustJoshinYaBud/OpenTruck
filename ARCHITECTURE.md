# OpenTruck — architecture overview

A short, public-facing summary of how the code fits together.

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
OEM overrides (optional, brand-specific)  lookup/oem.py (registry),
        |                                 lookup/oem_<brand>.py (identity +
        |                                 ONE fault-code table per brand)
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
  once per controller, the fault log (PID 0x0082) every 10 s, and CAT's
  documented engine live parameters (speed, coolant, oil pressure, battery
  voltage, hourmeter, inlet manifold) every few seconds, one request per
  400 ms tick. Values use CAT's published identifier scales and MSB-first
  byte order; an unknown parameter is never named. The tool identifies
  itself as MID 11 ("Communication Adapter"); fault codes decode against
  CAT's own CID and FMI tables (`lookup/oem_cat.py` — the CDL FMI vocabulary is deliberately
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
- **Fault-code tables are ONE literal per brand.** A manufacturer publishes
  its diagnostic list for one engine family at a time, but the differences are
  wording, not different faults - so each brand keeps **one pure table** in
  `lookup/oem_<brand>.py`: `<BRAND>_SPN_FMI`, nothing else. Once the brand is
  known, exactly one table is read; a code outside it falls back to the
  generic SAE name. Table files carry no provenance, no source-document
  references and no merge commentary: just the data.
- **Live data overrides.** The `lookup/oem.py` registry includes a `live`
  dictionary per OEM that maps canonical parameter names to maker-specific
  display text. These are **display-only** — the canonical name remains the
  data key, CSV column header, and graph identifier. Only the GUI shows the
  OEM's preferred terminology.
- **Module naming.** A module is named from its address-claim NAME (the
  complete J1939-71 global name-function table, plus the industry-group/
  vehicle-system specific functions where the NAME carries that context),
  then from its Component Identification, then from the chassis maker's own
  source-address map, and only then from the standard J1939 preferred-address
  table — so a controller that never identifies itself still gets a sensible
  role.
- **Offline vehicle identification.** The frame-stamped identifier is shown
  as a VIN or a machine PIN based on what the wire says (a 13-character
  identifier is always a PIN; a 17-character one is a PIN when the bus is
  an off-highway machine). Make names come from the NHTSA world manufacturer
  identifier table and the AEM off-highway manufacturer-code list, chosen by
  machine/truck context. Where the VIN carries them, the engine model and
  the vehicle model/series (e.g. "F-750", "F-Series Super Duty") are decoded
  from the public NHTSA vPIC VIN patterns; when a VIN declares no engine
  model, the engine line falls back to its displacement, cylinder count and
  fuel type. The patterns cover North American highway trucks (maker-specific
  VIN positions, e.g. Kenworth/Peterbilt/Freightliner/International) as well
  as bus, coach and fire/emergency chassis, for model years 2001 and newer
  (older vehicles fall outside the heavy-duty scope). Model years are
  reconciled with the manufacturer's VIN schema ranges so pre-2010 trucks
  are not shifted a cycle. All of this is offline - the app makes no
  network requests except the update check.
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
Data Link MID/CID/FMI identifiers, plus manufacturer fault-code
identifiers for Bendix, Caterpillar, Cummins, Haldex, John Deere and
WABCO. Vehicle-identification tables are generated from public sources:
the NHTSA vPIC standalone database (public domain, a U.S. federal government
work) for manufacturer identifiers and VIN model/engine patterns, and the AEM
ISO 10261 World Manufacturer Code public record for off-highway maker codes.
The code is licensed under the GNU General Public License, version 3
or (at your option) any later version (GPL-3.0-or-later); the SAE identifiers
used are publicly standardized values.
