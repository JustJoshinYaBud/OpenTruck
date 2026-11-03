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
- **Units** convert at display time (metric, US customary, Canadian), so
  switching them updates values already on screen.

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
