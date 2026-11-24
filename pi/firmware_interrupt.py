"""FR-040 — interrupted firmware download.

A DUT must survive an OTA download that stops part-way: the server closes the
connection (the client sees EOF before Content-Length) or goes silent with the
connection open (the client must time out). Only the Pi is on the AP network,
so only the Pi's firmware route (FR-021) can produce either stimulus.

A test *arms* a cut for one file; the next GET of that file announces the
whole Content-Length, sends the first N bytes, then closes or stalls. The URL
is the DUT's choice, so the cut is armed by name, never by query string.

Pure logic and a small locked registry — no sockets, no files — so the whole
decision is host-tested (pytest/host/test_firmware_interrupt.py).
"""
from __future__ import annotations

import threading

MODES = ("close", "stall")
DEFAULT_HOLD_S = 60
MAX_HOLD_S = 600


def _bad_name(s) -> bool:
    return (not isinstance(s, str) or not s or ".." in s or "/" in s
            or "\\" in s)


def validate(body: dict, file_size: int | None) -> tuple[dict | None, str | None]:
    """(rule, None) for a valid arm request, else (None, reason).

    file_size is the size of the named file now, or None when it does not
    exist. A cut is fixed in bytes at arm time, so a test knows exactly how
    many bytes the DUT will receive.
    """
    if not isinstance(body, dict):
        return None, "body must be a JSON object"
    project, filename = body.get("project"), body.get("filename")
    if _bad_name(project) or _bad_name(filename):
        return None, "project and filename are required plain names"
    if file_size is None:
        return None, "not found"
    has_b, has_f = "after_bytes" in body, "after_fraction" in body
    if has_b == has_f:
        return None, "give exactly one of after_bytes, after_fraction"
    if has_b:
        n = body["after_bytes"]
        if isinstance(n, bool) or not isinstance(n, int) or not 0 <= n < file_size:
            return None, f"after_bytes must be an integer 0..{file_size - 1}"
        cut = n
    else:
        f = body["after_fraction"]
        if isinstance(f, bool) or not isinstance(f, (int, float)) or not 0 <= f < 1:
            return None, "after_fraction must be a number 0 <= f < 1"
        cut = int(file_size * f)
    mode = body.get("mode", "close")
    if mode not in MODES:
        return None, f"mode must be one of {', '.join(MODES)}"
    hold = body.get("hold_s", DEFAULT_HOLD_S)
    if isinstance(hold, bool) or not isinstance(hold, (int, float)) or not 0 < hold <= MAX_HOLD_S:
        return None, f"hold_s must be a number 0 < s <= {MAX_HOLD_S}"
    once = body.get("once", True)
    if not isinstance(once, bool):
        return None, "once must be true or false"
    return {"project": project, "filename": filename, "cut_at": cut,
            "size": file_size, "mode": mode, "hold_s": hold, "once": once}, None


def log_line(rule: dict, sent: int) -> str:
    """The activity-log entry for one cut download."""
    return (f"firmware: {rule['project']}/{rule['filename']} cut after "
            f"{sent} of {rule['size']} bytes ({rule['mode']})")


class Registry:
    """Armed cuts, at most one per file. `take` is what the download route
    calls: it returns the rule for that file (and forgets a one-shot rule), so
    two concurrent GETs of a one-shot file cannot both be cut."""

    def __init__(self):
        self._lock = threading.Lock()
        self._rules: dict[tuple[str, str], dict] = {}

    def arm(self, rule: dict) -> None:
        with self._lock:
            self._rules[(rule["project"], rule["filename"])] = dict(rule)

    def take(self, project: str, filename: str) -> dict | None:
        with self._lock:
            rule = self._rules.get((project, filename))
            if rule and rule["once"]:
                del self._rules[(project, filename)]
            return dict(rule) if rule else None

    def list(self) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self._rules.values()]

    def clear(self) -> bool:
        """Forget every armed cut; True when there was one."""
        with self._lock:
            had = bool(self._rules)
            self._rules.clear()
            return had
