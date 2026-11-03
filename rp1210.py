"""OpenTruck - RP1210 adapter backend.

Drives an installed RP1210 vendor DLL directly via ctypes (the adapter is
auto-enumerated from RP121032.ini and the vendor INIs) and exposes the same
FrameSource interface as the replay source.

J1939 message layout (RP1210_ReadMessage buffer, echo disabled):
    [0:4]  timestamp (ms)
    [4:7]  PGN              (18-bit, little-endian)
    [7]    priority / "how" (low 3 bits = priority)
    [8]    source address
    [9]    destination address
    [10:]  data payload
"""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import threading
from ctypes import wintypes, c_char, c_short, POINTER
from dataclasses import dataclass
from typing import Optional

from framesource import FrameSource
from modules.j1939 import Frame
from modules.j1708 import from_rp1210_buffer, J1708Message

# Auto-select 64- vs 32-bit DLL to match the running Python interpreter.
if ctypes.sizeof(ctypes.c_void_p) == 8:
    RP1210_DLL = r"C:\Windows\System32\NULN3R32.DLL"
else:
    RP1210_DLL = r"C:\Windows\SysWOW64\NULN3R32.DLL"

DEVICE_ID  = 1                   # first device listed in the vendor INI
PROTOCOL   = "J1939:Baud=Auto"   # auto-detect 250k/500k/1M at connect time
TX_BUFFER  = 8192
RX_BUFFER  = 8192

BLOCKING     = 1
NON_BLOCKING = 0

# RP1210 error code the adapter returns when our read loop can't drain its
# receive queue fast enough (e.g. right after a burst of clear/request messages
# triggers many ACK/NACK replies). The RP1210 spec calls it error 139 -
# "receive queue full": the adapter dropped a few frames, empties the queue and
# just wants us to keep polling. It is TRANSIENT and benign - NOT a lost link -
# so it must be treated as "no message", never as a connection error.
# Vendors are inconsistent about the sign (the TMC spec and PEAK's forum
# document 139; some drivers return -139), so accept either.
ERR_RX_QUEUE_FULL = 139
ERR_RX_QUEUE_FULL_NEG = -139

# RP1210 `SendCommand` command numbers (RP1210B spec).
CMD_SET_ALL_FILTERS_PASS = 3    # without this the adapter reports NOTHING
CMD_PROTECT_J1939_ADDR   = 19   # claims our J1939 source address (for TX)

# Source address the tool presents on the J1939 bus ("off-board diagnostics tool #1").
TOOL_SOURCE_ADDR = 0xF9


def _tool_name() -> bytes:
    """8-byte J1939 NAME (little-endian) identifying our tool on the bus."""
    identity = 0x001234
    manufacturer = 0x0C0
    function = 0x80   # "off-board diagnostics" area
    n = ((identity & 0x1FFFFF)
         | ((manufacturer & 0x7FF) << 21)
         | ((function & 0xFF) << 40))
    return n.to_bytes(8, "little")


# ------------------------------------------------------------ RP1210 disc --- #
# Adapter discovery. RP1210 is a pluggable standard: a master INI lists every
# installed vendor's DLL, and each vendor INI declares its devices + protocols.
# We enumerate them so OpenTruck isn't hard-wired to any one adapter.

MASTER_INI = r"C:\Windows\RP121032.ini"


@dataclass
class AdapterInfo:
    code: str            # RP1210 vendor code from the INI, e.g. "XYZUSB1"
    name: str            # human name from the vendor INI, e.g. "Vendor X USB adapter"
    dll_path: str        # in-process DLL (matching bitness); "" = use bridge
    protocol: str        # this vendor's J1939 protocol string (usually "J1939")
    device_id: int       # device/TID to connect to (usually 1)
    j1708_protocol: str  # this vendor's J1708 protocol string (usually "J1708")
    bridge_dll: str = "" # 32-bit DLL path when dll_path is empty (drive it via the bridge)


def _parse_ini(path: str) -> dict[str, dict[str, str]]:
    """Tolerant INI parser -> {section: {key: value}}.

    RP1210 vendor INIs aren't always strict INI (some contain bare lines such
    as ``0,All``), so anything that isn't ``[section]`` or ``key=value`` is
    ignored rather than treated as an error.
    """
    sections: dict[str, dict[str, str]] = {}
    current: Optional[str] = None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return sections
    for line in lines:
        line = line.strip()
        if not line or line[:1] in (";", "#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip()
            sections.setdefault(current, {})
            continue
        if current is None:
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            sections[current][key.strip()] = value.strip()
    return sections


def _bitness_is_64() -> bool:
    return ctypes.sizeof(ctypes.c_void_p) == 8


def _find_dlls(code: str) -> tuple[Optional[str], Optional[str]]:
    """Return ``(matching, other)`` DLL paths for a vendor code.

    ``matching`` is the DLL whose bitness matches this running process (the
    only one ctypes can load). ``other`` is the opposite-bitness DLL if it
    exists, used only to explain "32-bit only" / "64-bit only" in the UI.
    """
    sys32 = os.path.join(r"C:\Windows\System32", code + ".DLL")
    syswow = os.path.join(r"C:\Windows\SysWOW64", code + ".DLL")
    if _bitness_is_64():
        matching = sys32 if os.path.exists(sys32) else None
        other = syswow if os.path.exists(syswow) else None
    else:
        matching = syswow if os.path.exists(syswow) else None
        other = sys32 if os.path.exists(sys32) else None
    return matching, other


def _j1939_protocol(sections: dict[str, dict[str, str]]) -> tuple[str, int]:
    """Find this vendor's J1939 protocol string + device id from its INI.

    Vendor INIs expose a bare ``ProtocolString=J1939``, which on several
    drivers locks the link to one fixed baud. A vehicle running a different
    rate (e.g. 500k when the driver assumes 250k) then looks completely
    silent, even though the adapter and the bus are both fine. We therefore
    always emit ``J1939:Baud=Auto`` so the adapter syncs to the vehicle's
    actual rate (250k/500k/1M). Device id still comes from the vendor INI
    (e.g. 1=USB, 2=Bluetooth, 3=WiFi).
    """
    for name, opts in sections.items():
        if not name.lower().startswith("protocolinformation"):
            continue
        proto = opts.get("ProtocolString", "")
        # Match "J1939" but not "J1939FD" (FD needs its own :Baud handling).
        if proto.upper() == "J1939" or proto.upper().startswith("J1939:"):
            dev = 1
            try:
                dev = int(opts.get("Devices", "1").split(",")[0])
            except (ValueError, IndexError):
                dev = 1
            return "J1939:Baud=Auto", dev
    return "J1939:Baud=Auto", 1


def _j1708_protocol(sections: dict[str, dict[str, str]]) -> str:
    """Find this vendor's J1708 protocol string, defaulting to "J1708"."""
    for name, opts in sections.items():
        if not name.lower().startswith("protocolinformation"):
            continue
        proto = opts.get("ProtocolString", "")
        if proto.upper() == "J1708" or proto.upper().startswith("J1708"):
            return proto
    return "J1708"


def list_adapters() -> list[AdapterInfo]:
    """Enumerate installed RP1210 adapters that have a usable DLL on disk.

    Adapters listed in the master INI but with no DLL in *either* bitness are
    skipped (they are just leftover INI entries, not real hardware we can talk
    to). Each returned `AdapterInfo` is ready to use:
      * ``dll_path`` set   -> load in-process (bitness matches this build).
      * ``bridge_dll`` set -> 32-bit-only driver; drive it via the 32-bit
        ``rp1210_bridge`` helper (see `BridgedRP1210Source`).
    """
    out: list[AdapterInfo] = []
    if not os.path.exists(MASTER_INI):
        return out
    master = _parse_ini(MASTER_INI)
    impl = master.get("RP1210Support", {}).get("APIImplementations", "")
    for code in [c.strip() for c in impl.split(",") if c.strip()]:
        name = code
        proto = "J1939"
        j1708 = "J1708"
        device_id = 1
        ini = os.path.join(r"C:\Windows", code + ".INI")
        if os.path.exists(ini):
            sections = _parse_ini(ini)
            name = sections.get("VendorInformation", {}).get("Name", code)
            proto, device_id = _j1939_protocol(sections)
            j1708 = _j1708_protocol(sections)
        matching, other = _find_dlls(code)
        if matching is None and other is None:
            continue                      # no DLL -> not a real adapter; skip
        if matching is not None:
            out.append(AdapterInfo(code, name, matching, proto, device_id, j1708))
        else:
            out.append(AdapterInfo(
                code, name, "", proto, device_id, j1708, bridge_dll=other or ""))
    return out


def get_adapter(code: str) -> Optional[AdapterInfo]:
    """Look up one enumerated adapter by its vendor code."""
    for a in list_adapters():
        if a.code == code:
            return a
    return None


class RP1210Error(RuntimeError):
    pass


class RP1210Source(FrameSource):
    def __init__(self, dll_path: str = RP1210_DLL, protocol: str = PROTOCOL,
                 device_id: int = DEVICE_ID, passive: bool = False) -> None:
        self._protocol = protocol
        self._device_id = device_id
        self._is_j1708 = protocol.upper().startswith("J1708")
        self._passive = passive
        self._client_id: Optional[int] = None
        self._dll = ctypes.WinDLL(dll_path)
        self._bind()

    def _bind(self) -> None:
        d = self._dll
        d.RP1210_ClientConnect.restype = c_short
        d.RP1210_ClientConnect.argtypes = [
            wintypes.HWND, c_short, ctypes.c_char_p,
            ctypes.c_long, ctypes.c_long, c_short,
        ]
        d.RP1210_ClientDisconnect.restype = c_short
        d.RP1210_ClientDisconnect.argtypes = [c_short]

        d.RP1210_ReadMessage.restype = c_short
        d.RP1210_ReadMessage.argtypes = [c_short, POINTER(c_char), c_short, c_short]

        d.RP1210_SendMessage.restype = c_short
        d.RP1210_SendMessage.argtypes = [
            c_short, POINTER(c_char), c_short, c_short, c_short,
        ]

        d.RP1210_SendCommand.restype = c_short
        d.RP1210_SendCommand.argtypes = [c_short, c_short, POINTER(c_char), c_short]

        d.RP1210_GetErrorMsg.restype = c_short
        d.RP1210_GetErrorMsg.argtypes = [c_short, POINTER(c_char)]

    # -- helpers --------------------------------------------------------- #
    def _error_text(self, code: int) -> str:
        buf = ctypes.create_string_buffer(80)
        self._dll.RP1210_GetErrorMsg(c_short(code), buf)
        return buf.raw.split(b"\x00")[0].decode("ascii", "ignore")

    # -- FrameSource API -------------------------------------------------- #
    def connect(self) -> None:
        client = self._dll.RP1210_ClientConnect(
            None, self._device_id, self._protocol.encode("ascii"),
            TX_BUFFER, RX_BUFFER, 0,   # 0 = not ISO15765
        )
        if client <= 0:
            raise RP1210Error(f"ClientConnect failed: {self._error_text(client)}")
        self._client_id = int(client)

        # RP1210 adapters pass NO messages until "Set All Filters to Pass"
        # (command 3) is issued - and this is required for J1708 as well as
        # J1939. Skipping it for J1708 makes every read return "no message" (the
        # bus looks silent even though it is busy). A negative return means the
        # command was rejected (e.g. no hardware on the bus), even though
        # ClientConnect returned a positive client id.
        rc = self.send_command(CMD_SET_ALL_FILTERS_PASS)
        if rc < 0:
            self.close()
            raise RP1210Error(f"Filter command failed: {self._error_text(rc)}")
        if not self._is_j1708 and not self._passive:
            # J1939 only: claim a source address before the adapter will transmit
            # (e.g. a Request message) on the bus. Passive listeners skip the
            # claim (claiming our usual 0xF9 would collide with the other tool's
            # off-board address); with filters open they can still RECEIVE.
            claim = bytes([TOOL_SOURCE_ADDR]) + _tool_name() + bytes([0x00])  # 0x00 = block until claimed
            rc = self.send_command(CMD_PROTECT_J1939_ADDR, claim)
            if rc < 0:
                self.close()
                raise RP1210Error(f"Address claim failed: {self._error_text(rc)}")

    def read_frame(self) -> Optional[Frame]:
        if self._client_id is None:
            return None
        buf = ctypes.create_string_buffer(RX_BUFFER)
        n = self._dll.RP1210_ReadMessage(
            self._client_id, buf, RX_BUFFER, NON_BLOCKING,
        )
        # Transient receive-queue overflow: checked BEFORE the sign test, because
        # some drivers return it POSITIVE (139) and it must not be mistaken for a
        # 139-byte frame.
        if n in (ERR_RX_QUEUE_FULL, ERR_RX_QUEUE_FULL_NEG):
            # Our read loop fell behind and the adapter dropped frames out of its
            # receive queue. The link is still up - just keep polling.
            return None
        if n < 0:
            # Any other negative return is a real RP1210 *error* code (not "no
            # message"): the adapter/vehicle link has been lost (USB unplugged,
            # bus powered off, or an internal comm error). Raise so the GUI can
            # clear stale data and tell the user instead of leaving the last
            # values frozen on screen. The FrameReader's `finally` closes us.
            raise RP1210Error(f"Connection lost: {self._error_text(n)}")
        if self._is_j1708:
            return from_rp1210_buffer(buf.raw, n)
        if n <= 10:   # no message, or too short to be a valid frame
            return None
        raw = buf.raw
        return Frame(
            pgn=int.from_bytes(raw[4:7], "little"),
            data=raw[10:n],
            source=raw[8],
            destination=raw[9],
            priority=raw[7] & 0x07,
        )

    def read_raw_hex(self) -> Optional[str]:
        """Read one raw RP1210 buffer and return its hex (diagnostic sniff).

        Unlike `read_frame`, this never parses J1939/J1708 fields: it returns
        the adapter's receive bytes verbatim, so a bus can be inspected even
        when frames don't decode as expected. Returns ``None`` when there is
        no message pending (or no connection).
        """
        if self._client_id is None:
            return None
        buf = ctypes.create_string_buffer(RX_BUFFER)
        n = self._dll.RP1210_ReadMessage(
            self._client_id, buf, RX_BUFFER, NON_BLOCKING,
        )
        if n <= 0:
            return None
        return buf.raw[:n].hex().upper()

    def write_frame(self, frame: Frame) -> None:
        if self._client_id is None:
            return
        if self._is_j1708:
            # J1587 requests / DTC-clear are not wired in v1 (see TODO).
            return
        # Transmit layout: PGN(3 LE) + priority(1) + source(1) + dest(1) + data
        payload = (
            frame.pgn.to_bytes(3, "little")
            + bytes([frame.priority & 0x07, frame.source, frame.destination])
            + frame.data
        )
        buf = ctypes.create_string_buffer(bytes(payload))
        rc = self._dll.RP1210_SendMessage(
            self._client_id, buf, len(payload), 0, 0,
        )
        if rc < 0:
            raise RP1210Error(f"SendMessage failed: {self._error_text(rc)}")

    def send_j1708(self, mid: int, data: bytes) -> None:
        """Transmit one J1708/J1587 message. `mid` is the sender MID and `data`
        is the J1587 body (PID + fields); the adapter appends the J1708 checksum."""
        if self._client_id is None:
            return
        # RP1210 J1708 SendMessage buffer: [length][MID][data...], where length
        # is the number of bytes after the length byte (MID + data); the adapter
        # appends the J1708 checksum. Omitting the leading length byte makes the
        # adapter silently drop the message (send 'succeeds' but nothing goes out).
        payload = bytes([1 + len(data)]) + bytes([mid & 0xFF]) + bytes(data)
        buf = ctypes.create_string_buffer(payload)
        rc = self._dll.RP1210_SendMessage(
            self._client_id, buf, len(payload), 0, 0,
        )
        if rc < 0:
            raise RP1210Error(f"J1708 SendMessage failed: {self._error_text(rc)}")

    def send_command(self, command: int, data: bytes = b"") -> int:
        """Send an RP1210 command to this client (e.g. filter / address cmds)."""
        if self._client_id is None:
            return -1
        buf = ctypes.create_string_buffer(data if data else b"\x00")
        return int(self._dll.RP1210_SendCommand(
            command, self._client_id, buf, len(data),
        ))

    def send_raw_message(self, data: bytes) -> int:
        """RP1210_SendMessage with a caller-built buffer (no protocol framing).

        For protocols the normal `write_frame` framing doesn't fit (raw CAN,
        ISO15765/OBD-II): the caller builds the exact buffer the driver
        expects. Returns the RP1210 result code (0 = accepted).
        """
        if self._client_id is None:
            return -1
        buf = ctypes.create_string_buffer(data)
        # Signature: (clientID, pBuffer, NumBytes, BlockOnSend, ExtraTimeStatus).
        return int(self._dll.RP1210_SendMessage(
            self._client_id, buf, len(data), NON_BLOCKING, 0,
        ))

    def close(self) -> None:
        if self._client_id is not None:
            self._dll.RP1210_ClientDisconnect(self._client_id)
            self._client_id = None


def _bridge_command() -> Optional[list[str]]:
    """Return the argv used to spawn the 32-bit bridge, or None if unavailable.

    Frozen build: a bundled ``OpenTruckBridge32.exe`` sits next to the main exe.
    Source checkout: run ``rp1210_bridge.py`` under a 32-bit Python if present.
    """
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "rp1210_bridge.py")
    if getattr(sys, "frozen", False):
        exe = os.path.join(os.path.dirname(sys.executable), "OpenTruckBridge32.exe")
        return [exe] if os.path.exists(exe) else None
    for py in (
        r"C:\Program Files (x86)\Python313-32\python.exe",
        r"C:\Program Files (x86)\Python312-32\python.exe",
        r"C:\Program Files (x86)\Python311-32\python.exe",
        r"C:\Python313-32\python.exe",
        r"C:\Python312-32\python.exe",
        r"C:\Python311-32\python.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python313-32\python.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python312-32\python.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python311-32\python.exe"),
    ):
        if os.path.exists(py):
            return [py, script]
    return None


class BridgedRP1210Source(FrameSource):
    """Drive a 32-bit-only RP1210 DLL through an out-of-process 32-bit bridge.

    Same interface as `RP1210Source`; each call is an IPC round-trip to
    ``rp1210_bridge`` (which runs the real ctypes calls under a 32-bit Python).
    A lock serialises calls because `read_frame` runs on the reader thread while
    `write_frame`/`send_command` run on the GUI thread.
    """

    def __init__(self, dll_path: str, protocol: str, device_id: int = 1,
                 passive: bool = False,
                 bridge_command: Optional[list[str]] = None) -> None:
        self._dll_path = dll_path
        self._protocol = protocol
        self._device_id = device_id
        self._is_j1708 = protocol.upper().startswith("J1708")
        self._passive = passive   # listen-only: filters open, no address claim
        self._bridge_command = bridge_command if bridge_command is not None \
            else _bridge_command()
        self._proc = None
        self._lock = threading.Lock()

    def _spawn(self) -> None:
        if not self._bridge_command:
            raise RP1210Error(
                "This adapter's driver is 32-bit and needs the OpenTruck 32-bit "
                "bridge, but no bridge executable was found. Build the bridge "
                "with a 32-bit Python (see build.bat) and re-run.")
        self._proc = subprocess.Popen(
            self._bridge_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            bufsize=1, text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def _call(self, req: dict) -> dict:
        if self._proc is None:
            self._spawn()
        with self._lock:
            self._proc.stdin.write(json.dumps(req) + "\n")
            self._proc.stdin.flush()
            line = self._proc.stdout.readline()
        if not line:
            raise RP1210Error("32-bit bridge exited unexpectedly")
        return json.loads(line)

    def connect(self) -> None:
        self._spawn()
        resp = self._call({
            "op": "client_connect", "dll": self._dll_path,
            "device_id": self._device_id, "protocol": self._protocol,
        })
        if resp.get("rc", 0) <= 0:
            self.close()
            raise RP1210Error(
                f"ClientConnect failed: "
                f"{resp.get('error', 'rc ' + str(resp.get('rc')))}")
        if not self._is_j1708:
            rc = self.send_command(CMD_SET_ALL_FILTERS_PASS)
            if rc < 0:
                self.close()
                raise RP1210Error(f"Filter command failed (rc {rc})")
            if not self._passive:
                claim = bytes([TOOL_SOURCE_ADDR]) + _tool_name() + bytes([0x00])
                rc = self.send_command(CMD_PROTECT_J1939_ADDR, claim)
                if rc < 0:
                    self.close()
                    raise RP1210Error(f"Address claim failed (rc {rc})")

    def read_frame(self):
        resp = self._call({"op": "read_message"})
        n = int(resp.get("n", 0))
        if n in (ERR_RX_QUEUE_FULL, ERR_RX_QUEUE_FULL_NEG):
            # Transient receive-queue overflow (see constant): keep polling.
            return None
        if n < 0:
            raise RP1210Error(f"Connection lost (rc {n})")
        raw = bytes.fromhex(resp.get("raw", ""))
        if self._is_j1708:
            return from_rp1210_buffer(raw, n)
        if n <= 10:
            return None
        return Frame(
            pgn=int.from_bytes(raw[4:7], "little"),
            data=raw[10:n],
            source=raw[8],
            destination=raw[9],
            priority=raw[7] & 0x07,
        )

    def read_raw_hex(self) -> Optional[str]:
        """Raw receive buffer as hex (diagnostic sniff); see RP1210Source."""
        resp = self._call({"op": "read_message"})
        n = int(resp.get("n", 0))
        if n <= 0:
            return None
        return resp.get("raw", "").upper()

    def write_frame(self, frame: Frame) -> None:
        if self._is_j1708:
            return   # J1587 TX is not wired up (same as RP1210Source)
        payload = (
            frame.pgn.to_bytes(3, "little")
            + bytes([frame.priority & 0x07, frame.source, frame.destination])
            + frame.data
        )
        resp = self._call({"op": "send_message", "data": payload.hex()})
        if resp.get("rc", 0) < 0:
            raise RP1210Error(f"SendMessage failed (rc {resp.get('rc')})")

    def send_j1708(self, mid: int, data: bytes) -> None:
        """Transmit one J1708/J1587 message over the bridge (see RP1210Source)."""
        # Same [length][MID][data...] framing as RP1210Source.send_j1708.
        payload = bytes([1 + len(data)]) + bytes([mid & 0xFF]) + bytes(data)
        resp = self._call({"op": "send_message", "data": payload.hex()})
        if resp.get("rc", 0) < 0:
            raise RP1210Error(f"J1708 SendMessage failed (rc {resp.get('rc')})")

    def send_command(self, command: int, data: bytes = b"") -> int:
        resp = self._call({"op": "send_command", "number": command,
                           "data": data.hex()})
        return int(resp.get("rc", -1))

    def send_raw_message(self, data: bytes) -> int:
        """Raw SendMessage through the bridge (see RP1210Source)."""
        resp = self._call({"op": "send_message", "data": data.hex()})
        return int(resp.get("rc", -1))

    def close(self) -> None:
        if self._proc is not None:
            try:
                self._call({"op": "client_disconnect"})
                self._call({"op": "shutdown"})
            except Exception:
                pass
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None
