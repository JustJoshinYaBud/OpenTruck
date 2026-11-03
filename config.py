"""OpenTruck - remember the last-used connection across restarts.

Stores a small JSON blob in ``%APPDATA%\\OpenTruck\\config.json`` so the
Connect dialog preselects whatever source/adapter the user chose last time.

Deliberately kept out of the app folder so:
  * the USB drive stays read-only-safe, and
  * each PC remembers its own adapter (adapters differ per machine).
"""
from __future__ import annotations

import json
import os
from typing import Optional, Literal


def _dir() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "OpenTruck")


def _path() -> str:
    return os.path.join(_dir(), "config.json")


def load() -> dict:
    try:
        with open(_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save(data: dict) -> None:
    try:
        d = _dir()
        os.makedirs(d, exist_ok=True)
        with open(_path(), "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass


def last_source() -> Optional[str]:
    """The last-used source key: an adapter vendor code, "sim", or "replay"."""
    return load().get("last_source")


def set_last_source(key: str) -> None:
    data = load()
    data["last_source"] = key
    save(data)


def ui_layout() -> dict:
    """Saved GUI layout: splitter positions and table column widths.

    Keys are widget names; values are lists of pixel sizes. Missing or
    malformed entries simply fall back to the built-in defaults.
    """
    data = load().get("ui_layout")
    return data if isinstance(data, dict) else {}


def set_ui_layout(key: str, value) -> None:
    data = load()
    lay = data.get("ui_layout")
    if not isinstance(lay, dict):
        lay = {}
    lay[key] = value
    data["ui_layout"] = lay
    save(data)


def first_run_done() -> bool:
    """True once the first-launch setup dialog has been shown (or skipped).

    Deliberately a one-time flag: set on the very first launch only, so
    software updates never show the setup wizard again.
    """
    return bool(load().get("first_run_done"))


def set_first_run_done() -> None:
    data = load()
    data["first_run_done"] = True
    save(data)


def last_protocol() -> str:
    """The last-used vehicle protocol: "J1939" (default) or "J1708"."""
    return load().get("last_protocol", "J1939")


def set_last_protocol(key: str) -> None:
    data = load()
    data["last_protocol"] = key
    save(data)


def units() -> Literal["standard", "metric", "canadian"]:
    """The user's unit preference.

    Returns:
        "metric":   SI units (kPa, °C, N·m, km/h, L, L/h) — default
        "standard": US customary (psi, °F, ft·lb, mph, gal, lb/h)
        "canadian": metric, except torque (ft·lb) and pressure (psi)

    Carries a one-time migration for pre-release configs, where "standard"
    meant "Standard (SI)" (i.e. SI units). Those are promoted to "metric" so
    nobody is silently flipped to US customary.
    """
    data = load()
    val = data.get("units", "metric")
    if not data.get("units_schema_v2") and val == "standard":
        data["units"] = "metric"
        data["units_schema_v2"] = True
        save(data)
        return "metric"
    return val


def set_units(value: Literal["standard", "metric", "canadian"]) -> None:
    data = load()
    data["units"] = value
    data["units_schema_v2"] = True
    save(data)


def log_dir() -> Optional[str]:
    """The user-preferred folder for saved logs/captures, or None when unset.

    When empty (no preference), the app falls back to its existing default
    location (see ``app._log_root``). Stored as an absolute path chosen by the
    user in the Preferences dialog.
    """
    path = load().get("log_dir")
    return path if isinstance(path, str) and path.strip() else None


def set_log_dir(path: str) -> None:
    data = load()
    if path and path.strip():
        data["log_dir"] = path.strip()
    else:
        data.pop("log_dir", None)
    save(data)
