"""OpenTruck - UDS module scan (identification only, read-only).

Generic OBD (SAE J1979) only ever addresses 0x7DF / 0x7E0-0x7E7 and only
emissions controllers answer, so a light-duty vehicle shows an ECM and maybe a
TCM while the ABS and body modules stay invisible. They are still on the bus and
most of them speak UDS (ISO 14229); this asks each standard physical address who
it is:

  * ``3E 00`` Tester Present      - "are you there" (the standard keep-alive)
  * ``10 03`` Extended session    - the session OEM identification usually needs
  * ``22 F190`` VIN               - standard identification DID
  * ``22 F187`` software/part no
  * ``22 F18C`` serial number
  * ``22 F191`` hardware number
  * ``19 02 FF`` ReadDTCInformation - the module's stored DTC records

DTC records from ``19 02`` are shown as RAW numbers, never as P/C/B/U codes:
the service is standard (ISO 14229) but the numbering inside it belongs to the
manufacturer. A 2013 Ram TCM answers with ~47 records that look nothing like the
OBD codes for the same transmission, and that truck's ECM refuses ``19``
entirely (NRC 0x11) - running either through a generic P-code table would invent
codes that do not exist.

Nothing is written, cleared or actuated: no ``2E``, ``2F``, ``31``, ``14`` or
``04`` is ever sent. A negative response is reported as a result, not an error -
"NRC 0x12" is how a module that does not support a sub-function says "I am
here", and that is genuinely useful information.

Only the 8 standard diagnostic addresses are probed. A wider sweep is possible
in principle but poking unknown modules can make *other* modules log
communication (U-code) faults, which is not acceptable on a customer vehicle.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# UDS negative response codes we are likely to meet during identification.
NRC_TEXT = {
    0x10: "general reject",
    0x11: "service not supported",
    0x12: "sub-function/format not supported",
    0x13: "incorrect length",
    0x21: "busy, repeat request",
    0x22: "conditions not correct",
    0x24: "request sequence error",
    0x31: "request out of range",
    0x33: "security access denied",
    0x35: "invalid key",
    0x72: "general programming failure",
    0x78: "response pending",
    0x7E: "sub-function not supported in this session",
    0x7F: "service not supported in this session",
}

# Standard identification DIDs (ISO 14229-1 annex C).
IDENT_DIDS = (
    (0xF190, "VIN"),
    (0xF187, "SW / part no"),
    (0xF18C, "Serial no"),
    (0xF191, "HW no"),
)

SCAN_ADDRESSES = tuple(range(0x7E0, 0x7E8))


@dataclass
class ModuleResult:
    """What one physical address said about itself."""

    request_id: int
    response_id: Optional[int] = None
    tester_present: str = ""
    extended_session: str = ""
    dids: dict = field(default_factory=dict)     # DID -> value text or NRC text
    dtcs: list = field(default_factory=list)     # [(dtc_int, status_byte), ...]
    dtc_note: str = ""                           # NRC / "no records" when empty

    @property
    def label(self) -> str:
        return f"0x{self.request_id:03X}"

    @property
    def reply_label(self) -> str:
        return f"0x{self.response_id:03X}" if self.response_id else "-"


def _text(raw: bytes) -> str:
    """ASCII identifier bytes -> readable text (separators become spaces)."""
    out = "".join(chr(b) if 0x20 <= b < 0x7F else " " for b in raw)
    return " ".join(out.split())


def _nrc(payload: bytes) -> Optional[str]:
    """'NRC 0x31 (request out of range)' for a 7F reply, else None."""
    if len(payload) >= 3 and payload[0] == 0x7F:
        code = payload[2]
        return f"NRC 0x{code:02X} ({NRC_TEXT.get(code, 'negative response')})"
    return None


def _exchange(session, phys: int, payload: bytes,
              timeout: float) -> List[Tuple[int, bytes]]:
    """Send one raw UDS request and return every reply (positive and negative)."""
    link = getattr(session, "link", None)
    if link is not None:                     # serial ELM327: it frames for us
        link.cmd(f"AT SH {phys:03X}", timeout=0.5)
        return link.send_receive(payload, timeout=timeout)
    # Raw CAN (RP1210): build the ISO-TP single frame ourselves.
    frame = bytes([len(payload)]) + payload
    session._tx(phys, frame)
    return session._poll(timeout)


def _first_answer(replies) -> Optional[bytes]:
    """The meaningful reply out of a batch: a positive one, else an NRC.

    A slow module answers ``7F xx 78`` (response pending) first and only then
    sends the payload, so the first reply is not necessarily the useful one.
    """
    for _ecu, payload in replies:
        if payload and payload[0] != 0x7F:
            return payload
    for _ecu, payload in replies:
        if len(payload) >= 3 and payload[0] == 0x7F and payload[2] != 0x78:
            return payload
    return replies[0][1] if replies else None


def _parse_dtcs(payload: bytes) -> list:
    """``59 02 <mask>`` followed by 4-byte records: DTC (3 bytes) + status."""
    body = payload[3:]
    records = []
    for i in range(0, len(body) - 3, 4):
        dtc = int.from_bytes(body[i:i + 3], "big")
        records.append((dtc, body[i + 3]))
    return records


def scan(session, addresses=SCAN_ADDRESSES,
         probe_timeout: float = 0.35,
         did_timeout: float = 0.8) -> List[ModuleResult]:
    """Ask each standard diagnostic address to identify itself.

    Returns one entry per address that answered anything at all, in address
    order. Never raises for a silent or refusing module; the transport is reset
    (ELM header back to 0x7DF) before returning.
    """
    results: List[ModuleResult] = []
    link = getattr(session, "link", None)
    try:
        for phys in addresses:
            replies = _exchange(session, phys, b"\x3E\x00", probe_timeout)
            if not replies:
                continue                     # nothing lives at this address
            ecu, payload = replies[0]
            item = ModuleResult(request_id=phys, response_id=ecu)
            nrc = _nrc(payload)
            item.tester_present = nrc or ("yes" if payload[0] == 0x7E else "?")

            replies = _exchange(session, phys, b"\x10\x03", did_timeout)
            if replies:
                _ecu, payload = replies[0]
                nrc = _nrc(payload)
                item.extended_session = nrc or (
                    "yes" if payload[0] == 0x50 else "?")

            for did, _name in IDENT_DIDS:
                req = bytes([0x22, did >> 8, did & 0xFF])
                replies = _exchange(session, phys, req, did_timeout)
                if not replies:
                    item.dids[did] = "-"
                    continue
                _ecu, payload = replies[0]
                nrc = _nrc(payload)
                if nrc:
                    item.dids[did] = nrc
                elif payload[0] == 0x62 and len(payload) > 3:
                    item.dids[did] = _text(payload[3:]) or "(empty)"
                else:
                    item.dids[did] = "(unexpected reply)"

            # Stored DTC records. Generous timeout: a busy module answers with
            # 0x78 (response pending) and then a multi-frame list - the Ram TCM
            # sends 191 bytes, about 33 frames.
            replies = _exchange(session, phys, b"\x19\x02\xFF",
                                max(did_timeout, 1.5))
            payload = _first_answer(replies) if replies else None
            nrc = _nrc(payload) if payload else None
            if payload is None:
                item.dtc_note = "no answer"
            elif nrc:
                item.dtc_note = nrc
            elif payload[0] == 0x59 and len(payload) > 3:
                item.dtcs = _parse_dtcs(payload)
                item.dtc_note = "" if item.dtcs else "no records"
            else:
                item.dtc_note = "(unexpected reply)"
            results.append(item)
    finally:
        if link is not None:
            try:
                link.cmd("AT SH 7DF", timeout=0.5)   # restore OBD addressing
            except Exception:                        # noqa: BLE001
                pass
    return results
