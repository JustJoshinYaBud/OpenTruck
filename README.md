# OpenTruck

**OpenTruck is a free diagnostic tool for trucks and heavy equipment.** It
plugs into the truck's diagnostic port through an RP1210 adapter (the same
kind of box diesel shops use) and tells you what the computers on the vehicle
are saying — in plain English, not dealer-tool prices.

## Who is this software for?
The goal of this software is to be universal. It is meant to serve as a tool,
so anybody who owns their equipment can connect, view live data and codes, 
for free. It is a work in progress, so please double check any information 
the software gives you. It is designed to communicate with every type of 
equipment in north america that speaks the standard protocols, including 
medium duty pickup trucks over OBD-II. Will also talk to John Deere over 
a regular RP1210 adapter.

## What it is not
This is not a fully bidirectional program that's meant to replace paid 
service tools. It is simply to provide information for owners, mechanics,
operators, and clear codes so they can repair their equipment themselves.

## What it does

- **Speaks all four diagnostic protocols** — J1939 (2003+ trucks),
  J1708/J1587 (older trucks), **OBD-II** (2008+ cars and light/medium pickups)
  on the 16-pin port, and **CDL** on CAT-family
  adapters. OpenTruck auto-detects which ones the vehicle speaks when you
  connect.
- Works with trucks, tractors, and off-highway machines.
- **Shows every computer on the vehicle** — engine, transmission, ABS/brakes,
  and more — identified by name.
- **Reads fault codes** (check-engine / ABS trouble codes) from every module,
  with the code number, the description, and whether it's active right now or
  stored from before.
- **Clears fault codes** after the repair, the standard SAE way.
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
- **Identifies the vehicle** — the VIN gives make/model/year, the
  engine (displacement, cylinders, fuel, maker's engine code), and each
  module's serial/part number where it reports one.
- **Logs data to a spreadsheet (CSV)** while the truck is running, for
  troubleshooting intermittent problems.


## What you need

- A Windows 10/11 PC
- An **RP1210 adapter** — the industry-standard diagnostic interface used by
  heavy-duty scan tools. OpenTruck lists any RP1210 adapter whose driver is
  installed on the PC and handles 32-bit-only drivers automatically. Adapters
  come from the installed driver, not from plugging the USB cable in — an
  adapter with no driver shows no entry, and the Connect window now explains
  which of the two is missing. OEM-branded versions work the same way: the
  John Deere USB-Link 3 is Nexiq USB-Link 3 hardware and appears under the
  Nexiq driver name, and the John Deere EDL3 appears under its own driver.
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
   isn't yet code-signed; click **More info → Run anyway**. We are setting up
   free code signing via SignPath Foundation — see [Code signing & privacy]
   (#code-signing-and-privacy) below.)
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
- **If Windows blocks an automatic update**, the installer was stopped by
  SmartScreen or by Smart App Control before it could run. OpenTruck verifies
  the download and, when Smart App Control is enforced, warns you before
  closing so the program does not just disappear. In that case use **Open
  Download Page** and run the installer manually. Until code signing is fully
  active, Windows may show an "unrecognized app" prompt on a PC that has not
  seen OpenTruck before; every release can be verified against the published
  SHA-256 checksum.

## Code signing and privacy

- **Privacy.** OpenTruck has no telemetry, analytics, or tracking. Its only
  network activity is an update check against the **public GitHub Releases
  API** for this project (silent on startup, or via `Help ▸ Check for
  Updates`), which sends no personal data. See [`CODE_SIGNING.md`]
  (CODE_SIGNING.md) for details.

> **⚠️ Windows Smart App Control / SmartScreen notice.** Because OpenTruck's
> installer has not yet built up reputation with Windows, **Smart App Control**
> or **SmartScreen** may block it on some PCs — you may see a "Windows
> protected your PC" (SmartScreen) or "This app is blocked / has been blocked
> by Smart App Control" prompt. Until we complete code signing, it may be
> necessary on a PC that has never run OpenTruck to **temporarily disable**
> **Smart App Control** (Windows Security ▸ **App & browser control** ▸ Smart
> App Control) or, for SmartScreen, to click **More info → Run anyway** /
> **Learn more**, install, and then re-enable it.
>
> **Note — Caterpillar Comm Adapter 3**
> CA3 users may need to turn off Memory Integrity for the *adapter driver*, 
which is a separate thing from the Smart App Control block described above.
>
> Being blocked is a normal consequence of an unsigned, still-building-
> reputation app and is not a sign the software is unsafe. You can always
> verify the SHA-256 checksum published with each release. Please only disable
> these protections to run software you trust.

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

## License

OpenTruck is free software: you can redistribute it and/or modify it under
the terms of the [GNU General Public License, version 3 or (at your option)
any later version](LICENSE) (GPL-3.0-or-later). It is distributed in the
hope that it will be useful, but WITHOUT ANY WARRANTY; without even the
implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the [LICENSE](LICENSE) file for the full terms.

OpenTruck has no affiliation with, sponsorship from, or endorsement by any
vehicle, engine, or component manufacturer; all brand names are the property
of their respective owners. The diagnostic identifier tables are a
compilation assembled from sources found through ordinary internet search
and may be inaccurate, incomplete, or out of date.
