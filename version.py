"""OpenTruck - single source of truth for the application version.

``__version__`` is the semantic release version (MAJOR.MINOR.PATCH). Keep it in
sync with the GitHub release tag (tag the release ``v<full_version()>``, e.g.
``v0.2.0.85``), since the update-checker compares the release version against
``__version__`` + ``__build__``. It must be a plain semver like ``"0.2.0"``.

``__build__`` is a monotonically increasing build counter. It is auto-incremented
by ``bump_version.py`` every time ``build.bat`` runs, so each produced installer
is uniquely identified (the app's window title / About box and the installer
filename both carry the full ``MAJOR.MINOR.PATCH.build`` string). ``__build__``
IS part of the version the update-checker compares (so a newer local build is
never offered an older published build), but NOT part of the release tag's
semantic meaning.
"""
from __future__ import annotations

__version__ = "0.3.0"
__build__ = 146


def full_version() -> str:
    """Return the full ``MAJOR.MINOR.PATCH.build`` string for this build."""
    return f"{__version__}.{__build__}"