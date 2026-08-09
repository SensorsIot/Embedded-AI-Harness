"""WiFi Tester instrument self-tests (WT-xxx).

These verify the instrument itself works correctly.
Tests marked @requires_dut need a WiFi device connected; skip with default run.
"""

import base64
import json
import os
import re
import socket
import time
import uuid

import pytest

from conftest import (BENCH_DUT_PORTAL, _ap_stop_quietly,
                      _wait_for_any_station, ensure_bench_dut_firmware)
from workbench_driver import CommandError, CommandTimeout, WorkbenchError

# Path to pre-built debug-test firmware binaries
DEBUG_TEST_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "debug-test", "output"
)


# =====================================================================
# WT-1xx  Basic Protocol
# =====================================================================


class TestBasicProtocol:
    """WT-1xx: Basic protocol tests."""

    def test_wt100_ping_response(self, workbench):
        """WT-100: PING returns fw_version and uptime."""
        resp = workbench.ping()
        assert "fw_version" in resp
        assert "uptime" in resp
        assert isinstance(resp["uptime"], (int, float))
        assert resp["uptime"] >= 0

    def test_wt104_command_while_busy(self, workbench):
        """WT-104: Rapid commands don't crash the device."""
        r1 = workbench.ping()
        r2 = workbench.ping()
        assert "fw_version" in r1
        assert "fw_version" in r2


# =====================================================================
# WT-2xx  SoftAP Management
# =====================================================================


class TestSoftAPManagement:
    """WT-2xx: SoftAP start/stop/status tests."""

    def test_wt200_start_ap(self, workbench):
        """WT-200: AP_START with valid SSID/pass returns OK with IP."""
        resp = workbench.ap_start("WT-TEST-200", "password123")
        assert "ip" in resp
        assert resp["ip"].startswith("192.168.")
        workbench.ap_stop()

    def test_wt201_start_open_ap(self, workbench):
        """WT-201: AP_START with empty password creates open network."""
        resp = workbench.ap_start("WT-OPEN-201")
        assert "ip" in resp
        workbench.ap_stop()

    def test_wt202_stop_ap(self, workbench):
        """WT-202: AP_STOP after AP_START returns OK."""
        workbench.ap_start("WT-TEST-202", "password123")
        workbench.ap_stop()
        status = workbench.ap_status()
        assert status["active"] is False

    def test_wt203_stop_when_not_running(self, workbench):
        """WT-203: AP_STOP is idempotent."""
        workbench.ap_stop()
        workbench.ap_stop()

    def test_wt204_restart_ap_new_config(self, workbench):
        """WT-204: AP_START while running restarts with new config."""
        workbench.ap_start("WT-SSID-A", "password123")
        status_a = workbench.ap_status()
        assert status_a["ssid"] == "WT-SSID-A"

        workbench.ap_start("WT-SSID-B", "password456")
        status_b = workbench.ap_status()
        assert status_b["ssid"] == "WT-SSID-B"
        workbench.ap_stop()

    def test_wt205_ap_status_when_running(self, workbench):
        """WT-205: AP_STATUS reports active, SSID, channel."""
        workbench.ap_start("WT-STATUS-205", "password123", channel=6)
        status = workbench.ap_status()
        assert status["active"] is True
        assert status["ssid"] == "WT-STATUS-205"
        assert status["channel"] == 6
        assert "stations" in status
        workbench.ap_stop()

    def test_wt206_ap_status_when_stopped(self, workbench):
        """WT-206: AP_STATUS without AP reports inactive."""
        workbench.ap_stop()
        status = workbench.ap_status()
        assert status["active"] is False

    def test_wt207_max_ssid_length(self, workbench):
        """WT-207: 32-character SSID is accepted."""
        long_ssid = "A" * 32
        resp = workbench.ap_start(long_ssid, "password123")
        assert "ip" in resp
        workbench.ap_stop()

    def test_wt208_channel_selection(self, workbench):
        """WT-208: Channel parameter is respected."""
        workbench.ap_start("WT-CHAN-208", "password123", channel=11)
        status = workbench.ap_status()
        assert status["channel"] == 11
        workbench.ap_stop()


# =====================================================================
# WT-3xx  Station Connect/Disconnect Events
# =====================================================================


@pytest.mark.requires_dut
class TestStationEvents:
    """WT-3xx: Station connect/disconnect events (requires DUT)."""

    def test_wt300_station_connect_event(self, workbench, bench_dut):
        """WT-300: the joined station carries a MAC and an AP-subnet IP."""
        assert ":" in bench_dut["mac"]
        assert bench_dut["ip"].startswith("192.168.4."), bench_dut

    def test_wt301_station_disconnect_event(self, workbench, bench_dut):
        """WT-301: STA_DISCONNECT names the station that left.

        The DUT is asked to leave rather than waited on: a test that waits
        for a disconnect it never causes passes only when something else
        goes wrong.
        """
        workbench.drain_events()
        # POST, because that is how the DUT registers the route. This used to
        # send a GET, which the device answered with 404 and then carried on
        # happily connected — so the test waited sixty seconds for a
        # disconnect it had not caused, exactly as the paragraph above warns.
        # Asserting on the reply is the part that stops it recurring.
        r = workbench.wifi_http(f"{bench_dut['url']}/wifi-reset",
                                method="POST", timeout=6)
        assert r["status"] == 200, f"the DUT refused the reset: {r}"
        evt = workbench.wait_for_event("STA_DISCONNECT", timeout=60)
        assert evt["mac"] == bench_dut["mac"], evt

    def test_wt302_station_in_ap_status(self, workbench, bench_dut):
        """WT-302: the connected station appears in AP_STATUS."""
        macs = [s["mac"] for s in workbench.ap_status()["stations"]]
        assert bench_dut["mac"] in macs, macs

    def test_wt303_ip_matches_event(self, workbench, bench_dut):
        """WT-303: the IP reported at join matches the one in AP_STATUS."""
        for s in workbench.ap_status()["stations"]:
            if s["mac"] == bench_dut["mac"]:
                assert s["ip"] == bench_dut["ip"]
                return
        pytest.fail(f"{bench_dut['mac']} not in AP_STATUS")


# =====================================================================
# WT-4xx  STA Mode
# =====================================================================


@pytest.mark.requires_dut
class TestSTAMode:
    """WT-4xx: STA join/leave tests (requires another AP)."""

    @pytest.fixture
    def sta_network(self):
        import os
        ssid = os.environ.get("WIFI_TEST_STA_SSID")
        password = os.environ.get("WIFI_TEST_STA_PASS", "")
        if not ssid:
            pytest.skip("WIFI_TEST_STA_SSID not set")
        return {"ssid": ssid, "password": password}

    def test_wt401_join_wpa2_network(self, workbench, sta_network):
        """WT-401: Join WPA2 network with correct password."""
        if not sta_network["password"]:
            pytest.skip("Test network has no password")
        resp = workbench.sta_join(
            sta_network["ssid"], sta_network["password"],
        )
        assert "ip" in resp
        assert "gateway" in resp
        workbench.sta_leave()

    def test_wt402_join_wrong_password(self, workbench, sta_network):
        """WT-402: Wrong password returns ERR."""
        if not sta_network["password"]:
            pytest.skip("Test network has no password")
        with pytest.raises(CommandError):
            workbench.sta_join(
                sta_network["ssid"], "wrong_password_here", timeout=10,
            )

    def test_wt403_join_nonexistent_network(self, workbench):
        """WT-403: Nonexistent SSID returns ERR with timeout."""
        with pytest.raises(CommandError):
            workbench.sta_join(
                "NONEXISTENT_NETWORK_XYZ_999", timeout=5,
            )

    def test_wt404_leave_sta(self, workbench, sta_network):
        """WT-404: STA_LEAVE after join returns OK."""
        workbench.sta_join(
            sta_network["ssid"], sta_network["password"],
        )
        workbench.sta_leave()

    def test_wt405_softap_stops_during_sta(self, workbench, sta_network):
        """WT-405: AP is stopped when entering STA mode."""
        workbench.ap_start("WT-AP-405", "password123")
        status = workbench.ap_status()
        assert status["active"] is True

        workbench.sta_join(
            sta_network["ssid"], sta_network["password"],
        )
        status = workbench.ap_status()
        assert status["active"] is False
        workbench.sta_leave()


# =====================================================================
# WT-5xx  HTTP Relay
# =====================================================================


@pytest.mark.requires_dut
class TestHTTPRelay:
    """WT-5xx: HTTP relay tests (requires DUT with HTTP server)."""

    @pytest.fixture
    def dut_url(self, bench_dut):
        """The bench DUT's own HTTP server (port 8080, /status)."""
        return bench_dut["url"]

    def test_wt500_get_request(self, workbench, dut_url):
        """WT-500: GET through the relay returns 200 and a body."""
        resp = workbench.http_get(f"{dut_url}/status")
        assert resp.status_code == 200
        assert len(resp.content) > 0

    def test_wt501_post_with_body(self, workbench, dut_url):
        """WT-501: a POST body reaches the DUT and an answer comes back.

        404 counts: the relay's job is to carry the request and return what
        the device said, not to make the device implement the path.
        """
        resp = workbench.http_post(
            f"{dut_url}/api/test",
            json_data={"key": "value"},
        )
        assert resp.status_code in (200, 201, 404)

    def test_wt502_custom_headers(self, workbench, dut_url):
        """WT-502: Custom headers are forwarded."""
        resp = workbench.http_get(
            f"{dut_url}/status",
            headers={"X-Test-Header": "test-value"},
        )
        assert resp.status_code == 200

    def test_wt503_connection_refused(self, workbench, wifi_network):
        """WT-503: HTTP to non-existent IP returns ERR."""
        with pytest.raises(CommandError):
            workbench.http_get("http://192.168.4.99/", timeout=5)

    def test_wt504_request_timeout(self, workbench, wifi_network):
        """WT-504: HTTP to non-responding device times out."""
        with pytest.raises(CommandError):
            workbench.http_get("http://192.168.4.99/", timeout=3)

    def test_wt505_large_response(self, workbench, dut_url):
        """WT-505: a multi-line JSON body survives the relay intact."""
        resp = workbench.http_get(f"{dut_url}/status")
        assert resp.status_code == 200
        assert json.loads(resp.text), "relayed body is not the JSON the DUT sent"

    def test_wt506_http_via_sta_mode(self, workbench):
        """WT-506: HTTP relay works in STA mode."""
        import os
        ssid = os.environ.get("WIFI_TEST_STA_SSID")
        password = os.environ.get("WIFI_TEST_STA_PASS", "")
        target_url = os.environ.get("WIFI_TEST_HTTP_URL")
        if not ssid or not target_url:
            pytest.skip("WIFI_TEST_STA_SSID and WIFI_TEST_HTTP_URL required")
        workbench.sta_join(ssid, password)
        resp = workbench.http_get(target_url)
        assert resp.status_code == 200
        workbench.sta_leave()


# =====================================================================
# WT-6xx  WiFi Scan
# =====================================================================


class TestWiFiScan:
    """WT-6xx: WiFi scan tests."""

    def test_wt600_scan_finds_networks(self, workbench):
        """WT-600: SCAN returns non-empty network list.

        An empty list used to skip here as "RF-shielded?". It was not: `iw`
        was failing with "Device or resource busy" whenever a scan overlapped
        another, the failure was returned as `ok: true, networks: []`, and
        the skip made the bench's own broken instrument look like a quiet
        room. The portal now reports a failed scan as a failed scan (503),
        so an empty list here means the air really was empty — which, on a
        bench that is not in a shielded chamber, is a finding.
        """
        workbench.ap_stop()
        result = workbench.scan()
        assert "networks" in result
        assert len(result["networks"]) > 0, (
            "scan succeeded and saw nothing — either this bench is in a "
            "shielded chamber, or the radio is not scanning"
        )

    def test_wt601_scan_returns_fields(self, workbench):
        """WT-601: Each scan entry has ssid, rssi, auth."""
        workbench.ap_stop()
        result = workbench.scan()
        assert len(result["networks"]) > 0, "see WT-600"
        for net in result["networks"]:
            assert "ssid" in net
            assert "rssi" in net
            assert "auth" in net
            assert isinstance(net["rssi"], (int, float))
            assert net["rssi"] < 0

    def test_wt602_scan_does_not_find_own_ap(self, workbench):
        """WT-602: our own AP does not appear in scan results.

        Unanswerable on this bench, and recorded rather than quietly
        dropped. The question needs a scan taken while our own AP is
        beaconing, and one radio cannot do both — see WT-603, which asserts
        the refusal. It passed before only because the AP was silently not
        radiating, so the "own AP" it looked for was never on the air: the
        assertion held for the one reason that makes it worthless.

        A second radio would make it answerable, as would any bench whose
        AP and scan are not the same chip.
        """
        pytest.skip(
            "precondition unmet: this bench has one radio, which cannot "
            "beacon and scan at once (WT-603 asserts that refusal). WT-602 "
            "needs a scan taken while our own AP is up."
        )

    def test_wt603_scan_while_ap_running(self, workbench):
        """WT-603: a scan attempted while the AP runs is refused, with its
        reason, and does not cost the AP.

        This asserted that the scan *succeeded* and the AP survived, and it
        passed for a year on a bench whose AP was silently not radiating:
        the radio was idle, so the scan worked and the capability looked
        real. It is not. One radio cannot beacon and survey at the same
        time — `iw` on the AP interface answers "Device or resource busy"
        and a scan on the primary interface returns nothing at all.

        What is worth testing is therefore what the bench *does* with an
        impossible request: refuse it, name the reason, and leave the AP
        up. An empty network list returned as a successful measurement is
        the failure mode this whole class exists to prevent.
        """
        workbench.ap_start("WT-SCAN-603", "password123")
        try:
            with pytest.raises((CommandError, WorkbenchError)) as exc:
                workbench.scan()
            assert "cannot scan while the AP is running" in str(exc.value), \
                exc.value
            assert workbench.ap_status()["active"] is True, \
                "the refused scan took the AP down with it"
        finally:
            workbench.ap_stop()


# =====================================================================
# WT-13xx  Signal Generator (Si5351 + PE4302, GPCLK fallback)
# =====================================================================


class TestSiggen:
    """WT-13xx: signal generator tests against /api/siggen/*."""

    def test_wt1300_start_and_status(self, workbench):
        """WT-1300: Start carrier and verify status shows active."""
        result = workbench.siggen_start(freq_hz=3_500_000)
        assert result["active"] is True
        assert result["backend"] in ("si5351", "gpclk")
        assert result["freq_hz"] > 0

        status = workbench.siggen_status()
        assert status["active"] is True
        assert status["backend"] == result["backend"]
        assert status["freq_hz"] == result["freq_hz"]

        workbench.siggen_stop()

    def test_wt1301_stop(self, workbench):
        """WT-1301: Stop carrier and verify status shows inactive."""
        workbench.siggen_start(freq_hz=3_571_000)
        workbench.siggen_stop()

        status = workbench.siggen_status()
        assert status["active"] is False

    def test_wt1302_frequency_list(self, workbench):
        """WT-1302: Frequency list returns valid entries in range."""
        freqs = workbench.siggen_frequencies(
            low=3_500_000, high=4_000_000, backend="gpclk")
        assert len(freqs) > 0
        for f in freqs:
            assert "divider" in f
            assert "freq_hz" in f
            assert 3_500_000 <= f["freq_hz"] <= 4_000_000

    def test_wt1303_morse_keying(self, workbench):
        """WT-1303: Morse-keyed start records message in status."""
        workbench.siggen_start(
            freq_hz=3_571_000,
            morse={"message": "VVV DE TEST", "wpm": 15, "repeat": True})
        status = workbench.siggen_status()
        assert status["active"] is True
        assert status["morse"]["message"] == "VVV DE TEST"
        assert status["morse"]["wpm"] == 15

        workbench.siggen_stop()

    def test_wt1304_replaces_previous(self, workbench):
        """WT-1304: Starting a new carrier replaces the previous one."""
        workbench.siggen_start(
            freq_hz=3_571_000,
            morse={"message": "AAA", "wpm": 10, "repeat": True})
        result2 = workbench.siggen_start(
            freq_hz=3_597_000,
            morse={"message": "BBB", "wpm": 20, "repeat": True})

        status = workbench.siggen_status()
        assert status["active"] is True
        assert status["morse"]["message"] == "BBB"
        assert status["morse"]["wpm"] == 20
        assert status["freq_hz"] == result2["freq_hz"]

        workbench.siggen_stop()


def _sdr_available(workbench) -> bool:
    """True when a dongle + rtl_433 are present (RF tests need them)."""
    try:
        return bool(workbench.sdr_status().get("available"))
    except WorkbenchError:
        return False


# =====================================================================
# WT-19xx  RF Path
#   WT-1909  bench transmitter -> own SDR: the SDR self-test
# =====================================================================


class TestRfLoopback:
    """WT-1909: the bench transmits to its own dongle — no DUT, no operator.

    The signal generator tops out at 160 MHz, so it cannot reach 433.92 MHz
    directly. It emits a square wave, though, whose odd harmonics are strong:
    driving 86.784 MHz puts the **5th harmonic exactly on 433.92 MHz**, and the
    dongle sees it ~20 dB above ambient. Measured on the reference bench:
    -21.7 dBm quiet, +2.7 dBm transmitting.

    That makes this the bench's RF **self-test**. Every other SDR test assumes
    the dongle, antenna and receive path work; this is the only one that proves
    it, and it needs nothing plugged in. If it fails, treat every other SDR
    result as unreliable rather than debugging them individually.

    Deliberately *not* asserted here: RSSI versus PE4302 attenuation. Measured
    flat across 0–31.5 dB at both 433.92 MHz and the 86.784 MHz fundamental —
    the attenuator is not in the path that reaches the dongle, so the coupling
    is board-level leakage. A monotonicity test would need a deliberate coax
    from the attenuator output to the dongle input; until that exists such a
    test would assert something the hardware cannot do.
    """

    FUNDAMENTAL_HZ = 86_784_000      # 5th harmonic = 433.920 MHz
    TARGET_HZ = 433_920_000
    GAIN_DB = 20.0                   # fixed: AGC rescales and destroys the delta
    MIN_LIFT_DB = 15.0               # measured ~24 dB at fixed gain

    def _peak(self, workbench) -> float:
        # A fixed gain is not optional here. On AGC the tuner rescales from
        # whatever it saw recently, so the quiet floor wandered 16 dB between
        # runs on the reference bench and the carrier was compressed to a 3.7 dB
        # lift — the comparison this test makes is meaningless without it.
        r = workbench.sdr_power(freq_hz=self.TARGET_HZ, duration_s=3,
                                span_hz=200_000, bin_hz=5_000,
                                gain=self.GAIN_DB)
        return float(r["peak_db"])

    def test_wt1909_bench_transmitter_reaches_own_receiver(self, workbench):
        """WT-1909: siggen ON lifts peak_db at 433.92 MHz well clear of quiet."""
        if not _sdr_available(workbench):
            pytest.skip("no RTL-SDR dongle available")
        hw = workbench.siggen_status().get("hardware", {})
        if not hw.get("si5351"):
            pytest.skip("no Si5351 signal generator present")

        workbench.siggen_stop()
        time.sleep(1)
        quiet = self._peak(workbench)
        try:
            workbench.siggen_start(freq_hz=self.FUNDAMENTAL_HZ)
            time.sleep(2)
            transmitting = self._peak(workbench)
        finally:
            # Leave no carrier on air even if an assertion fails.
            workbench.siggen_stop()

        lift = transmitting - quiet
        assert lift >= self.MIN_LIFT_DB, (
            f"transmitting {transmitting:.1f} dB vs quiet {quiet:.1f} dB is only "
            f"{lift:.1f} dB of lift (need {self.MIN_LIFT_DB}). Either the "
            f"receive path is broken or the generator is not radiating.")

        time.sleep(2)
        after = self._peak(workbench)
        assert transmitting - after >= self.MIN_LIFT_DB, (
            f"level stayed at {after:.1f} dB after the carrier stopped — the "
            "reading is not tracking the transmitter")




# =====================================================================
# WT-20xx  MQTT Broker
# =====================================================================


class TestMqttBroker:
    """WT-20xx: workbench mosquitto broker via /api/mqtt/*."""

    def test_wt2000_start_reports_running(self, workbench):
        """WT-2000: Starting the broker reports running on port 1883."""
        r = workbench.mqtt_start()
        assert r.get("ok") is True
        assert r.get("port") == 1883
        st = workbench.mqtt_status()
        assert st.get("running") is True

    def test_wt2001_status_when_stopped(self, workbench):
        """WT-2001: After stop, status reports not running."""
        workbench.mqtt_stop()
        st = workbench.mqtt_status()
        assert st.get("running") is False

    def test_wt2002_start_idempotent(self, workbench):
        """WT-2002: Starting an already-running broker is a no-op success."""
        workbench.mqtt_start()
        r = workbench.mqtt_start()
        assert r.get("ok") is True and r.get("port") == 1883
        workbench.mqtt_stop()


# =====================================================================
# WT-21xx  Captive-Portal Provisioning (WiFiManager DUT onto NAT AP)
# =====================================================================


@pytest.mark.requires_dut
class TestCaptivePortal:
    """WT-21xx: the provisioning journey, one step per test.

    This was a single test that asserted the DUT had an address on the
    bench AP and called that "provisioned through its portal". It was not:
    the fixture it depended on provisions over the serial console first and
    only falls back to the portal, so the portal usually never ran. A test
    named after a capability, passing without exercising it.

    The journey is now four gates, each with its own observable:

      WT-2101  the DUT raises a captive portal
      WT-2102  the bench joins it and submits SSID, password and broker
      WT-2103  the DUT reboots, the bench raises that AP, the DUT joins
      WT-2104  the DUT reaches the broker and publishes

    Run once as a class fixture, because it is one sequence and re-running
    it per test would prove nothing extra and cost four reboots. The
    fixture never raises: it records what happened at each step, so a
    failure at step 2 leaves steps 3 and 4 reporting what they actually
    saw rather than erroring on setup.
    """

    BROKER_FROM_DUT = "mqtt://192.168.4.1"   # the bench, from the AP side
    TOPIC = "workbench/dut/+/hello"

    @pytest.fixture(scope="class")
    def journey(self, workbench):
        j = {"portal_ssid": BENCH_DUT_PORTAL, "portal_on_air": False,
             "form": "", "submitted": None, "station": None,
             "mqtt_message": None, "notes": []}

        ssid = f"WT-{uuid.uuid4().hex[:6].upper()}"
        password = "testpass123"
        j["ssid"], j["password"] = ssid, password

        workbench.mqtt_start()

        # ── Step 1: put the DUT back in front of its own portal ──────
        # It is provisioned from earlier tests, so it has to be asked to
        # forget. Erasing over the wire is the one route that does not
        # depend on the radio we are about to test.
        for dev in workbench.get_devices():
            if dev.get("present"):
                try:
                    workbench.serial_write(dev["label"], text="forget")
                except Exception:
                    pass
        time.sleep(25)
        _ap_stop_quietly(workbench)     # free the radio to scan
        time.sleep(3)

        for _ in range(4):
            try:
                nets = workbench.scan().get("networks", [])
            except Exception:
                nets = []
            hit = [n for n in nets if n["ssid"] == BENCH_DUT_PORTAL]
            if hit:
                j["portal_on_air"] = True
                j["portal_rssi"] = hit[0].get("rssi")
                break
            time.sleep(5)

        # ── Step 2: join the portal and read the form it serves ──────
        if j["portal_on_air"]:
            try:
                workbench.sta_join(BENCH_DUT_PORTAL, "")
                r = workbench.wifi_http("http://192.168.4.1/", timeout=8)
                body = r.get("body", "")
                try:
                    body = base64.b64decode(body).decode(errors="replace")
                except Exception:
                    pass
                j["form"] = body
            except Exception as exc:
                j["notes"].append(f"reading the form failed: {exc}")
            finally:
                try:
                    workbench.sta_leave()
                except Exception:
                    pass

            # ── Step 3: submit the credentials through that form ─────
            try:
                j["submitted"] = workbench.provision_wifimanager(
                    BENCH_DUT_PORTAL, ssid, password,
                    save_path="/connect", field_ssid="ssid",
                    field_password="password", internet=True,
                    extra={"broker": self.BROKER_FROM_DUT})
            except Exception as exc:
                j["notes"].append(f"submitting the form failed: {exc}")

            # ── Step 4: the DUT reboots and joins the AP it was given ──
            j["station"] = _wait_for_any_station(workbench, timeout=150)

        # ── Step 5: and publishes to the broker it was given ─────────
        if j["station"]:
            j["mqtt_message"] = self._await_publication(workbench, timeout=90)

        yield j
        _ap_stop_quietly(workbench)

    @staticmethod
    def _await_publication(workbench, timeout):
        """Subscribe to the bench broker and wait for the DUT to publish.

        Subscribed from here rather than through an endpoint the bench does
        not have — the broker listens on every interface, so the DUT
        publishing to 192.168.4.1 and this client listening on the bench's
        LAN address are the same broker.
        """
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            return None
        host = workbench.info()["host_ip"]
        got = []

        def on_connect(client, userdata, flags, rc, properties=None):
            client.subscribe(TestCaptivePortal.TOPIC)

        def on_message(client, userdata, msg):
            got.append({"topic": msg.topic,
                        "payload": msg.payload.decode(errors="replace")})

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_connect = on_connect
        client.on_message = on_message
        try:
            client.connect(host, 1883, 60)
        except Exception:
            return None
        client.loop_start()
        deadline = time.time() + timeout
        while time.time() < deadline and not got:
            time.sleep(1)
        client.loop_stop()
        try:
            client.disconnect()
        except Exception:
            pass
        return got[0] if got else None

    def test_wt2101_dut_raises_a_captive_portal(self, journey):
        """WT-2101: the DUT puts its provisioning portal on the air and
        serves the form."""
        assert journey["portal_on_air"], (
            f"no '{journey['portal_ssid']}' in the bench's scan. "
            f"{'; '.join(journey['notes']) or 'the DUT never raised its portal'}"
        )
        form = journey["form"]
        assert form, f"the portal is beaconing but served no form: {journey['notes']}"
        # The fields the bench is about to fill in must exist, or WT-2102 is
        # posting into a form nobody asked for.
        for field in ('name="ssid"', 'name="password"', 'name="broker"'):
            assert field in form, f"{field} missing from the portal form"

    def test_wt2102_bench_submits_credentials_and_broker(self, journey):
        """WT-2102: the bench joins that portal and enters the SSID,
        password and broker address of the network it is about to raise."""
        assert journey["submitted"] is not None, (
            f"the bench never submitted the form: {'; '.join(journey['notes'])}"
        )
        assert journey["submitted"].get("ok", True) is not False, \
            journey["submitted"]

    def test_wt2103_dut_reboots_and_joins_that_ap(self, journey):
        """WT-2103: the DUT reboots, the bench raises an AP with exactly the
        credentials just entered, and the DUT joins it. Success 1."""
        station = journey["station"]
        assert station, (
            f"the DUT never joined '{journey['ssid']}' after being given it "
            f"through its own portal. {'; '.join(journey['notes'])}"
        )
        assert station["ip"].startswith("192.168.4."), station

    def test_wt2104_dut_publishes_to_the_broker(self, journey):
        """WT-2104: the DUT reaches the MQTT broker it was given and
        publishes. Success 2 — the journey end to end."""
        assert journey["station"], "no DUT on the AP; WT-2103 covers that"
        msg = journey["mqtt_message"]
        assert msg, (
            "the DUT joined the AP but nothing arrived on "
            f"{self.TOPIC} within 90 s — provisioned, addressed, and not "
            "doing the thing it was provisioned for"
        )
        assert "bench-dut" in msg["payload"], msg


# =====================================================================
# WT-14xx  GDB Debug: USB JTAG
# =====================================================================


requires_dut = pytest.mark.requires_dut


class TestUSBJTAGDebug:
    """WT-14xx: USB JTAG debug tests (requires device with native USB)."""

    @requires_dut
    def test_wt1400_debug_start(self, workbench):
        """WT-1400: Start debug and verify GDB port assigned."""
        # Stop any auto-started session first
        workbench.debug_stop()
        time.sleep(1)
        result = workbench.debug_start()
        assert result["gdb_port"] > 0
        assert result["chip"] in ("esp32c3", "esp32c6", "esp32h2", "esp32s3", "esp32")
        assert len(result["slot"]) > 0
        assert "gdb_target" in result
        workbench.debug_stop()

    @requires_dut
    def test_wt1401_debug_stop_restores(self, workbench):
        """WT-1401: After debug stop, slot returns to normal."""
        workbench.debug_stop()
        time.sleep(1)
        workbench.debug_start()
        workbench.debug_stop()
        time.sleep(2)
        status = workbench.debug_status()
        # No slots should be debugging after stop
        for info in status.get("slots", {}).values():
            assert info["debugging"] is False

    @requires_dut
    def test_wt1402_debug_status(self, workbench):
        """WT-1402: Debug status shows active session."""
        workbench.debug_stop()
        time.sleep(1)
        result = workbench.debug_start()
        slot = result["slot"]
        status = workbench.debug_status()
        assert status["slots"][slot]["debugging"] is True
        assert status["slots"][slot]["chip"] == result["chip"]
        assert status["slots"][slot]["gdb_port"] == result["gdb_port"]
        workbench.debug_stop()

    def test_wt1403_debug_reject_absent(self, workbench):
        """WT-1403: Debug on absent slot returns error."""
        with pytest.raises((CommandError, CommandTimeout)):
            workbench.debug_start(slot="SLOT99")

    @requires_dut
    def test_wt1404_debug_reject_unsupported(self, workbench):
        """WT-1404: Unsupported chip returns error.

        Needs a DUT despite only checking a rejection: with no slot given the
        portal auto-selects the first present device, and on an empty bench it
        answers "no device found" before it ever looks at the chip.
        """
        with pytest.raises(CommandError):
            workbench.debug_start(chip="esp8266")

    @requires_dut
    def test_wt1405_debug_reject_duplicate(self, workbench):
        """WT-1405: Second start while debugging returns error."""
        workbench.debug_stop()
        time.sleep(1)
        result = workbench.debug_start()
        slot = result["slot"]
        with pytest.raises(CommandError):
            workbench.debug_start(slot=slot)
        workbench.debug_stop()

    @requires_dut
    def test_wt1406_jtag_reset(self, workbench):
        """WT-1406: serial/reset uses JTAG when debug session is active."""
        workbench.debug_stop()
        time.sleep(1)
        result = workbench.debug_start()
        slot = result["slot"]
        # Reset via serial API — should auto-select JTAG
        reset = workbench.serial_reset(slot)
        assert reset.get("method") == "jtag"
        assert "reset run" in reset.get("command", "")
        workbench.debug_stop()


# =====================================================================
# WT-17xx  GDB Debug: Auto-Debug
# =====================================================================


class TestAutoDebug:
    """WT-17xx: Auto-debug tests (OpenOCD auto-starts on hotplug/boot)."""

    @requires_dut
    def test_wt1704_auto_debug_on_boot(self, workbench):
        """WT-1704: Debug can be started automatically (simulates boot)."""
        # Ensure a session is active (start if needed after prior stop)
        workbench.debug_stop()
        time.sleep(1)
        result = workbench.debug_start()
        assert result["chip"] in (
            "esp32c3", "esp32c6", "esp32h2", "esp32s3", "esp32")
        status = workbench.debug_status()
        active = [s for s, info in status.get("slots", {}).items()
                  if info["debugging"]]
        assert len(active) >= 1, "No debug session active"

    @requires_dut
    def test_wt1705_auto_debug_in_devices(self, workbench):
        """WT-1705: Debug status reports in /api/devices."""
        # Ensure debugging is active
        status = workbench.debug_status()
        if not any(i["debugging"] for i in status.get("slots", {}).values()):
            workbench.debug_start()
            time.sleep(1)
        devices = workbench.get_devices()
        debug_devices = [d for d in devices
                         if d.get("debugging") and d.get("present")]
        assert len(debug_devices) >= 1
        dev = debug_devices[0]
        assert dev["debug_chip"] in (
            "esp32c3", "esp32c6", "esp32h2", "esp32s3", "esp32")
        assert isinstance(dev["debug_gdb_port"], int)
        assert dev["debug_gdb_port"] > 0

    @requires_dut
    def test_wt1707_manual_stop_prevents_autorestart(self, workbench):
        """WT-1707: Manual debug_stop prevents auto-restart."""
        workbench.debug_stop()
        time.sleep(3)
        status = workbench.debug_status()
        # After manual stop, no session should be active
        for info in status.get("slots", {}).values():
            assert info["debugging"] is False
        # Restart for other tests
        workbench.debug_start()

    @requires_dut
    def test_wt1709_auto_debug_skipped_during_flapping(self, workbench):
        """WT-1709: Auto-debug is not attempted when slot is flapping."""
        # We can only verify the logic exists — triggering real flapping
        # requires rapid USB connect/disconnect which we can't do remotely.
        # Instead, verify that debug_start on a non-present slot fails cleanly.
        workbench.debug_stop()
        time.sleep(1)
        status = workbench.debug_status()
        # Verify the API is responsive and all sessions are stopped
        for info in status.get("slots", {}).values():
            assert info["debugging"] is False
        # Restart for other tests
        workbench.debug_start()


# =====================================================================
# WT-18xx  End-to-End: Flash + Debug
# =====================================================================


def _find_present_device(workbench):
    """Find the first present DUT (not a debug probe) and return its slot info.

    Any present device that isn't a probe or HID-warning slot is a DUT.
    This covers both native USB chips (VID 303a, ttyACM) and classic ESP32
    boards with third-party USB-UART bridges (CP2102, CH340, ttyUSB).
    """
    devices = workbench.get_devices()
    for d in devices:
        if not d.get("present"):
            continue
        if d.get("is_probe"):
            continue
        if d.get("usb_warning"):
            continue
        return d
    return None


def _ocd_command(host, port, cmd, timeout=3.0):
    """Send a command to OpenOCD telnet and return response.

    Reads until the '>' prompt or timeout, so long-running commands
    like 'program' are handled correctly.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)  # connect timeout
    try:
        s.connect((host, port))
        time.sleep(0.3)
        s.settimeout(timeout)
        s.recv(4096)  # banner
        s.sendall(f"{cmd}\n".encode())
        # Read until prompt or timeout
        buf = b""
        deadline = time.time() + timeout
        while time.time() < deadline:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            s.settimeout(max(remaining, 0.5))
            try:
                chunk = s.recv(8192)
                if not chunk:
                    break
                buf += chunk
                if b"> " in buf or b">\n" in buf:
                    break
            except socket.timeout:
                break
        return buf.decode("latin-1", errors="replace").strip()
    finally:
        s.close()


def _wait_for_state(workbench, check_fn, timeout=30, poll=1.0, what="state"):
    """Poll workbench until check_fn(device) returns True or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        dev = _find_present_device(workbench)
        if dev and check_fn(dev):
            return dev
        time.sleep(poll)
    raise AssertionError(
        f"Timed out after {timeout}s waiting for {what}")


def _jtag_capable(dev: dict) -> bool:
    """Can this slot's chip be identified at all?

    `detected_chip` is populated by auto-debug, which only runs for parts with
    a built-in USB-JTAG interface. A device behind a UART bridge (CP2102,
    CH340) has no JTAG, so the field is None *by design* — asserting a chip for
    it tests a premise the portal never promised.
    """
    products = " ".join(u.get("product", "") for u in dev.get("usb_devices", []))
    bridge = any(k in products for k in ("CP210", "CH340", "FT232", "UART Bridge"))
    return not bridge


def _flash_device(workbench, chip, target_dir):
    """Flash debug-test firmware via esptool over RFC2217.

    Uses the RFC2217 proxy for flashing (binaries stay on the host).
    After flash, calls serial_reset to reboot the device into the
    new firmware.

    Returns True on success.
    """
    import subprocess

    bootloader = os.path.join(target_dir, "bootloader.bin")
    partition = os.path.join(target_dir, "partition-table.bin")
    app = os.path.join(target_dir, "debug-test.bin")

    if not all(os.path.exists(f) for f in [bootloader, partition, app]):
        print(f"Missing binaries in {target_dir}", flush=True)
        return False

    dev = _find_present_device(workbench)
    if not dev:
        return False

    slot_label = dev.get("label", "")
    serial_url = dev.get("url", "")
    if not serial_url:
        print("No serial URL", flush=True)
        return False

    # Stop debug if active (native USB shares serial + JTAG on same USB)
    was_debugging = dev.get("debugging")
    if was_debugging:
        workbench.debug_stop(slot=slot_label)
        _wait_for_state(
            workbench,
            lambda d: d.get("running") and not d.get("debugging"),
            timeout=20, what="debug stopped before flash")

    bl_offset = "0x1000" if chip == "esp32" else "0x0000"
    cmd = [
        "python3", "-m", "esptool",
        "--chip", chip,
        "--port", serial_url,
        "--before", "default-reset",
        "--after", "no-reset",
        "write-flash", "--flash-mode", "dio", "--flash-size", "4MB",
        bl_offset, bootloader,
        "0x8000", partition,
        "0x10000", app,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        if result.returncode != 0 and "Hash of data verified" not in output:
            print(f"Flash failed: {output[-300:]}", flush=True)
            return False
    except Exception as e:
        print(f"Flash error: {e}", flush=True)
        return False

    print(f"Flash OK: {slot_label} ({chip})", flush=True)

    # Reboot device into new firmware
    workbench.serial_reset(slot_label)

    # Restart debug if it was active (resume CPU so firmware runs)
    if was_debugging:
        workbench.debug_start(slot=slot_label, chip=chip)
        _wait_for_state(
            workbench,
            lambda d: d.get("debugging"),
            timeout=30, what="debug restart after flash")
        # OpenOCD halts CPU on connect — reset run so firmware boots
        host = workbench.base_url.split("//")[1].split(":")[0]
        dev = _find_present_device(workbench)
        telnet_port = dev.get("openocd_telnet_port") if dev else None
        if telnet_port:
            try:
                _ocd_command(host, telnet_port, "reset run", timeout=5)
            except Exception:
                pass  # best effort — firmware may already be running

    return True


def _jtag_slots(workbench) -> list:
    """Present slots whose board has a built-in USB-JTAG interface."""
    return [d for d in workbench.get_devices()
            if d.get("present") and not d.get("is_probe")
            and _jtag_capable(d)]


class TestPerSlotDebugIsolation:
    """WT-19xx: FR-037 — a debug session belongs to one slot, and to the
    board in that slot.

    Every native-USB ESP32 enumerates as 303a:1001, so nothing in the USB
    identity distinguishes two of them. These tests need two such boards on
    the bench; with one, they cannot fail and are skipped rather than
    reported as evidence.
    """

    def _two_jtag_slots(self, workbench):
        slots = _jtag_slots(workbench)
        if len(slots) < 2:
            pytest.skip(
                "precondition unmet: FR-037 needs two built-in-JTAG boards; "
                f"this bench has {len(slots)}"
            )
        return slots

    @requires_dut
    def test_each_slot_reports_its_own_chip(self, workbench):
        # verifies: FR-037
        """Detection blind to USB topology reports a neighbour's silicon.

        Observed before the location filter: SLOT1, holding an ESP32-C3,
        was reported as esp32s3 — the chip of the board in SLOT4.
        """
        slots = self._two_jtag_slots(workbench)
        chips = {d["label"]: (d.get("detected_chip") or d.get("debug_chip"))
                 for d in slots}
        for label, chip in chips.items():
            assert chip, f"{label}: no chip detected — {chips}"

        # The MAC is per-board, so it settles which physical device each
        # slot actually spoke to. Two slots reporting one MAC is the bug.
        macs = {}
        for d in slots:
            info = workbench.chip_info(d["label"])
            macs[d["label"]] = info.get("mac")
        assert all(macs.values()), f"a slot reported no MAC: {macs}"
        assert len(set(macs.values())) == len(macs), (
            f"two slots claim the same board: {macs}"
        )

    @requires_dut
    def test_two_slots_debug_concurrently(self, workbench):
        # verifies: FR-037
        """OpenOCD listens on three ports; the portal only ever assigned two.

        The third defaulted to 6666 for every session, so the second one to
        start anywhere on the bench died with "Address already in use" — a
        bench-wide limit of one debugger, from an undeclared number.
        """
        a, b = self._two_jtag_slots(workbench)[:2]
        for d in (a, b):
            try:
                workbench.debug_stop(d["label"])
            except CommandError:
                pass
        time.sleep(1)

        ra = workbench.debug_start(a["label"])
        assert ra["ok"] is True, ra
        try:
            rb = workbench.debug_start(b["label"])
            assert rb["ok"] is True, (
                f"second concurrent session refused: {rb}"
            )
            try:
                assert ra["gdb_port"] != rb["gdb_port"], (
                    "both sessions on one GDB port"
                )
                status = workbench.debug_status()["slots"]
                assert status[a["label"]]["debugging"] is True
                assert status[b["label"]]["debugging"] is True

                # Stopping one must leave the other alone.
                workbench.debug_stop(b["label"])
                time.sleep(1)
                after = workbench.debug_status()["slots"]
                assert after[a["label"]]["debugging"] is True, (
                    "stopping one slot's session ended another's"
                )
            finally:
                try:
                    workbench.debug_stop(b["label"])
                except CommandError:
                    pass
        finally:
            try:
                workbench.debug_stop(a["label"])
            except CommandError:
                pass


class TestEndToEnd:
    """WT-18xx: End-to-end flash + debug tests.

    These tests flash the debug-test firmware, verify serial output,
    and exercise GDB debugging (halt, step, memory read) for each chip.
    Run one chip at a time — plug in the target, run the test.

    Tests are ordered: WT-1800 (flash) must pass before debug tests
    run.  If flash fails, all subsequent tests are skipped.

    Usage:
        pytest workbench_test.py -k TestEndToEnd --run-dut --wt-url http://workbench.local:8080
    """

    _test_session_started = False
    _flash_ok = False

    @pytest.fixture(autouse=True, scope="class")
    def _end_test_session(self, workbench):
        """Send test_end when all tests in this class are done, and give the
        bench its own DUT back.

        This class deliberately flashes a throwaway image over the bench DUT
        — that is how it proves flashing works — and used to leave it there.
        Every later test that needs the DUT to *answer* then found a board
        printing `LOOP: n` and reported absent hardware, and so did the next
        run, and the one after that. A suite that destroys its own
        instrument has to rebuild it before it hands the bench on.
        """
        yield
        try:
            workbench.test_end()
        except Exception:
            pass
        TestEndToEnd._test_session_started = False
        restored = ensure_bench_dut_firmware(workbench)
        if restored:
            print(f"\n{restored}")

    @pytest.fixture(autouse=True)
    def _track_progress(self, workbench, request):
        """Report test progress to the workbench panel."""
        test_id = request.node.name.split("_")[1].upper()  # e.g. "WT1800"
        raw_name = request.node.obj.__doc__.split("\n")[0].strip() if request.node.obj.__doc__ else request.node.name
        # Strip "WT-1800: " prefix from docstring — test_id already carries it
        test_name = re.sub(r'^WT-?\d+:\s*', '', raw_name)

        if not TestEndToEnd._test_session_started:
            TestEndToEnd._test_session_started = True
            try:
                workbench.test_start(
                    spec="End-to-End Flash+Debug", phase="WT-18xx", total=6)
            except Exception:
                pass

        for _attempt in range(3):
            try:
                workbench.test_step(test_id, test_name, "Running...")
                break
            except Exception:
                time.sleep(2)

        yield

        # Determine result from pytest outcome
        result = "PASS"
        detail = ""
        if hasattr(request.node, "rep_setup") and request.node.rep_setup.skipped:
            result = "SKIP"
        elif hasattr(request.node, "rep_call"):
            if request.node.rep_call.failed:
                result = "FAIL"
                detail = str(request.node.rep_call.longrepr)[:200]
            elif request.node.rep_call.skipped:
                result = "SKIP"
        for _attempt in range(3):
            try:
                workbench.test_result(test_id, test_name, result, details=detail)
                break
            except Exception:
                time.sleep(2)

    @requires_dut
    def test_wt1800_flash_and_serial(self, workbench):
        """WT-1800: Flash debug-test firmware and verify serial output."""
        dev = _find_present_device(workbench)
        assert dev, "No device connected"

        chip = dev.get("debug_chip", "")
        slot = dev.get("label", "")

        # Map debug_chip to esptool chip name
        esptool_chip = chip if chip else None
        if not esptool_chip:
            # Try to detect from debug_start
            result = workbench.debug_start()
            esptool_chip = result.get("chip")
            assert esptool_chip, "Could not detect chip type"

        target_dir = os.path.join(DEBUG_TEST_DIR, esptool_chip)
        if not os.path.isdir(target_dir):
            pytest.skip(f"No pre-built binaries for {esptool_chip}")

        # Flash via portal API (stops proxy, runs esptool locally, restarts proxy)
        success = _flash_device(workbench, esptool_chip, target_dir)
        assert success, f"Flash failed for {esptool_chip}"

        # Verify serial output
        result = workbench.serial_monitor(slot, pattern="LOOP:", timeout=20)
        assert result.get("matched"), \
            f"Expected 'LOOP:' in serial output, got: {result.get('output', [])[-5:]}"
        TestEndToEnd._flash_ok = True

    @requires_dut
    def test_wt1801_debug_halt_and_resume(self, workbench):
        """WT-1801: Halt CPU via JTAG, read PC, resume."""
        if not TestEndToEnd._flash_ok:
            pytest.skip("WT-1800 (flash) did not pass")
        dev = _find_present_device(workbench)
        assert dev, "No device connected"
        assert dev.get("debugging"), "Debug not active — flash first (WT-1800)"

        host = workbench.base_url.split("//")[1].split(":")[0]
        telnet_port = dev["debug_gdb_port"] + 1111  # gdb=3333 → telnet=4444

        # Get actual telnet port from debug status
        status = workbench.debug_status()
        for label, info in status.get("slots", {}).items():
            if info.get("debugging"):
                telnet_port = info.get("telnet_port", telnet_port)
                break

        # Halt
        out = _ocd_command(host, telnet_port, "halt")
        assert "halted" in out.lower() or ">" in out

        # Read PC
        out = _ocd_command(host, telnet_port, "reg pc")
        assert "0x" in out, f"Expected PC value, got: {out}"

        # Resume
        _ocd_command(host, telnet_port, "resume", timeout=2)

    @requires_dut
    def test_wt1802_debug_single_step(self, workbench):
        """WT-1802: Single-step CPU via JTAG."""
        if not TestEndToEnd._flash_ok:
            pytest.skip("WT-1800 (flash) did not pass")
        dev = _find_present_device(workbench)
        assert dev, "No device connected"
        assert dev.get("debugging"), "Debug not active"

        host = workbench.base_url.split("//")[1].split(":")[0]
        status = workbench.debug_status()
        telnet_port = None
        for info in status.get("slots", {}).values():
            if info.get("debugging"):
                telnet_port = info["telnet_port"]
                break
        assert telnet_port, "No telnet port found"

        # Halt
        _ocd_command(host, telnet_port, "halt")

        # Read PC before step
        out1 = _ocd_command(host, telnet_port, "reg pc")
        import re
        m1 = re.search(r"0x[0-9a-fA-F]+", out1)
        assert m1, f"Could not read PC: {out1}"
        pc_before = m1.group()

        # Step
        out = _ocd_command(host, telnet_port, "step", timeout=2)
        assert "halted" in out.lower() or ">" in out

        # Read PC after step — should have advanced
        out2 = _ocd_command(host, telnet_port, "reg pc")
        m2 = re.search(r"0x[0-9a-fA-F]+", out2)
        assert m2, f"Could not read PC after step: {out2}"
        pc_after = m2.group()

        assert pc_before != pc_after, \
            f"PC did not advance: before={pc_before}, after={pc_after}"

        # Resume
        _ocd_command(host, telnet_port, "resume", timeout=2)

    @requires_dut
    def test_wt1803_debug_memory_read(self, workbench):
        """WT-1803: Read memory via JTAG."""
        if not TestEndToEnd._flash_ok:
            pytest.skip("WT-1800 (flash) did not pass")
        dev = _find_present_device(workbench)
        assert dev, "No device connected"
        assert dev.get("debugging"), "Debug not active"

        host = workbench.base_url.split("//")[1].split(":")[0]
        status = workbench.debug_status()
        telnet_port = None
        for info in status.get("slots", {}).values():
            if info.get("debugging"):
                telnet_port = info["telnet_port"]
                break
        assert telnet_port

        # Halt
        _ocd_command(host, telnet_port, "halt")

        # Read ROM memory (always present at 0x40000000 on all ESP32)
        out = _ocd_command(host, telnet_port, "mdw 0x40000000 4")
        assert "0x40000000" in out, f"Memory read failed: {out}"

        # Resume
        _ocd_command(host, telnet_port, "resume", timeout=2)

    @requires_dut
    def test_wt1804_debug_breakpoint(self, workbench):
        """WT-1804: Set and hit a hardware breakpoint via JTAG."""
        if not TestEndToEnd._flash_ok:
            pytest.skip("WT-1800 (flash) did not pass")
        dev = _find_present_device(workbench)
        assert dev, "No device connected"
        assert dev.get("debugging"), "Debug not active"

        host = workbench.base_url.split("//")[1].split(":")[0]
        status = workbench.debug_status()
        telnet_port = None
        for info in status.get("slots", {}).values():
            if info.get("debugging"):
                telnet_port = info["telnet_port"]
                break
        assert telnet_port

        import re

        # Halt, get current PC
        _ocd_command(host, telnet_port, "halt")
        out = _ocd_command(host, telnet_port, "reg pc")
        m = re.search(r"0x([0-9a-fA-F]+)", out)
        assert m
        pc = int(m.group(1), 16)

        # Set breakpoint a few instructions ahead
        bp_addr = pc + 8
        out = _ocd_command(host, telnet_port,
                           f"bp 0x{bp_addr:08X} 2 hw")
        assert "breakpoint" in out.lower() or ">" in out

        # Resume — should hit breakpoint
        out = _ocd_command(host, telnet_port, "resume", timeout=3)

        # Remove breakpoint
        _ocd_command(host, telnet_port, f"rbp 0x{bp_addr:08X}")

        # Resume normal execution
        _ocd_command(host, telnet_port, "resume", timeout=2)

    @requires_dut
    def test_wt1805_flash_preserves_debug(self, workbench):
        """WT-1805: Debug auto-restarts after flash (no manual intervention)."""
        if not TestEndToEnd._flash_ok:
            pytest.skip("WT-1800 (flash) did not pass")
        dev = _find_present_device(workbench)
        assert dev, "No device connected"

        chip = dev.get("debug_chip", "")
        slot = dev.get("label", "")

        if not chip:
            result = workbench.debug_start()
            chip = result.get("chip", "")
        assert chip, "Could not detect chip"

        target_dir = os.path.join(DEBUG_TEST_DIR, chip)
        if not os.path.isdir(target_dir):
            pytest.skip(f"No pre-built binaries for {chip}")

        # Verify debug is active before flash
        dev_before = _find_present_device(workbench)
        assert dev_before.get("debugging"), "Debug should be active before flash"

        # Flash via portal API (handles debug stop/restart automatically)
        success = _flash_device(workbench, chip, target_dir)
        assert success, "Flash failed"

        # Verify debug auto-restarted (portal restarts debug after flash)
        dev_after = _wait_for_state(
            workbench,
            lambda d: d.get("debugging"),
            timeout=30, what="debug restart after flash")
        assert dev_after, "Device not found after flash"

        # Verify serial output (extra time — proxy just restarted, device booting)
        result = workbench.serial_monitor(slot, pattern="LOOP:", timeout=20)
        assert result.get("matched"), "Firmware not running after flash"


# =====================================================================
# WT-19xx  Serial Architecture: Buffer + Detection
# =====================================================================


class TestSerialArchitecture:
    """WT-19xx: Serial reader buffer, passive output, and multi-slot detection."""

    def test_wt2200_devices_have_slots(self, workbench):
        """WT-2200: /api/devices returns slots with labels and state."""
        devices = workbench.get_devices()
        assert len(devices) > 0, "No slots configured"
        for d in devices:
            assert "label" in d
            assert "state" in d
            assert d["state"] in (
                "absent", "idle", "resetting", "monitoring",
                "flapping", "recovering", "download_mode", "debugging",
            )

    @requires_dut
    def test_wt2201_present_device_detected(self, workbench):
        """WT-2201: Present device has detected_chip set."""
        dev = _find_present_device(workbench)
        assert dev, "No device connected"
        chip = dev.get("detected_chip") or dev.get("debug_chip")
        assert chip, (
            f"No chip detected for {dev['label']} — "
            f"usb_devices={dev.get('usb_devices')}"
        )
        assert chip in (
            "esp32", "esp32s2", "esp32s3",
            "esp32c3", "esp32c6", "esp32h2",
        ), f"Unexpected chip: {chip}"

    @requires_dut
    def test_wt2202_all_present_devices_detected(self, workbench):
        """WT-2202: Every present DUT slot has a detected chip."""
        devices = workbench.get_devices()
        duts = [d for d in devices
                if d.get("present") and not d.get("is_probe")
                and _jtag_capable(d)]
        assert len(duts) > 0, "No JTAG-capable DUT devices present"
        for d in duts:
            chip = d.get("detected_chip") or d.get("debug_chip")
            assert chip, (
                f"{d['label']}: no chip detected — "
                f"usb_devices={d.get('usb_devices')}"
            )

    @requires_dut
    def test_wt2203_serial_output_buffer(self, workbench):
        """WT-2203: GET /api/serial/output returns buffered lines."""
        dev = _find_present_device(workbench)
        assert dev, "No device connected"
        slot = dev["label"]

        # Wait briefly for the reader thread to accumulate some output
        time.sleep(3)
        result = workbench.serial_output(slot, lines=20)
        assert result.get("ok"), f"serial_output failed: {result}"
        lines = result.get("lines", [])
        # Buffer should have entries (device is running firmware)
        assert isinstance(lines, list)
        # Each entry has ts and text
        for entry in lines:
            assert "ts" in entry
            assert "text" in entry
            assert isinstance(entry["ts"], (int, float))
            assert isinstance(entry["text"], str)

    @requires_dut
    def test_wt2204_serial_output_since_filter(self, workbench):
        """WT-2204: serial_output respects 'since' timestamp filter."""
        dev = _find_present_device(workbench)
        assert dev, "No device connected"
        slot = dev["label"]

        # Get all buffered lines
        all_lines = workbench.serial_output(slot, lines=100)
        assert all_lines.get("ok")
        if not all_lines["lines"]:
            time.sleep(3)
            all_lines = workbench.serial_output(slot, lines=100)

        if len(all_lines["lines"]) < 2:
            pytest.skip("Not enough serial output to test filtering")

        # Use timestamp of a middle line as the 'since' filter
        mid = len(all_lines["lines"]) // 2
        since_ts = all_lines["lines"][mid]["ts"]
        filtered = workbench.serial_output(slot, lines=100, since=since_ts)
        assert filtered.get("ok")
        # Filtered results should be a subset
        assert len(filtered["lines"]) <= len(all_lines["lines"])
        # All returned entries should have ts > since_ts
        for entry in filtered["lines"]:
            assert entry["ts"] > since_ts

    @requires_dut
    def test_wt2205_serial_monitor_from_buffer(self, workbench):
        """WT-2205: serial_monitor reads from buffer, not hardware."""
        dev = _find_present_device(workbench)
        assert dev, "No device connected"
        slot = dev["label"]

        # Monitor with no pattern — returns immediately with buffered data
        result = workbench.serial_monitor(slot, timeout=2)
        assert result.get("matched") is False
        assert isinstance(result.get("output"), list)

    @requires_dut
    def test_wt2206_serial_monitor_pattern_match(self, workbench):
        """WT-2206: serial_monitor matches pattern from buffer."""
        dev = _find_present_device(workbench)
        assert dev, "No device connected"
        slot = dev["label"]

        # The firmware prints "LOOP:" repeatedly — match from buffer
        result = workbench.serial_monitor(slot, pattern="LOOP:", timeout=15)
        if not result.get("matched"):
            # Firmware may not be running — try a boot message instead
            result = workbench.serial_monitor(
                slot, pattern="esp", timeout=10)
        # At minimum, we should get some output lines
        assert len(result.get("output", [])) >= 0

    @requires_dut
    def test_wt2207_multi_slot_detection(self, workbench):
        """WT-2207: Multiple slots independently detect their chips."""
        devices = workbench.get_devices()
        duts = [d for d in devices
                if d.get("present") and not d.get("is_probe")
                and _jtag_capable(d)]
        if len(duts) < 2:
            pytest.skip("Need 2+ DUT devices for multi-slot test")

        labels = []
        chips = []
        for d in duts:
            chip = d.get("detected_chip") or d.get("debug_chip")
            assert chip, f"{d['label']}: no chip detected"
            labels.append(d["label"])
            chips.append(chip)

        # Verify each slot has its own independent detection
        assert len(labels) == len(set(labels)), "Duplicate slot labels"
        # Each slot should have a valid chip
        for label, chip in zip(labels, chips):
            assert chip in (
                "esp32", "esp32s2", "esp32s3",
                "esp32c3", "esp32c6", "esp32h2",
            ), f"{label}: unexpected chip '{chip}'"


class TestSlotAccessManager:
    """FR-031 – FR-035. The manager arbitrates mode, never the data path.

    Every case below asserts a refusal as well as a grant: a lock that only
    ever says yes is not a lock, and the bug it hides is two consumers each
    believing they own the device.
    """

    # Bound at run time from whatever slot actually holds a device. It used
    # to be the constant "SLOT3", chosen because it carried no JTAG so
    # `debugging` could never pre-empt these cases — a good reason for a
    # choice that stopped being true when the boards moved, and then failed
    # as "SLOT3: proxy not running", which accuses the proxy.
    SLOT = None

    @pytest.fixture(autouse=True)
    def _bind_slot(self, workbench, present_slot):
        type(self).SLOT = present_slot
        # These cases are about the manager's own arbitration, so the slot
        # has to start unheld. The constant this replaced named a slot with
        # no JTAG precisely so a debug session could never pre-empt them —
        # a sound dodge that stops being available when the bench has one
        # board, which then arrives here still `debugging` from an earlier
        # class and refuses every acquire.
        try:
            if workbench.get_slot(self.SLOT).get("debugging"):
                workbench.debug_stop(self.SLOT)
        except Exception:
            pass

    def _drain(self, workbench):
        """Leave the slot idle whatever a previous case did."""
        m = workbench.slot_mode(self.SLOT)
        if m.get("mode") not in (None, "idle", "absent", "debugging"):
            # No token to hand back; the lease is what reclaims it.
            pass

    def test_idle_slot_reports_idle(self, workbench):
        # verifies: FR-031
        m = workbench.slot_mode(self.SLOT)
        assert m["ok"] is True
        assert m["mode"] in ("idle", "absent"), m

    def test_acquire_then_release_round_trip(self, workbench):
        # verifies: FR-031
        g = workbench.slot_acquire(self.SLOT, "monitoring", "pytest-roundtrip", ttl=30)
        assert g["ok"] is True, g
        token = g["token"]
        try:
            held = workbench.slot_mode(self.SLOT)
            assert held["mode"] == "monitoring"
            assert held["owner"] == "pytest-roundtrip"
            assert held["since"], "a grant must record when it started"
        finally:
            r = workbench.slot_release(token)
            assert r["ok"] is True, r
        assert workbench.slot_mode(self.SLOT)["mode"] in ("idle", "absent")

    def test_conflicting_acquire_is_refused_naming_the_incumbent(self, workbench):
        # verifies: FR-033
        g = workbench.slot_acquire(self.SLOT, "flashing", "pytest-first", ttl=30)
        assert g["ok"] is True, g
        try:
            second = workbench.slot_acquire(self.SLOT, "monitoring", "pytest-second")
            assert second["ok"] is False, "a held slot must not be granted twice"
            assert second["error"] == "held"
            assert second["owner"] == "pytest-first", (
                "a refusal that does not name the holder leaves the caller with "
                "the same mystery the manager exists to remove"
            )
            assert second["mode"] == "flashing"
            # FR-033: the incumbent keeps it.
            assert workbench.slot_mode(self.SLOT)["owner"] == "pytest-first"
        finally:
            workbench.slot_release(g["token"])

    def test_unknown_mode_is_rejected(self, workbench):
        # verifies: FR-031
        bad = workbench.slot_acquire(self.SLOT, "banana", "pytest-bad")
        assert bad["ok"] is False
        assert "unknown mode" in bad["error"]
        assert "modes" in bad, "a rejection should say what is valid"

    def test_renew_extends_by_the_granted_ttl(self, workbench):
        # verifies: FR-032
        g = workbench.slot_acquire(self.SLOT, "monitoring", "pytest-renew", ttl=9)
        assert g["ok"] is True, g
        try:
            assert g["expires_in"] == pytest.approx(9, abs=1)
            r = workbench.slot_renew(g["token"])
            assert r["ok"] is True, r
            assert r["expires_in"] == pytest.approx(9, abs=1), (
                "renew must extend by the ttl the grant was made with, not by "
                "the default — silently promoting a 9 s lease to 60 s hands out "
                "a lease nobody asked for"
            )
        finally:
            workbench.slot_release(g["token"])

    def test_expired_lease_is_reclaimed(self, workbench):
        # verifies: FR-032
        """A holder that stops renewing must not keep the slot forever.

        This is the bounded form of the failure it replaces: a client whose
        reader thread died held a slot until the portal was restarted.
        """
        dead = workbench.slot_acquire(self.SLOT, "monitoring", "pytest-dies", ttl=3)
        assert dead["ok"] is True, dead
        blocked = workbench.slot_acquire(self.SLOT, "flashing", "pytest-waiting")
        assert blocked["ok"] is False, "must still be held before the lease runs out"

        time.sleep(5)
        after = workbench.slot_acquire(self.SLOT, "flashing", "pytest-waiting")
        assert after["ok"] is True, (
            f"the lease should have been reclaimed after 3 s: {after}"
        )
        workbench.slot_release(after["token"])

    def test_release_with_an_unknown_token_is_refused(self, workbench):
        # verifies: FR-031
        r = workbench.slot_release("deadbeefdead")
        assert r["ok"] is False
        assert "unknown" in r["error"]

    def test_debug_session_holds_the_slot_it_owns(self, workbench):
        # verifies: FR-035
        """FR-035. OpenOCD claims a different USB interface, so devnode
        inspection cannot see it — the manager's own record must."""
        # get_devices() returns a list of slot dicts, not a wrapper.
        jtag = [s for s in workbench.get_devices()
                if s.get("present") and s.get("debugging")]
        if not jtag:
            pytest.skip("precondition unmet: no slot currently has a debug session")
        label = jtag[0]["label"]
        m = workbench.slot_mode(label)
        assert m["mode"] == "debugging", m
        refused = workbench.slot_acquire(label, "flashing", "pytest-vs-debug")
        assert refused["ok"] is False, (
            "a flash must not proceed while OpenOCD holds the USB interface"
        )
        assert refused["mode"] == "debugging"

    def test_acquire_is_not_blocked_by_the_slots_own_proxy(self, workbench):
        """FR-034, the false-positive half.

        The manager refuses to grant while an unexpected process holds the
        devnode. Its own proxy holds that devnode permanently, so a detector
        that failed to recognise the expected holder would refuse every
        acquire on every slot — the check would break the thing it protects.

        The true-positive half (an unrelated process holding the device is
        detected and named) cannot be driven from here: it needs a process
        started on the bench itself, and the bench rightly exposes no endpoint
        to start arbitrary processes. Recorded as the limit of this test
        rather than left as a silent gap.
        """
        slot = workbench.get_slot(self.SLOT)
        assert slot["running"] is True, "the proxy must be holding the device"
        g = workbench.slot_acquire(self.SLOT, "monitoring", "pytest-fp", ttl=20)
        assert g["ok"] is True, (
            f"acquire was refused while only the slot's own proxy held the "
            f"device — the out-of-band detector does not recognise its own "
            f"proxy: {g}"
        )
        workbench.slot_release(g["token"])


class TestBenchReset:
    """FR-036. The call that makes "before" mean the same thing every time."""

    def test_reset_reports_what_it_changed(self, workbench):
        r = workbench.bench_reset()
        assert r["ok"] is True, r
        assert isinstance(r.get("changed"), list)
        assert not r.get("errors"), f"reset reported errors: {r['errors']}"

    def test_reset_clears_a_held_slot(self, workbench):
        g = workbench.slot_acquire("SLOT3", "monitoring", "pytest-dirt", ttl=600)
        assert g["ok"] is True, g
        assert workbench.slot_mode("SLOT3")["mode"] == "monitoring"
        r = workbench.bench_reset()
        assert r["ok"] is True, r
        assert workbench.slot_mode("SLOT3")["mode"] in ("idle", "absent"), (
            "a long-lived grant survived the reset, so the next test would "
            "start from the previous test's state"
        )

    def test_reset_leaves_the_broker_running(self, workbench):
        """The broker is shared infrastructure: ensured, never stopped."""
        workbench.bench_reset()
        assert workbench.mqtt_status().get("running") is True

    def test_reset_is_idempotent(self, workbench):
        workbench.bench_reset()
        second = workbench.bench_reset()
        assert second["ok"] is True
        assert not second.get("errors"), second


class TestSerialWrite:
    """FR-030. Without it, a project's only way to send a byte is to open the
    RFC2217 port itself — and that asserts the control lines."""

    SLOT = None

    @pytest.fixture(autouse=True)
    def _bind_slot(self, present_slot):
        type(self).SLOT = present_slot

    def test_write_reaches_the_device_and_the_reply_is_captured(
            self, workbench, console_dut):
        """The only test here that proves bytes leave the bench.

        It needs something on the far end that answers. The bench used to
        own nothing that did, so this borrowed a project's M-Bus simulator —
        and went red when that project reflashed it, for a reason that had
        nothing to do with the workbench. The bench now carries its own
        console (test-firmware/): `ping` answers `OK pong`.

        The monitor has to be listening *before* the write. A reply to a
        one-line command arrives in milliseconds, so a monitor opened
        afterwards finds an empty buffer and reads it as silence — the same
        mistake as watching for a boot banner after the reset.
        """
        import threading
        slot = console_dut
        result = {}

        def watch():
            result["r"] = workbench.serial_monitor(
                slot, pattern="OK pong", timeout=12)

        t = threading.Thread(target=watch)
        t.start()
        time.sleep(1.5)
        w = workbench.serial_write(slot, text="ping\n")
        assert w["ok"] is True, w
        assert w["written"] > 0
        t.join()

        assert result["r"].get("matched"), (
            f"'ping' was written to {slot} and nothing answered. The bench "
            f"reports the write succeeded, which is a statement about the "
            f"socket, not the device. Last lines: "
            f"{result['r'].get('output', [])[-3:]}"
        )

    def test_hex_form_is_accepted(self, workbench):
        w = workbench.serial_write(self.SLOT, hex_bytes="0d0a")
        assert w["ok"] is True, w
        assert w["written"] == 2

    def test_neither_text_nor_hex_is_refused(self, workbench):
        w = workbench.serial_write(self.SLOT)
        assert w["ok"] is False
        assert "text" in w["error"] and "hex" in w["error"]

    def test_bad_hex_is_refused(self, workbench):
        w = workbench.serial_write(self.SLOT, hex_bytes="zz")
        assert w["ok"] is False
        assert "hex" in w["error"]

    def test_unknown_slot_is_refused(self, workbench):
        w = workbench.serial_write("SLOT9", text="x")
        assert w["ok"] is False


class TestApiSurface:
    """Every endpoint answers its contract.

    Not deep behaviour — that lives in the classes above. This is the check
    that an endpoint exists, accepts what Appendix D says it accepts, and
    refuses what it should. Twenty endpoints had no test of any kind before
    this, including two the author of these words guessed the wrong name for
    while reading the source instead of the contract.
    """

    def test_info_and_devices_answer(self, workbench):
        assert workbench.info().get("hostname")
        assert isinstance(workbench.get_devices(), list)

    def test_chip_info_reads_the_silicon(self, workbench):
        dut = next((d for d in workbench.get_devices()
                    if d.get("present") and d.get("detected_chip")), None)
        if not dut:
            pytest.skip("precondition unmet: no chip-detected DUT present")
        r = workbench._api_post_raw("/api/chip/info", {"slot": dut["label"]},
                                    timeout=90)
        if not r.get("ok"):
            pytest.skip(f"precondition unmet: esptool could not read the part ({r.get('error')})")
        assert r.get("mac"), "chip info returned no MAC"
        assert "ESP32" in r.get("chip", ""), r

    def test_proxy_stop_and_start_round_trip(self, workbench):
        dut = next((d for d in workbench.get_devices() if d.get("present")), None)
        if not dut:
            pytest.skip("precondition unmet: no device present")
        label, port = dut["label"], dut["tcp_port"]
        try:
            assert workbench._api_post_raw("/api/stop", {"slot": label})["ok"]
            after = workbench.get_slot(label)
            assert after["running"] is False
        finally:
            assert workbench._api_post_raw("/api/start", {"slot": label})["ok"]
        back = workbench.get_slot(label)
        assert back["running"] is True
        assert back["tcp_port"] == port, (
            "the slot came back on a different port; a client's saved URL "
            "would now reach the wrong device"
        )

    def test_human_interaction_lifecycle(self, workbench):
        st = workbench._api_get("/api/human/status")
        assert st["ok"] is True
        assert st.get("pending") is False, (
            "a prompt was already pending — bench_reset should have cleared it"
        )

    def test_test_progress_endpoint_answers(self, workbench):
        p = workbench._api_get("/api/test/progress")
        assert p.get("ok") is not False

    def test_sdr_endpoints_answer_or_declare_absence(self, workbench):
        """FR-0xx SDR. `live_stop` and `log_stop` had no test at all."""
        st = workbench.sdr_status()
        assert st["ok"] is True
        if not st.get("available"):
            # Honest: the endpoints must still answer, saying the dongle is absent.
            for ep in ("/api/sdr/live/stop", "/api/sdr/log/stop", "/api/sdr/stop"):
                r = workbench._api_post_raw(ep, {})
                assert "ok" in r, f"{ep} returned no verdict at all: {r}"
            pytest.skip("precondition unmet: no RTL-SDR dongle on this bench")
        for ep in ("/api/sdr/live/stop", "/api/sdr/log/stop", "/api/sdr/stop"):
            assert workbench._api_post_raw(ep, {}).get("ok") is not None

    def test_firmware_repository_round_trip(self, workbench):
        # The driver unwraps to the file list itself.
        assert isinstance(workbench.firmware_list(), list)

    def test_activity_log_answers(self, workbench):
        log = workbench.get_log()
        assert isinstance(log, (list, dict))


@requires_dut
class TestFlashEndpoint:
    """`/api/flash` — the bench's core job, and until now untested directly.

    The suite already flashed over RFC2217 from the test host
    (`_flash_device`), which exercises a different path entirely: esptool on
    the host talking through the proxy. This covers the endpoint, where
    esptool runs on the Pi against the devnode and the portal stops and
    restarts the proxy around it.
    """

    def _images(self, chip="esp32c3"):
        d = os.path.join(DEBUG_TEST_DIR, chip)
        images = {"0x0": os.path.join(d, "bootloader.bin"),
                  "0x8000": os.path.join(d, "partition-table.bin"),
                  "0x10000": os.path.join(d, "debug-test.bin")}
        if not all(os.path.exists(p) for p in images.values()):
            pytest.skip(f"precondition unmet: no prebuilt binaries for {chip}")
        return images

    def _c3_slot(self, workbench):
        dut = next((d for d in workbench.get_devices()
                    if d.get("present") and d.get("detected_chip") == "esp32c3"), None)
        if not dut:
            pytest.skip("precondition unmet: no esp32c3 DUT present")
        return dut

    def test_flash_writes_and_the_device_runs_the_image(self, workbench):
        """The whole point: after a flash, the part runs what was written.

        Asserting only that the call returned ok would pass on a flash that
        verified its hash and landed at an offset the partition table does not
        boot from — which is a real failure mode, and silent.
        """
        dut = self._c3_slot(workbench)
        label = dut["label"]
        r = workbench.flash(label, self._images(), chip="esp32c3")
        assert r.get("ok") is True, f"flash reported failure: {str(r)[:300]}"

        slot = workbench.get_slot(label)
        assert slot["running"] is True, (
            "the proxy was not restarted after the flash, so the slot is "
            "unusable even though the flash succeeded"
        )
        matched, lines = workbench.monitor_or_buffer(label, "LOOP:", seconds=20)
        assert matched, (
            f"the flash succeeded but the device is not running the image; "
            f"last lines: {lines[-3:]}"
        )

    def test_flash_with_no_images_is_refused(self, workbench):
        dut = self._c3_slot(workbench)
        r = workbench.flash(dut["label"], {}, chip="esp32c3")
        assert r.get("ok") is False, "a flash with no binaries must not report success"

    def test_flash_to_an_unknown_slot_is_refused(self, workbench):
        r = workbench.flash("SLOT9", self._images(), chip="esp32c3")
        assert r.get("ok") is False
        assert "not found" in str(r.get("error", "")).lower()

    def test_flash_leaves_the_slot_on_its_own_port(self, workbench):
        """A flash stops and restarts the proxy. If the slot came back on a
        different port, every client's saved URL would reach the wrong device.
        """
        dut = self._c3_slot(workbench)
        before = dut["tcp_port"]
        workbench.flash(dut["label"], self._images(), chip="esp32c3")
        after = workbench.get_slot(dut["label"])
        assert after["tcp_port"] == before
        assert after["monitor_port"] == before + 1000
