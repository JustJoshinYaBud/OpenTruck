"""OpenTruck - adapter capability sweep ("Developer > Check Adapter").

Answers the question a failed connect cannot answer by itself: **which of the
things an adapter claims to speak actually work on this vehicle right now?**

A connect attempt hides too much. `J1939:Baud=Auto` can be ACCEPTED by the
driver and still deliver nothing (auto-baud never synced); a raw-CAN client can
see a lively bus while the J1939 client is silent; a Caterpillar machine can put
everything on the CAT Data Link and nothing on J1939; and a driver that only
serves one session can be knocked out by a second client. Each of those has the
same symptom - "it won't connect" - and a different fix.

So this sweeps every vehicle protocol the vendor INI declares for the device,
ONE CLIENT AT A TIME (closing each before the next, which also makes it safe on
a single-session adapter), and for each one records:

  * did ClientConnect accept it (and which exact string the driver settled on),
  * did the filter command work,
  * did any bytes arrive in the dwell window, and
  * a decoded sample of what did arrive (J1939 PGN + source, raw CAN id, J1708
    MID).

Results go to the connection log (Help > Error logs) plus a readable capture
file under `<log root>/raw captures/adapter_check_<date>.log`, so the evidence
can be mailed in without asking the user to read anything back to us.

Usage:
    python adapter_check.py                      # all adapters installed
    python adapter_check.py --adapter CA3rp32    # one adapter
    python adapter_check.py --adapter CA3rp32 --seconds 4 --claim
"""
from __future__ import annotations

import argparse
import datetime
import os
import time
from typing import Callable, Optional

import connectlog
from rp1210 import (
    BridgedRP1210Source, RP1210Source, get_adapter, list_adapters,
    protocol_options, usb_driver_problems,
)

DEFAULT_SECONDS = 2.5


def make_source(a, protocol: str, claim: bool = True):
    """A source for one sweep step (in-process, or via the 32-bit bridge).

    ``claim=False`` keeps the client listen-only, exactly like the app's raw
    capture channel; ``claim=True`` exercises the real connect path including
    the J1939 address-claim command, which is where a driver can refuse.

    ``ladder=False`` is deliberate: each sweep step is ONE protocol string, so
    "J1939:Baud=250" in the report means exactly that string and nothing else
    (the ladder's other rates are separate steps).
    """
    if a.dll_path:
        return RP1210Source(a.dll_path, protocol, a.device_id,
                            passive=not claim, ladder=False)
    return BridgedRP1210Source(a.bridge_dll, protocol, a.device_id,
                               passive=not claim, ladder=False)


def describe(buffer_hex: str, protocol: str) -> str:
    """A short human label for one received RP1210 buffer."""
    try:
        b = bytes.fromhex(buffer_hex)
    except ValueError:
        return buffer_hex[:32]
    p = protocol.upper()
    if p.startswith("J1939") and len(b) > 10:
        pgn = int.from_bytes(b[4:7], "little")
        sa = b[8]
        try:
            from lookup.pgn import pgn_name
            name = pgn_name(pgn)
        except Exception:                     # noqa: BLE001
            name = ""
        return (f"PGN {pgn:#06x} src 0x{sa:02X} {name}".rstrip())
    if p.startswith("CAN") and len(b) >= 9 and b[4] in (0, 1):
        if b[4] == 1:
            can_id = int.from_bytes(b[5:9], "big")
            return f"29-bit id 0x{can_id:08X} {b[9:].hex().upper()}"
        can_id = int.from_bytes(b[5:7], "big")
        return f"11-bit id 0x{can_id:03X} {b[7:].hex().upper()}"
    if p.startswith("J1708"):
        try:
            from modules.j1708 import from_rp1210_buffer
            msg = from_rp1210_buffer(b, len(b))
            if msg is not None:
                return f"MID {msg.mid} ({len(msg.raw)} bytes)"
        except Exception:                     # noqa: BLE001
            pass
    return buffer_hex[:40]


def probe(a, protocol: str, seconds: float = DEFAULT_SECONDS,
          claim: bool = True) -> dict:
    """Open one client, listen for `seconds`, close it. Never raises."""
    entry: dict = {
        "protocol": protocol, "opened": False, "used": "", "ms": 0,
        "count": 0, "error": "", "samples": [], "labels": [],
    }
    src = None
    started = time.perf_counter()
    try:
        src = make_source(a, protocol, claim=claim)
        src.connect()                     # filters (and the claim, if enabled)
        entry["opened"] = True
        entry["used"] = getattr(src, "_protocol", protocol)
    except Exception as exc:              # noqa: BLE001 - a sweep never aborts
        entry["error"] = str(exc)
        entry["ms"] = int((time.perf_counter() - started) * 1000)
        connectlog.write("check %-22s -> FAILED in %d ms: %s"
                         % (protocol, entry["ms"], str(exc).replace("\n", " | ")))
        if src is not None:
            try:
                src.close()
            except Exception:             # noqa: BLE001
                pass
        return entry

    entry["ms"] = int((time.perf_counter() - started) * 1000)
    deadline = time.perf_counter() + seconds
    labels: list[str] = []
    while time.perf_counter() < deadline:
        try:
            raw = src.read_raw_hex()
        except Exception as exc:          # noqa: BLE001
            entry["error"] = f"read failed: {exc}"
            break
        if raw:
            entry["count"] += 1
            if len(entry["samples"]) < 6:
                entry["samples"].append(raw)
                labels.append(describe(raw, protocol))
        else:
            time.sleep(0.01)
    entry["labels"] = labels
    connectlog.write(
        "check %-22s -> open (%s) %d ms, %d message(s) in %.1f s%s"
        % (protocol, entry["used"], entry["ms"], entry["count"], seconds,
           (": " + "; ".join(labels[:3])) if labels else ""))
    try:
        src.close()
    except Exception:                     # noqa: BLE001
        pass
    return entry


def sweep(a, protocols: Optional[list[str]] = None, seconds: float = DEFAULT_SECONDS,
          claim: bool = True, out_dir: Optional[str] = None,
          progress: Optional[Callable[[str], None]] = None) -> dict:
    """Sweep one adapter and write a readable report. Never raises.

    Returns {"adapter": AdapterInfo, "results": [entry, ...], "path": str}.
    """
    if protocols is None:
        protocols = protocol_options(a.ini_path, a.device_id)
    log = progress or (lambda _msg: None)
    header = [
        "=== adapter check %s ===" % datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        "adapter: %s [%s]  rp1210 revision: %s  clients: %s"
        % (a.name, a.code, a.revision or "(not declared)",
           "one at a time" if a.single_client else "multi"),
        "driver: %s" % (a.dll_path or ("32-bit bridge: " + (a.bridge_dll or "missing"))),
        "device id: %s  claim address: %s" % (a.device_id, "yes" if claim else "no"),
        "protocols: %s" % ", ".join(protocols),
        "",
    ]
    for line in header:
        connectlog.write(line)
    results: list[dict] = []
    for i, protocol in enumerate(protocols, 1):
        log(f"Checking {protocol} ({i}/{len(protocols)})...")
        results.append(probe(a, protocol, seconds=seconds, claim=claim))

    lines = header + ["%-24s %-8s %6s %8s  %s"
                      % ("protocol", "result", "ms", "messages", "sample")]
    for r in results:
        if r["opened"]:
            state = "open"
        elif r["error"]:
            state = "refused"
        else:
            state = "failed"
        sample = r["labels"][0] if r["labels"] else ""
        lines.append("%-24s %-8s %6d %8d  %s"
                     % (r["protocol"], state, r["ms"], r["count"], sample))
        if r["error"]:
            for part in r["error"].splitlines():
                lines.append("%-24s   %s" % ("", part.strip()))
    lines.append("")

    # A plain-language verdict, so the report is useful without an engineer.
    heard = [r for r in results if r["count"]]
    opened = [r for r in results if r["opened"]]
    if heard:
        j1939 = [r for r in heard if r["protocol"].upper().startswith("J1939")]
        can = [r for r in heard if r["protocol"].upper().startswith("CAN")]
        other = [r for r in heard if r not in j1939 and r not in can]
        if j1939:
            lines.append("VERDICT: the adapter is reading J1939 traffic "
                         "(use %s)." % j1939[0]["used"])
        elif can:
            lines.append("VERDICT: CAN traffic is present but the J1939 client "
                         "delivered nothing - the driver's J1939 layer, not the "
                         "wiring, is the problem.")
        else:
            lines.append("VERDICT: traffic arrived on %s only - this vehicle "
                         "is not broadcasting on J1939."
                         % ", ".join(r["protocol"] for r in other or heard))
    elif opened:
        lines.append("VERDICT: the adapter accepted %d protocol(s) but NO "
                     "vehicle data arrived on any of them. Check the key is ON, "
                     "the cable is in the right connector, and try again."
                     % len(opened))
    else:
        lines.append("VERDICT: no client could be opened at all. The adapter is "
                     "not usable: re-seat it, close other diagnostic software, "
                     "and unplug/replug the USB cable.")

    # When NOTHING opened, ask Windows before blaming the adapter: a driver
    # the OS refuses to load (Memory Integrity blocking the 2016 CAT CA3 USB
    # driver on clean-install Windows 11, say) looks EXACTLY like this - and
    # the fix is a setting, not a cable. Live case: 2026-11-13.
    if not heard and not opened:
        for finding in usb_driver_problems():
            lines.append("WINDOWS: " + finding)

    path = "(could not write a report file)"
    try:
        base = out_dir or os.path.join(os.getcwd(), "raw captures")
        os.makedirs(base, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%d-%m-%Y_%H.%M.%S")
        path = os.path.join(base, f"adapter_check_{stamp}.log")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    except OSError:
        pass
    connectlog.write("adapter check report: %s" % path)
    connectlog.write(lines[-1])
    return {"adapter": a, "results": results, "path": path}


def summary(report: dict) -> str:
    """Dialog-ready text for a finished sweep."""
    a = report["adapter"]
    results = report["results"]
    heard = [r for r in results if r["count"]]
    opened = [r for r in results if r["opened"]]
    rows = []
    for r in results:
        if r["opened"]:
            rows.append("%-22s  %s  (%d msg)" % (
                r["protocol"], "data" if r["count"] else "open, no data",
                r["count"]))
        else:
            rows.append("%-22s  refused" % r["protocol"])
    if heard:
        verdict = ("Vehicle data arrived on %d protocol(s) - the adapter and "
                   "the wiring are working." % len(heard))
    elif opened:
        verdict = ("The adapter opened, but no vehicle data arrived on any "
                   "protocol. Check the key is ON and the cable is in the "
                   "diagnostic connector.")
    else:
        verdict = ("No protocol could be opened. Re-seat the adapter, close "
                   "any other diagnostic program, and replug the USB cable.")
    return (
        f"{a.name} [{a.code}]\n"
        f"{verdict}\n\n"
        + "\n".join(rows)
        + f"\n\nFull detail was written to:\n{report['path']}\n"
          f"(also in Help > Error logs)"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--adapter", help="vendor code, e.g. CA3rp32 (default: all)")
    ap.add_argument("--seconds", type=float, default=DEFAULT_SECONDS,
                    help=f"listen time per protocol (default {DEFAULT_SECONDS})")
    ap.add_argument("--claim", action="store_true",
                    help="claim a J1939 address (the real connect path)")
    ap.add_argument("--all", action="store_true",
                    help="also try light-duty protocols from the vendor INI")
    ap.add_argument("--out", help="report folder (default: <cwd>/raw captures)")
    args = ap.parse_args()

    adapters = list_adapters()
    if args.adapter:
        a = get_adapter(args.adapter)
        if a is None:
            raise SystemExit("Adapter %r not found. Installed: %s"
                             % (args.adapter, [x.code for x in adapters]))
        adapters = [a]
    if not adapters:
        raise SystemExit("No RP1210 adapter with a driver is installed.")

    for a in adapters:
        protocols = protocol_options(a.ini_path, a.device_id,
                                     all_protocols=args.all)
        print(f"\n=== {a.name} [{a.code}] -> {', '.join(protocols)} ===")
        report = sweep(a, protocols, seconds=args.seconds, claim=args.claim,
                       out_dir=args.out, progress=lambda m: print("  " + m))
        print(summary(report))


if __name__ == "__main__":
    main()
