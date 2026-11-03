"""OpenTruck - GitHub release update-check helpers.

The GUI (`app.py`) uses these to ask the GitHub Releases API whether a newer
release is available than the running `__version__` (see `version.py`). These
functions are pure (no Qt), so they can be unit-tested and re-used headlessly.

The actual network fetch happens in `app.py` via `QNetworkAccessManager`
(non-blocking), so a missing/offline connection simply means no response and
no check result — the app never hangs on this.
"""
from __future__ import annotations

import re
from typing import Optional

from version import __build__, __version__

# Which GitHub repo hosts the releases. Set these to the real owner/repo
# before the first tagged release; the API URL below is derived from them.
GITHUB_OWNER = "JustJoshinYaBud"
GITHUB_REPO = "OpenTruck"

LATEST_RELEASE_URL = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)

# The LIST endpoint, which is what the app actually uses. ``/releases/latest``
# is unusable in practice: GitHub hides pre-releases and drafts from it (a repo
# whose only release is flagged "pre-release" gets HTTP 404), and it returns a
# single object with no way to tell how the version was encoded.
RELEASES_URL = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
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
    """Return the running version as a comparable tuple.

    INCLUDES the build counter (``0.1.0.84``), because releases carry it too
    (installer name / release name). Without it, a local build newer than the
    last published one would be offered that older build as an "update".
    """
    return parse_version(f"{__version__}.{__build__}")


def is_newer(tag: str, current: str = __version__) -> bool:
    """True if ``tag`` represents a newer version than ``current``.

    Legacy helper kept for callers/tests that pass plain version strings; the
    GUI compares ``release_version(release) > current_version()`` instead.
    """
    return parse_version(tag) > parse_version(current)


def version_from_text(text: str) -> Optional[tuple[int, ...]]:
    """Pull the first version-like number out of arbitrary text.

    Releases in the wild are not always tagged cleanly: a tag may be just
    ``"OpenTruck"`` while the version lives in the release name
    (``"OpenTruck-0.1.0.61"``) or only in the installer filename
    (``"OpenTruckSetup-0.1.0.61.exe"``). Returns ``None`` when the text holds
    no digits at all, so a non-version tag can never be mistaken for 0.0.0.
    """
    match = re.search(r"(\d+(?:\.\d+)*)", text or "")
    if not match:
        return None
    return parse_version(match.group(1))


def release_version(release: dict) -> Optional[tuple[int, ...]]:
    """Best-effort version of a release: tag, name and installer filename.

    The MOST SPECIFIC candidate wins (the one with the most dot-segments), so
    a release tagged ``v0.2.0`` whose installer is ``OpenTruckSetup-0.2.0.85.exe``
    compares as ``0.2.0.85`` - otherwise a local build 0.2.0.84 would be told
    it is up to date against a tag that only says 0.2.0.
    """
    candidates = [release.get("tag_name"), release.get("name")]
    asset = find_setup_asset(release)
    if asset:
        candidates.append(asset.get("name"))
    parsed = [version_from_text(str(c or "")) for c in candidates]
    parsed = [p for p in parsed if p]
    if not parsed:
        return None
    return max(parsed, key=lambda p: (len(p), p))


def pick_latest_release(releases: list) -> Optional[dict]:
    """Choose the release the update check should compare against.

    Drafts are ignored. Published (non-prerelease) releases win when any
    exist; a repo that only ever publishes pre-releases still works, because
    otherwise those users could never update. Among the eligible releases the
    highest version wins (recency breaks ties).
    """
    published = [r for r in (releases or []) if not r.get("draft")]
    stable = [r for r in published if not r.get("prerelease")]
    pool = stable or published
    scored = [(release_version(r), r) for r in pool]
    scored = [(ver, r) for ver, r in scored if ver is not None]
    if not scored:
        return None
    return max(scored, key=lambda item: (item[0], item[1].get("published_at") or ""))[1]


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
