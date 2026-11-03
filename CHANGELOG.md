# Changelog

All notable changes to OpenTruck. A version is `MAJOR.MINOR.PATCH` plus a
build counter, and the full number - `0.2.0.133` - is what the window title,
the installer filename (`OpenTruckSetup-0.2.0.133.exe`) and the in-app update
check all use. Each entry below is titled with the full version that shipped.

## [0.4.0.161] — 2026-11-15

Field-test fixes for the J1587 bit-mapped status PIDs.

### Fixed

- **Air Conditioner System Status #2 (J1587 PID 25)** now decodes as four
  2-bit states — compressor discharge high pressure, compressor discharge
  very high pressure, compressor suction low pressure and evaporator
  temperature — instead of a raw number. On a live truck the reported raw
  63 is the ECM marking those states "not available"; it used to render as
  an unexplained integer.
- **Engine Retarder Switches Status (J1587 PID 40)** no longer breaks the
  live-data view on retarder-equipped trucks: the retarder level is a 4-bit
  field (0-8 retarded cylinders, error, not available) but was decoded as
  a 2-bit status, so level values above 3 raised an error. It now decodes
  to the standard's wording (e.g. "6 cylinders").
- Bit-mapped PID decoding is defensive: a field wider than its layout
  expects can no longer raise, it shows its raw value instead.

## [0.4.0.160] — 2026-11-15

The Eaton transmission and live-data expansion release.

### Added

- **Eaton Cummins Endurant transmission fault codes.** The proprietary
  transmission — shift-rail positions, shift-rail solenoids, clutch
  solenoids and actuators, transmission oil temperature/pressure and TCM
  operation SPNs — are now named from the Eaton Cummins troubleshooting
  guides, covering both the Endurant HD and Endurant XD fault-code sets.
  Previously these degraded to "Refer to OEM".
- **Eaton UltraShift PLUS / Fuller Advantage fault codes.** The Gen4 family
  fault set is included, and the correct Eaton table is chosen from the
  transmission's Component ID model string — the Endurant and UltraShift
  families reuse several SPN numbers with different meanings, so both are
  decoded correctly instead of mislabelled.
- **More live data from standard J1939 broadcasts.** Newly decoded: torque
  converter ratio and clutch/converter input speed (ETC8), engine throttle and
  fuel actuator commands (TFAC), high-resolution engine temperatures (ET3),
  turbocharger wastegate drives (TCW), rated engine power and speed (EEC4),
  engine fan speed (FD), adaptive cruise speeds (ACC1), aftertreatment
  air-control pressures (AT1AC1), bank-2 aftertreatment temperatures
  (AT2IMG/AT2OG2) and tachograph speeds (TCO1).
- **New J1587 decoders.** Accelerator position #2 (PID 29) and the parking
  brake switch status (PID 70) now decode to values and readable text.
- **Live-data coverage audit tool.** `check_live_coverage.py` reads a capture
  and reports, per module, which live-data PGNs appeared and which still have
  no decoder — separating manufacturer-proprietary PGNs (which need OEM
  documentation) from standard ones that can be added next.

## [0.3.0.153] — 2026-11-13

### Fixed

- **Diagnostic reports generate again.** A report listing any fault code —
  including every Cat Data Link code — failed to build. Reports now include
  them, with their CID/FMI descriptions.
- **Selecting a Cat Data Link controller no longer stalls the display.**
  The warning-lamp refresh expected every module to carry lamp state, which
  CDL controllers don't have; selecting one threw on every refresh tick and
  stopped the live view from updating.
- **Status notices stay visible long enough to read.** A notice shown in
  the status line was being overwritten by the activity refresh a fraction
  of a second later; notices now persist for their full display time and
  expire on their own.

## [0.3.0.152] — 2026-11-13

Follow-up to 0.3.0.151 on a Cat wheel loader.

### Fixed

- **Cat Data Link fault codes now fill in.** The fault-code table listed the
  right number of rows for CDL controllers but every cell was blank: a
  CDL controller has no J1939 identity object, and the table's module
  lookup assumed one, so the render stopped after creating the rows.
  CDL codes now show their module, bus, CID, FMI, description and status.
  The same assumption could also break the live-data table when a CDL
  module was selected in the component list; fixed as well.
- **The status bar is one line again.** Notices (ECU acknowledgements,
  clear results, "Connected", "Disconnected", ...) and the live
  activity line now render into a single status element on the left —
  notices first, expiring after a few seconds, then the activity parts.

## [0.3.0.151] — 2026-11-13

Hotfix roll-up: the live-data table froze, the status line told two
stories, and slow connects still looked like hangs on some adapters.

### Fixed

- **Live-data values no longer freeze.** The live-data table stopped
  updating its values while the graph kept moving — a regression that
  had been in every build for a while. The table now redraws whenever a
  value changes, on every bus (J1939, the legacy J1708/J1587 link and
  OBD-II; Cat Data Link live parameters are not decoded yet, so CDL
  modules show their identity and fault codes first and live data is
  coming).
- **One coherent status line.** The module count used to appear twice —
  a transient "N module(s) discovered" message on one side, the activity
  line on the other — and could disagree. The activity line is now the
  single source: connect narration, bus states, module counts, polls
  and sweeps, in one place, always visible.
- **The module count matches what you can see.** "N modules identified"
  only counted modules with a full network-claimed identity, so it read
  "2" while the component list named six. A module the program can name
  — by its claimed identity, its component make, or its standard network
  address — now counts as identified, and the number agrees with the
  component list.
- **Connect narration on every adapter.** The activity line now narrates
  the connect as it happens — which protocol is being probed, which
  answered, which found nothing — for RP1210 adapters (CAT Comm Adapter,
  Nexiq, vLinker and friends) exactly as it already did for ELM327
  cables, and the steps stay visible until they succeed or time out
  instead of flashing for a moment.
- **Adapters plugged in after the program starts now appear in the
  Connect window without a restart** — a Refresh button, plus an
  automatic refresh every 3 seconds.
- **Menu hover no longer clobbers status text.** The activity line is a
  permanent element of the status bar, so tooltips and hover help can
  no longer overwrite it.
- **Upgraders from builds before the what's-new popup existed now see
  the popup too.**

## [0.3.0.146] — 2026-11-13

The Cat Data Link release: identification and fault codes now come from
every bus a machine speaks - J1939, the legacy J1708/J1587 link, and
CAT's proprietary Cat Data Link - all at once, live-verified on real
machines (a Cat C6.6 engine and a Cat 938 wheel loader).

### Added

- **Cat Data Link support: CAT machines' controllers are now visible.**
  The machine controllers of a CAT machine (instrument display,
  transmission, telematics, implement - and the engine on many machines)
  live on CAT's proprietary Cat Data Link and never appear on J1939.
  Connecting a CAT-family adapter now listens on **every bus the machine
  speaks at once** - J1939, the legacy J1708/J1587 link and the Cat Data
  Link - so one connect shows both the engine (J1939) and the machine
  controllers (CDL), each with its own bus indicator in the vehicle panel.
- **CAT controllers identify themselves on demand.** Every CDL module the
  program discovers is asked for its model, serial number, part number
  and build date.
- **CAT fault codes are read live.** Each CDL controller's fault log is
  read on a timer and decoded into the fault-code table with CAT's own
  component (CID) and failure-mode (FMI) vocabularies - CDL failure modes
  are a different table from the J1939 one, so codes are labeled correctly
  for CAT equipment. Reading is a request-and-listen cycle only.
- **Live activity line.** The bottom of the window now shows what the
  program is doing in real time, pipe-separated: which buses answered
  during connect ("waiting for data on: j1939, j1708, cdl"), how many
  modules are identified, which buses are live, the CDL poll progress and
  the silent-ECU sweep - so a slow connect reads as work in progress, not
  a frozen app.
- **Light-duty OBD-II (2008+ cars and pickups) through a consumer ELM327
  cable.** The Connect window lists every serial port the PC has,
  identifies the adapter automatically - by USB chip (FTDI, CP210x,
  CH341) and by name (vLinker, OBDLink, Vgate and other ELM327 clones) -
  and finds its baud rate, so no driver setup is needed and unbranded
  clones work. SAE J1979 live data, confirmed / pending / permanent
  trouble codes with SAE J2012 descriptions plus maker-specific code
  wording for Ford, GM and the Chrysler family scoped by the vehicle's
  VIN, Mode 04 code clear, VIN + chassis make/model decoding (NHTSA vPIC),
  and a per-ECU module list. Auto-detected when a heavy-duty connect
  finds no bus, and available directly on RP1210 adapters too.
- **Every standard Mode 01 PID is decoded** - 107 decoders, including the
  variable-length blocks (fuel system status, O2 sensor readings,
  secondary trims, torque data, exhaust temperatures, DEF level) - and
  every decoder is verified offline against the published J1979
  scale/offset values by a bundled checker, so transcription errors
  cannot ship.
- **Modules that only speak UDS are now found.** After connecting, the
  standard diagnostic addresses are asked to identify themselves
  (read-only); controllers that never appear in generic OBD but answer
  UDS are listed with their serial and part numbers where the module
  provides them.
- **Engine identification from the VIN** - displacement, cylinder count,
  fuel type and the maker's engine sales code on the Vehicle panel
  (NHTSA vPIC).

### Fixed

- **Connection errors now explain when Windows itself is the problem.**
  Windows 11's Memory Integrity setting can silently refuse an older
  adapter's USB driver (the Caterpillar Comm Adapter 3's 2016 driver is a
  known case) - until now that surfaced as a generic "adapter not
  responding" message suggesting cable fixes. Selecting a Caterpillar
  adapter now warns before connecting, and the connect error, the
  diagnostic log and the Check Adapter report say which device Windows
  blocked and exactly which setting to change, instead of blaming the
  cable.
- **The Caterpillar Comm Adapter 3's first connection is no longer
  rejected.** The adapter's driver hands out client number 0 for its
  first session, which the RP1210 spec allows but the connection logic
  treated as an error - so the very first protocol attempt failed and was
  retried, leaking a driver session each time. Client numbers now cover
  the full spec range.

### Added

- **Lighter on the adapter while capturing.** The optional wire-view
  channels now open only while a raw capture is running (Developer ▸ Start
  Capture) and close when it stops, instead of being open for the whole
  session - one fewer connection for an adapter driver to refuse. Captures
  still contain the undecoded wire (transport handshakes, proprietary and
  other tools' traffic) exactly as before, and on CAT-family adapters they
  can now also include the Cat Data Link - captured byte-for-byte, ready
  for the CAT machine-controller work that follows.
- **Adapter commands are now sent per data link.** The J1939 address-claim
  command is only issued on a J1939 connection; older drivers of adapters
  that also speak J1708 or the Cat Data Link are no longer asked for a
  service their protocol does not have. Adapters driven through the bundled
  32-bit helper now also get the same initial setup on J1708 as 64-bit
  drivers always did - previously a J1708 connection through the helper
  could come up silent.
- **Check Adapter** (Developer ▸ Check Adapter): tries, one connection at a
  time, every protocol your adapter's driver declares - J1939 at each rate,
  raw CAN at each rate, J1708 and any maker data link - and reports which ones
  opened, what each one received, and a plain-language verdict (wrong baud?
  dead bus? another program holding the adapter?). The full table is written
  to the error log and to a capture file you can send in, so a stubborn vehicle
  can be diagnosed without a second trip.
- **One connection at a time** for adapters whose driver does not support
  several simultaneous connections - the Caterpillar Comm Adapter 3 is one.
  OpenTruck now detects this from the driver and opens only the connection it
  needs (with J1708 as the fallback for older vehicles), instead of asking for
  three connections that could interfere with each other. A Preferences ▸
  Connection switch can force the same behaviour on any adapter, which is
  also the thing to try when an adapter connects but a vehicle shows nothing.
- Adapters that hold the tool's bus address between sessions are now told to
  give it back on disconnect - the classic "connected once, then never again
  until the cable was unplugged" failure.

### Fixed

- **The tool's identity on the vehicle's J1939 network was wrong.** When
  claiming the standard diagnostic-tool address, the tool now presents the
  identity the standard requires for that address. It previously introduced
  itself as a different kind of device (twice, with two different
  identities), which vehicles that police their network - or other
  diagnostic tools already on the truck - can react badly to. This is a
  likely contributor to vehicles that connect fine in CAT ET or JPRO but
  not in OpenTruck.
- **A clearer failure when the 32-bit adapter helper cannot run.** Some
  adapters (including the CAT Comm Adapter 3) are driven by a bundled
  helper program; if Windows Smart App Control or antivirus blocks that
  helper, the failure now says so - previously it read as an adapter fault.
- **Adapter error codes were being mistaken for a connection.** Drivers
  report failures as codes in a fixed range; any adapter answering with one of
  those codes could look "connected" for a moment and then fail with a
  meaningless invalid-client error, hiding the real reason (device in use,
  protocol refused, hardware unplugged). Every failure now shows the number,
  its standard meaning, the adapter maker's own description, and what to do
  about it.
- **32-bit drivers reported bare error numbers.** Adapters driven through the
  bundled 32-bit helper (such as the CAT Comm Adapter 3) lost the maker's
  error description; it is now included with every failure, the same as
  64-bit drivers.