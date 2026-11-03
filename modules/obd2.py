"""OpenTruck - OBD-II (SAE J1979 over ISO 15765) support for light vehicles.

Talks to 2008+ cars and light/medium pickups on the 16-pin J1962 DLC:
11-bit CAN ids at 500 kbit/s, requests to the functional id 0x7DF, responses
from 0x7E8-0x7EF. Everything runs over the RAW-CAN RP1210 client using the
wire formats observed on 11-bit CAN vehicles:

  RX: [0:4] timestamp ms LE | [4] flag (01 = 29-bit, 00 = 11-bit)
      | 29-bit: [5:9] id big-endian, [9:] 8 data bytes
      | 11-bit: [5:7] id big-endian,  [7:] 8 data bytes
  TX: [flag][id 2 or 4 bytes big-endian][payload padded to 8 bytes]

ISO-TP (ISO 15765-2) framing is implemented here (single/first/consecutive
frames + our flow-control), NOT delegated to the driver: the driver's
ISO15765 client cannot coexist with another CAN client, while raw CAN can
(the same multi-client trick the J1939+J1708 support uses).
"""
from __future__ import annotations

import time
from typing import Callable, List, Optional, Tuple

from framesource import FrameSource
from lookup import obd_pids
from lookup.obd_pids import decode_pid
from lookup.vin import wmi_make
from lookup.obd_dtcs import obd_dtc_description
from lookup.obd_dtcs_mfg import brand_from_make, mfg_dtc_description

FRAME_FLAG_EXT = 0x01        # 29-bit extended id
FRAME_FLAG_STD = 0x00        # 11-bit standard id
OBD_REQ_ID = 0x7DF           # functional broadcast (all OBD ECUs)
OBD_RESP_BASE = 0x7E8        # responses: 0x7E8 .. 0x7EF
OBD_RESP_RANGE = range(0x7E8, 0x7F0)
CAN_PAYLOAD = 8              # classic CAN: fixed 8-byte payload

# ISO-TP network-layer frame types (high nibble of the first payload byte).
ISO_SF = 0x0                 # single frame
ISO_FF = 0x1                 # first frame of a multi-frame message
ISO_CF = 0x2                 # consecutive frame
ISO_FC = 0x3                 # flow control (we SEND these)


def dtc_to_code(raw: int) -> str:
    """Convert a 2-byte Mode 03/07 DTC into its P/B/C/U code text."""
    if raw == 0 or raw >= 0xFF00:
        return ""
    letter = ("P", "C", "B", "U")[(raw >> 14) & 0x3]
    d1 = (raw >> 12) & 0x3
    d2 = (raw >> 8) & 0xF
    d3 = (raw >> 4) & 0xF
    d4 = raw & 0xF
    return f"{letter}{d1}{d2:X}{d3:X}{d4:X}"


class OBD2Session:
    """State + request engine for one connected OBD-II vehicle."""

    def __init__(self, source: FrameSource) -> None:
        self.source = source
        self.ecus: set[int] = set()          # responding ECUs (7E8..7EF)
        self.ecu_names: dict[int, str] = {}  # Mode 09 0A ECU name per ECU
        self.cal_ids: dict[int, str] = {}    # Mode 09 04 calibration ID per ECU
        self.ecu_class: dict[int, str] = {}  # heuristic role per ECU
        self.supported_by_ecu: dict[int, list] = {}
        self.brand: Optional[str] = None     # FORD / GM / CHRYSLER (from VIN)
        self.vpic: Optional[dict] = None     # NHTSA vPIC chassis decode
        self.mil_on: Optional[bool] = None
        self.dtcs_stored: list[str] = []        # Mode 03 confirmed (MIL) codes
        self.dtcs_pending: list[str] = []       # Mode 07 pending codes
        self.dtcs_permanent: list[str] = []     # Mode 0A permanent codes
        self.vin: Optional[str] = None
        self.live: dict[str, Tuple[object, str]] = {}   # label -> (value, unit)
        self.live_by_ecu: dict[int, dict[str, Tuple[object, str]]] = {}

    # ------------------------------------------------------------- wire --- #
    def _tx(self, can_id: int, payload: bytes) -> None:
        """Transmit one CAN frame (payload padded to 8 bytes)."""
        flag = FRAME_FLAG_STD
        id_bytes = can_id.to_bytes(2, "big")
        data = payload + bytes(CAN_PAYLOAD - len(payload))
        buf = bytes([flag]) + id_bytes + data
        rc = self.source.send_raw_message(buf)
        if rc < 0:
            raise RuntimeError(f"CAN transmit failed (rc {rc})")

    def _poll(self, seconds: float,
              sink: Optional[Callable[[bytes], None]] = None,
              idle: float = 0.08) -> List[Tuple[int, bytes]]:
        """Drain RX for a window; return [(ecu_id, iso_tp_payload), ...].

        Returns early once at least one complete response has arrived and the
        bus has been idle for `idle` seconds - waiting out the full timeout on
        every request was making live data crawl (~0.35 s per PID).
        Multi-frame reassembly in progress suppresses the early exit so a
        long response is never cut short.
        """
        out: list[Tuple[int, bytes]] = []
        reassembly: dict[int, dict] = {}
        deadline = time.time() + seconds
        # A DLC can carry constant background module chatter (several
        # hundred frames per second is normal) - only frames from OBD ECUs
        # count toward the quiet-window, or the early exit would never fire.
        last_obd_rx = None
        while time.time() < deadline:
            raw = self.source.read_raw_hex()
            if not raw:
                if (out and not reassembly and last_obd_rx is not None
                        and time.time() - last_obd_rx >= idle):
                    break
                time.sleep(0.005)
                continue
            buf = bytes.fromhex(raw)
            if len(buf) < 9 or buf[4] != FRAME_FLAG_STD:
                continue
            can_id = int.from_bytes(buf[5:7], "big")
            data = buf[7:]
            if can_id not in OBD_RESP_RANGE:
                continue
            last_obd_rx = time.time()
            if sink:
                sink(buf)
            if not data:
                continue
            pci = data[0] >> 4
            if pci == ISO_SF:
                length = data[0] & 0xF
                out.append((can_id, data[1:1 + length]))
            elif pci == ISO_FF:
                length = ((data[0] & 0xF) << 8) | data[1]
                body = data[2:]
                reassembly[can_id] = {"left": length - len(body), "parts": [body]}
                # Flow control goes to the ECU's RECEIVE id (its response id
                # minus 8: ECU 0x7E8 listens on 0x7E0).
                self._send_flow_control(can_id - 8)
            elif pci == ISO_CF:
                state = reassembly.get(can_id)
                if state is None:
                    continue
                state["parts"].append(data[1:])
                state["left"] -= len(data) - 1
                if state["left"] <= 0:
                    body = b"".join(state["parts"])
                    out.append((can_id, body[:len(body) + min(0, state["left"])]))
                    del reassembly[can_id]
        return out

    def _send_flow_control(self, to_id: int) -> None:
        """ISO-TP flow control: continue, block size 0, STmin 10 ms (0x32)."""
        try:
            self._tx(to_id, bytes([ISO_FC << 4 | 0x0, 0x00, 0x32]))
        except Exception:
            pass   # FC is best-effort; most ECUs stream the rest regardless

    # --------------------------------------------------------- services --- #
    def request(self, service: int, pid: int = None,
                timeout: float = 1.0) -> List[Tuple[int, bytes]]:
        """Send one OBD request; return [(ecu_id, response payload), ...]."""
        # ISO-TP single frame: [PCI = length][service][pid?]
        sf = bytes([1 + (0 if pid is None else 1), service]) + \
            (bytes([pid]) if pid is not None else b"")
        self._tx(OBD_REQ_ID, sf)
        responses = self._poll(timeout)
        out = []
        for ecu, resp in responses:
            if resp and resp[0] == service + 0x40:       # positive response
                self.ecus.add(ecu)
                out.append((ecu, resp))
            elif resp and resp[0] == 0x7F and len(resp) > 2:
                pass                                     # negative response
        return out

    def probe(self) -> bool:
        """True if any ECU answers a Mode 01 supported-PID request."""
        resps = self.request(0x01, 0x00, timeout=0.6)
        return bool(resps)

    def supported_pids(self, ecu_resp: bytes) -> list[int]:
        """Walk the PID-00/20/40... bitmask chain; return supported PIDs."""
        supported: list[int] = []
        pid_base = 0x00
        data = ecu_resp[2:]                     # skip 41 <pid>
        while pid_base <= 0xE0 and len(data) >= 4:
            bits = data[:4]
            for i in range(32):
                if bits[i // 8] & (0x80 >> (i % 8)):
                    supported.append(pid_base + 1 + i)
            if not (bits[3] & 0x01):            # next-bitmap flag
                break
            pid_base += 0x20
            nxt = self.request(0x01, pid_base, timeout=0.4)
            if not nxt:
                break
            data = nxt[0][1][2:]
        return supported

    def poll_pid(self, pid: int) -> None:
        """Query one Mode 01 PID; merge decoded values into live (per ECU)."""
        for ecu, resp in self.request(0x01, pid, timeout=0.35):
            decoded = decode_pid(pid, resp[2:])
            if decoded:
                label, value, unit = decoded
                self.live[label] = (value, unit)
                self.live_by_ecu.setdefault(ecu, {})[label] = (value, unit)

    def supported_pids_for(self, ecu: int, first_resp: bytes) -> list:
        """Per-ECU supported-PID chain, matching replies from that one ECU."""
        supported: list = []
        pid_base = 0x00
        data = first_resp[2:]
        while pid_base <= 0xE0 and len(data) >= 4:
            bits = data[:4]
            for i in range(32):
                if bits[i // 8] & (0x80 >> (i % 8)):
                    supported.append(pid_base + 1 + i)
            if not (bits[3] & 0x01):            # next-bitmap flag
                break
            pid_base += 0x20
            match = [r for e, r in self.request(0x01, pid_base, timeout=0.4)
                     if e == ecu]
            if not match:
                break
            data = match[0][2:]
        return supported

    def classify_ecu(self, ecu: int, pids: list) -> str:
        """Heuristic role name from an ECU's supported-PID signature.

        Generic OBD-II only exposes emissions ECUs, and the engine is the one
        that answers RPM plus the temperature/position sensors. This is a
        hedge, never a certainty - Mode 09 0A names take precedence.
        """
        s = set(pids)
        if 0x0C in s and (0x05 in s or 0x0F in s or 0x11 in s):
            return "Engine controller (PCM)"
        if 0x0C in s:
            return "Engine-related ECU"
        if 0x0D in s:
            return "Vehicle controller"
        return "ECU"

    def refresh_live(self) -> None:
        """Poll every supported Mode 01 PID once; store label -> (value, unit)."""
        self.live.clear()
        base = self.request(0x01, 0x00, timeout=0.6)
        if not base:
            return
        for pid in self.supported_pids(base[0][1]):
            if pid in obd_pids.PIDS:
                self.poll_pid(pid)

    def read_dtcs(self, service: int, into: list) -> None:
        """Mode 03 (stored) / 07 (pending): fill `into` with code strings."""
        resps = self.request(service, timeout=0.8)
        into.clear()
        for _ecu, resp in resps:
            body = resp[2:]                     # skip 43/47 + count byte?
            for i in range(0, len(body) - 1, 2):
                code = dtc_to_code((body[i] << 8) | body[i + 1])
                if code:
                    into.append(code)

    def clear_dtcs(self) -> bool:
        """Mode 04: clear emission-related DTCs (key ON, engine OFF)."""
        return bool(self.request(0x04, timeout=0.8))

    def _record_vin(self) -> None:
        """After a VIN read: derive the brand family for maker-scoped lookups."""
        if self.vin:
            self.brand = brand_from_make(wmi_make(self.vin[:3]))

    def read_ecu_names(self) -> None:
        """Mode 09 0A: ask every physical ECU id for its generic ECU name.

        This is a STANDARD service (no vendor data involved): each OBD ECU
        that supports it replies with a 20-byte ASCII name such as "ECM" or
        "PCM". Unicast to 0x7E0..0x7E7 - a functional 0x7DF broadcast gets
        one answer for the whole request, not one per ECU.
        """
        for phys in range(0x7E0, 0x7E8):
            try:
                self._tx(phys, bytes([2, 0x09, 0x0A]))
            except Exception:
                continue
            for _ecu, resp in self._poll(0.45):
                if len(resp) < 2 or resp[0] != 0x4A or resp[1] != 0x0A:
                    continue
                name = bytes(resp[2:]).replace(b"\x00", b" ").decode(
                    "ascii", "ignore").strip()
                if name:
                    self.ecu_names[_ecu] = name

    def read_cal_ids(self) -> None:
        """Mode 09 04: calibration identifier per ECU (generic service).

        The closest generic equivalent of an engine serial / software ID on
        the light-duty DLC; J1939's engine serial itself is not carried by
        generic OBD-II.
        """
        for phys in range(0x7E0, 0x7E8):
            try:
                self._tx(phys, bytes([2, 0x09, 0x04]))
            except Exception:
                continue
            for ecu, resp in self._poll(0.45):
                if len(resp) < 2 or resp[0] != 0x4A or resp[1] != 0x04:
                    continue
                text = bytes(resp[2:]).decode("ascii", "ignore").strip(
                    "\x00 *\r\n")
                if text:
                    self.cal_ids[ecu] = text

    def read_permanent_dtcs(self) -> None:
        """Mode 0A: permanent DTCs - cannot be cleared with Mode 04; they
        clear themselves only after the ECU verifies the repair in use."""
        sess = self
        sess.read_dtcs(0x0A, sess.dtcs_permanent)

    def read_vin(self) -> Optional[str]:
        """Mode 09 02: VIN (often a multi-frame response)."""
        resps = self.request(0x09, 0x02, timeout=1.2)
        for _ecu, resp in resps:
            # Resp = 62 09 <count?> + VIN chars (Nordskog format: 01 02 + VIN);
            # strip the service echo and any leading record markers.
            text = resp[2:]
            text = text.lstrip(b"\x01\x02\x00")
            try:
                vin = text.decode("ascii", "ignore").strip("*\x00 \r\n")
                if len(vin) >= 11:
                    self.vin = vin
                    self._record_vin()
                    return self.vin
            except Exception:
                pass
        return self.vin

    def describe(self, code: str) -> str:
        """Best description for a code: maker-scoped first, then generic."""
        return mfg_dtc_description(code, self.brand) or obd_dtc_description(code)

    # ------------------------------------------------------- CLI (test) --- #

def open_session(adapter: Optional[str] = None) -> OBD2Session:
    """Connect to the DLC via the first usable adapter (or a named one)."""
    from rp1210 import list_adapters, RP1210Source, BridgedRP1210Source, RP1210Error
    a = None
    for cand in list_adapters():
        if adapter and cand.code.upper() != adapter.upper():
            continue
        if cand.dll_path or cand.bridge_dll:
            a = cand
            break
    if a is None:
        raise RuntimeError(f"No usable RP1210 adapter (wanted {adapter!r})")
    proto = "CAN:Baud=500"
    if a.dll_path:
        src = RP1210Source(dll_path=a.dll_path, protocol=proto,
                           device_id=a.device_id, passive=True)
    else:
        src = BridgedRP1210Source(dll_path=a.bridge_dll, protocol=proto,
                                  device_id=a.device_id, passive=True)
    src.connect()
    return OBD2Session(src)


def main(argv: Optional[list] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(
        description="OBD-II (J1979) live test over the 16-pin DLC")
    ap.add_argument("--adapter", help="RP1210 vendor code")
    ap.add_argument("--seconds", type=float, default=25)
    args = ap.parse_args(argv)

    sess = open_session(args.adapter)
    print("Raw CAN client connected (500k, 11-bit)")
    if not sess.probe():
        print("No OBD-II ECU responded (wrong cable/bus, or key off?).")
        sess.source.close()
        return 1
    print(f"OBD-II detected - {len(sess.ecus)} ECU(s) answered: "
          + ", ".join(f"0x{e:X}" for e in sorted(sess.ecus)))

    vin = sess.read_vin()
    print("VIN:", vin or "(not reported)")
    print("Brand (VIN-derived):", sess.brand or "unknown")
    sess.read_ecu_names()
    for ecu, name in sorted(sess.ecu_names.items()):
        print(f"ECU 0x{ecu:X}: {name}")
    sess.read_dtcs(0x03, sess.dtcs_stored)
    sess.read_dtcs(0x07, sess.dtcs_pending)
    print("Confirmed DTCs (MIL):",
          " ".join(sess.dtcs_stored) or "none")
    print("Pending DTCs:", " ".join(sess.dtcs_pending) or "none")
    print("Permanent DTCs:", " ".join(sess.dtcs_permanent) or "none")

    print(f"Polling live PIDs for {args.seconds}s ...")
    t0 = time.time()
    rounds = 0
    while time.time() - t0 < args.seconds:
        sess.refresh_live()
        rounds += 1
        if rounds == 1:
            for label, (value, unit) in sorted(sess.live.items()):
                print(f"    {label}: {value} {unit}")
    print(f"({rounds} live polling rounds, {len(sess.live)} parameters)")
    sess.source.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())