# Test lifecycle — order, status, and gaps

The other half of `test-design.md`. That file decides *what tests to build*;
this one covers *when to build each part, what a result means, and how to report
what is missing*.

Split because they are consulted at different moments: design once per feature,
lifecycle on every run.

---

## 1. Sequence — what to write when, and how to lead the user through it

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

## 2. Test status, and what a requirement being met means

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

## 3. Gap reports — four categories, not one list

A single undifferentiated gap list hides the fact that these need different
people to resolve them.

### 3.1 Specification defects
compound requirement · undefined initial state · undefined resulting state ·
missing timeout or tolerance · ambiguous term · missing failure behaviour ·
conflicting requirements · unverifiable observation · uncontrollable stimulus ·
missing security assumption · unsupported regulatory claim · missing
configuration rule

### 3.2 Verification gaps
approved requirement without a test specification · normative state transition
without a test · numeric boundary without a boundary test · rejection rule
without a negative test · test lacking evidence criteria · test lacking cleanup ·
test infeasible with available equipment

### 3.3 Implementation gaps
approved requirement without implementation mapping · implementation mapping
without an approved requirement · executable test absent · production behaviour
detected but undocumented · obsolete implementation after a requirement change

**Source without clause** (the backward arrow) forces a choice the developer must
make, not the skill: *add a clause to the FSD* (behaviour exists but is
undocumented) or *delete the code* (orphaned implementation).

### 3.4 Execution and evidence gaps
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
