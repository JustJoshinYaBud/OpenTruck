"""OpenTruck - SAE J1708 / J1587 decoding.

J1708 is the byte-oriented physical/data-link layer (RS-485, 9600 baud, 8N1)
used on older heavy-duty and off-highway vehicles. J1587 is the application
layer carried on top of it and defines MIDs (nodes), PIDs (parameters) and the
diagnostic (fault-code) message.

This module is deliberately parallel to j1939.py: the wire formats are entirely
different, so we do NOT reuse the J1939 Frame/PGN model. The J1708Session here
mirrors the *shape* of the J1939 Session (modules / live / vin) so the GUI can
render both with the same code.

RP1210_ReadMessage buffer for the J1708 protocol (RP1210B):
    [0:4] timestamp (ms, little-endian)
    [4]   MID (message identifier = source address, 128..255 for J1587)
    [5:]  data = one or more PID(1 byte) + parameter-data pairs

    The MID byte sits at offset 4 (confirmed against real adapter captures);
    everything downstream (PID parse + decode) is standard J1587.

J1587 PID length rule (lets us parse the data without a full PID table):
    0..127   -> 1 data byte follows
    128..191 -> 2 data bytes follow
    192..255 -> variable: the first data byte is the count of data bytes

Fault codes arrive on PID 194 ("Diagnostic Code and Occurrence Count Table");
its data is a run of 4-byte records [mode, pid/sid, fmi, occurrence].
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from lookup.pid1587 import MID_SID_NAMES, PID_NAMES, PID_SCALE, SID_NAMES, decode_bits
from lookup.spn import SPN_NAMES, UNRESOLVED_CODE
from lookup.oem import resolve_pid_name, resolve_sid_name, select_oems
from lookup.oem_eaton import eaton_transmission_fault
from lookup.manufacturers import friendly_make


# --- MID -> node name (SAE J1587 Table 1, common subset) ------------------- #
# MIDs 0..127 are protocol/control functions (0 = request, 1 = "invalid data",
# etc.), not user devices; real controllers live in 128..255.
MID_NAMES = {
    128: "Engine #1",
    129: "Turbocharger",
    130: "Transmission",
    131: "Power Takeoff",
    132: "Axle, Power Unit",
    133: "Axle, Trailer #1",
    134: "Axle, Trailer #2",
    135: "Axle, Trailer #3",
    136: "Brakes, Power Unit",
    137: "Brakes, Trailer #1",
    138: "Brakes, Trailer #2",
    139: "Brakes, Trailer #3",
    140: "Instrument Cluster",
    141: "Trip Recorder",
    142: "Vehicle Management System",
    143: "Fuel System",
    144: "Cruise Control",
    145: "Road Speed Indicator",
    146: "Cab Climate Control",
    147: "Cargo Refrigeration/Heating, Trailer #1",
    148: "Cargo Refrigeration/Heating, Trailer #2",
    149: "Cargo Refrigeration/Heating, Trailer #3",
    150: "Suspension, Power Unit",
    151: "Suspension, Trailer #1",
    152: "Suspension, Trailer #2",
    153: "Suspension, Trailer #3",
    154: "Diagnostic Systems, Power Unit",
    155: "Diagnostic Systems, Trailer #1",
    156: "Diagnostic Systems, Trailer #2",
    157: "Diagnostic Systems, Trailer #3",
    158: "Electrical Charging System",
    159: "Proximity Detector, Front",
    160: "Proximity Detector, Rear",
    161: "Aerodynamic Control Unit",
    162: "Vehicle Navigation Unit",
    163: "Vehicle Security",
    164: "Multiplex",
    165: "Communication Unit - Ground",
    166: "Tires, Power Unit",
    167: "Tires, Trailer #1",
    168: "Tires, Trailer #2",
    169: "Tires, Trailer #3",
    170: "Electrical",
    171: "Driver Information Center",
    172: "Off-board Diagnostics #1",
    173: "Engine Retarder",
    174: "Cranking/Starting System",
    175: "Engine #2",
    176: "Transmission, Additional",
    177: "Particulate Trap System",
    178: "Vehicle Sensors to Data Converter",
    179: "Data Logging Computer",
    180: "Off-board Diagnostics #2",
    181: "Communication Unit - Satellite",
    182: "Off-board Programming Station",
    183: "Engine #3",
    184: "Engine #4",
    185: "Engine #5",
    186: "Engine #6",
    187: "Vehicle Control Head Unit/Vehicle Management System #2",
    188: "Vehicle Logic Control Unit/Vehicle Management System #3",
    189: "Vehicle Head Signs",
    190: "Refrigerant Management Protection and Diagnostics",
    191: "Vehicle Location Unit - Differential Correction",
    192: "Front Door Status Unit",
    193: "Middle Door Status Unit",
    194: "Rear Door Status Unit",
    195: "Annunciator Unit",
    196: "Fare Collection Unit",
    197: "Passenger Counter Unit #1",
    198: "Schedule Adherence Unit",
    199: "Route Adherence Unit",
    200: "Environment Monitor Unit/Auxiliary Cab Climate Control",
    201: "Vehicle Status Points Monitor Unit",
    202: "High Speed Communications Unit",
    203: "Mobile Data Terminal Unit",
    204: "Vehicle Proximity, Right Side",
    205: "Vehicle Proximity, Left Side",
    206: "Base Unit (Radio Gateway to Fixed End)",
    207: "Bridge from SAE J1708 Drivetrain Link",
    208: "Maintenance Printer",
    209: "Vehicle Turntable",
    210: "Bus Chassis Identification Unit",
    211: "Smart Card Terminal",
    212: "Mobile Data Terminal",
    213: "Vehicle Control Head Touch Screen",
    214: "Silent Alarm Unit",
    215: "Surveillance Microphone",
    216: "Lighting Control Administrator Unit",
    217: "Tractor/Trailer Bridge, Tractor Mounted",
    218: "Tractor/Trailer Bridge, Trailer Mounted",
    219: "Collision Avoidance Systems",
    220: "Tachograph",
    221: "Driver Information Center #2",
    222: "Driveline Retarder",
    223: "Transmission Shift Console - Primary",
    224: "Parking Heater",
    225: "Weighing System, Axle Group #1/Vehicle",
    226: "Weighing System, Axle Group #2",
    227: "Weighing System, Axle Group #3",
    228: "Weighing System, Axle Group #4",
    229: "Weighing System, Axle Group #5",
    230: "Weighing System, Axle Group #6",
    231: "Communication Unit",
    232: "Safety Restraint System",
    233: "Intersection Preemption Emitter",
    234: "Instrument Cluster #2",
    235: "Engine Oil Control System",
    236: "Entry Assist Control #1",
    237: "Entry Assist Control #2",
    238: "Idle Adjust System",
    239: "Passenger Counter Unit #2",
    240: "Passenger Counter Unit #3",
    241: "Fuel Tank Monitor",
}


def mid_name(mid: int) -> str:
    if mid in MID_NAMES:
        return MID_NAMES[mid]
    return f"MID {mid}"


# PID names and scaling live in the dedicated SAE J1587 table (pid1587.py),
# which is kept separate from the J1939 SPN table in spn.py. decode_pid() below
# pulls a name from both registries and scales the value to canonical metric.


# J1587 identification PIDs (SAE J1587 Table 2). They carry ASCII text and are
# normally *on request only* (not broadcast), so the app requests them after a
# connect (see app._request_j1708_idents) to learn the VIN / make / serial.
PID_UNIT_NUMBER = 233       # Unit Number (Power Unit)
PID_SOFTWARE_ID = 234       # Software Identification
PID_VIN = 237               # Vehicle Identification Number
PID_COMPONENT_ID = 243      # Component Identification: [MID]make*model*serial

# MID a tester uses when requesting identification. SAE J1587 names MID 172
# (0xAC) "Off-board Diagnostics #1"; we send identification requests as it.
J1587_REQUESTER_MID = 0xAC

# PIDs that SAE J1587 defines as application/OEM-configured (the standard says
# "configured uniquely per application; not to be used in place of existing
# PIDs") or as natural-gas-only. Their value is meaningless when scaled with the
# generic factor on a diesel, so decode_pid() reports them as not-applicable
# instead of a confident (but wrong) reading:
#   136 Auxiliary Vacuum Pressure Reading
#   137 Auxiliary Gage Pressure Reading #1
#   138 Auxiliary Absolute Pressure Reading
#   147/148 Average/Instantaneous Fuel Economy (Natural Gas)
#   149 Fuel Mass Flow Rate (Natural Gas)
APP_SPECIFIC_PIDS = frozenset({136, 137, 138, 147, 148, 149})

# J1587 diagnostic-protocol PIDs. They are request/response traffic, not
# broadcast parameters, so they must never reach the live-data list.
DIAGNOSTIC_PIDS = frozenset({193, 194, 195, 196, 197, 198})


@dataclass
class J1708Message:
    mid: int
    params: list[tuple[int, bytes]]   # (pid, raw data bytes) in message order
    timestamp: float = 0.0
    truncated: bool = False   # a length-prefixed PID declared more bytes than arrived
    raw: bytes = b""          # the adapter's data field verbatim (checksum stripped)

    def to_log_line(self) -> str:
        # Log the adapter's raw data field, NOT the re-serialized params. The
        # length byte of a variable-length PID (192-255) is consumed by
        # parse_params and is NOT part of any param's data, so re-serializing
        # silently drops it - which made PID 194 fault lists unrecoverable from
        # a capture (the "n" byte vanished and the records looked truncated).
        body = self.raw if self.raw else b"".join(
            bytes([pid]) + d for pid, d in self.params)
        return f"J1708 {self.mid:02X}:{body.hex().upper()}"


@dataclass
class J1708DTC:
    mid: int
    pid: int          # PID or SID number of the failed parameter/subsystem
    fmi: int
    occurrence: int
    active: bool
    is_sid: bool = False   # True when ``pid`` is a SID (bit 5 of the 'b' byte)
    # Bit 6 of the flag byte: 1 = standard SAE diagnostic code, 0 = expansion
    # (page-2 / OEM-defined) code. When it is clear the generic page-1 SAE name
    # is NOT an authoritative description of the code, so we prefer the maker's
    # own table and otherwise report "Refer to OEM".
    standard: bool = True


def parse_params(body: bytes) -> list[tuple[int, bytes]]:
    """Split a J1587 data field into (pid, data) pairs using the length rule.

    Stops cleanly at a trailing J1708 checksum byte or truncation, so it is
    safe to feed it a buffer that still carries the checksum.

    A length-prefixed PID (192..255) declares its own byte count. When that
    count runs past the end of the message the field is TRUNCATED (a short read
    or a split multi-frame message). We record the bytes that are actually
    present rather than dropping the whole message, and mark it in
    ``last_parse_truncated`` so the caller can tell the data was incomplete.
    """
    global last_parse_truncated
    last_parse_truncated = False
    params: list[tuple[int, bytes]] = []
    i, n = 0, len(body)
    while i < n:
        pid = body[i]
        i += 1
        if pid <= 127:
            length = 1
        elif pid <= 191:
            length = 2
        else:                      # >= 192: length-prefixed (next byte = count)
            if i >= n:
                break
            length = body[i]
            i += 1
        avail = n - i
        if length > avail:
            # Truncated/over-declared length: keep what is there, then stop.
            last_parse_truncated = True
            if avail > 0:
                params.append((pid, bytes(body[i:i + avail])))
            break
        params.append((pid, bytes(body[i:i + length])))
        i += length
    return params


# Set by parse_params() when the last message declared more bytes than it
# actually carried (see the docstring). Diagnostics only.
last_parse_truncated = False


def from_rp1210_buffer(buf: bytes, n: int) -> Optional[J1708Message]:
    """Decode one J1708 message from an RP1210_ReadMessage buffer.

    Returns None when the read is empty/too short to be a real message.
    """
    if n < 6:                      # timestamp(4) + MID(1) + >= 1 data byte
        return None
    mid = buf[4]
    body = buf[5:n]
    params = parse_params(body)
    return J1708Message(mid=mid, params=params,
                        truncated=last_parse_truncated, raw=body)


def _fmt(v: float) -> str:
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return f"{v:.2f}".rstrip("0").rstrip(".")


def decode_pid(pid: int, data: bytes, make: str | None = None,
               mfr: int | None = None) -> tuple[str, str, str]:
    """Return (name, value string, unit) for one J1587 PID + data pair.

    The name is resolved OEM-first (when the module's make/manufacturer code is
    known), then from the J1587 table, then from the J1939 SPN table, so a
    number present in any registry resolves to a readable name. A PID with
    known scaling is decoded to canonical SI/metric units (kPa, degC, km/h, ...)
    so the shared units.convert() display converter applies; a bit-mapped status
    PID decodes to readable text; a PID with no scaling at all is shown as its
    raw integer value.
    """
    name = (resolve_pid_name(pid, make=make, mfr=mfr)
            or PID_NAMES.get(pid) or SPN_NAMES.get(pid) or f"PID {pid}")
    # Bit-mapped status PIDs decode to readable "label: value" text.
    text = decode_bits(pid, data)
    if text is not None:
        return name, text, ""
    # PIDs the J1587 standard defines as application/OEM-configured ("configured
    # uniquely per application; not to be used in place of existing PIDs") or as
    # natural-gas-only. On a diesel engine these carry nonsense if scaled with
    # the generic factor (e.g. "auxiliary gauge pressure" = 32 bar, "natural gas
    # fuel flow" on a diesel), so mark them instead of inventing a reading.
    if pid in APP_SPECIFIC_PIDS:
        return name, "n/a (application-specific)", ""
    # J1587 uses the same "not available"/"error" sentinels as J1939 (0xFE /
    # 0xFF) on the most-significant byte of a scaled value. Skip those rather
    # than showing a nonsense reading (e.g. 32739 kPa).
    if data and (all(b == 0xFF for b in data)
                 or data[-1] >= 0xFE):
        return name, "n/a", ""
    spec = PID_SCALE.get(pid)
    if spec is None:
        return name, str(int.from_bytes(data, "little")), ""
    scale, offset, unit, signed = spec
    raw = int.from_bytes(data, "little", signed=signed)
    return name, _fmt(raw * scale + offset), unit


def decode_fault_codes(mid: int, data: bytes) -> list[J1708DTC]:
    """Parse PID 194 data -> fault codes, per SAE J1587 Appendix A (PID 194).

    Each diagnostic record is ``[a: SID or PID][b: FMI + flags][c: count?]``
    where, in the ``b`` byte:
        bit 8 (0x80) = occurrence count present (adds the trailing ``c`` byte)
        bit 7 (0x40) = 1 inactive / 0 active
        bit 6 (0x20) = 1 standard code / 0 page-2 expansion PID
        bit 5 (0x10) = 1 the ``a`` byte is a SID / 0 a PID
        bits 4-1     = failure mode identifier (FMI)
    So records are 2 bytes, or 3 when the count byte is present.
    """
    out: list[J1708DTC] = []
    i, n = 0, len(data)
    while i + 1 < n:
        a = data[i]
        b = data[i + 1]
        has_count = bool(b & 0x80)
        is_sid = bool(b & 0x10)
        active = (b & 0x40) == 0
        fmi = b & 0x0F
        standard = bool(b & 0x20)
        if has_count:
            if i + 2 >= n:
                break                       # truncated count byte
            occ = data[i + 2] & 0x7F
            step = 3
        else:
            occ = 0
            step = 2
        # ``a`` = 0 is not a reportable parameter: PID 0 is "Request Parameter"
        # and SID 0 is reserved, so such records are padding, not faults.
        if a != 0:
            out.append(J1708DTC(mid, a, fmi, occ, active, is_sid, standard))
        i += step
    return out


class J1708Module:
    """Mirrors the fields the GUI reads off a J1939 ``reader.Module``, so the
    same component list / fault table / live-data rendering works unchanged."""

    def __init__(self, mid: int) -> None:
        self.address = mid
        self.name = None
        self.active_dtcs: list[dict] = []
        self.previous_dtcs: list[dict] = []
        self.lamps: dict = {}
        self.make: Optional[str] = None
        self.model: Optional[str] = None
        self.serial: Optional[str] = None
        self.software_id: Optional[str] = None
        self.ecu_part: Optional[str] = None
        self.ecu_serial: Optional[str] = None
        self.unit: Optional[str] = None
        self.fault_incomplete: bool = False   # PID 194 arrived truncated
        self.mfr: Optional[int] = None        # J1939 NAME manufacturer code (borrowed)

    @property
    def label(self) -> str:
        # Append the component make when known (from PID 243) so e.g. the brake
        # controller reads "Brakes, Power Unit \u2014 WABCO" instead of just the MID name.
        base = mid_name(self.address)
        label = f"{base} \u2014 {friendly_make(self.make)}" if self.make else base
        # The ECU broadcast its fault-code list truncated (short read/split msg);
        # say so rather than silently showing no J1587 codes for this module.
        return label + " (fault list incomplete)" if self.fault_incomplete else label


class J1708Session:
    """Accumulates J1708/J1587 state in the same shape as the J1939 Session."""

    def __init__(self) -> None:
        self.modules: dict[int, J1708Module] = {}
        self.live: dict[int, dict[str, tuple[str, str]]] = {}
        self.vin: str = ""

    def _module(self, mid: int) -> J1708Module:
        return self.modules.setdefault(mid, J1708Module(mid))

    def handle(self, msg: J1708Message) -> None:
        m = self._module(msg.mid)
        active: list[dict] = []
        previous: list[dict] = []
        saw_faults = False
        for pid, data in msg.params:
            if pid == 194:
                if msg.truncated:
                    # The fault-code list declared more bytes than arrived (short
                    # read / split message). Decoding the partial data would
                    # invent wrong codes, so skip it and flag the module so the
                    # UI can say "fault list incomplete - recapture".
                    m.fault_incomplete = True
                    continue
                saw_faults = True
                mfr = getattr(m, "mfr", None)
                known_oem = bool(select_oems(make=m.make, mfr=mfr))
                # Eaton Fuller "Top-2" has no controller of its own: the ENGINE
                # ECM drives the splitter/lockout solenoids and reports their
                # faults under its own MID. Treat such records as transmission
                # faults ONLY when a transmission is on the bus, so an engine's
                # own SID meaning still wins otherwise.
                transmission_present = any(
                    mid in (130, 176) for mid in self.modules)
                for dtc in decode_fault_codes(msg.mid, data):
                    kind = "SID" if dtc.is_sid else "PID"
                    comp = None
                    if transmission_present:
                        comp = eaton_transmission_fault(
                            dtc.is_sid, dtc.pid, dtc.fmi, msg.mid)
                    # Maker-specific name next: an OEM may repurpose a slot, or
                    # carry its own component ID in the PID slot (CAT's CDL CIDs
                    # do exactly that, so CID 248 = "CAT Data Link").
                    if comp is None and dtc.is_sid:
                        comp = resolve_sid_name(dtc.pid, fmi=dtc.fmi,
                                                make=m.make, mfr=mfr)
                    elif comp is None:
                        comp = resolve_pid_name(dtc.pid, fmi=dtc.fmi,
                                                make=m.make, mfr=mfr)
                    if comp is None:
                        # Fall back to the SAE tables - but ONLY when the record
                        # flags itself as a standard SAE code (bit 6), or when we
                        # don't know the maker. A page-2 / OEM-defined code on a
                        # maker we HAVE identified would otherwise be labelled
                        # with a generic SAE name that is almost certainly wrong
                        # (e.g. a Bendix brake's "Transmission Oil Temperature").
                        if dtc.is_sid or dtc.standard or not known_oem:
                            # SIDs are assigned BY CONTROLLER CLASS by SAE, so
                            # the per-MID table IS the standard meaning of that
                            # number here - trust it even when the ECU flags the
                            # code as expansion (the Bendix EC-60 clears bit 6 on
                            # its standard SIDs too). A PID name is a GLOBAL
                            # parameter assignment, so a page-2/OEM-defined PID
                            # from a maker we have identified is not safe to name
                            # generically.
                            if dtc.is_sid:
                                comp = (MID_SID_NAMES.get(msg.mid, {}).get(dtc.pid)
                                        or SID_NAMES.get(dtc.pid))
                            else:
                                comp = (PID_NAMES.get(dtc.pid)
                                        or SPN_NAMES.get(dtc.pid))
                    label = comp or UNRESOLVED_CODE
                    d = {
                        "spn": dtc.pid,
                        "fmi": dtc.fmi,
                        "occ": dtc.occurrence,
                        "num": f"{kind} {dtc.pid}",
                        "desc": label,
                    }
                    (active if dtc.active else previous).append(d)
            elif pid == PID_VIN:
                vin = data.decode("ascii", "replace").replace("\x00", "").strip()
                # Skip dummy "not programmed" VINs (all zeros).
                if vin and vin != "0" * len(vin):
                    self.vin = vin
            elif pid == PID_COMPONENT_ID:
                # data = [component MID][make*model*serial]; attribute it to the
                # module named in the first byte (which may differ from sender).
                if data:
                    target = self._module(data[0])
                    parts = data[1:].decode("ascii", "replace").split("*")
                    if parts and parts[0].strip():
                        target.make = parts[0].strip()
                    if len(parts) > 1 and parts[1].strip():
                        target.model = parts[1].strip()
                    if len(parts) > 2 and parts[2].strip():
                        target.serial = parts[2].strip()
            elif pid == PID_SOFTWARE_ID:
                sw = data.decode("ascii", "replace").replace("\x00", "").strip()
                if sw:
                    m.software_id = sw
            elif pid == PID_UNIT_NUMBER:
                unit = data.decode("ascii", "replace").replace("\x00", "").strip()
                if unit:
                    m.unit = unit
            elif pid in DIAGNOSTIC_PIDS:
                # 193-198 are the diagnostic request/response PIDs. PID 194 in
                # particular is NOT a live parameter - letting it fall through
                # here put the raw fault-table bytes into the live-data list as
                # a nonsense number.
                continue
            else:
                name, value, unit = decode_pid(pid, data, make=m.make,
                                               mfr=getattr(m, "mfr", None))
                bucket = self.live.setdefault(msg.mid, {})
                bucket[name] = (value, unit)
        if saw_faults:
            m.active_dtcs = active
            m.previous_dtcs = previous


# --- J1587 fault-code clearing (PID 195) ------------------------------------ #
# SAE J1587 defines no dedicated off-board tool MID the way J1939 names 0xF9
# "off-board tool #1". MIDs 0..127 are reserved for protocol/control and
# 128..255 are ECUs, so a tester claims an otherwise-unassigned value. The clear
# still targets a specific ECU via the `a` byte in the request (below), so this
# sender MID only affects response routing, not whether a clear is honoured.
J1587_TOOL_MID = 0x81

# PID 195 = "Transmitter Data Request / Clear Count".
PID_TRANSMITTER_REQUEST = 195   # 0xC3


def build_clear_request(target_mid: int) -> bytes:
    """Build the J1587 body that requests ALL diagnostic counts be cleared on
    the ECU at ``target_mid`` (PID 195, mode bits 7-8 = ``10`` = clear all).

    Body layout (excluding the sender MID and the J1708 checksum, both added by
    the RP1210 driver): ``[PID 195][n=3][target MID][b = ignored][c = 0x80]``.
    """
    return bytes([PID_TRANSMITTER_REQUEST, 0x03, target_mid & 0xFF, 0x00, 0x80])


def build_request(target_mid: int, pid: int) -> bytes:
    """J1587 body for a component-specific parameter request (PID 128):
    ``[128][requested PID][target MID]``. The caller adds its own MID."""
    return bytes([128, pid & 0xFF, target_mid & 0xFF])


def build_broadcast_request(pid: int) -> bytes:
    """J1587 body for a broadcast parameter request (PID 0):
    ``[0][requested PID]``. Any module that has the PID answers."""
    return bytes([0, pid & 0xFF])
