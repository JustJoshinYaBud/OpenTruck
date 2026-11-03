"""OpenTruck - frame sources.

A `FrameSource` yields J1939 `Frame` objects. The replay source lets you test
all the parsing logic with zero hardware; the RP1210 source is the live
heavy-duty adapter backend.
"""
from __future__ import annotations

import connectlog

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from modules.j1939 import Frame


class FrameSource(ABC):
    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def read_frame(self) -> Optional[Frame]:
        """Return the next frame, or None if none is currently available."""

    @abstractmethod
    def write_frame(self, frame: Frame) -> None:
        """Transmit a frame (used for requests / DTC clear)."""

    @abstractmethod
    def close(self) -> None: ...


class LoggingSource(FrameSource):
    """Wraps a source and tees every frame (received AND transmitted) to a
    replay-format log with an `RX` / `TX` direction marker.

    Useful for capturing a real truck's traffic so it can be replayed or
    analysed offline (to add new live-data decoders / manufacturer codes,
    or to see exactly what request/clear frames the tool itself sent).

    Construct with a `path` to always log, or with no path and call
    `start(path)` / `stop()` later to toggle logging on demand (used by the
    GUI "Tools > Start Logging..." toggle and "Developer > Capture"). A lock
    keeps the GUI-thread start/stop safe against the reader thread's write.
    """

    def __init__(self, inner: "FrameSource", path: Optional[str] = None) -> None:
        self._inner = inner
        self._fh = None
        self._path: Optional[str] = None
        self._lock = threading.Lock()
        if path is not None:
            self.start(path)

    @property
    def logging(self) -> bool:
        return self._fh is not None

    @property
    def path(self) -> Optional[str]:
        return self._path

    def start(self, path: str) -> None:
        """Open a log file and begin teeing frames to it."""
        with self._lock:
            self._close_locked()
            self._fh = open(path, "w", encoding="utf-8")
            self._fh.write("# OpenTruck raw capture (RX = received, TX = transmitted)\n")
            self._fh.write("# J1939 frame:   <arbid_hex>:<data_hex>\n")
            self._fh.write("# J1708 message: J1708 <mid_hex>:<pid_and_data_hex>\n")
            self._fh.write("# CDL message:   CDL <mid_hex>:<dest_iid_and_data_hex>\n")
            self._fh.write("# raw CAN frame: can2 <can_id_hex>:<data_hex>\n")
            self._fh.flush()
            self._path = path

    def _log(self, direction: str, frame: Frame) -> None:
        """Append one frame to the log with its direction, flushing immediately
        so a still-running capture is readable on disk."""
        with self._lock:
            if self._fh is not None:
                try:
                    self._fh.write(f"{direction} {frame.to_log_line()}\n")
                    self._fh.flush()
                except Exception:             # noqa: BLE001
                    pass

    def stop(self) -> None:
        """Flush and close the log file, if any."""
        with self._lock:
            self._close_locked()
            self._path = None

    def _close_locked(self) -> None:
        if self._fh is not None:
            try:
                self._fh.flush()
            except Exception:                 # noqa: BLE001
                pass
            try:
                self._fh.close()
            except Exception:                 # noqa: BLE001
                pass
            self._fh = None

    def connect(self) -> None:
        self._inner.connect()

    def read_frame(self) -> Optional[Frame]:
        f = self._inner.read_frame()
        if f is not None:
            self._log("RX", f)
        return f

    def write_frame(self, frame: Frame) -> None:
        # Record outgoing traffic too (request / clear frames the tool itself
        # transmits), tagged TX so analysis can separate the two directions.
        self._log("TX", frame)
        self._inner.write_frame(frame)

    def send_j1708(self, mid: int, data: bytes) -> None:
        """Log and forward an outgoing J1708/J1587 transmit."""
        with self._lock:
            if self._fh is not None:
                try:
                    self._fh.write(f"TX J1708 {mid:02X}:{data.hex().upper()}\n")
                    self._fh.flush()
                except Exception:             # noqa: BLE001
                    pass
        inner = getattr(self._inner, "send_j1708", None)
        if inner is not None:
            inner(mid, data)

    def close(self) -> None:
        self.stop()
        self._inner.close()


class ReplaySource(FrameSource):
    """Replays frames from a text log.

    Log format, one frame per line:
        <arbid_hex>:<data_hex>
    e.g.  18FECA00:FC003A0000000000
    Blank lines and lines starting with '#' are ignored.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._frames: list[Frame] = []
        self._i = 0

    def connect(self) -> None:
        self._frames = []
        with open(self.path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Trim an optional direction prefix ("RX " / "TX ") that
                # LoggingSource now writes; older logs have none.
                if line[:3] in ("RX ", "TX "):
                    line = line[3:]
                arbid_s, _, data_s = line.partition(":")
                try:
                    self._frames.append(
                        Frame.from_arbid(int(arbid_s, 16), bytes.fromhex(data_s)))
                except ValueError:
                    continue
        self._i = 0

    def read_frame(self) -> Optional[Frame]:
        if self._i >= len(self._frames):
            return None
        f = self._frames[self._i]
        self._i += 1
        return f

    def write_frame(self, frame: Frame) -> None:
        # read-only replay: ignore writes
        pass

    def close(self) -> None:
        pass


@dataclass
class TaggedFrame:
    """A received frame tagged with the protocol it arrived on, so a
    multi-protocol reader can route it to the right decoder (J1939 vs J1708)."""
    protocol: str        # "j1939" | "j1708" | "cdl" | "can2"
    frame: object        # j1939.Frame | j1708.J1708Message | cdl.CDLMessage/
                         # framesource.CdlFrame | framesource.RawCanFrame

    def to_log_line(self) -> str:
        return self.frame.to_log_line()


@dataclass
class CdlFrame:
    """A RAW buffer from a Cat Data Link (CDL) client - deliberately undecoded.

    The CDL wire format is CAT-proprietary and the receive-buffer layout of
    the RP1210 ``CAT`` protocol has not been verified against hardware yet,
    so this channel is CAPTURE-ONLY: every byte is preserved and logged
    (``cdl <hex>``), never interpreted. A decoder gets built offline from a
    real capture - not guessed (the same rule the raw-CAN wire formats
    followed, NOTES.md "Raw-CAN capture wire formats").
    """
    raw: bytes
    ts_ms: int = 0

    def to_log_line(self) -> str:
        return f"cdl {self.raw.hex().upper()}"


@dataclass
class RawCanFrame:
    """A RAW CAN frame from a raw-CAN channel (protocol tag 'can2').

    Deliberately undecoded: the point is to see EVERYTHING on the wire,
    including traffic the J1939 layer doesn't handle (proprietary PGNs,
    11-bit frames, handshake/commands such as a regen initiation). Log
    format 'can2 <id>:<data>' is distinct from the J1939 replay format so
    ReplaySource never misreads it - analyse captures offline instead.
    """
    can_id: int
    data: bytes
    ts_ms: int = 0
    ext: bool = True          # True = 29-bit id, False = 11-bit

    def to_log_line(self) -> str:
        idw = 8 if self.ext else 3
        return f"can2 {self.can_id:0{idw}X}:{self.data.hex().upper()}"


class RawCdlSource(FrameSource):
    """Reads raw CDL buffers through an RP1210 ``CAT`` protocol client.

    Wrap a client built with the vendor INI's ``CAT`` protocol string and
    ``passive=True`` (listen-only - CDL has request/broadcast messages, and
    this tool transmits nothing until the format is verified). Receive-only,
    capture-only: frames arrive as CdlFrame and every read error is swallowed
    (see RawCanSource - a capture channel must never kill the session).
    """

    def __init__(self, client) -> None:
        self._client = client

    def connect(self) -> None:
        self._client.connect()

    def read_frame(self) -> Optional[CdlFrame]:
        try:
            raw = self._client.read_raw_hex()
        except Exception:                   # noqa: BLE001
            return None
        if not raw:
            return None
        try:
            data = bytes.fromhex(raw)
        except ValueError:
            return None
        if not data:
            return None
        return CdlFrame(raw=data)

    def write_frame(self, frame) -> None:
        pass                                 # receive-only channel

    def close(self) -> None:
        self._client.close()


class RawCanSource(FrameSource):
    """Reads RAW CAN frames through an RP1210 raw-CAN client (protocol
    'CAN:Baud=...'). Frames arrive as RawCanFrame - everything on the wire,
    undecoded. Receive-only.

    Wrap an already-built RP1210Source/BridgedRP1210Source that was created
    with a CAN protocol string and `passive=True` (listen-only).

    RX buffer layout (observed from RP1210 raw-CAN clients):
    [0:4] timestamp ms LE | [4] flag (01 = 29-bit ext, 00 = 11-bit standard)
    | 29-bit: [5:9] id big-endian, [9:] data | 11-bit: [5:7] id BE, [7:] data.
    """

    def __init__(self, client) -> None:
        self._client = client

    def connect(self) -> None:
        self._client.connect()

    def read_frame(self) -> Optional[RawCanFrame]:
        try:
            raw = self._client.read_raw_hex()
        except Exception:
            # A passive capture channel must never kill the session: any
            # adapter error (queue-full bursts, transient driver states) is
            # just "nothing usable this tick".
            return None
        if not raw:
            return None
        b = bytes.fromhex(raw)
        if len(b) < 9 or b[4] not in (0x00, 0x01):
            return None                      # unknown buffer variant
        ext = b[4] == 0x01
        if ext:
            can_id = int.from_bytes(b[5:9], "big")
            data = b[9:]
        else:
            can_id = int.from_bytes(b[5:7], "big")
            data = b[7:]
        if not data:
            return None
        return RawCanFrame(can_id=can_id, data=data,
                           ts_ms=int.from_bytes(b[0:4], "little"), ext=ext)

    def write_frame(self, frame) -> None:
        pass                                 # receive-only channel

    def close(self) -> None:
        self._client.close()


class CombinedSource:
    """Reads several protocol sources at once (J1939 and J1708/J1587
    simultaneously), tagging each frame with its protocol.

    ``sources`` is a list of ``(protocol, FrameSource)`` pairs. J1939 is the
    write target (requests / DTC-clear); J1708 is receive-only.

    **Every protocol is best-effort, and the connect only fails when none of
    the vehicle buses could be opened.** J1939 used to be mandatory, which
    reported a false "no adapter" on a J1587-only vehicle: there is no HS-CAN
    to open, so the address claim (which needs a bus to claim on) returned
    negative and killed the connect before the J1708 client was even tried.
    A truck from before the J1939 era is a legitimate target for this app - it
    monitors J1587 modules - so a J1708-only link is a real mode, not a
    failure. ``j1939_error`` carries the reason when that happens, for the UI.
    """

    def __init__(self, sources: list[tuple[str, FrameSource]],
                 exclusive: bool = False) -> None:
        self._sources = sources
        # exclusive=True opens ONE client and keeps it: for a driver that can
        # only serve a single session (see rp1210._single_client). The list is
        # then a preference order, not a set - J1939 first, J1708 as the
        # fallback for a vehicle that has no HS-CAN at all.
        self._exclusive = exclusive
        self._connected: set[str] = set()
        self.j1939_error = ""        # why J1939 did not open ("" = it did)
        # Optional progress callback (str -> None): see RP1210Source - the
        # GUI routes these to the activity line during the (blocking, on the
        # GUI thread) connect.
        self.progress = None

    def _report(self, text: str) -> None:
        if self.progress is not None:
            try:
                self.progress(text)
            except Exception:      # noqa: BLE001 - progress never breaks a connect
                pass

    def connect(self) -> None:
        self._connected = set()
        self.j1939_error = ""
        for name, src in self._sources:
            self._report(f"opening the {name} client...")
            try:
                src.connect()
                self._connected.add(name)
                connectlog.write("channel %s: open" % name)
                self._report(f"{name} client open")
            except Exception as exc:        # noqa: BLE001
                self._report(f"{name} client refused")
                connectlog.write("channel %s: FAILED (%s)" % (name, exc))
                if name == "j1939":
                    # Not fatal: J1587-only vehicles have no HS-CAN at all,
                    # and the J1708 client is a separate, still-usable link.
                    self.j1939_error = str(exc) or "J1939 could not be opened"
                # Any non-vehicle protocol is optional: keep going without it.
                continue
            if self._exclusive:
                connectlog.write(
                    "single-client adapter: keeping the %s client only "
                    "(no second connection opened)" % name)
                self._report(f"single-client adapter: keeping the {name} "
                             f"client only")
                break
        if not ({"j1939", "j1708", "cdl"} & self._connected):
            # No vehicle bus opened (J1939, J1708 or the Cat Data Link):
            # that IS a failed connection.
            detail = self.j1939_error or "no protocol could be opened"
            self.close()
            raise RuntimeError(detail)

    def add_source(self, name: str, src: FrameSource) -> bool:
        """Open ONE more client on an already-connected source. Best-effort.

        Exists for the capture-time raw-CAN channel: the wire view is only
        useful while a capture is running, so it is not opened at connect
        time. Returns True when the client connected.

        Refused on an exclusive source - that mode exists precisely because
        the driver serves one session, so a second client is what it cannot
        take. Thread-safe by REBINDING (never mutating) the channel list: the
        reader thread's in-flight iteration keeps the old list and picks the
        new one up on its next pass; closing happens after the rebind, and the
        capture channel is wrapped in RawCanSource, which swallows every read
        error so a mid-close read can never kill the session.
        """
        if self._exclusive:
            connectlog.write(
                "channel %s: not opened - this adapter is connected with "
                "ONE client at a time (single-session driver)" % name)
            return False
        try:
            src.connect()
        except Exception as exc:                # noqa: BLE001
            connectlog.write("channel %s: FAILED (%s)" % (name, exc))
            return False
        self._sources = self._sources + [(name, src)]
        self._connected.add(name)
        connectlog.write("channel %s: open (opened on demand during the "
                         "session)" % name)
        return True

    def remove_source(self, name: str) -> None:
        """Close and drop one client (the capture channel). Best effort."""
        removed = [src for n, src in self._sources if n == name]
        if not removed:
            return
        self._sources = [pair for pair in self._sources if pair[0] != name]
        self._connected.discard(name)
        # Close AFTER the rebind so an in-flight read on the old list cannot
        # reach a client id mid-teardown (see add_source's thread note).
        for src in removed:
            try:
                src.close()
            except Exception:                 # noqa: BLE001
                pass
        connectlog.write("channel %s: closed (on-demand channel removed)"
                         % name)

    def read_frame(self) -> Optional[TaggedFrame]:
        for name, src in self._sources:
            if name not in self._connected:
                continue
            f = src.read_frame()
            if f is not None:
                return TaggedFrame(name, f)
        return None

    def write_frame(self, frame) -> None:
        for name, src in self._sources:
            if name == "j1939" and name in self._connected:
                src.write_frame(frame)
                return

    def send_j1708(self, mid: int, data: bytes) -> None:
        """Route an outgoing J1708/J1587 transmit to the J1708 channel."""
        for name, src in self._sources:
            if name == "j1708" and name in self._connected:
                src.send_j1708(mid, data)
                return

    def channel_connected(self, name: str) -> bool:
        """True when the named protocol's client is open ("cdl", "j1939")."""
        return name in self._connected

    def send_cdl(self, data: bytes) -> Optional[int]:
        """Transmit raw CDL bytes on the Cat Data Link channel.

        `data` is the wire message [src MID][dst MID][IID][data...] with no
        checksum/length - wire-proven framing on the CA3.
        Read requests only reach this path (the session builds them; see
        modules/cdl.py). Returns the RP1210 rc (0 = accepted), or None when
        there is no connected CDL channel.
        """
        for name, src in self._sources:
            if name == "cdl" and name in self._connected:
                rc = src.send_raw_message(data)
                connectlog.write("CDL TX %s -> rc %s"
                                 % (data.hex().upper(), rc))
                return rc
        return None

    def close(self) -> None:
        for name, src in self._sources:
            if name in self._connected:
                try:
                    src.close()
                except Exception:               # noqa: BLE001
                    pass
        self._connected = set()
