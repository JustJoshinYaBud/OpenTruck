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
- **Logs data to a spreadsheet (CSV)** while the truck is running, for
  troubleshooting intermittent problems.
- **Speaks all three diagnostic languages** — J1939 (2003+ trucks),
  J1708/J1587 (older trucks), and now **OBD-II (2008+ cars and light/medium
  pickups)** on the 16-pin port. OpenTruck auto-detects which one the vehicle
  speaks when you connect.
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
- The vehicle, with the key ON (engine running for live data).

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
  and the J1708/J1939 connection dots (green = that bus is talking).
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
