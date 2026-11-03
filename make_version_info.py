"""OpenTruck - generate Windows version resources for the built executables.

PyInstaller gives an exe no useful version metadata unless it is handed a
``--version-file``. A missing/blank version resource is one of the small
signals that makes a freshly built PyInstaller binary look disposable to
security heuristics and to users (Properties > Details shows nothing), so the
build stamps CompanyName / ProductName / FileDescription / version on both
OpenTruck.exe and OpenTruckBridge32.exe.

Called by build.bat AFTER bump_version.py, so the numbers are always current.
Writes (git-ignored, under build/):
    build/version_info.txt          -> OpenTruck.exe
    build/version_info_bridge.txt   -> OpenTruckBridge32.exe
"""
from __future__ import annotations

import os
import sys

from version import __build__, __version__


def _numbers() -> tuple[int, int, int, int]:
    parts = [int(p) for p in __version__.split(".") if p.isdigit()]
    while len(parts) < 3:
        parts.append(0)
    return parts[0], parts[1], parts[2], int(__build__)


def _text(path: str, original_name: str, description: str) -> str:
    major, minor, patch, build = _numbers()
    full = f"{major}.{minor}.{patch}.{build}"
    return f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, {build}),
    prodvers=({major}, {minor}, {patch}, {build}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', 'OpenTruck'),
         StringStruct('FileDescription', {description!r}),
         StringStruct('FileVersion', {full!r}),
         StringStruct('InternalName', {os.path.splitext(original_name)[0]!r}),
         StringStruct('LegalCopyright', 'Copyright (C) 2026 JustJoshinYaBud, GNU GPL v3.0-or-later'),
         StringStruct('OriginalFilename', {original_name!r}),
         StringStruct('ProductName', 'OpenTruck'),
         StringStruct('ProductVersion', {full!r})])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def main() -> int:
    root = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(root, "build")
    os.makedirs(out, exist_ok=True)
    targets = [
        ("version_info.txt", "OpenTruck.exe",
         "OpenTruck heavy-duty vehicle diagnostics"),
        ("version_info_bridge.txt", "OpenTruckBridge32.exe",
         "OpenTruck 32-bit RP1210 adapter bridge"),
    ]
    for name, exe, desc in targets:
        path = os.path.join(out, name)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(_text(path, exe, desc))
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
