---
name: testbench-test-handling
description: Use this skill when running or writing automated tests against the testbench — the three-phase execution protocol every test case follows, live progress on the Pi's web UI, blocking prompts for physical operator actions (button press, cable swap, power cycle), the TestbenchDriver Python API, and activity log queries. Use it for authoring a pytest suite as well as for tracking a manual run. For driving one instrument, use that instrument's skill instead. Triggers on "test progress", "test session", "test spec", "test case", "test harness", "run the tests", "write a test", "TestbenchDriver", "human interaction", "operator", "activity log", "test panel".
---

# ESP32 Test Automation

Base URL: `$TESTBENCH_URL` — see Step 0

**The portal and the MQTT broker are always-on infrastructure. A test never
starts, stops or restarts them** — doing so breaks whatever else is using the
bench, and a test that needs a restart to pass is testing the restart.

## The execution protocol

Every test case runs in three phases, and the panel shows which one is current so
the operator can follow along without a terminal.

| Phase | Panel shows | What happens |
|-------|-------------|--------------|
| **Preconditions** | `[TC-100] Preconditions: checking DUT reachable...` | Verify **and establish** each precondition from the spec. If the AP is not running, start it. Fail only when a precondition is genuinely unrecoverable. |
| **Execute** | `[TC-100] Step 2: <the step from the spec>` | Run the spec's steps one at a time, checking the expected result after each. |
| **Result** | `TC-100: PASS` / `TC-100: FAIL — <what was seen>` | Record PASS/FAIL/SKIP with the observed value, not just the verdict. |

Rules that decide whether a run is worth anything:

1. **The spec is the script.** Execute its preconditions, steps and pass criteria
   as written — not an improved version of them.
2. **Update the panel before each action**, never after. The panel is how the
   operator knows what the bench is doing to the hardware right now.
3. **Record baselines.** Where the spec says "record X as `X_before`", capture it
   and compare in the result phase.
4. **Generate test credentials per run.** A random SSID and password for the test
   AP proves the DUT used what it was provisioned with, rather than a network it
   had already cached.
5. **Write the results out.** A markdown file with test ID, name, result, details
   and timestamps — the panel is live state, not a record.

Workflows that span several instruments — provision, reboot, re-provision, soak —
are in [`references/common-workflows.md`](references/common-workflows.md).

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

## Step 0.5: Reach the DUT through the API, never through raw RFC2217

The slots expose RFC2217 ports, and it is tempting to open one with pyserial
and read the device directly. **Do not do this to a DUT.** Use `/api/flash`,
`/api/serial/monitor`, `/api/serial/reset` and `/api/chip/info`, which
implement each chip's sequences correctly.

The reason is that **serial control lines are not inert on modern parts**. On
an ESP32-C3, -S3 or any native-USB device, the USB-Serial/JTAG controller
reads them as boot-mode signals: **DTR asserted selects download mode, RTS
asserted holds the part in reset**. pyserial asserts both on open by default,
and the Linux CDC-ACM driver asserts them too. So merely *connecting to look
at* a DUT can stop it — and what you then observe is your own connection, not
the firmware.

That failure is vicious because it is silent and it is self-confirming: the
device prints nothing, which reads as a crash or a hang; a reset appears to
fix it; and repeating the observation reproduces the silence, which feels like
evidence. On a UART-bridge part (CP2102, CH340) the same lines usually drive
an auto-reset circuit, so the effect is a restart rather than a halt — quieter
still, because the device looks alive.

**To write to a device, use `POST /api/serial/write`** (FR-030). It takes
`text` or `hex`, opens nothing, and disturbs no control line.

**The bench's own DUT answers.** `test-firmware/` gives the bench a device
that talks back, so a write can be *proved* to have arrived rather than
assumed. One line in, one line out, no echo and no prompt:

| Command | Reply | Use |
|---|---|---|
| `ping` | `OK pong` | the write reached the device |
| `status` | `OK status wifi=… ap_mode=… ip=… mac=…` | what the DUT thinks its network is |
| `scan` | `OK scan <n>`, then `<rssi> <ch> <auth> <ssid>` per line | **what the DUT's own radio can hear** |
| `info` | `OK info project=… version=… idf=…` | which image is *actually* running |
| `mark <text>` | `OK mark <text>` | an observable on demand, without waiting for the heartbeat |
| `wifi <ssid> [pass]` | `OK wifi stored …` then reboots | provision over the wire, no radio needed |
| `forget` / `reboot` | `OK …` then reboots | back to the portal / restart |

`scan` is the one worth reaching for first when a DUT will not join. The
bench can scan and the DUT could not, so a failure to meet had only one
witness — and `NO_AP_FOUND` from the DUT reads as the DUT's fault when it
is just as often the AP that is not on the air. Two radios reporting is a
measurement; one is an assertion.

`info` settles the other recurring waste of time: after a flash, ask the
device what it is running rather than inferring it from a log tail, which
may still hold the previous image's lines. Raw RFC2217 is
now only for a peer you are driving deliberately with a protocol the API
cannot express. When you do reach for it, the control lines must be low
**before** the port opens, not after:

```python
# The order is the whole point: opening first asserts the lines.
ser = serial.serial_for_url(url, do_not_open=True)
ser.baudrate = 115200
ser.dtr = False          # DTR asserted = download mode on native USB
ser.rts = False          # RTS asserted = held in reset
ser.open()               # only now, with both lines already low
```

This is exactly what the portal's own `serial_monitor()` does, and it is why
the portal can read a device that a naive client stops dead.

**Boot-time output is observable now**, by three routes, so a missed banner is
no longer a reason to reach for raw serial:

- `GET /api/serial/output?slot=…` — a recorder runs on every present slot
  whether or not anyone is watching, so the banner is already in the buffer
  by the time you ask. `lines=N` returns the **most recent** N of a
  1000-line ring; pass `since=<ts>` to get only what arrived after a moment
  you chose. Check the entries' `ts`: a buffer whose newest line is minutes
  old is telling you the device went quiet, which is itself the observation.
  (It once returned the *oldest* N, so a slot that had been up a while
  always answered with ancient history whose newest timestamp aged
  steadily — indistinguishable from a dead recorder. If you are reading an
  older bench and the tail never advances, that is the bug, not the device.)
- **the reset's own reply.** `POST /api/serial/reset` captures the boot while
  it performs it and returns those lines in `output` — the simplest route,
  and the one to reach for first.
- **the read-only fan-out**, `tcp_port + 1000` — a plain TCP stream of the
  same bytes, as many readers as you like, no control lines and no
  competition with the proxy's own client. Use it to watch a device that is
  already running. **Do not connect to it and then trigger a reset or a
  flash**: both stop and restart the proxy, so the socket dies and the
  capture comes back empty — which reads exactly like a silent device. The
  exception is a slot with a live debug session, where reset goes over JTAG
  and the proxy stays up.

Reset is not guaranteed to take on every part. If a device keeps counting
uptime across a `/api/serial/reset`, it did not reboot — check before
concluding anything about what it printed. And after a flash the recorder's
buffer starts again with the new proxy, so an old newest-line timestamp
there means the proxy was replaced, not that the device went quiet.

## Test Progress Tracking

Test scripts can push live progress updates to the testbench web UI so operators can monitor test execution without a terminal.

### Endpoints

Request and response shapes: [FSD Appendix D.13](../../../docs/Harness-FSD.md#d13-test-progress--human-interaction).

### Session Lifecycle

```bash
# 1. Start a test session
curl -X POST $TESTBENCH_URL/api/test/update \
  -H 'Content-Type: application/json' \
  -d '{"spec": "<test-spec> v1.0", "phase": "Phase 1", "total": 8}'

# 2. Update current test step
curl -X POST $TESTBENCH_URL/api/test/update \
  -H 'Content-Type: application/json' \
  -d '{"current": {"id": "TC-001", "name": "WiFi Provisioning", "step": "Joining AP...", "manual": false}}'

# 3. Record a result
curl -X POST $TESTBENCH_URL/api/test/update \
  -H 'Content-Type: application/json' \
  -d '{"result": {"id": "TC-001", "name": "WiFi Provisioning", "result": "PASS"}}'

# 4. End the session
curl -X POST $TESTBENCH_URL/api/test/update \
  -H 'Content-Type: application/json' \
  -d '{"end": true}'

# Poll current progress
curl $TESTBENCH_URL/api/test/progress
```

### Python Driver Methods

```python
wt.test_start("<test-spec> v1.0", "Phase 1", total=8)
wt.test_step("TC-001", "WiFi Provisioning", "Joining AP...", manual=False)
wt.test_result("TC-001", "WiFi Provisioning", "PASS")
wt.test_end()
```

## TestbenchDriver

**Inside this repo's suite there is nothing to set up** — `pytest/conftest.py`
provides a session-scoped `testbench` fixture. Take it as an argument:

```python
def test_boots_clean(testbench):
    testbench.serial_reset("SLOT1")
```

From a standalone script, put the testbench repo's `pytest/` on the path — the
repo's own location, not a copy under `/tmp`:

```python
import sys
sys.path.insert(0, "<testbench-repo>/pytest")
from testbench_driver import TestbenchDriver
wt = TestbenchDriver("$TESTBENCH_URL")
```

Then discover the slot rather than hard-coding one, because labels move with the
USB topology:

```python
dut = next(s for s in wt.get_devices() if s["present"])
SLOT = dut["label"]
```

**Use the driver when writing tests**; it gives typed responses, real error
handling and the slot `state` field. For a one-off operation at the prompt, reach
for the instrument skill and its `curl` instead — the driver is not worth an
import path. The methods worth knowing are in
[`references/driver-methods.md`](references/driver-methods.md); the full surface
is `pytest/testbench_driver.py`.

## Human Interaction

Some test steps require physical actions that cannot be automated — pressing a button, connecting a cable, power-cycling a device. The human interaction endpoint lets test scripts block until an operator confirms the action via the web UI.

### Endpoints

Request and response shapes: [FSD Appendix D.13](../../../docs/Harness-FSD.md#d13-test-progress--human-interaction).

`/api/human-interaction` **blocks the caller** until Done, Cancel or timeout — so
give it a timeout shorter than the client's own, or the client gives up first and
leaves the modal on screen with nothing waiting for it.

### Examples

```bash
# Request operator action (blocks until Done/Cancel/timeout)
curl -X POST $TESTBENCH_URL/api/human-interaction \
  -H 'Content-Type: application/json' \
  -d '{"message": "Connect USB cable to port 2 and click Done", "timeout": 120}'

# Check if a request is pending
curl $TESTBENCH_URL/api/human/status

# Operator confirms
curl -X POST $TESTBENCH_URL/api/human/done

# Operator cancels
curl -X POST $TESTBENCH_URL/api/human/cancel
```

### Responses

| Outcome | Response |
|---------|----------|
| Confirmed | `{"ok": true, "confirmed": true}` |
| Cancelled | `{"ok": true, "confirmed": false}` |
| Timeout | `{"ok": true, "confirmed": false, "timeout": true}` |

Only one request can be pending at a time. A second request while one is active returns `409 Conflict`.

### Python Driver Method

```python
wt.human_interaction("Press the reset button and click Done", timeout=60)
# Returns True if confirmed, False if cancelled or timed out
```

## Activity Log

Timestamped log of all testbench operations — hotplug events, WiFi operations, enter-portal steps, human interactions.

### Endpoints

Request and response shapes: [FSD Appendix D.14](../../../docs/Harness-FSD.md#d14-activity-log).

```bash
# Get all entries
curl -s $TESTBENCH_URL/api/log | jq .

# Get entries since a timestamp
curl -s "$TESTBENCH_URL/api/log?since=2025-01-01T00:00:00Z" | jq .
```

## Common Workflows

1. **Run automated test suite with progress tracking:**
   - `POST /api/test/update` with `spec`, `phase`, `total` — start session
   - For each test: update step → run test → record result
   - `POST /api/test/update` with `end: true` — end session
   - Operator monitors on web UI (progress bar, results with PASS/FAIL/SKIP badges)

2. **Test requiring physical action:**
   - `POST /api/human-interaction` with instruction message
   - Web UI shows pulsing orange modal with the message
   - Operator performs action, clicks Done
   - Test script continues

3. **Monitor testbench operations:**
   - `GET /api/log?since=<ts>` — poll for new activity entries
   - Useful for debugging enter-portal sequences and tracking what happened

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Human interaction returns 409 | Another request is pending — wait or cancel it |
| Test progress not showing in UI | Ensure a session was started with `spec`, `phase`, `total` |
| Activity log empty | No operations have been performed yet |
