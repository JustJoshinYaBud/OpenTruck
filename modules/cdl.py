"""OpenTruck - Cat Data Link (CDL) decode + CdlSession.

The CDL is CAT's proprietary 9600-baud RS-485 link that carries the machine
controllers of a CAT machine (implement, hydraulics, payload - and on many
machines the engine ECM as well). Those controllers never appear on J1939,
which is why a J1939-only view of a CAT machine shows a handful of modules
while CAT ET sees them all.

Evidence base (live capture 2026-11-13, aux engine via the CA3's 'CAT'
protocol, 74 buffers / 3 message groups): the RP1210 receive buffer is

    [0:4]  receive timestamp, little-endian (free-running, NOT wall clock)
    [4]    MID  - module identifier (0x24 = 36 = "Engine Control #1")
    [5]    destination (0x00 = broadcast on every message observed)
    [6]    IID  - instruction identifier (0xF3, 0xFA, 0xFC observed)
    [7:]   data

which matches CAT's documented CDL header shape [MID][destination][IID]
[optional length][data][checksum] (CCM protocol manual; "zz is the number of
bytes in the message after this byte... checksum is a 2's complement"). No
trailing checksum byte validated on any range tested, so the CA3 appears to
strip/handle the checksum itself - every byte after the IID is kept verbatim
as data, and NOTHING is guessed:

Further observed on a wheel loader (2026-11-13, 19,449 buffers /
180 s): byte 2 is a REAL destination MID, not always broadcast - the
controllers talk to each other (engine 36 <-> transmission 81 <-> Graphical
Display 53, e.g. `24 51 A2 ...`, `51 35 A2 ...`); broadcast frames keep
dest = 0x00. IID 162 (0xA2) is the documented "length-then-data" form
(`[MID][dest][A2][len][data]`, every observed length consistent), and
IID 248 from the display carried an ASCII serial/part string
("MJC00494"). The loader's MIDs: 36 Engine Control #1, 53 Graphical
Display Module, 81 Transmission Control, 122 Product Link Module.
NO IID 15 (diagnostic codes) appears spontaneously - codes are only sent
when requested via IID 82, exactly as the CCM manual documents.

  * the meaning of the broadcast IIDs (0xA2, 0xF3, 0xF8, 0xFA, 0xFC, 0x60
    and friends) is not yet verified, so they are counted, shown and logged
    but never interpreted;
  * diagnostic codes arrive as IID 15 (per the same manual, requested via
    IID 82 "Request to Broadcast Diagnostic Codes") - NOT decoded until a
    live capture shows the real packed format.

Keep it that way: the CDL rules are the same rules the raw-CAN wire formats
followed (see NOTES.md) - decode only what real bytes proved.
"""
from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Optional

from lookup.oem_cat import CAT_CDL_MID, CAT_CDL_FMI, CAT_PID

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
# 2026-11-13): an onboard service interface (MID 13, the reserved
# "Cat Electronic Technician" address) polls the engine (MID 36) with
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
# MID 13 (CAT ET's slot, which may collide with an onboard poller).
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


def build_read_request(target: int, iid: int, sub: Optional[int] = None) -> bytes:
    """One CDL read request in the wire-verified raw framing.

    Sub form:    [TOOL_MID][target][0x60][iid][sub]  (the identity reads).
    Sub-less:   [TOOL_MID][target][0x20][iid]  (the 0x86 build date; the
                PID 0x0082 diagnostic-codes read).
    """
    if sub is None:
        return bytes([TOOL_MID, target, 0x20, iid])
    return bytes([TOOL_MID, target, 0x60, iid, sub])


def decode_codes(data: bytes) -> list[dict]:
    """Decode a PID 0x0082 "Diagnostic Codes" reply payload.

    LIVE + DOCUMENTED (SEBU7014 "Diagnostic Codes - Retrieve"; wire
    evidence 2026-11-13): [len][record]... with each record [CID hi][CID lo]
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
        self.live: dict[int, dict] = {}      # no CDL parameters decoded yet
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

    def set_sender(self, fn: Callable[[bytes], Optional[int]]) -> None:
        """Register the transmit callback (CombinedSource.send_cdl) and
        reset the poll state - one poll campaign per connection."""
        self._send = fn
        self._tx_ok = True
        self._queue.clear()
        self._identity_polled.clear()
        self._last_codes.clear()

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
        # Remember read requests seen on the wire (an onboard tool or CAT ET
        # polling identities), so the replies are recognisable as answers.
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
        self.messages += 1
        return msg