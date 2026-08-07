# WiFi Test Cases for ESP32 Projects

Standard test cases for ESP32 WiFi STA functionality. Copy relevant sections into project FSDs.

---

## 1. WiFi Requirements

### 1.1 WiFi Station Mode (STA)

| ID | Requirement | Priority |
|----|-------------|----------|
| WIFI-001 | System SHALL connect to configured WiFi network in STA mode | Must |
| WIFI-002 | WiFi credentials SHALL be stored per the project's security profile — see NVS-010..013 in `nvs-test-cases.md`, which owns this requirement | Must |
| WIFI-003 | System SHALL automatically reconnect on WiFi disconnect | Must |
| WIFI-004 | System SHALL log WiFi connection status changes | Should |
| WIFI-005 | System SHALL support WPA2/WPA3 authentication | Must |

### 1.2 Test Mode (WiFi + Ethernet)

| ID | Requirement | Priority |
|----|-------------|----------|
| TEST-001 | System SHALL support a "Test mode" configurable via captive portal or NVS | Should |
| TEST-002 | In Test mode, server SHALL listen on ALL interfaces (ETH + WiFi) | Should |
| TEST-003 | In Test mode, clients MAY connect via WiFi instead of Ethernet | May |
| TEST-004 | Test mode SHALL be indicated via serial log and status messages | Should |
| TEST-005 | Test mode allows full operation without Ethernet hardware connected | Should |

---

## 2. Edge Case Test Cases

### EC-100: Network Disconnect During Active Session

**Objective**: Verify the device survives a network outage and resumes
publishing without losing buffered telemetry.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Active session running | Data publishing |
| 2 | Disconnect network cable/WiFi | Connection lost |
| 3 | Session continues locally | Uptime counter keeps incrementing; no reboot line in serial |
| 4 | Wait 30 s | >= 2 reconnect attempts logged, each with a timestamp |
| 5 | Restore network | Reconnects |
| 6 | Session state restored | Publishing resumes within {{reconnect_deadline_s}} s of link-up |

**Pass Criteria**: publishing resumes within {{reconnect_deadline_s}} s of the
link returning; every sample generated during the outage, up to the buffer depth
the FSD declares ({{offline_buffer_depth}}), reaches the subscriber in order; the
uptime counter is continuous (no reboot).

### EC-101: WiFi Disconnect During Operation

**Objective**: Verify WiFi loss does not affect other network operations.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Session active | Application layer publishing via WiFi |
| 2 | Disable WiFi AP | WiFi connection lost |
| 3 | Other interfaces continue | Ethernet communication OK |
| 4 | Messages queued | Buffer fills |
| 5 | Re-enable WiFi AP | WiFi reconnects |
| 6 | Queued messages sent | Application layer catches up |

**Pass Criteria**: Other interfaces unaffected, application layer recovers automatically.

### EC-110: WiFi Signal Strength Degradation

**Objective**: Verify link degradation is bounded and recovery automatic as RSSI falls.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Normal operation | RSSI > -60 dBm |
| 2 | Increase distance to AP | RSSI decreases |
| 3 | Monitor at -70 dBm | Connection maintained |
| 4 | Publish 200 messages at -80 dBm | >= 190 delivered (<= 5 % loss); link stays associated |
| 5 | Monitor at -85 dBm | Reconnection attempts |
| 6 | Return to normal range | Connection stabilizes |

**Pass Criteria**: no reboot at any RSSI step; loss stays <= 5 % down to -80 dBm;
after returning to range the device is associated and publishing within
{{reconnect_deadline_s}} s without manual action.

### EC-111: WiFi AP Channel Congestion

**Objective**: Verify system handles congested WiFi environment.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Connect to AP on channel 6 | Normal operation |
| 2 | Enable multiple interfering APs on the same channel | Round-trip latency rises above baseline |
| 3 | Publish 200 messages and count them at the subscriber | All 200 arrive, though slower than baseline |
| 4 | Monitor reconnection behaviour | Any reconnect completes without operator action |
| 5 | Disable interfering APs | Latency returns to within 20 % of baseline |

**Pass Criteria**: all 200 published messages reach the subscriber within 120 s
of publication; at QoS 1 no message is redelivered more than once; no reboot.

### EC-115: DHCP Lease Expiry

**Objective**: Verify system handles DHCP lease renewal.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Set short DHCP lease (60s) | System gets IP |
| 2 | Wait for lease expiry | Renewal attempt |
| 3 | Verify IP maintained | Same or new IP |
| 4 | Verify application connection | Reconnects if IP changed |
| 5 | Publish 10 messages after renewal | All 10 delivered; no operator action performed |

**Pass Criteria**: Automatic lease renewal, connection recovery.

---

## 3. Test Environment Setup

### Required Equipment

- ESP32 device under test
- WiFi router with configurable settings
- Network analyzer (Wireshark optional)

### Network Configuration Template

```
WiFi Network: TestNetwork
Password: testpassword123
DHCP Range: 192.168.1.100-200
```

### Monitoring Commands

```bash
# Monitor ESP32 serial output
idf.py monitor
# or
pio device monitor

# Check WiFi signal strength
iw dev wlan0 link
```
