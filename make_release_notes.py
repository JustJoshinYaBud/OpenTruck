"""Generate releasenotes.py (this build's release notes) from CHANGELOG.md.

Run by ``build.bat`` right after the version bump: extracts the CHANGELOG.md
section titled with the version being built and writes it into
``releasenotes.py``, which PyInstaller bundles with the app. The app shows
those notes ONCE at startup after an update (``app._show_release_notes_once``)
- so the changelog a user sees in the popup is exactly the curated public
changelog for the version they just updated to.

``releasenotes.py`` is generated output and git-ignored; CHANGELOG.md stays
the single source of truth. A missing changelog section is a loud warning,
not a build failure (the popup simply does not ship for that build).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    from version import full_version
    full = full_version()
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(
        r"^## \[" + re.escape(full) + r"\][^\n]*\n(.*?)(?=^## \[|\Z)",
        text, re.M | re.S)
    if not m:
        print(f"WARN: CHANGELOG.md has no section for {full} - the in-app "
              "release-notes popup will not ship with this build. Add a "
              f"'## [{full}]' section before releasing.")
        return 0
    body = m.group(1).strip()
    if '"""' in body:
        # Markdown prose will not carry a triple quote, but never let a
        # formatting quirk break the generated module silently.
        print(f"WARN: changelog body for {full} contains triple quotes; "
              "escaping")
        body = body.replace('"""', r'\"\"\"')
    (ROOT / "releasenotes.py").write_text(
        '"""Release notes for this build, shown once at startup after an\n'
        'update. Generated from CHANGELOG.md by make_release_notes.py at\n'
        'build time - do not edit by hand.\n"""\n'
        f'NOTES_VERSION = "{full}"\n'
        'NOTES = """\n'
        f'{body}\n'
        '"""\n',
        encoding="utf-8")
    print(f"releasenotes.py written for {full}")
    return 0


if __name__ == "__main__":
    sys.exit(main())