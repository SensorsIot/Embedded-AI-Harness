---
name: testbench-wifi
description: Use this skill whenever you need to control the testbench's WiFi radio for testing — starting a SoftAP for DUTs to connect to, joining a DUT's captive portal as a station, scanning for networks, relaying HTTP requests to devices on the WiFi network, or provisioning DUT WiFi credentials. Essential for any test that involves WiFi connectivity, captive portal flows, or HTTP communication with devices on the isolated test network (192.168.4.x). Triggers on "wifi", "AP", "station", "scan", "provision", "captive portal", "enter-portal", "HTTP relay", "wifi test", "SoftAP".
---

# ESP32 WiFi & Provisioning

Base URL: `$TESTBENCH_URL` — see Step 0

## Step 0: Point at a bench

There are several benches and their addresses move, so nothing here writes one
down. `testbench.local` is not usable either — a container cannot resolve mDNS.
Discover the bench and export its URL:

```bash
export TESTBENCH_URL=$(sudo python3 .claude/skills/esp-idf-handling/discover-testbench.py \
                         --url --name <bench-hostname>)
curl -s "$TESTBENCH_URL/api/info"        # confirm before anything else
```

`--url` refuses to guess when more than one bench answers, so `--name` is
required whenever a second bench is powered on. `TESTBENCH_URL` is the same
variable `pytest --wt-url` falls back to.

## Operating Modes

The testbench has two WiFi operating modes:

| Mode | wlan0 usage | WiFi endpoints |
|------|-------------|----------------|
| **wifi-testing** (default) | Test instrument (AP/STA/scan) | Active |
| **serial-interface** | Joins WiFi for additional LAN | Disabled |

```bash
# Check current mode
curl $TESTBENCH_URL/api/wifi/mode

# Switch to wifi-testing mode
curl -X POST $TESTBENCH_URL/api/wifi/mode \
  -H 'Content-Type: application/json' \
  -d '{"mode": "wifi-testing"}'

# Switch to serial-interface mode (joins a WiFi network)
curl -X POST $TESTBENCH_URL/api/wifi/mode \
  -H 'Content-Type: application/json' \
  -d '{"mode": "serial-interface", "ssid": "MyNetwork", "pass": "password"}'
```

## Endpoints

Request and response shapes: [FSD Appendix D.4](../../../docs/Harness-FSD.md#d4-wifi-instrument), plus
`/api/enter-portal` in [D.2](../../../docs/Harness-FSD.md#d2-serial-management).

**AP and STA are mutually exclusive** — one radio. Starting the AP drops any STA
association and vice versa, so a test that needs both must sequence them.

## WiFi AP (Access Point)

```bash
# Start AP
curl -X POST $TESTBENCH_URL/api/wifi/ap_start \
  -H 'Content-Type: application/json' \
  -d '{"ssid": "TestAP", "pass": "testpass123", "channel": 6}'

# Check AP status and connected clients
curl $TESTBENCH_URL/api/wifi/ap_status

# Stop AP
curl -X POST $TESTBENCH_URL/api/wifi/ap_stop
```

AP and STA are mutually exclusive — starting one stops the other.

## WiFi STA (Station)

```bash
# Join a network
curl -X POST $TESTBENCH_URL/api/wifi/sta_join \
  -H 'Content-Type: application/json' \
  -d '{"ssid": "MyNetwork", "pass": "password", "timeout": 15}'

# Disconnect
curl -X POST $TESTBENCH_URL/api/wifi/sta_leave
```

## WiFi Scan

```bash
curl $TESTBENCH_URL/api/wifi/scan
```

## WiFi On/Off Testing

To test a device's behavior when WiFi connectivity is lost and restored:

```bash
# 1. Ensure device is connected to testbench AP
curl -X POST $TESTBENCH_URL/api/wifi/ap_start \
  -H 'Content-Type: application/json' \
  -d '{"ssid": "TestAP", "pass": "testpass123"}'

# 2. Stop AP — device loses WiFi
curl -X POST $TESTBENCH_URL/api/wifi/ap_stop

# 3. Monitor device behavior (serial or UDP logs)
# ... wait for desired duration ...

# 4. Restart AP — device should reconnect
curl -X POST $TESTBENCH_URL/api/wifi/ap_start \
  -H 'Content-Type: application/json' \
  -d '{"ssid": "TestAP", "pass": "testpass123"}'

# 5. Wait for device to reconnect
curl "$TESTBENCH_URL/api/wifi/events?timeout=30"
```

## HTTP Relay

**IMPORTANT:** Devices on the testbench AP (192.168.4.x) are NOT directly reachable from the development machine. Always use this relay to make HTTP requests to device endpoints (e.g. `/status`, `/ota`). The response body is base64-encoded — decode it to get the actual JSON.

```bash
# GET request to device
curl -X POST $TESTBENCH_URL/api/wifi/http \
  -H 'Content-Type: application/json' \
  -d '{"method": "GET", "url": "http://192.168.4.2/status", "timeout": 10}'

# POST with base64-encoded body
BODY=$(echo -n '{"key":"value"}' | base64)
curl -X POST $TESTBENCH_URL/api/wifi/http \
  -H 'Content-Type: application/json' \
  -d "{\"method\": \"POST\", \"url\": \"http://192.168.4.2/config\", \"headers\": {\"Content-Type\": \"application/json\"}, \"body\": \"$BODY\", \"timeout\": 10}"

# Decode the base64 response body
curl -s -X POST $TESTBENCH_URL/api/wifi/http \
  -H 'Content-Type: application/json' \
  -d '{"method": "GET", "url": "http://192.168.4.x:8080/endpoint", "timeout": 10}' \
  | python3 -c "import json,sys,base64; r=json.load(sys.stdin); print(base64.b64decode(r['body']).decode())"
```

## WiFi Events

Long-poll for STA_CONNECT / STA_DISCONNECT events:

```bash
curl "$TESTBENCH_URL/api/wifi/events?timeout=30"
```

## Enter-Portal (Captive Portal Provisioning)

Ensures a device is connected to the testbench AP. If the device has no WiFi credentials, the testbench provisions it via the device's captive portal.

```bash
curl -X POST $TESTBENCH_URL/api/enter-portal \
  -H 'Content-Type: application/json' \
  -d '{"portal_ssid": "<DUT-portal-SSID>", "ssid": "TestAP", "password": "testpass123"}'
```

| Field | Description |
|-------|-------------|
| `portal_ssid` | Device's captive portal SoftAP name |
| `ssid` | Testbench's AP SSID (filled into the device's portal form) |
| `password` | Testbench's AP password (filled into the device's portal form) |

**Procedure:**
1. Starts testbench AP (using `ssid`/`password`) if not already running
2. Waits for the device to connect (it may already have credentials)
3. If device doesn't connect, testbench joins the device's captive portal SoftAP (`portal_ssid`)
4. Follows the auto-redirect to the portal page
5. Parses the HTML form and fills in the testbench AP credentials
6. Submits the form
7. Disconnects from the device's SoftAP
8. Waits for the device to reboot and connect to the testbench AP

**All three values must come from the project FSD** — never guess them.

Monitor progress via `GET /api/log`.

### Getting the device into portal mode first

`/api/enter-portal` assumes the device will offer its portal. A device that
already holds credentials will not, so the portal has to be forced. Three ways,
best first — all of them need the pin, the active level and the serial marker
looked up in the project's FSD:

**GPIO** — fully automated, when a Pi pin is wired to the device's portal button:

```python
try:
    wt.gpio_set(PI_PIN, 0)                 # hold the portal pin low
    result = wt.serial_reset(SLOT)          # reset — device boots into portal
    assert any(PORTAL_MARKER in l for l in result["output"])
finally:
    wt.gpio_set(PI_PIN, "z")               # always release, even on failure
```

Release the pin in a `finally`: left driven, it holds the device in portal mode
for every later test in the run. `ok: true` confirms the write — do not poll
`gpio_get()` to check.

**Rapid resets** — for firmware with a boot-counter trigger:
`wt.enter_portal(SLOT, resets=3)`, then wait for `idle`.

**An operator** — no GPIO wiring: raise a blocking prompt (see
`testbench-test-handling`) on a thread, reset, and match the marker while the
operator holds the button.

## Common Workflows

1. **Ensure device is connected to testbench AP:**
   - `POST /api/enter-portal` with all three values
   - `GET /api/wifi/ap_status` — verify device appears as connected client

2. **Test device WiFi connectivity:**
   - `POST /api/enter-portal` — ensure device is on testbench AP
   - `POST /api/wifi/http` — relay HTTP to device's IP to verify it responds

3. **Test WiFi disconnect/reconnect behavior:**
   - `POST /api/wifi/ap_stop` — device loses WiFi
   - Monitor device via serial (see testbench-logging)
   - `POST /api/wifi/ap_start` — device should reconnect
   - `GET /api/wifi/events` — confirm reconnection

## Troubleshooting

| Problem | Fix |
|---------|-----|
| AP won't start | Check that mode is `wifi-testing` via `GET /api/wifi/mode` |
| STA join timeout | Verify SSID/password; increase timeout |
| HTTP relay fails | Ensure testbench is on same network as target (AP or STA) |
| enter-portal "already running" | Previous run still active; wait for it to finish |
| No events from long-poll | DUT may not have connected yet; increase timeout |
| WiFi endpoints return "disabled" | System is in serial-interface mode; switch to wifi-testing |
