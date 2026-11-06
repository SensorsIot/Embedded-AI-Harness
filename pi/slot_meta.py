"""Per-slot facts an operator sets or the bench measured, judged for display.

Pure: no files, no hardware, no clock of its own. portal.py reads and writes
the JSON files and passes the records in.

- FR-041: a slot carries an operator-set board name ("T-SIM7080G"), so several
  boards on one bench are told apart by more than their slot number.
- FR-042: a BOOT/EN wiring measurement belongs to one board at one time. It is
  shown only while that board is in the slot, and is not trusted once another
  board is there or the measurement is older than its maximum age.
"""
import re
from datetime import datetime
from zoneinfo import ZoneInfo

# The bench's operator works in US Eastern time; every time the dashboard
# shows is in that zone, with EST/EDT spelled out.
BENCH_TZ = ZoneInfo("America/New_York")

BOARD_NAME_MAX = 40
WIRING_MAX_AGE_S_DEFAULT = 7 * 24 * 3600

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def clean_board_name(name) -> str | None:
    """An operator's board name, tidied, or None to clear it.

    Raises ValueError for a value that is not a string or is too long.
    """
    if name is None:
        return None
    if not isinstance(name, str):
        raise ValueError("name must be a string")
    name = " ".join(_CONTROL.sub(" ", name).split())
    if not name:
        return None
    if len(name) > BOARD_NAME_MAX:
        raise ValueError(f"name is longer than {BOARD_NAME_MAX} characters")
    return name


def bench_time(ts: float | None) -> str | None:
    """Epoch seconds as bench-local text, e.g. "2026-11-06 08:33 EST"."""
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, BENCH_TZ).strftime("%Y-%m-%d %H:%M %Z")


def bench_iso(ts: float) -> str:
    """Epoch seconds as ISO 8601 with the Eastern offset, for stored records."""
    return datetime.fromtimestamp(ts, BENCH_TZ).isoformat(timespec="seconds")


def wiring_verdict(record: dict | None, present: bool,
                   board_serial: str | None, now: float,
                   max_age_s: float = WIRING_MAX_AGE_S_DEFAULT) -> dict:
    """Judge a stored BOOT/EN measurement against the board in the slot now.

    Returns:
      status  "untested" | "wired" | "not_wired" | "stale" | "other_board"
      wired   True/False only for a current measurement of this board, else
              None — recovery takes the GPIO path only on True
      show    whether the dashboard shows it: only while a board is present,
              and never a result that belongs to another board
      checked_at  when it was measured, in bench time (None if unknown)
      reason  why a result is stale, else None
    """
    out = {"status": "untested", "wired": None, "show": False,
           "checked_at": None, "reason": None}
    if not record:
        return out
    ts = record.get("checked_ts")
    out["checked_at"] = bench_time(ts) if ts is not None else record.get("checked_at")

    recorded_serial = record.get("board_serial")
    if (board_serial and recorded_serial
            and board_serial != recorded_serial):
        out["status"] = "other_board"
        return out

    if "board_serial" not in record or ts is None:
        # Written before measurements named their board and time: nothing
        # says which board it was, so it cannot be trusted for this one.
        out["status"] = "stale"
        out["reason"] = "recorded before the bench noted which board it tested"
    elif now - ts > max_age_s:
        out["status"] = "stale"
        days = max_age_s / 86400
        out["reason"] = (f"older than {days:g} day{'s' if days != 1 else ''}"
                         if days >= 1 else
                         f"older than {max_age_s / 3600:g} h")
    else:
        wired = bool(record.get("gpio_wired"))
        out["status"] = "wired" if wired else "not_wired"
        out["wired"] = wired
    out["show"] = bool(present)
    return out
