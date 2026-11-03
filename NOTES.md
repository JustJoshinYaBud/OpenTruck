# OpenTruck — field diagnostics notes

Technical findings from live vehicle sessions, sanitized for publication.
These are observations of standard, published protocols (SAE J1939,
ISO 15765, ISO 14229) and empirical wire formats — useful for anyone
building diagnostic tooling. Nothing here is vendor-confidential.

## Raw-CAN capture wire formats

Two buffer layouts have been observed from RP1210 raw-CAN clients
(`CAN:Baud=Auto/500`), across different vehicles and sessions:

* **12-byte form**: `[CAN id 4 bytes big-endian][8 data bytes]`
  (no timestamp, no flag byte)
* **17-byte form**: `[timestamp 4 bytes LE][flag 1][id 4 bytes BE][8 data]`
  (flag: `01` = 29-bit extended id, `00` = 11-bit standard id; an 11-bit
  variant is 15 bytes with a 2-byte id)

Both carry the full CAN id + 8 data bytes. Parse **adaptively by length**
and verify against a parallel J1939 decode when in doubt. The two forms
have been seen in different capture sessions with the same adapter and
protocol string — the cause is not yet identified (logged for research).

### Raw CAN is the same bus as the J1939 client, one layer lower

Running a raw-CAN client and a J1939 client on the same adapter at the same
time shows the **same traffic twice** — every single-frame PGN matches in
count and payload sequence. The difference is what each client exposes:

* the **J1939 client reassembles** multi-frame messages in firmware and
  delivers them as one long frame (no TP.CM / TP.DT ever appears), and it
  does not report frames transmitted by other clients;
* the **raw-CAN client shows the wire**, including the TP.CM/TP.DT
  handshake (PGN 0xEC00 / 0xEB00) and other tools' transmissions.

So the raw channel is not a second datalink — it is the transport/handshake
view of the bus you are already reading. It is the channel to capture when
you care about *how* something was sent (requests, multi-frame service
tool traffic), not just what was broadcast. Matching a raw TP session to
the reassembled J1939 frame is the quickest way to confirm the pairing.

## CAT (Caterpillar) diagnostic session over Proprietary A

CAT service tooling communicates with the engine over J1939 Proprietary A
(PGN 0xEF00, PDU1, directed per module) plus standard J1939 requests.
Observed frame pairs between a service tool (source 0xFA) and the engine
(source 0x00):

| Tool → ECM | ECM → Tool | Interpretation |
|---|---|---|
| `80 F0 16` | `F0 16 0007 01DB 0080 07` | keep-alive / status poll, every ~6 s, for the whole session |
| `93 00 <ctr> 80 0000` | `94 00 <ctr> C0 0004 00` | proprietary read poll; `<ctr>` increments steadily (~6 s) |
| `80 F0 49` | `F0 49 <state> FFFF…` | **regeneration status poll** — only runs while a regen is active; `<state>` counts up through the regen (observed 00 → 0x3C) |
| `80 F0 59` | `F0 59 <data>` | additional status poll (late session) |

The service tool also polls standard J1939 diagnostics continuously
(DM2 via PGN 0xEA00 requests) and bursts requests for specific PGNs
(EEC1/EEC2/CCVS1/ET1 and the aftertreatment EGT PGNs) when supervision
data is needed.

### Regeneration initiation

A regeneration can start two ways. An **ECM-initiated** one announces
itself on the **standard DPFC1 PGN (0xFD7C)** — the "Active Regeneration"
status flips a little before the flame/EGT temperatures climb — and no
command appears on the bus at all. A **service-tool-requested** one is
driven by a maker-specific command outside the SAE standards; OpenTruck
does not transmit one and does not publish the vendor command. Either way,
the DPFC1 status field plus the aftertreatment gas temperatures are the
reliable, standard way to observe what the vehicle is doing.

## Aftertreatment EGT sensor positions — OEM-specific by design

J1939 SPNs 3241/3249/3245 ("Aftertreatment 1 Exhaust Gas Temperature
1/2/3") and 1737 ("Exhaust Gas Temperature", IC1) are
**OEM-application-specific**: the SPN proves a sensor exists, never where
it sits. One OEM's EGT 1 is a DOC inlet thermocouple; another's is an
aftertreatment burner flame sensor; a DPF-only truck has no SCR-position
sensor. Applying a universal mapping WILL display values under the wrong
component.

OpenTruck therefore shows neutral, SPN-identified labels
("Exhaust Temperature 1 (SPN 3241)") unless the engine matches a curated
per-engine entry in `lookup/obd_aft_positions.py`. Entries are added only
from confirmed field data. Confirmed so far:

* **Caterpillar C13 ACERT** (DOC+DPF, no SCR; confirmed during a live
  regeneration): SPN 3245 = the regeneration flame temperature (the
  highest reading of the cycle); SPNs 1737 and 3241 are the same sensor —
  the turbo-outlet exhaust temperature (the ARD inlet) — kept under the
  generic Exhaust Temperature naming; SPN 3249 (intermediate) not fitted.
  DPF inlet / outlet (SPN 3242 / 3246) need no override — the standard
  decoders already report them correctly.

**ARD is Caterpillar's device** (Aftertreatment Regeneration Device — the
burner/igniter head on CAT engines). It is not a Navistar/International
therm: "flame temperature" wording is applied to CAT engines only. No
non-CAT engine is mapped to any position yet.

Caterpillar also names cooled EGR **"Clean Gas Induction" (CGI)** on ACERT
and later engines — the aftertreatment panel applies that wording on CAT
engines.

## EGT sensor inventory examples (key-on engine off)

Observed sensor complements differ per engine — examples from live
captures (values at cold key-on):

* CAT C13 ACERT (DOC+DPF): SPN 1737 and 3241 reporting identically
  (turbo outlet), 3245 fitted (flame), 3249/3250 not fitted, DPF
  intake/outlet (3242/3246) fitted, no SCR temperatures.
* Generic guidance: the *set* of EGT sensors that actually report live
  data tells you which aftertreatment positions the OEM instrumented —
  absence of an SCR temperature set means no SCR sensors, not a broken
  decoder.

## Live Data Parameter Naming

OpenTruck uses **display-only overrides** for live data parameter names. The
underlying decode logic and canonical parameter keys remain unchanged, so CSV
exports, graph identifiers, and saved logs are never affected. Only the GUI
display text is translated to the maker's preferred terminology.

### Common Terminology Differences

Some OEMs use different names for standard J1939 parameters:

* **Intake Charge Pressure (ICP)**: Cummins and Detroit Diesel prefer this name
  over SAE's "Fuel Delivery Pressure" (SPN 94).
* **Air Restriction**: Shorter alternative to "Air Filter Differential Pressure"
  (SPN 107) used by Cummins, Detroit Diesel and PACCAR.
* **Retarder Torque**: Volvo/Mack use this instead of SAE's verbose
  "Actual Retarder Torque".
* **Compression Brake Torque**: PACCAR (Kenworth/Peterbilt) uses Jake Brake
  terminology instead of the generic name.

These overrides are applied per-OEM and never leak to other manufacturers.

### NOx Sensor Placeholders

The aftertreatment panel now includes placeholder rows for:

* **SCR Inlet NOx**
* **SCR Outlet NOx**

These display "—" (not available) until proprietary Aftertreatment Control
Module (ACM) PGNs are identified and decoded. Most OEMs broadcast NOx sensor
data on proprietary PGNs rather than standard J1939 broadcasts, so actual
NOx readings require manufacturer-specific documentation.

## See also

* [ARCHITECTURE.md](ARCHITECTURE.md) — how the code layers fit together
* [ROADMAP.md](ROADMAP.md) — what is implemented and what is planned
* Raw-CAN analysis tooling in the repository: `can2_probe.py` (multi-client
  wire capture), `obd2_probe.py` (OBD-II DLC capture), `uds_sweep.py`
  (UDS module discovery)