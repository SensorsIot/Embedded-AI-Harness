---
name: workbench-test-handling
description: Use this skill when running or writing automated tests against the workbench — the three-phase execution protocol every test case follows, live progress on the Pi's web UI, blocking prompts for physical operator actions (button press, cable swap, power cycle), the WorkbenchDriver Python API, and activity log queries. Use it for authoring a pytest suite as well as for tracking a manual run. For driving one instrument, use that instrument's skill instead. Triggers on "test progress", "test session", "test spec", "test case", "test harness", "run the tests", "write a test", "WorkbenchDriver", "human interaction", "operator", "activity log", "test panel".
---

# ESP32 Test Automation

Base URL: `http://workbench.local:8080`

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

## Step 0: Discover Workbench

Before using any workbench API, ensure `workbench.local` resolves:

```bash
curl -s http://workbench.local:8080/api/info
```

If that fails, run the discovery script from the workbench repo:

```bash
sudo python3 .claude/skills/esp-idf-handling/discover-workbench.py --hosts
```

## Test Progress Tracking

Test scripts can push live progress updates to the workbench web UI so operators can monitor test execution without a terminal.

### Endpoints

Request and response shapes: [FSD Appendix D.13](../../../docs/Embedded-Workbench-FSD.md#d13-test-progress--human-interaction).

### Session Lifecycle

```bash
# 1. Start a test session
curl -X POST http://workbench.local:8080/api/test/update \
  -H 'Content-Type: application/json' \
  -d '{"spec": "<test-spec> v1.0", "phase": "Phase 1", "total": 8}'

# 2. Update current test step
curl -X POST http://workbench.local:8080/api/test/update \
  -H 'Content-Type: application/json' \
  -d '{"current": {"id": "TC-001", "name": "WiFi Provisioning", "step": "Joining AP...", "manual": false}}'

# 3. Record a result
curl -X POST http://workbench.local:8080/api/test/update \
  -H 'Content-Type: application/json' \
  -d '{"result": {"id": "TC-001", "name": "WiFi Provisioning", "result": "PASS"}}'

# 4. End the session
curl -X POST http://workbench.local:8080/api/test/update \
  -H 'Content-Type: application/json' \
  -d '{"end": true}'

# Poll current progress
curl http://workbench.local:8080/api/test/progress
```

### Python Driver Methods

```python
wt.test_start("<test-spec> v1.0", "Phase 1", total=8)
wt.test_step("TC-001", "WiFi Provisioning", "Joining AP...", manual=False)
wt.test_result("TC-001", "WiFi Provisioning", "PASS")
wt.test_end()
```

## WorkbenchDriver

**Inside this repo's suite there is nothing to set up** — `pytest/conftest.py`
provides a session-scoped `workbench` fixture. Take it as an argument:

```python
def test_boots_clean(workbench):
    workbench.serial_reset("SLOT1")
```

From a standalone script, put the workbench repo's `pytest/` on the path — the
repo's own location, not a copy under `/tmp`:

```python
import sys
sys.path.insert(0, "<workbench-repo>/pytest")
from workbench_driver import WorkbenchDriver
wt = WorkbenchDriver("http://workbench.local:8080")
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
is `pytest/workbench_driver.py`.

## Human Interaction

Some test steps require physical actions that cannot be automated — pressing a button, connecting a cable, power-cycling a device. The human interaction endpoint lets test scripts block until an operator confirms the action via the web UI.

### Endpoints

Request and response shapes: [FSD Appendix D.13](../../../docs/Embedded-Workbench-FSD.md#d13-test-progress--human-interaction).

`/api/human-interaction` **blocks the caller** until Done, Cancel or timeout — so
give it a timeout shorter than the client's own, or the client gives up first and
leaves the modal on screen with nothing waiting for it.

### Examples

```bash
# Request operator action (blocks until Done/Cancel/timeout)
curl -X POST http://workbench.local:8080/api/human-interaction \
  -H 'Content-Type: application/json' \
  -d '{"message": "Connect USB cable to port 2 and click Done", "timeout": 120}'

# Check if a request is pending
curl http://workbench.local:8080/api/human/status

# Operator confirms
curl -X POST http://workbench.local:8080/api/human/done

# Operator cancels
curl -X POST http://workbench.local:8080/api/human/cancel
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

Timestamped log of all workbench operations — hotplug events, WiFi operations, enter-portal steps, human interactions.

### Endpoints

Request and response shapes: [FSD Appendix D.14](../../../docs/Embedded-Workbench-FSD.md#d14-activity-log).

```bash
# Get all entries
curl -s http://workbench.local:8080/api/log | jq .

# Get entries since a timestamp
curl -s "http://workbench.local:8080/api/log?since=2025-01-01T00:00:00Z" | jq .
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

3. **Monitor workbench operations:**
   - `GET /api/log?since=<ts>` — poll for new activity entries
   - Useful for debugging enter-portal sequences and tracking what happened

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Human interaction returns 409 | Another request is pending — wait or cancel it |
| Test progress not showing in UI | Ensure a session was started with `spec`, `phase`, `total` |
| Activity log empty | No operations have been performed yet |
