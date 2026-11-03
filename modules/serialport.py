"""OpenTruck - minimal serial port access (no third-party dependency).

Only what the ELM327 discovery/probe needs: open a COM port, 8N1 at a chosen
baud rate, write bytes, and collect complete lines until a deadline. Windows
only - the app targets Windows, and other platforms raise ``SerialPortError``
at open time so an import never fails on a developer's Mac.

Implemented directly against ``kernel32`` with ctypes, the same approach the
RP1210 layer uses, so the installer carries no extra runtime dependency
(pyserial would work too, but it is one more thing to bundle and license).

Reading is polled rather than blocking: the port is configured with a zero
read timeout and the caller loops until its own deadline, which is what a
line-oriented protocol like ELM327's wants (the chip answers when it feels
like it, and a reset can take a second).
"""
from __future__ import annotations

import sys
import time
from typing import Optional


class SerialPortError(Exception):
    """Raised when a port cannot be opened, or a transfer fails."""


if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class _DCB(ctypes.Structure):
        """Win32 DCB (device control block), 8N1 layout."""

        _fields_ = [
            ("DCBlength", wintypes.DWORD),
            ("BaudRate", wintypes.DWORD),
            ("fBinary", wintypes.DWORD, 1),
            ("fParity", wintypes.DWORD, 1),
            ("fOutxCtsFlow", wintypes.DWORD, 1),
            ("fOutxDsrFlow", wintypes.DWORD, 1),
            ("fDtrControl", wintypes.DWORD, 2),
            ("fDsrSensitivity", wintypes.DWORD, 1),
            ("fTXContinueOnXoff", wintypes.DWORD, 1),
            ("fOutX", wintypes.DWORD, 1),
            ("fInX", wintypes.DWORD, 1),
            ("fErrorChar", wintypes.DWORD, 1),
            ("fNull", wintypes.DWORD, 1),
            ("fRtsControl", wintypes.DWORD, 2),
            ("fAbortOnError", wintypes.DWORD, 1),
            ("fDummy2", wintypes.DWORD, 17),
            ("wReserved", wintypes.WORD),
            ("XonLim", wintypes.WORD),
            ("XoffLim", wintypes.WORD),
            ("ByteSize", wintypes.BYTE),
            ("Parity", wintypes.BYTE),
            ("StopBits", wintypes.BYTE),
            ("XonChar", ctypes.c_char),
            ("XoffChar", ctypes.c_char),
            ("ErrorChar", ctypes.c_char),
            ("EofChar", ctypes.c_char),
            ("EvtChar", ctypes.c_char),
            ("wReserved1", wintypes.WORD),
        ]

    class _COMMTIMEOUTS(ctypes.Structure):
        _fields_ = [
            ("ReadIntervalTimeout", wintypes.DWORD),
            ("ReadTotalTimeoutMultiplier", wintypes.DWORD),
            ("ReadTotalTimeoutConstant", wintypes.DWORD),
            ("WriteTotalTimeoutMultiplier", wintypes.DWORD),
            ("WriteTotalTimeoutConstant", wintypes.DWORD),
        ]

    _GENERIC_READ = 0x80000000
    _GENERIC_WRITE = 0x40000000
    _OPEN_EXISTING = 3
    _DTR_CONTROL_ENABLE = 0x01
    _RTS_CONTROL_ENABLE = 0x01
    _NOPARITY = 0
    _ONESTOPBIT = 0
    _PURGE_TXCLEAR = 0x0004
    _PURGE_RXCLEAR = 0x0008
    _INVALID_HANDLE = ctypes.c_void_p(-1).value

    _kernel32.CreateFileW.restype = wintypes.HANDLE
    _kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    _kernel32.GetCommState.argtypes = [wintypes.HANDLE, ctypes.POINTER(_DCB)]
    _kernel32.SetCommState.argtypes = [wintypes.HANDLE, ctypes.POINTER(_DCB)]
    _kernel32.SetCommTimeouts.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(_COMMTIMEOUTS)]
    _kernel32.PurgeComm.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    _kernel32.ReadFile.argtypes = [
        wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID,
    ]
    _kernel32.WriteFile.argtypes = [
        wintypes.HANDLE, wintypes.LPCVOID, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID,
    ]
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


class SerialPort:
    """A minimal 8N1 serial port; construct then call :meth:`open`."""

    def __init__(self, port: str, baud: int = 38400,
                 read_timeout: float = 0.2) -> None:
        self.port = port
        self.baud = baud
        self.read_timeout = read_timeout
        self._handle: Optional[int] = None
        self._rx = bytearray()

    # -- lifecycle -------------------------------------------------------- #
    def open(self) -> None:
        """Open and configure the port (8 data bits, no parity, 1 stop bit)."""
        if sys.platform != "win32":
            raise SerialPortError("serial ports are only supported on Windows")
        name = self.port
        if not name.startswith("\\\\.\\"):
            name = "\\\\.\\" + name
        handle = _kernel32.CreateFileW(
            name, _GENERIC_READ | _GENERIC_WRITE, 0, None, _OPEN_EXISTING,
            0, None)
        if not handle or handle == _INVALID_HANDLE:
            raise SerialPortError(
                f"cannot open {self.port} (is it in use?): {self._last_error()}")
        self._handle = handle

        dcb = _DCB()
        dcb.DCBlength = ctypes.sizeof(_DCB)
        if not _kernel32.GetCommState(handle, ctypes.byref(dcb)):
            self.close()
            raise SerialPortError(
                f"cannot read port settings: {self._last_error()}")
        dcb.BaudRate = self.baud
        dcb.ByteSize = 8
        dcb.Parity = _NOPARITY
        dcb.StopBits = _ONESTOPBIT
        dcb.fBinary = 1
        dcb.fParity = 0
        dcb.fOutxCtsFlow = 0
        dcb.fOutxDsrFlow = 0
        dcb.fOutX = 0
        dcb.fInX = 0
        dcb.fAbortOnError = 0
        # ELM-style adapters expect DTR/RTS asserted.
        dcb.fDtrControl = _DTR_CONTROL_ENABLE
        dcb.fRtsControl = _RTS_CONTROL_ENABLE
        if not _kernel32.SetCommState(handle, ctypes.byref(dcb)):
            self.close()
            raise SerialPortError(
                f"cannot apply port settings: {self._last_error()}")

        timeouts = _COMMTIMEOUTS()
        # MAXDWORD interval + BOTH totals zero is the documented non-blocking
        # recipe: ReadFile returns at once with whatever has arrived, so the
        # caller owns the deadline.
        # A non-zero constant here does NOT mean "wait up to N ms for the first
        # byte" - ReadFile blocks for the whole constant, every call. With the
        # 200 ms this port used to set, every ELM exchange cost 200 ms even for
        # a bare `AT I` (measured: 203 ms/request, 34-PID sweep 6.9 s), which is
        # what made OBD live data crawl.
        timeouts.ReadIntervalTimeout = 0xFFFFFFFF
        timeouts.ReadTotalTimeoutMultiplier = 0
        timeouts.ReadTotalTimeoutConstant = 0
        timeouts.WriteTotalTimeoutMultiplier = 0
        timeouts.WriteTotalTimeoutConstant = 500
        if not _kernel32.SetCommTimeouts(handle, ctypes.byref(timeouts)):
            self.close()
            raise SerialPortError(
                f"cannot set port timeouts: {self._last_error()}")
        _kernel32.PurgeComm(handle, _PURGE_RXCLEAR | _PURGE_TXCLEAR)

    def close(self) -> None:
        if self._handle:
            try:
                _kernel32.CloseHandle(self._handle)
            except Exception:          # noqa: BLE001 - never fail on cleanup
                pass
            self._handle = None

    def __enter__(self) -> "SerialPort":
        self.open()
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    # -- transfer --------------------------------------------------------- #
    def write(self, data: bytes) -> None:
        """Send raw bytes."""
        if not self._handle:
            raise SerialPortError("port is not open")
        written = wintypes.DWORD(0)
        ok = _kernel32.WriteFile(
            self._handle, data, len(data), ctypes.byref(written), None)
        if not ok or written.value != len(data):
            raise SerialPortError(f"write failed: {self._last_error()}")

    def discard_input(self) -> None:
        """Drop everything buffered on the port (stale replies).

        A reply that outran its timeout - a reset, or an ELM protocol search -
        would otherwise be read as the answer to the *next* command, shifting
        every reply by one. Measured on hardware: one unread 'OK' after connect
        made every subsequent request return the previous answer.
        """
        self._rx.clear()
        if not self._handle:
            return
        try:
            _kernel32.PurgeComm(self._handle, _PURGE_RXCLEAR)
        except Exception:              # noqa: BLE001 - best effort
            pass

    def read_available(self) -> bytes:
        """Return waiting bytes (empty when there are none)."""
        if not self._handle:
            raise SerialPortError("port is not open")
        buf = ctypes.create_string_buffer(4096)
        got = wintypes.DWORD(0)
        if not _kernel32.ReadFile(
                self._handle, buf, 4096, ctypes.byref(got), None):
            raise SerialPortError(f"read failed: {self._last_error()}")
        return buf.raw[:got.value]

    def read_lines(self, timeout: float = 0.5) -> list[str]:
        """Collect complete CR/LF terminated lines for ``timeout`` seconds.

        ELM-style interfaces answer with ASCII lines and a ``>`` prompt; blank
        lines and the prompt are dropped, so the caller sees only real replies
        ("ELM327 v1.5", "OK", "NO DATA", "?").
        """
        started = time.monotonic()
        deadline = started + timeout
        lines: list[str] = []
        while time.monotonic() < deadline:
            chunk = self.read_available()
            if chunk:
                self._rx.extend(chunk)
                while True:
                    cut = self._next_break()
                    if cut < 0:
                        break
                    raw = bytes(self._rx[:cut])
                    del self._rx[:cut + 1]
                    text = raw.decode("ascii", "replace").strip()
                    if text and text != ">":
                        lines.append(text)
                continue
            self._idle_pause(started)
        return lines

    def read_until_prompt(self, timeout: float = 1.0) -> list[str]:
        """Read lines until the ELM ``>`` prompt (or ``timeout`` expires).

        ELM-style interfaces terminate a reply with a prompt that does NOT sit
        on its own CR-terminated line ("41 0C 1A F8\\r\\r>"), so the prompt has
        to end the read - otherwise every request would wait out the full
        timeout, and a leftover ``>`` would corrupt the next reply.
        """
        started = time.monotonic()
        deadline = started + timeout
        lines: list[str] = []
        current = bytearray()
        while time.monotonic() < deadline:
            chunk = self.read_available()
            if not chunk:
                self._idle_pause(started)
                continue
            self._rx.extend(chunk)
            while self._rx:
                byte = self._rx[0]
                del self._rx[0]
                if byte in (0x0D, 0x0A):
                    text = current.decode("ascii", "replace").strip()
                    if text:
                        lines.append(text)
                    current.clear()
                elif byte == 0x3E:              # '>' prompt = reply finished
                    text = current.decode("ascii", "replace").strip()
                    if text:
                        lines.append(text)
                    return lines
                else:
                    current.append(byte)
        text = current.decode("ascii", "replace").strip()
        if text:
            lines.append(text)
        return lines

    @staticmethod
    def _idle_pause(started: float) -> None:
        """Nap between non-blocking reads.

        Fine-grained while a reply is probably in flight (keeps request latency
        in the low milliseconds), coarser once we are clearly waiting out a
        timeout, so a silent adapter does not spin the CPU for a second.
        """
        time.sleep(0.001 if (time.monotonic() - started) < 0.05 else 0.005)

    def _next_break(self) -> int:
        """Index of the next CR or LF in the buffer, or -1."""
        cr = self._rx.find(b"\r")
        lf = self._rx.find(b"\n")
        if cr < 0:
            return lf
        if lf < 0:
            return cr
        return min(cr, lf)

    @staticmethod
    def _last_error() -> str:
        err = ctypes.get_last_error() if sys.platform == "win32" else 0
        try:
            return f"[WinError {err}] {ctypes.FormatError(err)}"
        except Exception:              # noqa: BLE001
            return f"[WinError {err}]"
