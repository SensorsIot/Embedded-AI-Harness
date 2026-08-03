# Embedded / IoT Section Templates

Optional sections for projects involving firmware, hardware, serial communication, OTA updates, WiFi, BLE, or message brokers. Include these when the system under test is an embedded device or IoT product.

## Table of Contents

1. [Hardware Setup & Infrastructure Rules](#e1-hardware-setup--infrastructure-rules)
2. [Serial State Detection & Recovery](#e2-serial-state-detection--recovery)
3. [OTA Update Tests](#e3-ota-update-tests)
4. [WiFi / BLE / MQTT Protocol Tests](#e4-wifi--ble--mqtt-protocol-tests)
5. [GPIO Wiring & Automated Pin Control](#e5-gpio-wiring--automated-pin-control)

---

## E1. Hardware Setup & Infrastructure Rules

Add this to the Test Environment section when the SUT is a physical device.

```markdown
### Hardware Setup

| Component | Description | Connection |
|-----------|-------------|------------|
| DUT | {DEVICE_NAME} ({MCU_TYPE}) | {USB/UART/JTAG} via {HOST} |
| {PERIPHERAL_1} | {DESCRIPTION} | {CONNECTION_TYPE} |
| {PERIPHERAL_2} | {DESCRIPTION} | {CONNECTION_TYPE} |

### Partition Layout

| Partition | Offset | Size | Contents |
|-----------|--------|------|----------|
| bootloader | {OFFSET} | {SIZE} | Second-stage bootloader |
| partition table | {OFFSET} | {SIZE} | Partition definitions |
| nvs | {OFFSET} | {SIZE} | Non-volatile storage (config) |
| app | {OFFSET} | {SIZE} | Application firmware |

### Infrastructure Rules

- **{SERVICE_1}** (e.g., serial portal): always running. No test may restart it.
- **{SERVICE_2}** (e.g., MQTT broker): always running. Only TC-000 and {RECOVERY_TESTS} may restart it.
- **DUT**: may be reset by flash/erase tests. Must be restored to clean state after.

### DUT Initial State

Before running any test, the DUT must be in this state:

1. Flash firmware: `{FLASH_COMMAND}`
2. Erase NVS/config: `{ERASE_COMMAND}`
3. Verify boot: serial output contains `{BOOT_SUCCESS_STRING}`
4. Verify clean config: `{CONFIG_CHECK}` returns defaults

**What "clean" means:**
- Factory default configuration
- No persisted credentials or custom settings
- Boot counter at initial value
- No error flags set
```

---

## E2. Serial State Detection & Recovery

Add this when the DUT communicates via serial (UART, USB CDC, JTAG).

```markdown
### Serial State Detection

The serial port is the primary diagnostic interface. It works in ALL device states including boot loops and crashed firmware.

| Serial Output Pattern | Device State | Action |
|-----------------------|-------------|--------|
| `{BOOT_DOWNLOAD_PATTERN}` | Download/bootloader mode | Flash firmware to recover |
| `{BOOT_NORMAL_PATTERN}` | Normal boot, running | Ready for testing |
| `{CRASH_PATTERN}` | Crash/panic | Read backtrace, reflash |
| No output | Firmware has serial off, or connection issue | Check cables, reflash with serial-enabled build |

### Recovery Procedures

**From download mode:**
```bash
{FLASH_COMMAND_WITH_RESET}
```

**From crash loop:**
```bash
{ERASE_AND_REFLASH_COMMAND}
```

**Serial monitoring:**
```bash
{SERIAL_MONITOR_COMMAND}
```

### Serial Port Safety Rules

- {RULE_1, e.g., "Never open port without disabling DTR to avoid reset"}
- {RULE_2, e.g., "Use --after=watchdog-reset for ESP32-C3 native USB"}
- {RULE_3, e.g., "Wait 2s after hotplug before opening port"}
```

---

## E3. OTA Update Tests

Test cases for over-the-air firmware update mechanisms.

```markdown
### OTA Update Tests

#### TC-{NNN}: OTA Firmware Update (Happy Path)

**Precondition:**
- DUT reachable: `{HEALTH_CHECK}` returns {EXPECTED}
- Current version: `{VERSION_CHECK}` returns `{OLD_VERSION}`
- New firmware built: `{BUILD_ARTIFACT}` exists

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Upload firmware via {METHOD} | Upload accepted, progress reported |
| 2 | Wait for DUT to reboot | DUT reboots within {TIMEOUT} seconds |
| 3 | Verify new version | `{VERSION_CHECK}` returns `{NEW_VERSION}` |
| 4 | Verify configuration preserved | Settings match pre-update values |
| 5 | Verify functionality | `{HEALTH_CHECK}` returns {EXPECTED} |

**Pass Criteria:** Firmware updates successfully, version increments, config is preserved, DUT is operational.

**Automation:** `{OTA_COMMAND}`

---

#### TC-{NNN}: OTA with Invalid Authentication

**Precondition:**
- DUT reachable: `{HEALTH_CHECK}` returns {EXPECTED}

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Attempt OTA upload with wrong credentials | HTTP 401 or 403 |
| 2 | Attempt OTA upload with no credentials | HTTP 401 or 403 |
| 3 | Verify DUT unchanged | Version unchanged, DUT operational |

**Pass Criteria:** DUT rejects unauthorized OTA attempts and continues normal operation.

**Automation:** `{OTA_AUTH_TEST_COMMAND}`

---

#### TC-{NNN}: OTA with Corrupt Firmware

**Precondition:**
- DUT reachable: `{HEALTH_CHECK}` returns {EXPECTED}
- Corrupt firmware file prepared: `{CORRUPT_FILE}`

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Upload corrupt firmware | Upload rejected or fails validation |
| 2 | Verify DUT unchanged | Original firmware still running |
| 3 | Verify functionality | `{HEALTH_CHECK}` returns {EXPECTED} |

**Pass Criteria:** DUT rejects corrupt firmware and remains on previous working version.

**Automation:** `{OTA_CORRUPT_TEST_COMMAND}`
```

---

## E4. WiFi / BLE / MQTT Protocol Tests

Test cases for wireless connectivity and message broker protocols.

```markdown
### WiFi Connection Tests

#### WIFI-{NNN}: Connect to Known Network

**Precondition:**
- DUT in default state (no saved credentials)
- Test AP running: `{AP_CHECK}` returns active

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Configure WiFi credentials via {METHOD} | Credentials accepted |
| 2 | Wait for connection | DUT connects within {TIMEOUT} seconds |
| 3 | Verify IP address | DUT has valid IP on test network |
| 4 | Verify connectivity | `{PING_OR_HTTP_CHECK}` succeeds |

**Pass Criteria:** DUT connects to WiFi and is reachable on the network.

**Automation:** `{WIFI_CONNECT_TEST}`

---

#### WIFI-{NNN}: Reconnect After AP Dropout

**Precondition:**
- DUT connected to test AP: `{CONNECTION_CHECK}`
- Baseline reconnect count: record as `R_before`

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Disable test AP | DUT loses connection |
| 2 | Wait {DROPOUT_DURATION} | DUT in disconnected state |
| 3 | Re-enable test AP | AP broadcasting again |
| 4 | Wait for reconnection | DUT reconnects within {TIMEOUT} seconds |
| 5 | Verify reconnect count | Count is `R_before + 1` |

**Pass Criteria:** DUT automatically reconnects after AP dropout without manual intervention.

**Automation:** `{WIFI_RECONNECT_TEST}`

---

### Captive Portal Tests

#### CP-{NNN}: Captive Portal WiFi Provisioning

**Precondition:**
- DUT in AP/portal mode (triggered via GPIO — see E5 — or by erasing credentials)
- DUT AP visible: scan shows `{AP_SSID}`

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Connect to DUT AP | Client gets IP from DUT DHCP |
| 2 | Open captive portal page | Portal UI loads at `{PORTAL_URL}` |
| 3 | Enter WiFi credentials | Form accepts input |
| 4 | Submit credentials | DUT saves and attempts connection |
| 5 | Verify DUT connects to target network | DUT reachable on target network |

**Pass Criteria:** User can provision WiFi credentials through captive portal, DUT connects to target network.

**Automation:** Manual / `{PORTAL_TEST_COMMAND}`

---

### MQTT Tests

#### TC-{NNN}: MQTT Subscribe and Receive

**Precondition:**
- DUT connected to network: `{NETWORK_CHECK}`
- MQTT broker accessible: `{BROKER_CHECK}`
- DUT subscribed to `{TOPIC}`: `{SUBSCRIPTION_CHECK}`

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Publish test message to `{TOPIC}` | Broker accepts message |
| 2 | Wait {PROCESSING_TIME} | DUT processes message |
| 3 | Verify DUT received message | `{STATE_CHECK}` reflects published value |

**Pass Criteria:** DUT receives and correctly processes MQTT message.

**Automation:** `{MQTT_SUB_TEST}`

---

#### TC-{NNN}: MQTT Disconnect and Reconnect

**Precondition:**
- DUT MQTT connected: `{MQTT_STATUS_CHECK}` shows connected
- Baseline reconnect count: record as `R_before`

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Stop MQTT broker | DUT detects disconnection |
| 2 | Wait {DISCONNECT_DURATION} | DUT in disconnected state |
| 3 | Restart MQTT broker | Broker available again |
| 4 | Wait for reconnection | DUT reconnects within {TIMEOUT} |
| 5 | Publish test message | DUT receives message normally |
| 6 | Verify reconnect count | Count is `R_before + 1` |

**Pass Criteria:** DUT automatically reconnects to MQTT broker and resumes normal operation.

**Automation:** `{MQTT_RECONNECT_TEST}`

---

### Watchdog Tests

#### EC-{NNN}: Software Watchdog Recovery

**Precondition:**
- DUT running: `{HEALTH_CHECK}` returns {EXPECTED}
- Watchdog timeout configured: {TIMEOUT_VALUE}

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Trigger condition that stalls main loop | DUT hangs |
| 2 | Wait for watchdog timeout ({TIMEOUT_VALUE}) | Watchdog triggers reset |
| 3 | Verify DUT reboots | Serial shows boot sequence |
| 4 | Verify DUT recovers | `{HEALTH_CHECK}` returns {EXPECTED} |

**Pass Criteria:** Watchdog detects stall and resets DUT to operational state.

**Automation:** Manual (requires special test firmware) / `{WATCHDOG_TEST}`

---

#### EC-{NNN}: Memory Exhaustion Watchdog

**Precondition:**
- DUT running: `{HEALTH_CHECK}` returns {EXPECTED}
- Baseline heap: record `{HEAP_METRIC}` as `H_before`
- Memory threshold: {THRESHOLD_VALUE}

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Trigger progressive memory allocation | Heap decreases |
| 2 | Monitor heap until below threshold | Watchdog detects low memory |
| 3 | Verify protective action | DUT restarts or frees memory |
| 4 | Verify recovery | Heap returns to safe level |

**Pass Criteria:** Memory watchdog prevents crash by taking corrective action when heap drops below threshold.

**Automation:** Manual (requires special test firmware) / `{MEMORY_TEST}`
```

---

## E5. GPIO Wiring & Automated Pin Control

Add this section when the DUT has GPIO pins that affect behavior (boot mode selection, config/provisioning triggers, factory reset buttons). Wiring these to the Serial Portal Pi allows tests to drive them programmatically, eliminating manual button presses.

### How to discover GPIO pins to wire

Search the DUT firmware source code for pins that the DUT **reads** to decide behavior:

```bash
# Search patterns — adapt to the project's language/framework
grep -rn "digitalRead\|gpio_get_level\|INPUT_PULLUP\|INPUT_PULLDOWN" src/
grep -rn "BUTTON\|BTN\|PORTAL\|FACTORY_RESET\|BOOT_MODE" src/
```

For each pin found, record:

| Field | Example |
|-------|---------|
| DUT pin number | GPIO 2 |
| Function | Captive portal trigger |
| Active level | LOW (pressed = LOW) |
| Pull resistor | INPUT_PULLUP (internal) |
| When sampled | Once at boot, after NVS init |
| Serial output when triggered | `CAPTIVE PORTAL MODE TRIGGERED` |

### Template

```markdown
### GPIO Wiring for Automated Testing

The Serial Portal Pi can drive GPIO pins on the DUT to trigger hardware-level behavior changes (e.g. enter provisioning mode, factory reset) without manual button presses. Each connection uses one Pi GPIO wired directly to one DUT GPIO.

**Discovery:** Search DUT firmware for `digitalRead`, `gpio_get_level`, `INPUT_PULLUP`, `INPUT_PULLDOWN`, and button/pin definitions. Any GPIO the DUT reads to decide behavior is a candidate.

#### GPIO Connections

| Pi GPIO (BCM) | DUT GPIO | Function | Active Level | DUT Pull | When Sampled |
|---------------|----------|----------|-------------|----------|-------------|
| {PI_PIN_1} | {DUT_PIN_1} | {FUNCTION_1} | {LOW/HIGH} | {PULLUP/PULLDOWN/NONE} | {BOOT/CONTINUOUS} |
| {PI_PIN_2} | {DUT_PIN_2} | {FUNCTION_2} | {LOW/HIGH} | {PULLUP/PULLDOWN/NONE} | {BOOT/CONTINUOUS} |

**Pin allowlist:** Only these Pi BCM pins may be used: {5, 6, 12, 13, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26}

#### Usage Pattern

To trigger a boot-time behavior (e.g. captive portal, factory reset):

```python
try:
    wt.gpio_set({PI_PIN}, 0)                # Hold DUT pin in active state
    result = wt.serial_reset(SLOT)           # Reset DUT — boots with pin held
    assert any("{EXPECTED_MARKER}" in l for l in result["output"])
finally:
    wt.gpio_set({PI_PIN}, "z")              # Release — DUT pull-up/down restores idle
```

**Rules:**
1. Always release GPIO to input (`"z"`) when done — use try/finally
2. Trust the `ok: true` response — do not poll `gpio_get()` to verify
3. Drive the pin **before** resetting the DUT, not after

#### Impact on Test Classification

Tests that previously required manual button presses become fully automated when GPIO wiring is available. Move these tests from "Manual" to "Automated" phase and remove `human_interaction()` calls.

| Before GPIO | After GPIO |
|------------|-----------|
| Phase 1 (Manual): operator holds button during boot | Phase 2 (Automated): `wt.gpio_set()` + `wt.serial_reset()` |
| `wt.human_interaction("Hold button...")` | `wt.gpio_set(pin, 0)` |
| 5+ second human response time | Instant, deterministic |
```
