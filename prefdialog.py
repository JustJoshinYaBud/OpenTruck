"""OpenTruck - Preferences dialog for user settings (tabbed).

Tabs are organised so more option groups can be added later without touching
existing tabs. Current tabs: "Units" and "Log".
"""
from __future__ import annotations

from typing import Literal, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QComboBox,
    QLabel,
    QVBoxLayout,
    QGroupBox,
    QRadioButton,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QFileDialog,
    QTabWidget,
    QWidget,
)


class PreferencesDialog(QDialog):
    """Tabbed preferences dialog: unit system + log location (extensible)."""

    units_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setModal(True)
        self.setMinimumWidth(420)
        self._default_unit = "metric"
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the dialog: a tab widget + OK/Cancel buttons."""
        layout = QVBoxLayout()
        layout.setSpacing(12)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_units_tab(), "Units")
        self.tabs.addTab(self._build_log_tab(), "Log")
        layout.addWidget(self.tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    # ---------------------------------------------------------------- tabs #
    def _make_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        return tab

    def _build_units_tab(self) -> QWidget:
        """Unit-system selection (metric / standard / canadian)."""
        tab = self._make_tab()
        layout = tab.layout()

        group = QGroupBox("Unit System")
        gl = QVBoxLayout(group)

        self.radio_metric = QRadioButton("Metric")
        self.radio_metric.setObjectName("metric")
        self.radio_metric.setToolTip("SI units: kPa, °C, N·m, km/h, L, L/h")

        self.radio_standard = QRadioButton("Standard (US)")
        self.radio_standard.setObjectName("standard")
        self.radio_standard.setToolTip("US customary: psi, °F, ft·lb, mph, gal, lb/h")

        self.radio_canadian = QRadioButton("Canadian")
        self.radio_canadian.setObjectName("canadian")
        self.radio_canadian.setToolTip("Metric, except torque (ft·lb) and pressure (psi)")

        gl.addWidget(self.radio_metric)
        gl.addWidget(self.radio_standard)
        gl.addWidget(self.radio_canadian)

        layout.addWidget(group)
        layout.addStretch(1)
        return tab

    def _build_log_tab(self) -> QWidget:
        """Log/capture output folder selection (blank = default location)."""
        tab = self._make_tab()
        layout = tab.layout()

        group = QGroupBox("Log File Location")
        gl = QVBoxLayout(group)

        hint = QLabel(
            "Folder where saved logs and captures are written.\n"
            "Leave blank to use the default location."
        )
        hint.setWordWrap(True)
        gl.addWidget(hint)

        row = QHBoxLayout()
        self.edit_log_dir = QLineEdit()
        self.edit_log_dir.setPlaceholderText("Default location")
        self.btn_browse = QPushButton("Browse…")
        self.btn_browse.clicked.connect(self._browse_log_dir)
        row.addWidget(self.edit_log_dir, 1)
        row.addWidget(self.btn_browse)
        gl.addLayout(row)

        layout.addWidget(group)
        layout.addStretch(1)
        return tab

    # ------------------------------------------------------------ handlers #
    def _browse_log_dir(self) -> None:
        """Open a folder picker and fill the log-directory line edit."""
        start = self.edit_log_dir.text().strip() or None
        chosen = QFileDialog.getExistingDirectory(self, "Choose Log Folder", start or "")
        if chosen:
            self.edit_log_dir.setText(chosen)

    # --------------------------------------------------------- get/set API #
    def get_units(self) -> Literal["standard", "metric", "canadian"]:
        """Return the currently selected unit system."""
        for btn in (self.radio_metric, self.radio_standard, self.radio_canadian):
            if btn.isChecked():
                return btn.objectName()  # type: ignore[return-value]
        return self._default_unit

    def set_units(self, value: Literal["standard", "metric", "canadian"]) -> None:
        """Set the initial selection based on a saved value."""
        for btn in (self.radio_metric, self.radio_standard, self.radio_canadian):
            if btn.objectName() == value:
                btn.setChecked(True)
                return

    def get_log_dir(self) -> Optional[str]:
        """Return the entered log-directory path, or None when blank."""
        text = self.edit_log_dir.text().strip()
        return text or None

    def set_log_dir(self, value: Optional[str]) -> None:
        """Pre-fill the log-directory line edit from a saved value."""
        self.edit_log_dir.setText(value or "")


class FirstRunDialog(QDialog):
    """One-time first-launch setup shown after installing OpenTruck.

    Lets the user pick a preferred RP1210 adapter (from the drivers already
    installed on the machine - nothing is connected or probed here) and a
    default folder for log files, with the option to skip entirely.

    Shows once per machine: the caller persists a ``first_run_done`` flag in
    config.json afterwards, so software updates never show it again.
    """

    DISCLAIMER = (
        "OpenTruck is an experimental, community-built diagnostic tool. It "
        "reads standard SAE J1939/J1708 data, but some live readings and "
        "fault codes may not appear, or may not be named correctly, for "
        "every make and model. Always confirm important findings with a "
        "service manual or a dealer-level tool before spending money on "
        "parts or repairs.")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Welcome to OpenTruck")
        self.setModal(True)
        self.setMinimumWidth(480)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        welcome = QLabel(
            "<b>Welcome to OpenTruck!</b><br><br>"
            "This quick setup only takes a moment. You can change "
            "everything here later under <b>File &#9656; Preferences</b>.")
        welcome.setWordWrap(True)
        layout.addWidget(welcome)

        # --- experimental disclaimer ------------------------------------- #
        note = QGroupBox("Please read")
        nl = QVBoxLayout(note)
        lbl = QLabel(self.DISCLAIMER)
        lbl.setWordWrap(True)
        nl.addWidget(lbl)
        layout.addWidget(note)

        # --- preferred adapter (no connection attempt is made here) ------ #
        group = QGroupBox("Preferred RP1210 adapter")
        gl = QVBoxLayout(group)
        hint = QLabel(
            "Adapters whose driver is installed on this PC are listed below. "
            "Nothing is connected yet - this just makes your adapter the "
            "first choice when you press Connect.")
        hint.setWordWrap(True)
        gl.addWidget(hint)

        self.adapter_combo = QComboBox()
        adapters = []
        try:
            from rp1210 import list_adapters
            adapters = list_adapters()
        except Exception:
            adapters = []          # enumeration is best-effort in first-run
        if adapters:
            for a in adapters:
                label = a.name + ("  (32-bit driver)" if a.bridge_dll and not a.dll_path else "")
                self.adapter_combo.addItem(label, a.code)
            self.adapter_combo.setCurrentIndex(0)
        else:
            self.adapter_combo.addItem("No RP1210 drivers detected on this PC", None)
            self.adapter_combo.setEnabled(False)
        gl.addWidget(self.adapter_combo)
        layout.addWidget(group)

        # --- default log folder (same setting as Preferences > Log) ------ #
        log_group = QGroupBox("Log file location")
        ll = QVBoxLayout(log_group)
        log_hint = QLabel(
            "Where saved logs, captures and reports are written. "
            "Leave blank to use the default location.")
        log_hint.setWordWrap(True)
        ll.addWidget(log_hint)
        row = QHBoxLayout()
        self.edit_log_dir = QLineEdit()
        self.edit_log_dir.setPlaceholderText("Default location")
        self.btn_browse = QPushButton("Browse\u2026")
        self.btn_browse.clicked.connect(self._browse_log_dir)
        row.addWidget(self.edit_log_dir, 1)
        row.addWidget(self.btn_browse)
        ll.addLayout(row)
        layout.addWidget(log_group)

        # --- buttons: Skip vs Save & Finish ------------------------------- #
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.btn_skip = QPushButton("Skip")
        self.btn_skip.setToolTip("Close this setup and use the defaults.")
        self.btn_save = QPushButton("Save && Finish")
        self.btn_save.setDefault(True)
        buttons.addWidget(self.btn_skip)
        buttons.addWidget(self.btn_save)
        layout.addLayout(buttons)
        self.btn_skip.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self.accept)

    def _browse_log_dir(self) -> None:
        start = self.edit_log_dir.text().strip() or None
        chosen = QFileDialog.getExistingDirectory(self, "Choose Log Folder", start or "")
        if chosen:
            self.edit_log_dir.setText(chosen)

    def get_adapter_code(self) -> Optional[str]:
        """The selected adapter's RP1210 vendor code, or None (none/skip)."""
        return self.adapter_combo.currentData()

    def get_log_dir(self) -> Optional[str]:
        """The entered log-directory path, or None when blank."""
        text = self.edit_log_dir.text().strip()
        return text or None
