# Test lifecycle — status, gaps, and the retrofit

The other half of `test-design.md`. That file decides *what tests to build*;
the chain that orders the work lives in `../SKILL.md` §1 (it is the driver's
state model); this file covers *what a result means, how to report what is
missing, and how to recover a project where the code came first*.

---

## 1. Test status, and what a requirement being met means

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
| needs *capability* — unavailable | project-side: whoever builds that peer. Bench-side: a change request on the testbench repo — never the project |
| precondition unmet | fix that first; the result would mean nothing |

**A failed precondition is `not done`, not `failed`.** Recording a failure claims
you learned something about the requirement; with a broken baseline you learned
nothing, and it sends the next person hunting the wrong defect. An unpowered
testbench or DUT at run time is a precondition, not a failure.

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
    available: no        # cannot be done — state the consequence
  mbus-simulator:
    what:      the project's meter simulator emits complete telegrams
    available: unproven  # project-side peer; nobody has seen it work HERE
```

**`available` has three values.** `yes` — for the testbench's declared
capabilities, taken at face value: *no project tests the testbench; a project
depends on its quality* (fixed in the bench's own repo only when DUT evidence
disproves it). `no` — it cannot be done; state the consequence.
**`unproven`** — for **project-side equipment only** (peers, simulators, the
DUT's own wiring): declared but never observed doing its job here — treated
as unavailable for blocking, and every `unproven` entry is a debugging-agenda
item. Proving it flips it to `yes`; nothing is typed twice.

This is where the model earns its keep. On one project a safety requirement
rendered as *"needs button-gpio, ota-relay"* — because observing it required
states the testbench could not reach — a fact no review had found.

Record **testbench limitations on the capability, with their consequence**. "The
simulator is unstable" is a note; *"two bursts in six arrive clean, so assert
across several cycles and require one good one"* changes how tests get written.

### Reconcile the plan against the code, both directions

Two lists, both of which must end empty:

- declared in the plan with an empty `impl:` → the backlog
- **an executable that no entry's `impl:` points at** → a test verifying
  something nobody wrote down, or a duplicate about to be written for a
  requirement already covered

Both lists are computed from `impl:` (`test-design.md` §5a), never from
matching names.

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

## 2. Gap reports — four categories, not one list

A single undifferentiated gap list hides the fact that these need different
people to resolve them.

### 2.1 Specification defects
compound requirement · undefined initial state · undefined resulting state ·
missing timeout or tolerance · ambiguous term · missing failure behaviour ·
conflicting requirements · unverifiable observation · uncontrollable stimulus ·
missing security assumption · unsupported regulatory claim · missing
configuration rule

### 2.2 Verification gaps
approved requirement without a declared test · normative state transition
without a test · numeric boundary without a boundary test · rejection rule
without a negative test · test lacking evidence criteria · test lacking cleanup ·
test infeasible with available equipment

### 2.3 Implementation gaps
approved requirement without implementation mapping · implementation mapping
without an approved requirement · executable test absent · production behaviour
detected but undocumented · obsolete implementation after a requirement change

**Source without clause** (the backward arrow) forces a choice the developer must
make, not the skill: *add a clause to the FSD* (behaviour exists but is
undocumented) or *delete the code* (orphaned implementation).

### 2.4 Execution and evidence gaps
executable test never run · result not tied to a commit · missing raw evidence ·
stale evidence after a requirement or implementation change · test passed but
prohibited outcomes were never checked · coverage present without behavioural
assertions

### Also listed, so they are not mistaken for gaps
clauses marked `pending: true` (the FSD itself is unresolved),
`testability: philosophical` (no rig can decide them), and **wave-locked
tests** — deviation/negative tests unwritten because their wave has not
opened (`test-design.md` §5) are by design, not neglect; report them under
the wave they wait for, never as verification gaps.

**The skill proposes resolutions. It does not silently decide product questions.**

---

## 3. When the code already exists

Most projects arrive here, and the honest position is that the chain cannot be
replayed. What can be done is to remove the specific harm it causes. Both steps
are mandatory:

- **Write the test from the contract with the implementation closed.** If you
  cannot state the assertion without reading the code, the contract is incomplete
  — fixing the contract is the finding, and it is worth more than the test.
- **Then prove the test can fail.** Break the code deliberately — invert a
  comparison, stub a return — watch it go red, restore. A test that has only ever
  been green is a claim, not a check, and this is the only way to tell the two
  apart after the fact.

A retrofitted suite that skips them reliably encodes the defects it was written
to catch.

---

Traceability is the join between requirement ids in the FSD and the tests in the
plan that reference them, computed by the report. There is no separate matrix to
maintain, no `@fsd` tag to keep in step, and no evidence directory: the plan entry
carries the commit its result came from, which is what makes staleness visible.

A heavier project may want source tags and a retained evidence archive. Both are
additions to this model, not parts of it, and both cost a synchronisation problem
in exchange for provenance the plan already approximates.
