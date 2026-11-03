"""OpenTruck - Cat Data Link (CDL) decode + CdlSession.

Evidence base (live capture 2026-11-13, aux engine via the CA3's 'CAT'
protocol, 74 buffers / 3 message groups): the RP1210 receive buffer is

    [0:4]  receive timestamp, little-endian (free-running, NOT wall clock)
    [4]    MID  - module identifier (0x24 = 36 = "Engine Control #1")
    [5]    destination (0x00 = broadcast on every message observed)
    [6]    IID  - instruction identifier (0xF3, 0xFA, 0xFC observed)
    [7:]   data

Keep it that way: decode only what real bytes proved.
"""
from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Optional

from lookup.oem_cat import CAT_CDL_MID, CAT_CDL_FMI, CAT_PID
from lookup.oem_cat_cdl import (CAT_CDL_LIVE, CAT_CDL_LIVE_POLL,
                                CAT_CDL_FID, CAT_CDL_SIGNED,
                                ENGINE_MID_NAMES)

# Documented CDL IIDs (CAT CCM protocol manual + service-tool docs). Factual
# names only; used for tooltips/log lines, never for decode decisions.
CDL_IID_NAMES: dict[int, str] = {
    10: "Broadcast data",
    13: "Broadcast list",
    15: "Diagnostic codes",
    34: "Parameter write / login",
    82: "Request to broadcast diagnostic codes",
}

# Identity request/reply IIDs, VERIFIED on the wire (Challenger ML98B capture
# 2026-11-13): an onboard service interface (MID 13 - the reserved
# address) polls the engine (MID 36) with
#   [13][36][0x60][iid][sub]   (read request for iid/sub)
#   [13][36][0x20][iid]        (read request, sub-less - answered at iid)
# and the engine replies with
#   [36][13][iid][sub][len][ASCII]   (IID 0xF8 family: sub echoed, then a
#                                    length byte and the string)
#   [36][13][iid][len][ASCII]       (IID 0x86: no sub echo)
# Observed: model "CAT 3056 Engine", serial "35602905", arrangement
# "11256044IB", part "2312480-00", build date "AUG04", status "NOT
# PROGRAMMED". Unknown subs are kept under raw keys, never guessed.
IDENTITY_FIELDS: dict[tuple[int, int | None], str] = {
    (0xF8, 0x1C): "model",
    (0xF8, 0x10): "serial",
    (0xF8, 0x11): "arrangement",
    (0xF8, 0x14): "part_number",
    (0xF8, 0x1A): "status",
    (0x86, None): "build_date",
}


def _clean_ascii(raw: bytes) -> str | None:
    """Extract a printable-ASCII string with NUL padding, or None if not text.

    Identity replies pad with NULs inside the declared length (e.g. "CAT 3056
    Engine" + 4 NULs), so NULs are allowed then stripped; at least 3 real
    printable characters are required so binary payloads never masquerade as
    identity strings.
    """
    text = raw.split(b"\x00", 1)[0]
    if len(text) < 3:
        return None
    if not all(0x20 <= b <= 0x7E for b in text):
        return None
    return text.decode("ascii").strip()


def cdl_mid_name(mid: int) -> str:
    """Human name for a CDL MID ("Engine Control #1", ...)."""
    return CAT_CDL_MID.get(mid) or f"CDL module {mid}"


def describe_iid(iid: int) -> str:
    """One-line label for an IID: documented name when known, else raw."""
    return CDL_IID_NAMES.get(iid, "IID %d" % iid)


# --- CDL transmit: read requests (wire-proven 2026-11-13) -------------- #
# The CA3's SendMessage takes the raw message bytes [src][dst][IID][data] -
# no checksum, no length prefix (the adapter framing handles both); wire-
# proven live on the C6.6 aux engine (reply in ~31 ms). We present as MID 11
# "Communication Adapter" - the natural ID for an adapter-driven tool, never
# MID 13 (which may collide with an onboard poller).
TOOL_MID = 0x0B

# The identity reads verified on TWO engine families (C6.6 aux engine and
# the Challenger ML98B's 3056 - the same subs answered on both, so they are
# family-standard, not machine-specific). (iid, sub) pairs; sub=None uses
# the sub-less [0x20] form answered at the IID itself.
IDENTITY_REQUESTS: list[tuple[int, Optional[int]]] = [
    (0xF8, 0x1C),   # model
    (0xF8, 0x10),   # serial
    (0xF8, 0x14),   # part number
    (0x86, None),   # build date
]

# How often each discovered module's fault log is re-read (seconds). The
# engine answered within ~31 ms live, so this is politeness, not latency.
CODES_POLL_S = 10.0

# How often the engine live-parameter set is re-queued (seconds). One request
# goes out per 400 ms tick, so the 8 documented sensors above refresh in ~3 s.
LIVE_POLL_S = 4.0


def build_read_request(target: int, iid: int, sub: Optional[int] = None) -> bytes:
    """One CDL read request in the wire-verified raw framing.

    Sub form:    [TOOL_MID][target][0x60][iid][sub]  (the identity reads).
    Sub-less:   [TOOL_MID][target][0x20][iid]  (the 0x86 build date; the
                PID 0x0082 diagnostic-codes read).
    """
    if sub is None:
        return bytes([TOOL_MID, target, 0x20, iid])
    return bytes([TOOL_MID, target, 0x60, iid, sub])


def build_pid_request(target: int, pid: int) -> bytes:
    """A single-parameter read for a CAT two-byte parameter identifier.

    Same wire shapes the onboard display uses (wheel-loader capture
    2026-11-13): PIDs below 0x100 use the sub-less 0x20 form, all others the
    0x60 high/low form. Read requests only.
    """
    if pid <= 0xFF:
        return bytes([TOOL_MID, target, 0x20, pid])
    return bytes([TOOL_MID, target, 0x60, (pid >> 8) & 0xFF, pid & 0xFF])


def _fmt(v: float, decimals: int = 1) -> str:
    """Trim a scaled number the way the other live decoders do."""
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    s = f"{v:.{decimals}f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def _scaled_value(pid: int, raw: int) -> Optional[tuple[str, str, str]]:
    """Scale one raw (LSB-assembled) CDL value to (name, value, unit).

    Shared by the single-parameter reply path and the F1 multiplexed-block
    path so the FID-range rejection and the signed-range rule can never
    drift apart. Returns None for an unknown PID, a Fault-Identifier value,
    or anything not in ``CAT_CDL_LIVE``.
    """
    if pid not in CAT_CDL_LIVE:
        return None
    name, _lengths, scale, offset, unit = CAT_CDL_LIVE[pid]
    fid = CAT_CDL_FID.get(pid)
    if fid and fid[0] <= raw <= fid[1]:
        return None       # a Fault Identifier, not a value
    if pid in CAT_CDL_SIGNED and raw >= 0x8000:
        raw -= 0x10000
    return name, _fmt(raw * scale + offset), unit


# The multiplexed "broadcast list" the engine pushes to a polling tool
# (IID 0xF1, ~1 Hz, observed live on the bus): data = [0x18 type][seq][records to the end of the buffer].
# Record = [pid_lo][2-byte LSB value] when the first byte < 0xF0 (so 0x40
# is PID 0x0040), else [pid_hi][pid_lo][value] with the value length taken
# from F1_VALUE_LEN. Strict validation: the record walk must consume the
# data exactly, or the whole block is ignored - never partially decoded.
F1_TYPE = 0x18
F1_VALUE_LEN: dict[int, int] = {
    0xF1: 1,   # observed only as PID 0xF189, value 0x00 (163 blocks)
    0xF4: 2, 0xF5: 2, 0xF6: 2,
    0xFC: 4,
}
# PIDs whose presence in an F1 block is wire-proven; the only ones the
# passive F1 decode may render. Expand only when an F1 block is observed
# carrying the PID - do not assume the block will ever include the rest
# of CAT_CDL_LIVE (the C6.6's blocks carried speed and coolant only).
F1_DECODE_OK = frozenset((0x0040, 0x0044))


def decode_f1_block(data: bytes) -> Optional[dict[int, int]]:
    """Parse an IID 0xF1 multiplexed parameter block into {pid: raw LSB}.

    WIRE-PROVEN (2026-11-14 ET capture, ground truth = the operator's
    throttle actions + ET's own screen): speed read 775 RPM at low idle
    and 2000 at high idle, coolant 40-53 C through the warm-up, and the
    shutdown sample carried raw 0x8018 - a Fault Identifier, caught by the
    same FID rule as the single-parameter path.

    Returns None (and nothing is decoded) unless the whole block parses.
    """
    if len(data) < 3 or data[0] != F1_TYPE:
        return None
    pos, recs = 2, {}
    while pos < len(data):
        b = data[pos]
        if b < 0xF0:
            pid, vlen = b, 2
            pos += 1
        else:
            if pos + 1 >= len(data):
                return None
            pid = (b << 8) | data[pos + 1]
            vlen = F1_VALUE_LEN.get(b)
            if vlen is None:
                return None
            pos += 2
        if pos + vlen > len(data):
            return None
        recs[pid] = int.from_bytes(data[pos:pos + vlen], "little")
        pos += vlen
    return recs


def decode_live_reply(iid: int, data: bytes) -> Optional[tuple[int, str, str, str]]:
    """Decode a CDL parameter reply into (pid, name, value, unit) or None.

    Two documented reply shapes, both proven on the wire:
      * PID high byte 0x00: reply IID is the PID low byte, data is the value;
      * PID high byte != 0: reply IID is the PID high byte, data starts with
        the PID low byte, then the value.

    Only PIDs in ``CAT_CDL_LIVE`` are decoded; the value is little-endian
    (LSB first) and an all-0xFF value is the not-available sentinel. A raw
    value inside the PID's documented Fault-Identifier range (CAT_CDL_FID,
    e.g. $8000-$801F for engine speed/coolant/oil pressure) is a sensor
    fault, not data: rejected the same way. PIDs in ``CAT_CDL_SIGNED`` have
    published negative ranges (coolant, oil pressure) and decode signed.
    Anything else returns None and stays raw.

    Byte order is WIRE-PROVEN, not manual-quoted (2026-11-14 C6 ACERT field
    test, key on / engine off): coolant replied ``19 00`` = 25 C and oil
    pressure ``05 00`` = 2.5 kPa LSB-first, where the previous MSB-first
    decode displayed 6400 C and 92 psi. The loader capture agrees
    (hourmeter ``5D 26`` = 9821 h, 7 h from the display's 0xFC20 hours
    parameter 9814; MSB-first would put them 1792 h apart). The manuals'
    "most significant byte first" wording never matched a nonzero value.
    """
    if not data:
        return None
    if iid in CAT_CDL_LIVE:
        pid, value = iid, data
    else:
        pid = (iid << 8) | data[0]
        if pid not in CAT_CDL_LIVE:
            return None
        value = data[1:]
    name, lengths, scale, offset, unit = CAT_CDL_LIVE[pid]
    if len(value) not in lengths:
        return None
    if all(b == 0xFF for b in value):
        return None
    scaled = _scaled_value(pid, int.from_bytes(value, "little"))
    if scaled is None:
        return None
    return pid, scaled[0], scaled[1], scaled[2]


def decode_codes(data: bytes) -> list[dict]:
    """Decode a PID 0x0082 "Diagnostic Codes" reply payload.

    LIVE + DOCUMENTED (wire evidence 2026-11-13): [len][record]... with each record [CID hi][CID lo]
    [flags+FMI], max 9 codes. CID is MSB-first (the manual's CID 501-09
    example, and both live CIDs land on real sensors). The third byte is
    flags+FMI, NOT a plain FMI: every live byte carries FMI 3 in the low
    bits (unplugged sensor = voltage above normal), while the top 3 bits
    differ per key cycle (0, 1, 2 across three reads - status or occurrence
    count, NOT determined). The FMI is read as the low 5 bits (the CDL FMI
    table runs to 21, which a 4-bit field could not express) and the whole
    byte is kept verbatim in "occ" - recorded, never guessed.
    """
    n = data[0] if data else 0
    body = data[1:1 + n]
    out: list[dict] = []
    for i in range(0, len(body) - 2, 3):
        cid = (body[i] << 8) | body[i + 1]
        fb = body[i + 2]
        out.append({
            "spn": cid,
            "fmi": fb & 0x1F,
            "occ": fb,                    # the raw flags+FMI byte, verbatim
            "num": f"CID {cid}",
            "desc": CAT_PID.get(cid) or f"CID {cid}",
        })
    return out


def cdl_fmi_name(fmi: int) -> str:
    """Failure-mode text for a CAT CDL FMI - NOT the J1939 FMI list.

    CDL FMI 0 is "High", not "data valid but above normal"; using the J1939
    table for CDL codes would mislabel every one of them (TODO 55 rule: CDL
    FMI is a separate vocabulary). Used once the IID 15 diagnostic-code
    decode lands; staged now so the codes path never ships with the wrong
    table.
    """
    return CAT_CDL_FMI.get(fmi, "FMI %d" % fmi)


@dataclass
class CDLMessage:
    """One decoded CDL message (see the module docstring for the layout)."""
    mid: int               # module identifier (0x24 = 36 = Engine Control #1)
    dest: int              # destination MID (0 = broadcast, all observed)
    iid: int              # instruction identifier
    data: bytes           # everything after the IID, verbatim
    raw: bytes             # the whole message as received (mid..end, no ts)

    def to_log_line(self) -> str:
        # Mirrors the J1708 line shape ("J1708 <mid>:<rest>") so a capture
        # stays one-message-per-line and distinguishable from the raw
        # capture channel's "cdl <hex>" full-buffer lines.
        return f"CDL {self.mid:02X}:{self.raw[1:].hex().upper()}"


def from_rp1210_buffer(buf, n: int) -> Optional[CDLMessage]:
    """Decode one CDL message from an RP1210 'CAT'-protocol ReadMessage buffer.

    Returns None when the buffer is empty or too short to carry the header.
    No checksum is verified: the CA3 delivers none to verify (see module
    docstring), and a buffer we cannot explain is logged raw, not guessed.
    """
    if n < 7:                      # ts(4) + mid(1) + dest(1) + iid(1)
        return None
    mid = buf[4]
    if mid == 0:                   # MID 0 is not a CDL module; flush noise
        return None
    return CDLMessage(mid=mid, dest=buf[5], iid=buf[6],
                      data=bytes(buf[7:n]), raw=bytes(buf[4:n]))


class CdlModule:
    """One CDL controller (MID-keyed) as the module list sees it.

    Mirrors the J1708Module surface the GUI reads (label, make, dtc lists),
    so CDL controllers drop into the same merged view without special cases.
    """

    def __init__(self, mid: int) -> None:
        self.mid = mid
        self.make = "CAT"          # friendly_make() maps it straight through
        self.model: Optional[str] = None
        # Identity strings read from the wire (IDENTITY_FIELDS above); a
        # CDL engine can name itself "CAT 3056 Engine" with its serial,
        # arrangement, part number and build date. Unknown identity subs
        # land under "iid_0xNN_sub_0xNN" keys - kept, shown, never guessed.
        self.identity: dict[str, str] = {}
        # Diagnostic codes read back on demand (PID 0x0082, wire-proven
        # 2026-11-13): the reply is the module's fault-log snapshot; a
        # healthy engine answers len=0 (which is real evidence, so an empty
        # list is genuine). The active/logged status bits in the flags byte
        # are NOT yet understood, so every reported code is shown under
        # active_dtcs; the raw flags byte rides along in each entry's "occ".
        self.active_dtcs: list = []
        self.previous_dtcs: list = []
        self.messages = 0
        self.iids: Counter = Counter()
        self.last_data: dict[int, bytes] = {}

    @property
    def label(self) -> str:
        model = self.identity.get("model")
        if model:
            return f"{model} (Cat Data Link)"
        return f"{cdl_mid_name(self.mid)} (Cat Data Link)"

    def describe(self) -> str:
        """Module line for the support log: traffic + any wire-read identity."""
        seen = ", ".join(
            "%s (%s)" % (describe_iid(iid), self.iids[iid])
            for iid in sorted(self.iids))
        line = "%s: %d message(s): %s" % (self.label, self.messages, seen)
        if self.identity:
            line += " | identity: " + ", ".join(
                "%s=%r" % kv for kv in sorted(self.identity.items()))
        if self.active_dtcs:
            line += " | %d CDL code(s)" % len(self.active_dtcs)
        return line


class CdlSession:
    """Receive-side CDL state: MID-keyed modules + wire-read identities."""

    def __init__(self) -> None:
        self.modules: dict[int, CdlModule] = {}
        self.live: dict[int, dict[str, tuple[str, str]]] = {}
        self.vin: str = ""
        self.messages = 0
        # Read requests OBSERVED on the wire, keyed (responder, iid, sub):
        # when the reply arrives we know its shape is an identity answer.
        self._pending: set[tuple[int, int, Optional[int]]] = set()
        # Active polling (wire-proven 2026-11-13): identity on demand + codes.
        # The app registers the transmitter and calls poll_tick() on a
        # timer; one request goes out per tick so the poll stays a rounding
        # error next to the machine's own heartbeat traffic.
        self._send: Optional[Callable[[bytes], Optional[int]]] = None
        self._tx_ok = True             # False after a failed send: stop asking
        self._queue: list[bytes] = []
        self._identity_polled: set[int] = set()
        self._last_codes: dict[int, float] = {}
        self._last_live: dict[int, float] = {}

    def set_sender(self, fn: Callable[[bytes], Optional[int]]) -> None:
        """Register the transmit callback (CombinedSource.send_cdl) and
        reset the poll state - one poll campaign per connection."""
        self._send = fn
        self._tx_ok = True
        self._queue.clear()
        self._pending.clear()
        self._identity_polled.clear()
        self._last_codes.clear()
        self._last_live.clear()

    def poll_tick(self) -> None:
        """One pacing tick of the active poll: queue per-module work, then
        send at most ONE request (identity once per module, codes every
        CODES_POLL_S seconds). Read requests only - no writes, no clears,
        no security (the documented clear path is unverified on this wire
        and deliberately not wired).
        """
        if self._send is None or not self._tx_ok:
            return
        now = time.monotonic()
        for mid in list(self.modules):
            if mid == TOOL_MID:
                continue       # our own address (an echoed TX) is not a module
            if mid not in self._identity_polled:
                self._identity_polled.add(mid)
                for iid, sub in IDENTITY_REQUESTS:
                    self._queue.append(build_read_request(mid, iid, sub))
            if now - self._last_codes.get(mid, -1e9) >= CODES_POLL_S:
                self._last_codes[mid] = now
                self._queue.append(build_read_request(mid, 0x82, None))
            if (CAT_CDL_MID.get(mid) in ENGINE_MID_NAMES
                    and now - self._last_live.get(mid, -1e9) >= LIVE_POLL_S):
                self._last_live[mid] = now
                for pid in CAT_CDL_LIVE_POLL:
                    self._queue.append(build_pid_request(mid, pid))
        if len(self._queue) > 64:      # a runaway queue must never flood the bus
            self._queue = self._queue[-64:]
        if not self._queue:
            return
        data = self._queue.pop(0)
        # Register our own request so its reply is recognisable as an
        # answer (exactly what handle() does for requests we OBSERVE on the
        # wire): the 0x86 sub-less reply form only decodes when the request
        # is known. The 0xF8 sub-echo form decodes on shape alone.
        if len(data) >= 4 and data[2] == 0x60 and len(data) >= 5:
            self._pending.add((data[1], data[3], data[4]))
        elif len(data) >= 4 and data[2] == 0x20:
            self._pending.add((data[1], data[3], None))
        try:
            rc = self._send(data)
        except Exception:               # channel gone mid-send            # noqa: BLE001
            rc = -1
        if rc is None or rc < 0:
            # The CDL channel refused (or is gone): stop asking this
            # session. The passive decode keeps working either way.
            self._tx_ok = False
            self._queue.clear()

    def _codes_from_reply(self, msg: CDLMessage) -> None:
        """A PID 0x0082 answer addressed to us: replace the module's
        fault-log snapshot (LIVE-VERIFIED shapes only - see decode_codes)."""
        self.modules[msg.mid].active_dtcs = decode_codes(msg.data)

    def _identity_from_reply(self, msg: CDLMessage) -> None:
        """Attach wire-read identity strings to the sending module.

        Evidence-based: only IID 0xF8 replies with a sub echo and
        a declared ASCII length, and sub-less replies to an observed 0x20
        request (the 0x86 build-date form). Everything else is left alone -
        the parameter broadcasts (0xA2 family) have a different shape and
        must never be scraped as identity.
        """
        mod = self.modules[msg.mid]
        if msg.iid == 0xF8 and len(msg.data) >= 2 and msg.dest != 0:
            # [sub][len][ASCII] - NUL padding allowed inside the string.
            n = msg.data[1]
            if 3 <= n <= 64 and len(msg.data) >= n + 2:
                text = _clean_ascii(msg.data[2:2 + n])
                if text is not None:
                    key = IDENTITY_FIELDS.get((0xF8, msg.data[0]),
                                               "iid_0xF8_sub_0x%02X" % msg.data[0])
                    mod.identity[key] = text
        elif (msg.mid, msg.iid, None) in self._pending and msg.data:
            # Sub-less reply form: [len][ASCII] (the 0x86 build date).
            n = msg.data[0]
            if 3 <= n <= 64 and len(msg.data) >= n + 1:
                text = _clean_ascii(msg.data[1:1 + n])
                if text is not None:
                    key = IDENTITY_FIELDS.get((msg.iid, None),
                                               "iid_0x%02X" % msg.iid)
                    mod.identity[key] = text

    def handle(self, frame) -> Optional[CDLMessage]:
        """Consume one CDL frame - decoded (CDLMessage) or raw (CdlFrame).

        The raw-capture channel delivers whole receive buffers as CdlFrame;
        the decoded channel delivers CDLMessage. Both end up here so a
        capture session populates the same view as a live one.
        """
        if hasattr(frame, "mid"):
            msg: Optional[CDLMessage] = frame
        else:
            raw = getattr(frame, "raw", b"")
            msg = from_rp1210_buffer(raw, len(raw))
        if msg is None:
            return None
        # Remember read requests seen on the wire (requests from any polling
        # tool), so the replies are recognisable as answers.
        if msg.iid == 0x60 and len(msg.data) >= 2:
            self._pending.add((msg.dest, msg.data[0], msg.data[1]))
        elif msg.iid == 0x20 and msg.data:
            self._pending.add((msg.dest, msg.data[0], None))
        mod = self.modules.setdefault(msg.mid, CdlModule(msg.mid))
        mod.messages += 1
        mod.iids[msg.iid] += 1
        mod.last_data[msg.iid] = msg.data
        if msg.iid in (0xF8, 0x86):
            self._identity_from_reply(msg)
        if msg.iid == 0x82 and msg.dest == TOOL_MID and msg.data:
            self._codes_from_reply(msg)
        # Live parameter replies are addressed to the requester and only count
        # when they ANSWER a read request we observed (the onboard display's
        # 0x20/0x60 poll or our own). Without that gate a message that merely
        # reuses an IID equal to a PID low byte is misread as a value - the
        # loader capture's periodic engine-to-transmission `24 51 400000`
        # (IID 0x40, no request) would otherwise show "Engine Speed 0".
        if msg.dest and msg.dest != msg.mid:
            answered = ((msg.mid, msg.iid, None) in self._pending
                        or (msg.data and
                            (msg.mid, msg.iid, msg.data[0]) in self._pending))
            if answered:
                live = decode_live_reply(msg.iid, msg.data)
                if live is not None:
                    _pid, name, value, unit = live
                    self.live.setdefault(msg.mid, {})[name] = (value, unit)
            elif msg.iid == 0xF1:
                # The multiplexed "broadcast list" the engine pushes to a
                # polling client (MID 13; an onboard display could use it
                # too): ~1 Hz parameter blocks that the CDL client sees
                # because it hears the whole bus. Not a reply to any
                # request, so the
                # request gate does not apply - the block's strict
                # structure IS the evidence (decode_f1_block). Only the
                # PIDs actually observed inside F1 blocks are rendered.
                recs = decode_f1_block(msg.data)
                if recs:
                    for pid in F1_DECODE_OK:
                        if pid not in recs:
                            continue
                        scaled = _scaled_value(pid, recs[pid])
                        if scaled is not None:
                            name, value, unit = scaled
                            self.live.setdefault(msg.mid, {})[name] = (value, unit)
        self.messages += 1
        return msg