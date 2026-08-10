---
name: testbench-ble
description: Use this skill whenever the user needs to interact with BLE peripherals through the testbench — scanning for devices, connecting by address, writing to GATT characteristics, or checking connection status. The Pi acts as a BLE-to-HTTP bridge using bleak. Also use when sending keystrokes to BLE HID devices, triggering OTA via BLE commands, or debugging BLE connectivity. Triggers on "BLE", "bluetooth", "GATT", "NUS", "Nordic UART", "BLE scan", "BLE write", "BLE connect".
---

# ESP32 Bluetooth LE Proxy

Base URL: `$TESTBENCH_URL` — see Step 0

## Step 0: Point at a bench

There are several benches and their addresses move, so nothing here writes one
down. `$BENCH` is not usable either — a container cannot resolve mDNS.
Discover the bench and export its URL:

```bash
export TESTBENCH_URL=$(sudo python3 .claude/skills/esp-idf-handling/discover-testbench.py \
                         --url --name <bench-hostname>)
curl -s "$TESTBENCH_URL/api/info"        # confirm before anything else
```

`--url` refuses to guess when more than one bench answers, so `--name` is
required whenever a second bench is powered on. `TESTBENCH_URL` is the same
variable `pytest --wt-url` falls back to.

## Endpoints

Request and response shapes: [FSD Appendix D.5](../../../docs/Harness-FSD.md#d5-ble-proxy).

**One BLE connection at a time** — connect to a second peripheral without
disconnecting the first and the call fails rather than switching.

## Examples

```bash
# Scan for BLE devices (5s timeout)
curl -X POST $TESTBENCH_URL/api/ble/scan \
  -H 'Content-Type: application/json' \
  -d '{"timeout": 5}'

# Scan with name filter
curl -X POST $TESTBENCH_URL/api/ble/scan \
  -H 'Content-Type: application/json' \
  -d '{"timeout": 5, "name_filter": "<device-name>"}'

# Connect by MAC address
curl -X POST $TESTBENCH_URL/api/ble/connect \
  -H 'Content-Type: application/json' \
  -d '{"address": "AA:BB:CC:DD:EE:FF"}'

# Write hex data to a GATT characteristic
curl -X POST $TESTBENCH_URL/api/ble/write \
  -H 'Content-Type: application/json' \
  -d '{"characteristic": "6e400002-b5a3-f393-e0a9-e50e24dcca9e", "data": "48656c6c6f", "response": true}'

# Check connection status
curl $TESTBENCH_URL/api/ble/status

# Disconnect
curl -X POST $TESTBENCH_URL/api/ble/disconnect
```

## Nordic UART Service (NUS) UUIDs

| UUID | Role |
|------|------|
| `6e400001-b5a3-f393-e0a9-e50e24dcca9e` | NUS Service |
| `6e400002-b5a3-f393-e0a9-e50e24dcca9e` | RX Characteristic (write to this) |
| `6e400003-b5a3-f393-e0a9-e50e24dcca9e` | TX Characteristic (notifications from device) |

## Common Workflows

1. **Send a command via NUS:**
   - `POST /api/ble/scan` with `name_filter` to find device
   - `POST /api/ble/connect` with the MAC address from scan results
   - `POST /api/ble/write` with NUS RX UUID and hex-encoded command
   - `POST /api/ble/disconnect` when done

2. **Check if device is advertising:**
   - `POST /api/ble/scan` with short timeout and name filter
   - Check `devices` array in response

3. **Send binary command protocol:**
   - Connect to device
   - Encode command bytes as hex (e.g., `0x02` + "Hello" = `0248656c6c6f`)
   - Write to NUS RX characteristic
   - Monitor device response via serial or UDP logs (see testbench-logging)

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "BLE not available" | `bleak` not installed on testbench Pi |
| Scan returns empty | Increase timeout; check device is advertising |
| Connect fails (409) | Already connected — disconnect first |
| Write fails "invalid hex data" | Data must be hex string (e.g., `"48656c6c6f"` for "Hello") |
| Device not found by name | Check exact advertised name; BLE names are case-sensitive |
