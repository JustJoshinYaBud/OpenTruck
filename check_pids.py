"""OpenTruck - verify every OBD PID decoder against the J1979 reference.

Run from the project root:  python check_pids.py

Why this exists: two PID definitions were wrong in the field (catalyst
temperature 3D/3E labels swapped, EVAP pressure 0x32 using PID 0x54's
formula), both found by a vehicle instead of by a test. This checker compares
every decoder in lookup/obd_pids.py against the published J1979 scale/offset
values (CSS Electronics' PID table, cross-checked with Wikipedia's OBD-II PID
table) and fails loudly on any mismatch.

Numeric PIDs are evaluated over several raw-byte vectors and compared with
`offset + scale * raw`. Encoded/bitfield PIDs (monitor status, fuel system,
O2 presence, fuel type...) are checked to return text.

Reference notes:
  * PID 0x32 is a SIGNED 16-bit value: Pa = signed(256A+B) / 4.
  * PID 0x54 is Pa = (256A+B) - 32768. CSS Electronics lists the offset as
    -32767; Wikipedia says -32768. The public tables disagree by one - we
    follow Wikipedia.
  * 0x32/0x54 are converted to kPa at decode time (the canonical pressure unit
    used by the display layer), so their reference scale/offset here are in
    kPa (0x32: signed*0.00025; 0x54: raw/1000 - 32.768).
  * PIDs 0x14-0x1B: the first byte is voltage; the second (trim) byte is not
    decoded. PIDs 0x24-0x2B / 0x34: only the lambda half is decoded.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lookup import obd_pids
from lookup.obd_pids import decode_pid

# pid: (raw_bytes, scale, offset, unit, J1979/CSS name); 'text' = encoded.
REF = {
 0x01: ("text", "Monitor status since DTCs cleared"),
 0x03: ("text", "Fuel system status"),
 0x04: (1, 100/255, 0, "%", "Calculated engine load"),
 0x05: (1, 1, -40, "degC", "Engine coolant temperature"),
 0x06: (1, 1/1.28, -100, "%", "Short term fuel trim (bank 1)"),
 0x07: (1, 1/1.28, -100, "%", "Long term fuel trim (bank 1)"),
 0x08: (1, 1/1.28, -100, "%", "Short term fuel trim (bank 2)"),
 0x09: (1, 1/1.28, -100, "%", "Long term fuel trim (bank 2)"),
 0x0A: (1, 3, 0, "kPa", "Fuel pressure"),
 0x0B: (1, 1, 0, "kPa", "Intake manifold absolute pressure"),
 0x0C: (2, 0.25, 0, "rpm", "Engine speed"),
 0x0D: (1, 1, 0, "km/h", "Vehicle speed"),
 0x0E: (1, 0.5, -64, "deg", "Timing advance"),
 0x0F: (1, 1, -40, "degC", "Intake air temperature"),
 0x10: (2, 0.01, 0, "g/s", "Mass air flow"),
 0x11: (1, 100/255, 0, "%", "Throttle position"),
 0x12: ("text", "Commanded secondary air status"),
 0x13: ("text", "Oxygen sensors present (2 banks)"),
 0x14: (1, 0.005, 0, "V", "O2 voltage (bank 1, sensor 1)"),
 0x15: (1, 0.005, 0, "V", "O2 voltage (bank 1, sensor 2)"),
 0x16: (1, 0.005, 0, "V", "O2 voltage (bank 1, sensor 3)"),
 0x17: (1, 0.005, 0, "V", "O2 voltage (bank 1, sensor 4)"),
 0x18: (1, 0.005, 0, "V", "O2 voltage (bank 2, sensor 1)"),
 0x19: (1, 0.005, 0, "V", "O2 voltage (bank 2, sensor 2)"),
 0x1A: (1, 0.005, 0, "V", "O2 voltage (bank 2, sensor 3)"),
 0x1B: (1, 0.005, 0, "V", "O2 voltage (bank 2, sensor 4)"),
 0x1C: ("text", "OBD standards the vehicle conforms to"),
 0x1D: ("text", "Oxygen sensors present (4 banks)"),
 0x1E: ("text", "Auxiliary input status"),
 0x1F: (2, 1, 0, "s", "Run time since engine start"),
 0x21: (2, 1, 0, "km", "Distance traveled with MIL on"),
 0x22: (2, 0.079, 0, "kPa", "Fuel rail pressure (relative to manifold)"),
 0x23: (2, 10, 0, "kPa", "Fuel rail pressure"),
 0x24: (2, 2/65536, 0, "ratio", "O2 sensor 1 lambda"),
 0x25: (2, 2/65536, 0, "ratio", "O2 sensor 2 lambda"),
 0x26: (2, 2/65536, 0, "ratio", "O2 sensor 3 lambda"),
 0x27: (2, 2/65536, 0, "ratio", "O2 sensor 4 lambda"),
 0x28: (2, 2/65536, 0, "ratio", "O2 sensor 5 lambda"),
 0x29: (2, 2/65536, 0, "ratio", "O2 sensor 6 lambda"),
 0x2A: (2, 2/65536, 0, "ratio", "O2 sensor 7 lambda"),
 0x2B: (2, 2/65536, 0, "ratio", "O2 sensor 8 lambda"),
 0x2C: (1, 100/255, 0, "%", "Commanded EGR"),
 0x2D: (1, 1/1.28, -100, "%", "EGR error"),
 0x2E: (1, 100/255, 0, "%", "Commanded evaporative purge"),
 0x2F: (1, 100/255, 0, "%", "Fuel tank level input"),
 0x30: (1, 1, 0, "count", "Warm-ups since codes cleared"),
 0x31: (2, 1, 0, "km", "Distance traveled since codes cleared"),
 0x32: (2, 0.25/1000, 0, "kPa", "EVAP vapor pressure (signed, native Pa)"),
 0x33: (1, 1, 0, "kPa", "Absolute barometric pressure"),
 0x34: (2, 1/32768, 0, "ratio", "O2 sensor 1 lambda (wide range)"),
 0x3C: (2, 0.1, -40, "degC", "Catalyst temperature (bank 1, sensor 1)"),
 0x3D: (2, 0.1, -40, "degC", "Catalyst temperature (bank 2, sensor 1)"),
 0x3E: (2, 0.1, -40, "degC", "Catalyst temperature (bank 1, sensor 2)"),
 0x3F: (2, 0.1, -40, "degC", "Catalyst temperature (bank 2, sensor 2)"),
 0x35: (2, 1/32768, 0, "ratio", "O2 sensor 2 lambda (wide range)"),
 0x36: (2, 1/32768, 0, "ratio", "O2 sensor 3 lambda (wide range)"),
 0x37: (2, 1/32768, 0, "ratio", "O2 sensor 4 lambda (wide range)"),
 0x38: (2, 1/32768, 0, "ratio", "O2 sensor 5 lambda (wide range)"),
 0x39: (2, 1/32768, 0, "ratio", "O2 sensor 6 lambda (wide range)"),
 0x3A: (2, 1/32768, 0, "ratio", "O2 sensor 7 lambda (wide range)"),
 0x3B: (2, 1/32768, 0, "ratio", "O2 sensor 8 lambda (wide range)"),
 0x41: ("text", "Monitor status this drive cycle"),
 0x42: (2, 0.001, 0, "V", "Control module voltage"),
 0x43: (2, 100/255, 0, "%", "Absolute load value"),
 0x44: (2, 1/32768, 0, "ratio", "Commanded equivalence ratio"),
 0x45: (1, 100/255, 0, "%", "Relative throttle position"),
 0x46: (1, 1, -40, "degC", "Ambient air temperature"),
 0x47: (1, 100/255, 0, "%", "Absolute throttle position B"),
 0x48: (1, 100/255, 0, "%", "Absolute throttle position C"),
 0x49: (1, 100/255, 0, "%", "Accelerator pedal position D"),
 0x4A: (1, 100/255, 0, "%", "Accelerator pedal position E"),
 0x4B: (1, 100/255, 0, "%", "Accelerator pedal position F"),
 0x4C: (1, 100/255, 0, "%", "Commanded throttle actuator"),
 0x4D: (2, 1, 0, "min", "Time run with MIL on"),
 0x4E: (2, 1, 0, "min", "Time since codes cleared"),
 0x51: ("text", "Fuel type"),
 0x52: (1, 100/255, 0, "%", "Ethanol fuel percentage"),
 0x53: (2, 1/200, 0, "kPa", "Absolute EVAP vapor pressure"),
 0x54: (2, 1/1000, -32.768, "kPa", "EVAP vapor pressure (native Pa)"),
 0x59: (2, 10, 0, "kPa", "Fuel rail absolute pressure"),
 0x5A: (1, 100/255, 0, "%", "Relative accelerator pedal position"),
 0x5B: (1, 100/255, 0, "%", "Hybrid battery pack remaining life"),
 0x5C: (1, 1, -40, "degC", "Engine oil temperature"),
 0x5D: (2, 1/128, -210, "deg", "Fuel injection timing"),
 0x5E: (2, 1/20, 0, "L/h", "Engine fuel rate"),
 0x5F: ("text", "Emission requirements"),
 0x4F: ("text", "Maximum values (lambda / O2 V / O2 mA / MAP)"),
 0x50: (1, 10, 0, "g/s", "Maximum MAF"),
 0x55: ("text", "Short term secondary O2 trim (banks 1/3)"),
 0x56: ("text", "Long term secondary O2 trim (banks 1/3)"),
 0x57: ("text", "Short term secondary O2 trim (banks 2/4)"),
 0x58: ("text", "Long term secondary O2 trim (banks 2/4)"),
 0x61: (1, 1, -125, "%", "Demanded engine percent torque"),
 0x64: ("text", "Engine percent torque data (idle + 4 points)"),
 0x66: ("text", "MAF sensors B-E (support bits + 16-bit /32 g/s)"),
 0x67: ("text", "Engine coolant temperature, sensors 2/3"),
 0x68: ("text", "Intake air temperature, sensors 2/3"),
 0x78: ("text", "Exhaust gas temperature bank 1 (support bits + /10 - 40 C)"),
 0x79: ("text", "Exhaust gas temperature bank 2"),
 0x7F: ("text", "Engine run time (extended, 32-bit seconds)"),
 0x8D: (1, 100/255, 0, "%", "Throttle position G"),
 0x8E: (1, 1, -125, "%", "Engine friction torque"),
 0x9B: (4, 100/255, 0, "%", "Diesel exhaust fluid level (byte D)"),
 0xA2: (2, 1/32, 0, "mg/stroke", "Cylinder fuel rate"),
 0xA6: (4, 0.1, 0, "km", "Odometer"),
 0x62: (1, 1, -125, "%", "Actual engine percent torque"),
 0x63: (2, 1, 0, "Nm", "Engine reference torque"),
}

VECTORS = [(0, 0), (255, 255), (128, 0), (17, 34)]


def main() -> int:
    failures = []
    unverified = []

    for pid in sorted(obd_pids.PIDS):
        label = obd_pids.PIDS[pid][0]
        ref = REF.get(pid)
        if ref is None:
            unverified.append("0x%02X (%s): no reference row - add one to "
                              "check_pids.py" % (pid, label))
            continue
        if ref[0] == "text":
            r = decode_pid(pid, b"\x02\x10\x00\x00\x00\x00\x00\x00")
            if not (isinstance(r, tuple) and isinstance(r[1], str)):
                failures.append("0x%02X (%s): expected text, got %r"
                                % (pid, label, r))
            continue
        nbytes, scale, offset, _unit, _name = ref
        for a, b in VECTORS:
            raw = (a << 8) | b if nbytes == 2 else a
            if nbytes == 4:
                raw = (a << 24) | (b << 16) | (a << 8) | b
            expected = offset + scale * raw
            if pid == 0x32:      # signed 16-bit
                expected = offset + scale * (raw - 65536 if raw >= 0x8000
                                             else raw)
            if pid == 0x9B:      # DEF level lives in byte D only
                expected = offset + scale * b
            r = decode_pid(pid, bytes([a, b, a, b]))
            if r is None:
                failures.append("0x%02X (%s): decoder returned None for "
                                "%02X %02X" % (pid, label, a, b))
                continue
            _label, value, _unit = r
            if not isinstance(value, (int, float)):
                failures.append("0x%02X (%s): expected a number, got %r"
                                % (pid, label, value))
                continue
            if abs(float(value) - expected) > max(1e-6, abs(expected) * 1e-6):
                failures.append("0x%02X (%s): %r != expected %g "
                                "(raw %d, scale %g, offset %g)"
                                % (pid, label, value, expected, raw,
                                   scale, offset))

    print("PID decoders checked: %d (reference rows: %d)"
          % (len(obd_pids.PIDS), len(REF)))
    for line in unverified:
        print("  UNVERIFIED " + line)
    if failures:
        print("\nFAIL (%d):" % len(failures))
        for line in failures:
            print("  " + line)
        return 1
    print("PASS - all decoders match the J1979 reference.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
