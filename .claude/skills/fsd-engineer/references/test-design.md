# Test design

This skill owns test design end to end. It does not delegate to another
test-planning model in §9.

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

**Second: what does one ordinary successful run look like, end to end?**

### Ask for the standard run before writing anything

**The second question: what does one ordinary, successful use of this system
look like, end to end?**

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

### The four kinds

Every test declares which it is, and the balance is a design property to watch
rather than an accident.

| Kind | Is | Build |
|---|---|---|
| **standard** | The ordinary case — the product doing its job | first |
| **deviation** | Still normal, just not the simplest case | second |
| **negative** | A fault or malfunction is injected | third, and only the ones that matter |
| **security** | Derived from the threat profile, not from a feature | alongside, from §6.5.1 |

**Keep the volume tilted towards the first two.** A suite heavy on negatives has
never checked the product works. Negatives accumulate one at a time, each
individually justified, and nobody notices the ordinary case is missing.

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
that applies:

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

## 9. Sequence — what to write when, and how to lead the user through it

```
ask for the standard run  →  requirement + contract  →  test declared
                          →  executable test (xfail)  →  code  →  run
                          →  record  →  report
```

**The ask comes first and happens once**, before any test is declared — §5. It
is the one input the FSD cannot supply, and everything else is ordered around
it: the standard run becomes the first tests written and the gate the rest run
behind.

**This runs per requirement, not as project phases.** One requirement walks the
whole chain before the next one starts. Writing every contract, then every
declaration, then all the code is the same order on paper and a different project
in practice: the plan reads finished while nothing is verified, and the
declarations were never tested against a real interface, so a fraction of them
turn out to be undeliverable at once.

Batch only the first step, and only to find the shape of the work.

**The contract is written with the requirement, before any code.** Attempting it
*is* the quality gate: a requirement whose stimulus cannot be stated is not
finished.

**The test is declared next, still before code** — id, tier, equipment, what it
does, what it expects. Cheap, and it surfaces two things nothing else does:
equipment that does not exist, and **interfaces nobody has decided**. A clause
saying a counter is "available on the serial console" cannot be declared without
deciding the command, and that is a specification gap caught before it becomes an
implementation guess.

**The executable test is written before or alongside the code — never after.**

> A test written after the code is a description of the code, not a check on it.
> It will assert what the implementation happens to do, including the bug.

Writing it first also validates the contract. In practice a contract demanding
"a complete set is published" after a mid-burst start proved unsatisfiable — the
identity is sent once per telegram and cannot be recovered from a cycle that
began after it passed. The test corrected the specification within minutes.

**Mark tests for unimplemented features expected-to-fail** — `WILL_FAIL` in
CTest, `xfail` in pytest. This is what makes test-first survivable: the suite
stays green so a real regression is still visible, the test exists rather than
living in someone's intent, and **xfail reports XPASS when it unexpectedly
passes** — the day the feature lands the test announces itself.

A permanently red suite is worse than no suite. People stop reading it, and the
one real failure hides among the twenty expected ones.

The only step that may legitimately wait for code is the executable test, and
only when the interface it drives has not been decided. Then the missing decision
is the deliverable, not the test.

### Say where the project is, unprompted

The user should never have to ask what comes next. Open every session by locating
the project on the chain and naming the next act:

| What exists | Position | The next act |
|---|---|---|
| a description, no requirements | before the chain | grill it, then write requirements with contracts |
| requirements without contracts | contract step | write the contracts — expect this to rewrite requirements, that is the gate working |
| contracts, no declared tests | declaration step | declare them; report the equipment that turns out not to exist and the interfaces nobody has decided |
| declared tests, none executable | executable step | write them, xfail where the feature is absent |
| executable tests, feature absent | code step | hand off to development; the XPASS is the landing signal |
| **code with no tests** | off the chain | the retrofit below |

If the answer is "several at once", say which requirement is at which position
rather than averaging them. An average hides the one requirement that has nothing.

### When the code already exists

Most projects arrive here, and the honest position is that the order cannot be
replayed. What can be done is to remove the specific harm it causes.

- **Write the test from the contract with the implementation closed.** If you
  cannot state the assertion without reading the code, the contract is incomplete
  — fixing the contract is the finding, and it is worth more than the test.
- **Then prove the test can fail.** Break the code deliberately — invert a
  comparison, stub a return — watch it go red, restore. A test that has only ever
  been green is a claim, not a check, and this is the only way to tell the two
  apart after the fact.

Neither step is optional busywork. A retrofitted suite that skips them reliably
encodes the defects it was written to catch.

---

## 10. Test status, and what a requirement being met means

Two levels, never collapsed into one `covered` flag.

**A test** has exactly three statuses, written by whatever ran it and never by
hand, carrying the commit so staleness is visible rather than assumed:

```text
not done      no result — see the reason, which is the important part
successful    it ran and passed, including its prohibited-outcome check
failed        it ran and did not
```

`not done` covers four different problems and must say which, because they need
different people:

| Reason | Who resolves it |
|---|---|
| test not written | the backlog |
| the feature is not implemented | development |
| needs *capability* — unavailable | whoever builds the rig |
| precondition unmet | fix that first; the result would mean nothing |

**A failed precondition is `not done`, not `failed`.** Recording a failure claims
you learned something about the requirement; with a broken baseline you learned
nothing, and it sends the next person hunting the wrong defect.

**Never predict.** A test you are confident is about to fail still reads
`not done` until it runs. Once predictions are allowed into that column it stops
being evidence.

**A requirement is met** when every test that verifies it is successful —
including the check that its *must not* did not happen. That is a derived answer,
not a stored one, and the honest reply is usually "no": it has two tests, one
passes and one is blocked on equipment that does not exist.

### Blocked is computed, never typed

Declare the equipment once; let each test list what it `needs`. A test needing an
unavailable capability then renders as blocked, with the reason, without anyone
writing it down:

```yaml
capabilities:
  wifi-ap-outage:
    what:      Stopping and restarting the access point on demand
    available: no
```

This is where the model earns its keep. On one project a safety requirement
rendered as *"needs button-gpio, ota-relay"* — because observing it required
states the rig could not reach — a fact no review had found.

Record **rig limitations on the capability, with their consequence**. "The
simulator is unstable" is a note; *"two bursts in six arrive clean, so assert
across several cycles and require one good one"* changes how tests get written.

### Reconcile the plan against the code, both directions

Two lists, both of which must end empty:

- declared in the plan, absent from the code → the backlog
- **implemented, absent from the plan** → a test verifying something nobody wrote
  down, or a duplicate about to be written for a requirement already covered

The second is the one people forget, and it silently produces duplicate work.

### What the artefacts actually prove

| Artefact | Proves | Does **not** prove |
|----------|--------|--------------------|
| `@fsd` tag | This source location *claims* responsibility for this clause | That the mapping is correct, that the code ran, or that anything asserted the outcome |
| Coverage data | These lines executed during some run | That the behaviour was correct, or which test exercised them |
| A passing test | The assertions it contains held | Anything about assertions it does not contain — notably prohibited outcomes |

Aggregate coverage cannot attribute a line to a test. Per-test attribution needs
per-test coverage contexts or separate execution runs; without one of those, do
not claim it.

---

## 11. Gap reports — four categories, not one list

A single undifferentiated gap list hides the fact that these need different
people to resolve them.

### 11.1 Specification defects
compound requirement · undefined initial state · undefined resulting state ·
missing timeout or tolerance · ambiguous term · missing failure behaviour ·
conflicting requirements · unverifiable observation · uncontrollable stimulus ·
missing security assumption · unsupported regulatory claim · missing
configuration rule

### 11.2 Verification gaps
approved requirement without a test specification · normative state transition
without a test · numeric boundary without a boundary test · rejection rule
without a negative test · test lacking evidence criteria · test lacking cleanup ·
test infeasible with available equipment

### 11.3 Implementation gaps
approved requirement without implementation mapping · implementation mapping
without an approved requirement · executable test absent · production behaviour
detected but undocumented · obsolete implementation after a requirement change

**Source without clause** (the backward arrow) forces a choice the developer must
make, not the skill: *add a clause to the FSD* (behaviour exists but is
undocumented) or *delete the code* (orphaned implementation).

### 11.4 Execution and evidence gaps
executable test never run · result not tied to a commit · missing raw evidence ·
stale evidence after a requirement or implementation change · test passed but
prohibited outcomes were never checked · coverage present without behavioural
assertions

### Also listed, so they are not mistaken for gaps
clauses marked `pending: true` (the FSD itself is unresolved) and
`testability: philosophical` (no rig can decide them).

**The skill proposes resolutions. It does not silently decide product questions.**

---

---

Traceability is the join between requirement ids in the FSD and the tests in the
plan that reference them, computed by the report. There is no separate matrix to
maintain, no `@fsd` tag to keep in step, and no evidence directory: the plan entry
carries the commit its result came from, which is what makes staleness visible.

A heavier project may want source tags and a retained evidence archive. Both are
additions to this model, not parts of it, and both cost a synchronisation problem
in exchange for provenance the plan already approximates.
