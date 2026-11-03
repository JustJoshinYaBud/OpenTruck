"""OpenTruck - ELM327 adapter discovery.

Two tiers, mirroring how RP1210 adapters are found:

**Tier 1 - passive enumeration.** Windows already knows every serial port and
which USB device is behind it. Reading that registry data gives the port, the
USB VID/PID and the driver's friendly name ("vLinker FS USB") without opening
anything: instant, safe, and it works even for adapters we have no driver for.

There is no ELM327 equivalent of RP1210's vendor INIs - nothing is "installed",
the adapter either is plugged in or it isn't - so passive enumeration can only
report what is present right now.

**Tier 2 - active identification.** A USB VID/PID only proves which *chip* is
in the cable: FTDI and CH340 are used by countless non-OBD gadgets. The only
reliable answer is to ask the device who it is - ``ATZ`` (reset) then ``ATI``
(identification) - and look for an ``ELM327``/``STN``/``OBDLink`` ID string.
Baud rates vary between clones (38400 is the ELM default, many adapters ship
at 115200, cheap ones are stuck on 9600), so each candidate is tried at several.

Nothing here transmits OBD requests: probing only speaks the AT command set,
so it is harmless to a vehicle.
"""
from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Iterable, Optional

from modules.serialport import SerialPort, SerialPortError

# --- Tier 1: what Windows tells us ------------------------------------------ #

# USB-to-serial bridges used by ELM327 adapters. Values: (kind, human name).
# A match makes a port "worth probing" - it does NOT prove an ELM327 is there.
KNOWN_USB = {
    (0x0403, 0x6001): ("ftdi", "FTDI FT232R"),
    (0x0403, 0x6010): ("ftdi", "FTDI FT2232"),
    (0x0403, 0x6014): ("ftdi", "FTDI FT232H"),
    (0x0403, 0x6015): ("ftdi", "FTDI FT230X"),
    (0x10C4, 0xEA60): ("cp210x", "Silicon Labs CP210x"),
    (0x10C4, 0xEA70): ("cp210x", "Silicon Labs CP2105"),
    (0x10C4, 0xEA71): ("cp210x", "Silicon Labs CP2108"),
    (0x1A86, 0x7523): ("ch34x", "WCH CH340"),
    (0x1A86, 0x5523): ("ch34x", "WCH CH341"),
    (0x1A86, 0x55D4): ("ch34x", "WCH CH343/CH9102"),
    (0x067B, 0x2303): ("pl2303", "Prolific PL2303"),
    (0x0483, 0x5740): ("cdc", "STM32 USB CDC"),
    (0x2341, 0x0043): ("cdc", "Arduino-style CDC"),
}

# Friendly-name words that suggest an OBD adapter even when the chip is unknown.
# The chip families are here too: a clone whose VID/PID we do not list still
# reports "USB-SERIAL CH340" as its device name.
LIKELY_WORDS = ("elm", "obd", "vlinker", "vgate", "obdlink", "stn", "scan",
                "diagnos", "autel", "launch", "icar", "kcan",
                "ch34", "cp210", "ftdi", "pl2303")
# Deliberately NOT "usb serial": that is the generic Windows CDC driver name
# ("USB Serial Device (COM3)") used by phones, GPS pucks and debug boards - it
# made every such device "likely" on real hardware.


@dataclass
class ElmCandidate:
    """One serial port that might be an ELM327-class adapter."""

    port: str                       # "COM7"
    label: str = ""                 # driver friendly name, e.g. "vLinker FS USB"
    vid: Optional[int] = None
    pid: Optional[int] = None
    kind: str = "unknown"           # ftdi / cp210x / ch34x / pl2303 / cdc / bluetooth / unknown
    source: str = "usb"             # usb / bluetooth / legacy
    present: bool = True            # port exists now (registered with Windows)
    likely: bool = False            # worth probing by default
    # Tier 2 results
    probed: bool = False
    is_elm: Optional[bool] = None   # None = not probed
    id_string: str = ""
    baud: Optional[int] = None
    error: str = ""

    @property
    def chip(self) -> str:
        """Human name of the USB bridge (or 'Bluetooth SPP' / 'Unknown')."""
        known = KNOWN_USB.get((self.vid, self.pid))
        if known is not None:
            return known[1]
        if self.kind == "bluetooth":
            return "Bluetooth SPP"
        return self.kind.title() if self.kind != "unknown" else "Unknown"

    @property
    def status(self) -> str:
        """One-line description for a list/dialog."""
        if not self.probed:
            return "not probed"
        if self.is_elm:
            return f"{self.id_string} @ {self.baud} baud"
        return self.error or "no ELM327 response"


def _com_number(port: str) -> int:
    """Sort key: COM10 after COM9."""
    digits = "".join(ch for ch in port if ch.isdigit())
    return int(digits) if digits else 0


def _clean_value(value) -> str:
    """Registry strings may be '@file.inf,%name%;Real Name' - keep the name."""
    if isinstance(value, bytes):
        value = value.decode("utf-16-le", "replace").rstrip("\x00")
    text = str(value)
    if text.startswith("@") and ";" in text:
        text = text.rsplit(";", 1)[1]
    return text.strip()


def _reg_value(key, name: str) -> str:
    import winreg
    try:
        value, _kind = winreg.QueryValueEx(key, name)
    except OSError:
        return ""
    return _clean_value(value)


def _serialcomm_ports() -> dict[str, str]:
    """COM ports Windows has registered: port -> device path."""
    if sys.platform != "win32":
        return {}
    import winreg
    ports: dict[str, str] = {}
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"HARDWARE\DEVICEMAP\SERIALCOMM") as key:
            i = 0
            while True:
                try:
                    name, value, _kind = winreg.EnumValue(key, i)
                except OSError:
                    break
                i += 1
                ports[_clean_value(value).upper()] = name
    except OSError:
        return {}
    return ports


def _enum_bus_ports(bus: str, source: str) -> list[dict]:
    """Walk ``HKLM\\SYSTEM\\CurrentControlSet\\Enum\\<bus>`` for serial ports.

    Each USB device instance that exposes a COM port stores it under
    ``Device Parameters\\PortName``; the instance key also carries the driver's
    FriendlyName. Bluetooth SPP ports live under BTHENUM with the same layout.

    ``bus`` is the enumerator branch, and it matters which one is walked: an
    FTDI VCP device appears twice - a bare USB converter under ``Enum\\USB``
    (no PortName) and the actual serial port under ``Enum\\FTDIBUS`` (e.g.
    ``VID_0403+PID_6015+SERIAL``). Only the latter carries the COM name.
    """
    if sys.platform != "win32":
        return []
    import winreg
    found: list[dict] = []
    root = rf"SYSTEM\CurrentControlSet\Enum\{bus}"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, root) as bus_key:
            i = 0
            while True:
                try:
                    device = winreg.EnumKey(bus_key, i)      # e.g. VID_0403&PID_6001
                except OSError:
                    break
                i += 1
                vid = pid = None
                upper = device.upper()
                if upper.startswith("VID_"):
                    try:
                        vid = int(upper[4:8], 16)
                        pid = int(upper.split("PID_", 1)[1][:4], 16)
                    except (ValueError, IndexError):
                        vid = pid = None
                try:
                    with winreg.OpenKey(bus_key, device) as dev_key:
                        j = 0
                        while True:
                            try:
                                instance = winreg.EnumKey(dev_key, j)
                            except OSError:
                                break
                            j += 1
                            try:
                                with winreg.OpenKey(dev_key, instance) as inst:
                                    port = ""
                                    try:
                                        with winreg.OpenKey(
                                                inst, "Device Parameters") as params:
                                            port = _reg_value(params, "PortName")
                                    except OSError:
                                        pass
                                    if not port:
                                        port = _reg_value(inst, "PortName")
                                    if not port.upper().startswith("COM"):
                                        continue
                                    found.append({
                                        "port": port.upper(),
                                        "label": (_reg_value(inst, "FriendlyName")
                                                  or _reg_value(inst, "DeviceDesc")),
                                        "manufacturer": _reg_value(inst, "Manufacturer"),
                                        "vid": vid, "pid": pid, "source": source,
                                    })
                            except OSError:
                                continue
                except OSError:
                    continue
    except OSError:
        return []
    return found


def list_candidates(likely_only: bool = False) -> list[ElmCandidate]:
    """Enumerate serial ports that could be an ELM327 adapter (Tier 1).

    Never opens a port, so it is instant and safe to call from the GUI thread.
    ``likely_only`` drops ports with no USB-serial identity and no OBD-ish name
    (a motherboard COM1, say) - they can still be probed on request.
    """
    registered = _serialcomm_ports()
    entries = (_enum_bus_ports("USB", "usb")
               + _enum_bus_ports("FTDIBUS", "usb")   # FTDI VCP: the real port
               + _enum_bus_ports("BTHENUM", "bluetooth"))

    by_port: dict[str, ElmCandidate] = {}
    for item in entries:
        port = item["port"]
        # A device that was unplugged keeps its Enum entry (and PortName), so
        # the registry can list ports that no longer exist. SERIALCOMM only
        # holds ports Windows has registered right now - use that to tell.
        present = port in registered
        kind = "bluetooth" if item["source"] == "bluetooth" else "unknown"
        name = ""
        if item["vid"] is not None and item["pid"] is not None:
            kind, name = KNOWN_USB.get((item["vid"], item["pid"]), ("unknown", ""))
        label = item["label"] or name or "Serial port"
        by_port[port] = ElmCandidate(
            port=port, label=label, vid=item["vid"], pid=item["pid"],
            kind=kind, source=item["source"], present=present,
        )

    # Ports Windows registered but that no USB/BT instance claimed (legacy
    # motherboard ports, or a device whose driver key we could not read).
    for port in registered:
        if port not in by_port:
            by_port[port] = ElmCandidate(port=port, label="Serial port",
                                         source="legacy")

    for cand in by_port.values():
        lowered = cand.label.lower()
        cand.likely = (
            cand.kind in {k for k, _ in KNOWN_USB.values()}
            or cand.kind == "bluetooth"
            or any(word in lowered for word in LIKELY_WORDS)
        )

    out = sorted(by_port.values(), key=lambda c: _com_number(c.port))
    if likely_only:
        out = [c for c in out if c.likely]
    return out


# --- Tier 2: ask the adapter who it is -------------------------------------- #

# Baud rates to try, most common first. 38400 is the ELM327 default (PP 0C),
# 115200 is what several modern adapters ship with, 9600 is the fallback for
# cheap clones that ignore the high-speed setting, 57600 shows up on some
# clones and Bluetooth SPP modules.
# Order matters: this is also the ladder ElmLink.connect() walks, because the
# connect dialog can only pass a port name - the rate is never known up front.
BAUD_CANDIDATES = (38400, 115200, 9600, 57600)

# Substrings that identify an OBD interpreter in an ATI / reset response.
# "ELM 327" covers clones that print a space; STN/OBDLink are the other
# widely used interpreter chips, and an adapter built on one behaves the same.
ID_TOKENS = ("ELM327", "ELM 327", "STN1", "OBDLINK", "OBD II", "OBDII")


def _identify(lines: Iterable[str]) -> str:
    """Return the first line that looks like an adapter identification."""
    for line in lines:
        upper = line.upper()
        if any(token in upper for token in ID_TOKENS):
            return upper.strip()
    return ""


def probe(candidate: ElmCandidate, bauds: tuple[int, ...] = BAUD_CANDIDATES,
          settle: float = 1.0) -> ElmCandidate:
    """Ask one candidate whether it is an ELM327 (Tier 2).

    Tries ``ATZ`` (reset - which prints the ID string) and then ``ATI``, at each
    baud rate in turn. Never raises: failures land in ``candidate.error`` so a
    caller can probe a whole list unattended.
    """
    candidate.probed = True
    candidate.is_elm = False
    candidate.id_string = ""
    candidate.baud = None
    errors: list[str] = []

    for baud in bauds:
        port: Optional[SerialPort] = None
        try:
            port = SerialPort(candidate.port, baud=baud, read_timeout=0.2)
            port.open()
            port.write(b"\r")             # wake / discard a partial line
            time.sleep(0.05)
            port.read_lines(0.1)
            port.write(b"ATZ\r")          # reset; replies with the ID string
            lines = port.read_lines(settle)
            ident = _identify(lines)
            if not ident:
                port.write(b"ATI\r")      # some clones skip the ID on reset
                ident = _identify(lines + port.read_lines(settle / 2))
            if ident:
                candidate.is_elm = True
                candidate.id_string = ident
                candidate.baud = baud
                candidate.error = ""
                return candidate
            errors.append(f"{baud} baud: no ELM327 id")
        except SerialPortError as exc:
            errors.append(f"{baud} baud: {exc}")
        except Exception as exc:           # noqa: BLE001 - probing must not crash
            errors.append(f"{baud} baud: {exc}")
        finally:
            if port is not None:
                port.close()

    candidate.error = "; ".join(errors) if errors else "no response"
    return candidate


def probe_all(candidates: Iterable[ElmCandidate],
              max_workers: int = 4) -> list[ElmCandidate]:
    """Probe several candidates in parallel (each uses its own port handle)."""
    items = list(candidates)
    if not items:
        return []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(probe, items))


def main(argv: Optional[list[str]] = None) -> int:
    """CLI: ``python -m modules.elm_adapter [--all] [--no-probe]``."""
    args = list(sys.argv[1:] if argv is None else argv)
    likely_only = "--all" not in args
    do_probe = "--no-probe" not in args

    candidates = list_candidates(likely_only=likely_only)
    if not candidates:
        print("No serial ports found."
              + ("" if likely_only else " (try without --all filtering)"))
        return 1

    if do_probe:
        probe_all(candidates)

    print(f"{'Port':<7} {'Device':<34} {'Chip':<20} Result")
    print("-" * 92)
    for cand in candidates:
        print(f"{cand.port:<7} {cand.label[:33]:<34} {cand.chip[:19]:<20} "
              f"{cand.status}")
    found = [c for c in candidates if c.is_elm]
    print(f"\n{len(found)} ELM327 adapter(s) identified, "
          f"{len(candidates)} port(s) checked.")
    return 0 if found else 2


if __name__ == "__main__":
    raise SystemExit(main())
