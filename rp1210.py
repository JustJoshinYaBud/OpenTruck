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

import connectlog
from framesource import FrameSource
from modules.j1939 import Frame, offboard_tool_name
from modules.j1708 import from_rp1210_buffer, J1708Message
from modules.cdl import from_rp1210_buffer as cdl_from_rp1210_buffer

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
CMD_RELEASE_J1939_ADDR   = 31   # gives the claimed address back on disconnect

# RP1210 standard return codes 128-159 (public TMC table - the same numbers in
# every RP1210B/C/D document). A driver's own text is ALWAYS logged next to
# the name, because vendors reuse numbers; the name is what makes a field
# report actionable without the vendor's table ("rc 135" alone says nothing,
# "rc 135 ERR_DEVICE_IN_USE" says another program has the adapter).
RP1210_ERRORS = {
    128: "ERR_DLL_NOT_INITIALIZED",
    129: "ERR_INVALID_CLIENT_ID",
    130: "ERR_CLIENT_ALREADY_CONNECTED",
    131: "ERR_CLIENT_AREA_FULL",
    132: "ERR_FREE_MEMORY",
    133: "ERR_NOT_ENOUGH_MEMORY",
    134: "ERR_INVALID_DEVICE",
    135: "ERR_DEVICE_IN_USE",
    136: "ERR_INVALID_PROTOCOL",
    137: "ERR_TX_QUEUE_FULL",
    138: "ERR_TX_QUEUE_CORRUPT",
    139: "ERR_RX_QUEUE_FULL",
    140: "ERR_RX_QUEUE_CORRUPT",
    141: "ERR_MESSAGE_TOO_LONG",
    142: "ERR_HARDWARE_NOT_RESPONDING",
    143: "ERR_COMMAND_NOT_SUPPORTED",
    144: "ERR_INVALID_COMMAND",
    145: "ERR_TXMESSAGE_STATUS",
    146: "ERR_ADDRESS_CLAIM_FAILED",
    147: "ERR_CANNOT_SET_PRIORITY",
    148: "ERR_CLIENT_DISCONNECTED",
    149: "ERR_CONNECT_NOT_ALLOWED",
    150: "ERR_CHANGE_MODE_FAILED",
    151: "ERR_BUS_OFF",
    152: "ERR_COULD_NOT_TX_ADDRESS_CLAIMED",
    153: "ERR_ADDRESS_LOST",
    154: "ERR_CODE_NOT_FOUND",
    155: "ERR_BLOCK_NOT_ALLOWED",
    156: "ERR_BLOCK_TIMEOUT",
    157: "ERR_INVALID_BLOCK_SIZE",
}

ERR_CLIENT_ALREADY_CONNECTED = 130
ERR_CLIENT_AREA_FULL = 131
ERR_INVALID_DEVICE = 134
ERR_DEVICE_IN_USE = 135
ERR_INVALID_PROTOCOL = 136
ERR_HARDWARE_NOT_RESPONDING = 142
ERR_ADDRESS_CLAIM_FAILED = 146
ERR_CONNECT_NOT_ALLOWED = 149


def is_client_id(rc: int) -> bool:
    """True when an RP1210_ClientConnect return value is a usable client id.

    The spec splits the range: a CLIENT ID is 0..127 (INCLUDING 0), an ERROR
    CODE is 128..255 (some drivers return negative codes instead). Treating
    128+ as success - the old behaviour - hands an error code to every later
    call, where it surfaces as the meaningless `rc 129 ERR_INVALID_CLIENT_ID`
    and the actual reason (`rc 135 ERR_DEVICE_IN_USE`, say) is lost.

    0 is a REAL client id, not an error: the CAT CA3 driver assigns 0 to its
    FIRST client (live 2026-11-13 - the morning connect logged `rc 0`, then a
    second attempt got `client 1`, i.e. driver-side ids are 0,1,...). Nexiq
    starts at 1 and never returns 0, so accepting 0 changes nothing there.
    Rejecting 0 made the CA3's Cat Data Link capture fail outright with the
    absurd "ClientConnect failed for CAT: rc 0" and leaked a live client
    every time the ladder retried.
    """
    return 0 <= int(rc) < 128


def should_claim(protocol: str, passive: bool) -> bool:
    """True when this client must run the J1939 address-claim command.

    Command 19 (ProtectJ1939Address) is a J1939-layer command. Sending it on a
    J1708 or CAT (Cat Data Link) client asks the driver for a service the
    protocol does not have: some drivers answer "command not supported",
    others answer something stranger, and the log gains a line that looks
    like a fault. Claim only where the protocol is J1939.
    """
    return (not passive) and protocol.upper().startswith("J1939")


def error_hint(rc: int) -> str:
    """One actionable sentence for a connection error code ("" if unknown)."""
    rc = int(rc)
    if rc in (ERR_DEVICE_IN_USE, ERR_CLIENT_ALREADY_CONNECTED,
              ERR_CLIENT_AREA_FULL, ERR_CONNECT_NOT_ALLOWED):
        return ("The adapter is already claimed by another program or by a "
                "previous session. Close CAT ET / other diagnostics software, "
                "unplug the adapter for a few seconds and plug it back in.")
    if rc == ERR_INVALID_PROTOCOL:
        return ("The driver rejected that protocol/baud string. That is a "
                "driver/rate mismatch, not a wiring fault.")
    if rc == ERR_HARDWARE_NOT_RESPONDING:
        return ("The driver cannot see the adapter. Re-seat the USB cable, "
                "use a direct port (no hub) and try again.")
    if rc == ERR_INVALID_DEVICE:
        return ("The driver has no device with that ID - the vendor INI may "
                "be left over from an uninstalled adapter.")
    if rc == ERR_ADDRESS_CLAIM_FAILED:
        return ("The adapter refused to claim a J1939 address; another tool "
                "may hold it. Receive-only data can still arrive.")
    return ""


# Device Manager problem codes (cfgmgr32 CM_PROB_*) that mean "Windows itself
# refused the adapter's driver". Encountered live on 2026-11-13: Windows 11
# Memory Integrity (HVCI) blocks the CAT Comm Adapter 3's 2016-era FTDI USB
# driver (ftdibus.sys, CodeIntegrity event 3111 "not compatible with
# hypervisor enforcement") on EVERY clean-install Windows 11 24H2+ machine -
# the driver then reports rc 142 "hardware not responding" and no cable
# re-seat in the world will fix it. CAT ships no HVCI-compatible driver, so
# the ONLY fix is the Windows setting - which is why the hint below is the
# most valuable sentence this file can produce.
_CM_PROB_DRIVER_FAILED_LOAD = 39   # "cannot load the device driver"
_CM_PROB_DRIVER_SIGNATURE = 52    # "driver signature... cannot be verified"

# Classes an RP1210 adapter's USB device shows up under. Anything else with a
# broken driver (a printer, say) must not hijack a connect-failure message.
_USB_RELEVANT_CLASSES = {"usb", "ports", "vehicledatalink",
                         "vehicledata link", "modem", "net"}


def _usb_probe_output() -> str:
    """One `name|class|problemcode|status` line per device Windows has flagged.

    Runs a tiny read-only PowerShell query (Get-PnpDevice is present on every
    Windows 8.1+/11 box). Kept in its own function so the offline checks can
    feed it canned output without touching subprocess.
    """
    # Win32_PnPEntity is used for the numeric problem code on purpose:
    # on newer Windows builds Get-PnpDevice hands back the code as an ENUM
    # NAME string ("CM_PROB_DRIVER_FAILED_LOAD"), which no integer parse
    # survives. Get-PnpDeviceProperty is still needed for the NTSTATUS -
    # Win32_PnPEntity does not carry it.
    ps = (
        "[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
        "Get-CimInstance Win32_PnPEntity | "
        "Where-Object { $_.ConfigManagerErrorCode -ne 0 } | "
        "ForEach-Object { "
        "$c = $_.ConfigManagerErrorCode; "
        "$s = (Get-PnpDeviceProperty -InstanceId $_.PNPDeviceID "
        "-KeyName DEVPKEY_Device_ProblemStatus).Data; "
        '"{0}|{1}|{2}|0x{3:X8}" -f $_.Name, $_.PNPClass, '
        " $c, [uint32]$s }"
    )
    out = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=20)
    return out.stdout or ""


def usb_driver_problems() -> list[str]:
    """Plain-language findings when Windows itself blocks the adapter's driver.

    Returns [] on any surprise - a diagnostics probe must never stand in the
    way of reporting the real connect error.
    """
    if sys.platform != "win32":
        return []
    try:
        raw = _usb_probe_output()
    except Exception:
        return []
    findings: list[str] = []
    for line in raw.splitlines():
        parts = line.split("|")
        if len(parts) != 4:
            continue
        name, cls, code_s, status = (p.strip() for p in parts)
        try:
            code = int(code_s)
        except ValueError:
            continue
        if not name or cls.lower() not in _USB_RELEVANT_CLASSES:
            continue
        if code == _CM_PROB_DRIVER_FAILED_LOAD:
            findings.append(
                "Windows is refusing to load the driver for \"%s\" (Device "
                "Manager code 39, status %s). On Windows 11 the usual cause "
                "is Memory Integrity blocking an old driver: Settings > "
                "Privacy & security > Windows Security > Device security > "
                "Core isolation details > turn Memory integrity OFF, then "
                "reboot and reconnect."
                % (name, status))
        elif code == _CM_PROB_DRIVER_SIGNATURE:
            findings.append(
                "Windows blocked the driver for \"%s\" as unsigned (Device "
                "Manager code 52) - reinstall it from the vendor."
                % name)
    return findings


# Source address the tool presents on the J1939 bus ("off-board diagnostics tool #1").
TOOL_SOURCE_ADDR = 0xF9


def _tool_name() -> bytes:
    """8-byte J1939 NAME (little-endian) identifying our tool on the bus.

    The ONE canonical NAME (modules.j1939.offboard_tool_name) - identical to
    the NAME the session broadcasts on the wire. The old hand-built NAME here
    differed from it (identity 0x001234, manufacturer code 192 = Floscan, a
    real vendor, function 128), so a single connect put TWO different NAMEs
    for the same address 0xF9 on the bus: one from this ProtectJ1939Address
    command and one from the session's own Address Claimed frame. J1939-81
    4.1.2 requires the NAME at preferred address 249 to declare the tool
    function, and two claims for one address with different NAMEs is a claim
    contention of our own making.
    """
    return offboard_tool_name()


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
    revision: str = ""   # INI `RP1210=` value: "A".."D", "" = not declared
    single_client: bool = False   # one connection at a time (see _single_client())
    ini_path: str = ""   # the vendor INI this came from ("" = none found)


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


def _ini_value(sections: dict[str, dict[str, str]], section: str,
               key: str) -> str:
    """Case-insensitive INI lookup (vendor INIs are not consistent)."""
    for k, v in sections.get(section, {}).items():
        if k.strip().upper() == key.upper():
            return v.strip()
    return ""


def _revision_of(sections: dict[str, dict[str, str]]) -> str:
    """The vendor's declared RP1210 revision ("A".."D"), "" when absent."""
    return _ini_value(sections, "VendorInformation", "RP1210").upper()


def _single_client(revision: str) -> bool:
    """Should this driver get ONE connection at a time?

    OpenTruck normally opens three clients on one adapter (J1939 for requests,
    J1708 to see J1587 modules, raw CAN to capture the wire). That is fine on
    an RP1210B+ driver that supports several simultaneous clients - the Nexiq
    USB-Link 3 declares RP1210=D and 5 CAN channels.

    Some drivers do not. The CAT Comm Adapter 3's INI declares no `RP1210=`
    revision at all and no extra channels; RP1210A left multi-client support
    ambiguous (an adapter need not serve more than one application), and one
    CA3 hardware session is a single data link. On such a driver the extra
    ClientConnect calls can take the session away from the J1939 client that
    the app actually needs, and the symptom is exactly the field report: the
    adapter connects and then nothing arrives.

    UPDATE (live 2026-11-13): the CA3 disproved the guess - it served THREE
    simultaneous clients (J1939 + J1708 + CAT), all delivering data on one
    adapter. app._rp1210_source() therefore overrides this to multi-client
    for CAT-family adapters; this function stays conservative for unknown
    no-revision drivers (and the 2026-11-10 field failure it was built for
    may in fact have been the J1939-81 NAME bug fixed the same week).

    So: a driver that does not declare B/C/D gets one connection at a time,
    and a J1708-only vehicle still works because J1708 is then the fallback
    after J1939 is refused (see CombinedSource(exclusive=True)).
    """
    return revision not in ("B", "C", "D")


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


def _protocol_ladder(protocol: str) -> list[str]:
    """Protocol strings to try, in order, when ``ClientConnect`` is refused.

    Two real-world failures this covers:

    * **Vendor string pickiness.** We append ``:Baud=Auto`` to the INI's
      ``J1939`` because several drivers otherwise lock to one fixed rate - but
      not every DLL accepts the parameter syntax (CAT's CA3 among them) and
      answers ``ERR_INVALID_PROTOCOL``. The bare string is the INI's own.
    * **Auto-baud cannot lock a quiet/slow bus.** Auto-baud needs traffic to
      sync on; a 250 k engine bus idling at key-on can leave it unsynced, so
      the explicit rates are tried last (250 k for pre-2010 heavy duty, 500 k
      for later vehicles).

    Only J1939 gets a ladder: J1708 and the raw-CAN channels name their own
    protocol and have no baud parameter to vary.
    """
    base = protocol.strip()
    if ":Baud=" in base and not base.upper().endswith("BAUD=AUTO"):
        # Already pinned to an explicit rate (the silent-bus retry path).
        # Falling back to the bare string would re-enable the adapter's
        # auto-baud - exactly the mode that failed to sync - and silently
        # undo the pinning this attempt exists to try.
        return [base]
    plain = base.split(":", 1)[0] or "J1939"
    out: list[str] = []
    # 1 Mbit/s is nominally legal on J1939 and some off-highway machines run it.
    # An adapter that does not accept ':Baud=1000' simply refuses the connect
    # and the ladder moves on, so it costs one line in the log and nothing
    # else. Refusal ladder only - the watchdog retries each cost the user 4 s
    # before the OBD-II fallback (see app._arm_baud_retries).
    for candidate in (base, plain, plain + ":Baud=250", plain + ":Baud=500",
                      plain + ":Baud=1000"):
        if candidate and candidate not in out:
            out.append(candidate)
    return out


def _rc_text(rc: int, vendor_text: str = "") -> str:
    """'rc 135 (ERR_DEVICE_IN_USE: driver text)' - number, name, then text.

    Three layers, because a field report needs all of them:
      * the number, because it is the only thing that is stable across drivers;
      * the standard RP1210 name, because the number alone is unreadable and
        some drivers answer with the literal placeholder "err_code_not_found"
        for any code outside their own table (Nexiq does exactly this);
      * the driver's own text, which is the only vendor-specific detail we get.
    """
    name = RP1210_ERRORS.get(int(rc), "")
    text = (vendor_text or "").strip()
    if name and text and text.upper() != name:
        detail = f"{name}: {text}"
    else:
        detail = name or text
    return f"rc {rc} ({detail})" if detail else f"rc {rc}"


def _j1708_protocol(sections: dict[str, dict[str, str]]) -> str:
    """Find this vendor's J1708 protocol string, defaulting to "J1708"."""
    for name, opts in sections.items():
        if not name.lower().startswith("protocolinformation"):
            continue
        proto = opts.get("ProtocolString", "")
        if proto.upper() == "J1708" or proto.upper().startswith("J1708"):
            return proto
    return "J1708"


def _device_list(opts: dict[str, str]) -> list[int]:
    """The `Devices=` list of a protocol section (empty = "not declared")."""
    out: list[int] = []
    for part in opts.get("Devices", "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            continue
    return out


# Protocols worth sweeping on a vehicle. Everything else in a vendor INI
# (J1850, KWP2000, Hummer ALDL, ...) is light-duty legacy and cannot carry
# J1939/J1587, so it is only tried with all_protocols=True.
VEHICLE_PROTOCOLS = ("J1939", "CAN", "CAT", "J1708", "ISO15765")


def protocol_options(ini_path: str, device_id: int = 1,
                     all_protocols: bool = False) -> list[str]:
    """Every useful protocol string this vendor INI offers for ``device_id``.

    J1939 is expanded into the strings worth trying on a vehicle, in the order
    that resolves a real fault fastest: the driver's auto-detect form first,
    then the two classic rates explicitly, then 1 Mbit/s. A driver can ACCEPT
    ``J1939:Baud=Auto`` and still never sync on a quiet bus, so "connect" and
    "data" have to be measured separately per string - that is the whole point
    of the sweep.

    Order is the sweep order: J1939, raw CAN, CAT Data Link, J1708, ISO15765.
    """
    sections = _parse_ini(ini_path) if ini_path else {}
    declared: list[str] = []
    for name, opts in sections.items():
        if not name.lower().startswith("protocolinformation"):
            continue
        proto = opts.get("ProtocolString", "").strip()
        if not proto:
            continue
        devices = _device_list(opts)
        if devices and device_id not in devices:
            # The INI says this device does not speak this protocol; offering
            # the pair only produces a useless ClientConnect failure.
            continue
        declared.append(proto)
    if not declared:                       # no INI: the common defaults
        declared = ["J1939", "CAN", "J1708"]

    def base(p: str) -> str:
        return p.split(":", 1)[0].strip().upper()

    out: list[str] = []
    for wanted in VEHICLE_PROTOCOLS:
        matches = [p for p in declared if base(p) == wanted]
        if not matches:
            continue
        if wanted == "J1939" or wanted == "CAN":
            for p in matches:
                for variant in (p if ":" in p else p + ":Baud=Auto",
                                p.split(":", 1)[0] + ":Baud=250",
                                p.split(":", 1)[0] + ":Baud=500"):
                    if variant not in out:
                        out.append(variant)
        else:
            for p in matches:
                if p not in out:
                    out.append(p)
    if all_protocols:
        for p in declared:
            if p not in out:
                out.append(p)
    return out


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
        revision = ""
        ini = os.path.join(r"C:\Windows", code + ".INI")
        if not os.path.exists(ini):
            # Some installers name the INI exactly like the DLL, some don't.
            ini = os.path.join(r"C:\Windows", code + ".ini")
        if os.path.exists(ini):
            sections = _parse_ini(ini)
            name = _ini_value(sections, "VendorInformation", "Name") or code
            proto, device_id = _j1939_protocol(sections)
            j1708 = _j1708_protocol(sections)
            revision = _revision_of(sections)
        else:
            ini = ""
        matching, other = _find_dlls(code)
        if matching is None and other is None:
            continue                      # no DLL -> not a real adapter; skip
        single = _single_client(revision)
        connectlog.write(
            "adapter %s (%s): dll=%s bridge=%s protocol=%s device=%s "
            "rp1210=%s clients=%s"
            % (code, name, matching or "-", other or "-", proto, device_id,
               revision or "(not declared)", "1 at a time" if single else "multi"))
        if matching is not None:
            out.append(AdapterInfo(code, name, matching, proto, device_id, j1708,
                                   revision=revision, single_client=single,
                                   ini_path=ini))
        else:
            out.append(AdapterInfo(
                code, name, "", proto, device_id, j1708, bridge_dll=other or "",
                revision=revision, single_client=single, ini_path=ini))
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
                 device_id: int = DEVICE_ID, passive: bool = False,
                 ladder: bool = True) -> None:
        self._protocol = protocol
        self._device_id = device_id
        # ladder=False: try EXACTLY the protocol string given, no refusal
        # fallbacks. The adapter sweep enumerates those strings itself, so a
        # step must mean one ClientConnect with one string.
        self._ladder = ladder
        self._is_j1708 = protocol.upper().startswith("J1708")
        # The CAT-family 'CAT' protocol is the Cat Data Link (modules/cdl.py);
        # its receive buffers are NOT J1939 frames.
        self._is_cdl = protocol.split(":", 1)[0].strip().upper() == "CAT"
        self._passive = passive
        self._tx_blocked = False   # address claim refused: receive-only
        self._claimed = False      # our J1939 address was accepted by the driver
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
        return _rc_text(code, buf.raw.split(b"\x00")[0].decode("ascii", "ignore"))

    # -- FrameSource API -------------------------------------------------- #
    def connect(self) -> None:
        attempts = (_protocol_ladder(self._protocol)
                    if self._ladder and self._protocol.upper().startswith("J1939")
                    else [self._protocol])
        client = 0
        first_error = ""
        first_rc = 0
        for protocol in attempts:
            client = int(self._dll.RP1210_ClientConnect(
                None, self._device_id, protocol.encode("ascii"),
                TX_BUFFER, RX_BUFFER, 0,   # 0 = not ISO15765
            ))
            if is_client_id(client):
                connectlog.write(
                    "ClientConnect %s device=%s -> client %s"
                    % (protocol, self._device_id, client))
                self._protocol = protocol      # the string that actually worked
                break
            # 128..255 is an ERROR CODE, not a client id (see is_client_id).
            connectlog.write(
                "ClientConnect %s device=%s -> %s"
                % (protocol, self._device_id, self._error_text(client)))
            if not first_error:
                # The FIRST attempt's error is the representative one: the
                # later rungs are fallbacks, and the last (1000 k) is the
                # least meaningful to a user. Every rung is already logged.
                first_error = self._error_text(client)
                first_rc = client
        if not is_client_id(client):
            hint = error_hint(first_rc)
            if first_rc == ERR_HARDWARE_NOT_RESPONDING:
                # "the driver cannot see the adapter" is often Windows itself
                # refusing to load the adapter's USB driver (Memory Integrity
                # blocks the 2016 CAT CA3 driver on every clean-install
                # Windows 11 box). Say so instead of blaming the cable.
                for finding in usb_driver_problems():
                    hint = (hint + " " + finding).strip()
                    connectlog.write("USB " + finding)
            text = (f"ClientConnect failed for {', '.join(attempts)}: "
                    f"{first_error}")
            if hint:
                text += f"\n\n{hint}"
            connectlog.write("FAIL " + text.replace("\n\n", " - "))
            raise RP1210Error(text)
        self._client_id = client

        # RP1210 adapters pass NO messages until "Set All Filters to Pass"
        # (command 3) is issued - and this is required for J1708 as well as
        # J1939. Skipping it for J1708 makes every read return "no message" (the
        # bus looks silent even though it is busy). A negative return means the
        # command was rejected (e.g. no hardware on the bus), even though
        # ClientConnect returned a positive client id.
        rc = self.send_command(CMD_SET_ALL_FILTERS_PASS)
        connectlog.write("SetAllFiltersToPass -> rc %s" % int(rc))
        if rc < 0:
            text = f"Filter command failed: {self._error_text(rc)}"
            connectlog.write("FAIL " + text)
            self.close()
            raise RP1210Error(text)
        if should_claim(self._protocol, self._passive):
            # J1939 only: claim a source address before the adapter will transmit
            # (e.g. a Request message) on the bus. Passive listeners skip the
            # claim (claiming our usual 0xF9 would collide with the other tool's
            # off-board address); with filters open they can still RECEIVE.
            claim = bytes([TOOL_SOURCE_ADDR]) + _tool_name() + bytes([0x00])  # 0x00 = block until claimed
            rc = self.send_command(CMD_PROTECT_J1939_ADDR, claim)
            connectlog.write("ProtectJ1939Address 0x%02X -> rc %s"
                             % (TOOL_SOURCE_ADDR, int(rc)))
            if rc < 0:
                # NOT fatal. The claim only gates TRANSMISSION (requests, DM
                # discovery); with filters already passing, broadcasts still
                # arrive, and broadcasts are most of what this app shows. A
                # refused claim kills the whole channel otherwise - which is
                # how a truck that reads fine can report "no adapter".
                self._tx_blocked = True
                connectlog.write(
                    "Address claim refused (%s) - continuing RECEIVE-ONLY"
                    % self._error_text(rc))
            else:
                self._claimed = True

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
        if self._is_cdl:
            return cdl_from_rp1210_buffer(buf.raw, n)
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
        if self._client_id is None or self._tx_blocked:
            # _tx_blocked: the address claim was refused, so the adapter will
            # not transmit. Staying silent beats raising on every request.
            return
        if self._is_j1708:
            # J1587 requests / DTC-clear are not wired in v1 (see TODO).
            return
        if self._is_cdl:
            # CDL TX goes through send_raw_message() (raw [src][dst][IID]
            # [data], wire-verified framing; the app reaches it
            # via CombinedSource.send_cdl). This J1939-shaped Frame API must
            # never frame onto the Cat Data Link.
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
        if self._client_id is None:
            return
        if self._claimed:
            # Hand the source address back before disconnecting. A driver that
            # keeps a stale claim makes the NEXT connect (or another tool)
            # fail with ERR_ADDRESS_CLAIM_FAILED - a classic "worked once,
            # never again until replug" symptom on J1939 adapters.
            try:
                self.send_command(CMD_RELEASE_J1939_ADDR,
                                  bytes([TOOL_SOURCE_ADDR]))
            except Exception:                       # noqa: BLE001
                pass
            self._claimed = False
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
                 bridge_command: Optional[list[str]] = None,
                 ladder: bool = True) -> None:
        self._dll_path = dll_path
        self._protocol = protocol
        self._device_id = device_id
        self._ladder = ladder          # see RP1210Source
        self._is_j1708 = protocol.upper().startswith("J1708")
        self._is_cdl = protocol.split(":", 1)[0].strip().upper() == "CAT"
        self._passive = passive   # listen-only: filters open, no address claim
        self._tx_blocked = False  # address claim refused: receive-only
        self._claimed = False     # our J1939 address was accepted by the driver
        self._bridge_command = bridge_command if bridge_command is not None \
            else _bridge_command()
        self._proc = None
        self._lock = threading.Lock()
        self._last_msg = ""       # vendor error text from the last bridge reply

    def _spawn(self) -> None:
        if not self._bridge_command:
            raise RP1210Error(
                "This adapter's driver is 32-bit and needs the OpenTruck 32-bit "
                "bridge, but no bridge executable was found. Build the bridge "
                "with a 32-bit Python (see build.bat) and re-run.")
        try:
            self._proc = subprocess.Popen(
                self._bridge_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                bufsize=1, text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as exc:
            # Windows application control (Smart App Control / Device Guard)
            # refuses unsigned binaries at CreateProcess with "blocked by
            # your organization's policy" (WinError 1260); an antivirus
            # quarantine raises something similar. Without this the user sees
            # a bare OSError and blames the adapter.
            raise RP1210Error(
                "Could not start the 32-bit adapter helper "
                f"({self._bridge_command[0]}): {exc}. Windows Smart App "
                "Control or antivirus may be blocking it - which makes every "
                "32-bit driver adapter fail while CAT ET / JPRO keep working.")

    def _call(self, req: dict) -> dict:
        if self._proc is None:
            self._spawn()
        with self._lock:
            self._proc.stdin.write(json.dumps(req) + "\n")
            self._proc.stdin.flush()
            line = self._proc.stdout.readline()
        if not line:
            # The helper process died or never answered. A missing helper and
            # a BLOCKED helper are the two field-real causes: unsigned freshly
            # built binaries can be refused outright by Windows application
            # control (Smart App Control / Device Guard - the same "blocked by
            # your organization's policy" dialog), and an antivirus quarantine
            # looks identical from here. Name both, or this reads as our bug.
            raise RP1210Error(
                "The 32-bit adapter helper (OpenTruckBridge32.exe) exited "
                "without answering. Make sure OpenTruckBridge32.exe exists "
                "next to OpenTruck.exe and is not blocked by Windows Smart "
                "App Control / antivirus - a blocked or quarantined helper "
                "makes every 32-bit driver adapter fail while other tools "
                "(CAT ET, JPRO) keep working.")
        resp = json.loads(line)
        if resp.get("msg"):
            self._last_msg = str(resp["msg"])
        return resp

    def connect(self) -> None:
        self._spawn()
        attempts = (_protocol_ladder(self._protocol)
                    if self._ladder and self._protocol.upper().startswith("J1939")
                    else [self._protocol])
        resp: dict = {}
        rc = 0
        first_error = ""
        first_rc = 0
        for protocol in attempts:
            resp = self._call({
                "op": "client_connect", "dll": self._dll_path,
                "device_id": self._device_id, "protocol": protocol,
            })
            rc = int(resp.get("rc", 0))
            if is_client_id(rc):
                connectlog.write(
                    "BRIDGED ClientConnect %s device=%s -> client %s"
                    % (protocol, self._device_id, rc))
                self._protocol = protocol      # the string that actually worked
                break
            # 128..255 is an error code, not a client id (see is_client_id).
            connectlog.write(
                "BRIDGED ClientConnect %s device=%s -> %s"
                % (protocol, self._device_id,
                   _rc_text(rc, resp.get("msg", ""))))
            if not first_error:
                # See RP1210Source.connect(): the first rung's error is the
                # representative one; each rung is already logged above.
                first_error = _rc_text(rc, resp.get("error") or resp.get("msg", ""))
                first_rc = rc
        if not is_client_id(rc):
            text = ("ClientConnect failed for %s: %s"
                    % (", ".join(attempts), first_error))
            hint = error_hint(first_rc)
            if first_rc == ERR_HARDWARE_NOT_RESPONDING:
                # See RP1210Source.connect(): a bridged driver equally cannot
                # see hardware whose USB driver Windows refused to load.
                for finding in usb_driver_problems():
                    hint = (hint + " " + finding).strip()
                    connectlog.write("USB " + finding)
            if hint:
                text += f"\n\n{hint}"
            connectlog.write("FAIL " + text.replace("\n\n", " - "))
            self.close()
            raise RP1210Error(text)
        # Filters must be set for EVERY protocol (J1708 and CAT included):
        # adapters default to discarding everything, so a client that forgets
        # this reads nothing from a healthy link.
        rc = self.send_command(CMD_SET_ALL_FILTERS_PASS)
        connectlog.write("BRIDGED SetAllFiltersToPass -> rc %s" % rc)
        if rc < 0:
            text = f"Filter command failed: {_rc_text(rc, self._last_msg)}"
            connectlog.write("FAIL " + text)
            self.close()
            raise RP1210Error(text)
        if should_claim(self._protocol, self._passive):
            claim = bytes([TOOL_SOURCE_ADDR]) + _tool_name() + bytes([0x00])
            rc = self.send_command(CMD_PROTECT_J1939_ADDR, claim)
            connectlog.write("BRIDGED ProtectJ1939Address 0x%02X -> rc %s"
                             % (TOOL_SOURCE_ADDR, rc))
            if rc < 0:
                # Receive-only fallback: see RP1210Source.connect().
                self._tx_blocked = True
                connectlog.write(
                    "Address claim refused (%s) - continuing RECEIVE-ONLY"
                    % _rc_text(rc, self._last_msg))
            else:
                self._claimed = True

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
        if self._is_cdl:
            return cdl_from_rp1210_buffer(raw, n)
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
        if self._is_cdl:
            return   # CDL TX uses send_raw_message (see RP1210Source.write_frame)
        if self._tx_blocked:
            return   # claim refused: the adapter will not transmit
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
            if self._claimed:
                # Release the J1939 address first (see RP1210Source.close).
                try:
                    self._call({"op": "send_command",
                                "number": CMD_RELEASE_J1939_ADDR,
                                "data": bytes([TOOL_SOURCE_ADDR]).hex()})
                except Exception:                   # noqa: BLE001
                    pass
                self._claimed = False
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
