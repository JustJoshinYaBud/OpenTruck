"""OpenTruck — verify the build/run environment before building.

Run this with the *64-bit* Python you intend to build with, e.g.:

    "C:\\Program Files\\Python312\\python.exe" check_env.py

It checks everything `build.bat` needs and prints a PASS/FAIL report, exiting
non-zero (exit code 1) if anything critical is missing. It does NOT touch
`dist\\`, `build\\`, or any other folder — safe to run any time, on any machine.

Why this exists: a previous build pass deleted `dist\\` before discovering that
PyInstaller was missing. `build.bat` now runs these checks (and stages its
output) so that can't happen again; this script is the standalone, re-runnable
version of the same checks for when a new machine/agent is being set up.
"""

from __future__ import annotations

import importlib
import os
import platform
import struct
import sys

# Source files that MUST exist for a build (checked relative to this script's dir).
REQUIRED_FILES = [
    "app.py",
    "MainWindow.ui",
    "rp1210_bridge.py",
    "modules/j1939.py",
    "modules/j1708.py",
    "lookup/spn.py",
    "reader.py",
]

# Candidate locations for a 32-bit Python (drives the 32-bit RP1210 bridge).
PY32_GLOBS = [
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python313-32\python.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python312-32\python.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python311-32\python.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python310-32\python.exe"),
    r"C:\Program Files (x86)\Python313-32\python.exe",
    r"C:\Program Files (x86)\Python312-32\python.exe",
    r"C:\Program Files (x86)\Python311-32\python.exe",
    r"C:\Python313-32\python.exe",
    r"C:\Python312-32\python.exe",
    r"C:\Python311-32\python.exe",
]


def _bitness() -> int:
    return struct.calcsize("P") * 8


def _module_version(name: str) -> str | None:
    try:
        mod = importlib.import_module(name)
    except Exception:
        return None
    return getattr(mod, "__version__", "installed (no __version__)")


def _check_import(name: str) -> tuple[bool, str]:
    ver = _module_version(name)
    if ver is None:
        return False, "MISSING"
    return True, ver


def main() -> int:
    results: list[tuple[bool, str, str]] = []  # (ok, check, detail)
    ok_all = True

    def add(ok: bool, check: str, detail: str) -> None:
        nonlocal ok_all
        results.append((ok, check, detail))
        if not ok:
            ok_all = False

    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)

    # --- interpreter ---
    py = sys.executable or "python"
    add(_bitness() == 64, "interpreter", f"{py}  ({platform.python_version()}, {_bitness()}-bit)")

    # --- critical build tooling ---
    ok, detail = _check_import("PyInstaller")
    add(ok, "PyInstaller", detail)
    if not ok:
        add(False, "PyInstaller", f"install with: {py} -m pip install pyinstaller")

    ok, detail = _check_import("PySide6")
    add(ok, "PySide6", detail)
    if not ok:
        add(False, "PySide6", "install with: pip install -r requirements.txt")

    # --- source files ---
    for f in REQUIRED_FILES:
        add(os.path.isfile(f), f"file {f}", "present" if os.path.isfile(f) else "MISSING")

    # --- 32-bit python (optional: needed to build the 32-bit driver bridge) ---
    found32 = next((p for p in PY32_GLOBS if os.path.isfile(p)), None)
    add(bool(found32), "32-bit Python (bridge)", found32 or "NOT FOUND (bridge won't build)")

    # --- pip ---
    try:
        import pip  # noqa: F401
        add(True, "pip", "available")
    except Exception:
        add(False, "pip", "missing — run `python -m ensurepip`")

    # --- report ---
    print()
    print("=" * 64)
    print(" OpenTruck environment check")
    print("=" * 64)
    for ok, check, detail_out in results:
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {check:<26} {detail_out}")
    print("=" * 64)
    if ok_all:
        print("  All critical dependencies are present. You can run build.bat.")
    else:
        print("  Fix the FAIL items above, then re-run.")
        print("  NOTE: nothing was deleted or modified by this check.")
    print("=" * 64)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
