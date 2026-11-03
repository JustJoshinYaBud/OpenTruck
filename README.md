# OpenTruck

**OpenTruck is a free diagnostic tool for trucks and heavy equipment.** It
plugs into the truck's diagnostic port through an RP1210 adapter (the same
kind of box diesel shops use) and tells you what the computers on the vehicle
are saying — in plain English, not dealer-tool prices.

## What it does

- **Shows every computer on the vehicle** — engine, transmission, ABS/brakes,
  and more — identified by name.
- **Reads fault codes** (check-engine / ABS trouble codes) from every module,
  with the code number, the description, and whether it's active right now or
  stored from before.
- **Clears fault codes** after the repair, the standard SAE way (DM11/DM3 for
  newer trucks, the J1587 clear for older ones). Won't clear while the engine
  is running.
- **Live data** — coolant temp, oil pressure, RPM, speeds, air pressures, DPF
  status, DEF level, and dozens more, updating in real time, with a graph for
  any reading you click.
- **Warns you about dash lamps** — shows MIL / STOP / ABS / trailer-ABS lamp
  status straight from the bus, so you know what the driver is seeing.
- **Prints a PDF report** of the vehicle info, engine totals, and fault codes
  — good for keeping with the repair order.
- **Works with consumer OBD-II cables too** — an ELM327-class serial adapter
  covers 2008+ cars and light pickups; the Connect window lists every serial
  port present, identifies the adapter and finds its baud rate automatically.
- **Identifies the vehicle** — the VIN gives make/model/year (NHTSA vPIC), the
  engine (displacement, cylinders, fuel, maker's engine code), and each
  module's serial/part number where it reports one.
- **Logs data to a spreadsheet (CSV)** while the truck is running, for
  troubleshooting intermittent problems.
- **Speaks all four diagnostic protocols** — J1939 (2003+ trucks),
  J1708/J1587 (older trucks), **OBD-II** (2008+ cars and light/medium pickups)
  on the 16-pin port, and CAT's proprietary **Cat Data Link** on CAT-family
  adapters. OpenTruck auto-detects which ones the vehicle speaks when you
  connect.
- **CAT machines: controllers, identity and fault codes over the Cat Data
  Link.** A CAT machine's controllers (instrument display, transmission,
  telematics and more) live on CAT's own data link and never appear on
  J1939. On a CAT-family adapter OpenTruck listens on every bus at once,
  asks each controller it discovers for its model, serial number, part
  number and build date, and reads its fault codes into the same fault-code
  table — labeled with CAT's own component (CID) and failure-mode (FMI)
  descriptions, not generic guesses. (Reading is request-and-listen only;
  clearing codes over the Cat Data Link is not supported — on machines with
  a J1939 bus, the standard clear is the supported path.)
- **Shows what it's doing** — a live activity line at the bottom of the
  window tracks the connect in real time (which buses answered, how many
  modules are identified, what is still being probed), so a slow connect
  reads as work in progress instead of a frozen app.
- **OEM fault-code tables** — Caterpillar, Cummins, Detroit Diesel,
  International, Volvo/Mack, Deutz, Kubota, Perkins, WABCO, Bendix and Haldex.
  Codes the maker's table can't name read "Refer to OEM" instead of a generic
  SAE description.
- **OEM live data overrides** — displays manufacturer-preferred parameter names
  (e.g., Cummins "Intake Charge Pressure", Volvo/Mack "Retarder Torque")
  without changing the underlying decode logic.
- Works with trucks, tractors, and off-highway machines.

## What you need

- A Windows 10/11 PC
- An **RP1210 adapter** — the industry-standard diagnostic interface used by
  heavy-duty scan tools. OpenTruck lists any RP1210 adapter whose driver is
  installed on the PC and handles 32-bit-only drivers automatically.
  **Fair warning:** not every adapter brand has been tested, so we can't
  guarantee that every RP1210 adapter will work. If yours doesn't, please
  open an issue so the list of known-good adapters can grow.
- **or** a consumer **ELM327-class OBD-II adapter** (USB serial) if you work on
  2008+ cars and light pickups rather than heavy trucks. No driver setup is
  needed — the Connect window lists every serial port the PC has, identifies
  the adapter and finds its baud rate. Unbranded clones work too.
- The vehicle, with the key ON (engine running for live data).
- **Caterpillar Comm Adapter 3 users:** its USB driver dates from 2016, and
  Windows 11's *Memory Integrity* (Core Isolation) setting can silently
  refuse to load it — the adapter won't connect on a stock Windows 11 24H2
  PC until that setting is turned off (or a newer CA3 driver is installed).
  OpenTruck detects the block and tells you exactly which setting to change.

## Getting started

1. **Install:** download `OpenTruckSetup-<version>.exe` from the
   [Releases](https://github.com/JustJoshinYaBud/OpenTruck/releases) page and
   run it. No Python or anything else needed — everything is included.
   (Windows may show a "Windows protected your PC" warning because the app
   isn't code-signed; click **More info → Run anyway**.)
2. **Connect the adapter** to the truck's diagnostic port and to the PC
   (USB), then turn the key ON.
3. **Open OpenTruck.** A short first-time setup appears (just once): pick your
   adapter so it's pre-selected for next time, choose where logs are saved —
   or skip it. Then click **Connect**, pick your adapter from the list, and
   click Connect.
4. **Click a module** on the left (Engine, Brakes, …) to see its details.
   Fault codes from *all* modules are listed together in the Fault Codes
   table — active codes first.
5. **Click any row in the Live Data table** to graph it.
6. When you're done: **Clear Fault** erases codes from the selected module,
   **Clear All Faults** erases them everywhere. The engine must be OFF to
   clear.

No truck nearby? The program starts in **Simulator (demo) mode** so you can
see exactly how it works before plugging into anything.

## Reading the screen

- **Vehicle panel (left):** VIN, make/model, engine serial, software/ECU IDs,
  and the bus connection dots (green = that bus is talking): J1939, J1708,
  CDL, OBD.
- **Fault Codes (top right):** every code from every module. "Active" means
  the problem exists right now; "Previously Active"/"Stored" means it
  happened and was remembered. Click a row, then Clear Fault to clear just
  that module's codes.
- **Live Data (bottom right):** everything the selected module is
  broadcasting. Click a row to graph it over time. Drag the divider bars to
  make any section bigger or smaller — OpenTruck remembers your layout next
  time.

## Settings worth knowing

- **File ▸ Preferences** — switch between **Canadian** (the default), **Metric**,
  or **US Standard** units, and choose where log files are saved.
- **Tools ▸ Start Logging…** — pick which live readings to write to a CSV
  spreadsheet; great for catching problems that come and go.
- **Tools ▸ Generate Report…** — save a PDF snapshot of the vehicle and its
  codes for the service file.
- **Help ▸ Check for Updates** — or just wait: OpenTruck checks by itself on
  startup. When a new version is out, you can let it **download and install
  the update for you** (with a progress bar) — OpenTruck closes, updates, and
  starts again by itself. Your settings and log files are kept.

## If it won't connect

- **Check the adapter is listed.** OpenTruck lists every RP1210 adapter it can
  find on the machine. If yours is missing from the list, its driver is not
  installed or the cable is not plugged in. Adapters shown as *(32-bit driver)*
  are supported through a bundled 32-bit helper and work normally.
- **Send in the log.** **Help ▸ Error logs** shows what happened
  during each connection attempt - the adapter that was used, the bus settings
  that were tried, and the adapter's own error message where it gave one. Click
  **Copy all to clipboard** and paste it into an email. That is usually enough
  to identify the problem without a second trip to the vehicle.
- **Run Check Adapter** (Developer ▸ Check Adapter, vehicle plugged in but
  OpenTruck disconnected). It opens each protocol your adapter supports, one
  connection at a time, and reports which ones received vehicle data - that
  distinguishes a rate problem, a wiring/connector problem, a vehicle that
  puts its diagnostics on another data link, and an adapter being held by
  other software. The result lands in the same error log, so one email covers
  everything.
- **If an adapter connects but the vehicle shows nothing**, also try
  File ▸ Preferences ▸ Connection ▸ *Open only one connection at a time*,
  then reconnect - some adapters drop the link as soon as a second connection
  is opened.
- **Two different failures.** "No data received" means the adapter connected but
  the vehicle said nothing - ignition off, wrong socket, or a bus this adapter
  cannot reach. "No adapter is connected" means the computer could not open the
  cable at all, which is usually a driver, port or device-in-use problem.

## For developers

The source is Python 3 + PySide6. See [`ARCHITECTURE.md`](ARCHITECTURE.md)
for how the code fits together, [`ROADMAP.md`](ROADMAP.md) for what's done
and planned, and [`CHANGELOG.md`](CHANGELOG.md) for what changed in each
release. [`NOTES.md`](NOTES.md) collects the field-observed protocol details.

## License

OpenTruck is free for personal, educational, and other **noncommercial** use
under the [PolyForm Noncommercial License 1.0.0](LICENSE). Selling it,
selling a product built on it, or using it in a for-profit business requires
a separate commercial license from the author.
