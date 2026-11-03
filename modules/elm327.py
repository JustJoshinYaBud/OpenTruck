"""OpenTruck - ELM327 host link and the OBD-II session that runs over it.

An ELM327-class adapter is not a raw CAN interface: the chip performs the
protocol search, bus initialisation, ISO-TP framing and flow control, and hands
back ASCII. The datasheet (ELM327DS, Elm Electronics) defines the whole host
interface used here:

  * serial link - 38400 baud by default (9600 for cheap clones, 115200 on some
    modern adapters), 8 data bits, no parity, 1 stop bit;
  * ``ATZ`` reset (prints the ID string), ``ATE0`` echo off, ``ATL0`` LF off,
    ``ATL0``/``ATS0`` formatting, ``ATH1`` headers on, ``ATSP0`` automatic
    protocol search, ``ATDPN`` "which protocol did you find";
  * requests are plain ASCII hex (``010C``), the reply is the request mode plus
    0x40 (``41 0C ...``); multi-frame answers arrive as several lines that the
    chip has already reassembled the transport protocol for.

Because the chip does the framing, the host side is a line-oriented client -
which is why :class:`ElmObdSession` subclasses the existing OBD-II session and
only replaces the wire: every PID/DTC/VIN decoder is shared with the raw-CAN
path, unchanged.
"""
from __future__ import annotations

import time
from typing import Callable, List, Optional, Tuple

import connectlog
from modules.elm_adapter import BAUD_CANDIDATES
from modules.obd2 import OBD2Session
from modules.serialport import SerialPort, SerialPortError

# Reply tokens that mean "no usable data" (ELM327DS "OBD Message Formats").
NO_DATA_TOKENS = ("NO DATA", "NODATA", "SEARCHING", "BUS INIT", "STOPPED",
                  "BUFFER FULL", "CAN ERROR", "DATA ERROR", "UNABLE TO CONNECT",
                  "ERROR")

# ID strings the datasheet documents for ELM327 and the compatible interpreters.
ID_TOKENS = ("ELM327", "ELM 327", "STN1", "OBDLINK", "OBD II", "OBDII")

# What the adapter is DOING while it probes, keyed by the compacted status
# token it prints. Surfaced live on the activity line while a connect is
# probing (checked most-specific first; the compacted form strips spaces so
# "BUS INIT: OK" and "BUSINIT:OK" both match).
STATUS_STEPS: list[tuple[str, str]] = [
    ("BUSINIT:OK", "bus initialised - the vehicle answered"),
    ("SEARCHING", "searching for the vehicle's protocol..."),
    ("UNABLETOCONNECT", "no vehicle answered (unable to connect)"),
    ("STOPPED", "search stopped"),
    ("CANERROR", "bus error while probing"),
    ("DATAERROR", "data error while probing"),
    ("BUFFERFULL", "adapter buffer overflow while probing"),
    ("NODATA", "no data - no ECU answered"),
]

DEFAULT_BAUD = 38400

# Last baud rate that answered, per port. Not persisted to disk - the connect
# dialog only knows the port name, so without this every reconnect after a
# disconnect re-tries 38400 first and wastes ~3 s before the right rate.
_LAST_BAUD: dict[str, int] = {}


class ElmError(Exception):
    """A connection or protocol failure talking to the adapter."""


class ElmLink:
    """A connected ELM327: AT setup plus OBD request/response over serial."""

    def __init__(self, port: str, baud: int = DEFAULT_BAUD) -> None:
        self.port = port
        self.baud = baud
        self.id_string = ""
        self.protocol = ""          # raw ATDPN reply, e.g. "A6"
        self.can = True             # 11/29-bit CAN (ISO 15765-4)
        self._sp: Optional[SerialPort] = None
        # Optional progress callback (str -> None): called with short human
        # texts while the link comes up and while the first requests run -
        # the adapter's own status lines (SEARCHING / BUS INIT / UNABLE TO
        # CONNECT) become "what is it doing right now" on the activity
        # line. The OBD worker sets it for the probing phase only, so
        # steady-poll "NO DATA" replies (unsupported PIDs) never spam it.
        self.progress: Optional[Callable[[str], None]] = None

    def _report(self, text: str) -> None:
        if self.progress is not None:
            try:
                self.progress(text)
            except Exception:      # noqa: BLE001 - progress must never break
                pass               # the connect that is being reported

    # -- setup ------------------------------------------------------------ #
    def connect(self, timeout: float = 2.0) -> None:
        """Open the port, reset the adapter and put it in a known state.

        The baud rate is not something Windows knows about, and the connect
        dialog only passes a port name, so the rates are tried in turn (the
        preferred one first) exactly as Tier 1 probing does. Without this an
        adapter running at 115200 - the shipping rate of most modern ones - is
        silent at the ELM default 38400, so connect failed on hardware that
        discovery had just successfully identified. ``self.baud`` ends up as
        the rate that answered.
        """
        preferred = self.baud
        order: List[int] = [preferred]
        order += [rate for rate in BAUD_CANDIDATES if rate not in order]
        errors: List[str] = []
        for index, rate in enumerate(order):
            try:
                # The preferred rate gets the caller's timeout; a wrong rate
                # only needs long enough for a reset to answer.
                self._report(f"opening {self.port} at {rate} baud")
                self._open_at(rate, timeout if index == 0 else min(timeout, 1.2))
                connectlog.write(
                    "ELM %s opened at %d baud: %s"
                    % (self.port, rate, self.id_string or "(no id string)"))
                self._report(f"adapter ready: {self.id_string or 'ELM327'} "
                             f"- protocol: automatic search")
                return
            except (SerialPortError, ElmError) as exc:
                errors.append(f"{rate} baud: {exc}")
                connectlog.write("ELM %s at %d baud: %s"
                                 % (self.port, rate, exc))
                self._report(f"no answer at {rate} baud - trying the next "
                             f"rate")
                self.close()
        self.baud = preferred
        text = (f"no ELM327 identification from {self.port} "
                f"({'; '.join(errors)})")
        connectlog.write("FAIL " + text)
        raise ElmError(text)

    def _open_at(self, baud: int, timeout: float) -> None:
        """Bring the adapter up at ``baud``; raise if it does not identify."""
        self.baud = baud
        self._sp = SerialPort(self.port, baud=baud, read_timeout=0.2)
        self._sp.open()
        # A partial line from a previous session would poison the first reply.
        self._sp.write(b"\r")
        self._sp.read_until_prompt(0.3)

        lines = self.cmd("ATZ", timeout=timeout)      # reset -> ID string
        ident = self._find_id(lines)
        if not ident:
            ident = self._find_id(self.cmd("ATI", timeout=1.0))
        if not ident:
            raise ElmError("no identification")
        self.id_string = ident

        for cmd in ("ATE0", "ATL0", "ATS0", "ATH1"):
            self.cmd(cmd, timeout=1.0)
        # Automatic protocol search; the chip reports what it locked onto.
        self.cmd("ATSP0", timeout=1.0)

    @staticmethod
    def _find_id(lines: List[str]) -> str:
        for line in lines:
            upper = line.upper()
            if any(tok in upper for tok in ID_TOKENS):
                return upper.strip()
        return ""

    def close(self) -> None:
        if self._sp is not None:
            self._sp.close()
            self._sp = None

    # -- AT / OBD transport ---------------------------------------------- #
    def cmd(self, text: str, timeout: float = 1.0) -> List[str]:
        """Send one AT or OBD command, return the reply lines (prompt consumed).

        Buffered input is dropped first. Any reply still sitting there belongs
        to an earlier command that timed out (a reset, a protocol search), and
        reading it as this command's answer shifted every following reply by
        one - the failure that made a connect report "no vehicle" on real
        hardware while the adapter was answering fine.
        """
        if self._sp is None:
            raise ElmError("adapter is not connected")
        self._sp.discard_input()
        self._sp.write((text + "\r").encode("ascii"))
        lines = self._sp.read_until_prompt(timeout)
        # Surface the adapter's own probe status (SEARCHING / BUS INIT /
        # UNABLE TO CONNECT / ...) while a connect is in its probing phase.
        if self.progress is not None:
            for line in lines:
                compact = line.replace(" ", "").upper()
                for token, message in STATUS_STEPS:
                    if token in compact:
                        self._report(message)
                        break
        return lines

    def _learn_protocol(self) -> None:
        """Ask which protocol the automatic search settled on (ATDPN)."""
        lines = self.cmd("ATDPN", timeout=0.6)
        for line in lines:
            text = line.strip().upper()
            if text and text[0] in "A0123456789" and len(text) <= 3:
                number = text[-1]
                if number == "0":
                    # "A0" = automatic search has not locked a protocol yet,
                    # which is what a real adapter answers until the first
                    # request completes (verified: ATDP then reads "AUTO").
                    # Treating it as "not CAN" dropped headers and broke every
                    # later parse, so keep the defaults and ask again next time.
                    return
                self.protocol = text
                # 6/7/8/9 = ISO 15765-4 CAN; 1-5 = the legacy J1850/ISO/KWP set.
                self.can = number in "6789"
                if not self.can:
                    # Legacy protocols have no ISO-TP: no headers needed, and the
                    # whole reply line is the payload. (Approximate - legacy
                    # support is a bonus; light-duty CAN is the target.)
                    self.cmd("ATH0", timeout=0.6)
                return

    def request(self, service: int, pid: Optional[int] = None,
                timeout: float = 1.0) -> List[Tuple[int, bytes]]:
        """Send one OBD request; return [(ecu_id, payload), ...].

        ``ecu_id`` follows the raw-CAN convention (0x7E8.. for CAN; a placeholder
        for legacy protocols), so the shared decoders treat both transports the
        same way.
        """
        cmd = f"{service:02X}" + (f"{pid:02X}" if pid is not None else "")
        lines = self.cmd(cmd, timeout=timeout)
        if not lines:
            lines = self.cmd(cmd, timeout=timeout)      # one retry: dropped reply
        if not self.protocol:
            self._learn_protocol()
        return self._decode_lines(lines, service)

    def send_receive(self, payload: bytes,
                     timeout: float = 1.0) -> List[Tuple[int, bytes]]:
        """Send raw payload bytes; return every reply, positive or negative.

        :meth:`request` keeps only positive responses (mode + 0x40) because that
        is what OBD polling wants. A UDS scan needs the negative ones too:
        "NRC 0x12" is how a module says "I am here, but not like that".
        The caller owns the header (``AT SH``).
        """
        lines = self.cmd(payload.hex().upper(), timeout=timeout)
        return self._decode_lines(lines, None)

    # -- reply parsing ---------------------------------------------------- #
    @staticmethod
    def _is_noise(text: str) -> bool:
        compact = text.replace(" ", "").upper()
        if not compact:
            return True
        if compact == "?":
            return True
        return any(tok.replace(" ", "") in compact for tok in NO_DATA_TOKENS)

    def _split(self, text: str) -> Tuple[Optional[int], bytes]:
        """Split one reply line into (ecu id, payload bytes)."""
        compact = text.replace(" ", "").upper()
        if self.can:
            # ATH1: 11-bit id = 3 hex digits ("7E8 ..."), 29-bit = 8.
            width = 8 if self.protocol and self.protocol[-1] in "79" else 3
            if len(compact) <= width:
                return None, b""
            try:
                ecu = int(compact[:width], 16)
                return ecu, bytes.fromhex(compact[width:])
            except ValueError:
                return None, b""
        # Legacy: ATH0, so the line is the whole message. The ECU identity is
        # not available at this layer; report it under the conventional id.
        try:
            return 0x7E8, bytes.fromhex(compact)
        except ValueError:
            return None, b""

    def _decode_lines(self, lines: List[str],
                      service: Optional[int]) -> List[Tuple[int, bytes]]:
        """Reassemble ISO-TP frames (CAN) and keep the replies we want.

        ``service`` is the requested mode: replies are filtered to its positive
        form (service + 0x40) and negative responses are dropped. ``None`` keeps
        everything, which is what :meth:`send_receive` uses.
        """
        finished: List[Tuple[int, bytes]] = []
        pending: dict[int, dict] = {}
        for line in lines:
            if self._is_noise(line):
                continue
            ecu, payload = self._split(line)
            if ecu is None or not payload:
                continue
            if not self.can:
                finished.append((ecu, payload))
                continue
            pci = payload[0] >> 4
            if pci == 0x0:                        # single frame
                length = payload[0] & 0x0F
                finished.append((ecu, payload[1:1 + length]))
            elif pci == 0x1:                      # first frame
                total = ((payload[0] & 0x0F) << 8) | payload[1]
                pending[ecu] = {"need": total, "buf": bytearray(payload[2:])}
            elif pci == 0x2 and ecu in pending:   # consecutive frame
                state = pending[ecu]
                state["buf"].extend(payload[1:])
                if len(state["buf"]) >= state["need"]:
                    finished.append((ecu, bytes(state["buf"][:state["need"]])))
                    del pending[ecu]

        out: List[Tuple[int, bytes]] = []
        for ecu, resp in finished:
            if not resp:
                continue
            if service is None:
                out.append((ecu, resp))         # raw mode: keep 0x7F too
            elif resp[0] == service + 0x40:     # positive response
                out.append((ecu, resp))
        return out


class ElmObdSession(OBD2Session):
    """OBD-II session over an ELM327 link.

    Inherits the whole decoding stack (supported PIDs, live data, DTCs, VIN,
    ECU names, manufacturer-scoped descriptions) and replaces only the wire:
    :meth:`request` asks the adapter instead of building ISO-TP frames.
    """

    def __init__(self, link: ElmLink) -> None:
        # The base stores a FrameSource; there isn't one on this transport.
        super().__init__(None)                       # type: ignore[arg-type]
        self.link = link

    # -- transport -------------------------------------------------------- #
    def request(self, service: int, pid: Optional[int] = None,
                timeout: float = 1.0) -> List[Tuple[int, bytes]]:
        out = self.link.request(service, pid, timeout=timeout)
        for ecu, _resp in out:
            self.ecus.add(ecu)              # same bookkeeping as the raw-CAN path
        return out

    def read_ecu_names(self) -> None:
        """Mode 09 0A, functional request.

        With headers on, the adapter prints one reply per ECU, so a functional
        request identifies every ECU at once (the raw-CAN path has to unicast
        to each physical address for the same information).
        """
        for ecu, resp in self.request(0x09, 0x0A, timeout=1.2):
            self._apply_ecu_name(ecu, resp)

    def read_cal_ids(self) -> None:
        """Mode 09 04 calibration identifiers (functional, one line per ECU)."""
        for ecu, resp in self.request(0x09, 0x04, timeout=1.2):
            self._apply_cal_id(ecu, resp)

    def close(self) -> None:
        self.link.close()


def open_elm_session(port: Optional[str] = None,
                     baud: Optional[int] = None,
                     progress: Optional[Callable[[str], None]] = None
                     ) -> ElmObdSession:
    """Connect to an ELM327 and return a ready OBD-II session.

    With a port, that port is used directly (the usual path - the user picked
    it in the connect dialog). Without one, the serial ports are probed for an
    ELM327 (AT only, no vehicle traffic) and the first that answers is used.
    ``progress`` (str -> None), when given, receives short human texts for
    every step: baud attempts, adapter identification, and the adapter's own
    probe status lines (SEARCHING / BUS INIT / UNABLE TO CONNECT) - the
    caller shows them live while the connect is in progress.
    """
    if port:
        connectlog.write("ELM selected port %s" % port)
        link = ElmLink(port, baud=baud or _LAST_BAUD.get(port) or DEFAULT_BAUD)
        link.progress = progress
        link.connect()
        _LAST_BAUD[port] = link.baud
        return ElmObdSession(link)

    from modules.elm_adapter import list_candidates, probe

    errors: List[str] = []
    connectlog.write("ELM no port given - probing every candidate")
    for cand in list_candidates(likely_only=True):
        try:
            connectlog.write("ELM probe %s (%s)" % (cand.port, cand.label))
            if probe(cand).is_elm:
                link = ElmLink(cand.port, baud=cand.baud or DEFAULT_BAUD)
                link.connect()
                _LAST_BAUD[cand.port] = link.baud
                return ElmObdSession(link)
        except (SerialPortError, ElmError) as exc:
            errors.append(f"{cand.port}: {exc}")
        except Exception as exc:          # noqa: BLE001 - keep probing
            errors.append(f"{cand.port}: {exc}")
    detail = ("; ".join(errors)) if errors else "no serial ports found"
    raise ElmError(f"No ELM327 adapter answered ({detail})")
