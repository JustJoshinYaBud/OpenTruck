"""OpenTruck - UDS (ISO 14229) over ISO-TP, for reading VIN / identification.

Many modern engines and controllers answer a UDS "Read Data By Identifier"
request for the VIN (DID 0xF190) even when they NACK the J1939 Vehicle
Identification PGN (65260). This module speaks the UDS-on-J1939 variant
(ISO 14229-5): requests are addressed with the 29-bit ID ``0x18DA<DA><SA>``
(PGN 0x00DA00), and multi-byte replies are carried by ISO-TP (ISO 15765-2),
which we reassemble here (the RP1210 adapter only reassembles J1939 TP, not
ISO-TP).

The caller supplies any frame source that implements
``write_frame(Frame)`` and ``read_frame() -> Frame | None`` (e.g. an
``RP1210Source`` configured for J1939).

Note: support is vehicle-specific. On some trucks the engine answers neither
J1939 VI nor UDS at all, and only another module (e.g. the transmission)
speaks UDS - possibly without the VIN DID. This module simply reports
"no VIN" in that case; it cannot invent data the bus does not carry.
"""
from __future__ import annotations

import time
from typing import Optional

from modules.j1939 import Frame

# UDS-on-J1939 addressing (ISO 14229-5): 0x18DA<DA><SA> / 0x18DB<DA><SA>.
UDS_PHYSICAL_PGN = 0x00DA00
UDS_FUNCTIONAL_PGN = 0x00DB00
DEFAULT_TOOL_SA = 0xF9          # "off-board diagnostics tool #1"

# Standard identification DIDs (ISO 14229-1 Annex C / common OEM use).
DID_VIN = 0xF190                # Vehicle Identification Number
DID_VIN_ALT = 0xF194            # some OEMs use this for the VIN
DID_SPARE_PART = 0xF187
DID_SUPPLIER = 0xF18A           # "System Supplier Identifier" (e.g. WABCO)
DID_SERIAL = 0xF18C
DID_HW_VM = 0xF191
DID_HW_SUPPLIER = 0xF192

# Positive service id is request + 0x40; negative is 0x7F.
_SID_READ_DID = 0x22
_SID_SESSION = 0x10
_NRC_NAMES = {
    0x10: "generalReject",
    0x11: "serviceNotSupported",
    0x12: "subFunctionNotSupported",
    0x13: "incorrectMessageLength",
    0x22: "conditionsNotCorrect",
    0x31: "requestOutOfRange",
    0x33: "securityAccessDenied",
    0x78: "responsePending",
}


class IsoTp:
    """Minimal ISO-TP (ISO 15765-2) client side: send a request, reassemble the
    reply. Only what a short diagnostic read needs (single-frame requests,
    first/consecutive-frame replies, one flow-control frame)."""

    def __init__(self, source, target: int, source_addr: int = DEFAULT_TOOL_SA,
                 pgn: int = UDS_PHYSICAL_PGN) -> None:
        self._src = source
        self._target = target & 0xFF
        self._sa = source_addr & 0xFF
        self._pgn = pgn

    def _send(self, payload: bytes) -> None:
        self._src.write_frame(Frame(
            pgn=self._pgn, source=self._sa, destination=self._target,
            priority=6, data=bytes(payload),
        ))

    def _recv(self, timeout: float) -> Optional[bytes]:
        """Return the next ISO-TP frame payload addressed back to us, or None."""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            f = self._src.read_frame()
            if f is None:
                time.sleep(0.002)
                continue
            if f.pgn == self._pgn and f.destination == self._sa:
                return bytes(f.data)
        return None

    def request(self, uds: bytes, timeout: float = 0.8) -> Optional[bytes]:
        """Transmit a UDS request (<=7 bytes, sent as one ISO-TP single frame)
        and return the reassembled UDS reply, or None on no response."""
        if not 0 < len(uds) <= 7:
            raise ValueError("request must be 1..7 bytes for single-frame ISO-TP")
        self._send(bytes([len(uds)]) + bytes(uds))
        first = self._recv(timeout)
        if first is None:
            return None
        pci = first[0]
        kind = pci >> 4
        if kind == 0:                                   # single frame
            return first[1:1 + (pci & 0x0F)]
        if kind == 1:                                   # first frame -> reassemble
            length = ((pci & 0x0F) << 8) | first[1]
            self._send(bytes([0x30, 0x00, 0x00]))       # flow control: continue
            buf = bytearray(first[2:8])
            while len(buf) < length:
                cf = self._recv(timeout)
                if cf is None:
                    break
                if (cf[0] >> 4) == 2:                   # consecutive frame
                    buf += cf[1:8]
            return bytes(buf[:length])
        return bytes(first)


def _text(data: bytes) -> str:
    """Trim trailing 0x00/0xFF padding and decode as ASCII."""
    return data.decode("ascii", "replace").replace("\x00", "").strip()


class UdsClient:
    """Reads identification DIDs from one ECU over UDS-on-J1939."""

    def __init__(self, source, target: int,
                 source_addr: int = DEFAULT_TOOL_SA) -> None:
        self.tp = IsoTp(source, target, source_addr)
        self.target = target

    def read_did(self, did: int, timeout: float = 0.8) -> Optional[bytes]:
        """Read one DID; returns its data bytes, or None (no/negative reply)."""
        resp = self.tp.request(
            bytes([_SID_READ_DID, (did >> 8) & 0xFF, did & 0xFF]), timeout)
        if not resp or len(resp) < 3:
            return None
        if resp[0] == _SID_READ_DID + 0x40 and resp[1] == (did >> 8) & 0xFF \
                and resp[2] == did & 0xFF:
            return resp[3:]
        return None

    def negative_response(self, did: int, timeout: float = 0.8) -> Optional[str]:
        """If the DID read is refused, return the NRC name (diagnostic aid)."""
        resp = self.tp.request(
            bytes([_SID_READ_DID, (did >> 8) & 0xFF, did & 0xFF]), timeout)
        if resp and resp[0] == 0x7F and len(resp) >= 3:
            nrc = resp[2]
            return f"0x{nrc:02X} {_NRC_NAMES.get(nrc, '')}".strip()
        return None

    def read_vin(self, timeout: float = 0.8) -> Optional[str]:
        """Try DID 0xF190 then 0xF194; return a 17-char VIN or None."""
        for did in (DID_VIN, DID_VIN_ALT):
            data = self.read_did(did, timeout)
            if data:
                vin = _text(data)
                if len(vin) >= 17:
                    return vin[:17]
        return None

    def read_supplier(self, timeout: float = 0.8) -> Optional[str]:
        """DID 0xF18A = System Supplier Identifier (the real vendor name)."""
        data = self.read_did(DID_SUPPLIER, timeout)
        return _text(data) if data else None


def open_extended_session(client: UdsClient, timeout: float = 0.6) -> bool:
    """Send DiagnosticSessionControl (0x10 0x03); True on a positive reply."""
    resp = client.tp.request(bytes([_SID_SESSION, 0x03]), timeout)
    return bool(resp) and resp[0] == _SID_SESSION + 0x40


def find_vin(source, targets, source_addr: int = DEFAULT_TOOL_SA,
             timeout: float = 0.8, log=None) -> Optional[tuple[str, int]]:
    """Scan ``targets`` for a UDS VIN. Returns (vin, target) or None."""
    for target in targets:
        client = UdsClient(source, target, source_addr)
        if log:
            log(f"  UDS: probing 0x{target:02X} for VIN...")
        vin = client.read_vin(timeout)
        if vin:
            return vin, target
    return None
