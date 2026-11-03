# Changelog

All notable changes to OpenTruck. Versions follow `MAJOR.MINOR.PATCH`; the
installer filename and window title append a build counter
(`OpenTruckSetup-0.2.0.85.exe`), which is what the in-app update check
compares.

## [0.2.0] — 2026-11-05

The "works on more than one kind of truck" release: older J1708 vehicles,
light-duty OBD-II vehicles, and a much deeper aftertreatment/OEM-code story.

### Added

- **OBD-II support (2008+ cars and light/medium pickups)** over the 16-pin
  DLC, auto-detected when a heavy-duty connect finds no bus: SAE J1979 live
  data, confirmed/pending/permanent DTCs with SAE J2012 descriptions, Mode 04
  clear, VIN + chassis decode (NHTSA vPIC), per-ECU module list, and
  maker-specific code descriptions for Ford, GM and the Chrysler family
  scoped by the vehicle's VIN.
- **Aftertreatment panel** (Tools ▸ Aftertreatment): DOC/DPF gas
  temperatures, inlet/outlet pressures (differential computed), DEF level and
  temperature, dosing, soot/ash load and regeneration state, grouped by
  category.
- **ABS panel** (Tools ▸ ABS): per-wheel speeds, ABS/ATC configuration parsed
  from the component ID, wheels-reporting count, ABS/EBS/trailer-ABS status
  and the controller's active/stored code counts.
- **Totals & Counters panel** (Tools ▸ Totals and Counters): engine/PTO/
  vehicle hours, revolutions, odometer and trip distance, lifetime/trip fuel,
  regeneration counts and time, vehicle weight.
- **Computed live values**: fuel economy (instant and average), boost (gauge),
  calculated torque and power, derate percentage, average road speed, idle
  percentage.
- **OEM fault-code tables** for Caterpillar, Cummins, Detroit Diesel,
  Navistar/International, WABCO, Bendix, Haldex, Volvo/Mack and John Deere,
  applied only to that maker's modules. Unresolved codes read
  "Refer to OEM" instead of a misleading generic name.
- **DPF regeneration status and gas-temperature decoders**, including the
  regen-inhibit reason where the ECM reports it.
- **J1708 identification and lossless capture**: VIN/component/software ID
  over J1587, byte-exact raw capture that replays faithfully, and J1587
  fault-code clearing.
- **OBD-II mode now logs and captures too**: CSV logging of per-ECU live
  values, and a raw CAN capture of everything on the DLC (including other
  modules' chatter) for later analysis.
- **Air-path live data**: air inlet pressure, air-filter differential
  pressure and particulate-trap inlet pressure are now decoded from IC1.
- **More live readings**: fuel level, throttle position, cruise-control set
  speed and the cruise brake switch.
- **Kubota engine codes**: 71 fault codes for the common-rail V3800/V3307/V2607 families, including Kubota's private 52xxxx band (EGR actuator, air-heater relay, pump-seizing pair, CAN frame errors, parked-regen timeout) that the generic tables cannot name.
- **Perkins engine codes**: the monitored items and event codes documented in Perkins' official application manual (coolant, oil, overspeed, NRS temperature, DEF level and SCR inducement).
- **Deutz engine codes**: 77 fault codes named from Deutz's own published DTC lists (EMR5 / Bosch MD1), including aftertreatment, DEF and dual-ECU faults.
- **Eaton Fuller Top-2 transmission faults**: on trucks where the engine ECM drives the splitter/lockout solenoids, those codes are now named for what they are — "Transmission (Eaton Fuller Top-2): Shift Solenoid or Lockout Solenoid" — even though the engine reports them. Only applied when a transmission is actually present, so an engine's own meaning for the same code is preserved otherwise.
- **Maker wording for live data**: a module's own vocabulary can now be shown
  for a decoded parameter (e.g. Caterpillar's "Clean Gas Induction" instead of
  EGR, Cummins/Detroit Diesel's "Intake Charge Pressure", Volvo/Mack's "Retarder
  Torque", PACCAR's "Compression Brake Torque", and Navistar's battery voltage
  is now reported correctly even though it arrives in the non-standard field).
- **Per-engine exhaust-temperature labelling** for the aftertreatment panel:
  neutral, SPN-identified labels by default, with confirmed per-engine names
  where they are known (and maker wording such as Caterpillar's "Clean Gas
  Induction").

### Improved

- **Fault table** now shows module, source address, SPN, FMI, description,
  status and troubleshooting type, with OEM-aware descriptions, and lists all
  active codes before all inactive ones.
- **PDF report** redesigned: vehicle identification, components with serial
  and software ID, engine totals and lamp states, and fault tables grouped by
  module.
- **Update check** reads the full release list (so pre-releases and release
  naming variations are handled), compares against the full installed version
  including the build number, and a manual check now always reports a result —
  up to date, update available, or couldn't connect — instead of failing
  silently.
- **Units** convert at display time (Canadian, metric, US customary), so
  switching them updates values already on screen. **Canadian is now the
  default unit system** and is listed first in Preferences.

### Added

- **Mack / Volvo depth**: 65 engine and aftertreatment codes now carry the
  maker's own parameter wording (e.g. "Camshaft Position Sensor (CMP)"), taken
  from Volvo Group's official 2010-emissions DTC guide. Applied to both Volvo
  and Mack MP engines and to nothing else.
- **Detroit Diesel depth**: 11 more official SPN/FMI entries (DEF circuit,
  EGR learn-cycle, idle-smoothness misfires, cam/crank correlation, reverse
  rotation).

### Changed

- **Fault table shows the protocol instead of the address**: the second column is
  now **Protocol** (J1939 / J1708 / ISO 15765 in OBD mode) rather than `0x0B`,
  and the component list shows `J1939` / `J1708` before the module name. The
  numeric address is still available as a tooltip.

- **More maker-specific source-address maps** (Volvo, Mack, Kenworth, Peterbilt)
  from the manufacturers' own body-builder manuals, so a module that never
  identifies itself is named correctly for that chassis — e.g. Volvo's 0x3D
  aftertreatment module, 0x31/0x37 cab interface, 0xEE telematics gateway;
  Mack's gear-shift ECU on 0x05; PACCAR's cab electrical control unit on 0x31.
- **Maker-specific source-address maps**: when the chassis is identified (from
  the VIN), a manufacturer's own address map is used instead of the generic
  table — e.g. on an International, 0x15 reads "Front HVAC Control Head" rather
  than "Suspension - Drive Axle #1", and 0x28/0x55/0xA0 name the VID/DID display,
  the aftertreatment control module and the OnGuard radar. International is the
  first map; the standard table remains the fallback for every other vehicle and
  for modules that identify themselves.
- **Module role names from the source address** now follow the full SAE J1939-71
  preferred-address table (0x00 Engine #1 … 0x27 Management Computer, plus the
  off-board tool). This is only used when a module never claims an address, so
  identification from the NAME or Component ID still takes precedence.

- Standard SPN names added for 25 widely-used codes (injectors, ECM/controller,
  crank/cam, injection control pressure, aftertreatment fuel pressure and
  injectors, water-in-fuel sensor), so those faults no longer fall back to
  "Refer to OEM".
- The aftertreatment panel was trimmed to the reference parameter set.

- The module list only shows controllers that have something to report: a
  module is listed when it can be identified, when it broadcasts live data, or
  when it has fault codes. Unknown bus addresses that report nothing are
  ignored (they are still polled, so one that starts answering becomes visible
  on its own). The PDF report's component table follows the same rule.

### Fixed

- OBD-II live values failed to populate and refreshed slowly on busy DLCs.
- OBD-II graph was not fed, and the Mode 04 clear button did nothing.
- Clear-fault buttons were enabled with no vehicle connected.
- Two broadcast decoders that had never met real data could abort a session.
- The connect dialog's replay-file row is now hidden unless replay is chosen.

## [0.1.0] — 2026-11-03

First public release: J1939 and J1708/J1587 diagnostics over any RP1210
adapter, module discovery and identification, fault-code reading and clearing,
live data with graphing, CSV logging and raw capture, PDF reporting, unit
selection, a Windows installer, and an in-app update check.
