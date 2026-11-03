"""OpenTruck - persistent connection diagnostics log.

A field failure ("adapter wouldn't connect on this truck") is impossible to
diagnose from a dialog: the popup text is the only record, and it is gone the
moment someone clicks OK. That is exactly what happened with the CAT CA3 and
the 2007 CAT-engined Freightliner - two rounds of fixes went in against
guesses rather than the adapter's own words.

Every connection event appends one timestamped line here: which adapter was
chosen, every protocol string tried and its return code, the filter and
address-claim results, which channels opened, and the text of any failure.

**Where the file lives.** In the per-user local app data folder. Writing next
to the program was tried and rejected: Program Files is not writable to a
normal process, so it would have needed a special ACL for no real gain. The
actual requirement - easy to reach, easy to mail - is met inside the app
instead: Help > Open diagnostics log shows the contents (rotated generations
included) in a read-only pane with a "Copy all to clipboard" button.

**Bounded size.** The file is rotated at ``MAX_BYTES`` and only
``KEEP_GENERATIONS`` older files are kept, so a machine that has been in
service for years cannot accumulate a multi-megabyte log nobody can email.
Rotation is best-effort inside the same never-raise guard as the write: losing
a log line must never cost a connection.

Never raises. Diagnostics must not be able to break a connect attempt.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time

_FILENAME = "connection.log"
_RESOLVED: str | None = None

# 1 MB is several thousand connect attempts (a full attempt is ~20 lines) -
# enough to still hold last month's failure, small enough to attach to an email.
MAX_BYTES = 1_000_000
KEEP_GENERATIONS = 2          # connection.log.1, connection.log.2
_MAX_MESSAGE = 2000           # a runaway vendor string cannot bloat a line


def _app_dir() -> str:
    """Folder the program runs from (kept for diagnostics/portable builds)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def candidates() -> list[str]:
    """Where the log may live. One entry: the per-user app data folder.

    Deliberately not next to the program - see the module docstring. It is
    listed as a single-element list because the resolution logic below is
    generic and a portable build may add locations later.
    """
    local = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    return [os.path.join(local, "OpenTruck", _FILENAME)]


def _writable(target: str) -> bool:
    """True when we can create the folder and append to the file."""
    folder = os.path.dirname(target)
    try:
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(target, "a", encoding="utf-8"):
            pass
        return True
    except OSError:
        return False


def path() -> str:
    """Full path of the log file, resolved once per run."""
    global _RESOLVED
    if _RESOLVED:
        return _RESOLVED
    options = candidates()
    for option in options:
        if _writable(option):
            _RESOLVED = option
            return option
    _RESOLVED = options[-1]      # report the intended path even if unwritable
    return _RESOLVED


def _rotate(target: str) -> None:
    """Shift generations once ``target`` is full; the oldest is dropped."""
    try:
        # Oldest first: drop the last generation, then walk each one up.
        for gen in range(KEEP_GENERATIONS, 0, -1):
            src = "%s.%d" % (target, gen)
            dst = "%s.%d" % (target, gen + 1)
            if os.path.exists(src):
                if gen == KEEP_GENERATIONS:
                    os.remove(src)          # beyond what we keep
                else:
                    os.replace(src, dst)
        os.replace(target, target + ".1")
    except OSError:
        # Cannot rotate (file locked by a reader, permissions): leave it alone.
        # It will simply keep growing until a run can rotate it.
        pass


def write(message: str) -> None:
    """Append one timestamped line, rotating first if the file is full."""
    global _RESOLVED
    try:
        target = path()
        folder = os.path.dirname(target)
        if folder:
            os.makedirs(folder, exist_ok=True)   # may have been deleted mid-run
        try:
            if os.path.getsize(target) >= MAX_BYTES:
                _rotate(target)
                _RESOLVED = target         # rotation kept the same path
        except OSError:
            pass                           # size unknown: just append
        with open(target, "a", encoding="utf-8") as handle:
            handle.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"),
                                      message[:_MAX_MESSAGE]))
    except OSError:
        pass


def read_all(max_chars: int = 400_000) -> str:
    """Whole log as text, newest generation first, for the in-app viewer.

    Rotated files are included - they may hold the failure that mattered - each
    under a header naming the file. An enormous log is truncated from the
    FRONT, so the newest lines (the ones describing the current failure) are
    the ones that survive.
    """
    parts: list[str] = []
    for generation in range(0, KEEP_GENERATIONS + 1):
        target = path() if generation == 0 else "%s.%d" % (path(), generation)
        try:
            with open(target, encoding="utf-8", errors="replace") as handle:
                body = handle.read()
        except OSError:
            continue
        parts.append("----- %s -----\n%s" % (os.path.basename(target), body))
    text = "\n".join(parts)
    if len(text) > max_chars:
        text = "...(older lines omitted)...\n" + text[-max_chars:]
    return text
