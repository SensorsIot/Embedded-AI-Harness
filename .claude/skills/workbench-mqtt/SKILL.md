---
name: workbench-mqtt
description: Use this skill whenever tests involve MQTT communication — starting/stopping the mosquitto broker on the workbench Pi, publishing test messages, subscribing to topics, or verifying ESP32 MQTT client behavior. The broker runs on the Pi's WiFi AP network (192.168.4.1:1883) so DUTs can reach it without internet. Use for MQTT integration tests, pub/sub verification, and broker lifecycle management. Triggers on "MQTT", "broker", "mosquitto", "publish", "subscribe", "topic", "MQTT test".
---

# ESP32 MQTT Broker

Base URL: `$WORKBENCH_URL` — see Step 0

## Step 0: Point at a bench

There are several benches and their addresses move, so nothing here writes one
down. `workbench.local` is not usable either — a container cannot resolve mDNS.
Discover the bench and export its URL:

```bash
export WORKBENCH_URL=$(sudo python3 .claude/skills/esp-idf-handling/discover-workbench.py \
                         --url --name <bench-hostname>)
curl -s "$WORKBENCH_URL/api/info"        # confirm before anything else
```

`--url` refuses to guess when more than one bench answers, so `--name` is
required whenever a second bench is powered on. `WORKBENCH_URL` is the same
variable `pytest --wt-url` falls back to.

The workbench can run an MQTT broker (mosquitto) for testing ESP32 devices that use MQTT for communication. The broker is accessible to devices connected to the workbench's WiFi AP.

## Endpoints

Request and response shapes: [FSD Appendix D.12](../../../docs/Embedded-Workbench-FSD.md#d12-mqtt-test-broker).

## Examples

```bash
# Start the MQTT broker
curl -X POST $WORKBENCH_URL/api/mqtt/start

# Check broker status
curl $WORKBENCH_URL/api/mqtt/status

# Stop the MQTT broker
curl -X POST $WORKBENCH_URL/api/mqtt/stop
```

## MQTT Broker Details

| Property | Value |
|----------|-------|
| Broker | the bench address (from the LAN) or `192.168.4.1` (from the workbench AP) |
| Default port | `1883` |
| Authentication | None (open broker for testing) |

## Common Workflows

1. **Test ESP32 MQTT client:**
   - Ensure device is on workbench WiFi (see workbench-wifi)
   - `POST /api/mqtt/start` — start broker
   - Device connects to `192.168.4.1:1883`
   - Monitor device behavior via serial or UDP logs (see workbench-logging)
   - `POST /api/mqtt/stop` — stop broker when done

2. **Test MQTT disconnect/reconnect:**
   - Start broker, let device connect
   - `POST /api/mqtt/stop` — device loses MQTT
   - Monitor device's reconnection behavior
   - `POST /api/mqtt/start` — device should reconnect

3. **Test MQTT + WiFi together:**
   - Start AP + broker
   - `POST /api/wifi/ap_stop` — device loses both WiFi and MQTT
   - `POST /api/wifi/ap_start` + `POST /api/mqtt/start` — restore both
   - Verify device recovers

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Broker won't start | Check if mosquitto is installed on the workbench Pi |
| Device can't connect | Ensure device is on workbench WiFi; use broker IP `192.168.4.1` from AP clients |
| Broker status shows stopped | Start it with `POST /api/mqtt/start` |
