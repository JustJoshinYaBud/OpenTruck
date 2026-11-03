"""OpenTruck CLI - discover modules and list active faults.

Usage:
    python reader.py sample.log      # replay a log (no hardware)
    python reader.py --rp1210        # live, via an RP1210 adapter
    python reader.py --rp1210 --rawlog capture.log --seconds 10
                                     # capture live traffic to a replay log
    python reader.py --sniff --seconds 5
                                     # dump raw adapter bytes (diagnostic)
"""
from __future__ import annotations

import sys
import time
from typing import Optional

from modules.j1939 import (
    Frame, PGN, FUNCTION_NAMES, decode_name, function_name,
    parse_dm_payload, preferred_address_name, TransportProtocol,
    decode_ack, encode_name, build_address_claim, ACK_RESPONSE_PENDING,
    offboard_tool_name,
)
from modules.j1708 import (
    J1587_REQUESTER_MID, PID_VIN, PID_COMPONENT_ID, PID_SOFTWARE_ID,
    build_broadcast_request, build_request,
)
from lookup.spn import spn_name, fmi_name, UNRESOLVED_CODE
from lookup.oem import resolve_code_description
from modules.livedata import decode_live
from framesource import FrameSource, LoggingSource, ReplaySource
from lookup.manufacturers import manufacturer_name, friendly_make, navistar_engine_model
from modules.j1708 import J1708Session
from modules.cdl import CdlSession
from modules.virtual import compute_live

TOOL_ADDRESS = 0xF9   # J1939 "off-board diagnostics tool #1" source address
NULL_ADDRESS = 0xFF   # J1939 reserved "global/null" source address (never a real ECU)

# J1939-81 NAME for the off-board tool, broadcast in our Address Claimed
# message. This is the ONE canonical NAME (modules.j1939.offboard_tool_name),
# shared with the RP1210 ProtectJ1939Address command so the bus never sees
# two different NAMEs for this tool's one address. J1939-81 4.1.2 requires a
# CA at preferred address 249 to declare the tool function in its NAME; the
# old NAME here declared function 0 ("Engine") at the tool address, which is
# exactly what that rule forbids - see the notes at offboard_tool_name().
TOOL_NAME = offboard_tool_name()

# An ECU that answers a request with "NACK - response pending" is telling us it
# has the answer but needs more time. We re-ask on a back-off schedule, at most
# ACK_RETRY_LIMIT times per (address, PGN) pair. This is the practical form of
# the "timer multiplier" elm-style interfaces expose for multi-frame replies.
ACK_RETRY_LIMIT = 3
ACK_RETRY_DELAY_S = 1.5

# Manufacturer codes that are vehicle/engine OEMS, not brake-component
# suppliers. Brake controllers (functions 11/12/13) are actually built by
# Bendix, Haldex, WABCO, Meritor, Knorr-Bremse, ...; when such a module's NAME
# reports an OEM code (Mercedes-Benz=79, Freightliner/Sterling=25, Volvo=60/61,
# PACCAR=45, International=42/43, Mack=37, Ford=23, Kenworth=35, Caterpillar=8,
# Cummins=10) it is a mislabel: the code just names the truck maker that
# *integrated* the brake (e.g. a WABCO HABS on a Sterling reports Mercedes-Benz).
# In that case trust the CI "make" string (the real brake vendor) instead; when
# there is no CI make, leave the vendor blank rather than attribute the brake
# to the truck OEM. Extend the set as more mislabels turn up on real trucks.
OEM_MAKER_CODES = {8, 10, 23, 25, 35, 37, 42, 43, 45, 60, 61, 79}
BRAKE_FUNCTIONS = {11, 12, 13}   # 11=ABS/EBS, 12=steer axle, 13=drive axle


def _decode_ascii_fields(payload: bytes) -> list[str]:
    """Split a J1939 ASCII message on the '*' delimiter (CI/VI format).

    Drops any 0xFF padding beyond the last real byte first.
    """
    cut = payload.find(b"\xff")
    if cut != -1:
        payload = payload[:cut]
    return payload.decode("ascii", "replace").split("*")


class Module:
    def __init__(self, address: int) -> None:
        self.address = address
        self.name = None                # decoded j1939.Name
        self.active_dtcs: list[dict] = []
        self.previous_dtcs: list[dict] = []
        self.lamps: dict = {}
        self.make: Optional[str] = None      # from Component Identification (CI)
        self.model: Optional[str] = None
        self.serial: Optional[str] = None
        self.unit: Optional[str] = None
        self.software_id: Optional[str] = None   # Software Identification (0xFEDA)
        self.ecu_part: Optional[str] = None      # ECU Identification part no (0xFDED)
        self.ecu_serial: Optional[str] = None    # ECU Identification serial no
        # Chassis make (from the VIN WMI), set by the session once known. Lets a
        # maker's own source-address map beat the generic J1939-71 fallback.
        self.vehicle_make: Optional[str] = None

    @property
    def label(self) -> str:
        """Human description: function + vendor + model.

        Resolution order: function from the NAME (address-claim), else from the
        preferred source address; vendor from the manufacturer code, else from
        the CI make string; model from the CI model field. Brake controllers
        that claim an engine maker's code are re-resolved from the CI make
        string. Falls back to "unidentified" when no vendor/role is known.
        """
        func = vendor = model = None

        # Manufacturer code 0 is "experimental/reserved", not a vendor - an ECU
        # that reports it (e.g. a Bosch SCR dosing unit) would otherwise be
        # labelled "For experimental or developmental use only". Prefer the CI
        # make string in that case.
        name_mfr_ok = (self.name is not None and self.name.manufacturer != 0)
        if self.name is not None and name_mfr_ok:
            if self.name.function in FUNCTION_NAMES:
                func = function_name(self.name.function)
            # A brake controller reporting an OEM code is a mislabel (see
            # OEM_MAKER_CODES above). Resolve the real vendor from the CI
            # "make" string; when there is no CI make, leave the vendor blank
            # so we show just the function role rather than mis-naming the
            # brake as "Mercedes-Benz" / "Volvo" / etc.
            mislabeled_brake = (
                self.name.function in BRAKE_FUNCTIONS
                and self.name.manufacturer in OEM_MAKER_CODES
            )
            if mislabeled_brake and self.make:
                vendor = friendly_make(self.make)
            elif not mislabeled_brake and name_mfr_ok:
                vendor = manufacturer_name(self.name.manufacturer)

        if func is None:
            # A chassis maker's own SA map wins over the generic preferred
            # address table (OEMs reuse standard addresses).
            try:
                from lookup.oem import address_label
                func = (address_label(self.address, self.vehicle_make, None)
                        or preferred_address_name(self.address))
            except Exception:      # noqa: BLE001 - labelling must never break decode
                func = preferred_address_name(self.address)

        if vendor is None and self.make:
            vendor = friendly_make(self.make)

        # Bosch SCR dosing units broadcast NAME function 0 ("Engine") but are
        # really exhaust-aftertreatment controllers (CI make "DCU17"...).
        if self.make and self.make.strip().upper().startswith("DCU"):
            func = "Exhaust Aftertreatment (SCR Dosing)"

        if self.model:
            model = self.model.strip()

        desc = " ".join(x for x in (vendor, model) if x) if (vendor or model) else None

        if func and desc:
            return f"{func} \u2014 {desc}"
        if func:
            return func
        if desc:
            return desc
        return "unidentified"

    def __repr__(self) -> str:
        return f"0x{self.address:02X}  {self.label}"


def module_is_useful(module, live_bucket) -> bool:
    """Whether a discovered module is worth showing to the user.

    A module is kept when we can identify it (its label resolves to more than
    "unidentified"), when it currently shows decoded live data, or when it
    reports fault codes. Everything else is an address that merely exists on
    the bus - typically a gateway, relay or controller that answers nothing -
    and is hidden from the module list.

    Hidden modules are NOT dropped from the session: identification requests
    still go to them, so a silent ECU that later answers a CI/VIN request
    becomes visible as soon as it has something to show.
    """
    if getattr(module, "label", "unidentified") != "unidentified":
        return True
    if live_bucket:
        return True
    return bool(getattr(module, "active_dtcs", None)
                or getattr(module, "previous_dtcs", None))


def module_vendor(module) -> Optional[str]:
    """Vendor name for a module: its CI make, else its NAME manufacturer code."""
    make = getattr(module, "make", None)
    if make:
        return friendly_make(make)
    name = getattr(module, "name", None)
    if name is not None:
        return manufacturer_name(name.manufacturer)
    return None


# Engine vendors that ARE the chassis maker (vertically integrated). A Cummins
# or Caterpillar engine says nothing about the chassis - a Freightliner can run
# either - so those must never be used as a chassis-make guess.
_VERTICAL_MAKERS = (
    "INTERNATIONAL", "NAVISTAR", "VOLVO", "MACK", "MERCEDES", "MRCBN",
    "PACCAR", "KENWORTH", "PETERBILT", "SCANIA", "DAF", "HINO", "ISUZU",
)


def chassis_make_from_engine(engine) -> Optional[str]:
    """Chassis maker inferred from the engine module, or None if unreliable."""
    vendor = module_vendor(engine)
    if not vendor:
        return None
    upper = vendor.upper()
    if any(upper.startswith(k) for k in _VERTICAL_MAKERS):
        return vendor
    return None


class Session:
    def __init__(self, source: FrameSource) -> None:
        self.source = source
        # The transport protocol must transmit two frames of its own (CTS and
        # End-Of-Message-ACK) to collect a directed multi-frame reply.
        self.tp = TransportProtocol(source_address=TOOL_ADDRESS,
                                    send=self._send_tp_frame)
        self.modules: dict[int, Module] = {}
        # source address -> { parameter name -> (value, unit) }  (latest live data)
        self.live: dict[int, dict[str, tuple[str, str]]] = {}
        self.vin: str = ""                 # from Vehicle Identification (VI)
        self.chassis_make: Optional[str] = None   # from the VIN WMI
        # J1939-73 acknowledgements: the latest one (surfaced in the GUI) plus
        # the back-off schedule for "response pending" replies.
        self.last_ack: Optional[dict] = None
        self.last_ack_address: Optional[int] = None
        self.ack_serial: int = 0           # bumps on every ACK (GUI change test)
        self._ack_due: dict[tuple[int, int], float] = {}
        self._ack_retries: dict[tuple[int, int], int] = {}
        self._claimed_at: float = 0.0

    def _module(self, address: int) -> Module:
        mod = self.modules.setdefault(address, Module(address))
        if getattr(self, "chassis_make", None) and mod.vehicle_make is None:
            mod.vehicle_make = self.chassis_make
        return mod

    def visible_modules(self) -> dict[int, "Module"]:
        """Modules worth showing (see :func:`module_is_useful`)."""
        return {a: m for a, m in self.modules.items()
                if module_is_useful(m, self.live.get(a))}

    # ------------------------------------------------------ housekeeping --- #
    def _send_tp_frame(self, frame: Frame) -> None:
        """Transmit a frame the transport protocol must answer (CTS / EOMA)."""
        if self.source is not None:
            self.source.write_frame(frame)

    def claim_address(self) -> None:
        """Claim the tool's source address on the bus (J1939-81).

        RP1210's "Protect J1939 Address" command reserves 0xF9 *inside the
        adapter*, which is invisible on the wire: an ECU that filters on
        observed address claims never learns we are here, and some will not
        direct a multi-frame reply to an address they have not seen claim.
        Sending the standard Address Claimed message makes the tool a normal
        bus citizen; a failure is harmless (we simply stay unclaimed).
        """
        if self.source is None:
            return
        try:
            self.source.write_frame(build_address_claim(TOOL_ADDRESS, TOOL_NAME))
            self._claimed_at = time.monotonic()
        except Exception:          # noqa: BLE001 - claiming is best effort
            pass

    def _note_reply(self, address: int, pgn: int) -> None:
        """Record that an address did answer a PGN (clears its ACK back-off)."""
        key = (address, pgn)
        self._ack_retries.pop(key, None)
        self._ack_due.pop(key, None)

    def _store_ack(self, frame: Frame) -> None:
        """Record an ECU's acknowledgement and schedule a retry if it is late.

        A "NACK - response pending" answer means the ECU HAS the data but needs
        more time; re-asking on a back-off is what turns a slow controller into
        a successful identification instead of an empty one. Every other
        acknowledgement is recorded so the GUI can say *why* a request came
        back empty (denied / cannot respond).
        """
        ack = decode_ack(frame.data)
        if ack is None:
            return
        self.last_ack = ack
        self.last_ack_address = frame.source
        self.ack_serial += 1
        if ack["control"] != ACK_RESPONSE_PENDING:
            return
        key = (frame.source, ack["pgn"])
        tries = self._ack_retries.get(key, 0)
        if tries >= ACK_RETRY_LIMIT:
            return
        self._ack_retries[key] = tries + 1
        self._ack_due[key] = time.monotonic() + ACK_RETRY_DELAY_S * (tries + 1)

    def poll(self) -> None:
        """Send any re-requests that have come due (response-pending back-off)."""
        if not self._ack_due:
            return
        now = time.monotonic()
        for key, due in list(self._ack_due.items()):
            if due > now:
                continue
            del self._ack_due[key]
            address, pgn = key
            self._request_pgn(pgn, address)

    def handle(self, frame: Frame) -> None:
        # J1939-73 acknowledgements and "who is there?" address-claim requests
        # are protocol housekeeping, not vehicle data.
        if frame.pgn == PGN.ACK:
            if frame.source not in (TOOL_ADDRESS, NULL_ADDRESS, 0xFE):
                self._module(frame.source)      # it exists; show it
            self._store_ack(frame)
            return

        if frame.pgn == PGN.REQUEST and frame.data[:3] == b"\x00\xee\x00":
            # Another tool asked every ECU to identify itself (J1939-81).
            # Re-claim our address so we are visible to anyone listening.
            if frame.destination in (NULL_ADDRESS, TOOL_ADDRESS):
                if time.monotonic() - self._claimed_at > 1.0:
                    self.claim_address()
            return

        if frame.pgn == PGN.ADDRESS_CLAIMED:
            if frame.source in (TOOL_ADDRESS, NULL_ADDRESS):
                return  # tool (0xF9) or global/null (0xFF) claim — not a real ECU
            m = self._module(frame.source)
            m.name = decode_name(frame.data)
            return

        if frame.pgn in (PGN.TP_CM, PGN.TP_DT):
            result = self.tp.feed(frame)
            if result:
                real_pgn, payload = result
                if real_pgn in (PGN.DM1, PGN.DM2):
                    self._store_dm(frame.source, real_pgn, payload)
                elif real_pgn in (PGN.CI, PGN.VI, PGN.SOFTWARE_ID, PGN.ECU_ID):
                    self._store_ident(frame.source, real_pgn, payload)
                else:
                    # Reassembled multi-frame *live-data* broadcast (>8 bytes):
                    # decode it into the per-module live-data map (some adapters
                    # do this in hardware and never emit TP_CM/TP_DT, but raw
                    # CAN dongles expose the transport protocol to us).
                    vals = decode_live(real_pgn, payload)
                    if vals:
                        bucket = self.live.setdefault(frame.source, {})
                        for name, value, unit in vals:
                            bucket[name] = (value, unit)
                self._note_reply(frame.source, real_pgn)
            return

        if frame.pgn in (PGN.DM1, PGN.DM2):
            self._store_dm(frame.source, frame.pgn, frame.data)
            self._note_reply(frame.source, frame.pgn)
            return

        if frame.pgn in (PGN.CI, PGN.VI, PGN.SOFTWARE_ID, PGN.ECU_ID):
            self._store_ident(frame.source, frame.pgn, frame.data)
            self._note_reply(frame.source, frame.pgn)
            return

        # Live data: decode broadcast PGNs into parameters keyed by source.
        if frame.source not in (TOOL_ADDRESS, NULL_ADDRESS):
            # Register every broadcasting ECU so it appears in the component
            # list even if it never sends an address-claim / DM / CI. (The NULL
            # address 0xFF is reserved for global/NACK responses and is not a
            # real ECU, so it is excluded alongside the tool address.)
            self._module(frame.source)
        vals = decode_live(frame.pgn, frame.data)
        if vals:
            bucket = self.live.setdefault(frame.source, {})
            for name, value, unit in vals:
                bucket[name] = (value, unit)

    def _store_ident(self, address: int, pgn: int, payload: bytes) -> None:
        """Store identification: CI, VI, Software ID (0xFEDA) or ECU ID
        (0xFDED).

        CI / VI / ECU-ID are ASCII fields terminated by the '*' delimiter
        (J1939-71). CI carries make/model/serial/unit; VI carries the 17-char
        VIN; ECU-ID carries part-number/serial/location/type. Software-ID has a
        leading count byte followed by that many '*' delimited strings.
        """
        fields = _decode_ascii_fields(payload)
        if pgn == PGN.VI:
            if fields and fields[0]:
                vin = fields[0].replace("\x00", "").strip()
                # Skip dummy "not programmed" VINs (all zeros) so we don't show
                # "00000000000000000" as if it were the vehicle's VIN.
                if vin and vin != "0" * len(vin):
                    self.vin = vin
                    self._apply_chassis_make(vin)
            return

        if pgn == PGN.SOFTWARE_ID:
            # Software Identification (SPN 234): byte 0 = number of fields,
            # then that many ASCII strings '*' delimited (cal version, checksum
            # etc.). 0xFF count = not available.
            m = self._module(address)
            if not payload or payload[0] in (0x00, 0xFF):
                return
            n = payload[0]
            ids = [s for s in _decode_ascii_fields(payload[1:]) if s]
            joined = " | ".join(ids[:n]) if ids else None
            if joined:
                m.software_id = joined
            return

        if pgn == PGN.ECU_ID:
            # ECU Identification: part number, serial number, location, type
            # (the first two are what we show in the Vehicle panel).
            m = self._module(address)
            m.ecu_part = fields[0] if len(fields) > 0 and fields[0] else m.ecu_part
            m.ecu_serial = fields[1] if len(fields) > 1 and fields[1] else m.ecu_serial
            return

        m = self._module(address)
        m.make = fields[0] if len(fields) > 0 and fields[0] else m.make
        m.model = fields[1] if len(fields) > 1 and fields[1] else m.model
        m.serial = fields[2] if len(fields) > 2 and fields[2] else m.serial
        m.unit = fields[3] if len(fields) > 3 and fields[3] else m.unit
        # Navistar/MaxxForce engines report a raw EDC data-plate string (and
        # sometimes an emissions-cert tail like "CARB ESS EXEMPT") as the model
        # field. Resolve a readable engine-family name from the serial instead.
        family = navistar_engine_model(m.serial)
        if family:
            m.model = family

    def _store_dm(self, address: int, pgn: int, payload: bytes) -> None:
        m = self._module(address)
        lamps, dtcs = parse_dm_payload(payload)
        if pgn == PGN.DM1:
            # DM1 carries the *active* lamp state; DM2 (previously-active) has
            # its own lamp byte that must not clobber the active lamps.
            m.lamps.update(lamps)
        target = m.active_dtcs if pgn == PGN.DM1 else m.previous_dtcs
        target[:] = [{
            "spn": d.spn, "fmi": d.fmi,
            "occ": d.occurrence, "cm": d.conversion_method,
        } for d in dtcs]

    def request_addresses(self) -> None:
        """Ask every ECU to re-broadcast its NAME (Request PGN, global dest)."""
        self.source.write_frame(Frame(
            pgn=PGN.REQUEST, source=TOOL_ADDRESS, destination=0xFF,
            priority=6, data=bytes.fromhex("00EE00"),
        ))

    def _request_pgn(self, pgn: int, address: Optional[int] = None) -> None:
        """Request one PGN globally (default) or directed to one ECU address."""
        dest = address if address is not None else 0xFF
        self.source.write_frame(Frame(
            pgn=PGN.REQUEST, source=TOOL_ADDRESS, destination=dest,
            priority=6, data=pgn.to_bytes(3, "little"),
        ))

    def request_diagnostics(self) -> None:
        """Full discovery pass: address claims, DTCs (DM1/DM2), and
        identification (CI/VI/SW/ECU).

        Some ECUs (notably Caterpillar) answer *only* a request directed to
        their own source address and silently ignore the global (0xFF) request,
        so every PGN is requested both globally and directed to each ECU we
        already know about."""
        for pgn in (PGN.ADDRESS_CLAIMED, PGN.DM1, PGN.DM2, PGN.CI, PGN.VI,
                    PGN.SOFTWARE_ID, PGN.ECU_ID):
            self._request_pgn(pgn)                       # global
            for address in list(self.modules):           # directed, per ECU
                self._request_pgn(pgn, address)

    def run(self, seconds: float = 3.0, request: bool = False,
            request_ident: bool = False) -> None:
        self.source.connect()
        # Claim our source address first (J1939-81), so ECUs that only answer a
        # known/legitimate address have already seen us before the requests go
        # out.
        self.claim_address()
        if request:
            self.request_addresses()
        if request_ident:
            self.request_diagnostics()
        deadline = time.monotonic() + seconds
        last_poll = 0.0
        while time.monotonic() < deadline:
            f = self.source.read_frame()
            if f is not None:
                self.handle(f)
            else:
                time.sleep(0.005)
            # Service the acknowledgement back-off (a "response pending" reply
            # schedules a re-request this releases).
            self.poll()
            # Re-poll on a timer regardless of bus activity so the directed
            # requests fire once modules have been discovered (a busy bus must
            # not prevent the per-ECU directed DM2/DM55 requests from going out).
            if request_ident and time.monotonic() - last_poll > 1.0:
                last_poll = time.monotonic()
                self.request_diagnostics()
        # drain any remaining frames so BAM reassembly / claims finish
        while True:
            f = self.source.read_frame()
            if f is None:
                break
            self.handle(f)
        # No VIN was answered? The engine's CI make still identifies the chassis
        # (falls back inside the helper), so chassis modules get the maker's
        # address map and code tables.
        self._apply_chassis_make(self.vin)
        self.source.close()

    def _apply_chassis_make(self, vin: str) -> None:
        """Name silent modules from the chassis maker's own address map.

        Uses the VIN WMI when there is one; otherwise falls back to the engine's
        CI make, so a truck that answers no VIN (common) still gets its maker's
        address map and code tables applied to its chassis modules.
        """
        chassis = None
        if vin:
            try:
                from lookup.vin import wmi_make
                chassis = wmi_make(vin)
            except Exception:          # noqa: BLE001
                chassis = None
        if not chassis:
            eng = self.modules.get(0x00)
            if eng is not None:
                chassis = chassis_make_from_engine(eng)
        if not chassis:
            return
        self.chassis_make = chassis
        for mod in self.modules.values():
            mod.vehicle_make = chassis

    def report(self) -> None:
        modules = self.visible_modules()
        if not modules:
            print("No J1939 modules discovered.")
            return
        for addr in sorted(modules):
            m = modules[addr]
            lamps = m.lamps
            lamp_str = " ".join(
                k for k, v in lamps.items() if v and not k.endswith("_flash")
            ) or "no lamps"
            print(f"\n=== {m} ===")
            print(f"    lamps: {lamp_str}")
            for kind, items in (("ACTIVE", m.active_dtcs), ("PREVIOUS", m.previous_dtcs)):
                if not items:
                    continue
                print(f"    {kind} DTCs ({len(items)}):")
                for d in items:
                    # Same resolution the GUI uses: the maker's own meaning
                    # first, then the generic SAE name. Pass the module's role
                    # so a strict maker (DTNA) still names its engine codes.
                    component = (function_name(m.name.function)
                                 if m.name is not None
                                 and m.name.function in FUNCTION_NAMES
                                 else preferred_address_name(addr))
                    desc = d.get("desc") or resolve_code_description(
                        d["spn"], d["fmi"], component=component,
                        make=(friendly_make(m.make) if m.make
                              else getattr(m, "vehicle_make", None)),
                        mfr=m.name.manufacturer if m.name is not None else None,
                        cm=d.get("cm", 0))
                    print(f"      SPN {d['spn']:<5} FMI {d['fmi']:<2}  "
                          f"{desc}  [{fmi_name(d['fmi'])}]")


# J1708 MIDs (128..255) occupy the same integer range as J1939 source addresses
# (0..253), so to hold both in one merged dict we shift J1708 keys up by this
# offset. J1939 keys stay 0..253; J1708 keys become J1708_KEY_BASE + MID.
J1708_KEY_BASE = 0x4000

# CDL MIDs (9..255) live in their own range but collide with J1708 MID numbers,
# so merged CDL keys shift up again (see J1708_KEY_BASE for the same reason).
CDL_KEY_BASE = 0x8000


def is_j1708_key(key: int) -> bool:
    """True when a merged module/live key is a J1708 MID (not a J1939 address)."""
    return J1708_KEY_BASE <= key < CDL_KEY_BASE


def j1708_mid(key: int) -> int:
    """Recover a J1708 MID from a merged key."""
    return key - J1708_KEY_BASE


def is_cdl_key(key: int) -> bool:
    """True when a merged module key is a Cat Data Link MID."""
    return key >= CDL_KEY_BASE


def cdl_mid(key: int) -> int:
    """Recover a CDL MID from a merged key."""
    return key - CDL_KEY_BASE


# Keyword hints used to infer why the engine is derating (see _derate_reason).
_AFT_DERATE_HINTS = ("aftertreatment", "dpf", "doc", "scr", "diesel particulate",
                    "def ")
_PROTECT_DERATE_HINTS = ("coolant", "oil pressure", "boost pressure",
                        "intake manifold temperature", "exhaust gas temperature",
                        "engine protection", "oil temperature", "overheat")


def _derate_reason(modules) -> Optional[str]:
    """Best-effort cause of an engine derate, from the active fault-code text.

    DPF/SCR/DEF codes indicate an aftertreatment-induced derate; coolant / oil /
    boost / exhaust-temperature codes indicate an engine-protection derate.
    Returns ``None`` when nothing points at a cause."""
    from lookup.spn import spn_name
    descs = [(d.get("desc") or spn_name(d.get("spn")) or "").lower()
             for mod in modules.values()
             for d in getattr(mod, "active_dtcs", ())]
    if any(h in t for t in descs for h in _AFT_DERATE_HINTS):
        return "Aftertreatment (inferred)"
    if any(h in t for t in descs for h in _PROTECT_DERATE_HINTS):
        return "Engine protection (inferred)"
    return None


class CombinedSession:
    """Merge the J1939 and J1708 sessions into one view, so the GUI shows every
    module (and its faults / live data) from both buses at once.

    ``modules`` / ``live`` are rebuilt after each frame from the two underlying
    sessions; J1708 entries are re-keyed into the J1708_KEY_BASE.. range so they
    never collide with a J1939 source address. ``handle`` accepts a tagged frame
    (see ``framesource.TaggedFrame``) and routes on its ``protocol``.
    """

    def __init__(self) -> None:
        self.j1939 = Session(None)
        self.j1708 = J1708Session()
        self.cdl = CdlSession()
        self.modules: dict[int, object] = {}
        self.live: dict[int, dict[str, tuple[str, str]]] = {}
        self.vin: str = ""

    def handle(self, tagged) -> None:
        if tagged.protocol == "can2":
            return      # raw-CAN channel: capture-only, nothing to decode
        if tagged.protocol == "j1708":
            self.j1708.handle(tagged.frame)
        elif tagged.protocol == "cdl":
            # Either the decoded CDL client (CDLMessage) or the capture-only
            # raw channel (CdlFrame); CdlSession decodes both.
            self.cdl.handle(tagged.frame)
        else:
            self.j1939.handle(tagged.frame)
        self._sync()

    def poll(self) -> None:
        """Service time-based J1939 work (acknowledgement back-off)."""
        self.j1939.poll()

    def claim_address(self) -> None:
        """Claim the tool's J1939 source address on the bus (J1939-81)."""
        self.j1939.claim_address()

    # J1708 MID -> the J1939 NAME "function" code(s) of the same physical
    # controller. J1587 identity (make) only arrives if an ECU answers PID 243;
    # when it doesn't, borrow the make from the matching J1939 controller so the
    # J1587 fault-code OEM overrides (Cummins/WABCO/Deere PID+SID tables) fire.
    _MID_FUNCTIONS: dict[int, tuple[int, ...]] = {
        128: (0,), 175: (0,), 183: (0,), 184: (0,), 185: (0,), 186: (0,),
        130: (3, 5), 176: (3, 5),
        136: (11, 12, 13), 137: (11, 12, 13), 138: (11, 12, 13),
        139: (11, 12, 13),
    }

    # Preferred J1939 source address -> NAME function code, for controllers that
    # broadcast a CI but never claimed an address (e.g. a Bendix ABS at 0x0B).
    _PREFERRED_ADDR_FUNCTION = {0x00: 0, 0x03: 3, 0x0B: 11, 0x0F: 12,
                                0x11: 17, 0x15: 21, 0x21: 22}

    def _link_j1708_identity(self) -> None:
        """Copy each J1939 controller's make onto the matching J1708 module when
        the J1708 module has no make of its own (PID 243 not answered)."""
        # Two tiers: a controller whose NAME carries a REAL (non-zero) SAE
        # manufacturer code is authoritative for its function. One that reports
        # manufacturer code 0 ("experimental/reserved") is not - e.g. a Bosch
        # SCR dosing unit claims function 0 ("Engine") with mfr 0, and letting
        # it win handed the engine's J1708 module the dosing unit's identity.
        primary: dict[int, tuple[Optional[str], Optional[int]]] = {}
        fallback: dict[int, tuple[Optional[str], Optional[int]]] = {}
        for mod in self.j1939.modules.values():
            # A module may know its maker from the NAME's manufacturer code even
            # when it never answers a Component-ID request (very common on
            # engines) - so accept either source of identity here.
            mfr = mod.name.manufacturer if mod.name is not None else None
            if not mod.make and mfr is None:
                continue
            entry = (mod.make, mfr)
            tier = primary if mfr else fallback
            if mod.name is not None:
                tier.setdefault(mod.name.function, entry)
            func = self._PREFERRED_ADDR_FUNCTION.get(mod.address)
            if func is not None:
                tier.setdefault(func, entry)
        by_func = primary or fallback
        if not by_func:
            return
        for mid, mod in self.j1708.modules.items():
            if not mod.make:
                for func in self._MID_FUNCTIONS.get(mid, ()):
                    if func in by_func:
                        mod.make, mod.mfr = by_func[func]
                        break
            # The NAME manufacturer code is the more reliable OEM selector
            # (the CI make string is free-form), so borrow it independently.
            if mod.mfr is None:
                for func in self._MID_FUNCTIONS.get(mid, ()):
                    if func in by_func and by_func[func][1] is not None:
                        mod.mfr = by_func[func][1]
                        break

    def _sync(self) -> None:
        self._link_j1708_identity()
        m: dict[int, object] = dict(self.j1939.modules)
        for mid, mod in self.j1708.modules.items():
            m[J1708_KEY_BASE + mid] = mod
        for mid, mod in self.cdl.modules.items():
            m[CDL_KEY_BASE + mid] = mod
        self.modules = m

        # Copy the buckets so the computed entries below don't mutate the
        # per-protocol sessions.
        live: dict[int, dict[str, tuple[str, str]]] = {
            k: dict(b) for k, b in self.j1939.live.items()
        }
        for mid, bucket in self.j1708.live.items():
            live[J1708_KEY_BASE + mid] = dict(bucket)
        # CDL live parameters are not decoded yet (the store is empty), but
        # the merge must already be here so the moment the 0xA2 decoders land
        # the values reach the live table (field check 2026-11-13: the CDL
        # bucket was silently dropped from the merged live map).
        for mid, bucket in self.cdl.live.items():
            live[CDL_KEY_BASE + mid] = dict(bucket)

        # Attach computed "virtual" parameters (fuel economy / boost / torque /
        # power) to the engine module so they sit next to the real sensors.
        try:
            merged: dict[str, tuple[str, str]] = {}
            for b in live.values():
                for name, val in b.items():
                    merged.setdefault(name, val)
            eng = 0x00 if 0x00 in live else next(
                (k for k, b in live.items() if "Engine Speed" in b), None)
            extra = compute_live(merged)
            if eng is not None:
                for name, val in extra.items():
                    live[eng].setdefault(name, val)
                # Derate reason: the ECU reports the torque shortfall ("Derate
                # %") but NOT why, and there is no single "derate reason" PGN.
                # Infer the cause from the active codes - DPF/SCR/DEF codes =>
                # aftertreatment derate; coolant / oil / boost etc. => engine-
                # protection derate.
                if "Derate %" in live[eng]:
                    try:
                        _derate = float(live[eng]["Derate %"][0])
                    except (ValueError, TypeError):
                        _derate = 0.0
                    reason = _derate_reason(self.modules) if _derate > 0 else None
                    if reason:
                        live[eng].setdefault("Derate Reason", (reason, ""))
        except Exception:      # a computed value must never break the live link
            pass

        self.live = live
        self.vin = self.j1939.vin or self.j1708.vin

        # Chassis make lets each J1939 module use its maker's own source-address
        # map and code tables instead of the generic ones. Prefer the VIN WMI;
        # fall back to the engine's CI make when the truck answers no VIN.
        chassis = None
        if self.vin:
            try:
                from lookup.vin import wmi_make
                chassis = wmi_make(self.vin)
            except Exception:          # noqa: BLE001
                chassis = None
        if not chassis:
            eng = self.j1939.modules.get(0x00)
            if eng is not None:
                chassis = chassis_make_from_engine(eng)
        if chassis:
            for mod in self.j1939.modules.values():
                mod.vehicle_make = chassis

    def visible_modules(self) -> dict[int, object]:
        """Modules worth showing (see :func:`module_is_useful`)."""
        return {a: m for a, m in self.modules.items()
                if module_is_useful(m, self.live.get(a))}


def main(argv: list[str]) -> int:
    args = argv[1:]
    if not args:
        print(__doc__)
        return 2

    rawlog = None
    seconds = 3.0
    if "--rawlog" in args:
        rawlog = args[args.index("--rawlog") + 1]
    if "--seconds" in args:
        seconds = float(args[args.index("--seconds") + 1])

    if args[0] == "--sniff":
        # Raw diagnostic: read the adapter's receive buffer WITHOUT J1939/J1708
        # decoding, so we can tell a dead bus from a wrong-baud/protocol one.
        # Uses J1939:Baud=Auto (the default), so 250k/500k/1M vehicles are seen.
        from rp1210 import RP1210Source
        src = RP1210Source(passive=True)
        src.connect()
        count = 0
        print(f"Sniffing raw RP1210 traffic for {seconds:g}s (",
              "J1939:Baud=Auto) ...", sep="")
        deadline = time.time() + seconds
        try:
            while time.time() < deadline:
                h = src.read_raw_hex()
                if h:
                    count += 1
                    ts = (int.from_bytes(bytes.fromhex(h[0:8]), "little")
                          if len(h) >= 8 else 0)
                    print(f"[{ts:08x}] {h}")
                else:
                    time.sleep(0.002)
        finally:
            src.close()
        print(f"\n{count} raw buffers captured.")
        if count == 0:
            print("Bus is silent: check key-ON, wiring, and that the vehicle"
                  " is actually a live J1939 bus (not J1708-only).")
        return 0

    if args[0] == "--rp1210":
        from rp1210 import PROTOCOL, RP1210Source, list_adapters
        from framesource import CombinedSource, RawCanSource
        adapters = [a for a in list_adapters() if a.dll_path] or list_adapters()
        if not adapters:
            print("No RP1210 adapter with a driver DLL is installed.")
            return 1
        info = adapters[0]
        if info.dll_path:
            j1939 = RP1210Source(dll_path=info.dll_path, protocol=PROTOCOL,
                                 device_id=info.device_id)
        else:
            from rp1210 import BridgedRP1210Source
            j1939 = BridgedRP1210Source(info.bridge_dll, protocol=PROTOCOL,
                                        device_id=info.device_id)
        # Listen on J1708 at the same time, exactly as the GUI does, so a
        # capture holds BOTH buses. (The CLI used to record J1939 only, which
        # made every J1587 fault list unrecoverable from the log.)
        j1708_src = None
        if info.dll_path:
            try:
                j1708_src = RP1210Source(dll_path=info.dll_path,
                                         protocol=info.j1708_protocol,
                                         device_id=info.device_id)
            except Exception as exc:                 # noqa: BLE001
                print(f"(J1708 unavailable: {exc} - capturing J1939 only)")
        # Raw-CAN channel: everything on the wire, undecoded (proprietary
        # PGNs, handshake/commands) - best-effort like J1708.
        can2 = None
        try:
            if info.dll_path:
                can2 = RP1210Source(dll_path=info.dll_path,
                                    protocol="CAN:Baud=Auto",
                                    device_id=info.device_id, passive=True)
            else:
                can2 = BridgedRP1210Source(info.bridge_dll,
                                           protocol="CAN:Baud=Auto",
                                           device_id=info.device_id,
                                           passive=True)
        except Exception as exc:                     # noqa: BLE001
            print(f"(Raw CAN unavailable: {exc})")
        channels = [("j1939", j1939)]
        label = "J1939"
        if j1708_src is not None:
            channels.append(("j1708", j1708_src))
            label += " + J1708"
        if can2 is not None:
            channels.append(("can2", RawCanSource(can2)))
            label += " + raw CAN"
        if len(channels) > 1:
            base = CombinedSource(channels)
        else:
            base = j1939
        print(f"Listening on {label} via {info.name} ({info.code})")
        if rawlog:
            base = LoggingSource(base, rawlog)
        if j1708_src is None:
            s = Session(base)
            try:
                s.run(seconds=seconds, request=True, request_ident=True)
                s.report()
            finally:
                base.close()   # never leave an RP1210 client open (see below)
        else:
            s = CombinedSession()
            src = base
            try:
                src.connect()
                # Route the J1939 sub-session's writes through the combined
                # source so requests/clears still go out (and get logged as TX).
                s.j1939.source = src
                s.j1939.claim_address()
                s.j1939.request_addresses()
                s.j1939.request_diagnostics()
                deadline = time.monotonic() + seconds
                last_poll = 0.0
                last_j1708_ident = 0.0
                while time.monotonic() < deadline:
                    tf = src.read_frame()
                    if tf is not None:
                        s.handle(tf)
                    else:
                        time.sleep(0.002)
                    s.poll()      # acknowledgement back-off re-requests
                    # Re-poll gently. A full sweep is ~80 requests, each of
                    # which draws an ACK/NACK; polling too often floods the
                    # adapter's receive queue, which makes read_frame() silently
                    # DROP frames (error -139) - and a dropped TP.CM announce
                    # orphans the TP.DT frames behind it, so a multi-frame VIN
                    # never reassembles.
                    if time.monotonic() - last_poll > 30.0:
                        last_poll = time.monotonic()
                        s.j1939.request_diagnostics()
                    # J1587 identification PIDs (VIN / component id / software
                    # id) are ON-REQUEST ONLY - listening never surfaces them,
                    # so a capture that never asks has no VIN at all. Pace the
                    # same way the GUI does (every 3 s, bounded) so a 9600-baud
                    # J1708 bus is not flooded.
                    if time.monotonic() - last_j1708_ident > 3.0:
                        last_j1708_ident = time.monotonic()
                        try:
                            pids = (PID_VIN, PID_COMPONENT_ID, PID_SOFTWARE_ID)
                            for pid in pids:
                                src.send_j1708(J1587_REQUESTER_MID,
                                               build_broadcast_request(pid))
                            for mid in list(s.j1708.modules):
                                for pid in pids:
                                    src.send_j1708(J1587_REQUESTER_MID,
                                                   build_request(mid, pid))
                        except Exception:            # noqa: BLE001 - retried next tick
                            pass
                s.j1939.report()
            finally:
                # ALWAYS disconnect. An RP1210 client left open by a crashed or
                # aborted run wedges the adapter - afterwards every ReadMessage
                # returns -128 and no traffic reaches us until it is reset.
                src.close()
        if rawlog:
            print(f"\nCaptured raw traffic to {rawlog}")
        return 0

    src = ReplaySource(args[0])
    s = Session(src)
    s.run(seconds=1.0)
    s.report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
