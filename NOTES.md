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
## Cat Data Link (CDL) wire format

The Cat Data Link is CAT's proprietary 9600-baud RS-485 link carrying a
machine's controllers (the same messages CAT ET shows). The header shape
is published in CAT's own service documentation, and matches what the
wire shows:

```
RP1210 'CAT' protocol receive buffer:
[timestamp 4 bytes LE][MID][destination MID (0x00 = broadcast)][IID][data...]
MID = module identifier (36 = Engine Control #1); IID = instruction
identifier (82 = request to broadcast diagnostic codes, 15 = diagnostic
codes per CAT's published CCM protocol documentation).
```

OpenTruck treats the Cat Data Link like any other diagnostic bus: it reads
what the machine broadcasts and what it answers to, transmits read requests
only, and never touches security, calibration or programming. The
MID/CID/FMI identifier tables come from CAT's published "Diagnostic Code
Information" document (REHS0126), the same public source independent
repair shops use; no OEM manual prose is reproduced.

### CDL read requests — the empirical formats (2026-11-13)

A CDL controller does not volunteer its identity or its fault log: a
tool has to ask. The request shapes below were taken from a machine's own
service-tool traffic and then answered identically by two engine families
and four machine controllers on real hardware (a C6.6 engine and a 938
wheel loader, via a Comm Adapter 3):

```
read request, sub form:    [src MID 11][target MID][0x60][iid][sub]
read request, sub-less:    [src MID 11][target MID][0x20][pid]
identity reply (sub echo):  [target][11][0xF8][sub][len][ASCII]
sub-less reply:            [target][11][pid][len][ASCII]   (e.g. 0x86 build date)
fault-code read:           [11][target][0x20][0x82]
fault-code reply:          [target][11][0x82][len][records...]
    each record:           [CID hi][CID lo][flags+FMI]    (max 9 codes)
```

* the identity subs answered identically across engine families:
  0x1C model, 0x10 serial, 0x14 part number, 0x86 build date — a blank
  reply length (len = 0) on the fault-code read is a healthy machine's
  genuine "zero codes";
* CID is MSB-first (CAT's own documented example, CID 501-09, is
  `01 F5`), and the FMI in each record is the **CDL** failure-mode table —
  not the J1939 FMI table; CDL FMI 0 is "High";
* the top bits of the flags+FMI byte vary with key cycles and code state
  (observed 0x03, 0x23, 0x43 while a code was fresh/aged and 0x44/0x48/
  0x49 on logged codes) — most consistent with a small occurrence/status
  field; keep the byte and don't over-interpret it;
* through the Comm Adapter 3's RP1210 driver, SendMessage takes the raw
  message bytes `[src][dst][IID][data]` with no checksum or length prefix
  (the adapter framing handles both).

### What OpenTruck transmits on CDL

Read requests only: the identity and fault-code reads above, addressed as
MID 11 ("Communication Adapter") — the same request-and-listen traffic a
service tool performs. No writes, no code clearing, no security, no
calibration, no programming; anything unrecognized is recorded as-is
rather than guessed.

## Ford HS-CAN: engine RPM on the proprietary bus (empirical)

A 2011 F-150 (16-pin DLC, 500k, all-11-bit HS-CAN, ~940 frames/s across
69 ids) was captured while the engine was swept idle -> 2700 -> idle,
with **simultaneous OBD-II PID 0x0C polling as ground truth** (320 RPM
samples against 60,645 raw frames). Correlation of every candidate byte
and 16-bit field against the RPM curve:

* **id 0x201, bytes 0-1, unsigned 16-bit BIG-ENDIAN, value / 4 = engine
  RPM** (r = 0.999; broadcast ~125 Hz). Verified at both ends of the
  sweep: idle 0x08FB -> 574.8 RPM vs OBD 574.5; high rev 0x2A3B ->
  2702.8 vs OBD 2708.5. Mean deviation 19.6 RPM, dominated by the OBD
  reference's own sampling lag.
* 0x201 byte 4 correlates ~0.5 with RPM (small range 0-18; throttle/load
  shaped), byte 5 steps in 64s (flag bits), bytes 2-3 and 6-7 constant
  across the sweep.
* 0x420 (u16 LE @2, r = 0.975) tracks RPM loosely - a derived/filtered
  value, not the tach.

Method note: synchronized OBD polling as ground truth while exercising
the vehicle is the general recipe for decoding any proprietary stream -
it needs no vendor documentation and no transmission of anything onto
the proprietary bus (the OBD-II layer is the only thing talked to).

## Ford HS-CAN: brake pedal flag (empirical)

Follow-up action-gated capture on the same F-150 (each action captured on
its own, so the timeline needs no clock assumptions): three deliberate
brake presses produced **exactly six transitions** of

* **id 0x200, byte 0: 0x7F (released) <-> 0x80 (pressed)**

the only action-gated field on the bus during the window - confirmed
against the earlier mixed-action sweep, where the same byte showed
127/128 transitions during the brake phase only. Steering lock-to-lock
(at standstill) produced NOTHING on this bus: steering-angle data rides
Ford's MS-CAN (16-pin DLC pins 3/11, a second CAN segment) or is gated
to vehicle speed - it is not present on the pins 6/14 HS-CAN the
standard OBD cable wires. The brake state reaches HS-CAN only because
the powertrain needs it (torque/creep management).

Practical decode summary for the F-150 HS-CAN (pins 6/14):
* 0x201 bytes 0-1 (u16 BE) / 4 = engine RPM, ~125 Hz
* 0x200 byte 0 = brake pedal flag (0x7F/0x80)
* 0x084, 0x092, 0x433, 0x250 carry rolling counters (bytes stepping
  mod 8 / in 16-step nibbles) - anti-stale counters, not sensor data
* 0x420 / 0x42B carry RPM-derived/filtered values (r 0.94-0.97)

## Ford MS-CAN is reachable on the Nexiq USB-Link 3 (16-pin DLC pins 3/11)

The USB-Link 3 has five CAN channels on one RP1210 device; the channel is
selected with a suffix on the protocol string. With the standard 16-pin
J1962 cable:

* **`CAN:Baud=125,Channel=2` = Ford MS-CAN (DLC pins 3/11, 125 kbps)** -
  observed on a 2011 F-150: ~120 frames/s of body-bus traffic across
  ~42 ids (incl. frames carrying VIN fragments), a completely different
  id population than the pins 6/14 HS-CAN. Channel 1 at 125 k reads
  nothing (it is the 6/14 HS-CAN pair at the wrong rate) - a quick
  channel-sanity check when probing.

### Steering state on MS-CAN (empirical)

Action-gated captures with slow step moves (full left - center - full
right) show id **0x425 bytes 6-7 tracking steering state in DISCRETE
steps**: stable for 20+ s with hands off, one clean step per move,
four moves across two captures each stepping exactly at the move. The
value does NOT sweep through intermediates during a slow turn, so it is
a position code/counter, not a continuous angle. The continuous
steering-angle signal was absent from BOTH buses at standstill (the
sensor feeds stability control and appears to be speed-gated) - reading
it needs a capture while the vehicle is moving.
