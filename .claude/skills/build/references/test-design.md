# Test design

The Method skill owns test design end to end — there is no separate
test-specification skill or layer.

It designs and documents tests. It does **not** implement them, run them, or
operate hardware — see the dispatch table in `../SKILL.md` §2.

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
  tier: <see test-architecture.md SS3>
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

**`test-architecture.md` §3 owns the tier taxonomy** — what each tier is, how
they are named per platform, why the full-system tier is defined by control
rather than realism, and why the deployed tier is optional. It is not restated
here: a tier list in two files is a tier list that will disagree, and this one
did.

What belongs to *design* rather than architecture is the choice for a given
clause. Two rules:

**Assign each behaviour to the lowest tier where the defect can occur and the
behaviour can be both controlled and observed.**

**Difficulty changes the tier or demands a test seam — it never justifies dropping
a failure mode.** If a clause's natural tier is uncontrollable, add a seam and
relocate the test downward. The full-system tier is for behaviour that genuinely
needs real peers to manifest, not a bin for inconvenient cases.

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

## 5. What to build, and in what order

### Open with a discussion, not a test

Test design begins with two questions put to the user, in this order. Neither is
answerable from the FSD, and getting them wrong costs days rather than minutes.

**First: what has to be debugged before anything is tested?**

Ask which parts of the system are not yet known to work at all — not "which are
unfinished", but *which have never been observed doing their job*. A new board's
wiring. A protocol nobody has spoken to the real peer. A rig that has never
delivered a complete message. A library integrated but never exercised on the
target.

Go through the system with the user and produce a short agenda:

```text
part                    unproven because            proven by
meter UART              never driven on this board  a known pattern arrives intact
M-Bus simulator         new to the bench            it emits a whole telegram
broker path             device has never published  a message reaches the broker
```

That agenda is **debugging work, not test cases.** It gets done, it gets
discussed, and it produces measurements that belong in the rig's notes — none of
it enters the plan. The point is to reach a state where a failing test means
something, because until each of those parts is known to work, every test result
is unattributable and the suite is measuring the environment.

Do not skip this because the code compiles or because a component is
well-regarded. The question is not whether it is good; it is whether *this*
instance of it has been seen working *here*.

### The second question: the standard run, before writing anything

**What does one ordinary, successful use of this system look like, end to
end?**

Ask the user. It cannot be derived from the FSD, and that is the whole problem —
the FSD says what must be *true*, clause by clause, and never what a normal run
*is*. Nothing in a requirements document describes the journey, so a suite built
faithfully from one covers every clause and never once checks the product works.

Get it as an ordered list of steps with an observable at each. A real answer:

```text
1  captive portal, enter credentials     the form accepts them
2  device joins the access point         association succeeds
3  device connects to the broker         a session is established
4  the meter sends a normal telegram     values decode
5  values arrive at the broker           a live message, twice
```

Then write **one test per step**, each asserting its own checkpoint. Separately,
because they fail for different reasons and the difference is what says where to
look — step 4 failing is a decoder problem, step 5 failing with step 4 passing is
a topic or a session problem, and a single end-to-end test that only says "no
data arrived" distinguishes neither.

This phase is the **gate**: while it fails, every later test is unreadable,
because they all fail for the same upstream reason and the report reads as a
dozen defects instead of one.

**The cheap tier is exempt from all of this.** Host tests run in full, every
time, in whatever order — they cost milliseconds, so selecting among them buys
nothing and risks running a subset that hides the one failure that mattered.
Ordering, gating and phasing are disciplines for runs that cost minutes. Run
every host test before every hardware session, and treat a red one as a reason
not to start the session at all.

### Bring-up may come first — that is a judgement call

Where the system meets hardware nobody has exercised yet, the standard run is
not the first thing to attempt. **A bring-up test answers "is this connected the
way we think it is?"** — the pin is wired, the polarity is right, the parity
matches, bytes arrive at all — and it is far cheaper to answer directly than to
infer from a journey that fails five steps later for a reason that turns out to
be an inverted line.

Decide this at the start of test design, and decide it explicitly:

| Reach for bring-up when | Skip it when |
|---|---|
| A physical interface has never been driven | The system is software over settled transports |
| The wiring or polarity is unconfirmed | The hardware is a known-good rig |
| A previous session's result was unattributable | The last run reached the end of the journey |

Keep it small and keep it honest about what it proves. A pattern that cannot
survive the error you are hunting is the right stimulus: a continuous `0x55`
alternates every bit, so an inverted line turns it into a uniform `0xD5` rather
than into noise that looks like data. Reading back the pad configuration after
boot is the same idea one layer down.

**Most bring-up work is not a test case at all — it is a debugging aid, and it
must not enter the plan.** The question that separates them:

> Does it discharge a requirement, or does it interrogate the rig?

A check that drives a known pattern and asserts the device receives it intact
discharges a requirement about the device's line configuration, and is a test.
A sweep that varies a *simulator* setting to see what the board happens to
receive answers "what does this rig do" — it is a measurement, it can fail in no
way that matters, and counting it inflates the plan with an entry no requirement
asked for.

Keep the measurement; put it on the **capability**, where a rig's properties
belong, not on a test ID. On one project a preamble sweep was promoted to a test
case and had to be withdrawn: the number it produced was genuinely useful and
belonged in the rig's notes, while the test entry claimed coverage of a
requirement it never checked.

The bring-up work that *is* a test case is `standard` in kind — not a fifth bin,
just the first standard tests, ordered ahead of the journey because the journey
cannot be read without them.

### The four kinds, gated in three waves

Every test declares its kind, and the kinds are **gated, not merely ordered**:
tests exist to pull the prototype forward, so each wave is locked until the
one before it is green.

| Kind | Is |
|---|---|
| **standard** | The ordinary case — the product doing its job |
| **deviation** | Still normal, just not the simplest case |
| **negative** | A fault or malfunction is injected |
| **security** | Derived from the threat profile, not from a feature |

| Wave | Builds | Tests written | Gate to enter — derived, never declared |
|---|---|---|---|
| **1 · Build the running prototype** | The features | `standard` only | Testbench trusted |
| **2 · Cover the normal variants** | Breadth of normal life | `deviation` | Journey green **and** every standard test green — *the prototype runs* |
| **3 · Build the error handling** | Fault and abuse behaviour | `negative` + adversarial `security` | All standard **and** deviation tests green |

**The gates lock authoring, not just execution.** During Wave 1 a deviation or
negative test is not merely skipped — it is **not written**: an unwritten test
cannot turn red as noise, cannot rot against a still-moving interface, and does
not bloat the plan. One exception: a later-wave test that needs a *capability
or seam* is **declared** (never implemented) as soon as it is known — equipment
and seams have lead time, and discovering "we need a clock-set command" in
Wave 3 is too late.

**The cheap tier runs in full, always — but its authoring is wave-locked too.**
One principled escape: when the contract makes a limit part of the standard
path (a parser that must reject over-length input to parse correctly at all),
that rejection is Wave 1 — the standard path is meaningless without it.
Everything else — DST days, empty sets, malformed frames — waits for its wave
even on the host tier.

**Security is built in Wave 1 and attacked in Wave 3.** Security
*functionality* the threat profile demands — the ordinary connection is TLS,
provisioning requires auth — is part of the standard path: the prototype is
born secure or it is not a prototype of the product. *Attack resistance* —
malformed packets, replay, downgrade, credential extraction — is Wave 3,
mechanically the same bin as error handling. Tests keep the `security` kind
tag so the threat profile's coverage stays auditable as its own list; there is
no security wave.

**Keep the volume tilted towards the first two kinds.** A suite heavy on
negatives has never checked the product works. Negatives accumulate one at a
time, each individually justified, and nobody notices the ordinary case is
missing — the wave gates exist precisely to make that impossible.

Measured on one project: 108 declared tests, and the standard end-to-end journey
was still unwritten. The bench suite ran corrupted checksums, silent lines, noise
injection and no-download-without-a-command against a device whose ordinary path
had never been checked — and a defect that stopped it publishing *entirely* was
found sideways, when unrelated update tests could not read the device's topic
name. The balance there was 46 / 17 / 27 / 8, and the deviation bin was the
thinnest when it should be among the fattest: "still normal, just not the
simplest case" is where real deployments live.

**A deviation is not a malfunction.** Two valid serial lengths are two normal
configurations. Waking mid-transmission is what happens on every power-up when
the device is energised by the thing it reads. Filing those under faults is part
of how the ordinary case goes untested — the bin looks full while nothing in it
tests normal operation.

### Then, per clause

Once the standard run and its variations exist, derive per clause every class
that applies — **each carries its kind, and its kind decides its wave**: the
minimum-enforcement list below defines what *fully verified* means by the end
of Wave 3, not what Wave 1 writes.

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

Per-clause coverage is necessary and not sufficient. It is the step that reaches
100% of requirements while leaving the product untested, because no clause
describes the journey.

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

---

## 8. Test seams are a handoff, not a workaround

Some clauses cannot be observed unless the implementation exposes something: a
console command listing which tasks are watchdog-subscribed, a hook to see what
reaches a decoder's input.

Name the seam on the test that needs it. It is an obligation on development,
discovered at design time rather than when someone sits down to write the test
and finds they cannot. The alternative is worse than it looks — without the seam
the clause gets quietly weakened to whatever happens to be observable, and
nobody records that the claim shrank.

---

Designing tests is half the job. Running them, tracking what they produced and
reporting the gaps is `test-lifecycle.md`.
