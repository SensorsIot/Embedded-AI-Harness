# Traceability, evidence, and gap reporting

Traceability distinguishes **mapping** from **verification**. Collapsing them is
the most consequential error in this whole skill, because it converts "we wrote
something down" into "it works" without anyone deciding to.

---

## 1. The seven lifecycle states

A requirement moves through seven states. They are **never** collapsed into a
single `covered` flag.

```text
1. Specified                     the requirement exists and passes the quality gate
2. Test designed                 a complete test specification exists
3. Implementation mapped         source claims responsibility (an @fsd tag)
4. Executable test implemented   runnable test code exists
5. Test executed                 it ran, against a known commit
6. Evidence captured             raw artefacts stored and retained
7. Requirement verified          evidence shows pass, prohibited outcomes checked
```

Each state is a separate field, and the honest answer to "is this requirement
verified?" is usually "no — it is at state 3". A dashboard that reports 100%
"covered" while every requirement sits at state 3 is worse than no dashboard,
because it is confidently wrong.

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

## 2. Required relationships

```text
FSD clause          ↔ test specification
FSD clause          ↔ implementation mapping
test specification  ↔ executable test
executable test     ↔ test evidence
test evidence       ↔ tested commit and environment
```

The last link is what makes evidence **falsifiable over time**: when the commit
moves, evidence tied to the old commit becomes stale and must be re-earned rather
than inherited.

### Example record

```yaml
clauses:
  FR-MQTT-08:
    status: approved
    lifecycle:
      specified: true
      test_designed: true
      implementation_mapped: true
      executable_test_implemented: true
      test_executed: true
      evidence_captured: true
      requirement_verified: true
    tests:
      - TC-MQTT-08
    implementation:
      - path: firmware/src/mqtt_manager.cpp
        tag: "@fsd FR-MQTT-08"

tests:
  TC-MQTT-08:
    spec_path: verification/test-specs/mqtt.yaml
    executable_test: tests/bench/test_mqtt_recovery.py
    last_execution:
      commit: abc1234
      firmware_build: 1.4.2
      workbench_commit: def5678
      result: pass
      timestamp: 2026-08-03T14:22:07Z
      evidence:
        - test-results/run-002/TC-MQTT-08.json
        - test-results/run-002/TC-MQTT-08.log
```

---

## 3. `@fsd` tags

Language-appropriate comment at or immediately above the implementing branch:

```c
/* @fsd FSD-5.2-403-led */
if (status == 403) {
    led_set(LED_RED_GREEN_ALT);
}
```

Rules:

1. Grep every configured source root for `@fsd` markers; parse ID, path, line. A
   tag covers its block to the next closing brace / dedent / blank line.
2. Multiple tags per clause are allowed — a clause may span branches. The matrix
   is many-to-many.
3. A clause with no tag is a gap. **Never invent a mapping.** Propose where a tag
   belongs; never insert one — placement is a human decision.
4. Source files in the configured roots with zero tags feed the backward arrow.
5. Only declared source roots participate. Generated code, vendored libraries, and
   test code are out of scope.

A tag on the wrong branch is a real defect that this skill cannot detect — the
`fsd-compliance-checker` agent verifies that code at each claimed range actually
implements the cited clause.

---

## 4. Evidence

Evidence records the environment, not just the result:

```text
repository · branch · commit · firmware build identifier · FSD version ·
test-specification version · workbench version or commit · hardware identity or
type · execution timestamp · result · artifact paths
```

This is what makes a historical result reproducible and reviewable, and what lets
staleness be computed rather than guessed.

---

## 5. Gap reports — four categories, not one list

A single undifferentiated gap list hides the fact that these need different
people to resolve them.

### 5.1 Specification defects
compound requirement · undefined initial state · undefined resulting state ·
missing timeout or tolerance · ambiguous term · missing failure behaviour ·
conflicting requirements · unverifiable observation · uncontrollable stimulus ·
missing security assumption · unsupported regulatory claim · missing
configuration rule

### 5.2 Verification gaps
approved requirement without a test specification · normative state transition
without a test · numeric boundary without a boundary test · rejection rule
without a negative test · test lacking evidence criteria · test lacking cleanup ·
test infeasible with available equipment

### 5.3 Implementation gaps
approved requirement without implementation mapping · implementation mapping
without an approved requirement · executable test absent · production behaviour
detected but undocumented · obsolete implementation after a requirement change

**Source without clause** (the backward arrow) forces a choice the developer must
make, not the skill: *add a clause to the FSD* (behaviour exists but is
undocumented) or *delete the code* (orphaned implementation).

### 5.4 Execution and evidence gaps
executable test never run · result not tied to a commit · missing raw evidence ·
stale evidence after a requirement or implementation change · test passed but
prohibited outcomes were never checked · coverage present without behavioural
assertions

### Also listed, so they are not mistaken for gaps
clauses marked `pending: true` (the FSD itself is unresolved) and
`testability: philosophical` (no rig can decide them).

**The skill proposes resolutions. It does not silently decide product questions.**

---

## 6. Optional coverage check

Given a coverage report (gcov `.info`, lcov, coverage.py JSON), emit
`<output_root>/coverage-check.py`: for each test in `traceability.yaml`, read its
claimed source ranges, parse the coverage data, and exit non-zero if a claimed
line was never executed.

Generated once; the user wires it into CI. It proves execution — never
behaviour. If there is no coverage tooling, skip it and say so in the run summary
rather than leaving the impression it ran.
