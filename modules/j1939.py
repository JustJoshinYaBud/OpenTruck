"""OpenTruck - SAE J1939 protocol decoding (J1939-21, -71, -73, -81).

Hardware-agnostic: everything here operates on decoded 29-bit CAN frames, so
the same code works whether frames come from an RP1210 adapter, a raw CAN
dongle, or a replay log.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Callable, Optional


class PGN(IntEnum):
    ADDRESS_CLAIMED = 0x00EE00   # 60928  NAME broadcast (J1939-81)
    REQUEST         = 0x00EA00   # 59904  "request" (e.g. re-claim addresses)
    TP_CM           = 0x00EC00   # 60416  Transport Protocol - Connection Mgmt
    TP_DT           = 0x00EB00   # 60160  Transport Protocol - Data Transfer
    DM1             = 0xFECA     # 65226  Active DTCs (+ lamp status)
    DM2             = 0xFECB     # 65227  Previously active DTCs
    DM3             = 0xFECC     # 65228  DTC clear request/response
    DM11            = 0xFED3     # 65235  Diagnostic Data Clear/Reset for ACTIVE DTCs
    DM55            = 0xFCD3     # 64723  Diagnostic Data Clear/Reset for SERVICE-ONLY DTCs
    DM22            = 0xC300     # 49920  Individual Clear/Reset of one Active/Previously-Active DTC
    CI              = 0xFEEB     # 65259  Component Identification (make/model/serial)
    VI              = 0xFEEC     # 65260  Vehicle Identification (VIN)
    SOFTWARE_ID     = 0xFEDA     # 65242  Software Identification (SPN 234)
    ECU_ID          = 0xFDED     # 65005  ECU Identification (part/serial/location/type)
    ACK             = 0x00E800   # 59392  Acknowledgement (J1939-73)
    # --- live data examples (for later) ---
    EEC1            = 0xF004     # 61444  engine speed / driver demand torque
    ECT1            = 0xFEEE     # 65262  coolant temp / fuel rate
    VDH             = 0xFEF1     # 65265  vehicle distance / road speed
    AMB             = 0xFEF5     # 65269  ambient air temp / baro pressure
    EBC1            = 0xF001     # 61441  brakes/ABS status + brake pedal position
    WHEEL_SPEED     = 0xFEBF     # 65215  wheel speed information (SPN 904)
    TC1             = 0x00100    # 256    transmission control 1 (requests)
    ETC7            = 0xFE4A     # transmission warning/service indicators
    PTO             = 0xFEF0     # power takeoff speed / oil temp
    BRAKES1         = 0xFEFA     # brake application pressure etc.
    AIR_SUPPLY      = 0xFEAE     # pneumatic / service-brake air pressure
    VEHICLE_HOURS   = 0xFEE7     # total vehicle + PTO hours
    RC              = 0xFEE1     # retarder config: reference retarder torque
    EC1             = 0xFEE3     # engine config: idle speed, reference torque
    AT1TI           = 0xFD79     # DPF regeneration trip statistics


# J1939-73 Acknowledgement (PGN 0x00E800) control bytes. An ECU answers a
# request with one of these: a plain ACK, or a NACK reporting that the answer is
# merely late ("response pending"), refused, or impossible. They matter in
# practice: an ECU that cannot answer a VIN / DM2 request within one poll sends
# "response pending" first and the data afterwards, so a tool that ignores the
# acknowledgement reports "no data" for a controller that is about to reply.
ACK_CONTROL = {
    0: "ACK",
    1: "NACK - response pending",
    2: "NACK - access denied",
    3: "NACK - cannot respond",
}
ACK_RESPONSE_PENDING = 1


def decode_ack(data: bytes) -> Optional[dict]:
    """Decode an Acknowledgement payload.

    J1939-73 layout: ``[0]`` control byte, ``[1]`` group-function value,
    ``[2:5]`` reserved (0xFF), ``[5:8]`` the acknowledged PGN (little-endian).
    Returns ``{"control", "name", "pgn"}`` or None for a short frame.
    """
    if len(data) < 8:
        return None
    control = data[0]
    return {
        "control": control,
        "name": ACK_CONTROL.get(control, f"control {control}"),
        "pgn": int.from_bytes(data[5:8], "little"),
    }


@dataclass
class Frame:
    pgn: int                 # Parameter Group Number (18-bit)
    data: bytes
    source: int = 0          # source address (the ECU that sent it)
    destination: int = 0xFF  # destination address (0xFF = broadcast)
    priority: int = 6
    timestamp: float = 0.0

    @classmethod
    def from_arbid(cls, arbid: int, data: bytes, timestamp: float = 0.0) -> "Frame":
        """Build a Frame from a raw 29-bit CAN identifier."""
        return cls(
            pgn=pgn_from_id(arbid),
            data=data,
            source=arbid & 0xFF,
            destination=(arbid >> 8) & 0xFF,
            priority=(arbid >> 26) & 0x07,
            timestamp=timestamp,
        )

    def to_arbid(self) -> int:
        """Reconstruct the 29-bit CAN identifier (inverse of `from_arbid`)."""
        pgn = self.pgn
        edp = (pgn >> 17) & 0x01
        dp = (pgn >> 16) & 0x01
        pf = (pgn >> 8) & 0xFF
        ps = pgn & 0xFF
        # PDU1 (pf < 0xF0): PS field is actually the destination address.
        mid = (self.destination & 0xFF) if pf < 0xF0 else ps
        return ((self.priority & 0x07) << 26) | (edp << 25) | (dp << 24) \
               | (pf << 16) | (mid << 8) | (self.source & 0xFF)

    def to_log_line(self) -> str:
        """Serialize for the replay/log format: ``<arbid_hex>:<data_hex>``."""
        return f"{self.to_arbid():08X}:{self.data.hex().upper()}"


def pgn_from_id(arbid: int) -> int:
    """Extract the 18-bit Parameter Group Number from a 29-bit CAN id.

    The identifier is priority(3) | EDP(1) | DP(1) | PF(8) | PS(8) | SA(8), so
    a PGN is 18 bits: EDP (bit 17), DP (bit 16), PF, PS. J1939 requires EDP to
    be 0, but it is carried through rather than masked away - a non-conforming
    frame then round-trips honestly instead of collapsing into the standard PGN
    that happens to share its DP/PF/PS bits.
    """
    pf = (arbid >> 16) & 0xFF
    ps = (arbid >> 8) & 0xFF
    edp = (arbid >> 25) & 0x01
    dp = (arbid >> 24) & 0x01
    if pf < 0xF0:                        # PDU1: destination-specific (PS == DA)
        return (edp << 17) | (dp << 16) | (pf << 8)
    return (edp << 17) | (dp << 16) | (pf << 8) | ps   # PDU2: broadcast


# --------------------------------------------------------------------------- #
# NAME decoding (J1939-81): what kind of ECU is on each address               #
# --------------------------------------------------------------------------- #

@dataclass
class Name:
    identity: int
    manufacturer: int
    ecu_instance: int
    function_instance: int
    function: int
    vehicle_system: int
    industry_group: int
    arbitrary_addr_capable: bool


def decode_name(data: bytes) -> Name:
    """Decode a 64-bit J1939 NAME (8 bytes little-endian) from an Address
    Claimed message payload."""
    n = int.from_bytes(data[:8], "little")
    return Name(
        identity               = n & 0x1FFFFF,
        manufacturer           = (n >> 21) & 0x7FF,
        ecu_instance           = (n >> 32) & 0x07,
        function_instance      = (n >> 35) & 0x1F,
        function               = (n >> 40) & 0xFF,
        vehicle_system         = (n >> 49) & 0x0F,
        industry_group         = (n >> 58) & 0x1F,
        arbitrary_addr_capable = bool((n >> 63) & 0x01),
    )


# Subset of the SAE J1939-71 "Function" field. Extend from the full table if
# you need more (the values below are the well-known heavy-duty ones).
FUNCTION_NAMES = {
    0:  "Engine",
    3:  "Transmission",
    5:  "Gear Shift Control",
    11: "Brakes - System Controller (ABS/EBS)",
    12: "Brakes - Steer Axle Controller",
    13: "Brakes - Drive Axle Controller",
    15: "Retarder - System Controller",
    17: "Suspension - System Controller",
    19: "Steering Controller",
    21: "Instrument Cluster",
    22: "Vehicle Body Controller",
    28: "Tire Pressure Monitor",
    31: "Tachograph",
    33: "Body Controller",
    37: "Virtual Terminal",
}


def function_name(function: int) -> str:
    return FUNCTION_NAMES.get(function, f"Function {function} (unknown)")


def encode_name(identity: int, manufacturer: int = 0, ecu_instance: int = 0,
                function_instance: int = 0, function: int = 0,
                vehicle_system: int = 0, industry_group: int = 0,
                arbitrary_addr_capable: bool = True) -> bytes:
    """Build the 8-byte J1939 NAME (inverse of :func:`decode_name`)."""
    n = ((identity & 0x1FFFFF)
         | ((manufacturer & 0x7FF) << 21)
         | ((ecu_instance & 0x07) << 32)
         | ((function_instance & 0x1F) << 35)
         | ((function & 0xFF) << 40)
         | ((vehicle_system & 0x0F) << 49)
         | ((industry_group & 0x1F) << 58)
         | ((1 if arbitrary_addr_capable else 0) << 63))
    return n.to_bytes(8, "little")


def build_address_claim(source: int, name: bytes,
                        priority: int = 6) -> "Frame":
    """An Address Claimed frame (PGN 0x00EE00) for ``source`` (J1939-81)."""
    return Frame(pgn=PGN.ADDRESS_CLAIMED, data=bytes(name[:8]), source=source,
                 destination=0xFF, priority=priority)


# The tool's J1939-81 identity on the bus: ONE NAME, shared by everything
# that ever claims an address for OpenTruck (the RP1210 ProtectJ1939Address
# command AND the on-wire Address Claimed broadcast).
#
# J1939-81 section 4.1.2: "A CA claiming a preferred address in the range 0 to
# 127 and 248 to 253 must perform the function defined for that preferred
# address and specify that Function within its NAME. Other CAs may assume
# that to be the case." OpenTruck claims 0xF9 (249, "Off-Board Diagnostic
# Tool #1"), so the NAME must declare the tool function - for industry group
# 0 / vehicle system 0 that is function 129, "Off-board Service Tool" (the
# same function a Dearborn DPA service-tool node declares). Claiming 0xF9
# while declaring function 0 ("Engine") - an earlier bug here - breaks that
# rule, and a strict ECU that takes the standard at its word can react badly
# to an "engine" sitting at the tool address.
#
# Manufacturer code 0 is "experimental or developmental" - honest for a
# community tool, and it cannot collide with a real vendor's code. The
# arbitrary-address-capable bit is deliberately 0: that bit PROMISES the
# node will move to an address in 128..247 if it loses a claim, and this tool
# does not do that (a refused claim means receive-only), so setting it would
# be another lie on the bus.
TOOL_IDENTITY = 0x0F9001
TOOL_FUNCTION = 0x81          # 129 = "Off-board Service Tool" (IG 0 / VS 0)


def offboard_tool_name(identity: int = TOOL_IDENTITY) -> bytes:
    """The 8-byte J1939-81 NAME for this tool (see the notes above)."""
    return encode_name(identity=identity, manufacturer=0, ecu_instance=0,
                      function_instance=0, function=TOOL_FUNCTION,
                      vehicle_system=0, industry_group=0,
                      arbitrary_addr_capable=False)


# Preferred source addresses (SAE J1939-71 "Preferred Addresses"). Used as a
# *fallback* label for a module whose NAME (address-claim) was never captured
# and that has no Component Identification - the NAME/CI identity always wins.
#
# NOTE: these are preferences, not guarantees. ECUs may use any address, and
# OEMs do reuse them (one truck's 0x0F really is the engine retarder; another
# puts a brake controller there), which is why this is only a last resort.
PREFERRED_ADDRESS_NAMES = {
    0x00: "Engine #1",
    0x01: "Engine #2",
    0x02: "Turbocharger",
    0x03: "Transmission #1",
    0x04: "Transmission #2",
    0x05: "Shift Console - Primary",
    0x06: "Shift Console - Secondary",
    0x07: "Power Take Off (main or rear)",
    0x08: "Axle - Steering",
    0x09: "Axle - Drive #1",
    0x0A: "Axle - Drive #2",
    0x0B: "Brakes - System Controller (ABS)",
    0x0C: "Brakes - Steer Axle",
    0x0D: "Brakes - Drive Axle #1",
    0x0E: "Brakes - Drive Axle #2",
    0x0F: "Retarder - Engine",
    0x10: "Retarder - Driveline",
    0x11: "Cruise Control",
    0x12: "Fuel System",
    0x13: "Steering Controller",
    0x14: "Suspension - Steer Axle",
    0x15: "Suspension - Drive Axle #1",
    0x16: "Suspension - Drive Axle #2",
    0x17: "Instrument Cluster",
    0x18: "Trip Recorder",
    0x19: "Passenger / Operator Climate Control",
    0x1A: "Electrical Charging System",
    0x1B: "Aerodynamic Control",
    0x1C: "Vehicle Navigation",
    0x1D: "Vehicle Security",
    0x1E: "Electrical System",
    0x1F: "Starter System",
    0x20: "Tractor-Trailer Bridge #1",
    0x21: "Body Controller",
    0x22: "Auxiliary Valve Control",
    0x23: "Hitch Control",
    0x24: "Power Take Off (front or secondary)",
    0x25: "Off-Vehicle Gateway",
    0x26: "Virtual Terminal",
    0x27: "Management Computer #1",
    0xF9: "Off-Board Diagnostic Tool #1",
}


def preferred_address_name(address: int) -> Optional[str]:
    """Common name for a fixed/preferred source address, or None."""
    return PREFERRED_ADDRESS_NAMES.get(address)


# --------------------------------------------------------------------------- #
# DTC decoding (J1939-73): DM1 / DM2 payload -> SPN + FMI list                #
# --------------------------------------------------------------------------- #

@dataclass
class DTC:
    spn: int                 # Suspect Parameter Number (19 bits)
    fmi: int                 # Failure Mode Identifier (5 bits)
    occurrence: int          # Occurrence Count (7 bits)
    conversion_method: int   # SPN Conversion Method (1 bit)


def decode_dtc(b: bytes) -> DTC:
    # J1939-73: SPN bits 16-18 are the TOP 3 bits of byte 2 (bits 7..5) and
    # FMI is the BOTTOM 5 bits (4..0). A previous revision had these swapped.
    spn = b[0] | (b[1] << 8) | ((b[2] >> 5) << 16)
    return DTC(
        spn=spn,
        fmi=b[2] & 0x1F,
        occurrence=b[3] & 0x7F,
        conversion_method=(b[3] >> 7) & 0x01,
    )


def decode_lamp_status(b: bytes) -> dict:
    """Decode the 2-byte Lamp Status / Flash field at the head of a DM1/DM2."""
    if len(b) < 2:
        return {}
    b0, b1 = b[0], b[1]
    # J1939-73: 2 bits per lamp. Byte 0 (LSB-first): bits 1-0 protect,
    # 3-2 amber, 5-4 red, 7-6 MIL; byte 1 = the matching "flash" fields.
    # Status: 0b01=on, 0b00=off, 0b10=error, 0b11=not-available.
    # Flash:  0b00=slow flash, 0b01=fast flash, 0b10=reserved, 0b11=n/a.
    on = lambda v: v == 0x01
    flash = lambda v: (v & 0x02) == 0
    return {
        "protect":       on(b0 & 0x03),
        "amber":         on((b0 >> 2) & 0x03),
        "red":           on((b0 >> 4) & 0x03),
        "mil":           on((b0 >> 6) & 0x03),
        "protect_flash": flash(b1 & 0x03),
        "amber_flash":   flash((b1 >> 2) & 0x03),
        "red_flash":     flash((b1 >> 4) & 0x03),
        "mil_flash":     flash((b1 >> 6) & 0x03),
    }


def is_null_dtc(dtc: DTC) -> bool:
    """True for the J1939-73 "no active DTC" placeholder (SPN & FMI all-ones)
or the SPN=0/FMI=0 convention. These mean "no fault", not a real fault."""
    return (dtc.spn == 0x7FFFF and dtc.fmi == 31) or (dtc.spn == 0 and dtc.fmi == 0)


def parse_dm_payload(data: bytes) -> tuple[dict, list[DTC]]:
    """Parse a DM1/DM2 payload -> (lamps, [DTC, ...]) (null DTCs dropped)."""
    lamps = decode_lamp_status(data[:2])
    dtcs = [
        d
        for i in range(2, len(data) - 3, 4)
        for d in [decode_dtc(data[i:i + 4])]
        if not is_null_dtc(d)
    ]
    return lamps, dtcs


# --------------------------------------------------------------------------- #
# Transport Protocol (J1939-21): reassemble multi-frame messages              #
# --------------------------------------------------------------------------- #

# TP.CM control bytes (first data byte of a Connection-Management frame).
TP_RTS   = 0x10   # Request To Send  (peer-to-peer; receiver answers with CTS)
TP_CTS   = 0x11   # Clear To Send    (we SEND this)
TP_EOMA  = 0x13   # End Of Message Acknowledgement
TP_BAM   = 0x20   # Broadcast Announce Message (no handshake)
TP_ABORT = 0xFF   # session abort

# A session that stops receiving DT frames is dropped after this long, so a
# half-finished transfer cannot block the source address for ever.
TP_SESSION_TIMEOUT = 12.0


class TransportProtocol:
    """Reassembles multi-packet J1939 messages (J1939-21).

    DM1/DM2 with many DTCs, VIN, component ID and long live-data groups all
    exceed one 8-byte frame. J1939-21 defines two transfer modes:

    * **BAM** (control 0x20) - broadcast, no handshake. Works from a bus tap or
      a replay log, because nothing has to be transmitted.
    * **RTS/CTS** (control 0x10) - peer-to-peer, used whenever a *directed*
      request produces a multi-frame answer. The receiver must answer the
      sender's Request-To-Send with a Clear-To-Send before any data flows, and
      acknowledge completion with an End-Of-Message-ACK. Adapters that
      reassemble in firmware hide all of this; a raw-CAN path does not, and
      without it a directed VIN / component-ID / long-DM2 reply can never be
      collected at all.

    ``send`` is an optional callable used for the two frames a receiver must
    transmit. When it is None (replay, simulator, passive capture) BAM still
    reassembles and RTS sessions are tracked but left unanswered.
    """

    def __init__(self, source_address: Optional[int] = None,
                 send: Optional[Callable[["Frame"], None]] = None) -> None:
        self.source_address = source_address
        self.send = send
        self._sessions: dict[int, dict] = {}

    # -- inbound ---------------------------------------------------------- #
    def feed(self, frame: Frame) -> Optional[tuple[int, bytes]]:
        """Feed TP.CM / TP.DT frames.

        Returns (pgn, full_payload) when a message is complete, else None.
        """
        if frame.pgn == PGN.TP_CM:
            return self._connection_management(frame)
        if frame.pgn == PGN.TP_DT:
            return self._data_transfer(frame)
        return None

    def _connection_management(self, frame: Frame) -> Optional[tuple[int, bytes]]:
        """An RTS or BAM announce opens a session; CTS/EOMA/abort do not."""
        data = frame.data
        if len(data) < 8:
            return None
        ctrl = data[0]
        if ctrl in (TP_BAM, TP_RTS):
            size    = int.from_bytes(data[1:3], "little")
            packets = data[3]
            pgn     = int.from_bytes(data[5:8], "little")
            self._sessions[frame.source] = {
                "pgn": pgn, "size": size, "packets": packets,
                "chunks": {}, "started": time.monotonic(),
                "rts": ctrl == TP_RTS,
            }
            if ctrl == TP_RTS:
                self._send_cts(frame)
            return None
        if ctrl == TP_ABORT:
            self._sessions.pop(frame.source, None)
        return None

    def _send_cts(self, rts: Frame) -> None:
        """Answer a Request-To-Send with a Clear-To-Send for the whole message.

        A J1939-21 message is at most 255 packets, which fits the single
        "number of packets that can be sent" byte, so one CTS is enough - no
        windowed flow control is needed.
        """
        session = self._sessions.get(rts.source)
        if self.send is None or session is None:
            return
        # Reply from the address the RTS was addressed to: that is us.
        source = self.source_address
        if source is None:
            source = rts.destination if rts.destination not in (0xFE, 0xFF) else 0xF9
        allowed = min(session["packets"], 0xFF)
        frame = Frame(
            pgn=PGN.TP_CM, source=source, destination=rts.source, priority=6,
            data=bytes([TP_CTS, allowed, 1, 0xFF, 0xFF])
                 + session["pgn"].to_bytes(3, "little"),
        )
        try:
            self.send(frame)
        except Exception:          # noqa: BLE001 - a failed CTS is never fatal
            pass

    def _data_transfer(self, frame: Frame) -> Optional[tuple[int, bytes]]:
        session = self._sessions.get(frame.source)
        if session is None:
            return None
        if time.monotonic() - session["started"] > TP_SESSION_TIMEOUT:
            del self._sessions[frame.source]
            return None
        seq = frame.data[0]
        session["chunks"][seq] = frame.data[1:]
        if len(session["chunks"]) < session["packets"]:
            return None
        payload = bytearray()
        for i in range(1, session["packets"] + 1):
            payload += session["chunks"].get(i, b"")
        del self._sessions[frame.source]
        if session.get("rts"):
            self._send_eoma(frame.source, session)
        return session["pgn"], bytes(payload[:session["size"]])

    def _send_eoma(self, destination: int, session: dict) -> None:
        """Acknowledge a completed RTS/CTS message (End Of Message ACK)."""
        if self.send is None:
            return
        frame = Frame(
            pgn=PGN.TP_CM, source=self.source_address or 0xF9,
            destination=destination, priority=6,
            data=bytes([TP_EOMA])
                 + session["size"].to_bytes(2, "little")
                 + bytes([session["packets"], 0xFF])
                 + session["pgn"].to_bytes(3, "little"),
        )
        try:
            self.send(frame)
        except Exception:          # noqa: BLE001
            pass
