"""OpenTruck - RP1210 adapter-layer regression (run: python check_rp1210.py).

Guards the things that made the 2026-11-10/11 field failures undiagnosable,
plus the single-connection behaviour that is the current CA3 hypothesis:

  * client id vs error code (0..127 are ALL clients - the CA3 assigns 0
    to its first; 128..255 is an ERROR, not a client),
  * the error text carries number + standard name + vendor text,
  * the 32-bit bridge returns vendor text for POSITIVE error codes too,
  * vendor-INI revision parsing decides multi- vs single-client,
  * CombinedSource(exclusive=True) keeps exactly one connection,
  * protocol_options() sweeps what the INI declares, in a useful order,
  * the sweep's buffer classifier reads J1939 / raw CAN correctly.

Everything here is offline: no adapter, no vehicle, no vendor DLL.
"""
import ctypes
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rp1210
import rp1210_bridge
import modules.j1939 as J
from adapter_check import describe, summary
from framesource import CombinedSource, FrameSource

ok = []


def check(name, cond):
    ok.append((name, bool(cond)))


# --- 1. client id vs error code ------------------------------------------ #
# 0 IS a valid client id: the CAT CA3 assigns 0 to its first client (live
# 2026-11-13), and the spec range is 0..127. Nexiq starts at 1, so accepting
# 0 costs nothing there.
check("rc 0 is a client (CA3 first id)", rp1210.is_client_id(0))
check("rc -0 is a client", rp1210.is_client_id(-0))
check("rc 1 is a client", rp1210.is_client_id(1))
check("rc 127 is a client", rp1210.is_client_id(127))
check("rc 128 is an error", not rp1210.is_client_id(128))
check("rc 135 is an error", not rp1210.is_client_id(135))
check("rc 255 is an error", not rp1210.is_client_id(255))
check("rc -1 is an error", not rp1210.is_client_id(-1))

# --- 2. error text ------------------------------------------------------- #
t = rp1210._rc_text(135, "err_code_not_found")
check("text: number first", t.startswith("rc 135"))
check("text: standard name", "ERR_DEVICE_IN_USE" in t)
check("text: vendor text kept", "err_code_not_found" in t)
check("text: name only", rp1210._rc_text(136) == "rc 136 (ERR_INVALID_PROTOCOL)")
check("text: unnamed code", rp1210._rc_text(999, "odd") == "rc 999 (odd)")
check("hint: device in use", "CAT ET" in rp1210.error_hint(135))
check("hint: unknown code", rp1210.error_hint(999) == "")

# --- 3. bridge vendor text for positive error codes ---------------------- #
class _FakeDll:
    """Minimal stand-in: writes the vendor text the way the real DLL does."""
    def RP1210_GetErrorMsg(self, code, buf):
        # `code` arrives as c_short - int(code) would parse the raw bytes.
        text = {135: b"CA3 is busy\x00", 142: b"no adapter\x00"}.get(
            int(code.value), b"?\x00")
        ctypes.memmove(buf, text, len(text))
        return 0


check("bridge: error 135 has text",
      rp1210_bridge._errmsg(_FakeDll(), 135) == "CA3 is busy")
check("bridge: error 142 has text",
      rp1210_bridge._errmsg(_FakeDll(), 142) == "no adapter")
check("bridge: client id has no text",
      rp1210_bridge._errmsg(_FakeDll(), 3) == "")

# --- 4. INI revision -> single client ------------------------------------ #
check("revision: undeclared = single", rp1210._single_client(""))
check("revision: A = single", rp1210._single_client("A"))
check("revision: B = multi", not rp1210._single_client("B"))
check("revision: C = multi", not rp1210._single_client("C"))
check("revision: D = multi", not rp1210._single_client("D"))

# The real CA3.INI on a machine that has one declares no revision at all;
# reproduce its shape here so the parse is what is under test.
CA3_INI = """
[VendorInformation]
Name=Caterpillar
Devices=1
Protocols=1,2,3,4
CANAutoBaud=TRUE

[ProtocolInformation1]
ProtocolString=J1708
Devices=1

[ProtocolInformation2]
ProtocolString=J1939
ProtocolSpeed=250,500,Auto
Devices=1

[ProtocolInformation3]
ProtocolString=CAN
Devices=1

[ProtocolInformation4]
ProtocolString=CAT
ProtocolDescription=Cat Data Link
Devices=1
"""

NEXIQISH_INI = """
[VendorInformation]
Name=Example Multi
RP1210=C
Devices=1,2

[ProtocolInformation1]
ProtocolString=J1939
Devices=1,2

[ProtocolInformation2]
ProtocolString=J1939
ProtocolSpeed=500
Devices=2

[ProtocolInformation3]
ProtocolString=CAN
Devices=1
"""

with tempfile.TemporaryDirectory() as tmp:
    ca3 = os.path.join(tmp, "CA3rp32.INI")
    with open(ca3, "w", encoding="utf-8") as fh:
        fh.write(CA3_INI)
    nexiq = os.path.join(tmp, "NULN3R32.INI")
    with open(nexiq, "w", encoding="utf-8") as fh:
        fh.write(NEXIQISH_INI)

    opts = rp1210.protocol_options(ca3, device_id=1)
    check("CA3 opts: J1939 auto first", opts[0] == "J1939:Baud=Auto")
    check("CA3 opts: explicit 250/500",
          "J1939:Baud=250" in opts and "J1939:Baud=500" in opts)
    check("CA3 opts: raw CAN included", any(o.startswith("CAN") for o in opts))
    check("CA3 opts: CAT data link included", "CAT" in opts)
    check("CA3 opts: J1708 included", "J1708" in opts)
    check("CA3 opts: J1939 before CAN",
          opts.index("J1939:Baud=Auto") < opts.index("CAN:Baud=Auto"))

    nopts = rp1210.protocol_options(nexiq, device_id=1)
    check("Nexiq opts: device-2-only J1939 variant excluded",
          nopts.count("J1939:Baud=500") == 1)

    sections = rp1210._parse_ini(ca3)
    check("CA3 INI: revision undeclared", rp1210._revision_of(sections) == "")
    check("Nexiq INI: revision C",
          rp1210._revision_of(rp1210._parse_ini(nexiq)) == "C")

# --- 5. exclusive CombinedSource ---------------------------------------- #
class _Fake(FrameSource):
    def __init__(self, fail=False):
        self.fail = fail
        self.opened = False
        self.closed = False

    def connect(self):
        if self.fail:
            raise RuntimeError("refused")
        self.opened = True

    def read_frame(self):
        return None

    def write_frame(self, frame):
        pass

    def close(self):
        self.closed = True


a, b = _Fake(fail=True), _Fake()
src = CombinedSource([("j1939", a), ("j1708", b)], exclusive=True)
src.connect()
check("exclusive: J1939 refused -> J1708 opened", b.opened)
check("exclusive: error remembered", "refused" in src.j1939_error)
src.close()
check("exclusive: opened channel closed", b.closed)

a, b = _Fake(), _Fake()
src = CombinedSource([("j1939", a), ("j1708", b)], exclusive=True)
src.connect()
check("exclusive: J1939 wins", a.opened and not b.opened)

a, b = _Fake(), _Fake()
src = CombinedSource([("j1939", a), ("j1708", b)])
src.connect()
check("multi: both channels opened", a.opened and b.opened)

a, b = _Fake(fail=True), _Fake(fail=True)
src = CombinedSource([("j1939", a), ("j1708", b)], exclusive=True)
try:
    src.connect()
    raised = False
except RuntimeError:
    raised = True
check("exclusive: neither open -> failure", raised)

# --- 6. sweep buffer classifier ----------------------------------------- #
# PGN 0xFECA is stored little-endian in the RP1210 buffer: CA FE 00.
j1939_frame = "00000000" + "CAFE00" + "03" + "00" + "FF" + "0102030405060708"
check("describe: J1939 PGN",
      "PGN 0xfeca" in describe(j1939_frame, "J1939:Baud=250"))
can_frame = "00000000" + "01" + "18FECA00" + "0102030405060708"
check("describe: raw CAN id", "0x18FECA00" in describe(can_frame, "CAN:Baud=Auto"))

# --- 5a. claim gating (command 19 is J1939-only) ------------------------ #
check("claim: J1939 auto form claims", rp1210.should_claim("J1939:Baud=Auto", False))
check("claim: plain J1939 claims", rp1210.should_claim("J1939", False))
check("claim: pinned rate claims", rp1210.should_claim("J1939:Baud=250", False))
check("claim: J1708 never claims", not rp1210.should_claim("J1708", False))
check("claim: CAT (CDL) never claims", not rp1210.should_claim("CAT", False))
check("claim: passive never claims", not rp1210.should_claim("J1939:Baud=Auto", True))

# --- 5b. on-demand channels (capture-time raw CAN / CDL) --------------- #
class _Frame(FrameSource):
    """A fake that always has one frame to give (from a fixed list)."""
    def __init__(self, fail=False, payload=None):
        self.fail = fail
        self.payload = payload or ["f1", "f2"]
        self.opened = False
        self.closed = False

    def connect(self):
        if self.fail:
            raise RuntimeError("refused")
        self.opened = True

    def read_frame(self):
        return self.payload.pop(0) if self.payload else None

    def write_frame(self, frame):
        pass

    def close(self):
        self.closed = True


a, b, c = _Frame(payload=["f1"]), _Frame(payload=["f1"]), _Frame(payload=["f1"])
src = CombinedSource([("j1939", a), ("j1708", b)])
src.connect()
check("demand: refused client is not added",
      src.add_source("can2", _Frame(fail=True)) is False)
check("demand: list unchanged after refusal", len(src._sources) == 2)
check("demand: client added mid-session",
      src.add_source("can2", c) is True and c.opened)
seen = [src.read_frame(), src.read_frame(), src.read_frame()]
check("demand: added channel is read",
      any(getattr(t, "protocol", None) == "can2" for t in seen))
src.remove_source("can2")
check("demand: removed channel closed", c.closed)
check("demand: removal drops it from the list", len(src._sources) == 2)
check("demand: unknown name is a no-op", src.remove_source("nope") is None)
src.remove_source("j1939")            # even an original can be dropped
check("demand: original channel removable", len(src._sources) == 1)

x, y, extra = _Frame(), _Frame(), _Frame()
src = CombinedSource([("j1939", x), ("j1708", y)], exclusive=True)
src.connect()
check("demand: exclusive source refuses a second client",
      src.add_source("can2", extra) is False and not extra.opened)

# --- 5c. the Cat Data Link capture channel ------------------------------ #
from framesource import CdlFrame, RawCdlSource

f = CdlFrame(raw=bytes.fromhex("00000000240102FF"))
check("cdl: log line is verbatim", f.to_log_line() == "cdl 00000000240102FF")


class _HexClient:
    """Fake RP1210 client for RawCdlSource (read_raw_hex protocol)."""
    def __init__(self, script, blow_up=False):
        self.script = list(script)
        self.blow_up = blow_up
        self.closed = False

    def connect(self):
        pass

    def read_raw_hex(self):
        if self.blow_up:
            raise RuntimeError("driver exploded")
        return self.script.pop(0) if self.script else None

    def close(self):
        self.closed = True


c = _HexClient(["0102", "ZZ"])
# ("AB" would be valid hex - the odd/garbage string is the real test)
src = RawCdlSource(c)
f = src.read_frame()
check("cdl: bytes pass through verbatim", f.raw == bytes([0x01, 0x02]))
check("cdl: bad hex swallowed", src.read_frame() is None)
check("cdl: read errors never kill the session",
      RawCdlSource(_HexClient([], blow_up=True)).read_frame() is None)
bad = _HexClient([])
src = RawCdlSource(bad)
src.connect()
src.close()
check("cdl: close reaches the client", bad.closed)

# --- 6b. the tool's ONE J1939-81 NAME ------------------------------------ #
# J1939-81 4.1.2: a CA at preferred address 249 must declare the tool
# function in its NAME. Both claim paths (the RP1210 ProtectJ1939Address
# command and the session's own on-wire Address Claimed) must use the SAME
# NAME - two claims for one address with different NAMEs is a self-made
# claim contention, and the old wire NAME declared function 0 ("Engine").
import reader as _reader
name = rp1210._tool_name()
check("NAME: one definition everywhere",
      name == _reader.TOOL_NAME == J.offboard_tool_name())
_dec = J.decode_name(name)
check("NAME: function 129 (off-board service tool)", _dec.function == 0x81)
check("NAME: manufacturer 0 (experimental)", _dec.manufacturer == 0)
check("NAME: not arbitrary-address-capable", _dec.arbitrary_addr_capable is False)
check("NAME: identity stable", _dec.identity == 0x0F9001)
_claim = J.build_address_claim(0xF9, name)
check("claim: PGN 0xEE00 from 0xF9", _claim.pgn == 0xEE00 and _claim.source == 0xF9
      and _claim.destination == 0xFF and _claim.data == name)

# --- 6c. Windows blocking the adapter's USB driver ---------------------- #
# Live case 2026-11-13: Windows 11 Memory Integrity (HVCI) refuses the CAT
# CA3's 2016 ftdibus.sys (CodeIntegrity event 3111) -> Device Manager code
# 39 -> driver reports rc 142 "hardware not responding". The connect hint
# must name the setting, not blame the cable. Fed canned PowerShell output
# so the check stays offline.
_real_probe = rp1210._usb_probe_output


def _canned_probe(text):
    rp1210._usb_probe_output = lambda: text


def _restore_probe():
    rp1210._usb_probe_output = _real_probe


_canned_probe("CAT Comm Adapter 3|VehicleDataLink|39|0xC000007B\n")
findings = rp1210.usb_driver_problems()
check("usb: CA3 block detected", len(findings) == 1)
check("usb: names the device", "CAT Comm Adapter 3" in findings[0])
check("usb: names the fix (Memory integrity)",
      "Memory integrity" in findings[0] and "reboot" in findings[0])
check("usb: names the code", "code 39" in findings[0])
_canned_probe("USB-Link 3|USB|28|0x00000000\n")
check("usb: unrelated codes ignored",
      rp1210.usb_driver_problems() == [])
_canned_probe("Broken Printer|Printer|39|0xC000007B\n")
check("usb: irrelevant classes ignored",
      rp1210.usb_driver_problems() == [])
_canned_probe("vLinker FS COM3|Ports|52|0xC0000428\n")
check("usb: code 52 (unsigned) explained",
      len(rp1210.usb_driver_problems()) == 1
      and "unsigned" in rp1210.usb_driver_problems()[0])
_canned_probe("garbage output from a dead shell\n")
check("usb: unparseable output ignored",
      rp1210.usb_driver_problems() == [])


def _probe_raises():
    raise OSError("powershell not found")


rp1210._usb_probe_output = _probe_raises
check("usb: probe failure never raises", rp1210.usb_driver_problems() == [])
_restore_probe()

# --- 7. summary text ---------------------------------------------------- #
rep = {
    "adapter": rp1210.AdapterInfo("CA3rp32", "Caterpillar", "", "J1939", 1, "J1708"),
    "results": [
        {"protocol": "J1939:Baud=250", "opened": True, "count": 12,
         "used": "J1939:Baud=250", "ms": 90, "error": "", "labels": ["PGN"]},
        {"protocol": "CAT", "opened": False, "count": 0, "used": "", "ms": 5,
         "error": "rc 136 (ERR_INVALID_PROTOCOL)", "labels": []},
    ],
    "path": r"C:\tmp\adapter_check.log",
}
text = summary(rep)
check("summary: adapter named", "Caterpillar" in text)
check("summary: data verdict", "Vehicle data arrived" in text)
check("summary: report path", "adapter_check.log" in text)

# --- report -------------------------------------------------------------- #
fails = [n for n, good in ok if not good]
print("=" * 68)
print("RP1210 adapter-layer regression")
print("=" * 68)
for name, good in ok:
    print(("PASS  " if good else "FAIL  ") + name)
print("-" * 68)
print("%d/%d PASS" % (len(ok) - len(fails), len(ok)))
if fails:
    print("FAILED: " + ", ".join(fails))
sys.exit(1 if fails else 0)
