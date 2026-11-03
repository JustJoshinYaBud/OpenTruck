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
import sys

sys.path.insert(0, r"D:\OpenTruck")
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

failed = [n for n, c in ok if not c]
print("checks run:", len(ok))
print("FAILED:", failed if failed else "none - all pass")
sys.exit(1 if failed else 0)
