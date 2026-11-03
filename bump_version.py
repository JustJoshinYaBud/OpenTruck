"""Auto-increment the OpenTruck build number before each release build.

Increments ``__build__`` in ``version.py`` and stamps the new build into
``MyAppVersion`` in ``OpenTruckInstaller.iss`` (so the About box / Windows
"Programs and Features" shows which build you have). The installer filename
embeds the full version (``OpenTruckSetup-0.1.0.53.exe``) so release assets on
GitHub are never ambiguous; each build still overwrites the previous file in
``dist\\`` because the name changes only when the version does.

Prints the full ``MAJOR.MINOR.PATCH.build`` string to stdout so ``build.bat`` can
log it. Run with no arguments::

    python bump_version.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSION_FILE = ROOT / "version.py"
ISS_FILE = ROOT / "OpenTruckInstaller.iss"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def bump() -> str:
    version_txt = _read(VERSION_FILE)

    ver_match = re.search(r'^__version__\s*=\s*"([^"]+)"', version_txt, re.M)
    if not ver_match:
        sys.exit("ERROR: could not find __version__ in version.py")
    version = ver_match.group(1)

    build_match = re.search(r"^__build__\s*=\s*(\d+)", version_txt, re.M)
    if not build_match:
        sys.exit("ERROR: could not find __build__ in version.py")
    build = int(build_match.group(1)) + 1

    version_txt = re.sub(
        r"^__build__\s*=\s*\d+",
        f"__build__ = {build}",
        version_txt,
        count=1,
        flags=re.M,
    )
    _write(VERSION_FILE, version_txt)

    full = f"{version}.{build}"

    iss_txt = _read(ISS_FILE)
    iss_txt = re.sub(
        r"#define MyAppVersion\s+\"[^\"]*\"",
        f'#define MyAppVersion "{full}"',
        iss_txt,
        count=1,
    )
    # Versioned output filename (matches the About-box version), so release
    # assets on GitHub are never ambiguous. Each build overwrites the previous
    # dist\ file because the name only changes when the version does.
    iss_txt = re.sub(
        r"OutputBaseFilename\s*=\s*[^\r\n]*",
        "OutputBaseFilename=OpenTruckSetup-{#MyAppVersion}",
        iss_txt,
        count=1,
    )
    _write(ISS_FILE, iss_txt)

    return full


if __name__ == "__main__":
    print(bump())
