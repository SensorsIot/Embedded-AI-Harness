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
        "--run-wifi-dut",
        action="store_true",
        default=False,
        help="the DUT runs firmware that joins the bench AP (station-event, "
             "captive-portal and HTTP-relay tests need this)",
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
    config.addinivalue_line(
        "markers",
        "requires_wifi_dut: test needs a DUT running firmware that joins the AP",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-wifi-dut", default=False):
        skip_wifi = pytest.mark.skip(
            reason="precondition unmet: needs a DUT running firmware that "
                   "joins the bench AP (use --run-wifi-dut). A DUT that never "
                   "connects is an absent precondition, not a bench failure")
        for item in items:
            if "requires_wifi_dut" in item.keywords:
                item.add_marker(skip_wifi)

    run_dut = config.getoption("--run-dut", default=False)
    if not run_dut:
        skip_dut = pytest.mark.skip(reason="Requires a DUT (use --run-dut)")
        for item in items:
            if "requires_wifi_dut" in item.keywords:
                item.add_marker(skip_dut)
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
    """Session-scoped connection to the Embedded Workbench."""
    url = request.config.getoption("--wt-url")
    driver = WorkbenchDriver(url)
    driver.open()
    driver.ping()
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
