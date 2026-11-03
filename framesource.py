"""OpenTruck - frame sources.

A `FrameSource` yields J1939 `Frame` objects. The replay source lets you test
all the parsing logic with zero hardware; the RP1210 source is the live
heavy-duty adapter backend.
"""
from __future__ import annotations

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
    protocol: str        # "j1939" | "j1708"
    frame: object        # j1939.Frame | j1708.J1708Message

    def to_log_line(self) -> str:
        return self.frame.to_log_line()


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
    write target (requests / DTC-clear); J1708 is receive-only. J1708 (and any
    other optional protocol) is best-effort: if an adapter can't open it, the
    J1939 link is kept and the remaining sources still flow.
    """

    def __init__(self, sources: list[tuple[str, FrameSource]]) -> None:
        self._sources = sources
        self._connected: set[str] = set()

    def connect(self) -> None:
        self._connected = set()
        for name, src in self._sources:
            try:
                src.connect()
                self._connected.add(name)
            except Exception:
                if name == "j1939":
                    self.close()
                    raise
                # Any non-primary protocol is optional: keep going without it.

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

    def close(self) -> None:
        for name, src in self._sources:
            if name in self._connected:
                try:
                    src.close()
                except Exception:               # noqa: BLE001
                    pass
        self._connected = set()
