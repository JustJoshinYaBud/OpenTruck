"""OpenTruck - PySide6 GUI.

The window layout lives in `MainWindow.ui` (load it and edit visually with Qt
Designer / `designer.exe`). This file only wires widgets (looked up by
objectName) to the J1939 session — so you can restyle/relayout in Designer
without touching Python.

Layout:
    top toolbar  (Connect / Clear faults)
    left         Vehicle panel + component list (Engine, Transmission, Brakes…)
    centre       Fault-codes table, with a live-data list below

Run:
    python app.py                    # simulator (no hardware)
    python app.py --rp1210           # live via an RP1210 adapter
    python app.py --replay FILE      # replay a log
"""
from __future__ import annotations

import ctypes
import json
import os
import sys
import threading
import time
from datetime import datetime
from typing import Callable, Optional

from version import __version__, full_version

from PySide6.QtCore import Qt, QFile, QIODevice, QObject, QThread, Signal, QTimer, QRect
from PySide6.QtGui import QAction, QColor, QIcon, QPen, QPainter, QPainterPath
from PySide6.QtNetwork import (
    QNetworkAccessManager, QNetworkRequest, QNetworkReply,
)
from PySide6.QtCore import QUrl as _QUrl
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QAbstractItemView,
    QFileDialog, QMessageBox, QDialog, QComboBox, QLineEdit, QPushButton,
    QSplitter, QSizePolicy, QProgressDialog,
    QVBoxLayout, QHBoxLayout, QFormLayout, QDialogButtonBox,
)

from modules.j1939 import (Frame, PGN, FUNCTION_NAMES, function_name,
                            preferred_address_name)
from lookup.spn import fmi_name
from lookup.oem import resolve_code_description, resolve_live_label
from framesource import FrameSource, LoggingSource, ReplaySource, CombinedSource
from simsource import SimulatorSource
from reader import TOOL_ADDRESS, CombinedSession, J1708_KEY_BASE
from modules.j1708 import (
    J1587_TOOL_MID, build_clear_request,
    PID_VIN, PID_COMPONENT_ID, PID_SOFTWARE_ID,
    J1587_REQUESTER_MID, build_request, build_broadcast_request,
)
from prefdialog import PreferencesDialog, FirstRunDialog
from reportgen import generate_report
from lookup.manufacturers import manufacturer_name, friendly_make
from modules.uds import find_vin as uds_find_vin
from modules.obd2 import open_session
from lookup.obd_dtcs import obd_dtc_description
from lookup.obd_dtcs_mfg import mfg_dtc_description
from lookup.vin import wmi_make, model_year, decode_vin_vpic
from lookup.obd_aft_positions import (
    egt_positions, label_overrides, neutral_egt_label,
)
from units import convert
from config import (
    last_source, set_last_source,
    units, set_units, log_dir, set_log_dir,
    ui_layout, set_ui_layout,
    first_run_done, set_first_run_done,
)
from updater import (RELEASES_URL, current_version, find_setup_asset,
                     pick_latest_release, release_version)

# Gap (ms) between the DM11 (clear-active) and DM3 (clear-stored) clear
# requests. ECUs need a moment to finish processing DM11 — including any ABS
# self-test / re-init it triggers — before the stored-code clear lands. 700 ms
# gives them that time without stalling the GUI thread.
CLEAR_DM11_DM3_GAP_MS = 700


# Global dark theme. Applied in main() so the whole
# UI (tables, menus, dialogs and the live-data graph) shares one dark palette.
DARK_STYLESHEET = """
QMainWindow, QDialog { background-color: #2b2b2b; color: #e0e0e0; }
QWidget { background-color: #2b2b2b; color: #e0e0e0; }

QRadioButton, QCheckBox { color: #e0e0e0; background: transparent; }
QRadioButton::indicator {
    width: 15px; height: 15px; border-radius: 8px;
    border: 1px solid #999999; background-color: #1e1e1e;
}
QRadioButton::indicator:checked {
    background-color: #2ecc71; border: 1px solid #2ecc71;
}
QCheckBox::indicator {
    width: 15px; height: 15px; border-radius: 3px;
    border: 1px solid #999999; background-color: #1e1e1e;
}
QCheckBox::indicator:checked {
    background-color: #2ecc71; border: 1px solid #2ecc71;
}
QFrame { border: none; }

QGroupBox {
    background-color: #262626;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    margin-top: 10px;
    padding: 8px 4px 4px 4px;
    color: #e0e0e0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 3px;
    color: #9ecbff;
}

QLabel { color: #e0e0e0; background: transparent; }

QTableWidget, QListWidget {
    background-color: #1e1e1e;
    alternate-background-color: #242424;
    color: #e0e0e0;
    gridline-color: #333333;
    border: 1px solid #3a3a3a;
}
QTableWidget::item, QListWidget::item { padding: 2px; }
QTableWidget::item:selected, QListWidget::item:selected {
    background-color: #2d5a8a;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #333333;
    color: #e0e0e0;
    border: 1px solid #3a3a3a;
    padding: 4px;
}

QPushButton {
    background-color: #3a3a3a;
    color: #e0e0e0;
    border: 1px solid #555555;
    border-radius: 3px;
    padding: 4px 12px;
}
QPushButton:hover { background-color: #464646; }
QPushButton:pressed { background-color: #2b2b2b; }
QPushButton:disabled { color: #777777; }

QMenuBar { background-color: #2b2b2b; color: #e0e0e0; }
QMenuBar::item:selected { background-color: #3a3a3a; }
QMenu { background-color: #2b2b2b; color: #e0e0e0; border: 1px solid #3a3a3a; }
QMenu::item:selected { background-color: #3a3a3a; }

QStatusBar { background-color: #2b2b2b; color: #9a9a9a; }

QComboBox {
    background-color: #1e1e1e;
    color: #e0e0e0;
    border: 1px solid #555555;
    padding: 2px 6px;
}
QComboBox QAbstractItemView {
    background-color: #1e1e1e;
    color: #e0e0e0;
    selection-background-color: #2d5a8a;
}

QLineEdit {
    background-color: #1e1e1e;
    color: #e0e0e0;
    border: 1px solid #555555;
    padding: 2px 6px;
}
"""


def _log_root() -> str:
    """Base folder for saved captures/logs.

    Installed / frozen builds write to a per-user writable location
    (``%LOCALAPPDATA%\\OpenTruck``) so logging works even when the app is
    installed under a read-only Program Files directory. Source checkouts write
    alongside the project files. The callers' ``os.makedirs(..., exist_ok=True)``
    creates the subfolders on demand.

    Frozen build:  ``%LOCALAPPDATA%\\OpenTruck\\raw captures``, ``...\\vehicle logs``
    Source check:  ``<project>/raw captures``, ``<project>/vehicle logs``

    A user-chosen folder (set in Preferences) takes precedence over both.
    """
    configured = log_dir()
    if configured:
        return configured
    if getattr(sys, "frozen", False):
        base = os.path.join(
            os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
            "OpenTruck",
        )
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return base


def _slug(text: str) -> str:
    """Lowercase a name into a filename-safe token, '_'-separated."""
    out: list[str] = []
    prev_sep = False
    for ch in text.lower():
        if ch.isalnum():
            out.append(ch)
            prev_sep = False
        elif not prev_sep:
            out.append("_")
            prev_sep = True
    return "".join(out).strip("_") or "vehicle"


def _timestamp() -> str:
    """'DD-MM-YYYY_HH.MM.SS' — the time part of capture/log filenames."""
    return datetime.now().strftime("%d-%m-%Y_%H.%M.%S")


def _resource_path(name: str) -> str:
    """Locate a bundled data file, whether running from source or frozen by
    PyInstaller (which extracts bundled data into `sys._MEIPASS`)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


UI_PATH = _resource_path("MainWindow.ui")
ICON_PATH = _resource_path("icon.ico")

# PGNs we poll (one per discovery tick) once connected. Address claims + DM
# make the modules/faults appear; CI/VI fill in make/model/serial and the VIN.
DISCOVERY_PGNS = (PGN.ADDRESS_CLAIMED, PGN.DM1, PGN.DM2, PGN.CI, PGN.VI,
                  PGN.SOFTWARE_ID, PGN.ECU_ID)

# Identification PGNs swept by source-address to catch "silent" ECUs — ones
# that never broadcast an address-claim but may still hold the VIN (VI) or
# component identification (CI) and only answer a request addressed to them
# directly (the same directed-only behaviour Caterpillar ECMs show).
IDENTIFICATION_PGNS = (PGN.VI, PGN.CI, PGN.SOFTWARE_ID, PGN.ECU_ID)

# Source-address sweep range. J1939 ECUs may claim 0x00-0xFD (0-253); our own
# tool address (0xF9) is skipped, and 0xFE/0xFF are null/global, not real ECUs.
SWEEP_START, SWEEP_END = 0x00, 0xFD

# Pacing for the one-shot address sweep: send one address's worth of requests
# every SWEEP_TICK_MS, so the ~250 directed requests trickle out over ~5 s
# instead of flooding the bus (burst requests can overflow the adapter's
# receive queue, which silently drops frames).
SWEEP_TICK_MS = 20

# How often (in 1 s discovery ticks) to re-request the J1708 identification PIDs
# (VIN / component-id / software-id) from every module while still missing.
J1708_IDENT_EVERY = 3

# Tier 3 of the identification sequence (after J1939 VI and the J1587
# identification requests): fire the one-shot
# UDS VIN probe (DID 0xF190) after this many 1 s discovery ticks, and only while
# the VIN is still missing. It exists for J1939-only trucks (no J1708 bus at all)
# whose ECUs decline the J1939 VI PGN - on those, UDS is the only path left.
UDS_VIN_AFTER_TICKS = 10

# How long (ms) the vehicle may stay silent while connected before we declare
# the link lost. Normal J1939 broadcasts arrive every 10-100 ms (plus our own
# 1 s discovery poll), so 5 s of total silence means the bus/adapter has gone.
WATCHDOG_MS = 5000

# After a DTC clear, some ECUs (notably ABS) re-run their self-test and briefly
# stop broadcasting. Suppress the lost-link watchdog for this long after the
# last clear request so that self-test silence isn't mistaken for a disconnect.
CLEAR_WATCHDOG_GRACE_MS = 8000

# When a clear is refused because the engine is running, hold the link alive for
# this long so the key-off / key-on cycle needed to shut the engine down is not
# reported as a dropped connection. If the key comes back on within this window
# the link resumes silently; leave it silent longer and we report a lost link.
ENGINE_OFF_GRACE_MS = 10000


class FrameReader(QObject):
    """Runs on a background QThread, emitting each received frame."""
    frame = Signal(object)      # a j1939.Frame
    error = Signal(str)

    def __init__(self, source: FrameSource) -> None:
        super().__init__()
        self._source = source
        self._stop = False

    def request_stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        # NOTE: source.connect() is done synchronously in MainWindow._connect()
        # so a connect failure can be surfaced in the connection dialog; the
        # worker thread only reads frames.
        try:
            while not self._stop:
                f = self._source.read_frame()
                if f is None:
                    time.sleep(0.002)
                    continue
                self.frame.emit(f)
        except Exception as e:                # noqa: BLE001
            self.error.emit(str(e))
        finally:
            try:
                self._source.close()
            except Exception:                 # noqa: BLE001
                pass


class ConnectionDialog(QDialog):
    """Modal chooser for the J1939 source.

    On a failed connect it stays open and shows the error, so the user can fall
    back to the simulator or a different interface without reopening anything.
    """

    def __init__(self, parent, adapters,
                 last_source: Optional[str] = None,
                 on_connect: Optional[Callable[[str, Optional[str]], None]] = None) -> None:
        super().__init__(parent)
        self._on_connect = on_connect
        self.setWindowTitle("Connect to Vehicle")
        self.setMinimumWidth(440)

        # Installed RP1210 adapters first, then simulator / replay fallbacks.
        # Adapters whose driver only ships a 32-bit DLL are still listed and
        # selectable - they are driven via the out-of-process 32-bit bridge.
        self.combo = QComboBox()
        for a in adapters:
            label = a.name + ("  (32-bit driver)" if a.bridge_dll and not a.dll_path else "")
            self.combo.addItem(label, ("rp1210", a.code))
        self.combo.addItem("Simulator (Demo, no hardware)", ("sim", None))
        self.combo.addItem("Replay Log File\u2026", ("replay", None))

        # Preselect the last-used source when it is still present.
        if last_source is not None:
            for i in range(self.combo.count()):
                kind, arg = self.combo.itemData(i)
                if (kind == "rp1210" and arg == last_source) or \
                        (kind in ("sim", "replay") and kind == last_source):
                    self.combo.setCurrentIndex(i)
                    break

        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("Choose a replay log file\u2026")
        self.browse_btn = QPushButton("Browse\u2026")
        self.browse_btn.clicked.connect(self._browse)

        # The log-file row only makes sense when "Replay Log File" is selected.
        self.file_label = QLabel("Log file:")
        self.file_row_widget = QWidget()
        file_row = QHBoxLayout(self.file_row_widget)
        file_row.setContentsMargins(0, 0, 0, 0)
        file_row.addWidget(self.file_edit, 1)
        file_row.addWidget(self.browse_btn)

        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: #c0392b;")
        self.error_label.hide()

        form = QFormLayout()
        form.addRow("Interface:", self.combo)
        form.addRow(self.file_label, self.file_row_widget)
        form.addRow("", self.error_label)
        self.combo.currentIndexChanged.connect(self._update_file_visibility)
        self.combo.currentIndexChanged.connect(self._update_enabled)
        self._update_file_visibility()
        self._update_enabled()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Connect")
        buttons.accepted.connect(self._connect_clicked)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _update_file_visibility(self) -> None:
        """Show the log-file field only for the Replay Log File interface."""
        data = self.combo.currentData()
        is_replay = bool(data) and data[0] == "replay"
        self.file_label.setVisible(is_replay)
        self.file_row_widget.setVisible(is_replay)

    def _selected(self):
        return self.combo.currentData()

    def _update_enabled(self) -> None:
        kind = self._selected()[0]
        replay = kind == "replay"
        self.file_edit.setEnabled(replay)
        self.browse_btn.setEnabled(replay)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open replay log", "", "Log files (*.log *.txt);;All files (*)",
        )
        if path:
            self.file_edit.setText(path)

    def _connect_clicked(self) -> None:
        kind, arg = self._selected()
        path = self.file_edit.text().strip() if kind == "replay" else None
        if kind == "replay" and not path:
            self._show_error("Please choose a replay log file.")
            return
        ok = False
        try:
            if self._on_connect is not None:
                ok = bool(self._on_connect(kind, arg if kind == "rp1210" else path))
        except Exception as e:                # noqa: BLE001
            self._show_error(f"No connection: {e}")
        if ok:
            self.accept()

    def _show_error(self, text: str) -> None:
        self.error_label.setText(text)
        self.error_label.show()


class ParameterSelectDialog(QDialog):
    """Check-list of live-data parameters to include in a CSV log."""

    def __init__(self, parent, candidates: list[tuple[int, str, str]]) -> None:
        # candidates: [(source_addr, parameter_name, module_label), ...]
        super().__init__(parent)
        self.setWindowTitle("Select Parameters to Log")
        self.setMinimumSize(440, 440)

        self.listw = QListWidget()
        for addr, name, label in candidates:
            item = QListWidgetItem(f"{label}  \u2014  {name}")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, (addr, name))
            self.listw.addItem(item)

        all_btn = QPushButton("Select All")
        none_btn = QPushButton("Select None")
        all_btn.clicked.connect(lambda: self._set_all(Qt.Checked))
        none_btn.clicked.connect(lambda: self._set_all(Qt.Unchecked))
        row = QHBoxLayout()
        row.addWidget(all_btn)
        row.addWidget(none_btn)
        row.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Start Logging")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addWidget(self.listw)
        lay.addLayout(row)
        lay.addWidget(buttons)

    def _set_all(self, state) -> None:
        for i in range(self.listw.count()):
            self.listw.item(i).setCheckState(state)

    def selected(self) -> list[tuple[int, str]]:
        out = []
        for i in range(self.listw.count()):
            item = self.listw.item(i)
            if item.checkState() == Qt.Checked:
                out.append(item.data(Qt.UserRole))
        return out


# "Totals & Counters" panel: (display label, candidate live-data names). The
# first matching parameter found on either bus is shown; missing ones render as
# an em-dash. Names come from livedata.py (J1939) and pid1587.py (J1587), so a
# counter resolves whether the truck reports it on CAN or J1708.
TOTALS_ROWS = [
    ("Total Engine Hours",        ("Total Engine Hours",)),
    ("Engine Idle Hours",         ("Total Idle Hours", "Engine Idle Hours")),
    ("PTO Hours",                 ("Total PTO Hours", "PTO Hours")),
    ("Total Vehicle Hours",       ("Total Vehicle Hours",)),
    ("Total Engine Revolutions",  ("Total Engine Revolutions",)),
    ("Odometer (Distance)",       ("Total Vehicle Distance", "Total Distance")),
    ("Trip Distance",             ("Trip Distance",)),
    ("Lifetime Fuel Used",        ("Total Fuel Used",)),
    ("Trip Fuel",                 ("Trip Fuel",)),
    ("DPF Trip Fuel Used",        ("DPF Trip Fuel Used",)),
    ("Active Regen Time",         ("Active Regen Time",)),
    ("Active Regens (trip)",      ("Active Regens (trip)",)),
    ("Passive Regens (trip)",     ("Passive Regens (trip)",)),
    ("Vehicle Weight",            ("Vehicle Weight",)),
]


class TotalsCountersDialog(QDialog):
    """Modeless panel of accumulated/lifetime counters (Tools menu).

    Rows come from ``get_rows()`` as ``[(counter, value, unit, source), ...]``
    already unit-converted. It refreshes once a second so it tracks the live
    link without blocking the GUI.
    """

    def __init__(self, parent, get_rows) -> None:
        super().__init__(parent)
        self.setWindowTitle("Totals & Counters")
        self.setMinimumSize(560, 460)
        self._get_rows = get_rows

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Counter", "Value", "Unit", "Source"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 210)
        self.table.setColumnWidth(1, 110)
        self.table.setColumnWidth(2, 60)

        note = QLabel("Values update live.  \u2014  = the vehicle is not currently "
                      "broadcasting that counter.")
        note.setWordWrap(True)

        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self._populate)
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        btns = QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(refresh)
        btns.addWidget(close)

        lay = QVBoxLayout(self)
        lay.addWidget(self.table)
        lay.addWidget(note)
        lay.addLayout(btns)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._populate)
        self._timer.start(1000)
        self._populate()

    def _populate(self) -> None:
        rows = self._get_rows()
        t = self.table
        t.setRowCount(len(rows))
        for r, (counter, value, unit, source) in enumerate(rows):
            for c, text in enumerate((counter, value, unit, source)):
                t.setItem(r, c, QTableWidgetItem(str(text)))


# Aftertreatment panel: (category, label, candidate live-data names). The
# first matching name on either bus is shown; missing rows show an em-dash. Any
# other aftertreatment-named parameter is appended under "Other" so nothing is
# hidden. Names come from livedata.py (J1939) and pid1587.py (J1587).
AFT_ROWS = [
    # Parameter set mirrors the reference aftertreatment diagnostic layout.
    # Rows fed from a maker's proprietary range (SCR temps, injector/EGR/DOC
    # pressures) legitimately read N/A until that documentation is obtained.
    ("Regen", "Active Regeneration",                  ("Active Regeneration",)),
    ("Regen", "Regeneration Inhibited",               ("Regeneration Inhibited",)),
    ("Regen", "Regen Inhibit Reason",                 ("Regen Inhibit Reason",)),
    ("Temperatures", "DOC Inlet Temp",                ("DOC Inlet Temp",)),
    ("Temperatures", "DPF Intake Gas Temp",           ("DPF Intake Gas Temperature",)),
    ("Temperatures", "DPF Outlet Gas Temp",           ("DPF Outlet Gas Temperature",)),
    ("Temperatures", "SCR Intake Gas Temp",           ("SCR Intake Gas Temperature",)),
    ("Temperatures", "SCR Outlet Gas Temp",           ("SCR Outlet Gas Temperature",)),
    ("Temperatures", "Coolant Temp",                  ("Engine Coolant Temperature", "Engine Coolant Temp")),
    ("Pressures", "DPF Differential Pressure",        ("DPF Differential Pressure",)),
    ("Pressures", "DPF Inlet Pressure",               ("DPF Intake Pressure", "DPF Inlet Pressure")),
    ("Pressures", "DPF Outlet Pressure",              ("DPF Outlet Pressure",)),
    ("Pressures", "Aftertreatment Injector Pressure", ("Aftertreatment Injector Pressure",)),
    ("Pressures", "EGR Differential Pressure",        ("EGR Differential Pressure",)),
    ("EGR", "EGR Valve Position",                     ("Percent Exhaust Gas Recirculation Valve #1 Position",
                                                      "Percent Exhaust Gas Recirculation Valve Position")),
    # Placeholder NOx sensor readings - will decode when proprietary PGNs are identified
    ("NOx", "SCR Inlet NOx",                          ("SCR Inlet NOx",)),
    ("NOx", "SCR Outlet NOx",                         ("SCR Outlet NOx",)),
    ("DEF", "DEF Tank Level",                         ("DEF Tank Level",)),
    ("DEF", "DEF Tank Temp",                          ("DEF Temperature",)),
    ("DEF", "DEF Injector Pressure",                  ("DEF Injector Pressure",)),
    ("Load / Counts", "DPF Soot Load",                ("DPF Soot Load",)),
    ("Load / Counts", "Active Regen Time",            ("Active Regen Time",)),
]

_AFT_KEYWORDS = ("dpf", "doc", "scr", "regen", "aftertreatment", "exhaust gas",
                 "particulate", "urea", "dosing", "soot", "ash", "nox",
                 "ammonia", "doser", "trap", "def ")


def _is_aftertreatment_name(name: str) -> bool:
    n = name.strip().lower()
    return any(k in n for k in _AFT_KEYWORDS)


class AftertreatmentDialog(QDialog):
    """Modeless aftertreatment panel (Tools menu).

    Rows come from ``get_rows()`` as ``[(category, label, value, unit, source)]``
    already unit-converted; refreshes once a second.
    """

    def __init__(self, parent, get_rows, title="Aftertreatment") -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(720, 560)
        self._get_rows = get_rows

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Category", "Parameter", "Value", "Unit", "Source"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 110)
        self.table.setColumnWidth(1, 250)
        self.table.setColumnWidth(2, 110)
        self.table.setColumnWidth(3, 60)

        note = QLabel("Aftertreatment parameters from both J1939 and J1708. "
                      "Values update live.  \u2014  = not currently broadcast.")
        note.setWordWrap(True)

        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self._populate)
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        btns = QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(refresh)
        btns.addWidget(close)

        lay = QVBoxLayout(self)
        lay.addWidget(self.table)
        lay.addWidget(note)
        lay.addLayout(btns)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._populate)
        self._timer.start(1000)
        self._populate()

    def _populate(self) -> None:
        rows = self._get_rows()
        t = self.table
        t.setRowCount(len(rows))
        for r, (category, label, value, unit, source) in enumerate(rows):
            for c, text in enumerate((category, label, value, unit, source)):
                t.setItem(r, c, QTableWidgetItem(str(text)))


class LiveGraph(QWidget):
    """Realtime line graph for a single live-data parameter.

    Keeps a rolling buffer of (seconds, value) samples and paints them with a Y
    axis that auto-scales to the buffer's current min/max (plus a small
    margin), so the trace always fits whatever range the parameter reports.
    """

    MAX_SAMPLES = 600           # 600 ticks * 250 ms refresh ~= 2.5 minutes
    MARGIN_FRAC = 0.05          # headroom above/below the reported min/max

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._samples: list[tuple[float, float]] = []   # (seconds, value)
        self._param: str = ""
        self._unit: str = ""
        self.setMinimumSize(280, 160)

    def set_parameter(self, name: str, unit: str) -> None:
        """Start graphing `name` from scratch."""
        self._param = name
        self._unit = unit
        self._samples = []
        self.update()

    def set_unit(self, unit: str) -> None:
        """Update just the Y-axis unit label (keeps the buffered samples)."""
        if unit != self._unit:
            self._unit = unit
            self.update()

    def reset(self) -> None:
        self._param = ""
        self._unit = ""
        self._samples = []
        self.update()

    def add_sample(self, t: float, value: float) -> None:
        self._samples.append((t, value))
        if len(self._samples) > self.MAX_SAMPLES:
            self._samples = self._samples[-self.MAX_SAMPLES:]
        self.update()

    def paintEvent(self, _event) -> None:                # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#1e1e1e"))

        if not self._samples:
            p.setPen(QColor("#9a9a9a"))
            p.drawText(self.rect(), Qt.AlignCenter,
                       "Select a value in the Live Data list to graph it")
            return

        left, top, right, bottom = 58, 22, 16, 30
        pw = self.width() - left - right
        ph = self.height() - top - bottom
        if pw <= 0 or ph <= 0:
            return

        vals = [v for _, v in self._samples]
        lo, hi = min(vals), max(vals)
        if hi == lo:
            hi += 1.0
            lo -= 1.0
        else:
            pad = (hi - lo) * self.MARGIN_FRAC
            hi += pad
            lo -= pad

        t0 = self._samples[0][0]
        t1 = self._samples[-1][0]
        if t1 == t0:
            t1 = t0 + 1.0

        def px(t: float) -> float:
            return left + (t - t0) / (t1 - t0) * pw

        def py(v: float) -> float:
            return top + (1.0 - (v - lo) / (hi - lo)) * ph

        # frame + centre line
        p.setPen(QColor("#444444"))
        p.drawRect(left, top, pw, ph)
        p.setPen(QColor("#2e2e2e"))
        mid = py((lo + hi) / 2.0)
        p.drawLine(int(left), int(mid), int(left + pw), int(mid))

        # trace
        p.setPen(QPen(QColor("#2ecc71"), 2.0))
        path = QPainterPath()
        path.moveTo(px(self._samples[0][0]), py(self._samples[0][1]))
        for t, v in self._samples[1:]:
            path.lineTo(px(t), py(v))
        p.drawPath(path)

        # y-axis min/max labels
        p.setPen(QColor("#9a9a9a"))
        p.drawText(QRect(0, top - 9, left - 6, 16),
                   Qt.AlignRight | Qt.AlignVCenter, f"{hi:.4g}")
        p.drawText(QRect(0, top + ph - 7, left - 6, 16),
                   Qt.AlignRight | Qt.AlignVCenter, f"{lo:.4g}")

        # title: parameter + latest value + unit
        cur = self._samples[-1][1]
        title = f"{self._param}  =  {cur:.4g} {self._unit}".strip()
        p.setPen(QColor("#e8e8e8"))
        p.drawText(QRect(left, 2, pw, 16), Qt.AlignHCenter | Qt.AlignTop, title)


class ObdWorker(QObject):
    """Runs on a background QThread: one OBD-II (J1979) session, polled.

    Emits a state dict {live, mil, dtc_count, stored, pending, vin, ecus}
    after every polling round (about once per second). A `command` attribute
    set from the GUI thread is honoured between rounds ("clear" = Mode 04).
    """
    state = Signal(dict)
    failed = Signal(str)

    def __init__(self, adapter_code: Optional[str]) -> None:
        super().__init__()
        self._adapter = adapter_code
        self._stop = False
        self.command: Optional[str] = None
        self.session = None                 # OBD2Session, once connected
        self._capture_fh = None             # raw-frame capture sink
        self._capture_lock = threading.Lock()

    def request_stop(self) -> None:
        self._stop = True

    # --------------------------------------------------- raw capture --- #
    def start_capture(self, path: str) -> None:
        """Begin writing every CAN frame on the DLC to `path`."""
        with self._capture_lock:
            self.stop_capture()
            self._capture_fh = open(path, "w", encoding="utf-8")
            self._capture_fh.write(
                "# OpenTruck OBD-II raw capture (RX/TX = direction)\n"
                "# obd frame: <direction> obd <can id hex>:<data hex>\n")
            self._capture_fh.flush()
        if self.session is not None:
            self.session.frame_logger = self._write_capture_line

    def stop_capture(self) -> None:
        """Stop and close the capture, if one is running."""
        with self._capture_lock:
            fh, self._capture_fh = self._capture_fh, None
        if fh is not None:
            try:
                fh.flush()
                fh.close()
            except Exception:                # noqa: BLE001
                pass
        if self.session is not None:
            self.session.frame_logger = None

    def _write_capture_line(self, line: str) -> None:
        with self._capture_lock:
            fh = self._capture_fh
            if fh is None:
                return
            try:
                fh.write(line + "\n")
            except Exception:                # noqa: BLE001
                pass

    def run(self) -> None:
        from lookup import obd_pids
        try:
            sess = open_session(self._adapter)
        except Exception as exc:
            self.failed.emit(f"obd-connect: {exc}")
            return
        self.session = sess
        if self._capture_fh is not None:
            sess.frame_logger = self._write_capture_line
        try:
            if not sess.probe():
                sess.source.close()
                self.failed.emit("no-vehicle")
                return
            sess.read_vin()
            sess.vpic = decode_vin_vpic(sess.vin) if sess.vin else None
            sess.read_ecu_names()
            sess.read_cal_ids()
            sess.read_dtcs(0x03, sess.dtcs_stored)
            sess.read_dtcs(0x07, sess.dtcs_pending)
            sess.read_permanent_dtcs()
            base = sess.request(0x01, 0x00, timeout=0.6)
            pids = []
            if base:
                for ecu, resp in base:
                    sup = sess.supported_pids_for(ecu, resp)
                    sess.supported_by_ecu[ecu] = sup
                    if not sess.ecu_names.get(ecu):
                        sess.ecu_class[ecu] = sess.classify_ecu(ecu, sup)
                allp = sorted({p for sup in sess.supported_by_ecu.values()
                               for p in sup})
                pids = [p for p in allp if p in obd_pids.PIDS]
                # Full sweep once so the table is populated immediately
                # (supported PIDs answer in milliseconds, unlike the timeout
                # spent on unsupported ones).
                for pid in pids:
                    sess.poll_pid(pid)
            self._emit(sess)
            rounds = 0
            idx = 0
            while not self._stop:
                if self.command == "clear":
                    self.command = None
                    sess.clear_dtcs()
                    sess.read_dtcs(0x03, sess.dtcs_stored)
                    sess.read_dtcs(0x07, sess.dtcs_pending)
                # Rotate through the supported live PIDs, eight per round -
                # poll_pid decodes and merges into the live store (a bare
                # request() does NOT decode; that was the empty-table bug).
                # With the OBD-only early-exit (~0.1 s each), eight per round
                # refreshes every supported parameter about every 2 s.
                if pids:
                    for k in range(8):
                        sess.poll_pid(pids[(idx + k) % len(pids)])
                    idx = (idx + 8) % len(pids)
                rounds += 1
                if rounds % 8 == 0:              # MIL + DTC status ~ every 4 s
                    r = sess.request(0x01, 0x01, timeout=0.4)
                    if r:
                        b0 = r[0][1][2] if len(r[0][1]) > 2 else 0
                        sess.mil_on = bool(b0 & 0x80)
                    sess.read_dtcs(0x03, sess.dtcs_stored)
                    sess.read_dtcs(0x07, sess.dtcs_pending)
                    sess.read_permanent_dtcs()
                self._emit(sess)
                time.sleep(0.15)
        except Exception as exc:
            self.failed.emit(f"obd-runtime: {exc}")
        finally:
            self.stop_capture()
            try:
                sess.source.close()
            except Exception:
                pass

    def _emit(self, sess) -> None:
        names = {}
        for ecu in sess.ecus:
            name = sess.ecu_names.get(ecu) or sess.ecu_class.get(ecu) or "ECU"
            names[ecu] = name
        self.state.emit({
            "live": dict(sess.live),
            "live_by_ecu": {e: dict(v) for e, v in sess.live_by_ecu.items()},
            "mil": sess.mil_on,
            "vin": sess.vin,
            "brand": sess.brand,
            "vpic": sess.vpic,
            "ecu_names": names,
            "cal_ids": dict(sess.cal_ids),
            "stored": list(sess.dtcs_stored),
            "pending": list(sess.dtcs_pending),
            "permanent": list(sess.dtcs_permanent),
            "ecus": sorted(sess.ecus),
        })


class MainWindow(QObject):
    """Controller around the Qt Designer .ui file.

    Subclasses QObject (rather than a plain class) so that slots connected to
    the reader thread's signals (`frame` / `error`) are delivered back to the
    GUI thread via a queued connection. Without this, `_on_frame` runs on the
    worker thread, which makes any QTimer it starts (the connection watchdog)
    inert, and races `Session` state against the GUI's `_refresh` timer.
    """

    COLUMNS = ["Module", "Protocol", "SPN / PID", "FMI", "Description",
               "Status", "Troubleshooting Type"]

    def __init__(self, win, initial_kind: str = "sim",
                 replay_path: Optional[str] = None) -> None:
        super().__init__(win)
        self.win = win
        self._source_kind = initial_kind
        self._replay_path = replay_path
        self._rp1210_code: Optional[str] = None   # selected RP1210 vendor code
        self.session = CombinedSession()          # merged J1939 + J1708 view
        self._seen_j1939 = False                  # data flowed on this protocol?
        self._seen_j1708 = False
        self._uds_tried = False          # one-shot UDS VIN fallback, per connect
        self._uds_vin_from: Optional[int] = None
        self._source: Optional[FrameSource] = None
        self._logger: Optional[LoggingSource] = None
        self._thread: Optional[QThread] = None
        self._worker: Optional[FrameReader] = None
        self._current_addr: Optional[int] = None
        self._last_components = None
        self._last_table_sig = None
        self._last_live_sig = None
        self._totals_dialog = None
        self._aft_dialog = None
        self._abs_dialog = None
        self._obd_worker = None          # OBD-II (light-duty) mode state
        self._obd_thread = None
        self._obd_state = None
        self._obd_command = None
        self._obd_selected = None        # OBD ECU selected in the module list
        self._obd_tried = False          # one OBD fallback per connect attempt
        self._obd_probing = False        # mid fallback: J1939 silent, OBD probing

        self._grab_widgets()
        self._setup_table()
        self._setup_live_table()
        self._restore_columns()
        self._wire()
        self.live_splitter = self.splitters.get("liveDataSplitter")
        self._set_connected(False)

        self._timer = QTimer(win)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(250)

        self._discovery_idx = 0
        self._j1708_ident_tries = 0
        self._discovery_timer = QTimer(win)
        self._discovery_timer.timeout.connect(self._discovery_tick)

        # One-shot address sweep for silent ECUs (see IDENTIFICATION_PGNS).
        self._sweep_queue: list[int] = []
        self._sweep_timer = QTimer(win)
        self._sweep_timer.setInterval(SWEEP_TICK_MS)
        self._sweep_timer.timeout.connect(self._sweep_tick)

        # Connection watchdog: after source.connect() succeeds at the RP1210
        # layer we still wait for real frames before going green. If none
        # arrive within this window (adapter present but no live bus), we error
        # out and return to the connection dialog.
        self._connect_timeout = QTimer(win)
        self._connect_timeout.setSingleShot(True)
        self._connect_timeout.timeout.connect(self._on_connect_timeout)
        self._first_frame_seen = False

        # Continuous connection watchdog ("deadman"): once frames are flowing
        # this single-shot timer is restarted on every incoming frame. If it
        # ever fires, the vehicle went silent and we treat the link as lost.
        self._watchdog = QTimer(win)
        self._watchdog.setSingleShot(True)
        self._watchdog.timeout.connect(self._on_watchdog_timeout)
        # Monotonic deadline until which a clear suppresses the lost-link check.
        self._clear_grace_until = 0.0

        # Human-readable CSV logging (selected live-data parameters).
        self._csv_fh = None
        self._csv_path: Optional[str] = None
        self._csv_params: list[tuple[int, str]] = []
        self._csv_timer = QTimer(win)
        self._csv_timer.timeout.connect(self._csv_tick)

        # Developer > Raw capture (toggleable).
        self._capture_active = False
        self._obd_capture_path: Optional[str] = None
        self._capture_timer = QTimer(win)
        self._capture_timer.timeout.connect(self._capture_tick)

        # Update check (Help > Check for Updates / silent on-launch check).
        # Non-blocking: a missing/offline connection just never fires `finished`.
        self._nam = QNetworkAccessManager(win)
        self._nam.finished.connect(self._on_update_reply)
        self._update_interactive = False
        self._update_release: Optional[dict] = None   # last release JSON seen
        self._update_reply: Optional[object] = None   # active download reply

    # ---------------------------------------------------------------- UI --- #
    def _grab_widgets(self) -> None:
        w = self.win
        self.component_list = w.findChild(QListWidget, "componentList")
        self.codes_table = w.findChild(QTableWidget, "codesTable")
        self.live_table = w.findChild(QTableWidget, "liveDataTable")
        self.lbl_conn = w.findChild(QLabel, "lblConnStatus")
        self.lbl_vin = w.findChild(QLabel, "lblVin")
        self.lbl_model = w.findChild(QLabel, "lblModel")
        self.lbl_serial = w.findChild(QLabel, "lblEngSerial")
        self.lbl_software_id = w.findChild(QLabel, "lblSoftwareId")
        self.lbl_ecu_id = w.findChild(QLabel, "lblEcuId")
        self.led_j1708 = w.findChild(QLabel, "ledJ1708")
        self.led_j1939 = w.findChild(QLabel, "ledJ1939")
        self.led_obd = w.findChild(QLabel, "obdLed")
        self.fault_label = w.findChild(QLabel, "faultCodesLabel")
        self.live_label = w.findChild(QLabel, "liveDataLabel")
        self.lamp_amber = w.findChild(QLabel, "lampAmber")
        self.lamp_red = w.findChild(QLabel, "lampRed")
        self.lamp_abs = w.findChild(QLabel, "lampAbs")
        self.lamp_trailer_abs = w.findChild(QLabel, "lampTrailerAbs")
        self.btn_connect = w.findChild(QPushButton, "btnConnect")
        self.btn_clear_fault = w.findChild(QPushButton, "btnClearFault")
        self.btn_clear_all = w.findChild(QPushButton, "btnClearAllFaults")
        self.act_connect_menu = w.findChild(QAction, "actionConnect")
        self.act_logging = w.findChild(QAction, "actionStartLogging")
        self.act_exit = w.findChild(QAction, "actionExit")
        self.act_capture = w.findChild(QAction, "actionCapture")
        self.act_sniff = w.findChild(QAction, "actionSniffBus")
        self.act_preferences = w.findChild(QAction, "actionPreferences")
        self.act_generate_report = w.findChild(QAction, "actionGenerateReport")
        self.act_totals = w.findChild(QAction, "actionTotalsCounters")
        self.act_aftertreatment = w.findChild(QAction, "actionAftertreatment")
        self.act_abs = w.findChild(QAction, "actionAbs")
        self.act_check_updates = w.findChild(QAction, "actionCheckForUpdates")
        self.act_about = w.findChild(QAction, "actionAbout")
        for lbl in (self.fault_label, self.live_label):
            if lbl is not None:
                f = lbl.font()
                f.setBold(True)
                f.setPointSize(13)
                lbl.setFont(f)

        # Live-data graph (custom widget hosted in the .ui placeholder).
        host = w.findChild(QWidget, "liveGraphHost")
        self.live_graph = LiveGraph()
        if host is not None:
            lay = QVBoxLayout(host)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(self.live_graph)
        self._graph_param: Optional[str] = None

        # Splitter layout: restore each splitter's last-used position, or fall
        # back to a sensible default. Saved sizes are applied after the window
        # is shown (setSizes() on a hidden widget gets clamped to its tiny
        # pre-layout size).
        # Defaults match the intended proportions of the maximized window:
        # side panel ~22 % of the width, fault-codes section ~46 % of the
        # centre height, live-data graph ~26 % of the live-data width.
        defaults = {
            "mainSplitter":      (420, 1500),   # side panel | centre
            "faultLiveSplitter": (460, 540),    # faults | live data
            "liveDataSplitter":  (740, 260),    # table | graph
        }
        self.splitters: dict[str, QSplitter] = {}
        self._saved_split_sizes: dict[str, list[int]] = {}
        saved_layout = ui_layout()
        for name, default_sizes in defaults.items():
            sp = w.findChild(QSplitter, name)
            if sp is None:
                continue
            self.splitters[name] = sp
            # QUiLoader loads splitters with a Preferred size policy, which
            # stops them absorbing extra space when a neighbouring splitter
            # pane grows. Force Expanding so everything rescales properly.
            sp.setSizePolicy(QSizePolicy.Policy.Expanding,
                             QSizePolicy.Policy.Expanding)
            saved = saved_layout.get(name)
            if self._valid_split_sizes(saved, len(default_sizes)):
                self._saved_split_sizes[name] = saved
            else:
                self._apply_split(sp, list(default_sizes))
        if self._saved_split_sizes:
            QTimer.singleShot(0, self._apply_saved_split)

    @staticmethod
    def _valid_split_sizes(saved, count: int) -> bool:
        """A saved splitter layout is only trusted if it is plausible.

        Guards against layouts saved while the window was hidden/tiny (e.g.
        by an offscreen test run): every pane must be a positive integer of
        usable width and the total must be big enough to be a real layout.
        """
        return (isinstance(saved, list) and len(saved) == count
                and all(isinstance(x, int) and x >= 40 for x in saved)
                and sum(saved) >= 400)

    @staticmethod
    def _apply_split(sp: QSplitter, sizes: list[int]) -> None:
        """Apply sizes and derive the stretch factors from them, so the same
        proportions are kept when the window is later resized (hardcoded
        stretch factors would drag the layout back toward a fixed ratio)."""
        sp.setSizes(sizes)
        for i, size in enumerate(sizes):
            sp.setStretchFactor(i, size)

    def _apply_saved_split(self) -> None:
        for name, sizes in self._saved_split_sizes.items():
            sp = self.splitters.get(name)
            if sp is not None:
                self._apply_split(sp, sizes)
        self._saved_split_sizes = {}

    def _setup_table(self) -> None:
        t = self.codes_table
        t.setColumnCount(len(self.COLUMNS))
        t.setHorizontalHeaderLabels(self.COLUMNS)
        t.horizontalHeader().setStretchLastSection(True)
        t.setColumnWidth(0, 200)   # Module
        t.setColumnWidth(1, 70)    # Protocol (J1939 / J1708)
        t.setColumnWidth(2, 90)    # SPN / PID
        t.setColumnWidth(3, 50)    # FMI
        t.setColumnWidth(4, 300)   # Description
        t.setColumnWidth(5, 70)    # Status
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)

    def _restore_columns(self) -> None:
        """Re-apply saved column widths (falls back to the set defaults)."""
        saved = ui_layout()
        for name, t in (("codesTable", self.codes_table),
                        ("liveDataTable", self.live_table)):
            widths = saved.get(name)
            if not (isinstance(widths, list) and len(widths) == t.columnCount()
                    and all(isinstance(x, int) and x >= 0 for x in widths)):
                continue
            for i, wd in enumerate(widths[:-1]):
                t.setColumnWidth(i, wd)   # last column stretches to fill

    def _save_ui_layout(self) -> None:
        """Persist splitter positions and table column widths for next launch.

        Skipped entirely when the window is not visible (e.g. a headless test
        session) — sizes captured from a hidden window are garbage and would
        corrupt the restored layout.
        """
        if not self.win.isVisible():
            return
        for name, sp in self.splitters.items():
            sizes = sp.sizes()
            if not self._valid_split_sizes(sizes, len(sizes)):
                return   # refuse to persist a degenerate layout
            set_ui_layout(name, sizes)
        for name, t in (("codesTable", self.codes_table),
                        ("liveDataTable", self.live_table)):
            set_ui_layout(name, [t.columnWidth(i) for i in range(t.columnCount())])

    def _setup_live_table(self) -> None:
        t = self.live_table
        t.setColumnCount(3)
        t.setHorizontalHeaderLabels(["Parameter", "Value", "Unit"])
        t.horizontalHeader().setStretchLastSection(True)
        t.setColumnWidth(0, 320)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)

    def _wire(self) -> None:
        self.btn_connect.clicked.connect(self._toggle_connect)
        self.btn_clear_all.clicked.connect(self._clear_all_faults)
        self.btn_clear_fault.clicked.connect(self._clear_selected_fault)
        self.act_connect_menu.triggered.connect(self._toggle_connect)
        self.act_logging.triggered.connect(self._toggle_logging)
        if self.act_preferences is not None:
            self.act_preferences.triggered.connect(self._show_preferences)
        if self.act_generate_report is not None:
            self.act_generate_report.triggered.connect(self._generate_report)
        if self.act_totals is not None:
            self.act_totals.triggered.connect(self._show_totals_counters)
        if self.act_aftertreatment is not None:
            self.act_aftertreatment.triggered.connect(self._show_aftertreatment)
        if self.act_abs is not None:
            self.act_abs.triggered.connect(self._show_abs)
        self.act_exit.triggered.connect(self.win.close)
        if self.act_capture is not None:
            self.act_capture.triggered.connect(self._toggle_raw_capture)
        if self.act_sniff is not None:
            self.act_sniff.triggered.connect(self._sniff_bus)
        if self.act_check_updates is not None:
            self.act_check_updates.triggered.connect(self._check_for_updates)
        if self.act_about is not None:
            self.act_about.triggered.connect(self._show_about)
        self.component_list.currentItemChanged.connect(self._on_module_changed)
        self.live_table.cellClicked.connect(self._on_live_click)

    def _set_connected(self, connected: bool) -> None:
        # During the J1939 -> OBD-II fallback probe we are neither connected
        # nor disconnected: keep the Disconnect button active (the attempt is
        # still in progress) and show what is happening instead of the
        # misleading "Not connected".
        if getattr(self, "_obd_probing", False):
            self.btn_connect.setText("Disconnect")
            self.act_connect_menu.setText("Disconnect")
            self._label(self.lbl_conn, "Probing OBD-II (16-pin DLC)...")
            self.win.statusBar().showMessage(
                "No J1939/J1708 data - probing OBD-II (16-pin DLC)...")
            # No session to clear anything on while probing.
            self.btn_clear_fault.setEnabled(False)
            self.btn_clear_all.setEnabled(False)
            return
        # Clear buttons require a live link (heavy-duty, OBD-II, sim or
        # replay); disabled whenever there is no connection.
        self.btn_clear_fault.setEnabled(connected)
        self.btn_clear_all.setEnabled(connected)
        label = "Disconnect" if connected else "Connect"
        self.btn_connect.setText(label)
        self.act_connect_menu.setText(label)
        self._label(self.lbl_conn, "Connected" if connected else "Not connected")
        if connected:
            # Both buses are monitored simultaneously; a bus shows green only
            # once it has actually produced data, grey while the live link is
            # otherwise up but that particular bus is silent (normal for J1708
            # on a modern truck). The OBD dot goes green in light-duty
            # (J1979) mode, and stays grey while a heavy-duty link is up.
            j1939 = "#2e7d32" if self._seen_j1939 else "#888888"
            j1708 = "#2e7d32" if self._seen_j1708 else "#888888"
            obd = "#2e7d32" if self._obd_state is not None else "#888888"
        else:
            j1939 = "#c0392b"
            j1708 = "#c0392b"
            obd = "#c0392b"
        self._led(self.led_j1939, "J1939", j1939)
        self._led(self.led_j1708, "J1708", j1708)
        self._led(self.led_obd, "OBD", obd)

    @staticmethod
    def _label(w: Optional[QLabel], text: str) -> None:
        if w is not None:
            w.setText(text)

    @staticmethod
    def _led(w: Optional[QLabel], name: str, color: str) -> None:
        if w is not None:
            w.setText(f"\u25cf {name}")
            w.setStyleSheet(f"color: {color};")

    @staticmethod
    def _bus_tag(key: int) -> str:
        """Bus name for a merged module key."""
        return "J1708" if key >= J1708_KEY_BASE else "J1939"

    @staticmethod
    def _key_text(key: int) -> str:
        """Render a merged module key for display, tagged with its bus: a J1939
        source address or a J1708 MID (shifted keys >= J1708_KEY_BASE). The bus
        tag makes it obvious when the same ECU appears on both wires (e.g. the
        engine at 0x00 on J1939 and MID 128 on J1708)."""
        if key >= J1708_KEY_BASE:
            return f"MID {key - J1708_KEY_BASE:02X} (J1708)"
        return f"0x{key:02X} (J1939)"

    # ---------------------------------------------------------- connect --- #
    def _toggle_connect(self) -> None:
        if self._thread is not None or self._obd_thread is not None:
            self._disconnect()
        else:
            self._show_connection_dialog()

    def _show_connection_dialog(self) -> None:
        from rp1210 import list_adapters
        adapters = list_adapters()
        dlg = ConnectionDialog(
            self.win, adapters,
            last_source=last_source(),
            on_connect=self._connect_from_selection,
        )
        dlg.exec()

    def _make_source(self):
        if self._source_kind == "rp1210":
            from rp1210 import get_adapter, list_adapters
            if self._rp1210_code:
                a = get_adapter(self._rp1210_code)
                if a is not None:
                    return self._rp1210_source(a)
            adapters = list_adapters()
            if adapters:
                return self._rp1210_source(adapters[0])
            raise RuntimeError("No compatible RP1210 adapter found.")
        if self._source_kind == "replay":
            return CombinedSource([("j1939", ReplaySource(self._replay_path))])
        return CombinedSource([("j1939", SimulatorSource())])

    def _rp1210_source(self, a) -> CombinedSource:
        """Build the multi-protocol source for adapter `a`: J1939 (the write /
        request target) plus J1708 (listen-only, so we surface J1587 modules too).
        J1708 is optional — if the adapter can't open it, the J1939 link still
        works.

        A 32-bit-only driver (`a.dll_path` empty, `a.bridge_dll` set) is driven
        through the out-of-process `BridgedRP1210Source`."""
        from rp1210 import RP1210Source, BridgedRP1210Source
        from framesource import RawCanSource

        def build(protocol, passive=False):
            if a.dll_path:
                return RP1210Source(a.dll_path, protocol, a.device_id,
                                    passive=passive)
            return BridgedRP1210Source(a.bridge_dll, protocol, a.device_id,
                                       passive=passive)

        channels = [
            ("j1939", build(a.protocol)),
            ("j1708", build(a.j1708_protocol)),
        ]
        # Raw-CAN channel: capture EVERYTHING on the wire, undecoded - this is
        # how handshake/commands that the J1939 layer doesn't surface (e.g. a
        # regen initiation) end up in the capture log. Best-effort: skipped if
        # the driver refuses the third client.
        try:
            channels.append(("can2", RawCanSource(
                build("CAN:Baud=Auto", passive=True))))
        except Exception:
            pass
        return CombinedSource(channels)

    def _connect_from_selection(self, kind: str, arg: Optional[str]) -> bool:
        """Receive the dialog's choice (kind in {'rp1210','sim','replay'}).
        Returns True when the connection opened (so the dialog closes)."""
        if kind == "rp1210":
            self._source_kind = "rp1210"
            self._rp1210_code = arg
            self._replay_path = None
            set_last_source(arg)
        elif kind == "replay":
            self._source_kind = "replay"
            self._replay_path = arg
            set_last_source("replay")
        else:
            self._source_kind = "sim"
            self._replay_path = None
            set_last_source("sim")
        return self._connect()

    def _connect(self) -> bool:
        self._set_connected(False)               # stay red until fully connected
        source = None
        try:
            source = self._make_source()
            source.connect()                     # synchronous: raise on failure
        except Exception as e:                   # noqa: BLE001
            if source is not None:
                try:
                    source.close()
                except Exception:                # noqa: BLE001
                    pass
            if self._source_kind != "rp1210":
                raise                            # replay/sim: keep the inline dialog error
            # The PC can't talk to the adapter at all (not enumerated, or the
            # driver rejected ClientConnect / the filter / the address claim).
            # Surface it as a clear popup and keep the connection dialog open.
            QMessageBox.warning(
                self.win, "No Adapter",
                "No adapter is connected.\n\n"
                "OpenTruck couldn't talk to the diagnostic adapter.\n\n"
                f"({e})\n\n"
                "Check the adapter is plugged in, its driver is installed, "
                "and retry.")
            return False
        self._logger = LoggingSource(source)
        self._source = self._logger
        self.session = CombinedSession()
        self._seen_j1939 = False
        self._seen_j1708 = False
        self._uds_tried = False          # one-shot UDS VIN fallback, per connect
        self._current_addr = None
        self._last_components = None
        self._last_table_sig = None
        self._last_live_sig = None
        self.component_list.clear()
        self.codes_table.setRowCount(0)
        self.live_table.setRowCount(0)

        self._thread = QThread(self.win)
        self._worker = FrameReader(self._logger)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.frame.connect(self._on_frame)
        self._worker.error.connect(self._on_error)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.start()

        # Do NOT turn the J1939 dot green yet: we only declare the link live
        # once real frames arrive. A dead bus (adapter present but no vehicle)
        # therefore stays red and times out with an error instead of showing a
        # false "Connected".
        self.btn_connect.setText("Disconnect")
        self.act_connect_menu.setText("Disconnect")
        self._label(self.lbl_conn, "Connecting...")
        self._led(self.led_j1939, "J1939", "#c0392b")
        self._led(self.led_j1708, "J1708", "#c0392b")
        self._led(self.led_obd, "OBD", "#c0392b")
        self._first_frame_seen = False
        self.win.statusBar().showMessage("Connecting... waiting for vehicle data")

        # J1587 modules announce themselves passively, so only J1939 needs the
        # explicit address-claim / DM discovery polling. Requests always go out
        # on the J1939 source; the J1708 listener is receive-only.
        self._discovery_idx = 0
        self._j1708_ident_tries = 0
        for pgn in (PGN.ADDRESS_CLAIMED, PGN.DM1, PGN.DM2):
            self._request_pgn(pgn)
        self._discovery_timer.start(1000)

        # Arm the connect watchdog only for live RP1210 links: if the adapter
        # connects but no real vehicle is on the bus, we time out and return to
        # the connection dialog. Replay/simulator feed data immediately (or
        # loop) and have no 'dead bus' notion, so they must not time out here.
        if self._source_kind == "rp1210":
            self._obd_tried = False          # each connect gets its own probe
            self._connect_timeout.start(4000)

        return True

    def _show_preferences(self) -> None:
        """Show the preferences dialog and apply settings.
        
        Saves unit preferences to config.json. No vehicle connection required.
        Preferences will be used when live data is displayed.
        """
        # Create the dialog - parent must be a QWidget (not QObject)
        self._pref_dialog = PreferencesDialog(self.win)
        
        # Load saved settings if any
        current = units()
        self._pref_dialog.set_units(current)
        saved_log_dir = log_dir()
        self._pref_dialog.set_log_dir(saved_log_dir)
        
        result = self._pref_dialog.exec()
        if result == QDialog.Accepted:
            new_val = self._pref_dialog.get_units()
            set_units(new_val)
            new_log_dir = self._pref_dialog.get_log_dir()
            set_log_dir(new_log_dir or "")
            # Re-render live data immediately so a unit change shows on-screen
            # (the 250 ms refresh timer would catch it too, but don't wait).
            self._last_live_sig = None
            self._refresh_live_data()
            self._graph_tick()
            self.win.statusBar().showMessage(f"Preferences saved: {new_val} units")
            self.win.statusBar().messageChanged.emit()

    # ---------------------------------------------------------- updates --- #
    def _check_for_updates(self, interactive: bool = True) -> None:
        """Ask GitHub's Releases API whether a newer release exists.

        Interactive (Help > Check for Updates) ALWAYS reports a result - up to
        date, update available, or failed - because a manual check that looks
        like it did nothing is indistinguishable from a broken menu item. The
        silent on-launch check only surfaces a dialog when a newer release is
        found.
        """
        self._update_interactive = interactive
        if interactive:
            self.win.statusBar().showMessage("Checking for updates...")
            self.win.statusBar().messageChanged.emit()
        request = QNetworkRequest(RELEASES_URL)
        # A manual check must never hang silently: give up after 15 s and let
        # the reply's error path report it.
        request.setTransferTimeout(15000)
        self._nam.get(request)

    def _on_update_reply(self, reply) -> None:
        """Handle the GitHub API response for the update check."""
        interactive = self._update_interactive
        try:
            status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
            body = bytes(reply.readAll()).decode("utf-8", errors="replace")
            if status == 404:
                # The releases endpoint 404s while the repo has no published
                # release yet - that is "nothing newer exists", NOT an error.
                if interactive:
                    self._announce_up_to_date(
                        "No release has been published yet, so this is the "
                        "newest version available.")
                return
            if status != 200:
                raise RuntimeError(f"HTTP {status}")
            data = json.loads(body)
            # The list endpoint returns an array; accept a single object too so
            # a cached/older response shape still works.
            releases = data if isinstance(data, list) else [data]
            release = pick_latest_release(releases)
            if release is None:
                if interactive:
                    self._announce_up_to_date(
                        "No release has been published yet, so this is the "
                        "newest version available.")
                return
            tag = release.get("tag_name", "")
            name = release.get("name") or tag
            url = release.get("html_url", "")
            latest = release_version(release)
            self._update_release = release
            if latest is not None and latest > current_version():
                self._announce_update(name, tag, url, latest)
            elif interactive:
                shown = ".".join(str(x) for x in latest) if latest else (tag or name)
                self._announce_up_to_date(
                    f"The latest release is {shown}." if shown else "")
        except Exception as exc:  # noqa: BLE001 - report any failure gracefully
            if interactive:
                self.win.statusBar().showMessage(
                    "Update check failed (offline?)"
                )
                self.win.statusBar().messageChanged.emit()
                QMessageBox.warning(
                    self.win, "Check for Updates",
                    "Could not check for updates. You may be offline, or the "
                    "GitHub repository is not reachable.\n\n"
                    f"({exc})"
                )
        finally:
            reply.deleteLater()

    def _announce_up_to_date(self, note: str = "") -> None:
        """Tell the user a MANUAL update check found nothing newer."""
        self.win.statusBar().showMessage(
            f"OpenTruck is up to date ({full_version()})")
        self.win.statusBar().messageChanged.emit()
        box = QMessageBox(self.win)
        box.setIcon(QMessageBox.Information)
        box.setWindowTitle("Check for Updates")
        box.setText("OpenTruck is up to date.")
        text = f"You are running version {full_version()}"
        if note:
            text += f"\n\n{note}"
        box.setInformativeText(text)
        box.setStandardButtons(QMessageBox.Ok)
        box.exec()

    def _announce_update(self, name: str, tag: str, url: str,
                         latest=None) -> None:
        """Prompt the user about an available update (also used non-interactively)."""
        box = QMessageBox(self.win)
        box.setIcon(QMessageBox.Information)
        box.setWindowTitle("Update Available")
        label = name if name != tag else f"Version {tag}"
        box.setText(f"An update to OpenTruck is available: {label}")
        new_ver = ".".join(str(x) for x in latest) if latest else label
        box.setInformativeText(
            f"You are running {full_version()}; the new version is {new_ver}. "
            "It can be downloaded and installed automatically — OpenTruck "
            "will close, update, and start again.")
        if url:
            box.setDetailedText(f"Download page: {url}")
        install = box.addButton("Download && Install", QMessageBox.AcceptRole)
        download = box.addButton("Open Download Page", QMessageBox.ActionRole)
        box.addButton("Later", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is install:
            self._download_update()
        elif box.clickedButton() is download and url:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl(url))

    # ------------------------------------------------ self-update (Windows) -
    #
    # Flow: download the new OpenTruckSetup-<version>.exe from the GitHub
    # release into a temp folder (progress bar), verify its size against the
    # release metadata, quit this app, then launch the installer elevated
    # (UAC) in silent mode. The installer's [Run] section relaunches OpenTruck
    # automatically after a silent install, so the app comes back on its own.
    def _download_update(self) -> None:
        """Download the installer asset from the latest release, with progress."""
        asset = find_setup_asset(self._update_release or {})
        if asset is None:
            QMessageBox.warning(
                self.win, "Update",
                "The new release does not include a downloadable installer. "
                "Please update from the GitHub releases page.")
            return
        url = asset.get("browser_download_url")
        if not url:
            QMessageBox.warning(self.win, "Update", "Installer download link not found.")
            return
        self._update_expected_size = int(asset.get("size") or 0)
        self._update_asset_name = asset.get("name") or "OpenTruckSetup.exe"

        import os
        import tempfile
        dest_dir = os.path.join(tempfile.gettempdir(), "OpenTruckUpdate")
        try:
            os.makedirs(dest_dir, exist_ok=True)
            self._update_dest = os.path.join(dest_dir, self._update_asset_name)
            self._update_file = open(self._update_dest, "wb")
        except OSError as exc:
            QMessageBox.warning(self.win, "Update",
                                f"Could not create the download folder:\n{exc}")
            return

        self._update_progress = QProgressDialog(
            f"Downloading {self._update_asset_name}...", "Cancel",
            0, max(self._update_expected_size, 1), self.win)
        self._update_progress.setWindowTitle("Downloading Update")
        self._update_progress.setWindowModality(Qt.WindowModal)
        self._update_progress.setMinimumDuration(0)
        self._update_progress.canceled.connect(self._cancel_update_download)

        reply = self._nam.get(QNetworkRequest(_QUrl(url)))
        self._update_reply = reply
        reply.downloadProgress.connect(self._on_download_progress)
        reply.readyRead.connect(self._on_download_chunk)
        reply.finished.connect(self._on_download_finished)

    def _on_download_progress(self, received: int, total: int) -> None:
        if total > 0:
            self._update_progress.setMaximum(total)
        self._update_progress.setValue(received)

    def _on_download_chunk(self) -> None:
        reply = self._update_reply
        if reply is None:
            return
        self._update_file.write(bytes(reply.readAll()))

    def _cancel_update_download(self) -> None:
        if self._update_reply is not None:
            self._update_reply.abort()

    def _on_download_finished(self) -> None:
        reply, self._update_reply = self._update_reply, None
        self._update_progress.reset()
        self._update_progress.deleteLater()
        try:
            self._update_file.close()
        except OSError:
            pass
        # NOTE: PySide6's QNetworkReply.NetworkError is a plain Python enum,
        # so bool(NoError) is True — never use it in a truthiness check.
        failed = (reply is None
                  or reply.error() != QNetworkReply.NetworkError.NoError)
        if failed:
            # Aborted by the user (dialog Cancel) or a network error.
            try:
                os.remove(self._update_dest)
            except OSError:
                pass
            if (reply is not None
                    and reply.error() != QNetworkReply.NetworkError.OperationCanceledError):
                QMessageBox.warning(
                    self.win, "Update",
                    "The download failed. You can retry from Help > Check for "
                    "Updates, or download the installer manually from the "
                    "releases page.")
            return
        size = os.path.getsize(self._update_dest)
        if self._update_expected_size and size != self._update_expected_size:
            QMessageBox.warning(
                self.win, "Update",
                f"The downloaded installer looks incomplete "
                f"({size:,} of {self._update_expected_size:,} bytes). "
                "Please download it manually from the releases page.")
            return
        self._install_update(self._update_dest)

    def _install_update(self, setup_exe: str) -> None:
        """Quit this app and run the downloaded installer (silent, elevated)."""
        answer = QMessageBox.question(
            self.win, "Install Update",
            "Download complete. Install now?\n\nOpenTruck will close, Windows "
            "may ask for permission to install, and the new version starts "
            "automatically when the update is finished.")
        if answer != QMessageBox.Yes:
            return
        # ShellExecuteW with the "runas" verb triggers the UAC elevation
        # prompt. The installer must be silent: the app has already exited by
        # the time the user answers the prompt, so there is nothing to see.
        params = "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS"
        rc = ctypes.windll.shell32.ShellExecuteW(
            0, "runas", setup_exe, params, None, 1)   # SW_SHOWNORMAL
        if rc > 32:
            # The installer is launching; exit so it can replace the files.
            self.win.statusBar().showMessage("Installing update...")
            QTimer.singleShot(500, self.win.close)
        else:
            # UAC declined (or blocked) — leave everything as it was.
            QMessageBox.information(
                self.win, "Update",
                "The update was not installed (permission was declined or "
                "blocked). OpenTruck is still running the current version.")

    def _totals_rows(self) -> list:
        """Flatten live data into the Totals & Counters rows (unit-converted)."""
        index: dict[str, tuple] = {}
        for addr, bucket in self.session.live.items():
            mod = self.session.modules.get(addr)
            src = self._key_text(addr)
            if mod is not None:
                src = f"{src}  {mod.label}"
            for name, (value, unit) in bucket.items():
                index.setdefault(name, (value, unit, src))
        system = units()
        rows = []
        for label, candidates in TOTALS_ROWS:
            found = next((index[c] for c in candidates if c in index), None)
            if found is None:
                rows.append((label, "\u2014", "", ""))
            else:
                value, unit, src = found
                cv, cu = convert(value, unit, system)
                rows.append((label, cv, cu, src))

        # Utilization - computed from the counters gathered above.
        def _n(name):
            if name in index:
                try:
                    return float(str(index[name][0]).replace(",", ""))
                except (TypeError, ValueError):
                    return None
            return None

        idle_h, eng_h = _n("Total Idle Hours"), _n("Total Engine Hours")
        if idle_h is not None and eng_h:
            rows.append(("Idle %", f"{idle_h / eng_h * 100:.0f}", "%", ""))
        else:
            rows.append(("Idle %", "\u2014", "", ""))

        dist = _n("Total Vehicle Distance")
        denom = _n("Total Vehicle Hours") or eng_h
        if dist is not None and denom:
            cv, cu = convert(f"{dist / denom:.1f}", "km/h", system)
            rows.append(("Average Road Speed", cv, cu, ""))
        else:
            rows.append(("Average Road Speed", "\u2014", "", ""))
        return rows

    def _show_totals_counters(self) -> None:
        """Open (or re-raise) the Totals & Counters panel."""
        dlg = getattr(self, "_totals_dialog", None)
        if dlg is None:
            dlg = TotalsCountersDialog(self.win, self._totals_rows)
            self._totals_dialog = dlg
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _aftertreatment_rows(self) -> list:
        """Assemble the Aftertreatment panel rows from both buses."""
        index: dict[str, tuple] = {}
        for addr, bucket in self.session.live.items():
            mod = self.session.modules.get(addr)
            src = self._key_text(addr)
            if mod is not None:
                src = f"{src}  {mod.label}"
            for name, (value, unit) in bucket.items():
                index.setdefault(name, (value, unit, src))
        system = units()

        # EGT sensors are OEM-application-specific: neutral SPN-identified
        # labels unless a curated per-OEM position entry matches this engine.
        eng = self.session.modules.get(0x00)
        eng_make = (eng.make if eng is not None else None) or ""
        eng_model = (eng.model if eng is not None else None) or ""
        positions, _egt_confirmed = egt_positions(eng_make, eng_model)
        wording = label_overrides(eng_make, eng_model)

        def apply_wording(label: str) -> str:
            for old, new in wording.items():
                label = label.replace(old, new)
            return label

        EGT_SPN = {"Exhaust Gas Temperature": 1737,
                   "Exhaust Gas Temperature 1": 3241,
                   "Exhaust Gas Temperature 2": 3249,
                   "Exhaust Gas Temperature 3": 3245}

        def egt_label(name: str) -> str:
            """Curated position name, else a neutral SPN-identified label."""
            spn = EGT_SPN.get(name)
            if spn in positions:
                return positions[spn]
            return neutral_egt_label(spn) if spn else name

        # Rows that carry no diagnostic value on this panel (redundant with
        # the positioned EGT sensors, or not wanted): never shown here.
        AFT_EXCLUDED = {
            "DPF Intermediate Gas Temperature", "DOC Differential Temperature",
            "Passive Regeneration",
        }

        def conv(v, u):
            return convert(v, u, system)

        def num(s):
            try:
                return float(str(s).replace(",", ""))
            except (TypeError, ValueError):
                return None

        # Differential pressure computed as inlet - outlet when both are present.
        delta = None
        if "DPF Intake Pressure" in index and "DPF Outlet Pressure" in index:
            pi = num(index["DPF Intake Pressure"][0])
            po = num(index["DPF Outlet Pressure"][0])
            if pi is not None and po is not None:
                delta = (f"{pi - po:.1f}", "kPa", index["DPF Intake Pressure"][2])

        rows = []
        shown = set()
        for category, label, candidates in AFT_ROWS:
            if label == "DPF Differential Pressure" and delta is not None:
                cv, cu = conv(delta[0], delta[1])
                rows.append((category, label + " (inlet-outlet)", cv, cu, delta[2]))
                shown.add("DPF Differential Pressure")
                continue
            found = next(((c, index[c]) for c in candidates if c in index), None)
            if found is None:
                rows.append((category, apply_wording(label), "\u2014", "", ""))
            else:
                name, (value, unit, src) = found
                shown.update(candidates)   # consume every alias of this row
                cv, cu = conv(value, unit)
                rows.append((category, apply_wording(label), cv, cu, src))

        # The EGT sensors: curated position names where confirmed (e.g. the
        # CAT C13 flame temperature), neutral SPN labels elsewhere
        # (shown after the fixed rows so the Other pass cannot duplicate them).
        for egt in ("Exhaust Gas Temperature", "Exhaust Gas Temperature 1",
                    "Exhaust Gas Temperature 2", "Exhaust Gas Temperature 3"):
            if egt not in index:
                continue
            value, unit, src = index[egt]
            cv, cu = conv(value, unit)
            rows.append(("Temperatures", egt_label(egt), cv, cu, src))
            shown.add(egt)

        # Any aftertreatment-named parameter not already shown, so nothing
        # hides - minus the excluded placeholders.
        for name, (value, unit, src) in index.items():
            if name in shown or name in AFT_EXCLUDED:
                continue
            if _is_aftertreatment_name(name):
                cv, cu = conv(value, unit)
                rows.append(("Other", name, cv, cu, src))
        return rows

    def _show_aftertreatment(self) -> None:
        """Open (or re-raise) the Aftertreatment panel."""
        dlg = getattr(self, "_aft_dialog", None)
        if dlg is None:
            dlg = AftertreatmentDialog(self.win, self._aftertreatment_rows)
            self._aft_dialog = dlg
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _abs_rows(self) -> list:
        """Assemble the ABS panel from the brake controller's messages."""
        import re
        addr = None
        for a, b in self.session.live.items():
            if ("EBS Amber Warning" in b or "Front Axle Speed" in b
                    or "ABS Active" in b):
                addr = a
                break
        bucket = self.session.live.get(addr, {}) if addr is not None else {}
        mod = self.session.modules.get(addr) if addr is not None else None
        src = ""
        if addr is not None:
            src = self._key_text(addr)
            if mod is not None:
                src = f"{src}  {mod.label}"
        system = units()

        def conv(v, u):
            return convert(v, u, system)

        rows: list = []

        def add(cat, label, name):
            if name in bucket:
                v, u = bucket[name]
                cv, cu = conv(v, u)
                rows.append((cat, label, cv, cu, src))
            else:
                rows.append((cat, label, "\u2014", "", ""))

        # Sensor / modulator detection. Prefer the ABS CI model string (e.g.
        # "HABS 4S/4M"); the sensor count is cross-checked against how many
        # wheel-speed positions actually report.
        sensors_ci = modulators_ci = None
        model = getattr(mod, "model", None) if mod is not None else None
        if model:
            mm = re.search(r"(\d)\s*[Ss]\s*[/\-\s]?\s*(\d)\s*[Mm]", model)
            if mm:
                sensors_ci, modulators_ci = mm.group(1), mm.group(2)
        wheels = [n for n in ("Wheel Speed FL", "Wheel Speed FR",
                              "Wheel Speed R1L", "Wheel Speed R1R",
                              "Wheel Speed R2L", "Wheel Speed R2R") if n in bucket]
        sensors_detected = len(wheels) if wheels else None
        cfg = (f"{sensors_ci}S/{modulators_ci}M"
               if sensors_ci and modulators_ci else "\u2014")
        rows.append(("Configuration", "Config (from CI)", cfg, "", src))
        rows.append(("Configuration", "Sensors detected (wheel speeds)",
                     str(sensors_detected) if sensors_detected is not None else "\u2014",
                     "", src))
        rows.append(("Configuration", "Modulators (from CI)",
                     modulators_ci or "\u2014", "", src))

        add("Wheel Speeds", "Front Axle (average)", "Front Axle Speed")
        add("Wheel Speeds", "Front Left", "Wheel Speed FL")
        add("Wheel Speeds", "Front Right", "Wheel Speed FR")
        add("Wheel Speeds", "Rear Axle 1 Left", "Wheel Speed R1L")
        add("Wheel Speeds", "Rear Axle 1 Right", "Wheel Speed R1R")
        add("Wheel Speeds", "Rear Axle 2 Left", "Wheel Speed R2L")
        add("Wheel Speeds", "Rear Axle 2 Right", "Wheel Speed R2R")

        add("Status", "ABS Active", "ABS Active")
        add("Status", "ABS Fully Operational", "ABS Fully Operational")
        add("Status", "EBS Amber Warning", "EBS Amber Warning")
        add("Status", "EBS Red Warning", "EBS Red Warning")
        add("Status", "Trailer ABS Status", "Trailer ABS Status")
        add("Status", "Trailer ABS Warning", "Trailer ABS Warning")

        rows.append(("Faults", "Active codes",
                     str(len(mod.active_dtcs)) if mod is not None else "\u2014", "", src))
        rows.append(("Faults", "Stored codes",
                     str(len(mod.previous_dtcs)) if mod is not None else "\u2014", "", src))
        return rows

    def _show_abs(self) -> None:
        """Open (or re-raise) the ABS panel."""
        dlg = getattr(self, "_abs_dialog", None)
        if dlg is None:
            dlg = AftertreatmentDialog(self.win, self._abs_rows, title="ABS")
            self._abs_dialog = dlg
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _show_about(self) -> None:
        """Show an About box with the running version and license note."""
        QMessageBox.about(
            self.win, "About OpenTruck",
            f"<b>OpenTruck {full_version()}</b><br><br>"
            "A J1939 / J1708 diagnostics reader for heavy-duty vehicles "
            "and off-highway machines, plus OBD-II for 2008+ cars and light "
            "pickups, driven through any RP1210 adapter.<br><br>"
            "Licensed under the PolyForm Noncommercial License 1.0.0: free for "
            "personal, educational and other noncommercial use. Commercial use "
            "requires a separate license from the author. "
            "See the LICENSE file for details."
        )

    def _generate_report(self) -> None:
        """Generate a PDF diagnostic report from the connected vehicle data."""
        if self._obd_state is not None:
            QMessageBox.information(
                self.win, "Report Generation",
                "PDF reports are not supported in OBD-II mode yet.")
            return
        if not self._first_frame_seen:
            QMessageBox.warning(
                self.win, "Report Generation",
                "No vehicle data available. Connect to a vehicle or replay a "
                "log file first, then generate the report."
            )
            return

        # Vehicle identity (mirrors _refresh_vehicle_info's cascade). Prefer the
        # VIN's WMI as the vehicle OEM "Make"; fall back to the engine CI make
        # only when there is no VIN (or its WMI is unknown). The VIN carries no
        # model name, so the engine's model is only used in that fallback.
        vin = self.session.vin or None
        eng = self.session.modules.get(0x00)
        eng_make = model = None
        if eng is not None:
            eng_make = friendly_make(eng.make) if eng.make else None
            if not eng_make and eng.name is not None:
                eng_make = manufacturer_name(eng.name.manufacturer)
            model = eng.model
        vin_make = wmi_make(vin) if vin else None
        if vin_make:
            make, model = vin_make, None
        else:
            make = eng_make
        year = model_year(vin) if vin else None

        # Components (engine first), using each module's friendly label.
        # Unidentified modules with nothing to report are omitted, matching
        # the on-screen module list.
        report_modules = self.session.visible_modules()
        components = []
        for addr in sorted(report_modules, key=lambda a: (a != 0x00, a)):
            m = report_modules[addr]
            name, _, desc = m.label.partition("\u2014")
            serial = m.serial or ""
            if m.ecu_part:
                serial = f"{serial} / {m.ecu_part}" if serial else m.ecu_part
            components.append({
                "name": f"{name.strip()} ({self._bus_tag(addr)})",
                "description": desc.strip(),
                "serial": serial,
                "software": m.software_id or "",
            })

        active_dtcs = self._report_dtcs(active=True)
        inactive_dtcs = self._report_dtcs(active=False)
        totals = self._report_totals()
        lamps = self._report_lamps()

        ident = (eng.serial if (eng is not None and eng.serial) else
                 make or model or vin or "OpenTruck")
        default_name = f"{_slug(str(ident))}_{_timestamp()}.pdf"

        filename, _ = QFileDialog.getSaveFileName(
            self.win, "Generate Diagnostic Report", default_name,
            "PDF Files (*.pdf);;All Files (*)",
        )
        if not filename:
            return

        if generate_report(
            filename,
            vin=vin,
            make=make,
            model=model,
            year=year,
            components=components,
            totals=totals,
            lamps=lamps,
            active_dtcs=active_dtcs,
            inactive_dtcs=inactive_dtcs,
        ):
            self.win.statusBar().showMessage(f"Report generated: {filename}")
            self.win.statusBar().messageChanged.emit()
            QMessageBox.information(
                self.win, "Report Generated",
                f"Diagnostic report saved to:\n{filename}"
            )
        else:
            QMessageBox.warning(self.win, "Report Generation Failed",
                                "Failed to generate PDF report.")

    def _report_dtcs(self, active: bool) -> list:
        """Build active/inactive DTC rows for the report."""
        out = []
        for addr in sorted(self.session.modules):
            m = self.session.modules[addr]
            # Role for code resolution: the NAME's function when there is one,
            # otherwise the address-derived role (so a module that never claims
            # an address still gets the right generic/Refer-to-OEM decision).
            component = (function_name(m.name.function)
                         if m.name is not None and m.name.function in FUNCTION_NAMES
                         else preferred_address_name(a))
            # Module identity for code resolution: its own CI make, else the
            # chassis make (a body module reports the chassis maker's codes).
            make = (friendly_make(m.make) if m.make
                    else getattr(m, "vehicle_make", None))
            mfr = m.name.manufacturer if m.name is not None else None
            for d in (m.active_dtcs if active else m.previous_dtcs):
                out.append({
                    "module": m.label,
                    "address": self._key_text(addr),
                    "description": d.get("desc") or resolve_code_description(
                        d["spn"], d["fmi"], component=component, make=make,
                        mfr=mfr, cm=d.get("cm", 0)),
                    "spn": d.get("spn"),
                    "fmi": d.get("fmi"),
                    "count": d.get("occ", 0),
                })
        out.sort(key=lambda d: (d["module"], d["spn"]))
        return out

    def _report_totals(self) -> list:
        """Collect totals/counters for the report: engine hours, idle hours,
        mileage and the emissions-system totals. Every row is always shown,
        using an em-dash when the vehicle doesn't report that value."""
        wanted = (
            ("Total Engine Hours", ("Total Engine Hours",)),
            ("Idle Hours", ("Total Idle Hours", "Engine Idle Hours")),
            ("Odometer (Distance)", ("Total Vehicle Distance", "Total Distance")),
            ("DPF Soot Load", ("DPF Soot Load",)),
            ("DPF Ash Load", ("DPF Ash Load",)),
            ("DEF Tank Level", ("DEF Tank Level",)),
            ("Active Regen Time", ("Active Regen Time",)),
            ("Active Regens (trip)", ("Active Regens (trip)",)),
            ("Passive Regens (trip)", ("Passive Regens (trip)",)),
            ("DPF Trip Fuel Used", ("DPF Trip Fuel Used",)),
        )
        index: dict[str, tuple] = {}
        for addr in sorted(self.session.live, key=lambda a: (a != 0x00, a)):
            for name, (value, unit) in self.session.live[addr].items():
                index.setdefault(name, (value, unit))
        system = units()
        totals = []
        for label, candidates in wanted:
            found = next((index[c] for c in candidates if c in index), None)
            if found is None:
                totals.append((label, "\u2014"))
            else:
                cv, cu = convert(found[0], found[1], system)
                totals.append((label, f"{cv} {cu}".strip()))
        return totals

    def _report_lamps(self) -> list:
        """Collect lamp states as (label, state) pairs."""
        names = (
            ("mil", "Malfunction Indicator Lamp"),
            ("red", "Red Stop Lamp"),
            ("amber", "Amber Warning Lamp"),
            ("protect", "Protect Lamp"),
        )
        m = self.session.modules.get(0x00)
        if m is None or not m.lamps:
            for x in self.session.modules.values():
                if x.lamps:
                    m = x
                    break
        if m is None or not m.lamps:
            return []
        return [(label, "On" if m.lamps.get(key) else "Off") for key, label in names]

    # -------------------------------------------------------- OBD-II mode --- #
    def _start_obd(self, adapter_code: str) -> None:
        """Switch to light-duty OBD-II (J1979) mode on the given adapter."""
        self._obd_worker = ObdWorker(adapter_code)
        self._obd_thread = QThread(self.win)
        self._obd_worker.moveToThread(self._obd_thread)
        self._obd_worker.state.connect(self._on_obd_state)
        self._obd_worker.failed.connect(self._on_obd_failed)
        self._obd_thread.started.connect(self._obd_worker.run)
        self._obd_thread.start()

    def _on_obd_state(self, state: dict) -> None:
        first = self._obd_state is None
        self._obd_state = state
        if first:
            self._obd_probing = False
            self._connect_timeout.stop()
            self._first_frame_seen = True     # suppress the no-data watchdog
            self._set_connected(True)
            self.win.statusBar().showMessage(
                f"Connected (OBD-II) - {len(state.get('ecus', []))} ECU(s)")
        self._refresh()

    def _on_obd_failed(self, reason: str) -> None:
        w, th = self._obd_worker, self._obd_thread
        self._obd_worker = None
        self._obd_thread = None
        self._obd_state = None
        self._obd_probing = False
        if w is not None:
            w.stop_capture()
            w.request_stop()
        if self._obd_capture_path:
            self._obd_capture_path = None
            self._capture_active = False
            self.act_capture.setText("Start Capture")
        if th is not None:
            th.quit()
            th.wait()
        self._set_connected(False)
        if reason.startswith("obd-connect"):
            QMessageBox.warning(
                self.win, "Connection Failed",
                "Could not connect to the adapter for OBD-II.\n\n" + reason)
        else:
            QMessageBox.warning(
                self.win, "No Data Received",
                "No data received from vehicle.\n\n"
                "Nothing answered on either the heavy-duty (J1939/J1708) or "
                "the light-duty OBD-II bus.\n\n"
                "  \u2022  Check the key is ON.\n"
                "  \u2022  Check the adapter is seated in the connector.\n"
                "  \u2022  Heavy-duty: 9-pin / 6-pin diagnostic connector.\n"
                "  \u2022  Cars & light pickups: 16-pin OBD-II port under the dash.")
        self._show_connection_dialog()

    def _refresh_obd(self) -> None:
        """Render the GUI from OBD-II state (replaces the J1939 rendering)."""
        st = self._obd_state or {}
        ecus = st.get("ecus", [])
        names = st.get("ecu_names", {})
        sig = ("obd", tuple(sorted((e, names.get(e, "")) for e in ecus)))
        if sig != self._last_components:
            self._last_components = sig
            self.component_list.blockSignals(True)
            self.component_list.clear()
            self.component_list.addItem(QListWidgetItem("OBD-II (SAE J1979)"))
            for e in sorted(ecus):
                name = names.get(e) or "ECU"
                it = QListWidgetItem(f"{name}  (OBD-II 0x{e:X})")
                it.setData(Qt.UserRole, f"obd:{e:X}")
                self.component_list.addItem(it)
            self.component_list.blockSignals(False)
            # Select the first ECU so the live table shows that module's data.
            if self.component_list.count() > 1:
                self.component_list.setCurrentRow(1)
        self._refresh_table()
        self._refresh_live_data()
        self._refresh_vehicle_info()
        self._refresh_lamps()

    def _refresh_obd_table(self) -> None:
        """Fault-code table in OBD-II mode: stored + pending P-codes."""
        t = self.codes_table
        st = self._obd_state or {}
        # OBD-II terminology (there is no J1939-style "active" here):
        # Mode 03 confirmed codes are the ones that turn the MIL on,
        # Mode 07 pending = seen once, Mode 0A permanent = sticks until the
        # repair is verified in use (Mode 04 cannot clear them).
        rows = [("Confirmed (MIL)", c) for c in st.get("stored", [])]
        rows += [("Pending", c) for c in st.get("pending", [])]
        rows += [("Permanent", c) for c in st.get("permanent", [])]
        sig = tuple(rows)
        if sig == getattr(self, "_last_obd_codes_sig", None):
            return
        self._last_obd_codes_sig = sig
        t.setRowCount(len(rows))
        brand = st.get("brand")
        for r, (kind, code) in enumerate(rows):
            desc = mfg_dtc_description(code, brand) or obd_dtc_description(code)
            cells = ("OBD-II", "ISO 15765", code, "", desc, kind,
                     "Emissions (OBD-II)")
            for c, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if c == 0:
                    item.setData(Qt.UserRole, ("obd", kind, code))
                t.setItem(r, c, item)

    def _refresh_obd_live(self) -> None:
        """Live-data table in OBD-II mode: per selected ECU (or merged)."""
        t = self.live_table
        live_by = (self._obd_state or {}).get("live_by_ecu", {})
        sel = self._obd_selected
        live = live_by.get(sel) if (sel is not None and sel in live_by) \
            else (self._obd_state or {}).get("live", {})
        sys = units()
        rows = []
        for label, entry in sorted(live.items()):
            value, unit = entry if isinstance(entry, tuple) and len(entry) == 2 \
                else (entry, "")
            try:
                vtxt, unit_txt = convert(str(value), unit, sys)
            except Exception:
                vtxt, unit_txt = str(value), unit
            rows.append((label, vtxt, unit_txt))
        sig = (tuple(rows), sys)
        if sig == self._last_live_sig:
            return
        self._last_live_sig = sig
        t.setRowCount(len(rows))
        for r, (label, vtxt, unit_txt) in enumerate(rows):
            for c, text in enumerate((label, vtxt, unit_txt)):
                t.setItem(r, c, QTableWidgetItem(text))

    def _disconnect(self) -> None:
        if self._obd_worker is not None:
            self._obd_worker.stop_capture()
            self._obd_worker.request_stop()
        if self._obd_capture_path:
            self._obd_capture_path = None
            self._capture_active = False
            self.act_capture.setText("Start Capture")
        if self._obd_thread is not None:
            self._obd_thread.quit()
            self._obd_thread.wait()
        self._obd_worker = None
        self._obd_thread = None
        self._obd_state = None
        self._obd_command = None
        self._obd_probing = False
        if self._worker is not None:
            self._worker.request_stop()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
        self._worker = None
        self._thread = None
        self._source = None
        self._logger = None
        self.act_logging.setText("Start Logging...")
        self._stop_csv_logging()
        if self._capture_active:
            self._capture_tick()
            self._capture_active = False
        self.act_capture.setText("Start Capture")
        self._capture_timer.stop()
        # Clean up preferences dialog if open
        if hasattr(self, '_pref_dialog') and self._pref_dialog:
            del self._pref_dialog
        self._discovery_timer.stop()
        self._cancel_sweep()
        self._connect_timeout.stop()
        self._watchdog.stop()
        self._first_frame_seen = False
        self._clear_grace_until = 0.0
        self._set_connected(False)
        self.win.statusBar().showMessage("Disconnected")

    def _engine_name(self) -> str:
        """A filename-safe engine/machine name (CI make -> NAME mfr -> VIN WMI).

        Falls back to a generic "engine" when the vendor can't be resolved, and
        (worst case) to the first module's hex source address.
        """
        eng = self.session.modules.get(0x00)
        name = None
        if eng is not None:
            if eng.make:
                name = friendly_make(eng.make)
            if not name and eng.name is not None:
                name = manufacturer_name(eng.name.manufacturer)
        if not name and self.session.vin:
            name = wmi_make(self.session.vin)
        if name:
            return _slug(name)
        if eng is not None:
            return "engine"
        if self.session.modules:
            return "0x%02x" % sorted(self.session.modules)[0]
        return "vehicle"

    def _toggle_logging(self) -> None:
        """Start/stop human-readable CSV logging of selected live-data params."""
        if self._csv_fh is not None:
            self._stop_csv_logging()
            self.act_logging.setText("Start Logging...")
            self.win.statusBar().showMessage("Logging stopped")
            return
        # Collect every live-data parameter currently being broadcast - from
        # the OBD-II ECUs in OBD mode, or from the J1939/J1708 modules.
        candidates = []
        if self._obd_state is not None:
            live_by = self._obd_state.get("live_by_ecu") or {}
            names = self._obd_state.get("ecu_names") or {}
            for ecu in sorted(live_by):
                label = names.get(ecu) or f"ECU 0x{ecu:03X}"
                for name in sorted(live_by[ecu]):
                    candidates.append((ecu, name, label))
        elif self._source is None:
            QMessageBox.information(
                self.win, "Logging",
                "Connect to a vehicle first.")
            return
        else:
            for addr in sorted(self.session.modules):
                mod = self.session.modules[addr]
                for name in sorted(self.session.live.get(addr, {})):
                    candidates.append((addr, name, mod.label))
        if not candidates:
            QMessageBox.information(
                self.win, "Logging",
                "No live-data parameters are available yet.\n\n"
                "Connect to a vehicle and wait for the Live Data list to "
                "populate, then try again.")
            return
        dlg = ParameterSelectDialog(self.win, candidates)
        if dlg.exec() != QDialog.Accepted:
            return
        selected = dlg.selected()
        if not selected:
            return
        self._start_csv_logging(selected)

    def _start_csv_logging(self, params: list[tuple[int, str]]) -> None:
        d = os.path.join(_log_root(), "vehicle logs")
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, f"{self._engine_name()}_{_timestamp()}.csv")
        self._csv_fh = open(path, "w", encoding="utf-8")
        self._csv_fh.write("timestamp,module,parameter,value,unit\n")
        self._csv_fh.flush()
        self._csv_path = path
        self._csv_params = params
        self._csv_timer.start(250)
        self.act_logging.setText("Stop Logging")
        self.win.statusBar().showMessage(f"Logging to {path}")

    @staticmethod
    def _csv_field(text: str) -> str:
        if any(c in text for c in ',"\n'):
            return '"' + text.replace('"', '""') + '"'
        return text

    def _csv_tick(self) -> None:
        if self._csv_fh is None:
            return
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        for addr, name in self._csv_params:
            label, entry = self._csv_entry(addr, name)
            if entry is None:
                continue
            value, unit = entry
            value, unit = convert(value, unit, units())
            row = [ts, label, name, value, unit]
            self._csv_fh.write(
                ",".join(self._csv_field(x) for x in row) + "\n")
        try:
            self._csv_fh.flush()
        except Exception:                 # noqa: BLE001
            pass

    def _csv_entry(self, addr: int, name: str):
        """(label, (value, unit)) for a CSV sample, on either bus or OBD-II."""
        if self._obd_state is not None:
            live_by = self._obd_state.get("live_by_ecu") or {}
            names = self._obd_state.get("ecu_names") or {}
            label = names.get(addr) or f"ECU 0x{addr:03X}"
            return label, (live_by.get(addr) or {}).get(name)
        mod = self.session.modules.get(addr)
        label = mod.label if mod is not None else f"0x{addr:02X}"
        return label, self.session.live.get(addr, {}).get(name)

    def _stop_csv_logging(self) -> None:
        self._csv_timer.stop()
        self._csv_params = []
        if self._csv_fh is not None:
            try:
                self._csv_fh.flush()
                self._csv_fh.close()
            except Exception:             # noqa: BLE001
                pass
            self._csv_fh = None
        self._csv_path = None

    def _toggle_raw_capture(self) -> None:
        """Start/stop raw-frame capture (replay-format .log)."""
        if self._obd_state is not None:
            self._toggle_obd_capture()
            return
        if self._capture_active:
            # Stop
            self._capture_timer.stop()
            self._capture_tick()
            self._capture_active = False
            self.act_capture.setText("Start Capture")
            self.win.statusBar().showMessage("Raw capture stopped")
            return

        logger = self._logger
        if logger is None:
            QMessageBox.information(self.win, "Capture",
                                    "Connect to a vehicle first.")
            return

        d = os.path.join(_log_root(), "raw captures")
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, f"{self._engine_name()}_{_timestamp()}.log")
        logger.start(path)
        self._capture_active = True
        self.act_capture.setText("Stop Capture")
        self.win.statusBar().showMessage(
            f"Capturing raw frames (J1939 + J1708 + CAN2) -> {path} "
            "(toggle to stop)")

    def _toggle_obd_capture(self) -> None:
        """Start/stop a raw CAN capture while in OBD-II mode.

        Every frame seen on the DLC (including other modules' chatter) is
        written by the OBD worker; the file is analysis-only - the replay
        source does not read the ``obd`` line format.
        """
        worker = self._obd_worker
        if worker is None:
            QMessageBox.information(self.win, "Capture",
                                    "Connect to a vehicle first.")
            return
        if self._obd_capture_path:
            worker.stop_capture()
            path, self._obd_capture_path = self._obd_capture_path, None
            self._capture_active = False
            self.act_capture.setText("Start Capture")
            self.win.statusBar().showMessage(f"Raw capture stopped ({path})")
            return
        d = os.path.join(_log_root(), "raw captures")
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, f"obd_{_timestamp()}.log")
        try:
            worker.start_capture(path)
        except OSError as exc:
            QMessageBox.warning(self.win, "Capture",
                                f"Could not start capture: {exc}")
            return
        self._obd_capture_path = path
        self._capture_active = True
        self.act_capture.setText("Stop Capture")
        self.win.statusBar().showMessage(
            f"Capturing raw OBD-II CAN frames -> {path} (toggle to stop)")

    def _capture_tick(self) -> None:
        """Flush the capture log every 250 ms so it's readable while running."""
        if self._logger is not None and hasattr(self._logger, '_fh'):
            with self._logger._lock:
                if self._logger._fh is not None:
                    try:
                        self._logger._fh.flush()
                    except Exception:               # noqa: BLE001
                        pass

    def _sniff_bus(self) -> None:
        """Developer > Sniff Bus (raw): dump the adapter's raw receive bytes.

        Opens a separate connection (so it also works when the main link is
        dead) and reads raw buffers with no J1939/J1708 decoding for ~4 s. This
        distinguishes a dead bus from a wrong-protocol/baud one, and writes a
        hex dump to ``<log root>/raw captures/``.
        """
        if getattr(self, '_sniff_timer', None) is not None:
            return                          # a sniff is already in progress
        from rp1210 import (get_adapter, list_adapters,
                            RP1210Source, BridgedRP1210Source)

        a = None
        if self._rp1210_code:
            a = get_adapter(self._rp1210_code)
        if a is None:
            adapters = list_adapters()
            if not adapters:
                QMessageBox.warning(self.win, "Sniff Bus",
                                    "No RP1210 adapter found on this machine.")
                return
            a = adapters[0]

        # Sniff J1939:Baud=Auto explicitly (ignores the selected protocol) so a
        # 500k/1M vehicle is seen as well as 250k.
        j1939 = a.protocol
        if a.dll_path:
            src = RP1210Source(a.dll_path, j1939, a.device_id)
        else:
            src = BridgedRP1210Source(a.bridge_dll, j1939, a.device_id)
        try:
            src.connect()
        except Exception as exc:                       # noqa: BLE001
            try:
                src.close()
            except Exception:                          # noqa: BLE001
                pass
            QMessageBox.warning(self.win, "Sniff Bus",
                                f"Could not open a raw link:\n{exc}")
            return

        self._sniff_src = src
        self._sniff_lines: list[str] = []
        self._sniff_deadline = time.time() + 4.0
        self._sniff_timer = QTimer(self.win)
        self._sniff_timer.timeout.connect(self._sniff_tick)
        self._sniff_timer.start(20)
        self.win.statusBar().showMessage("Sniffing raw bus traffic...")

    def _sniff_tick(self) -> None:
        """Poll the sniff source for raw buffers until the deadline."""
        h = self._sniff_src.read_raw_hex()
        if h:
            self._sniff_lines.append(h)
        if time.time() >= self._sniff_deadline:
            self._finish_sniff()

    def _finish_sniff(self) -> None:
        timer = self._sniff_timer
        self._sniff_timer = None
        if timer is not None:
            timer.stop()
        src = self._sniff_src
        self._sniff_src = None
        if src is not None:
            try:
                src.close()
            except Exception:                          # noqa: BLE001
                pass
        lines = self._sniff_lines
        self._sniff_lines = []

        path = "(could not write dump file)"
        try:
            d = os.path.join(_log_root(), "raw captures")
            os.makedirs(d, exist_ok=True)
            path = os.path.join(d, f"sniff_{_timestamp()}.hex")
            with open(path, "w", encoding="ascii") as f:
                f.write("\n".join(lines) + ("\n" if lines else ""))
        except OSError:
            pass

        self.win.statusBar().showMessage("Raw sniff finished")
        if lines:
            QMessageBox.information(
                self.win, "Sniff Bus",
                f"Captured {len(lines)} raw buffers — the bus IS carrying traffic.\n\n"
                f"Hex dump saved to:\n{path}")
        else:
            QMessageBox.warning(
                self.win, "Sniff Bus",
                "No raw bytes captured in 4 seconds — the bus looks silent.\n\n"
                "Check the vehicle key is ON, the adapter is seated in the "
                "diagnostic connector, and try the J1708 protocol (this truck "
                "may be a J1708-only vehicle).\n\n"
                f"Hex dump saved to:\n{path}")

    def shutdown(self) -> None:
        """Stop the reader thread cleanly (idempotent). Called on app quit so
        the background QThread does not outlive the window and crash on exit."""
        if self._thread is not None:
            self._disconnect()
        # Remember the GUI layout (splitter + column widths) for next launch.
        try:
            self._save_ui_layout()
        except Exception:
            pass   # layout must never block shutdown

    # -------------------------------------------------------- processing --- #
    def _on_frame(self, tagged) -> None:
        if tagged.protocol == "can2":
            return      # raw-CAN channel: capture-only (logged at the source)
        self.session.handle(tagged)
        # Track which protocol produced data (for the per-bus LEDs) and, if this
        # is the first frame on any protocol, declare the link live.
        if tagged.protocol == "j1708":
            if not self._seen_j1708:
                self._seen_j1708 = True
                if self._first_frame_seen:
                    self._set_connected(True)   # J1708 bus just came alive
        elif not self._seen_j1939:
            self._seen_j1939 = True

        # First real frame proves the link is actually carrying vehicle data;
        # only now is it safe to go green and cancel the no-data watchdog.
        if not self._first_frame_seen:
            self._first_frame_seen = True
            self._connect_timeout.stop()
            self._set_connected(True)
            self.win.statusBar().showMessage("Connected")
            # Once the link is live, sweep every source address for silent
            # ECUs that might hold the VIN / component ID (live J1939 only).
            if self._source_kind == "rp1210":
                self._start_sweep()
        # Feed the deadman watchdog once the link is live. Live RP1210 links
        # only: a replay/simulator source has no 'vehicle went silent' notion
        # (a replay simply ends), so it must not trip the lost-link error.
        if self._source_kind == "rp1210":
            self._watchdog.start(WATCHDOG_MS)

    def _on_error(self, msg: str) -> None:
        """The reader thread surfaced a fatal error (adapter unplugged, bus
        lost, or an RP1210 read error)."""
        self._connection_lost(f"The connection to the vehicle was lost.\n\n{msg}")

    def _on_watchdog_timeout(self) -> None:
        """Fired when frames stop arriving mid-session (a silent bus loss the
        adapter reports as 'no message' rather than a hard error)."""
        # A DTC clear makes some ECUs re-run their self-test and go quiet for a
        # few seconds; don't treat that as a lost link. Re-arm and keep waiting.
        if time.monotonic() < self._clear_grace_until:
            self._watchdog.start(WATCHDOG_MS)
            return
        self._connection_lost(
            f"The vehicle stopped sending data.\n\n"
            f"No messages were received for {WATCHDOG_MS // 1000} seconds. "
            "Check that the adapter is still connected and the vehicle bus "
            "is powered.")

    def _connection_lost(self, detail: str) -> None:
        """Common teardown for a lost link: stop the reader, blank every value,
        and put up a single 'Connection Lost' dialog."""
        self._disconnect()
        self._clear_screen()
        self.win.statusBar().showMessage("Connection lost")
        QMessageBox.critical(
            self.win, "Connection Lost",
            f"{detail}\n\nReconnect from the Connection menu when you're ready.")

    def _clear_screen(self) -> None:
        """Blank every vehicle value (module list, fault codes, live data,
        identification, lamps, graph) so a lost connection leaves no stale
        data on screen."""
        self.session = CombinedSession()
        self._seen_j1939 = False
        self._seen_j1708 = False
        self._current_addr = None
        self._graph_param = None
        self._last_components = None
        self._last_table_sig = None
        self._last_live_sig = None
        self.component_list.clear()
        self.codes_table.setRowCount(0)
        self.live_table.setRowCount(0)
        self.live_graph.reset()
        self._refresh_vehicle_info()
        self._refresh_lamps()

    def _on_connect_timeout(self) -> None:
        """Fired when source.connect() succeeded but no frames arrived, i.e.
        there is no real vehicle on the (J1939/J1708) bus. Before giving up,
        probe the light-duty OBD-II (J1979) bus on the same adapter: many
        vehicles - and every 2008+ car/light pickup - speak OBD-II instead.
        If that also finds nothing, revert to red, tell the user, and hand
        them back to the connection dialog."""
        if self._first_frame_seen:
            return
        self._disconnect()
        if self._source_kind == "rp1210" and not self._obd_tried \
                and self._rp1210_code:
            self._obd_tried = True
            self._obd_probing = True
            self._set_connected(False)   # renders the probing state
            self._start_obd(self._rp1210_code)
            return
        QMessageBox.warning(
            self.win, "No Data Received",
            "No data received from vehicle.\n\n"
            "The adapter connected, but no vehicle data was received "
            "(both the J1939 and J1708 buses appear to be silent).\n\n"
            "Common causes:\n"
            "  \u2022  Vehicle key is OFF \u2014 most controllers only broadcast "
            "with the key ON.\n"
            "  \u2022  The diagnostic connector's CAN/J1708 pins aren't wired "
            "through the adapter.\n"
            "  \u2022  The adapter is not seated firmly in the connector.\n\n"
            "Check the key is ON and the adapter is seated, then try again. "
            "You can also choose the Simulator or a Replay Log instead.")
        self._show_connection_dialog()

    # ---------------------------------------------------------- refresh --- #
    def _refresh(self) -> None:
        if self._obd_state is not None:
            self._graph_tick()   # the graph feeds off this tick - do not skip
            self._refresh_obd()
            return
        # Only modules with something to show: identified, live data, or
        # fault codes. Unknown addresses that report nothing are ignored.
        modules = self.session.visible_modules()
        addrs = sorted(modules)
        sig = [(a, modules[a].label) for a in addrs]
        if sig != self._last_components:
            self._last_components = sig
            self.component_list.blockSignals(True)
            self.component_list.clear()
            for a, _label in sig:
                # Bus first (J1939 / J1708) - the numeric address is clutter in
                # the normal view, so it moves to the tooltip.
                it = QListWidgetItem(f"{self._bus_tag(a)}  {modules[a].label}")
                it.setData(Qt.UserRole, a)
                it.setToolTip(self._key_text(a))
                self.component_list.addItem(it)
            if self._current_addr in addrs:
                self.component_list.setCurrentRow(addrs.index(self._current_addr))
            elif addrs:
                self.component_list.setCurrentRow(0)
            self.component_list.blockSignals(False)
            cur = self.component_list.currentItem()
            self._current_addr = cur.data(Qt.UserRole) if cur else None
        self._refresh_table()
        self._refresh_live_data()
        self._refresh_vehicle_info()
        self._refresh_lamps()
        self._graph_tick()
        self.win.statusBar().showMessage(f"{len(addrs)} module(s) discovered")

    def _on_module_changed(self, current, _previous) -> None:
        data = current.data(Qt.UserRole) if current else None
        if isinstance(data, str) and data.startswith("obd:"):
            try:
                self._obd_selected = int(data.split(":")[1], 16)
            except (ValueError, TypeError):
                self._obd_selected = None
            self._current_addr = None
            self._graph_param = None
            self.live_graph.reset()
            self._refresh_live_data()
            return
        self._obd_selected = None
        self._current_addr = data
        self._graph_param = None
        self.live_graph.reset()
        self._refresh_table()
        self._refresh_live_data()

    def _refresh_table(self) -> None:
        if self._obd_state is not None:
            self._refresh_obd_table()
            return
        t = self.codes_table
        # Show ALL codes from ALL modules (not just the selected one). Every row
        # carries the full identity: the reporting module + its source address
        # (SA, or MID on J1708), the SPN (or J1708 PID/SID), and the FMI — so
        # identical SPN/FMI codes from different modules never collapse. All
        # ACTIVE codes are listed first, then all INACTIVE.
        rows = []
        for kind, attr in (("Active", "active_dtcs"),
                           ("Inactive", "previous_dtcs")):
            for a in sorted(self.session.modules):
                m = self.session.modules[a]
                for d in getattr(m, attr):
                    rows.append((a, kind, d))
        sig = tuple((a, kind, d["spn"], d["fmi"], d["occ"])
                    for a, _kind, d in rows)
        if sig == self._last_table_sig:
            return
        self._last_table_sig = sig
        t.setRowCount(len(rows))
        for r, (a, kind, d) in enumerate(rows):
            m = self.session.modules[a]
            # Role for code resolution: the NAME's function when there is one,
            # otherwise the address-derived role (so a module that never claims
            # an address still gets the right generic/Refer-to-OEM decision).
            component = (function_name(m.name.function)
                         if m.name is not None and m.name.function in FUNCTION_NAMES
                         else preferred_address_name(a))
            # Module identity for code resolution: its own CI make, else the
            # chassis make (a body module reports the chassis maker's codes).
            make = (friendly_make(m.make) if m.make
                    else getattr(m, "vehicle_make", None))
            mfr = m.name.manufacturer if m.name is not None else None
            desc = d.get("desc") or resolve_code_description(
                d["spn"], d["fmi"], component=component, make=make,
                mfr=mfr, cm=d.get("cm", 0))
            num = d.get("num", str(d["spn"]))
            cells = (m.label, self._bus_tag(a), num, str(d["fmi"]), desc,
                     kind, fmi_name(d["fmi"]))
            for c, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if c == 0:
                    item.setData(Qt.UserRole, (a, kind, d))
                if c == 1:
                    # The address stays available as a tooltip: useful when
                    # debugging, clutter in the normal view.
                    item.setToolTip(self._key_text(a))
                t.setItem(r, c, item)

    def _refresh_live_data(self) -> None:
        if self._obd_state is not None:
            self._refresh_obd_live()
            return
        t = self.live_table
        a = self._current_addr
        values = self.session.live.get(a, {}) if (a is not None and a in self.session.modules) else {}
        rows = sorted(values.items())
        sys = units()
        # Maker wording for live parameters (display only - the stored key stays
        # canonical so the graph, CSV params and report lookups keep working).
        mod = self.session.modules.get(a) if a is not None else None
        make = friendly_make(mod.make) if (mod is not None and mod.make) else None
        mfr = mod.name.manufacturer if (mod is not None and mod.name is not None) else None
        display = {name: resolve_live_label(name, make, mfr) for name, _ in rows}
        # Include the unit system and the display labels in the render signature
        # so a Preferences change or a newly identified module re-renders.
        sig = ([(n, display[n]) for n, _ in rows], sys)
        if sig == self._last_live_sig:
            return
        self._last_live_sig = sig
        t.setRowCount(len(rows))
        for r, (name, (value, unit)) in enumerate(rows):
            value, unit = convert(value, unit, sys)
            item = QTableWidgetItem(display[name])
            item.setData(Qt.UserRole, name)      # canonical key
            t.setItem(r, 0, item)
            t.setItem(r, 1, QTableWidgetItem(value))
            t.setItem(r, 2, QTableWidgetItem(unit))

        # Re-apply the selection highlight for the graphed parameter (the table
        # is rebuilt every tick, which drops the selection).
        if self._graph_param is not None:
            for r in range(t.rowCount()):
                it = t.item(r, 0)
                if it is not None and it.data(Qt.UserRole) == self._graph_param:
                    t.selectRow(r)
                    break

    def _on_live_click(self, row: int, _col: int) -> None:
        """Graph the live-data row the user clicked."""
        name_item = self.live_table.item(row, 0)
        if name_item is None:
            return
        name = name_item.data(Qt.UserRole) or name_item.text()
        unit_item = self.live_table.item(row, 2)
        unit = unit_item.text() if unit_item is not None else ""
        if name != self._graph_param:
            self._graph_param = name
            self.live_graph.set_parameter(name, unit)

    def _graph_tick(self) -> None:
        """Feed the latest value of the selected parameter into the graph."""
        if self._graph_param is None:
            return
        if self._obd_state is not None:
            values = (self._obd_state or {}).get("live", {})
        else:
            a = self._current_addr
            values = self.session.live.get(a, {}) if (a is not None and a in self.session.modules) else {}
        entry = values.get(self._graph_param)
        if entry is None:
            return
        value_str, unit = entry
        try:
            value_str, unit = convert(str(value_str), unit, units())
        except Exception:
            value_str, unit = str(value_str), unit
        try:
            val = float(value_str)
        except ValueError:
            return                      # non-numeric (e.g. gear name)
        # Keep the graph's Y-axis label in sync with the active unit system.
        self.live_graph.set_unit(unit)
        self.live_graph.add_sample(time.monotonic(), val)

    def _request_pgn(self, pgn: int) -> None:
        """Ask every ECU to send one specific PGN.

        Sent both globally (0xFF) and directed to each known ECU address,
        because some ECUs (notably Caterpillar) answer only a request addressed
        to their own source address and ignore the global request."""
        src = self._source
        if src is None:
            return
        try:
            src.write_frame(Frame(
                pgn=PGN.REQUEST, source=TOOL_ADDRESS, destination=0xFF,
                priority=6, data=pgn.to_bytes(3, "little"),
            ))
            for address in list(self.session.modules):
                if address >= J1708_KEY_BASE:
                    continue  # J1708 MID, not a J1939 source address
                src.write_frame(Frame(
                    pgn=PGN.REQUEST, source=TOOL_ADDRESS, destination=address,
                    priority=6, data=pgn.to_bytes(3, "little"),
                ))
        except Exception:                     # noqa: BLE001
            pass

    def _start_sweep(self) -> None:
        """Begin the one-shot silent-ECU identification sweep.

        Queues a directed VI/CI/Software-ID/ECU-ID request to every source
        address, then dribbles them out via ``_sweep_tick``. Only runs on live
        J1939 links (a replay/simulator has a fixed ECU set and no 'hidden'
        module to find). Idempotent: safe to call again after a reconnect.
        """
        if self._sweep_timer.isActive():
            return
        self._sweep_queue = [a for a in range(SWEEP_START, SWEEP_END + 1)
                             if a != TOOL_ADDRESS]
        self._sweep_timer.start()

    def _sweep_tick(self) -> None:
        """Send the next address's identification requests, then stop when done."""
        if not self._sweep_queue:
            self._sweep_timer.stop()
            return
        src = self._source
        if src is None:
            self._sweep_queue.clear()
            self._sweep_timer.stop()
            return
        address = self._sweep_queue.pop(0)
        for pgn in IDENTIFICATION_PGNS:
            try:
                src.write_frame(Frame(
                    pgn=PGN.REQUEST, source=TOOL_ADDRESS, destination=address,
                    priority=6, data=pgn.to_bytes(3, "little"),
                ))
            except Exception:                 # noqa: BLE001 - stop on write error
                break

    def _cancel_sweep(self) -> None:
        """Stop the sweep and drop any queued addresses (e.g. on disconnect)."""
        self._sweep_queue.clear()
        self._sweep_timer.stop()

    def _request_j1708_idents(self) -> None:
        """Ask every J1708/J1587 module for its identification PIDs (VIN,
        component id, software id). Unlike J1939 these are on-request only, so
        simply listening never surfaces them; we issue the standard SAE J1587
        request. We send as the standard off-board tool MID 0xAC: one broadcast
        request plus a component-specific request to each known J1708 module.
        Stops after a bounded number of attempts."""
        src = self._source
        send = getattr(src, "send_j1708", None)
        if send is None:
            return
        if self._j1708_ident_tries >= 15:          # bounded: ~45 s of retries
            return
        self._j1708_ident_tries += 1
        j = self.session.j1708
        pids = (PID_VIN, PID_COMPONENT_ID, PID_SOFTWARE_ID)
        try:
            for pid in pids:
                send(J1587_REQUESTER_MID, build_broadcast_request(pid))
            for mid in list(j.modules):
                for pid in pids:
                    send(J1587_REQUESTER_MID, build_request(mid, pid))
        except Exception:                      # noqa: BLE001 - retried next tick
            pass

    def _discovery_tick(self) -> None:
        """Periodic poll: rotate through address-claim / DM / CI / VI so state
        stays current and modules appearing late still get discovered."""
        if self._source is None:
            return
        pgn = DISCOVERY_PGNS[self._discovery_idx % len(DISCOVERY_PGNS)]
        self._discovery_idx += 1
        self._request_pgn(pgn)
        # Also keep asking J1708 modules for their (on-request) identification
        # PIDs until we have the VIN and every module's component id.
        if self._source_kind == "rp1210" and self._discovery_idx % J1708_IDENT_EVERY == 0:
            self._request_j1708_idents()
        # After the normal identification paths have had a fair chance (~10 s),
        # try UDS ONCE: plenty of ECUs NACK the J1939 VI PGN but still answer UDS
        # DID 0xF190.
        if (self._source_kind == "rp1210" and not self._uds_tried
                and self._discovery_idx >= UDS_VIN_AFTER_TICKS):
            self._maybe_uds_vin()

    def _maybe_uds_vin(self) -> None:
        """One-shot UDS VIN fallback (DID 0xF190).

        Runs on its OWN passive RP1210 client so it never competes with the live
        reader thread for the main client's receive queue, and stores the result
        on the J1939 session so every existing VIN consumer (vehicle panel,
        report, logs) picks it up unchanged."""
        self._uds_tried = True
        if self.session.vin or self._source is None:
            return
        targets = [a for a in self.session.j1939.modules if a != TOOL_ADDRESS]
        if not targets:
            return

        def work() -> None:
            src = None
            try:
                from rp1210 import PROTOCOL as _J1939_PROTO, RP1210Source, list_adapters
                adapters = [a for a in list_adapters() if a.dll_path]
                if not adapters:
                    return
                info = adapters[0]
                src = RP1210Source(dll_path=info.dll_path, protocol=_J1939_PROTO,
                                   device_id=info.device_id, passive=True)
                src.connect()
                res = uds_find_vin(src, targets, timeout=0.8)
            except Exception:                      # noqa: BLE001 - best effort
                res = None
            finally:
                if src is not None:
                    try:
                        src.close()
                    except Exception:              # noqa: BLE001
                        pass
            if res:
                vin, target = res
                self.session.j1939.vin = vin
                self._uds_vin_from = target

        threading.Thread(target=work, daemon=True).start()

    # -------------------------------------------------------- clear DTCs --- #
    def _begin_clear_grace(self) -> None:
        """Suspend the lost-link watchdog briefly around a DTC clear.

        Some ECUs (notably ABS) re-run their self-test and stop broadcasting for
        a few seconds after DM11/DM3 clears their DTCs; without this, that
        silence is mistaken for a dropped link and shows 'Connection Lost'.
        """
        self._clear_grace_until = time.monotonic() + CLEAR_WATCHDOG_GRACE_MS / 1000.0

    def _send_clear(self, address: Optional[int], pgn: int) -> None:
        """Trigger a DTC clear by REQUESTING DM11 (active) or DM3 (stored).

        J1939-73: DM3/DM11 are "on-request" services — the tool sends a
        Request (PGN 0xEA00 / 59904) whose 3-byte little-endian data is the
        target PGN, NOT a direct DM message (most ECUs silently ignore a raw
        DM message with 0xFF data). `address` None -> global (0xFF), otherwise
        directed to that ECU. Clearing needs key-ON / engine-OFF.
        """
        src = self._source
        if src is None:
            return
        dest = 0xFF if address is None else address
        src.write_frame(Frame(
            pgn=PGN.REQUEST, source=TOOL_ADDRESS, destination=dest,
            priority=6, data=pgn.to_bytes(3, "little")))

    def _clear_scope(self, address: Optional[int]) -> None:
        """Clear DTCs with DM11 (active) then DM3 (previously-active), then
        re-poll DM1/DM2. The clear is sent as a SINGLE GLOBAL request (dest
        0xFF) — see the inline notes below for why directed clears are wrong.

        Per SAE J1939-73 this is DM11 (clear active) followed by DM3 (clear
        previously-active); DM55 (clear service-only DTCs) is NOT sent — it is
        not part of the standard clear and sending it after DM11/DM3 can
        prevent the clear from taking effect on some ECMs. Do not re-add it.

        DM3 is deferred by CLEAR_DM11_DM3_GAP_MS so the ECU can finish
        processing DM11 (and any re-init / ABS self-test it triggers) before the
        stored-code clear lands. Deferred via QTimer (non-blocking) rather than
        time.sleep() so the GUI thread never freezes."""
        # Phase 1 - clear active DTCs (DM11) with a SINGLE GLOBAL request.
        # DM11/DM3 are global services (J1939-73). Clear with a global
        # (destination 0xFF) request, not a per-ECU directed one; a directed
        # DM11/DM3 request is ignored by several ECUs — this Mercedes engine ECM
        # included — so the codes never disappear.
        self._begin_clear_grace()
        self._send_clear(None, PGN.DM11)
        # Blank the in-memory DTC store synchronously so the code box visibly
        # empties BEFORE the re-poll repopulates it. An active fault may come
        # straight back (the ECU re-raises it), but now the user *sees* the
        # clear-and-return instead of the code never disappearing.
        addrs = [address] if address is not None else list(self.session.modules)
        for a in addrs:
            m = self.session.modules.get(a)
            if m is not None:
                m.active_dtcs.clear()
                m.previous_dtcs.clear()
        self._last_table_sig = None      # defeat the render cache
        self._refresh_table()             # empty the box now
        for pgn in (PGN.DM1, PGN.DM2):
            self._request_pgn(pgn)
        # Phase 2 - clear stored DTCs (DM3) after the processing gap. Also a
        # single global request (see Phase 1).
        QTimer.singleShot(CLEAR_DM11_DM3_GAP_MS,
                          lambda: self._clear_dm3_phase())

    def _clear_dm3_phase(self) -> None:
        """Second half of the clear: send a single GLOBAL DM3 after the gap,
        then re-poll so the stored-code list refreshes."""
        if self._source is None:
            return
        self._begin_clear_grace()
        self._send_clear(None, PGN.DM3)
        for pgn in (PGN.DM1, PGN.DM2):
            self._request_pgn(pgn)

    def _confirm_clear(self, scope: str) -> bool:
        r = QMessageBox.warning(
            self.win, "Clear Fault Codes",
            f"Clear fault codes on {scope}?\n\n"
            "This clears both stored (inactive) and active codes. Active codes "
            "may come straight back if the fault is still present - the ECU "
            "will re-raise them until it judges the condition resolved "
            "(often after a drive cycle).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        return r == QMessageBox.StandardButton.Yes

    def _clear_j1708(self, mids) -> None:
        """Request each listed J1708 MID clear its diagnostic counts (PID 195).

        Unlike J1939 (DM11/DM3), J1587 has no active-vs-inactive split for
        clearing — mode ``10`` clears all clearable counts on the device. Blanks
        the in-memory list too so the box empties immediately, then re-syncs on
        the next J1708 broadcast.
        """
        if not mids:
            return
        src = self._source
        if src is None:
            return
        self._begin_clear_grace()
        for mid in mids:
            m = self.session.j1708.modules.get(mid)
            if m is not None:
                m.active_dtcs = []
                m.previous_dtcs = []
            try:
                src.send_j1708(J1587_TOOL_MID, build_clear_request(mid))
            except Exception:                     # noqa: BLE001
                pass
        self._last_table_sig = None
        self._refresh_table()

    def _engine_rpm(self) -> Optional[float]:
        """Highest Engine Speed currently seen on either bus, or None.

        J1939 EEC1 and J1587 PID 190 both surface as "Engine Speed", so this
        works whether the truck reports RPM over CAN, J1708, or both.
        """
        best: Optional[float] = None
        for bucket in self.session.live.values():
            for name, (value, _unit) in bucket.items():
                if name.strip().lower() != "engine speed":
                    continue
                try:
                    rpm = float(str(value).replace(",", ""))
                except (TypeError, ValueError):
                    continue
                if best is None or rpm > best:
                    best = rpm
        return best

    def _require_engine_off(self) -> bool:
        """Refuse a DTC clear while the engine is running (returns False).

        Clearing DM11/DM3 (or J1587 PID 195) with the engine running makes it
        stumble and immediately re-set fault codes, so the user is told to shut
        the engine off first. The lost-link watchdog is held for
        ENGINE_OFF_GRACE_MS so the key-off / key-on cycle needed to stop the
        engine is not reported as a dropped connection.
        """
        if self._obd_state is not None:
            raw = (self._obd_state.get("live") or {}).get("Engine speed", (0, ""))[0]
            try:
                rpm = float(raw)
            except (TypeError, ValueError):
                rpm = 0.0
            if rpm <= 0:
                return True
            self._clear_grace_until = time.monotonic() + ENGINE_OFF_GRACE_MS / 1000.0
            QMessageBox.warning(
                self.win, "Engine Running",
                f"The engine is running (~{rpm:.0f} RPM).\n\n"
                "Shut the engine OFF before clearing emission-related DTCs "
                "(OBD-II Mode 04). Then click Clear again.")
            return False
        rpm = self._engine_rpm()
        if rpm is None or rpm <= 0:
            return True
        self._clear_grace_until = time.monotonic() + ENGINE_OFF_GRACE_MS / 1000.0
        QMessageBox.warning(
            self.win, "Engine Running",
            f"The engine is running (~{rpm:.0f} RPM).\n\n"
            "Shut the engine OFF before clearing fault codes. Clearing while "
            "the engine is running can make it stumble and immediately set new "
            "fault codes.\n\n"
            f"The connection is held for {ENGINE_OFF_GRACE_MS // 1000} seconds "
            "so you can switch the engine off (key off and back on if needed); "
            "then click Clear again.")
        return False

    def _clear_all_faults(self) -> None:
        if self._obd_state is not None:
            # OBD-II Mode 04 clears emission-related DTCs on ALL ECUs at once;
            # there is no per-module clear in the generic OBD service set.
            if not self._require_engine_off():
                return
            if not self._confirm_clear(
                    "all OBD-II ECUs (Mode 04 - confirmed and pending codes; "
                    "permanent codes only clear after the repair is verified)"):
                return
            if self._obd_worker is not None:
                self._obd_worker.command = "clear"
            self.win.statusBar().showMessage("Clear sent (OBD-II Mode 04)")
            return
        if not self._require_engine_off():
            return
        if not self._confirm_clear("all modules (J1939 + J1708)"):
            return
        self._clear_scope(None)                             # J1939 DM11 + DM3
        self._clear_j1708(list(self.session.j1708.modules))  # J1587 PID 195
        self.win.statusBar().showMessage("Clear-all sent (J1939 + J1708)")

    def _clear_selected_fault(self) -> None:
        if self._obd_state is not None:
            # Generic OBD-II has no per-module clear - Mode 04 is global.
            self._clear_all_faults()
            return
        if not self._require_engine_off():
            return
        a = self._current_addr
        if a is None:
            QMessageBox.information(self.win, "Clear Fault Codes",
                                    "Select a module in the component list first.")
            return
        if a >= J1708_KEY_BASE:
            # A J1708 module: clear just this MID over J1587 (PID 195).
            mid = a - J1708_KEY_BASE
            mod = self.session.modules.get(a)
            label = f"{self._key_text(a)}  {mod.label}" if mod is not None else f"MID {mid:02X}"
            if not self._confirm_clear(label):
                return
            self._clear_j1708([mid])
            self.win.statusBar().showMessage(f"J1708 clear sent to {label}")
            return
        # J1939: DM11/DM3 clears are global — there is no standard per-module
        # J1939 clear (that would be DM22, per individual DTC). So this button
        # clears the connected J1939 modules globally.
        if not self._confirm_clear("the connected modules (J1939 clears are global)"):
            return
        self._clear_scope(a)
        self.win.statusBar().showMessage("Clear fault request sent (global)")

    def _session_get(self, key: str, default='—') -> str:
        """Helper to get session data by key."""
        # This is called from report generation - simplified for now
        # The actual values come from various sources
        if key in ('vin', 'esn', 'model', 'make', 'software_id', 'ecu_id'):
            return default
        return str(default)

    def _dtcs_from_live(self, live: dict) -> list:
        """Extract active DTCs from live data dictionary.
        
        This is a placeholder - actual DTC extraction happens via DM1/DM2 parsing.
        For now, return empty since we're checking for live connection elsewhere.
        """
        return []

    def _refresh_vehicle_info(self) -> None:
        if self._obd_state is not None:
            st = self._obd_state
            vin = st.get("vin")
            self.lbl_vin.setText(f"VIN: {vin}" if vin else "VIN: \u2014")
            vp = st.get("vpic") or {}
            make = vp.get("make") or (wmi_make(vin[:3]) if vin else None)
            chassis = " ".join(
                p for p in (make, vp.get("model"), vp.get("series")) if p)
            yr = vp.get("year") or (model_year(vin) if vin else None)
            label = " ".join(
                p for p in (chassis, f"({yr})" if yr else None) if p)
            self.lbl_model.setText(
                f"Make / Model: {label}" if label else "Make / Model: \u2014")
            # Generic OBD-II has no engine serial (that is a J1939 concept);
            # the DLC equivalents are calibration IDs (Mode 09 04) and the
            # ECU names (Mode 09 0A).
            cal = ", ".join(st.get("cal_ids", {}).values()) or None
            ecus = ", ".join(st.get("ecu_names", {}).values()) or None
            self.lbl_serial.setText("Engine Serial No: \u2014")
            self.lbl_software_id.setText(
                f"Software ID (Cal ID): {cal}" if cal else "Software ID: \u2014")
            self.lbl_ecu_id.setText(
                f"ECU ID: {ecus}" if ecus else "ECU ID: \u2014")
            return
        vin = self.session.vin
        self.lbl_vin.setText(f"VIN: {vin}" if vin else "VIN: \u2014")

        eng = self.session.modules.get(0x00)

        # Engine identity, from the engine ECU's CI make/model or NAME.
        eng_make = eng_model = None
        if eng is not None:
            eng_make = friendly_make(eng.make) if eng.make else None
            if not eng_make and eng.name is not None:
                eng_make = manufacturer_name(eng.name.manufacturer)
            eng_model = eng.model
        engine_desc = " ".join(x for x in (eng_make, eng_model) if x) or None

        # The VIN's WMI names the *vehicle* OEM (Sterling, Kenworth, ...), which
        # is the right "Make" for the truck; the engine CI make (Mercedes-Benz,
        # Cummins, ...) names the *engine*, often a different company. Prefer the
        # VIN WMI and fall back to the engine CI only when there is no VIN (or
        # its WMI is unknown), so this reads correctly for every vehicle.
        vin_make = wmi_make(vin) if vin else None
        year = model_year(vin) if vin else None

        if vin_make:
            # Vehicle OEM from the VIN. The VIN carries no model name, and our
            # model-year heuristic is unreliable, so show just the make.
            mm = vin_make
        else:
            mm = " ".join(x for x in (eng_make, eng_model) if x)
            if mm and year and not eng_model:
                mm = f"{mm} ({year})"
        self.lbl_model.setText(f"Make / Model: {mm}" if mm else "Make / Model: \u2014")

        # Engine line: keep the engine make/model visible next to its serial now
        # that Make/Model reflects the vehicle rather than the engine.
        serial = eng.serial if (eng is not None and eng.serial) else None
        if engine_desc and serial:
            self.lbl_serial.setText(f"Engine: {engine_desc} \u00b7 S/N {serial}")
        elif engine_desc:
            self.lbl_serial.setText(f"Engine: {engine_desc}")
        elif serial:
            self.lbl_serial.setText(f"Engine Serial No: {serial}")
        else:
            self.lbl_serial.setText("Engine Serial No: \u2014")

        sw = eng.software_id if eng is not None else None
        self._label(self.lbl_software_id,
                    f"Software ID: {sw}" if sw else "Software ID: \u2014")

        ecu_parts = []
        if eng is not None:
            if eng.ecu_part:
                ecu_parts.append(f"Part {eng.ecu_part}")
            if eng.ecu_serial:
                ecu_parts.append(f"S/N {eng.ecu_serial}")
        ecu_txt = ", ".join(ecu_parts) if ecu_parts else None
        self._label(self.lbl_ecu_id,
                    f"ECU ID: {ecu_txt}" if ecu_txt else "ECU ID: \u2014")

    def _refresh_lamps(self) -> None:
        if self._obd_state is not None:
            mil = bool((self._obd_state or {}).get("mil"))
            self._led(self.lamp_amber, "MIL", "#f39c12" if mil else "#777777")
            self._led(self.lamp_red, "STOP", "#777777")
            self._led(self.lamp_abs, "ABS", "#777777")
            self._led(self.lamp_trailer_abs, "TRL ABS", "#777777")
            return
        a = self._current_addr
        m = self.session.modules.get(a) if a is not None else None
        lamps = m.lamps if m is not None else {}
        # Amber indicator = any amber warning lamp (MIL, amber, protect);
        # red indicator = the red stop lamp. Coloured when lit, grey when off.
        amber_on = bool(lamps.get("mil") or lamps.get("amber") or lamps.get("protect"))
        red_on = bool(lamps.get("red"))

        # ABS and trailer-ABS come from the brake controller's EBC1, on whatever
        # module broadcasts it, so scan every live bucket (not just the selected
        # one). The trailer's ABS status is relayed to the tractor over PLC.
        def _on(name):
            return any(b.get(name, ("",))[0] == "On"
                       for b in self.session.live.values())
        abs_on = _on("EBS Amber Warning") or _on("EBS Red Warning")
        trailer_on = _on("Trailer ABS Warning")

        self._led(self.lamp_amber, "MIL", "#f39c12" if amber_on else "#777777")
        self._led(self.lamp_red, "STOP", "#e74c3c" if red_on else "#777777")
        self._led(self.lamp_abs, "ABS", "#f1c40f" if abs_on else "#777777")
        self._led(self.lamp_trailer_abs, "TRL ABS",
                  "#f1c40f" if trailer_on else "#777777")

def main(argv: list[str]) -> int:
    app = QApplication(argv)
    app.setStyleSheet(DARK_STYLESHEET)
    # Taskbar / window icon (also the title-bar icon of every dialog).
    app.setWindowIcon(QIcon(ICON_PATH))

    mode, arg = "sim", None
    if "--rp1210" in argv:
        mode = "rp1210"
    elif "--replay" in argv:
        i = argv.index("--replay")
        mode, arg = "replay", argv[i + 1]

    ui_file = QFile(UI_PATH)
    ui_file.open(QIODevice.ReadOnly)
    win = QUiLoader().load(ui_file)
    ui_file.close()

    if win is None:
        print(f"Failed to load {UI_PATH}", file=sys.stderr)
        return 1

    win.setWindowTitle(f"OpenTruck {full_version()}")
    ctrl = MainWindow(win, initial_kind=mode, replay_path=arg)
    app._opentruck_controller = ctrl   # keep a reference so it isn't GC'd
    app.aboutToQuit.connect(ctrl.shutdown)   # stop the reader thread on exit
    win.showMaximized()
    ctrl._apply_saved_split()   # restore saved splitter positions at full size
    # One-time first-launch setup: preferred adapter + log folder. Shows on
    # the very first launch only (never after an update). Choosing an adapter
    # here only records it as the preselected Connect option - no connection
    # is attempted. Skipping is fine: everything stays at its defaults.
    if not first_run_done():
        dlg = FirstRunDialog(win)
        if dlg.exec():   # Skip (reject) saves nothing
            if dlg.get_adapter_code():
                set_last_source(dlg.get_adapter_code())
            if dlg.get_log_dir():
                set_log_dir(dlg.get_log_dir())   # same key Preferences > Log edits
        set_first_run_done()
    # Silent, non-blocking update check on launch: only surfaces a dialog if a
    # newer release than __version__ is found (never prompts otherwise, and
    # never blocks when offline).
    ctrl._check_for_updates(interactive=False)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
