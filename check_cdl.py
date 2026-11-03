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
from framesource import TaggedFrame

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

# The loader's display answering with an UNKNOWN sub: kept under a raw key,
# never guessed (its meaning is unidentified - probably a serial).
feed(si, "3551F82D084D4A433030343934")          # -> "MJC00494"
check("identity: unknown sub kept raw",
      si.modules[53].identity.get("iid_0xF8_sub_0x2D") == "MJC00494")
check("identity: unknown sub does not hijack the label",
      "(Cat Data Link)" in si.modules[53].label
      and si.modules[53].label.startswith("Graphical"))

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
sp.poll_tick()                     # nothing new inside the 10 s window
check("poll: quiet until the codes interval", len(cd) == 5)
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