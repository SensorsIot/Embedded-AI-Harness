"""Host tier for FR-041 (board names) and FR-042 (BOOT/EN result staleness)."""
import pytest

import slot_meta as sm

MAC = "48:27:E2:EA:48:3C"
OTHER = "AA:BB:CC:DD:EE:FF"
T0 = 1_793_000_000.0          # 2026-10-26, a fixed clock
DAY = 86400.0


def rec(wired=False, serial=MAC, ts=T0):
    return {"gpio_wired": wired, "en_wired": wired, "boot_wired": wired,
            "detail": "", "board_serial": serial, "checked_ts": ts,
            "checked_at": sm.bench_iso(ts)}


# ── FR-041 ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,want", [
    ("T-SIM7080G", "T-SIM7080G"),
    ("  T-Display   AMOLED \n", "T-Display AMOLED"),
    ("", None),
    ("   ", None),
    (None, None),
    ("a\x00b", "a b"),
])
def test_fr041_clean_board_name(raw, want):
    assert sm.clean_board_name(raw) == want


@pytest.mark.parametrize("raw", ["x" * (sm.BOARD_NAME_MAX + 1), 7, ["a"]])
def test_fr041_board_name_refused(raw):
    with pytest.raises(ValueError):
        sm.clean_board_name(raw)


# ── FR-043 ────────────────────────────────────────────────────────────────

NOTECARD = [{"product": "Notecard", "vid_pid": "30a4:0001"}]
ESP_USB = [{"product": "USB JTAG/serial debug unit", "vid_pid": "303a:1001"}]
CP2102 = [{"product": "CP2102 USB to UART", "vid_pid": "10c4:ea60"}]


@pytest.mark.parametrize("chip,devs,want", [
    ("esp32s3", ESP_USB, True),
    (None, ESP_USB, True),       # native USB before the chip is probed
    (None, CP2102, True),        # bridge board: chip never auto-detected
    (None, NOTECARD, False),
    ("esp32", NOTECARD, True),   # a detected ESP chip always wins
    (None, [], True),            # nothing known: keep the test
])
def test_fr043_boot_pins_apply(chip, devs, want):
    assert sm.boot_pins_apply(chip, devs) is want


# ── FR-042 ────────────────────────────────────────────────────────────────

def test_fr042_untested():
    v = sm.wiring_verdict(None, True, MAC, T0)
    assert v["status"] == "untested" and v["wired"] is None and not v["show"]


@pytest.mark.parametrize("wired,status", [(False, "not_wired"),
                                          (True, "wired")])
def test_fr042_current_result_shown_for_its_board(wired, status):
    v = sm.wiring_verdict(rec(wired), True, MAC, T0 + 60)
    assert v["status"] == status and v["wired"] is wired and v["show"]


def test_fr042_hidden_while_slot_empty_but_kept():
    v = sm.wiring_verdict(rec(False), False, None, T0 + 60)
    assert not v["show"]
    assert v["wired"] is False   # still the fact recovery relies on mid-flap


def test_fr042_other_board_not_shown_or_trusted():
    v = sm.wiring_verdict(rec(True), True, OTHER, T0 + 60)
    assert v["status"] == "other_board"
    assert v["wired"] is None and not v["show"]


def test_fr042_old_result_is_stale():
    v = sm.wiring_verdict(rec(True), True, MAC, T0 + 8 * DAY, 7 * DAY)
    assert v["status"] == "stale" and v["wired"] is None and v["show"]
    assert "7 days" in v["reason"]


def test_fr042_legacy_record_is_stale():
    legacy = {"gpio_wired": False, "detail": "",
              "checked_at": "2026-11-01T10:00:00"}
    v = sm.wiring_verdict(legacy, True, MAC, T0)
    assert v["status"] == "stale" and v["wired"] is None
    assert v["checked_at"] == "2026-11-01T10:00:00"


def test_fr042_board_without_serial_judged_by_age_only():
    v = sm.wiring_verdict(rec(True, serial=None), True, None, T0 + 60)
    assert v["status"] == "wired" and v["wired"] is True


@pytest.mark.parametrize("ts,want", [
    (1_793_000_000.0, "EDT"),   # late October: daylight time
    (1_794_500_000.0, "EST"),   # mid November: standard time
])
def test_fr042_times_are_us_eastern(ts, want):
    assert sm.bench_time(ts).endswith(want)
