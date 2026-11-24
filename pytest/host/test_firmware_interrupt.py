"""Host tier for FR-040 (interrupted firmware download): which request is cut,
at which byte, and what is refused. Pure logic only — no sockets, no files."""
import pytest

import firmware_interrupt as fi

SIZE = 1000


def arm(**kw):
    body = {"project": "p", "filename": "f.bin", **kw}
    return fi.validate(body, SIZE)


def test_fr040_fraction_cuts_at_the_floor_of_the_byte_count():
    rule, err = arm(after_fraction=0.5)
    assert err is None and rule["cut_at"] == 500 and rule["size"] == SIZE
    assert arm(after_fraction=0.3333)[0]["cut_at"] == 333


def test_fr040_defaults_close_once_60s():
    rule, _ = arm(after_bytes=10)
    assert (rule["mode"], rule["once"], rule["hold_s"]) == ("close", True, 60)


@pytest.mark.parametrize("kw", [
    {}, {"after_bytes": 1, "after_fraction": 0.5},
    {"after_bytes": SIZE}, {"after_bytes": -1}, {"after_bytes": 1.5}, {"after_bytes": True},
    {"after_fraction": 1}, {"after_fraction": -0.1}, {"after_fraction": "0.5"},
    {"after_bytes": 1, "mode": "reset"}, {"after_bytes": 1, "hold_s": 0},
    {"after_bytes": 1, "hold_s": fi.MAX_HOLD_S + 1}, {"after_bytes": 1, "once": "yes"},
])
def test_fr040_rejects_invalid_arm_requests(kw):
    rule, err = arm(**kw)
    assert rule is None and err


@pytest.mark.parametrize("project,filename", [
    ("..", "f.bin"), ("p", "../f.bin"), ("p/q", "f.bin"), ("p", "a\\b"), ("", "f.bin"), ("p", None),
])
def test_fr040_rejects_names_outside_the_repository(project, filename):
    rule, err = fi.validate({"project": project, "filename": filename, "after_bytes": 1}, SIZE)
    assert rule is None and err


def test_fr040_missing_file_is_not_armed():
    rule, err = fi.validate({"project": "p", "filename": "f.bin", "after_bytes": 1}, None)
    assert rule is None and err == "not found"


def test_fr040_one_shot_cuts_the_next_request_only():
    reg = fi.Registry()
    reg.arm(arm(after_fraction=0.5)[0])
    assert reg.take("p", "other.bin") is None
    assert reg.take("p", "f.bin")["cut_at"] == 500
    assert reg.take("p", "f.bin") is None


def test_fr040_persistent_cut_stays_until_cleared():
    reg = fi.Registry()
    reg.arm(arm(after_bytes=7, once=False, mode="stall", hold_s=5)[0])
    assert reg.take("p", "f.bin")["cut_at"] == 7
    assert reg.take("p", "f.bin")["mode"] == "stall"
    assert reg.clear() is True and reg.take("p", "f.bin") is None
    assert reg.clear() is False


def test_fr040_rearming_a_file_replaces_its_rule():
    reg = fi.Registry()
    reg.arm(arm(after_bytes=7)[0])
    reg.arm(arm(after_bytes=9)[0])
    assert [r["cut_at"] for r in reg.list()] == [9]


def test_fr040_taken_rule_is_a_copy():
    reg = fi.Registry()
    reg.arm(arm(after_bytes=7, once=False)[0])
    reg.take("p", "f.bin")["cut_at"] = 0
    assert reg.take("p", "f.bin")["cut_at"] == 7


def test_fr040_log_line():
    rule, _ = arm(after_fraction=0.5)
    assert fi.log_line(rule, 500) == "firmware: p/f.bin cut after 500 of 1000 bytes (close)"
