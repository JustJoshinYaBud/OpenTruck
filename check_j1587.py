"""OpenTruck - J1587 parameter parsing regression (run: python check_j1587.py).

Locks in two real-world parsing behaviors found by diffing the SAE J1587
FEB2002 standard against field captures:

* some adapter paths omit the J1587 length byte on variable-length PIDs
  (the same truck shows "ED 11 <VIN>" on one path and "ED <VIN>" on another);
* page-2 PIDs arrive behind extension PID 255 (real PID = low byte + 256).

Plus the page-2 PID name table extracted from the standard's Table 2.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.j1708 import (  # noqa: E402
    parse_params, decode_pid, build_request, build_broadcast_request,
    decode_vehicle_wheel_speeds, J1708Session, J1708Message,
)
from lookup.pid1587 import PID_NAMES, PID_SCALE  # noqa: E402

ok = []


def check(name, cond):
    ok.append((name, bool(cond)))


# --- variable-length PID WITH the J1587 length byte (standard) --------------
p = parse_params(bytes([237, 0x11]) + b"1HTWGAAT6FH608218")
check("VIN with length byte", p == [(237, b"1HTWGAAT6FH608218")])

p = parse_params(bytes([243, 0x11, 0x88]) + b"WABCO*4461062010")
check("compID with length byte", p == [(243, b"\x88WABCO*4461062010")])

# --- same PIDs WITHOUT the length byte (some RP1210 paths) ------------------
p = parse_params(bytes([237]) + b"2FZAGCT37AY104616")
check("VIN without length byte",
      p == [(237, b"2FZAGCT37AY104616")])

p = parse_params(bytes([243, 0x80]) + b"MRCBN*906*592981")
check("compID without length byte (keep MID)",
      p == [(243, b"\x80MRCBN*906*592981")])
# And the component-ID decoder must recover the full make (MRCBN, not RCBN).
_pid, _data = p[0]
check("compID no-count make intact", _data[1:].split(b"*")[0] == b"MRCBN")

# --- page-2 extension (PID 255) --------------------------------------------
p = parse_params(bytes([255, 106, 0x05]))                 # low 106 -> 362
check("page2 single", p == [(362, b"\x05")])
p = parse_params(bytes([255, 161, 0x12, 0x34]))           # low 161 -> 417
check("page2 double", p == [(417, b"\x12\x34")])
p = parse_params(bytes([255, 192, 0x03, 1, 2, 3]))        # low 192 -> 448
check("page2 variable", p == [(448, b"\x01\x02\x03")])

# --- page-2 names + decode ------------------------------------------------
check("page2 name 362", PID_NAMES.get(362)
      == "Percent Exhaust Gas Recirculation Valve #2 Position")
check("page2 name 417", PID_NAMES.get(417) == "Gross Vehicle Weight")
check("page2 decode name", decode_pid(362, b"\x05")[0]
      == "Percent Exhaust Gas Recirculation Valve #2 Position")
check("page2 name 511", PID_NAMES.get(511) == "Page 2 Extension")
check("page1 name unchanged", PID_NAMES.get(110) == "Engine Coolant Temperature")

# --- page-2 request builders (extension PID 255) --------------------------
check("page1 broadcast request", build_broadcast_request(243) == bytes([0, 243]))
check("page2 broadcast request",
      build_broadcast_request(362) == bytes([255, 0x00, 106]))
check("page1 directed request",
      build_request(0x80, 243) == bytes([128, 243, 0x80]))
check("page2 directed request",
      build_request(0x80, 362) == bytes([255, 0x80, 106, 0x80]))

# --- page-2 Appendix A scaling -------------------------------------------
check("page2 scale 362", PID_SCALE.get(362) == (0.5, 0.0, "%", False))
check("page2 scale 424", PID_SCALE.get(424) == (0.05, 0.0, "V", False))
check("page2 scaled value",
      decode_pid(424, b"\x64\x00") == ("DC Voltage", "5", "V"))
check("page2 percent value", decode_pid(362, b"\x64")[1] == "50")

# --- PID 214 Vehicle Wheel Speeds (SAE J1587 A.214) ----------------------
ws = decode_vehicle_wheel_speeds(bytes([100, 100, 0xFE, 50, 0, 0xFF]))
check("wheel speeds: six rows", len(ws) == 6)
check("wheel speeds: 0.805 scale",
      ws[0] == ("Wheel Speed Axle 1 Left", "80.5", "km/h"))
check("wheel speeds: n/a on 0xFE/0xFF", ws[2][1] == "n/a" and ws[5][1] == "n/a")
_ws = J1708Session()
_ws.handle(J1708Message(mid=136, params=[(214, bytes([100] * 6))]))
check("wheel speeds: land in live data",
      _ws.live.get(136, {}).get("Wheel Speed Axle 3 Right") == ("80.5", "km/h"))

# --- Appendix A generated scalings --------------------------------------
check("scale PID18 kPa",
      decode_pid(18, bytes([100])) == ("Extended Range Fuel Pressure", "400", "kPa"))
check("scale PID178 weights->kg", decode_pid(178, bytes([0x10, 0x27]))[2] == "kg")
check("scale PID93 torque->Nm", decode_pid(93, bytes([0x40]))[2] == "Nm")
check("fuel economy ->L/100km",
      decode_pid(184, bytes([0xC3, 0x0B]))[2] == "L/100km")
check("multi-field PIDs excluded from PID_SCALE",
      215 not in PID_SCALE and 241 not in PID_SCALE)

# --- Appendix A temperatures vs. an ECM that substitutes fixed values --------
# Real 2026-11-16 Ford+Cummins capture: the engine broadcast PID 175 = "50 03"
# (848 x 0.25 degF = 212 F = 100 C) and PID 174 = "78 02" (158 F = 70 C) as the
# SAME bytes for the whole session, and the identical bytes again two days
# earlier, while coolant (PID 110) climbed 60->69 F and the same ECM's J1939
# ET1 (65262) sent SPN 174/175 as "not available". Those are the ECM's fixed
# substitute values for sensors it does not have - NOT a decode error. A.174/
# A.175 are signed 0.25 degF/bit with NO offset, and the same truck's J1939 oil
# temperature (SPN 175, 0.03125 C/bit, -273 C) matched this decode to 0.1 C on
# two other captures. Do NOT "fix" this by adding a -40 degF offset.
check("scale A.175 signed 0.25 degF/bit, no extra offset",
      PID_SCALE.get(175) == (0.25 * 5.0 / 9.0, -32.0 * (5.0 / 9.0), "\u00b0C", True))
check("oil temp real bytes 50 03 -> 100 C",
      decode_pid(175, bytes([0x50, 0x03]))
      == ("Engine Oil Temperature", "100", "\u00b0C"))
check("fuel temp real bytes 78 02 -> 70 C",
      decode_pid(174, bytes([0x78, 0x02]))
      == ("Fuel Temperature", "70", "\u00b0C"))
check("coolant pressure A.109 0.862 kPa/bit (gauge)",
      PID_SCALE.get(109) == (0.862, 0.0, "kPa", False)
      and decode_pid(109, bytes([116]))
      == ("Coolant Pressure", "99.99", "kPa"))
# Same capture: PID 190 raw 3410 is 852.5 rpm (idle), NOT 3410 rpm - the raw
# count and the rpm value are easy to confuse when eyeballing a capture.
check("engine speed A.190 0.25 rpm/bit",
      PID_SCALE.get(190) == (0.25, 0.0, "rpm", False)
      and decode_pid(190, bytes([0x52, 0x0D]))[1] == "852.5")
# A.105/A.110 are UNSIGNED 1.0 degF 0-255 (no offset): 71 -> 21.67 C.
check("intake manifold A.105 1 degF unsigned",
      PID_SCALE.get(105) == (5.0 / 9.0, -32.0 * (5.0 / 9.0), "\u00b0C", False)
      and decode_pid(105, bytes([71]))[1] == "21.67")

# --- an engine SID keeps its engine meaning next to a transmission module ----
# The Eaton Fuller Top-2 overlay is gone: a Top-2 system has no controller of
# its own, so its faults arrive as engine MIDs - indistinguishable from a real
# engine fault. With any transmission controller on the bus (MID 130) it used
# to relabel engine SID 26/40 FMI 3/4 as "Transmission (Eaton Fuller Top-2):
# Shift Solenoid...", which is wrong on an Allison/ZF truck.
_top2 = J1708Session()
_top2.handle(J1708Message(mid=130, params=[]))                 # transmission present
_top2.handle(J1708Message(mid=128, params=[(194, bytes([40, 0x34]))]))   # SID 40, FMI 4
_dtc = _top2.modules[128].active_dtcs[0]
check("engine SID 40 FMI 4 keeps the engine meaning",
      _dtc["desc"] == "Auxiliary Output Device Driver #2")
check("no Eaton Top-2 relabel", "Top-2" not in str(_dtc["desc"]))

failed = [n for n, c in ok if not c]
print("checks run:", len(ok))
print("FAILED:", failed if failed else "none - all pass")
sys.exit(1 if failed else 0)
