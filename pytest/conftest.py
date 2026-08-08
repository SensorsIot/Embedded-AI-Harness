"""Pytest fixtures for the Embedded Workbench (HTTP-only, Pi backend).

Usage:
    pytest workbench_test.py --wt-url http://<pi-ip>:8080
"""

import os
import uuid

import pytest

from workbench_driver import WorkbenchDriver


def pytest_addoption(parser):
    parser.addoption(
        "--wt-url",
        default=os.environ.get("WORKBENCH_URL", "http://localhost:8080"),
        help="Portal URL for the Embedded Workbench Pi",
    )
    parser.addoption(
        "--run-dut",
        action="store_true",
        default=False,
        help="Run tests that require a DUT connected",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "requires_dut: test needs a DUT or second WiFi device connected",
    )


def pytest_collection_modifyitems(config, items):
    """Only `requires_dut` is gated by a flag now.

    `requires_wifi_dut` used to hide twelve tests behind --run-wifi-dut,
    because nothing on the bench could join an AP and the suite had no way
    to tell "no device" from "device broken". The bench now owns that
    device, and the `bench_dut` fixture answers the question directly: it
    provisions the board, or skips naming exactly what is absent. A flag on
    top of that would only let a real failure hide as an opt-out.
    """
    if not config.getoption("--run-dut", default=False):
        skip_dut = pytest.mark.skip(reason="Requires a DUT (use --run-dut)")
        for item in items:
            if "requires_dut" in item.keywords:
                item.add_marker(skip_dut)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Attach test outcome to the node so fixtures can read it."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture(scope="session")
def workbench(request):
    """Session-scoped connection to the Embedded Workbench.

    The run begins with a bench reset (FR-036), which is what that endpoint
    was built for and what nothing was calling. Skipping it is not a
    theoretical risk: a run started on a bench carrying two live debug
    sessions and leftover SDR and WiFi state took the portal down partway
    through and failed nineteen tests, none of which had anything wrong with
    them. The same suite, on the same hardware, minutes later and after a
    reset: no failures.

    A reset that cannot be performed is reported, not swallowed — starting
    from an unknown state is exactly what this prevents.
    """
    url = request.config.getoption("--wt-url")
    driver = WorkbenchDriver(url)
    driver.open()
    driver.ping()
    r = driver.bench_reset()
    if not r.get("ok"):
        pytest.exit(f"bench reset failed, refusing to run from an unknown "
                    f"state: {r}", returncode=3)
    if r.get("changed"):
        print(f"\nbench reset: {', '.join(r['changed'])}")
    yield driver
    try:
        driver.ap_stop()
    except Exception:
        pass
    driver.close()


@pytest.fixture
def wifi_network(workbench):
    """Start a fresh AP for this test, stop on teardown."""
    ssid = f"WT-{uuid.uuid4().hex[:6].upper()}"
    password = "testpass123"
    workbench.drain_events()
    workbench.ap_start(ssid, password)
    yield {"ssid": ssid, "password": password, "ap_ip": "192.168.4.1"}
    workbench.ap_stop()


# The bench's own DUT — the firmware in test-firmware/, built by CI.
BENCH_DUT_PORTAL = "WB-Test-Setup"   # SSID it advertises unprovisioned
BENCH_DUT_HTTP_PORT = 8080           # its own server, not the portal's


@pytest.fixture(scope="session")
def bench_dut(workbench):
    """A DUT on the bench AP, provisioned through its captive portal.

    Session-scoped on purpose. Provisioning costs a reboot and half a
    minute, and every test that needs a joined DUT needs the same one; a
    per-test fixture would re-provision a dozen times and prove nothing
    extra. The SSID is still fresh per session, so a pass still shows the
    DUT used what it was just given rather than something cached.

    The device is the bench's own — never a project's board. A workbench
    test that asserts on project firmware goes red when that project ships,
    which is the dependency backwards.
    """
    ssid = f"WT-{uuid.uuid4().hex[:6].upper()}"
    password = "testpass123"
    workbench.drain_events()
    workbench.ap_start(ssid, password, internet=True)

    station = _wait_for_any_station(workbench, timeout=20)
    if not station:
        # Not joined: either unprovisioned, or holding a previous run's
        # SSID. Either way its portal is the way in — the firmware clears
        # stale credentials and returns to the portal by itself.
        if not _portal_is_up(workbench):
            _ap_stop_quietly(workbench)
            pytest.skip(
                f"precondition unmet: no bench DUT. Nothing joined the AP "
                f"and no '{BENCH_DUT_PORTAL}' portal is on the air. Flash "
                f"test-firmware/ to a free slot (CI publishes it as "
                f"bench-dut-<target>)."
            )
        workbench.provision_wifimanager(
            BENCH_DUT_PORTAL, ssid, password,
            save_path="/connect", field_ssid="ssid",
            field_password="password", internet=True)
        station = _wait_for_any_station(workbench, timeout=120)

    if not station:
        _ap_stop_quietly(workbench)
        pytest.skip(
            "precondition unmet: the bench DUT was provisioned but never "
            f"joined '{ssid}'"
        )

    yield {
        "ssid": ssid, "password": password, "ap_ip": "192.168.4.1",
        "mac": station["mac"], "ip": station["ip"],
        "url": f"http://{station['ip']}:{BENCH_DUT_HTTP_PORT}",
    }
    _ap_stop_quietly(workbench)


def _ap_stop_quietly(workbench):
    """Bring the AP down without letting the attempt become the verdict.

    ap_stop reconfigures hostapd and dnsmasq and can exceed the driver's
    timeout when the radio is busy. Raised out of a fixture, that turns a
    truthful skip ("no bench DUT") into nine ERRORs about a POST — and the
    next test then meets a radio nobody finished putting away.
    """
    try:
        workbench.ap_stop()
    except Exception:
        pass


def _wait_for_any_station(workbench, timeout: float):
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        stations = workbench.ap_status().get("stations") or []
        if stations and stations[0].get("ip"):
            return stations[0]
        time.sleep(3)
    return None


def _portal_is_up(workbench) -> bool:
    """Is the DUT advertising its provisioning portal?

    Scanning needs the radio, which the AP is using, so this is best-effort:
    a scan that cannot run is not evidence the portal is absent.
    """
    try:
        nets = workbench.scan().get("networks", [])
    except Exception:
        return True          # cannot tell — let provisioning try and fail loudly
    return any(n["ssid"] == BENCH_DUT_PORTAL for n in nets)
