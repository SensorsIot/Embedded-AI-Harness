# Test design

This skill owns test design end to end. It does not delegate to another
test-specification skill.

It designs and documents tests. It does **not** implement them, run them, or
operate hardware — see the responsibility table in `SKILL.md`.

---

## 1. Clause inventory

Walk every FSD chapter. Extract **atomic clauses** — one per decision point or
promise. Skip narrative prose. Assign stable IDs: `FSD-<section>-<short-slug>`.

A clause promising several things is split with suffixed IDs:

```text
FSD-5.2-403-status   "Provisioning returns HTTP 403"
FSD-5.2-403-led      "LED set to red+green alternating on 403"
FSD-5.2-403-retry    "Retry every 60 s after 403"
```

Record per clause:

```yaml
- id: FSD-5.2-403-led
  text: "LED set to red+green alternating on 403"
  source_section: "§5.2"
  tier: host | target | bench
  testability: testable | philosophical
  kind: positive | negative | boundary | state-transition | error
  pending: false        # true when the clause itself is TBD in the FSD
```

- **philosophical** — a promise no rig can decide ("secure by design"). No test is
  written; it is flagged in the gap report. Do not pretend otherwise.
- **pending** — the FSD itself is unresolved here. No tests; revisit when the
  open decision closes.

Save to `<output_root>/clauses.yaml`.

---

## 2. Verification tiers

Assign each test to the **lowest tier** where the defect can occur and the
behaviour can be both controlled and observed.

| Tier | Runs on | Catches |
|------|---------|---------|
| **host** | Dev machine, no hardware | Pure logic: parsing, encoding, validation, math, state calculations |
| **target** | The MCU or a faithful target environment | NVS, RTOS interaction, target timing, watchdog and reset behaviour |
| **bench** | Real physical interfaces and peers | WiFi environment, broker interruption, RF, GPIO, power, real peer interaction |

**Difficulty changes the tier or demands a test seam — it never justifies dropping
a failure mode.** If a clause's natural tier is uncontrollable, add a seam and
relocate the test downward. `bench` is for behaviour that genuinely needs real
hardware to manifest, not a bin for inconvenient cases.

---

## 3. Controllability

The tier follows from whether the condition can be **created** and the result
**observed**, per external device:

- **Drive** — command the real peer through its normal interface (publish,
  request, write). The clause can sit wherever that channel runs.
- **Feed** — the peer cannot be commanded, so supply its *inbound* data through a
  deliberate test seam (synthesized input on host, a fake-data build flag on
  target). Most "we reject / handle a bad X" failure modes are Feed.
- **Emulate** — substitute a fake device outside the system under test.
- **Observe** — real, uncommandable peer: watch-only validation, no provocation.
- **Rig** — the test infrastructure creates the condition: link loss, reboot,
  reset, power cycle, RF injection.

Application-logic clauses own no device; they inherit the controllability of the
interfaces they orchestrate.

---

## 4. Observability

For each expected behaviour, name how it will be observed: returned value · state
query · log · network message · broker event · GPIO level · debugger · reset
reason · timing measurement · SDR result · external application state.

**A log line alone is not accepted when stronger end-to-end evidence is
available.** A device that logs "connected" while never publishing has passed the
log test and failed the requirement.

---

## 5. Required test classes

For each applicable clause, derive every class that applies:

positive · negative/rejection · lower and upper boundary · invalid-format ·
error-handling · state-transition · persistence · recovery · timeout ·
concurrency where relevant · security where the approved profile requires it ·
performance or endurance where an NFR requires it.

Minimum enforcement:

- **≥ 1 positive test** per testable clause.
- **A negative test** for every clause with reject / deny / forbid semantics.
- **Boundary tests** at each numeric edge the spec implies (`= 0`, `= max`,
  `> max`, `< min`).
- **A state-transition test** for every normative row of every state table.

Test IDs: `TC-<area>-<nn>[-<qualifier>]`

```text
TC-PROV-04           positive
TC-PROV-04-neg       negative variant
TC-NULL-07-zero      boundary at max_export_w = 0
TC-NULL-07-over      boundary at max_export_w > RATED_W
```

---

## 6. Independence, ordering, cleanup

> Every test is independently executable and restores the system to a defined
> baseline.

Ordered tests are permitted only when the dependency is technically unavoidable,
explicit, carries a stable sequence identifier, and defines recovery after
partial execution.

Every test specifies setup, cleanup, recovery after **failure**, retained data to
clear, services to restart, and resources to release.

This matters more on a physical bench than anywhere else, because a failed test
does not merely fail — it poisons the next one. A run can leave behind:

- WiFi disabled, or the AP still up
- the MQTT broker stopped, or retained messages present
- invalid credentials stored in NVS
- the device in provisioning or download mode
- a GPIO held LOW (the DUT then cannot boot)
- a serial client still attached (RFC2217 allows one)
- the SDR dongle or the debug interface busy

Each of those is a state the *next* test will misdiagnose as a defect.

---

## 7. Test data and secrets

Define test data separately from procedure. Generate: valid values · lower and
upper boundaries · empty and missing values · overlength values · malformed
encodings · invalid addresses · unsupported enum values · stale and retained data
cases · corrupted persistence cases where feasible.

Choose values that cannot occur by chance, so a match is unambiguous and `grep`
alone decides the result.

**Secrets never appear in test specifications or committed evidence** — only
references:

```yaml
wifi_password_ref: env:WB_TEST_WIFI_PASSWORD
mqtt_password_ref: secret:workbench/mqtt-test
```
