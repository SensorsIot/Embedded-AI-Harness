# Requirement engineering — types, provenance, quality gate, verification contract

A requirement is not finished when it reads well. It is finished when a competent
stranger can build a rig that returns pass or fail.

---

## 1. Classify every statement

Every normative or advisory statement carries an explicit **type**. Architecture
and implementation guidance disguised as functional requirements is the most
common defect in an engineering spec, because it makes design choices
un-renegotiable and pollutes the test suite with tests of structure rather than
behaviour.

| Type | Meaning | Plane |
|------|---------|-------|
| **Functional requirement** | Externally observable system behaviour | FSD |
| **Quality requirement** | Measurable performance, reliability, accuracy, security, maintainability | FSD |
| **Constraint** | Mandatory restriction on platform, technology, environment, regulation, operation | FSD |
| **Verification requirement** | Mandatory method, tier, evidence, or acceptance rule | FSD |
| **Architecture decision** | Approved structural design choice | Method |
| **Implementation recommendation** | Non-normative advice; may be accepted, changed, or rejected | Method |
| **Assumption** | Treated as true, not yet established | FSD §5 Risks |
| **Open decision** | Product or architecture decision still unresolved | `open-issues.md` |

Worked distinction:

- "The device shall publish telemetry every five seconds" — **functional requirement**.
- "The MQTT manager shall be an independent module" — **architecture decision**.
- "Prefer a non-blocking state machine" — **implementation recommendation**, unless
  explicitly approved as a constraint.

The type determines the plane (see `three-planes.md`). A statement typed
*architecture decision* does not belong in the FSD body.

---

## 2. Provenance and status

Every requirement records **where it came from** and **how far along it is**.
These are orthogonal: a domain-pack proposal and a user statement can both be
`proposed`; a user statement and a detected behaviour can both be `approved`.

### Provenance (`source:`)

```text
user                            stated by the user directly
existing-approved-fsd           carried from an approved prior spec
existing-implementation         observed in code (see the rule below)
derived                         logical consequence of another approved requirement
domain-pack                     proposed by a domain pack
regulatory-or-normative-source  imposed by a standard or regulation
proposed-by-skill               this skill filled a gap
```

### Status (`status:`)

```text
proposed      awaiting acceptance
approved      normative
inferred      assumed from context, unconfirmed
detected-in-code   observed behaviour, not yet adjudicated
deprecated    no longer required, retained for history
rejected      considered and declined
superseded    replaced by another ID
pending       blocked on an open decision
```

### The two rules that matter

**Detected behaviour is not automatically a requirement.** Finding code that
does something proves only that it does it. Ask which of four things it is:

1. documented as intended behaviour → becomes `approved`;
2. retained only as an implementation detail → goes to the Method, not the FSD;
3. non-compliant → the *code* changes, not the spec;
4. orphaned → deleted.

**Never invent a normative value silently.** When a requirement needs a missing
timeout, tolerance, limit, default, initial state, error response, retry count,
persistence rule, or security assumption — report the omission. You may propose a
value, but it is marked:

```yaml
source: proposed-by-skill
status: proposed
```

and it stays that way until accepted or supported by authoritative material. A
proposed threshold silently promoted to approved is how a spec acquires numbers
nobody chose.

### Example

```yaml
id: FR-MQTT-08
type: functional
priority: must
source: user
status: approved
text: >
  After the configured MQTT broker becomes reachable again, the device shall
  establish a new MQTT session and resume valid telemetry publication within
  30 seconds without restarting.
```

---

## 3. Quality gate

Every **Must** and **Should** passes all thirteen checks. A failing requirement
goes to `gaps.md` or `open-issues.md`; it is never treated as complete.

| Check | Question |
|-------|----------|
| **Atomic** | One independently verifiable obligation? |
| **Unambiguous** | Would competent readers interpret it identically? |
| **Observable** | Can the result be observed directly or through defined evidence? |
| **Controllable** | Can the triggering condition be created or supplied? |
| **Measurable** | Are timing, limits, values, tolerances defined where needed? |
| **Feasible** | Can the system and the available test infrastructure satisfy and verify it? |
| **Consistent** | Does it conflict with another requirement, state rule, interface, or constraint? |
| **Necessary** | Is it supported by a source or an accepted derivation? |
| **Traceable** | Stable ID and stable provenance? |
| **Failure-defined** | Is behaviour specified for error and unavailable conditions? |
| **State-defined** | Are the relevant initial and resulting states known? |
| **Secure-by-profile** | Do security requirements derive from an explicit threat profile? |
| **Typed** | Is it classified per §1, and filed in the right plane? |

### Atomicity

Split anything joining two verbs, a behaviour and a deadline, a success and a
failure path, or a list of outputs.

> The device shall reject invalid credentials, flash the LED red, and retry after
> 60 seconds.

is three obligations that fail independently:

```text
FR-PROV-21  Invalid credentials shall be rejected.
FR-UI-14    Rejection shall activate the defined red LED indication.
FR-PROV-22  The next automatic provisioning attempt shall occur after 60 s.
```

### Words that signal a failed gate

Treat each as a defect to fix, not a style preference: *appropriate,
graceful(ly), user-friendly, as needed, if possible, reasonable, sufficient,
robust, properly, seamless, optimal, minimal, acceptable, normal operation, best
effort.*

Vacuous quantifiers are the same defect. "No data loss" needs a window and a
delivery guarantee. "Possible packet loss" is an observation, not an expected
result — state how many packets may be lost before the test fails.

If a genuinely subjective quality matters, state it as **May** with a named
human-judgement acceptance step, so it is never mistaken for something a rig can
decide.

---

## 4. Verification contract

Every approved **Must** and **Should** contains or references a verification
contract. This is the artefact that proves the requirement is testable —
attempting to write it *is* the testability check, which is why it belongs to the
requirement and not to a downstream skill.

```yaml
verification:
  preconditions:        # the state before the stimulus
  stimulus:             # what is done to the system
  expected_observations:# what an outside observer sees
  timing:               # deadline from stimulus to response
  tolerance:            # permitted deviation
  prohibited_outcomes:  # what must NOT happen, even if the deadline is met
  tier:                 # see test-architecture.md SS3
  evidence:             # what is captured to prove it
  cleanup:              # how the system is restored afterwards
```

`prohibited_outcomes` is not decoration. A recovery test that only checks "did it
recover in 30 s" passes when the device recovers *by rebooting* — which is
usually the failure being tested for. Name the outcomes that invalidate a pass.

### Example

```yaml
id: FR-MQTT-08
verification:
  preconditions:
    - The DUT is connected to WiFi.
    - The DUT has an active MQTT session publishing valid telemetry.
  stimulus:
    - Stop the MQTT broker.
    - Keep it unavailable for 10 s.
    - Restart the broker.
  expected_observations:
    - The DUT detects loss of the MQTT session.
    - WiFi remains connected throughout.
    - A new MQTT session is established.
    - A valid telemetry message is received within 30 s of broker restart.
  timing: 30 s from broker availability to first valid telemetry
  tolerance: ±5 s
  prohibited_outcomes:
    - The DUT restarts.
    - Manual reprovisioning is required.
    - A stale or invalid payload is accepted as recovery evidence.
  tier: bench
  evidence:
    - Broker stop and start timestamps.
    - First valid telemetry message after recovery.
    - Reset reason or boot-counter reading.
    - Serial or UDP diagnostic log.
  cleanup:
    - Ensure the broker is running.
    - Restore the DUT to its operational baseline.
```

The contract establishes verification **intent** at requirement level. It does
not replace the test entry in the plan (`test-lifecycle.md` §2), which adds
equipment, test data, automation handoff, and failure recovery.

### Two forms — pick per requirement, not per document

Writing the block above ninety times produces a document nobody reads. Both forms
below satisfy "every Must/Should carries a contract"; what changes is how much
room the requirement earns.

**Full YAML — where a wrong pass is plausible.** Use it when a broken system could
accidentally satisfy the success criterion: recovery, rollback, failover,
reconnection, anything whose happy-path observation is also reachable by the
failure you are testing for. These are the requirements where naming
`prohibited_outcomes` at length is the whole value — *the device restarts*,
*manual reprovisioning is required*, *a stale payload is accepted as evidence*.

**Compact table — everywhere else.** One row per requirement, in the chapter that
owns it:

```markdown
| ID | Precondition · stimulus | Expected observation | Must NOT happen | Tier |
|---|---|---|---|---|
| FR-HA-05 | Feed a cycle missing `U2` | No `U2` in the payload | `U2` present as 0 or stale | host |
```

Add a timing column only where a deadline applies; carrying an empty one on every
row trains readers to ignore it.

**The `Must NOT happen` column is not optional in either form.** It is the field
that makes a contract worth having: without it a recovery requirement passes when
the device recovers by rebooting, which is usually the defect. A compact row that
drops it is a description, not a contract.

State the split when reporting the run — "8 requirements carry full contracts, 85
compact" tells a reviewer where the risk was judged to be, and lets them disagree.
