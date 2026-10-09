"""Host tier for the security test fixtures: FR-038 (untrusted HTTPS mirror)
and FR-039 (AP network port scan). Pure logic only — no sockets, no files."""
import pytest

import netscan_controller as ns
import tls_mirror_controller as tls

SUBNET = "192.168.4.0/24"
PI = "192.168.4.1"


# ── FR-038 ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("cert,key,want", [
    (False, False, True), (True, False, True), (False, True, True), (True, True, False),
])
def test_fr038_generates_only_when_a_half_is_missing(cert, key, want):
    assert tls.needs_new_cert(cert, key) is want


def test_fr038_openssl_command_is_self_signed_and_keyless():
    cmd = tls.openssl_command("/d/c.pem", "/d/k.pem")
    assert cmd[:3] == ["openssl", "req", "-x509"]
    assert "-nodes" in cmd
    assert cmd[cmd.index("-out") + 1] == "/d/c.pem"
    assert cmd[cmd.index("-keyout") + 1] == "/d/k.pem"
    assert f"/CN={tls.CERT_CN}" in cmd


def test_fr038_resolves_a_firmware_file_under_the_root():
    assert tls.resolve_firmware_path("/fw", "/firmware/p/f.bin") == "/fw/p/f.bin"
    assert tls.resolve_firmware_path("/fw", "/firmware/p/f.json?x=1") == "/fw/p/f.json"


@pytest.mark.parametrize("path", [
    "/firmware/../x", "/firmware/p/../x", "/firmware/p/..", "/firmware/p",
    "/firmware/p/f/g", "/firmware//f", "/api/info", "/", "firmware/p/f",
    "/firmware/p/a\\b", "/firmware/./f",
])
def test_fr038_rejects_paths_outside_the_repository(path):
    assert tls.resolve_firmware_path("/fw", path) is None


# ── FR-039 ───────────────────────────────────────────────────────────────

def test_fr039_accepts_a_single_ap_host():
    assert ns.validate_target("192.168.4.15", SUBNET, PI) == "192.168.4.15"


@pytest.mark.parametrize("host", [
    "192.168.4.1",       # the testbench itself
    "192.168.0.10",      # the LAN
    "192.168.4.0",       # network address
    "192.168.4.255",     # broadcast
    "192.168.4.0/24",    # a range
    "example.com",       # a name
    "",
    None,
    5,
])
def test_fr039_refuses_every_other_target(host):
    with pytest.raises(ValueError):
        ns.validate_target(host, SUBNET, PI)


@pytest.mark.parametrize("spec,want", [
    ("80", [80]),
    ("1-3,7", [1, 2, 3, 7]),
    ("7, 1-3, 2", [1, 2, 3, 7]),
    ("65535", [65535]),
])
def test_fr039_parses_port_specs(spec, want):
    assert ns.parse_ports(spec) == want


def test_fr039_full_range_counts_each_port_once():
    assert len(ns.parse_ports("1-65535,80")) == 65535


@pytest.mark.parametrize("spec", ["0", "65536", "5-3", "a", "", "1-", "-5", "1,,2", None])
def test_fr039_rejects_bad_port_specs(spec):
    with pytest.raises(ValueError):
        ns.parse_ports(spec)


@pytest.mark.parametrize("value,want", [(None, 120.0), (1, 1.0), ("600", 600.0)])
def test_fr039_timeout_within_bounds(value, want):
    assert ns.clamp_timeout(value) == want


@pytest.mark.parametrize("value", [0, 0.5, 601, "x", [1]])
def test_fr039_timeout_out_of_bounds_rejected(value):
    with pytest.raises(ValueError):
        ns.clamp_timeout(value)
