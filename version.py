"""OpenTruck - single source of truth for the application version.

``__version__`` is the semantic release version (MAJOR.MINOR.PATCH). Keep it in
sync with the GitHub release tag name, since the Phase 4 update-checker compares
GitHub's latest release tag against this string; it must be a plain semver like
``"0.1.0"``.

``__build__`` is a monotonically increasing build counter. It is auto-incremented
by ``bump_version.py`` every time ``build.bat`` runs, so each produced installer
is uniquely identified (the app's window title / About box and the installer
filename both carry the full ``MAJOR.MINOR.PATCH.build`` string). ``__build__``
is intentionally *not* part of the semver that the update-checker compares.
"""
from __future__ import annotations

__version__ = "0.1.0"
__build__ = 61


def full_version() -> str:
    """Return the full ``MAJOR.MINOR.PATCH.build`` string for this build."""
    return f"{__version__}.{__build__}"