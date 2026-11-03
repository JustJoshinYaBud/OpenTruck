"""OpenTruck - CDL probe: the FIRST deliberate Cat Data Link transmission.

Purpose: CDL fault codes (IID 15, requested via IID 82
or read as PID 0x82) and identity on demand both need us to ASK. The request
formats are now evidence-backed:

  identity read, wire-verified on a Challenger ML98B:
      [req MID][target MID][0x60][iid][sub]     (sub-less form: [.. 0x20][iid])
      reply: [target][req][iid][sub][len][ASCII]
  diagnostic codes, documented in CAT's CCM protocol manual (REHS/SEBU7014):
      IID 82 request: [.. ][0x82][len][unit][interval][format][cs]
        -> IID 15 status reply, then packed codes broadcast every 5 s:
           [CID 16-bit][FMI 8-bit] pairs, max 9 codes
      also readable as a single parameter: PID 0x0082 via IID 24 / a 0x60 read.

FRAMING RESOLVED: the CA3's SendMessage for the 'CAT' protocol
takes the raw message bytes [src][dst][iid][data] - no checksum, no length
prefix - wire-proven on the C6.6 aux engine (reply in ~31 ms). The
ladder below stays for regression and for adapters other than the CA3.

  1. framing ladder for the ML98B-verified identity model request
     [0B][24][0x60][0xF8][0x1C]  (we present as MID 11 "Communication Adapter"
     - the natural ID for an adapter-driven tool; NOT 13, which is ET and may
     collide with an onboard poller). Variants: raw bytes as observed on RX;
     + trailing 2's-complement checksum; J1708-style length prefix; both.
  2. listens several seconds after every attempt and prints EVERYTHING that
     arrives, so a reply, a NACK or silence are all readable evidence.
  3. on the first working framing: reads model/serial/part/build date, then
     tries the diagnostic-code reads (PID/iid 0x82 forms) and listens long.

Safety: READ requests only - EXCEPT the documented code-clear experiment
(--clear, owner-approved): an IID 34 write to PID 0x000D "Remote Fault Reset"
with the documented value 0xFF ("reset all diagnostic codes"), the same
documented service action Cat ET performs. No security/login, no parameter
writes, nothing toward SRS/airbag. All other transmitted strings are
<= 7 bytes of verified shape.

Usage:
    python cdl_probe.py --adapter CA3rp32
    python cdl_probe.py --adapter CA3rp32 --framing raw   # one variant only
    python cdl_probe.py --adapter CA3rp32 --clear         # documented clear test
    python cdl_probe.py --adapter CA3rp32 --sweep         # the APP's poll path,
        # live: CdlSession.set_sender + poll_tick (identity + codes on EVERY
        # discovered module), the exact code the GUI runs on a CAT adapter.
"""
from __future__ import annotations

import argparse
import datetime
import os
import sys
import time

import connectlog
from rp1210 import get_adapter
from adapter_check import make_source
from modules.cdl import CDLMessage, cdl_mid_name, describe_iid, IDENTITY_FIELDS

# The requests, modeled on the observed ML98B service-tool exchange.
OUR_MID = 0x0B       # 11 = "Communication Adapter" (CAT's name for us)
ENGINE = 0x24         # 36 = Engine Control #1

IDENT_READS = [
    ("model", [0x60, 0xF8, 0x1C]),
    ("serial", [0x60, 0xF8, 0x10]),
    ("part number", [0x60, 0xF8, 0x14]),
    ("build date", [0x20, 0x86]),
]
# Diagnostic-code read attempts, in the same request shapes. PID 0x82 is the
# documented "Diagnostic Codes" parameter (packed [CID hi][CID lo][flags+FMI]...).
CODE_READS = [
    ("codes via 0x60 read, iid 0x82 sub 0", [0x60, 0x82, 0x00]),
    ("codes via 0x60 read, iid 0x82 sub 1", [0x60, 0x82, 0x01]),
    ("codes via 0x20 read, iid 0x82", [0x20, 0x82]),
]

# Documented code clear (CAT CCM manual SEBU7014, "Diagnostic Codes - Clear"):
# an IID 34 write to PID 0x000D "Remote Fault Reset", value 0xFF = "reset
# all diagnostic codes"; the CCM answers with IID 35. The manual's own
# examples use the CCM's $50-preamble protocol (with length/format/unit); this
# engine speaks the leaner [src][dst][IID] form, so the PID width inside the
# write body is the one unknown. Ladder: engine-wire analog of our working
# reads first (1-byte PID), manual-faithful form second (2-byte PID). Each
# attempt is verified by re-reading PID 0x0082 before the next is tried, and
# the documented "one IID 34 per second" pacing is respected.
CLEAR_BODY = [
    ("IID 34 write, 1-byte PID form (engine-wire analog)",
     bytes([0x34, 0x0D, 0xFF])),
    ("IID 34 write, 2-byte PID form (manual-faithful)",
     bytes([0x34, 0x00, 0x0D, 0xFF])),
]


def checksum(msg: bytes) -> int:
    """2's complement of the byte sum, so that all bytes + cs == 0 (mod 256)."""
    return (-sum(msg)) & 0xFF


def framing_variants(msg: bytes) -> list[tuple[str, bytes]]:
    return [
        ("raw", msg),
        ("raw+checksum", msg + bytes([checksum(msg)])),
        ("len-prefixed", bytes([len(msg)]) + msg),
        ("len+checksum", bytes([len(msg)]) + msg + bytes([checksum(msg)])),
    ]


def request_bytes(iid_block: list[int]) -> bytes:
    """[our MID][engine MID][iid][sub...] - the observed engine request shape."""
    return bytes([OUR_MID, ENGINE] + iid_block)


def drain(src, seconds: float, out, t0) -> list[CDLMessage]:
    """Read for `seconds`, log and return every decoded CDL message."""
    got: list[CDLMessage] = []
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        f = src.read_frame()
        if f is None:
            time.sleep(0.01)
            continue
        got.append(f)
        line = "%7.0fms  %s" % ((time.monotonic() - t0) * 1000,
                                f.raw.hex(" ").upper())
        if f.dest == OUR_MID:
            line += "   <- addressed to US"
        print("   RX " + line)
        out.write(line + "\n")
    return got


def send(src, data: bytes) -> None:
    """Transmit raw bytes on the CDL client via the 32-bit bridge."""
    resp = src._call({"op": "send_message", "data": data.hex()})
    print("   TX %s -> rc %s" % (data.hex(" ").upper(), resp.get("rc")))
    connectlog.write("CDL TX %s -> rc %s" % (data.hex().upper(), resp.get("rc")))


def read_codes(src, out, t0) -> list[CDLMessage]:
    """Documented PID 0x0082 read; returns the reply payload(s) addressed to us."""
    send(src, request_bytes([0x20, 0x82]))
    got = drain(src, 4.0, out, t0)
    return [m for m in got if m.dest == OUR_MID and m.iid == 0x82]


def _sweep(args) -> None:
    """Live test of the app's CDL poll path: the SAME session
    code the GUI runs - CdlSession.handle for passive discovery, then
    set_sender + poll_tick at the app's 400 ms pacing - against every CDL
    module the machine exposes. Read requests only. Prints each module's
    wire-read identity and decoded fault log at the end.
    """
    from modules.cdl import (CdlSession, cdl_fmi_name, cdl_mid_name,
                             describe_iid)

    a = get_adapter(args.adapter)
    src = make_source(a, "CAT", claim=False)
    src.connect()
    print("connected to %s via the CAT protocol - session sweep" % a.name)

    os.makedirs("raw captures", exist_ok=True)
    stamp = datetime.datetime.now().strftime("%d-%m-%Y_%H.%M.%S")
    path = os.path.join("raw captures", "cdl_sweep_%s.log" % stamp)
    out = open(path, "w", encoding="utf-8")
    out.write("# CDL session sweep (the app's poll path, live)\n")
    t0 = time.monotonic()

    session = CdlSession()

    def _send(data: bytes) -> int:
        resp = src._call({"op": "send_message", "data": data.hex()})
        rc = int(resp.get("rc", -1))
        line = "%7.0fms  TX %s -> rc %s" % ((time.monotonic() - t0) * 1000,
                                           data.hex(" ").upper(), rc)
        print("   " + line)
        out.write(line + "\n")
        return rc

    session.set_sender(_send)

    last_tick = 0.0
    deadline = t0 + args.seconds
    while time.monotonic() < deadline:
        now = time.monotonic()
        if now - last_tick >= 0.4:          # the app's timer interval
            session.poll_tick()
            last_tick = now
        f = src.read_frame()
        if f is None:
            time.sleep(0.01)
            continue
        session.handle(f)
        line = "%7.0fms  %s" % ((time.monotonic() - t0) * 1000,
                                f.raw.hex(" ").upper())
        if f.dest == 0x0B:
            line += "   <- addressed to US"
        print("   RX " + line)
        out.write(line + "\n")

    print("\n=== session sweep results (%d message(s)) ===" % session.messages)
    for mid in sorted(session.modules):
        mod = session.modules[mid]
        print("\n[%s]" % cdl_mid_name(mid))
        print("  " + mod.describe())
        for d in mod.active_dtcs:
            print("    CODE  %s-FMI %d  %s - %s  (flags byte 0x%02X)"
                  % (d["num"], d["fmi"], d["desc"],
                     cdl_fmi_name(d["fmi"]), d["occ"]))
        if not mod.active_dtcs:
            print("    (no codes reported)")
    print("\nFull transcript: %s" % path)
    connectlog.write("CDL sweep transcript: %s" % path)
    src.close()
    out.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--adapter", default="CA3rp32")
    ap.add_argument("--seconds", type=float, default=4.0,
                    help="listen window after each transmit (default 4 s)")
    ap.add_argument("--framing", choices=["raw", "raw+checksum",
                                          "len-prefixed", "len+checksum"],
                    help="use ONE framing variant only (default: the ladder)")
    ap.add_argument("--clear", action="store_true",
                    help="documented code-clear experiment: IID 34 write to "
                         "PID 0x000D (Remote Fault Reset, 0xFF), verified by "
                         "re-reading PID 0x0082. The ONLY write this probe sends.")
    ap.add_argument("--sweep", action="store_true",
                    help="live test of the APP's poll path: run CdlSession "
                         "(set_sender + poll_tick, the exact shipped code) "
                         "against every discovered module and report identity "
                         "+ fault codes")
    args = ap.parse_args()

    if args.sweep:
        _sweep(args)
        return

    a = get_adapter(args.adapter)
    src = make_source(a, "CAT", claim=False)
    src.connect()
    print("connected to %s via the CAT protocol, listen + transmit" % a.name)

    os.makedirs("raw captures", exist_ok=True)
    stamp = datetime.datetime.now().strftime("%d-%m-%Y_%H.%M.%S")
    path = os.path.join("raw captures", "cdl_probe_%s.log" % stamp)
    out = open(path, "w", encoding="utf-8")
    out.write("# CDL probe (first deliberate transmission)\n")
    t0 = time.monotonic()

    if not hasattr(src, "_call"):
        raise SystemExit("This probe drives the 32-bit bridge (CAT-family "
                         "adapters are 32-bit-only); no bridge on this source.")

    # --- 0. documented code-clear experiment (owner-approved) ------------
    if args.clear:
        print("=== code-clear experiment (documented: IID 34 -> PID 0x000D, 0xFF) ===")
        print("[1] codes BEFORE the clear")
        before = read_codes(src, out, t0)
        for m in before:
            print("    %s" % m.raw.hex(" ").upper())
        if not before:
            print("    (no codes reported - nothing to clear)")
        time.sleep(1.0)          # documented: max one IID 34 per second
        for name, body in CLEAR_BODY:
            print("\n[%s]" % name)
            send(src, bytes([OUR_MID, ENGINE]) + body)
            got = drain(src, 4.0, out, t0)
            for m in got:
                if m.dest == OUR_MID:
                    print("    response: %s   (%s)" % (m.raw.hex(" ").upper(),
                                                       describe_iid(m.iid)))
            time.sleep(2.0)
            print("[codes re-read after %s]" % name)
            after = read_codes(src, out, t0)
            for m in after:
                print("    %s" % m.raw.hex(" ").upper())
            if not after:
                print(">>> CODES GONE after the clear - path verified")
                break
            if [m.data for m in after] != [m.data for m in before]:
                print(">>> codes CHANGED after the clear (partial clear?)")
            before = after
            time.sleep(1.0)
        print("\nClear experiment complete. Full transcript: %s" % path)
        connectlog.write("CDL clear experiment transcript: %s" % path)
        src.close()
        out.close()
        return

    model_req = request_bytes(IDENT_READS[0][1])

    # --- 1. framing ladder on the identity model read -------------------
    working = None
    if args.framing is None:
        variants = framing_variants(model_req)
    else:
        variants = [(args.framing,
                     dict(framing_variants(model_req))[args.framing])]
    for name, payload in variants:
        print("\n[%s] framing=%s  TX the model-read request" % (name, name))
        send(src, payload)
        got = drain(src, args.seconds, out, t0)
        reply = [m for m in got if m.dest == OUR_MID and m.iid == 0xF8]
        if reply:
            print(">>> REPLY RECEIVED with framing %r - CDL TX works" % name)
            working = name
            break
        print("    (no reply addressed to us)")

    if working is None:
        print("\nNo framing produced a reply addressed to MID %d." % OUR_MID)
        print("Everything heard is logged in", path)
        print("Next steps: inspect the log - the engine may have replied to")
        print("a different MID, NAKed, or the framing may need adaptation.")
        src.close()
        out.close()
        return

    # --- 2. identity sweep with the working framing ---------------------
    print("\n=== identity reads (framing %s) ===" % working)
    for label, iid_block in IDENT_READS:
        payload = dict(framing_variants(request_bytes(iid_block)))[working]
        print("\n[%s] request" % label)
        send(src, payload)
        got = drain(src, 3.0, out, t0)
        for m in got:
            if m.dest == OUR_MID:
                if m.iid == 0xF8 and len(m.data) >= 2:
                    # sub-echo form: [sub][len][ASCII]
                    text = m.data[2:2 + m.data[1]]
                    field = IDENTITY_FIELDS.get((0xF8, m.data[0]))
                elif m.data:
                    # sub-less form: [len][ASCII] (the 0x86 build date)
                    text = m.data[1:1 + m.data[0]]
                    field = IDENTITY_FIELDS.get((m.iid, None))
                else:
                    text, field = b"", None
                text = text.split(b"\x00")[0]
                print("    reply: %s = %r" % (field or "raw", text))

    # --- 3. diagnostic-code reads ---------------------------------------
    print("\n=== diagnostic-code read attempts ===")
    for label, iid_block in CODE_READS:
        payload = dict(framing_variants(request_bytes(iid_block)))[working]
        print("\n[%s] request" % label)
        send(src, payload)
        got = drain(src, 8.0, out, t0)   # codes may come on an interval
        for m in got:
            # Everything addressed to us, plus anything on the code IIDs:
            # 0x82/0x52 = the request echo (hex and decimal readings of the
            # documented "IID 82"), 0x15/0x0F = the documented IID 15 status
            # and packed-code broadcasts (may be dest=0, not addressed to us).
            if m.dest == OUR_MID or m.iid in (0x82, 0x52, 0x15, 0x0F):
                print("    possible codes reply: %s" % m.raw.hex(" ").upper())

    print("\nProbe complete. Full transcript: %s" % path)
    connectlog.write("CDL probe transcript: %s" % path)
    src.close()
    out.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)