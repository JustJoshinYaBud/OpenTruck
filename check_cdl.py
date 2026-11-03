"""OpenTruck - Cat Data Link (CDL) decode regression (run: python check_cdl.py).

Guards the CDL transport that was built FROM a live capture (2026-11-13, aux
engine via the CA3's 'CAT' protocol):

  * the RP1210 'CAT' buffer layout [ts(4)][MID][dest][IID][data...],
  * the session behaviour (MID-keyed modules, decoded AND raw frames),
  * the merged-module key space (CDL_KEY_BASE) staying clear of J1939
    addresses and J1708 MIDs,
  * the CTPL -> "CAT" name fix (CAT engines broadcast the CI make "CTPL").

Everything here is offline: the byte strings below are from the real capture.
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import modules.cdl as cdl
from lookup.oem_cat import CAT_CDL_MID
import reader
from framesource import LoggingSource, TaggedFrame

ok = []


def check(name, cond):
    ok.append((name, bool(cond)))


# --- 1. buffer decode ---------------------------------------------------- #
# Real buffers from the 2026-11-13 capture (4-byte receive ts + message).
b_heartbeat = bytes.fromhex("000DCDA92400F33100")   # MID 36, IID 0xF3
b_param = bytes.fromhex("000DD4A32400FA1C055FEE5A3ED5")  # MID 36, IID 0xFA
m = cdl.from_rp1210_buffer(b_heartbeat, len(b_heartbeat))
check("heartbeat decodes", m is not None)
check("MID 36 (Engine Control #1)", m.mid == 36 and m.dest == 0x00)
check("IID 0xF3", m.iid == 0xF3)
check("data kept verbatim", m.data == bytes.fromhex("3100"))
check("raw keeps the message, drops the ts prefix",
      m.raw == bytes.fromhex("2400F33100"))

m2 = cdl.from_rp1210_buffer(b_param, len(b_param))
check("param broadcast decodes",
      m2 is not None and m2.mid == 36 and m2.iid == 0xFA
      and m2.data == bytes.fromhex("1C055FEE5A3ED5"))

# The capture's third group (IID 0xFC, twice, identical).
m3 = cdl.from_rp1210_buffer(bytes.fromhex("000E1CE12400FC5D8C9B9B00"),
                             len(bytes.fromhex("000E1CE12400FC5D8C9B9B00")))
check("IID 0xFC decodes", m3 is not None and m3.iid == 0xFC
      and m3.data == bytes.fromhex("5D8C9B9B00"))

check("too short -> None", cdl.from_rp1210_buffer(b"00000000", 4) is None)
check("MID 0 noise -> None",
      cdl.from_rp1210_buffer(bytes.fromhex("0000000000FF3100"), 7) is None)

# --- 2. names ------------------------------------------------------------- #
check("mid name 36", cdl.cdl_mid_name(36) == "Engine Control #1")
check("mid name unknown", cdl.cdl_mid_name(231) == "CDL module 231")
check("iid names documented",
      cdl.describe_iid(82) == "Request to broadcast diagnostic codes")
check("iid unknown", cdl.describe_iid(0xF3) == "IID 243")

# The complete REHS0126 CDL MID table (9-255): every live-observed controller
# plus the rest of the published list.
check("mid table complete size", len(CAT_CDL_MID) >= 130)
for mid, name in ((36, "Engine Control #1"), (53, "Graphical Display Module"),
                  (81, "Transmission Control"), (122, "Product Link Module"),
                  (39, "Machine Control Module"), (82, "Electronic Implement Control")):
    check("mid %d named" % mid, CAT_CDL_MID.get(mid) == name)

# CDL FMI is a DIFFERENT vocabulary from J1939 FMI - guard the split so the
# J1939 table can never be reused for CDL codes.
check("cdl fmi 0 is High (not the J1939 text)", cdl.cdl_fmi_name(0) == "High")
check("cdl fmi 3", cdl.cdl_fmi_name(3) == "Voltage Above Normal")
check("cdl fmi 14", cdl.cdl_fmi_name(14) == "Special Instruction")
check("cdl fmi unknown", cdl.cdl_fmi_name(99) == "FMI 99")
import lookup.spn as spn                                   # noqa: E402
check("cdl vs j1939 fmi tables differ",
      cdl.cdl_fmi_name(0) != spn.fmi_name(0))

# --- 3. session: decoded and raw frames both feed one view --------------- #
s = cdl.CdlSession()
s.handle(m)
s.handle(m2)
s.handle(m2)
raw_frame = SimpleNamespace(raw=bytes.fromhex("000DFC012400FC5D8C9B9B00"))
s.handle(raw_frame)                 # what RawCdlSource delivers in a capture
check("one module per MID", list(s.modules) == [36])
mod = s.modules[36]
check("message count", mod.messages == 4)
check("iid histogram", dict(mod.iids) == {0xF3: 1, 0xFA: 2, 0xFC: 1})
check("last data per iid", mod.last_data[0xFC] == bytes.fromhex("5D8C9B9B00"))
check("label names the controller and bus",
      mod.label == "Engine Control #1 (Cat Data Link)")
check("make is CAT", mod.make == "CAT")
check("no faked DTC lists", mod.active_dtcs == [] and mod.previous_dtcs == [])
check("describe line", "4 message(s)" in mod.describe())

# --- 4. merged key space -------------------------------------------------- #
check("cdl key math", reader.CDL_KEY_BASE + 36 != reader.J1708_KEY_BASE + 36)
check("cdl keys not j1708 keys", not reader.is_j1708_key(reader.CDL_KEY_BASE + 36))
check("j1708 keys still j1708 keys", reader.is_j1708_key(reader.J1708_KEY_BASE + 128))
check("cdl_mid recovers", reader.cdl_mid(reader.CDL_KEY_BASE + 36) == 36)

# --- 5. the merged session routes 'cdl' tags ------------------------------ #
from lookup.manufacturers import friendly_make   # noqa: E402

cs = reader.CombinedSession()
cs.handle(TaggedFrame("cdl", m))
key = reader.CDL_KEY_BASE + 36
check("cdl frame reaches the merged module list", key in cs.modules)
check("merged label intact", cs.modules[key].label == mod.label)
check("cdl session counted it", cs.cdl.messages == 1)

# A J1939 frame still routes to the J1939 session (regression guard).
import modules.j1939 as J                                   # noqa: E402
cs.handle(TaggedFrame("j1939", J.Frame(pgn=0x0EE00, source=0x00,
                                       destination=0xFF, data=bytes(8),
                                       priority=6)))
check("j1939 routing intact", 0x00 in cs.modules
      and cs.modules[0x00] is not None)

# --- 6. CTPL -> CAT (CAT engines' free-form CI make string) ---------------- #
check("friendly_make('CTPL') == 'CAT'", friendly_make("CTPL") == "CAT")
check("friendly_make('Caterpillar') == 'CAT'",
      friendly_make("Caterpillar") == "CAT")

# --- 7. wire-read identity (the ML98B MID-13 poll) ----------------------- #
# REAL bytes from the Challenger ML98B capture: the onboard service interface
# (MID 13) polls the engine (MID 36), and the engine answers with its identity.
si = cdl.CdlSession()

def feed(sess, hexstr):
    b = bytes.fromhex(hexstr)
    return sess.handle(cdl.CDLMessage(mid=b[0], dest=b[1], iid=b[2],
                                      data=b[3:], raw=b))

feed(si, "0D2460F81C")    # request: read IID 0xF8 sub 0x1C from the engine
feed(si, "0D242086")      # request: read IID 0x86 (the 0x20 sub-less form)
feed(si, "0D2460F810")    # request: serial
feed(si, "0D2460F81A")     # request: status
# model reply: sub 0x1C, len 0x13, "CAT 3056 Engine" + 4 NUL pads (observed)
feed(si, "240DF81C13434154203330353620456E67696E6500000000")
# serial reply: len 0x08, "35602905", then the unidentified BE03 tail
feed(si, "240DF810083335363032393035BE03F81000")
# build date reply to the 0x20 request: [0x86][len 5]["AUG04"]
feed(si, "240D86054155473034")
# status reply: " NOT  PROGRAMMED "
feed(si, "240DF81A11204E4F54202050524F4752414D4D454420")

eng = si.modules[36]
check("identity: model", eng.identity.get("model") == "CAT 3056 Engine")
check("identity: serial", eng.identity.get("serial") == "35602905")
check("identity: build date", eng.identity.get("build_date") == "AUG04")
check("identity: status", eng.identity.get("status") == "NOT  PROGRAMMED")
check("identity: label uses the model",
      eng.label == "CAT 3056 Engine (Cat Data Link)")
check("identity: describe carries it", "serial='35602905'" in eng.describe())

# An EVIDENCED sub (0x2D) is now named serial_2; it must not hijack the label.
feed(si, "3551F82D084D4A433030343934")          # -> "MJC00494"
check("identity: serial_2 mapped",
      si.modules[53].identity.get("serial_2") == "MJC00494")
check("identity: mapped serial does not hijack the label",
      si.modules[53].label.startswith("Graphical")
      and "MJC00494" not in si.modules[53].label)
# A TRULY unknown sub (0x2E) is still kept under a raw key, never guessed.
feed(si, "3551F82E084D4A433030343935")          # -> "MJC00495"
check("identity: unknown sub kept raw",
      si.modules[53].identity.get("iid_0xF8_sub_0x2E") == "MJC00495")

# 0x1A is the machine MODEL on loaders ("938H"), not a status phrase.
s1a = cdl.CdlSession()
feed(s1a, "350DF81A0439333848")                  # sub 0x1A, len 4, "938H"
check("identity: 0x1A model on machine",
      s1a.modules[53].identity.get("model") == "938H")
check("identity: 0x1A model drives label",
      s1a.modules[53].label == "938H (Cat Data Link)")

# Length robustness: a declared length that exceeds the payload, or is < 3,
# must never be scraped as identity (mirrors the J1587 length-byte lesson).
sl = cdl.CdlSession()
feed(sl, "240DF81C204341542033303536")    # len 0x20 but only 8 ASCII bytes
feed(sl, "240DF81C024341")                # len 2 (< 3)
check("identity: bad declared length not scraped",
      all(not m.identity for m in sl.modules.values()))

# FALSE-POSITIVE guards: binary F8 traffic and the parameter broadcasts
# (0xA2) must never be scraped as identity.
s3 = cdl.CdlSession()
feed(s3, "3551F8030A02030600 0E00 030001 00".replace(" ", ""))
feed(s3, "2451A20700BE0000000000")
feed(s3, "2435A203000000")
check("identity: binary F8 not scraped", not s3.modules or all(
    not m.identity for m in s3.modules.values()))
# The 0x86 sub-less form requires an observed request first.
s4 = cdl.CdlSession()
feed(s4, "240D86054155473034")
check("identity: sub-less reply needs the request",
      not s4.modules[36].identity)

# --- 8. CDL transmit: request builders + codes decode + active poll ------- #
# Wire-verified shapes (live on the C6.6 aux engine; the identity
# subs answered identically on the Challenger ML98B's 3056).

check("request: identity sub form",
      cdl.build_read_request(0x24, 0xF8, 0x1C) == bytes.fromhex("0B2460F81C"))
check("request: sub-less form",
      cdl.build_read_request(0x24, 0x86) == bytes.fromhex("0B242086"))
check("request: codes read",
      cdl.build_read_request(0x24, 0x82) == bytes.fromhex("0B242082"))
check("request: we present as MID 11, never ET's MID 13",
      cdl.TOOL_MID == 0x0B)

# --- 8a. the capture tee records the transmit side ------------------------ #
# A CDL exchange is request/response: if the request side never reaches the
# file, every reply in it is unreachable. Regression from 2026-11-19 (the
# C6.6 capture held 303 RX CDL frames and zero TX while the poll ran at
# ~5 requests/s - send_cdl went straight to CombinedSource, bypassing the
# LoggingSource tee that J1939 and J1708 already used).


class _FakeCombined:
    """Just enough of CombinedSource for the logging wrapper to tee."""

    def __init__(self):
        self.sent = []

    def send_cdl(self, data):
        self.sent.append(data)
        return 0


import tempfile                       # noqa: E402 - local to this check
te = _FakeCombined()
ts = LoggingSource(te)
tpath = os.path.join(tempfile.mkdtemp(), "cdl_capture.log")
treq = cdl.build_read_request(0x24, 0x82)
ts.start(tpath)
trc = ts.send_cdl(treq)
ts.stop()
with open(tpath, encoding="utf-8") as fh:
    # Drop the capture header comments: only frame lines matter here.
    tlines = [ln for ln in fh.read().splitlines()
              if ln and not ln.startswith("#")]

check("capture: TX CDL line is written",
      tlines == ["TX CDL 0B:242082"])   # codes read = 0x20 form
check("capture: TX CDL shares the CDLMessage line format",
      tlines and tlines[0] == "TX " + cdl.format_wire(treq))
check("capture: RX and TX CDL lines have the same shape",
      cdl.CDLMessage(mid=0x24, dest=0x0B, iid=0x82, data=b"",
                     raw=treq).to_log_line() == tlines[0][3:])
check("capture: the transmit is still forwarded", te.sent == [treq])
check("capture: the inner rc is returned", trc == 0)
# Logging off must be a pure pass-through, never a gate on the wire.
ts2 = LoggingSource(_FakeCombined())
check("capture: not logging -> forwarded, rc kept",
      ts2.send_cdl(treq) == 0 and ts2._inner.sent == [treq] and not ts2.logging)
check("capture: no sender on the inner -> None, no crash",
      LoggingSource(object()).send_cdl(treq) is None)

# --- 8b. live parameter reads (CAT PID registry; wire form from the loader) --
check("pid request: low PID uses the 0x20 form",
      cdl.build_pid_request(0x24, 0x40) == bytes.fromhex("0B242040"))
check("pid request: high-byte PID uses the 0x60 form",
      cdl.build_pid_request(0x24, 0xF013) == bytes.fromhex("0B2460F013"))
# BYTE ORDER: LSB first. The 0.3.0.155 MSB-first decode read a cold, key-on
# C6 ACERT as 6400 C coolant and 92 psi oil pressure (2026-11-14 field test).
# These are the REAL reply bytes from that capture.
check("live: C6 coolant 19 00 is 25 C, not the MSB reading 6400",
      cdl.decode_live_reply(0x44, bytes.fromhex("1900"))
      == (0x44, "Engine Coolant Temperature", "25", "\u00b0C"))
check("live: C6 oil pressure 05 00 is ~0, not the MSB reading 92 psi",
      cdl.decode_live_reply(0x54, bytes.fromhex("0500"))
      == (0x54, "Engine Oil Pressure", "2.5", "kPa"))
check("live: C6 hourmeter 10 0B is 2832 h",
      cdl.decode_live_reply(0x5E, bytes.fromhex("100B"))
      == (0x5E, "Hourmeter", "2832", "h"))
check("live: C6 battery 1-byte value 18 is 12 V",
      cdl.decode_live_reply(0xF0, bytes.fromhex("1318"))
      == (0xF013, "System Battery Voltage", "12", "V"))
check("live: C6 engine speed 00 00 is 0 RPM",
      cdl.decode_live_reply(0x40, bytes.fromhex("0000"))
      == (0x40, "Engine Speed", "0", "RPM"))
# REAL loader bytes: the display polls PID 0x005E every second and the engine
# answers 5D 26 = 9821 h LSB-first. Its 0xFC20 hours parameter answered
# 56 26 = 9814 h - 7 h apart, which only works little-endian (MSB would put
# them 1792 h apart).
check("live: loader hourmeter reply decodes from real bytes",
      cdl.decode_live_reply(0x5E, bytes.fromhex("5D26"))
      == (0x5E, "Hourmeter", "9821", "h"))
check("live: engine speed 0.5 rpm/bit, LSB first",
      cdl.decode_live_reply(0x40, bytes.fromhex("401F"))
      == (0x40, "Engine Speed", "4000", "RPM"))
check("live: coolant 1 C/bit, LSB first",
      cdl.decode_live_reply(0x44, bytes.fromhex("5700"))
      == (0x44, "Engine Coolant Temperature", "87", "\u00b0C"))
check("live: battery 0.5 V/bit, 2-byte LSB first",
      cdl.decode_live_reply(0xF0, bytes.fromhex("131A00"))
      == (0xF013, "System Battery Voltage", "13", "V"))
check("live: all-FF is not available",
      cdl.decode_live_reply(0x44, bytes.fromhex("FFFF")) is None)

# --- 8e. published engine PID table vs the idling C6.6 (2026-11-19) -------- #
# Real reply bytes from the live sweep. Every value here was cross-checked
# against the same quantity on J1939 at that moment, so these guard both the
# scale AND the PID identity (a wrong PID would not land on a matching value).
check("table: 0x0053 atmospheric BF00 = 95.5 kPa",
      cdl.decode_live_reply(0x53, bytes.fromhex("BF00"))
      == (0x53, "Atmospheric Pressure", "95.5", "kPa"))
check("table: 0x005B absolute boost = atmospheric at idle",
      cdl.decode_live_reply(0x5B, bytes.fromhex("BF00"))
      == (0x5B, "Boost Pressure (absolute)", "95.5", "kPa"))
check("table: 0x005A absolute oil press 9503 = 458.5 kPa",
      cdl.decode_live_reply(0x5A, bytes.fromhex("9503"))
      == (0x5A, "Filtered Oil Pressure (abs)", "458.5", "kPa"))
check("table: 0x0054 gauge oil press E402 = 370 kPa",
      cdl.decode_live_reply(0x54, bytes.fromhex("E402"))
      == (0x54, "Engine Oil Pressure", "370", "kPa"))
check("table: 0x005A abs = 0x0054 gauge + 0x0053 atmospheric (within 10 kPa)",
      abs((458.5 - 95.5) - 370.0) <= 10)
check("table: coolant 4C00 = 76 C",
      cdl.decode_live_reply(0x44, bytes.fromhex("4C00"))[2] == "76")
check("table: 0xF118 engine load factor 0A = 10 %",
      cdl.decode_live_reply(0xF1, bytes.fromhex("180A"))
      == (0xF118, "Engine Load Factor", "10", "%"))
check("table: 0xF189 power derate 00 = 0 %",
      cdl.decode_live_reply(0xF1, bytes.fromhex("8900"))
      == (0xF189, "Engine Power Derate", "0", "%"))
check("table: 0xF510 low idle speed 0E06 = 775 RPM",
      cdl.decode_live_reply(0xF5, bytes.fromhex("100E06"))
      == (0xF510, "Low Idle Speed", "775", "RPM"))
check("table: 0x00C8 total fuel is a 4-byte count",
      cdl.decode_live_reply(0xC8, bytes.fromhex("08A80000"))
      == (0xC8, "Total Fuel (raw count)", "43016", "count"))
# The trap: a parameter the ECM HAS but with no valid value answers with a
# fault identifier. Decoding those as numbers gave 3278 C and 32762 kPa
# before this rule - exactly the nonsense a user would report as a bug.
check("table: 0xF50E fuel pressure FFF4 is a fault identifier, not 32762 kPa",
      cdl.decode_live_reply(0xF5, bytes.fromhex("0EF4FF")) is None)
check("table: 0xF51D fuel temp 8014 is a fault identifier, not 3278 C",
      cdl.decode_live_reply(0xF5, bytes.fromhex("1D1480")) is None)
check("table: signed PIDs keep their negative range (0xFFE5 is -27 C)",
      cdl.decode_live_reply(0x44, bytes.fromhex("E5FF"))[2] == "-27")
check("table: 4-byte counters are exempt from the FID ranges",
      cdl.decode_live_reply(0xC8, bytes.fromhex("F0FFFF00")) is not None)

# --- 8f. loader capture (2026-11-13, 938H): two newly proven shapes ------- #
ldr = cdl.CdlSession()      # local: the shared `sp` is built further down
# Total operating TIME (published 0xFC2D "Total Operating Hours", 4 bytes,
# seconds). Two machines agree within an hour of their own hourmeter.
check("loader: 0xFC2D D0861B02 = 9821.8 h vs the 9821 h hourmeter",
      cdl.decode_live_reply(0xFC, bytes.fromhex("2DD0861B02"))
      == (0xFC2D, "Total Operating Time", "9821.8", "h"))
check("c6.6: 0xFC2D 7AA89B00 = 2833.7 h vs the 2833.3 h hourmeter",
      cdl.decode_live_reply(0xFC, bytes.fromhex("2D7AA89B00"))
      == (0xFC2D, "Total Operating Time", "2833.7", "h"))

# Engine speed is ALSO broadcast unsolicited, engine -> transmission, IID
# 0x40 (1,589 frames in that capture, 824-840 rpm at idle).
ldr.live.clear()
ldr.handle(cdl.CDLMessage(mid=0x24, dest=0x51, iid=0x40,
                         data=bytes.fromhex("7406"),
                         raw=bytes.fromhex("2451407406")))
check("loader: unsolicited 24->51 IID 0x40 decodes as 826 RPM",
      ldr.live.get(36, {}).get("Engine Speed") == ("826", "RPM"))
ldr.live.clear()
ldr.handle(cdl.CDLMessage(mid=0x24, dest=0x51, iid=0x40,
                         data=bytes.fromhex("0000"),
                         raw=bytes.fromhex("2451400000")))
check("loader: the real 24 51 40 0000 sample stays empty (0 rpm = no value)",
      ldr.live.get(36, {}) == {})
ldr.live.clear()
ldr.handle(cdl.CDLMessage(mid=0x24, dest=0x35, iid=0x40,
                         data=bytes.fromhex("1880"),
                         raw=bytes.fromhex("2435401880")))
check("loader: 0x8018 speed sample is still a fault identifier",
      ldr.live.get(36, {}) == {})

# --- 8g. A2 multiplexed blocks (2026-11-19 loader, real bytes) ----------- #
# [len][block id][records], len == len(data) - 1 (held on 6,750/6,750 frames).
check("a2: length rule accepted",
      cdl.decode_a2_block(bytes.fromhex("03019F08")) == (0x01, bytes.fromhex("9F08")))
check("a2: broken length rejected",
      cdl.decode_a2_block(bytes.fromhex("05019F08")) is None)
check("a2: block 0x01 stopped (0000) = 0 RPM, not suppressed",
      cdl.decode_a2_live(bytes.fromhex("03010000"))
      == [("Engine Speed", "0", "RPM")])
check("a2: block 0x01 running 9F08 = 1103.5 RPM",
      cdl.decode_a2_live(bytes.fromhex("03019F08"))
      == [("Engine Speed", "1103.5", "RPM")])
check("a2: block 0x03 warm sample (coolant 27 C, 1100 RPM, 476.5 kPa, 43 %)",
      cdl.decode_a2_live(bytes.fromhex(
          "1803001B009808B9032CB3020058005D3B00009201F1FF1480"))
      == [("Engine Coolant Temperature", "27", "\u00b0C"),
          ("Engine Speed", "1100", "RPM"),
          ("Engine Oil Pressure", "476.5", "kPa"),
          ("Actual Engine Torque", "44", "%")])
check("a2: block 0x03 cold sample (coolant 13 C)",
      cdl.decode_a2_live(bytes.fromhex(
          "1803000D009808A5032BB302007500A43B0000D601DDFF1480"))[0]
      == ("Engine Coolant Temperature", "13", "\u00b0C"))
check("a2: an unknown block stays raw",
      cdl.decode_a2_live(bytes.fromhex("0B0042FF7F8813FDFF0000AE")) == [])
check("a2: a different payload length for block 0x03 is not decoded",
      cdl.decode_a2_live(bytes.fromhex("0303001B00")) == [])

# --- 8h. the CDL engine also feeds the J1939 Engine row --------------------- #
# The panel renders ONE module bucket, so a machine whose ECM reports on CDL
# (loader: J1939 carried EEC1 only) must show the CDL values under Engine.
import reader as _reader
from framesource import TaggedFrame as _Tagged
from modules.j1939 import Frame as _Frame

cs = _reader.CombinedSession()
cs.handle(_Tagged("j1939", _Frame.from_arbid(
    0x0CF00400, bytes.fromhex("FFFFA86C22FFFFFF"))))          # EEC1 1102 rpm
# The loader delivers these as A2 blocks, which bypass the request gate.
cs.handle(_Tagged("cdl", cdl.CDLMessage(
    mid=0x24, dest=0x35, iid=0xA2,
    data=bytes.fromhex("1803001B009808B9032CB3020058005D3B00009201F1FF1480"),
    raw=bytes.fromhex("2435A2"))))
eng = cs.live.get(0x00, {})
check("merge: J1939 Engine keeps its own speed",
      eng.get("Engine Speed") == ("1102", "RPM"))
check("merge: CDL coolant reaches the J1939 Engine row",
      eng.get("Engine Coolant Temperature") == ("27", "\u00b0C"))
check("merge: CDL oil pressure reaches the J1939 Engine row",
      eng.get("Engine Oil Pressure") == ("476.5", "kPa"))
check("merge: the CDL module keeps its own bucket too",
      cs.live.get(_reader.CDL_KEY_BASE + 0x24, {}).get("Engine Coolant Temperature")
      == ("27", "\u00b0C"))
check("merge: a J1939 value is never overwritten by CDL",
      cs.live[0x00]["Engine Speed"] == ("1102", "RPM"))

# --- 8i. replay: CDL lines reach the session, our own TX is not a module --- #
import tempfile as _tempfile
from framesource import CdlReplaySource as _CdlReplay

with _tempfile.NamedTemporaryFile("w", suffix=".log", delete=False,
                                  encoding="utf-8") as _fh:
    _fh.write("# capture\n")
    _fh.write("RX 0CF00400:FFFFA86C22FFFFFF\n")
    _fh.write("TX CDL 0B:242044\n")          # our own request
    _fh.write("RX CDL 24:0B441B00\n")        # engine answers 27 C
rp = _CdlReplay(_fh.name)
rp.connect()
check("replay: CDL lines are replayed, J1939 lines are not",
      rp.frame_count == 2)
f1 = rp.read_frame()
check("replay: frame shape is a CDLMessage",
      f1.mid == 0x0B and f1.dest == 0x24 and f1.iid == 0x20)
rp.connect()                             # rewind: the session needs both
_rs = cdl.CdlSession()
for _ in range(2):
    _rs.handle(rp.read_frame())
check("replay: our own TX registers the request but is not a module",
      cdl.TOOL_MID not in _rs.modules and 0x24 in _rs.modules)
check("replay: the reply after our own request decodes",
      _rs.live.get(0x24, {}).get("Engine Coolant Temperature") == ("27", "\u00b0C"))

# SEBU6874: raw $8000-$801F are FAULT IDENTIFIERS for engine speed, coolant
# and oil pressure ($FFE0-$FFFF for PID 0xF40E) - a failed sensor must never
# render as "Engine Speed 16384 RPM". Coolant/oil pressure ranges include
# negatives, so those values are SIGNED (a -10 C winter reading must not
# render as ~65500).
check("live: engine-speed FID range is a fault, not a value",
      cdl.decode_live_reply(0x40, bytes.fromhex("0380")) is None)
check("live: coolant FID range is a fault, not a value",
      cdl.decode_live_reply(0x44, bytes.fromhex("0280")) is None)
check("live: oil-pressure FID range is a fault, not a value",
      cdl.decode_live_reply(0x54, bytes.fromhex("1F80")) is None)
check("live: F40E FID range (FFE0-FFFF) is a fault",
      cdl.decode_live_reply(0xF4, bytes.fromhex("0EE1FF")) is None)
check("live: coolant decodes signed below zero (winter machine)",
      cdl.decode_live_reply(0x44, bytes.fromhex("F6FF"))
      == (0x44, "Engine Coolant Temperature", "-10", "\u00b0C"))
check("live: oil pressure decodes signed (slight negative bias)",
      cdl.decode_live_reply(0x54, bytes.fromhex("FEFF"))
      == (0x54, "Engine Oil Pressure", "-1", "kPa"))
check("live: positive values unchanged by the signed rule",
      cdl.decode_live_reply(0x54, bytes.fromhex("0500"))
      == (0x54, "Engine Oil Pressure", "2.5", "kPa"))
# SEBU6874: hourmeter's valid range is $0000-$FFFF (NO Fault-Identifier
# range) - only the conservative all-0xFF sentinel rule hides the single
# 65535 h reading. Revisit only with wire evidence.
check("live: hourmeter has no FID range (FFFE = 65534 h)",
      cdl.decode_live_reply(0x5E, bytes.fromhex("FEFF"))
      == (0x5E, "Hourmeter", "65534", "h"))
check("live: wrong length rejected",
      cdl.decode_live_reply(0x40, bytes.fromhex("40")) is None)
check("live: unknown PID stays raw",
      # 0xFC20 is real loader traffic (payload 2059260C00) with no published
      # meaning yet - it must stay raw, not be guessed at.
      cdl.decode_live_reply(0xFC, bytes.fromhex("2059260C00")) is None)
check("live: identity reply is not a live value",
      cdl.decode_live_reply(0xF8, bytes.fromhex("1C134341542033303536")) is None)

# The decoded value must survive the per-protocol -> merged-session sync (the
# 2026-11-13 latent bug dropped cdl.live there; this is the end-to-end proof).
feed = lambda s, h: s.handle(cdl.CDLMessage(mid=bytes.fromhex(h)[0],
                                            dest=bytes.fromhex(h)[1],
                                            iid=bytes.fromhex(h)[2],
                                            data=bytes.fromhex(h)[3:],
                                            raw=bytes.fromhex(h)))
# A reply only decodes when it answers a request we saw. The display asks the
# engine for PID 0x005E, then the engine answers.
lv = cdl.CdlSession()
feed(lv, "3524205E")              # display -> engine: read PID 0x005E
feed(lv, "24355E5D26")            # engine -> display: hourmeter 9821 h
check("live: request gate decodes the answer",
      lv.live.get(36, {}).get("Hourmeter") == ("9821", "h"))
# REAL loader traffic: engine -> transmission every ~90 ms with IID 0x40 and
# data 0000. It is NOT a reply to a 0x0040 read (no request precedes it), so
# it must never surface as "Engine Speed 0".
fp = cdl.CdlSession()
feed(fp, "2451400000")
check("live: unreplied IID 0x40 is not Engine Speed", fp.live == {})

cs_live = reader.CombinedSession()
cs_live.handle(TaggedFrame("cdl", cdl.CDLMessage(
    mid=53, dest=36, iid=0x20, data=bytes.fromhex("5E"),
    raw=bytes.fromhex("3524205E"))))
cs_live.handle(TaggedFrame("cdl", cdl.CDLMessage(
    mid=36, dest=53, iid=0x5E, data=bytes.fromhex("5D26"),
    raw=bytes.fromhex("24355E5D26"))))
cs_live._sync()
check("cdl live reaches the merged session.live bucket",
      cs_live.live.get(reader.CDL_KEY_BASE + 36, {}).get("Hourmeter")
      == ("9821", "h"))

# The three live code replies: healthy / two sensors out /
# one sensor back in.
check("codes: healthy engine -> empty",
      cdl.decode_codes(bytes.fromhex("00")) == [])
two = cdl.decode_codes(bytes.fromhex("06070503" + "006E23"))
check("codes: two records", len(two) == 2)
check("codes: CID MSB-first (0x0705 = 1797, 0x006E = 110)",
      two[0]["spn"] == 1797 and two[1]["spn"] == 110)
check("codes: FMI from the low bits", all(c["fmi"] == 3 for c in two))
check("codes: raw flags byte kept",
      two[0]["occ"] == 0x03 and two[1]["occ"] == 0x23)
check("codes: component name from CAT_PID",
      two[0]["desc"] == "Fuel Rail Pressure Sensor"
      and two[1]["desc"] == "Engine Coolant Temperature Sensor")
# The legacy CID supplement (REHS0126-18) must survive: a 2010-era machine
# reporting CID 441 or 7798 must name the component, not fall back to the
# bare number.
check("codes: legacy -18 CID supplement resolves",
      cdl.CAT_PID.get(433) == "Hydraulic Oil Filter Differential Pressure Switch"
      and cdl.CAT_PID.get(441) == "Electronic Governor Relay"
      and cdl.CAT_PID.get(512) == "Cylinder #12 Prechamber"
      and cdl.CAT_PID.get(768) == "RS-485 Data Link"
      and cdl.CAT_PID.get(7798) == "Road Light"
      and cdl.CAT_PID.get(7802) == "Beacon")
check("codes: legacy -18 supplement names a CID code",
      cdl.decode_codes(bytes.fromhex("0301B103"))[0]["desc"]
      == "Hydraulic Oil Filter Differential Pressure Switch")
check("codes: num column", two[0]["num"] == "CID 1797")
one = cdl.decode_codes(bytes.fromhex("03070543"))
check("codes: single record after replug",
      len(one) == 1 and one[0]["spn"] == 1797 and one[0]["fmi"] == 3
      and one[0]["occ"] == 0x43)
check("codes: truncated record ignored",
      cdl.decode_codes(bytes.fromhex("040705")) == [])

# The active poll: one transmit per tick, identity once per module, then
# codes on the interval; a refused send ends the campaign without spraying.
sp = cdl.CdlSession()
feed(sp, "2400F33100")            # engine heartbeat -> module 36
cd: list[bytes] = []
sp.set_sender(lambda d: (cd.append(d), 0)[1])
# An echo of our own MID must exist as a module yet never be polled.
feed(sp, "0B00F33100")
sp.poll_tick()                     # tick 1: the first identity request
sp.poll_tick(); sp.poll_tick(); sp.poll_tick()   # ticks 2-4: rest of identity
sp.poll_tick()                     # tick 5: the codes read
check("poll: identity + codes, one per tick",
      [d.hex().upper() for d in cd] ==
      ["0B2460F81C", "0B2460F810", "0B2460F814", "0B242086", "0B242082"])
# The engine then gets the documented live-parameter set, one per tick; the
# low PIDs use 0x20 and the F0xx battery PID uses 0x60.
for _ in range(len(cdl.CAT_CDL_LIVE_POLL)):
    sp.poll_tick()
check("poll: live parameters follow identity/codes",
      [d.hex().upper() for d in cd[5:]] ==
      ["0B242040", "0B242044", "0B242054", "0B2460F013",
       "0B24205E", "0B242016", "0B24205D", "0B2460F40E",
       # 2026-11-19: wire-proven answering on the C6.6. Nothing is removed
       # for a silent machine - a loader answers different PIDs.
       "0B24205B", "0B2460F118"])
sp.poll_tick()                     # nothing new inside the 4 s/10 s windows
check("poll: quiet until the next live cycle",
      len(cd) == 5 + len(cdl.CAT_CDL_LIVE_POLL))
feed(sp, "240B82" + "03070543")   # the live single-code answer
eng = sp.modules[36]
check("codes reply lands in the module's list",
      len(eng.active_dtcs) == 1 and eng.active_dtcs[0]["spn"] == 1797)
check("codes reply carries the CID description",
      eng.active_dtcs[0]["desc"] == "Fuel Rail Pressure Sensor")
check("describe counts the codes", "1 CDL code(s)" in eng.describe())
feed(sp, "240B82" + "00")          # healthy engine: zero codes is REAL
check("healthy reply clears the list", sp.modules[36].active_dtcs == [])
feed(sp, "240082" + "03070543")    # a broadcast: NOT addressed to us
check("broadcast 82 ignored", sp.modules[36].active_dtcs == [])
# Our own 0x20 request makes the 0x86 build-date reply decodeable on a
# machine with no onboard poller (the C6.6 has none).
feed(sp, "240B86" + "05" + "4155473036")   # [len 5]"AUG06"
check("own request unlocks the build-date reply",
      sp.modules[36].identity.get("build_date") == "AUG06")
# Live reply from the engine to us: [engine][tool][0x5E][5D26] -> 9821 h.
feed(sp, "240B5E5D26")
check("live reply lands in the module's bucket",
      sp.live.get(36, {}).get("Hourmeter") == ("9821", "h"))
# A reply observed going to the DISPLAY decodes too (passive live data;
# 5E 26 is 9822 h LSB-first, one more than the reply to us above):
feed(sp, "24355E5E26")
check("passive live reply (engine -> display) decodes",
      sp.live[36]["Hourmeter"] == ("9822", "h"))
# A display REQUEST (IID 0x60) and a broadcast can never be read as values.
sp.live.clear()
feed(sp, "352460FC2D")
feed(sp, "24005E5D26")
check("requests/broadcasts are not decoded as live values", sp.live == {})

# --- F1 multiplexed blocks (REAL bytes, 2026-11-14 Cat ET session) ---------
# The engine pushes IID 0xF1 "broadcast list" blocks at ~1 Hz to the
# service tool (Cat ET = MID 13) once ET subscribes; we hear them
# passively. Block = [0x18][seq][records]; ground truth was the
# operator's 775-RPM low idle / 2000-RPM high idle sequence.
recs = cdl.decode_f1_block(bytes.fromhex("1813400D06443400F4170000" +
                                         "FC0700000000FC0800000000"))
check("F1: real steady block parses (speed/coolant/F417/FC07/FC08)",
      recs is not None and recs[0x40] == 0x060D and recs[0x44] == 0x34
      and recs[0xF417] == 0 and recs[0xFC07] == 0 and recs[0xFC08] == 0)
check("F1: real early block with F189/F525/F66A records parses",
      cdl.decode_f1_block(bytes.fromhex("1819F18900401106F4170000" +
                                        "F5254E00F66A0E06FC0700000000"))
      == {0xF189: 0, 0x40: 0x0611, 0xF417: 0, 0xF525: 0x4E,
          0xF66A: 0x060E, 0xFC07: 0})
check("F1: wrong type byte rejected",
      cdl.decode_f1_block(bytes.fromhex("1913400D06443400")) is None)
check("F1: truncated record rejects the whole block",
      cdl.decode_f1_block(bytes.fromhex("1813400D")) is None)
sp.live.clear()
sp.handle(cdl.CDLMessage(mid=0x24, dest=0x0D, iid=0xF1,
                         data=bytes.fromhex("1813400D06443400F4170000" +
                                            "FC0700000000FC0800000000"),
                         raw=bytes.fromhex("240DF11813400D06443400")))
check("F1: passive ET-session block lands in the live bucket",
      sp.live.get(36, {}).get("Engine Speed") == ("774.5", "RPM")
      and sp.live.get(36, {}).get("Engine Coolant Temperature") == ("52", "\u00b0C"))
sp.live.clear()
sp.handle(cdl.CDLMessage(mid=0x24, dest=0x0D, iid=0xF1,
                         data=bytes.fromhex("1819401880443500F4170000" +
                                            "FC0700000000"),
                         raw=bytes.fromhex("240DF11819401880443500")))
check("F1: FID-range speed (the real 0x8018 shutdown sample) renders nothing",
      "Engine Speed" not in sp.live.get(36, {})
      and sp.live.get(36, {}).get("Engine Coolant Temperature") == ("53", "\u00b0C"))
# ET's own single-parameter read, observed on the wire: the request gate
# must decode the engine's answer TO ET just like an answer to us.
sp.live.clear()
feed(sp, "0D242040")                # ET (MID 13) -> engine: read PID 0x0040
feed(sp, "240D400E06")              # engine -> ET: 0x060E LSB = 775 RPM
check("live: ET's own 0x20 poll decodes passively (775 RPM idle)",
      sp.live.get(36, {}).get("Engine Speed") == ("775", "RPM"))
# A refused send ends the poll campaign silently (passive decode lives on).
sp.set_sender(lambda d: -1)
sp.poll_tick()
sp.poll_tick()
check("failed send stops polling", not sp._tx_ok)

# LOADER replies, live 2026-11-13 (cdl_sweep_... capture):
# the transmission (MID 81) and display (MID 53) answered the SAME code-read
# with their own fault logs - the decode is not engine-specific.
tx = cdl.decode_codes(bytes.fromhex("0302A148"))
check("loader: transmission reply (CID 673 FMI 8)",
      len(tx) == 1 and tx[0]["spn"] == 673 and tx[0]["fmi"] == 8
      and tx[0]["occ"] == 0x48
      and tx[0]["desc"] == "Transmission Output Speed Sensor #2")
disp = cdl.decode_codes(bytes.fromhex("09032B49024E4900A844"))
check("loader: display reply, three codes",
      [(c["spn"], c["fmi"], c["occ"]) for c in disp]
      == [(811, 9, 0x49), (590, 9, 0x49), (168, 4, 0x44)])
check("loader: display code descriptions",
      disp[0]["desc"] == "Gauge Cluster #1"
      and disp[1]["desc"] == "Engine Control Module"
      and disp[2]["desc"] == "Electrical System Voltage")

# --- CAT CDL <-> J1939 cross-reference (80-1275) ------------------------- #
from lookup.oem_cat_cdl import (CAT_CDL_TO_J1939, CAT_J1939_TO_CDL,
                                j1939_for_cdl, j1939_candidates_for_cdl)
check("CDL xref size", len(CAT_CDL_TO_J1939) >= 260)
check("CDL 774-2 -> J1939 29-2", CAT_CDL_TO_J1939[(774, 2)] == ((29, 2),))
check("CDL 486-3 maps to itself", j1939_for_cdl(486, 3, "C13") == (486, 3))
check("CDL xref gated by family", j1939_for_cdl(486, 3, "C7") is None)
check("ambiguous 1836-3 keeps both",
      j1939_candidates_for_cdl(1836, 3, "C18") == ((441, 3), (1385, 3)))
check("reverse J1939 29-2 -> CDL 774-2",
      CAT_J1939_TO_CDL.get((29, 2)) == (774, 2))

# --- report --------------------------------------------------------------- #
fails = [n for n, good in ok if not good]
print("=" * 68)
print("CDL decode regression")
print("=" * 68)
for name, good in ok:
    print(("PASS  " if good else "FAIL  ") + name)
print("-" * 68)
print("checks run: %d" % len(ok))
print("FAILED: none - all pass" if not fails
      else "FAILED: %s" % ", ".join(fails))
sys.exit(1 if fails else 0)