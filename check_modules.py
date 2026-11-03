"""Guard: every module type must survive every SHARED render path.

Origin (2026-11-13, Cat 938 loader, build 151): adding the CDL module type
exposed implicit assumptions in shared code. CdlModule has no ``.name``
attribute; the fault-code table dereferenced it after setRowCount() and
showed the right number of BLANK rows. The report generator and the
live-data table carried the same trap, and the session's live merge
dropped the CDL bucket entirely. Each was a separate fix; this guard
makes sure the family stays fixed.

It instantiates ONE module of every bus type - J1939, J1708, CDL - each
with a fault code and a live value, plus a fake OBD-II state, and drives
every shared path (the 250 ms _refresh, the codes table, the live table,
the report, the activity line, and reader._sync). Any exception, blank
cell or missing bucket fails the guard.
"""
import hashlib
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import config

_TMP = tempfile.mkdtemp()
config._path = lambda: os.path.join(_TMP, "config.json")
# The release-notes popup is MODAL: without this, a fresh config hangs the
# guard (learned the hard way).
config.save({"first_run_done": True, "last_version": "0.3.0.152"})

from PySide6.QtWidgets import QApplication          # noqa: E402
from PySide6.QtCore import QFile, QIODevice          # noqa: E402
from PySide6.QtUiTools import QUiLoader              # noqa: E402

import app as appmod                                  # noqa: E402
import reader as readermod                            # noqa: E402
import updater                                        # noqa: E402
from modules.cdl import CdlModule, decode_codes       # noqa: E402
from modules import j1708 as j1708mod                 # noqa: E402

FAILED = []
CHECKS = [0]


def check(name, fn):
    CHECKS[0] += 1
    try:
        fn()
    except Exception as exc:                          # noqa: BLE001
        FAILED.append("%s: %s: %s" % (name, type(exc).__name__, exc))
        print("FAIL  %s -> %s: %s" % (name, type(exc).__name__, exc))
    else:
        print("ok    %s" % name)


def _code(num, fmi, desc):
    # Same shape the J1939/J1708 decoders produce: no "num" key (the table
    # falls back to str(spn)); CDL replies carry "CID n" from decode_codes.
    return {"spn": num, "fmi": fmi, "occ": fmi & 0x1F, "desc": desc}


def build_window():
    qapp = QApplication.instance() or QApplication([])
    ui = QFile(appmod.UI_PATH)
    ui.open(QIODevice.ReadOnly)
    win = QUiLoader().load(ui)
    ui.close()
    w = appmod.MainWindow(win)
    w._source = object()          # the activity line early-returns without it

    # One module per bus type, each with one active code and one live value.
    eng = readermod.Module(0x00)                       # J1939
    eng.make = "Cummins"
    eng.active_dtcs = [_code(100, 3, "Engine Oil Pressure Sensor")]
    j1587 = j1708mod.J1708Module(128)                  # J1708
    j1587.active_dtcs = [_code(105, 4, "Intake Manifold Temp")]
    cdl = CdlModule(36)                                # CDL
    cdl.identity = {"model": "C6.6"}
    cdl.active_dtcs = decode_codes(bytes([3, 0x00, 0x64, 0x03]))

    # Inject through the SUB-sessions and let _sync build the merged view,
    # exactly like a live connect does (assigning session.modules directly is
    # discarded the next time poll()/_sync() runs).
    s = w.session
    s.j1939.modules = {0x00: eng}
    s.j1708.modules = {128: j1587}
    s.cdl.modules = {36: cdl}
    live = {"Engine Speed": ("1200", "rpm")}
    s.j1939.live = {0x00: dict(live)}
    s.j1708.live = {128: dict(live)}
    s.cdl.live = {36: dict(live)}
    s.vin = ""
    s._sync()
    keys = dict(s.modules)
    assert len(keys) == 3, keys
    return w, keys


def main():
    w, keys = build_window()

    check("codes table renders a row per bus with NO blank cells", lambda: _codes(w))
    check("live table refreshes for every bus type", lambda: _live(w, keys))
    check("report lists codes from every bus type", lambda: _report(w))
    check("reader._sync merges the CDL live bucket", lambda: _sync(w))
    check("250 ms _refresh drives list+codes+live+activity", lambda: _refresh(w))
    check("status label composes notice + activity", lambda: _status(w))
    check("OBD-II state survives codes+live render", lambda: _obd(w))
    # A notice must survive the 250 ms tick, not be wiped by it.
    check("notice survives the activity refresh", lambda: _notice_survives(w))
    check("activity label fills the status bar (no stray separator)",
          lambda: _statusbar_fills(w))
    check("update: GitHub sha256 digest parsed and validated",
          _update_digest)
    check("update: file hash matches hashlib", _update_hash)
    check("update: Smart App Control state readable", _sac_state)
    check("update: Authenticode status mapping", _signature_map)
    # The degF(wire) -> degC(canonical) -> degF(display) chain, on real bytes.
    check("units: degF wire -> degC canonical -> display round-trip", _units)

    print("\nchecks run: %d" % CHECKS[0])
    if FAILED:
        print("FAILED: %d" % len(FAILED))
        for f in FAILED:
            print("  " + f)
        return 1
    print("FAILED: none - all pass")
    return 0


def _update_digest():
    good = "a" * 64
    assert updater.asset_sha256({"digest": "sha256:" + good}) == good
    assert updater.asset_sha256({"digest": "sha512:" + good}) is None
    assert updater.asset_sha256({"digest": "sha256:short"}) is None
    assert updater.asset_sha256({}) is None


def _update_hash():
    path = os.path.join(tempfile.mkdtemp(), "blob.bin")
    with open(path, "wb") as fh:
        fh.write(b"opentruck")
    assert updater.sha256_file(path) == hashlib.sha256(b"opentruck").hexdigest()


def _sac_state():
    assert updater.smart_app_control_state() in (
        "off", "evaluation", "enforced", "unknown")


def _signature_map():
    assert updater._signature_status("Valid") == "valid"
    assert updater._signature_status("NotSigned") == "unsigned"
    assert updater._signature_status("HashMismatch") == "invalid"
    assert updater._signature_status("NotTrusted") == "invalid"
    assert updater._signature_status("garbage") == "unknown"
    assert updater._signature_status("") == "unknown"


def _statusbar_fills(w):
    """The activity label must stretch, not size to its text.

    Qt draws a 1-px separator after each status-bar item. With a text-sized
    label that separator sat mid-bar and moved as the text changed (field
    report: "a random | in the bottom middle"). The addWidget stretch is the
    fix; this fails if it is ever dropped.
    """
    w.win.resize(1000, 700)
    w.win.show()
    QApplication.processEvents()
    sb = w.win.statusBar()
    assert w.lbl_activity.width() > sb.width() * 0.8, (
        "activity label is text-sized (%d of %d)" % (
            w.lbl_activity.width(), sb.width()))


def _codes(w):
    w._obd_state = None
    w._last_table_sig = None
    w._refresh_table()
    t = w.codes_table
    assert t.rowCount() == 3, "expected 3 code rows, got %d" % t.rowCount()
    for r in range(t.rowCount()):
        cells = [t.item(r, c).text() if t.item(r, c) else ""
                 for c in range(t.columnCount())]
        assert cells[0], "blank module cell in row %d" % r
        assert cells[1], "blank bus cell in row %d" % r
        assert cells[2], "blank code cell in row %d" % r
        assert cells[4], "blank description cell in row %d: %r" % (r, cells)
    buses = {(t.item(r, 1).text() or "").upper() for r in range(t.rowCount())}
    assert any("CDL" in b for b in buses), buses


def _live(w, keys):
    for a in keys:
        w._current_addr = a
        w._last_live_sig = None
        w._refresh_live_data()
        t = w.live_table
        assert t.rowCount() >= 1, "no live rows for %s" % w._key_text(a)
        assert t.item(0, 1).text(), "blank live value for %s" % w._key_text(a)


def _report(w):
    rows = w._report_dtcs(active=True)
    assert len(rows) == 3, "report rows: %d" % len(rows)
    for entry in rows:
        assert entry.get("module"), entry
        assert entry.get("description") or entry.get("code"), entry


def _sync(w):
    s = w.session
    s.j1939.live = {0: {"Engine Speed": ("800", "rpm")}}
    s.j1708.live = {128: {"Coolant Temp": ("190", "F")}}
    s.cdl.live = {36: {"Hydraulic Pressure": ("2500", "psi")}}
    s._sync()
    got = s.live.get(readermod.CDL_KEY_BASE + 36, {})
    assert got.get("Hydraulic Pressure") == ("2500", "psi"), got


def _units():
    """The degF->degC conversion happens ONCE, in the decoders (canonical
    degC); ``units.convert`` only maps canonical->display.

    Locked after a 2026-11-16 field report: J1587 transmits
    temperatures in degF (SAE J1587 3.4.1) while the app runs on the
    "Canadian" system, so is the degC display a conversion bug? No - proven
    with the real Ford/Cummins wire bytes: PID 175 raw 848 = 212 degF decodes
    to 100 degC, converts back to 212 degF on the US system, and stays
    100 degC on Canadian/metric. A double conversion would show 212 degC;
    a missing one would show 212 "degC"."""
    from units import convert
    _n, val, unit = j1708mod.decode_pid(175, bytes([0x50, 0x03]))
    assert (val, unit) == ("100", "\u00b0C"), (val, unit)
    assert convert(val, unit, "canadian") == ("100", "\u00b0C")
    assert convert(val, unit, "metric") == ("100", "\u00b0C")
    assert convert(val, unit, "standard") == ("212", "\u00b0F")
    _n, val, unit = j1708mod.decode_pid(110, bytes([0x45]))   # 69 degF wire
    assert convert(val, unit, "standard") == ("69", "\u00b0F")
    # Canadian = metric except pressure/torque/power: pressure converts,
    # temperature must NOT be touched on the metric systems.
    assert convert("99.99", "kPa", "canadian") == ("14.5", "psi")
    assert convert("20.56", "\u00b0C", "canadian") == ("20.56", "\u00b0C")


def _refresh(w):
    w._obd_state = None
    w._last_components = None
    w._first_frame_seen = True
    w._refresh()
    assert w.component_list.count() == 3, \
        "component list: %d" % w.component_list.count()
    assert w.codes_table.rowCount() == 3
    assert w.lbl_activity.text(), "activity line empty"


def _status(w):
    w._activity.clear()
    w._set_activity("modules", "3 modules identified")
    w._notice("0x00: NACK - response pending", 60.0)
    text = w.lbl_activity.text()
    assert "NACK" in text and "3 modules identified" in text, text
    w._status_notice = None


def _notice_survives(w):
    w._notice("test notice", 60.0)
    w._refresh_activity()
    assert "test notice" in w.lbl_activity.text(), \
        "the 250 ms tick wiped the notice: %r" % w.lbl_activity.text()
    w._status_notice = None


def _obd(w):
    w._obd_state = {"live": {"Engine RPM": ("1200", "rpm")},
                    "live_by_ecu": {}, "codes": [], "pending": [],
                    "permanent": [], "ecus": [0x7E8], "ecu_names": {},
                    "uds": []}
    w._obd_selected = None
    w._last_live_sig = None
    w._last_table_sig = None
    w._refresh_table()
    w._refresh_live_data()
    w._obd_state = None


if __name__ == "__main__":
    sys.exit(main())
