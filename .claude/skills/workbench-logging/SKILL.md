---
name: workbench-logging
description: Use this skill whenever you need to read serial output or debug logs from ESP32 devices on the workbench. Covers serial monitor with pattern matching (wait for boot messages, WiFi connected, crash dumps), UDP debug log retrieval when USB is occupied (e.g. HID keyboard), boot capture, and crash analysis. Use for verifying firmware started correctly, checking WiFi connection status, or diagnosing boot loops. Triggers on "serial monitor", "log", "debug log", "UDP log", "boot output", "crash", "monitor", "pattern", "serial output".
---

# ESP32 Debug Logging

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

Two logging methods are available. Choose based on your situation:

| | Serial Monitor | UDP Logs |
|---|---|---|
| **Works without WiFi** | Yes | No |
| **Boot/crash output** | Yes | No |
| **Pattern matching** | Built-in (regex + timeout) | Manual (poll + grep) |
| **Blocks serial port** | Yes (one session per slot) | No |
| **Multiple devices** | One slot at a time | All devices simultaneously |
| **Long-running** | Limited by timeout | Continuous (buffer persists) |

## Endpoints

Request and response shapes: serial in [FSD Appendix D.2](../../../docs/Embedded-Workbench-FSD.md#d2-serial-management),
UDP log in [D.7](../../../docs/Embedded-Workbench-FSD.md#d7-udp-log), the portal's own activity log in
[D.14](../../../docs/Embedded-Workbench-FSD.md#d14-activity-log).

Three different logs, and picking the wrong one wastes a test run: `/api/serial/*`
is what the device printed over USB, `/api/udplog` is what it sent over the
network, and `/api/log` is what the *portal* did — never device output.

## Serial Monitor

Reads serial output via RFC2217 proxy. Optionally waits for a regex pattern.

```bash
# Wait up to 10s for a pattern match
curl -X POST $WORKBENCH_URL/api/serial/monitor \
  -H 'Content-Type: application/json' \
  -d '{"slot": "SLOT1", "pattern": "WiFi connected", "timeout": 10}'

# Just capture output for 5s (no pattern)
curl -X POST $WORKBENCH_URL/api/serial/monitor \
  -H 'Content-Type: application/json' \
  -d '{"slot": "SLOT1", "timeout": 5}'
```

Response: `{"ok": true, "matched": true, "line": "WiFi connected to MyAP", "output": [...]}`

### A debug session silently changes what reset returns

`POST /api/serial/reset` picks its method from the slot. With no debug session it
pulses DTR/RTS and returns the boot log as **a list of lines**. With OpenOCD
attached it issues a JTAG `reset run` instead and returns **a single string** of
OpenOCD's reply — `JTAG tap: esp32c3.tap0 ...` — which is not the device's output
at all. Same endpoint, same request, two response shapes and two meanings.

Nothing in the response announces this except a `"method": "jtag"` key that is
absent on the serial path. Client code that iterates `output` gets characters
instead of lines and quietly finds no boot markers.

**OpenOCD attaches by itself when a device is plugged in**, so this is the
default state of a board on a JTAG-capable slot, not something you opted into.
Stop it before capturing boot output:

```bash
curl -X POST $WORKBENCH_URL/api/debug/stop \
  -H 'Content-Type: application/json' -d '{"slot": "SLOT3"}'
```

Check first with `debugging` in `/api/devices` — a slot reads `idle` either way.

**Serial is the lifeline.** Never decide whether a device is alive by pinging it
or calling its HTTP endpoint — a device that boots fine but never joins WiFi
looks identical to a dead one. Reading what it printed tells you which.
Boot-marker patterns for running / download-mode / unknown are in
[`references/state-detection.md`](references/state-detection.md).

### Use serial monitor when:
- You need **boot messages** (before WiFi is up)
- You need to **wait for a specific log line** (pattern matching with timeout)
- Device has **no WiFi** or UDP logging is not compiled in
- You want **crash/panic output** from the UART

### Dual-USB hub boards
- **Reset** via the JTAG slot (triggers DTR/RTS auto-download circuit)
- **Monitor** via the UART slot (where ESP_LOGI output appears)
- Boot output on the JTAG slot will be empty or minimal — the actual boot log appears on the UART slot

```bash
# Reset via JTAG slot
curl -X POST $WORKBENCH_URL/api/serial/reset \
  -H 'Content-Type: application/json' \
  -d '{"slot": "<JTAG-slot>"}'

# Capture boot output from UART slot
curl -X POST $WORKBENCH_URL/api/serial/monitor \
  -H 'Content-Type: application/json' \
  -d '{"slot": "<UART-slot>", "timeout": 10}'
```

## UDP Logs

ESP32 firmware sends debug logs as UDP datagrams to the workbench on port 5555. The workbench buffers up to 2000 lines.

```bash
# Get recent UDP logs (default limit: 200)
curl -s $WORKBENCH_URL/api/udplog | jq .

# Filter by source device IP
curl -s "$WORKBENCH_URL/api/udplog?source=192.168.4.2" | jq .

# Get logs since a timestamp, limited to 50 lines
curl -s "$WORKBENCH_URL/api/udplog?since=1700000000.0&limit=50" | jq .

# Clear the buffer before starting a test
curl -X DELETE $WORKBENCH_URL/api/udplog
```

Response format: `{"ok": true, "lines": [{"ts": 1700000001.23, "source": "192.168.4.2", "line": "OTA progress: 45%"}, ...]}`

### Use UDP logs when:
- Device is **on WiFi** and firmware sends UDP log packets
- You want **non-blocking** log collection (doesn't tie up the serial port)
- You're monitoring **multiple devices** simultaneously (filter by source IP)
- You need logs during **OTA updates** (serial may be unavailable)

### Do NOT use UDP logs when:
- Device has **no WiFi** yet (pre-provisioning, boot phase) — use serial monitor
- Firmware **doesn't include UDP logging** — use serial monitor
- You need **boot/crash output** — only serial captures UART output from early boot
- You need to **wait for a specific pattern** with a timeout — serial monitor has built-in pattern matching

## How ESP32 Sends UDP Logs

The workbench listens on UDP port **5555**. ESP32 firmware sends plain text lines:

```c
/* inet_aton() parses dotted-quad only — it does NOT resolve names, and on
   failure it leaves the address at 0.0.0.0, so the logs vanish silently.
   Always check the return value. */
struct sockaddr_in workbench = { .sin_family = AF_INET, .sin_port = htons(5555) };
if (inet_aton(CONFIG_WORKBENCH_IP, &workbench.sin_addr) == 0) {   /* dotted-quad */
    ESP_LOGE(TAG, "bad workbench address");
    return ESP_ERR_INVALID_ARG;
}
sendto(sock, msg, strlen(msg), 0, (struct sockaddr *)&workbench, sizeof(workbench));
```

To use a **name** instead of an IP, resolve it first —
`inet_aton` will not do it for you:

```c
struct addrinfo hints = { .ai_family = AF_INET, .ai_socktype = SOCK_DGRAM };
struct addrinfo *res;
if (getaddrinfo("workbench", "5555", &hints, &res) == 0) {
    sendto(sock, msg, strlen(msg), 0, res->ai_addr, res->ai_addrlen);
    freeaddrinfo(res);
}
```

Resolving the `.local` form needs mDNS, which is **not** bundled in ESP-IDF 6 —
add the `espressif/mdns` managed component if you want it. Passing an IP literal
avoids the dependency entirely, which is why the test firmware does that.

## Activity Log

The activity log tracks workbench actions (resets, WiFi changes, firmware uploads) — not device output.

```bash
curl -s $WORKBENCH_URL/api/log | jq .
curl -s "$WORKBENCH_URL/api/log?since=2025-01-01T00:00:00Z" | jq .
```

## Common Workflows

1. **Verify boot after flash:**
   - `POST /api/serial/reset` — returns boot output, **but only with debug stopped** (see below)
   - Check for expected boot messages (e.g., `boot:0x28`, firmware version)

2. **Wait for WiFi connection:**
   - `POST /api/serial/monitor` with `pattern: "WiFi connected"` and `timeout: 15`

3. **Monitor OTA progress:**
   - `DELETE /api/udplog` — clear buffer
   - Trigger OTA (see esp-idf-handling)
   - Poll: `GET /api/udplog?since=<last_ts>&limit=50`

4. **Debug a running device:**
   - `GET /api/udplog?source=<device_ip>` — see what it's logging
   - If empty, device may not have UDP logging — fall back to serial monitor

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Monitor timeout, no output | Baud rate is fixed at 115200; ensure device matches. For dual-USB boards: make sure you're monitoring the UART slot, not the JTAG slot |
| No UDP logs appearing | Ensure firmware sends UDP to workbench IP:5555; check WiFi connectivity |
| Logs from wrong device | Use `source` query param to filter by IP |
| Old/stale logs | Clear with `DELETE /api/udplog` before starting a test |
| Need boot output | UDP logs don't capture boot — use serial monitor. For dual-USB boards, monitor the UART slot |
| Slot shows `monitoring` | Another monitor session is active — wait for it to finish |
