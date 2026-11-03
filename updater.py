"""OpenTruck - GitHub release update-check helpers.

The GUI (`app.py`) uses these to ask the GitHub Releases API whether a newer
release is available than the running `__version__` (see `version.py`). These
functions are pure (no Qt), so they can be unit-tested and re-used headlessly.

The actual network fetch happens in `app.py` via `QNetworkAccessManager`
(non-blocking), so a missing/offline connection simply means no response and
no check result — the app never hangs on this.
"""
from __future__ import annotations

from typing import Optional

from version import __version__

# Which GitHub repo hosts the releases. Set these to the real owner/repo
# before the first tagged release; the API URL below is derived from them.
GITHUB_OWNER = "JustJoshinYaBud"
GITHUB_REPO = "OpenTruck"

LATEST_RELEASE_URL = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)


def parse_version(v: str) -> tuple[int, ...]:
    """Parse a semver-ish string into a comparable tuple of ints.

    Tolerates a leading ``v``/``V`` (GitHub tags are often ``v1.2.3``) and
    missing segments (``"0.1"`` -> ``(0, 1, 0)``).
    """
    cleaned = (v or "").strip().lstrip("vV")
    parts: list[int] = []
    for token in cleaned.split("."):
        digits = ""
        for ch in token:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def current_version() -> tuple[int, ...]:
    """Return the running version as a comparable tuple."""
    return parse_version(__version__)


def is_newer(tag: str, current: str = __version__) -> bool:
    """True if ``tag`` represents a newer version than ``current``."""
    return parse_version(tag) > parse_version(current)


def find_setup_asset(release: dict) -> Optional[dict]:
    """Find the installer asset (OpenTruckSetup-*.exe) in a release JSON.

    Returns the asset dict (with ``browser_download_url`` and ``size``) or
    ``None`` when the release carries no installer (e.g. a source-only tag).
    """
    for asset in release.get("assets", ()):   # type: ignore[union-attr]
        name = (asset.get("name") or "").strip()
        if name.lower().startswith("opentrucksetup-") and name.lower().endswith(".exe"):
            return asset
    return None
