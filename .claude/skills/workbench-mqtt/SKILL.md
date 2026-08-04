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

   **On a *shared* broker, don't stop it — isolate the one device.** If the
   broker also carries other devices (or the device under test uses a
   production broker over a tunnel rather than the bench mosquitto), stopping it
   is collateral damage. Cut MQTT for a single device with a source-scoped
   firewall rule on the broker host instead (needs root there):

   ```bash
   # black hole (timeout): device sees silence, its keepalive eventually fires the will
   iptables -I INPUT -s <device-ip> -p tcp --dport 1883 -j DROP
   # connection refused (TCP reset): device sees an immediate refusal
   iptables -I INPUT -s <device-ip> -p tcp --dport 1883 -j REJECT --reject-with tcp-reset
   ```

   The two are different tests: `DROP` is the "broker went away" black hole that
   exercises the last-will keepalive timeout; `REJECT` is the "broker actively
   refuses" path. Delete the rule (`-D` instead of `-I`) to restore. Prefer this
   over `/api/mqtt/stop` whenever the broker is not exclusively the DUT's.

3. **Test MQTT + WiFi together:**
   - Start AP + broker
   - `POST /api/wifi/ap_stop` — device loses both WiFi and MQTT
   - `POST /api/wifi/ap_start` + `POST /api/mqtt/start` — restore both
   - Verify device recovers

## A last-will topic is death-only — don't test for it "returning to online"

The MQTT Last Will is published by the **broker**, on the device's behalf, only
when the connection drops uncleanly. A device typically registers a retained
will like `<id>/LWT = offline` and signals *liveness* on a **separate** birth or
status topic (e.g. `<id>/STATUS {"online":true}`, republished on every connect
and periodically). Nothing ever writes `LWT = online` — the will topic stays
`offline` from the last drop until the next one.

So when checking recovery after an outage, watch for the **birth/status message
to be republished**, not for the will topic to flip back. And because the
retained will persists, a stale `offline` cannot be told apart from a freshly
fired one by reading the retained value — to prove a will *fired*, seed a
sentinel first (`mosquitto_pub -t <id>/LWT -r -m sentinel`), then confirm the
broker overwrites it with `offline` once the keepalive expires.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Broker won't start | Check if mosquitto is installed on the workbench Pi |
| Device can't connect | Ensure device is on workbench WiFi; use broker IP `192.168.4.1` from AP clients |
| Broker status shows stopped | Start it with `POST /api/mqtt/start` |
| Device "never comes back online" | You are probably watching the `/LWT` will topic — it is death-only; watch the birth/status topic instead (see above) |
