# Changelog

All notable changes to OpenTruck. A version is `MAJOR.MINOR.PATCH` plus a
build counter, and the full number - `0.2.0.133` - is what the window title,
the installer filename (`OpenTruckSetup-0.2.0.133.exe`) and the in-app update
check all use. Each entry below is titled with the full version that shipped.

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