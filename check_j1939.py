"""OpenTruck - J1939 protocol regression (run: python check_j1939.py).

Re-verifies the J1939 protocol work (arbid/PGN round-trip with EDP,
NAME encode/decode, address claim, ACK decode, BAM reassembly, directed
RTS/CTS/EOMA transfer, abort, DM1 parse) against the current code. The J1939
core has not been edited since that work; this is the guard that proves it.

The harness builds real J1939-21 frames: TP.CM carries size/packets/pgn in
data[1:8], DT frames carry [seq]+payload, and an abort is a full 8-byte frame.
"""


"""J1939 regression: re-verify the protocol work against the
current code (post all OBD/ELM changes)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modules import j1939 as J
from modules.j1939 import Frame, TransportProtocol, decode_ack

ok = []
def check(name, cond):
    ok.append((name, bool(cond)))

# 1. arbid <-> PGN round-trip
f = Frame.from_arbid(0x18FECA00, b"\x01\x02")
check("PDU2 pgn", f.pgn == 0xFECA and f.source == 0x00)
check("PDU2 roundtrip", f.to_arbid() == 0x18FECA00)
f = Frame.from_arbid(0x18EF0010, b"")          # PDU1: PF=EF, PS=dest 0x00, SA=0x10
check("PDU1 pgn/dest", f.pgn == 0xEF00 and f.destination == 0x00)
f = Frame.from_arbid(0x19FECA01, b"")          # EDP bit set
check("EDP carried", f.pgn == 0x1FECA and f.to_arbid() == 0x19FECA01)

# 2. NAME encode/decode round-trip
n = J.decode_name(bytes([0x01, 0x00, 0x90, 0x0F, 0x00, 0x00, 0x00, 0x00]))
enc = J.encode_name(n.identity, n.manufacturer, n.ecu_instance,
                    n.function_instance, n.function, n.vehicle_system,
                    n.industry_group, n.arbitrary_addr_capable)
check("NAME roundtrip", bytes(enc) == bytes([0x01, 0x00, 0x90, 0x0F, 0, 0, 0, 0]))
check("NAME function label", J.function_name(n.function) is not None)

# 3. Address claim build
claim = J.build_address_claim(0xF9, J.encode_name(0x0F9001), 0xFF)
check("claim is PGN 0xEE00 global", J.pgn_from_id(claim.to_arbid()) == 0xEE00)

# 4. ACK decode
check("ACK positive", decode_ack(b"\x00\x01\xF9\x00\xFF\xD3\xFE\x00")["control"] == 0)
check("ACK pending", decode_ack(b"\x01\x01\xF9\x00\xFF\xD3\xFE\x00")["control"] == 1)
check("ACK denied", decode_ack(b"\x02\x01\xF9\x00\xFF\xD3\xFE\x00")["control"] == 2)

sent = bytes(range(0x11, 0x11 + 12))           # 12-byte payload
PGN_UNDER_TEST = 0xFECA

# 5. BAM reassembly (broadcast): TP.CM BAM + 2 DT frames
bam = Frame.from_arbid(0x1CECFF00,
                       bytes([0x20, 12, 0, 2, 0xFF]) + PGN_UNDER_TEST.to_bytes(3, "little"), 0)
dt1 = Frame.from_arbid(0x1CEBFF00, bytes([1]) + sent[:7], 0)
dt2 = Frame.from_arbid(0x1CEBFF00, bytes([2]) + sent[7:12] + b"\xFF", 0)
tp = TransportProtocol()
r1 = tp.feed(bam)
r2 = tp.feed(dt1)
r3 = tp.feed(dt2)
check("BAM announce -> None", r1 is None and r2 is None)
check("BAM reassembled", r3 == (PGN_UNDER_TEST, sent))

# 6. Directed RTS -> CTS -> DT -> EOMA
tx = []
tp2 = TransportProtocol(source_address=0xF9, send=lambda fr: tx.append(fr))
rts = Frame.from_arbid(0x18ECF910,                       # to us (0xF9) from 0x10
                       bytes([0x10, 12, 0, 2, 0xFF]) + PGN_UNDER_TEST.to_bytes(3, "little"), 0)
r = tp2.feed(rts)
cts = tx[0]
check("RTS -> CTS sent", r is None and len(tx) == 1
      and cts.data[:3] == bytes([0x11, 0x02, 0x01])
      and cts.destination == 0x10 and cts.source == 0xF9)
d1 = Frame.from_arbid(0x18EB0010, bytes([1]) + sent[:7], 0)
d2 = Frame.from_arbid(0x18EB0010, bytes([2]) + sent[7:12] + b"\xFF", 0)
check("DT1 -> None", tp2.feed(d1) is None)
r2 = tp2.feed(d2)
check("RTS/CTS reassembled", r2 == (PGN_UNDER_TEST, sent))
check("EOMA sent to sender", len(tx) == 2 and tx[1].destination == 0x10
      and tx[1].data[0] == 0x13)

# 7. Abort drops the session (abort is a full 8-byte TP.CM frame)
tp2.feed(rts)
tp2.feed(Frame.from_arbid(0x18ECF910,
        bytes([0xFF, 0xFF, 0xFF, 0xFF, 0xFF]) + PGN_UNDER_TEST.to_bytes(3, "little"), 0))
check("abort clears session", tp2.feed(d1) is None)

# 8. DM1 payload parse -> SPN 110 FMI 0
lamps, dtcs = J.parse_dm_payload(b"\x00\x00\x6E\x00\x00\x00")
check("DM1 SPN110/FMI0", any(d.spn == 110 and d.fmi == 0 for d in dtcs))

# 9. VI (PGN 65260) validation: only a real 17-char VIN is accepted.
# Field failure behind this guard: a Kenworth whose VI was never
# programmed answered the VIN request with a 6-digit fleet unit number
# ("265008") and the app displayed it as the VIN. J1939-71 defines the
# VI field as 17 characters; anything else is a unit number/serial, not
# a VIN, and must never overwrite a real VIN either.
import reader as R
sess = R.Session(None)
def _vi(txt):
    sess._store_ident(0x21, 0xFEEC, txt.encode("ascii") + b"*\xff\xff\xff")
_vi("265008")                      # fleet unit number: rejected
check("VI unit number rejected", sess.vin == "")
_vi("0" * 17)                       # "not programmed" dummy: rejected
check("VI all-zeros rejected", sess.vin == "")
_vi("1NK")                          # 3 chars of a VIN: rejected
check("VI fragment rejected", sess.vin == "")
_vi("2NKNH4HX98M123456")            # real-shaped VIN: accepted
check("VI real VIN accepted", sess.vin == "2NKNH4HX98M123456")
_vi("265008")                      # junk must not overwrite the real VIN
check("VI junk cannot overwrite", sess.vin == "2NKNH4HX98M123456")

# 9b. 13-char identifiers are machine PINs (AEM / ISO 10261): stored as the
# PIN, never the VIN, and junk still cannot overwrite either.
def _pin(txt):
    sess._store_ident(0x21, 0xFEEC, txt.encode("ascii") + b"*\xff\xff\xff")
_pin("1DW644XZKLM12")               # 13-char machine PIN
check("13-char stored as PIN", sess.pin == "1DW644XZKLM12")
check("13-char never a VIN", sess.vin == "2NKNH4HX98M123456")
check("ident label is PIN", sess.vehicle_ident() == ("PIN", "1DW644XZKLM12"))
_pin("265008")                      # unit number: rejected from both fields
check("unit number rejected (PIN)", sess.pin == "1DW644XZKLM12")

# 9c. A 17-char identifier is a PIN on an ag/construction bus (NAME industry
# group 2/3) and a VIN everywhere else.
_mach = R.Session(None)
_mach.handle(J.build_address_claim(
    0x00, J.encode_name(1, manufacturer=49, function=0, industry_group=3)))
check("industry-group consensus", _mach.industry_group() == 3)
_mach._store_ident(0x00, 0xFEEC, b"1FF644XZKLM123456*\xff\xff\xff")
check("17-char on machine bus = PIN",
      _mach.vehicle_ident() == ("PIN", "1FF644XZKLM123456"))
_truck = R.Session(None)
_truck.handle(J.build_address_claim(
    0x00, J.encode_name(1, manufacturer=49, function=0, industry_group=1)))
_truck._store_ident(0x00, 0xFEEC, b"2NKNH4HX98M123456*\xff\xff\xff")
check("17-char on truck bus = VIN",
      _truck.vehicle_ident() == ("VIN", "2NKNH4HX98M123456"))
check("no ident -> None", R.Session(None).vehicle_ident() is None)

# 9d. The manufacturer-code vote decides the 17-char label. Wire-proven
# on a Deere 5055E (TractorHacking corpus): all 5 ECUs claim John Deere 33
# while the industry group is 8, an UNDEFINED value - IG alone can never
# identify that machine. Trucks are a federation of makers, so a lone
# machine-brand engine must not flip a truck bus.
from lookup.oem import machine_mfr_codes
_mcodes = machine_mfr_codes()
check("machine codes include Deere/CAT/CNH/AGCO",
      {33, 8, 94, 102} <= _mcodes)
check("truck makers are not machine codes",
      not ({45, 25, 42, 10, 60, 37} & _mcodes))
check("Volvo split: 60/61 trucks, 1061 CE",
      60 not in _mcodes and 61 not in _mcodes and 1061 in _mcodes)
_deere = R.Session(None)
for _sa, _fn in ((0x00, 0), (0x03, 3), (0x06, 14), (0x17, 19), (0x47, 52)):
    # the 5055E's five ECUs: engine/transmission/cruise/cluster/chassis,
    # all claiming John Deere (33) at the undefined industry group 8
    _deere.handle(J.build_address_claim(
        _sa, J.encode_name(1, manufacturer=33, function=_fn, industry_group=8)))
check("5055E claims consensus is Deere",
      _deere.manufacturer_consensus() == 33)
_deere._store_ident(0x00, 0xFEEC, b"1DW644XZKLM123456*\xff\xff\xff")
check("5055E-style: Deere vehicle-systems ECUs + IG 8 -> PIN",
      _deere.vehicle_ident() == ("PIN", "1DW644XZKLM123456"))
_cattruck = R.Session(None)
for _sa, _fn in ((0x00, 0), (0x01, 0), (0x0F, 12)):
    # the CAT C13-powered Oshkosh airport-equipment vehicle (ctrpl
    # captures; a VIN vehicle, identified on the vehicle itself): engine ECMs plus
    # the fn-12 engine retarder, all claiming CAT 8 at IG 4 - engine-domain
    # claims follow the ENGINE maker and must NOT make it a machine
    _cattruck.handle(J.build_address_claim(
        _sa, J.encode_name(1, manufacturer=8, function=_fn, industry_group=4)))
_cattruck._store_ident(0x00, 0xFEEC, b"2NKNH4HX98M123456*\xff\xff\xff")
check("CAT C13 Oshkosh airport vehicle stays VIN",
      _cattruck.vehicle_ident() == ("VIN", "2NKNH4HX98M123456"))
_lone = R.Session(None)
_lone.handle(J.build_address_claim(
    0x03, J.encode_name(1, manufacturer=7, function=3)))   # one Case transmission
_lone._store_ident(0x03, 0xFEEC, b"2NKNH4HX98M123456*\xff\xff\xff")
check("a lone vehicle-systems claim cannot decide",
      _lone.vehicle_ident() == ("VIN", "2NKNH4HX98M123456"))
# Fendt + ISOBUS (MF4 corpus): 3 AGCO + 3 Kverneland implement ECUs.
# Kverneland 89 is NOT a machine-maker code; the old majority rule let the
# implements outvote the tractor. Counting machine claims fixes it.
_fendt = R.Session(None)
for _sa, _mfr, _fn in ((0x20, 102, 54), (0x21, 102, 130), (0x22, 102, 29),
                       (0x30, 89, 29), (0x31, 89, 128), (0x32, 89, 134)):
    _fendt.handle(J.build_address_claim(
        _sa, J.encode_name(1, manufacturer=_mfr, function=_fn, industry_group=8)))
check("Fendt + ISOBUS implements -> machine",
      _fendt.is_machine_bus() is True)
# The Oshkosh CAT truck has exactly ONE CAT vehicle-systems controller; one
# machine-maker claim must not flip a real VIN vehicle.
_os = R.Session(None)
for _sa, _fn in ((0x00, 0), (0x01, 0), (0x0F, 12), (0x21, 22)):
    _os.handle(J.build_address_claim(
        _sa, J.encode_name(1, manufacturer=8, function=_fn, industry_group=4)))
check("single CAT body controller stays VIN", _os.is_machine_bus() is False)
_mixed = R.Session(None)
_mixed.handle(J.build_address_claim(0x00, J.encode_name(1, manufacturer=10)))            # Cummins
_mixed.handle(J.build_address_claim(0x0B, J.encode_name(1, manufacturer=1, function=11)))    # Bendix ABS
_mixed.handle(J.build_address_claim(0x21, J.encode_name(1, manufacturer=25, function=22)))   # DTNA body
_mixed.handle(J.build_address_claim(0x30, J.encode_name(1, manufacturer=33)))               # lone Deere engine
_mixed._store_ident(0x00, 0xFEEC, b"2NKNH4HX98M123456*\xff\xff\xff")
check("lone Deere engine on a truck bus -> VIN",
      _mixed.vehicle_ident() == ("VIN", "2NKNH4HX98M123456"))
check("truck mixed bus is not a machine", _mixed.is_machine_bus() is False)
check("CombinedSession delegates is_machine_bus",
      R.CombinedSession().is_machine_bus() is False)

# 10. Identification PGN constants must point at the right SAE PGNs.
# Regression: ECU_ID was long set to 0xFDED, but 65005/0xFDED is "Utility
# Total AC Energy" - real ECU ID is 64965/0xFDC5 (SPN 2901 part no, 2902
# serial, ...). The tool was requesting the wrong PGN and never saw ECU
# part/serial. Cross-checked against lookup/pgn.py's own names.
from lookup import pgn as _pgn
check("ECU_ID is 64965 (0xFDC5)", J.PGN.ECU_ID == 0xFDC5)
check("ECU_ID name matches table",
      _pgn.PGN_NAMES.get(J.PGN.ECU_ID) == "ECU Identification Information")
check("0xFDED is not ECU ID",
      _pgn.PGN_NAMES.get(0xFDED) == "Utility Total AC Energy")

# 11. Standard NAME-function and preferred-address tables must be COMPLETE
# and CORRECT. Regression 2026-11-17: FUNCTION_NAMES was a 15-entry hand
# subset and several values were actually address-numbered (15 read
# "Retarder" instead of "Fuel System", 19 "Steering" instead of "Instrument
# Cluster", ...). Global functions from SAE J1939-71 Table B11 / J1939DA,
# extended to 0-94 via the Wireshark/ISOBUS tables; addresses from the
# J1939-71 global preferred set (0-89 + 248-253).
check("FUNCTION_NAMES complete (>=95)", len(J.FUNCTION_NAMES) >= 95)
for _v, _nm in {0: "Engine", 3: "Transmission", 9: "Brakes - System Controller",
                15: "Fuel System", 19: "Instrument Cluster", 26: "Body Controller",
                29: "Virtual Terminal (in cab)", 52: "Chassis Controller",
                53: "Alternator/Charging System", 78: "Fire Suppression System",
                94: "Auxiliary Display"}.items():
    check(f"function {_v} == {_nm!r}", J.FUNCTION_NAMES.get(_v) == _nm)
check("PREFERRED_ADDRESS_NAMES complete (>=90)",
      len(J.PREFERRED_ADDRESS_NAMES) >= 90)
for _a, _nm in {0x00: "Engine #1", 0x0B: "Brakes - System Controller",
                0x17: "Instrument Cluster #1",
                0x2F: "Suspension - System Controller #1",
                0x31: "Cab Controller - Primary",
                0x4A: "Communications Unit, Cellular",
                0xF9: "Off Board Diagnostic-Service Tool #1"}.items():
    check(f"address 0x{_a:02X} == {_nm!r}", J.PREFERRED_ADDRESS_NAMES.get(_a) == _nm)
# Arbitrary (128-247) and GLOBAL (255) are NOT claimable source-address labels.
check("no arbitrary address labelled",
      not any(0x80 <= a <= 0xF7 for a in J.PREFERRED_ADDRESS_NAMES))
check("255 GLOBAL not a source label", 0xFF not in J.PREFERRED_ADDRESS_NAMES)
check("function_name never None", all(J.function_name(f) for f in range(0, 256)))

# 12. IG-specific NAME functions (Table B12): the same function number means
# different things per industry group / vehicle system, so resolution is
# EXACT and never falls back across contexts.
check("IG-specific table present", len(J.IG_SPECIFIC_NAME_FUNCTIONS) >= 280)
check("fn129 IG0/VS0 (flat)",
      J.function_name(129, 0, 0) == "Off-board diagnostic-service tool")
check("fn129 IG1/VS0", J.function_name(129, 1, 0) == "Door Controller")
check("fn129 IG1/VS1 differs",
      J.function_name(129, 1, 1) == "Fifth Wheel Smart System")
check("fn135 IG3/VS0", J.function_name(135, 3, 0) == "Loader Control")
check("unassigned stays unknown",
      J.function_name(200, 1, 1) == "Function 200 (unknown)")
check("fn255 Not Available", J.function_name(255) == "Not Available")
_n2 = J.decode_name(bytes([0x01, 0x00, 0x90, 0x0F, 0x00, 0x81, 0x00, 0x00]))
check("label fn129 IG0/VS0",
      J.name_function_label(_n2) == "Off-board diagnostic-service tool")
_n3 = J.decode_name(bytes([0x01, 0x00, 0x90, 0x0F, 0x00, 0x81, 0x02, 0x04]))
check("label fn129 IG1/VS1",
      J.name_function_label(_n3) == "Fifth Wheel Smart System")
_n4 = J.decode_name(bytes([0x01, 0x00, 0x90, 0x0F, 0x00, 0xC8, 0x00, 0x00]))
check("unresolvable -> None (address fallback)",
      J.name_function_label(_n4) is None)

# 13. Manufacturer codes: the standard SAE/ISOBUS registry is complete.
# Cross-checked 2026-11-17 against the ISOBUS public export
# (wireshark data-isobus.c, isobus.net CSV): 22 codes were missing and added;
# no code was mislabelled (the remaining name differences are the curated
# short names this table deliberately carries).
from lookup import manufacturers as M
check("manufacturer registry complete (1694)", len(M.MANUFACTURER_NAMES) == 1694)
check("code 1548 Sailgauge", M.manufacturer_name(1548) == "Sailgauge LLC")
check("code 1664 Nautech", M.manufacturer_name(1664) == "Nautech Ltd.")
check("code 1676 Merlin Solar",
      M.manufacturer_name(1676) == "Merlin Solar Technologies, Inc.")
check("code 1712 Optisens",
      M.manufacturer_name(1712) == "Optisens Intelligent Technology Co., Ltd.")
check("curated short name kept (Cummins)", M.manufacturer_name(10) == "Cummins")

# 14. Software ID: J1939 count-byte format AND the no-count format CAT
# broadcasts (wire-proven in the C13/C6.6 captures). A printable first
# character is text, not a field count.
_sid = R.Session(None)
_sid._store_ident(0x00, J.PGN.SOFTWARE_ID,
                  b"\x03Part Number*Date Code*:3825329-00*\xff")
check("software id count byte",
      _sid.modules[0].software_id == "Part Number | Date Code | :3825329-00")
_sid2 = R.Session(None)
_sid2._store_ident(0x00, J.PGN.SOFTWARE_ID,
                   b"Part Number*Date Code*:3825329-00*JAN12*\xff")
check("software id no-count CAT",
      _sid2.modules[0].software_id
      == "Part Number | Date Code | :3825329-00 | JAN12")
check("CTRPL CI make -> CAT", M.friendly_make("CTRPL") == "CAT")

# 14b. Each brand's code table stays loaded and resolves through the OEM layer.
from lookup.oem import resolve_code_description, resolve_pid_name
from lookup.oem_perkins import PERKINS_SPN_FMI
from lookup.oem_deutz import DEUTZ_SPN_FMI
from lookup.oem_cummins import CUMMINS_SPN_FMI
check("Perkins single table", len(PERKINS_SPN_FMI) >= 380)
check("Deutz single table", len(DEUTZ_SPN_FMI) >= 1500)
check("Cummins single table", len(CUMMINS_SPN_FMI) >= 1150)
check("Cummins model never changes resolution",
      resolve_code_description(84, 9, mfr=10, model="ISB")
      == resolve_code_description(84, 9, mfr=10, model="X15")
      == resolve_code_description(84, 9, mfr=10, model="QSG")
      == "Wheel-Based Vehicle Speed")
check("Cummins Tier-4-book row is reachable",
      resolve_code_description(91, 9, mfr=10)
      == "Accelerator Pedal Position 1")
check("Perkins code resolves",
      resolve_code_description(111, 1, mfr=93, model="1204E-E44TA").startswith("Engine Coolant Level"))
check("Perkins unknown model resolves via the brand broad",
      resolve_code_description(111, 1, mfr=93, model="4045")
      == "Engine Coolant Level")
check("Deutz code resolves",
      resolve_code_description(523924, 3, mfr=352, model="EMR4").startswith("Actuator relay 2"))
check("Deutz unknown model resolves via the EMR4+EMRL1 broad union",
      resolve_code_description(523924, 3, mfr=352, model="TCD 6.1")
      .startswith("Actuator relay 2"))
check("Cummins code resolves",
      "Intake Manifold 1 Pressure" in
      resolve_code_description(102, 18, mfr=10, model="QSB6.7"))
check("Cummins aftertreatment row resolves",
      resolve_code_description(520199, 3, mfr=10)
      .startswith("Cruise Control"))

# 14d. FPT, AGCO and Yanmar code tables plus their own code numbering.
from lookup.oem_fpt import FPT_SPN_FMI, spn_fmi_for_hex_dtc
from lookup.oem_agco import AGCO_SPN_FMI, spn_fmi_for_wintest_code
from lookup.oem_yanmar import YANMAR_SPN_FMI, spn_fmi_for_pcode
from lookup.oem_deutz import spn_fmi_for_dtc
check("FPT table", len(FPT_SPN_FMI) >= 1600)
check("FPT hex DTC 4B84-1F", spn_fmi_for_hex_dtc("4B84-1F", "N45") == (19332, 31))
check("FPT hex DTC translates regardless of model",
      spn_fmi_for_hex_dtc("4B84-1F", "CURSOR") == (19332, 31))
check("FPT resolves", resolve_code_description(19332, 31, make="FPT", model="N45").startswith("Air filter"))
check("FPT unknown model resolves via the brand broad",
      resolve_code_description(19332, 31, make="FPT").startswith("Air filter"))
check("AGCO single table size", len(AGCO_SPN_FMI) >= 380)
check("AGCO Wintest 91_3", spn_fmi_for_wintest_code("91_3", "SISU 44") == (91, 3))
check("AGCO Wintest translates regardless of model",
      spn_fmi_for_wintest_code("91_3", "FENDT") == (91, 3))
check("AGCO resolves",
      resolve_code_description(91, 3, mfr=102, model="SISU 44")
      == "Throttle 1 sensor above normal or open circuit (IDLE)")
check("AGCO unknown model resolves via the union broad",
      resolve_code_description(91, 3, mfr=102).startswith("Throttle 1 sensor"))
check("AGCO contested key takes the newer generation's wording",
      resolve_code_description(100, 18, mfr=102) == "Oil pressure LOW")
check("AGCO EEM3-only key survives in the union",
      resolve_code_description(9306, 31, mfr=102) == "PTO input error")
check("AGCO EEM4-only key reaches the broad",
      resolve_code_description(2791, 11, mfr=102).startswith("EGR Valve"))
check("Yanmar single table", len(YANMAR_SPN_FMI) >= 100)
check("Yanmar P0193", spn_fmi_for_pcode("P0193", "4TNV98") == (157, 3))
check("Yanmar P-code translates regardless of model",
      spn_fmi_for_pcode("P0193", "YANMAR OTHER") == (157, 3))
check("Yanmar resolves", resolve_code_description(3242, 4, mfr=172, model="4TNV98").startswith("DPF inlet"))
check("Yanmar third-column row still reads as plain text",
      resolve_code_description(157, 3, mfr=172) == YANMAR_SPN_FMI[(157, 3)][0])
from lookup.oem_eaton import EATON_SPN_FMI
check("Eaton single code table", len(EATON_SPN_FMI) >= 120)
check("Eaton newest wording wins (629 = Endurant, not Gen4)",
      resolve_code_description(629, 2, make="EATON") == "TCM Operation 1")
check("Eaton shared SPN takes Endurant wording on every FMI",
      resolve_code_description(5052, 2, make="EATON") == "Engine (Over) Speed")
check("Eaton Gen4-only SPN keeps its wording",
      resolve_code_description(520271, 3, make="EATON") == "ECA Battery Voltage")
check("Yanmar unknown model resolves via the brand broad",
      resolve_code_description(3242, 4, mfr=172).startswith("DPF inlet"))
check("Deutz DTC P1005-00", spn_fmi_for_dtc("P1005-00", "EMR4") == (107, 11))
check("Deutz maker code rides the single table",
      isinstance(DEUTZ_SPN_FMI[(107, 11)], tuple)
      and DEUTZ_SPN_FMI[(107, 11)][1] == "P1005-00")
check("Deutz DTC translates regardless of model",
      spn_fmi_for_dtc("P1005-00", "TCD 6.1") == (107, 11))

# 14c. Detroit DD platform and Navistar MaxxForce DT/9/10 tables (generated).
from lookup.oem_detroit import DETROIT_SPN_FMI
from lookup.oem_navistar import NAVISTAR_SPN_FMI
check("Detroit DD table size", len(DETROIT_SPN_FMI) >= 1300)
check("Detroit DD08 resolves via the DD list",
      resolve_code_description(100, 1, make="DETROIT", model="DD8")
      .startswith("Low Engine Oil Pressure"))
check("Detroit DD15 resolves",
      resolve_code_description(100, 1, make="DETROIT", model="DD15").startswith("Low Engine Oil Pressure"))
check("Detroit DD13 resolves",
      resolve_code_description(3251, 0, make="DETROIT", model="DD13").startswith("Diesel Particulate Filter"))
check("Navistar single table size", len(NAVISTAR_SPN_FMI) >= 790)
check("Navistar DT resolves",
      resolve_code_description(27, 3, make="INTERNATIONAL",
                               model="MAXXFORCE DT").startswith("EGR"))
# MaxxForce 11/13 ride the MAN D26 family with N13/A26 (SCR-era engines), so
# they get A26 wording instead of the SAE fallback.
check("MaxxForce 13 rides the MAN D26 family",
      resolve_code_description(1322, 31, make="INTERNATIONAL",
                               model="MAXXFORCE 13")
      .startswith("Engine Misfire for Multiple Cylinders"))
check("MaxxForce 11 rides the MAN D26 family",
      resolve_code_description(1322, 31, make="INTERNATIONAL",
                               model="MAXXFORCE 11")
      .startswith("Engine Misfire for Multiple Cylinders"))
check("MaxxForce DT keeps DT wording",
      resolve_code_description(27, 3, make="INTERNATIONAL",
                               model="MAXXFORCE DT").startswith("EGR"))
# 14d-2. N13 / A26 are their own family (MAN D26 lineage, A26 lists).
check("N13 resolves via n13_a26",
      resolve_code_description(1322, 31, make="INTERNATIONAL", model="N13")
      .startswith("Engine Misfire for Multiple Cylinders"))
check("A26 resolves via n13_a26",
      resolve_code_description(1322, 31, make="INTERNATIONAL", model="A26")
      .startswith("Engine Misfire for Multiple Cylinders"))
check("Navistar gives one answer regardless of model",
      resolve_code_description(1322, 31, make="INTERNATIONAL",
                               model="MAXXFORCE DT")
      == resolve_code_description(1322, 31, make="INTERNATIONAL",
                                  model="A26"))

# 14f. CAT / Volvo / Mack brand tables (ONE literal per brand).
from lookup.oem_cat import CAT_SPN_FMI, CAT_SPN
from lookup.oem_volvo import VOLVO_PID_FMI, VOLVO_SPN_FMI
check("CAT single code table size", len(CAT_SPN_FMI) >= 330)
check("CAT keeps its SPN name table",
      len(CAT_SPN) >= 2000)
check("CAT T4F-era C13 gets code text",
      resolve_code_description(486, 3, make="CAT", model="EMY2016 CAT C13")
      == "Engine Fan Reverse Switch")
check("CAT-branded C6.6 resolves via the CAT table",
      resolve_code_description(486, 3, make="CAT", model="C6.6L")
      == "Engine Fan Reverse Switch")

# 14g. One table per brand, the newest source generation winning a contested
# code. The CI model string does not affect which table is read.
from lookup.oem import select_oems
check("CAT 626-5 reads the CAT wording",
      resolve_code_description(626, 5, make="CAT", model="C7")
      == "Engine Start Enable Device 1")
check("CAT EMY2007 C13 reads the T4F-era wording (no gate)",
      resolve_code_description(651, 5, make="CAT", model="EMY2007 CAT C13")
      == "Engine Injector Cylinder #01")
check("CAT EMY2016 C13 reads the same wording (model irrelevant)",
      resolve_code_description(651, 5, make="CAT", model="EMY2016 CAT C13")
      == "Engine Injector Cylinder #01")
check("Perkins-built CAT C6.6 resolves via the brand tables",
      resolve_code_description(111, 1, mfr=93, model="C6.6L")
      .startswith("Engine Coolant Level"))
check("CAT CI make 'CTRPL' is the machine-family mark, not a maker key",
      not select_oems(make="CTRPL"))
check("Allison CI make abbreviation selects Allison",
      any(o.id == "allison" for o in select_oems(make="ALLSN")))

# 14h. Every brand with a table resolves over the generic SAE base; scope
# still decides whether an entry's tables are trusted at all (DTNA/Deere
# stay "unknown").
from lookup.oem import REGISTRY
check("scope vocabulary is the two-value ladder",
      {o.scope for o in REGISTRY.values()}
      <= {"oem_wide", "product_family", "unknown"})
check("Volvo unknown model keeps the broad wording",
      resolve_code_description(100, 1, make="VOLVO")
      .startswith("Engine Oil Pressure"))
check("Navistar resolves via the list",
      resolve_code_description(100, 1, mfr=42)
      == "EWPS Engine Oil System below Critical Pressure")

# 14j. One table per brand: the model token never changes the answer, and
# codes outside the table fall through to the generic SAE name.
check("Deutz resolves over the whole table",
      resolve_code_description(29, 2, mfr=352, model="EMR3")
      .startswith("Accelerator Pedal 2 Position"))
check("Deutz EMR5 family resolves",
      resolve_code_description(27, 3, mfr=352, model="EMR5").startswith("Engine"))
check("Deutz 27-3 resolves",
      resolve_code_description(27, 3, mfr=352, model="MD1")
      .startswith("Engine - Position EGR actuator"))
check("Perkins resolves",
      resolve_code_description(100, 1, mfr=93, model="1104E-44TA")
      == "Engine Oil Pressure: Low- most severe (3)")
check("Perkins 404F family resolves",
      resolve_code_description(100, 1, mfr=93, model="404F-22")
      .startswith("Engine Oil Pressure"))
check("Perkins 854F family resolves",
      resolve_code_description(27, 3, mfr=93, model="854F-E34T")
      .startswith("Engine Exhaust Gas Recirculation Valve Position"))
check("Yanmar 4LV family resolves",
      resolve_code_description(157, 10, mfr=172, model="4LV150")
      .startswith("Rail Pressure"))
check("Kubota 03-series family resolves",
      resolve_code_description(29, 3, mfr=416, model="V2403-CR")
      .startswith("Accelerator position sensor"))
check("CAT C9 OCR cross-reference resolves",
      resolve_code_description(100, 3, make="CAT", model="C9 INDUSTRIAL")
      .startswith("Engine Oil Pressure"))
check("CAT C7.1 resolves via the brand table",
      resolve_code_description(100, 3, make="CAT", model="C7.1 T4F")
      == "Engine Oil Pressure")

# 14l. PACCAR MX-11/MX-13 (2026-11-18): the brand finally has a code table.
from lookup.oem_paccar import PACCAR_SPN_FMI as _PM
check("PACCAR MX table size", len(_PM) >= 700)
check("MX-13 family resolves",
      resolve_code_description(723, 8, make="PETERBILT", mfr=45, model="MX-13")
      == "Camshaft Speed Signal - Not Corresponding With Engine Position")
check("MX-11 family resolves",
      resolve_code_description(27, 3, make="KENWORTH", mfr=45, model="MX-11")
      .startswith("EGR Valve"))
check("PACCAR unknown model keeps the broad wording",
      resolve_code_description(100, 1, mfr=45).startswith("Engine Oil Pressure"))
check("PACCAR body module still Refer to OEM",
      resolve_code_description(6977, 19, make="KENWORTH", mfr=45,
                               component="Body Controller") == "Refer to OEM")

# 14k. Volvo/Mack J1587 side (2026-11-18): the official Group 28 lists and
# the 2007 Mack emissions list feed the MID 128 PID/PPID slot, which now
# actually reaches resolve_pid_name (it reads the ENTRY's pid_fmi, not the
# family slot - the old family-only wiring was dead).
from lookup.oem_volvo import (VOLVO_PID_FMI as _VP,
                                VOLVO_J1587_XREF as _VX)
check("Volvo pid_fmi table size", len(_VP) >= 130)
check("Volvo SPN<->MID128 cross-reference size", len(_VX) >= 90)
check("Mack MID 128 PPID resolves",
      resolve_pid_name(442, 3, make="MACK") is not None)
check("Volvo MID 128 PID resolves",
      resolve_pid_name(26, 3, make="VOLVO") is not None)

check("Volvo/Mack SPN/FMI size", len(VOLVO_SPN_FMI) >= 450)
check("Volvo/Mack PID/FMI size", len(VOLVO_PID_FMI) >= 70)
check("Mack and Volvo read the same one table",
      resolve_code_description(100, 1, make="MACK")
      == resolve_code_description(100, 1, make="VOLVO"))
for _model in ("D11", "D13", "D16", "MP7", "MP8", "MP10"):
    check(f"{_model} resolves via d13_mp",
          resolve_code_description(100, 1, make="VOLVO", model=_model)
          .startswith("Engine Oil Pressure"))
check("Volvo D13 unknown code still resolves to something",
      bool(resolve_code_description(999999, 0, make="VOLVO", model="D13")))

# 15. Primary-engine selection: address 0 is only PREFERRED (J1939-81).
# (the CAT/Volvo/Mack family checks sit above, under 14f)
# Fendt sample: EEC1 broadcasts from SA 240 and no ECU claims fn 0 there.
_fendt_bus = R.Session(None)
_fendt_bus.handle(J.build_address_claim(
    0x00, J.encode_name(1, manufacturer=25, function=22)))   # truck body
_fendt_bus.handle(J.build_address_claim(
    0xF0, J.encode_name(1, manufacturer=102, function=134, industry_group=8)))
_fendt_bus.handle(J.Frame.from_arbid(
    0x18F004F0, bytes([0, 0, 0, 0xFA, 0, 0xFF, 0xFF, 0xFF])))   # EEC1 @ 0xF0
check("engine by EEC broadcaster when not fn0",
      _fendt_bus.engine_key() == 0xF0)
# Two engines (Oshkosh C13 @0, C18 @1): the preferred/main engine wins.
_two = R.Session(None)
for _sa in (0x00, 0x01):
    _two.handle(J.build_address_claim(
        _sa, J.encode_name(1, manufacturer=8, function=0, industry_group=4)))
check("two engines -> primary at SA 0", _two.engine_key() == 0)
# J1587 fallback: an engine MID 128 is used when J1939 has no engine.
_cj = R.CombinedSession()
from modules.j1708 import J1708Module   # noqa: E402
_cj.j1708.modules[128] = J1708Module(128)
_cj._sync()
check("J1587 MID 128 engine fallback",
      _cj.engine_key() == R.J1708_KEY_BASE + 128)

failed = [n for n, c in ok if not c]
print("checks run:", len(ok))
print("FAILED:", failed if failed else "none - all pass")
sys.exit(1 if failed else 0)
