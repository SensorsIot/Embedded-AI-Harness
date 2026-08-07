---
name: build
description: >
  Phase 3 of AI Closed-Loop Programming — the Build phase, and the driver of the
  whole loop: locate the project on the chain, name the next act, design and
  declare tests, dispatch code/flash/verify, correct until the tests run clean.
  Owns the test plan, test design, audit, reconcile, and the change-request
  procedure. Use this skill whenever the user wants to build or continue building
  a harnessed project, asks "what's next" or "where are we", wants a feature
  added (change request), mentions test design, the test plan, xfail, audit,
  coverage gaps, reconciling drifted code, or "run the loop" — and for Phase 2
  work when invoked via /commission.
---

# Build — the loop's driver (Method skill)

**AI Closed-Loop Programming**: open-loop AI coding generates and hopes; AICLP
feeds back reality — the code runs on real hardware, tests derived from the FSD
measure it against the spec, the error corrects the next iteration. The loop
exits at zero: tests green.

| Control loop | Here |
|---|---|
| Setpoint | The FSD — what must be true |
| Plant | Firmware on the real chip |
| Sensor | Tests derived from the FSD, run on the testbench |
| Error signal | Failing tests |
| Controller | The AI, correcting until error = 0 |

This skill drives Phases 2 and 3 of the journey. `/commission` and `/build` are
two doors into it; the phase is **derived from state, never chosen by the
command typed**.

Each phase ends at a **gate** — not a milestone. A milestone is a marker you
pass; a gate has to open, and it can send you back. Every gate is **derived,
never declared**, and every one is *checked*: the owning skill states its
deliverables and the check that opens it.

> **Run the check. If any requirement of the gate is unmet, name it, loop
> back to the step that owns it, fix it, and re-run the whole check** — not
> only the part that failed. Never carry a known deficiency forward, and
> never enter a phase whose predecessor's gate is still shut.

This is the loop's own discipline applied to itself: a deficiency waved
through is found later at many times the cost, and every result produced
after it is suspect — nobody can tell whether a red belongs to the new work
or to what was let past. "Mostly done" is a shut gate.

| Phase | Gate | Checked by |
|---|---|---|
| 0 · Definition (`/define`) | **Load defined** — every Must/Should carries a verification contract; three planes exist | `/define` §12.5 + `finalisation.md` §1 |
| 1 · Harness (`/harness`) | **AI harnessed** — a `/build` session opens, states its position, and acts without asking | `/harness` Exit — dry run of the next session |
| 2 · Commissioning | **Testbench trusted** — a failing test means the code, not the setup | `/commission` Exit — four checks, six records |
| 3 · Build | **Ready for shipment** — every requirement met, journey green, reconcile empty | this skill §4 audit + §5 reconcile |
| ⚑ Shipment | **Shipped** — release published *and* the journey green on the released bytes | the release-verify job (§6) |

## 0. Open every session by saying where the project is

Read `testing/test-plan.yaml` and the FSD, derive the position, and open with
it — unprompted. The user asking "so what do I do next?" means this skill
failed to lead.

- **Debugging agenda has open items** → Phase 2. Lead commissioning: next
  unproven **project-side** part, how to prove it (`../commission/SKILL.md`
  owns the phase and its four checks; the workbench is depended on, never
  proven by a project).
- **Agenda burned down, requirements unmet** → Phase 3. Derive the **wave**
  first, then name the next act from the chain below, per requirement — never
  an average that hides the requirement that has nothing.
- **All requirements met, reconcile empty, journey green** → announce **Ready
  for shipment** and stop; the tag is the user's act, never this skill's.

**Phase 3 runs in three waves, and the wave is derived from the plan** —
gates, authoring lock, and the capability-declaration exception in
`references/test-design.md` §5:

| Wave | Writes | Open while | Locked behind it |
|---|---|---|---|
| 1 · Build the running prototype | `standard` tests + features | any standard test red or unwritten | deviations, negatives |
| 2 · Cover the normal variants | `deviation` tests | journey + all standard green | negatives |
| 3 · Build the error handling | `negative` + adversarial `security` | all standard + deviation green | — |

The position report names the wave and what the gate is waiting on:
*"Wave 1 — 12/15 standard green, journey step 4 red; deviations locked."*
Work a user requests from a locked wave is declined with the gate as the
reason — the same posture as the intake rule.

| What exists (per requirement) | Position | The next act |
|---|---|---|
| requirement without contract | contract step | send it up to `/define` — writing the contract is the quality gate |
| contract, no declared test | declaration step | declare it in the plan; report equipment that does not exist and interfaces nobody has decided |
| declared, not executable | executable step | write it, `xfail`/`WILL_FAIL` while the feature is absent |
| executable, feature absent | code step | dispatch to the dev skill; the XPASS is the landing signal |
| code with no tests | off the chain | the retrofit — `references/test-lifecycle.md` §3, both steps mandatory |

## 1. The chain — order is not negotiable

```
contract (in FSD, by /define)  →  test declared in the plan  →
executable test (xfail)        →  code  →  build  →  flash  →
verify on the testbench        →  record result + commit    →  green
```

**Per requirement, never as project phases.** One requirement walks the whole
chain before the next starts. Batching every contract, then every declaration,
then all the code reads the same on paper and is a different project in
practice: the plan looks finished while nothing is verified.

- **The executable test is written before or alongside the code — never
  after.** A test written after the code asserts what the code happens to do,
  including the bug.
- **Mark tests for absent features expected-to-fail** (`xfail` / `WILL_FAIL`).
  The suite stays green, the test exists, and the XPASS announces the feature
  landing. A permanently red suite is worse than no suite.
- **The cheap tier is exempt from all ordering**: host tests run in full, every
  time, before every hardware session. A red one is a reason not to start.
- **The journey tests are the gate** for every hardware session: while a
  journey step fails, later results are unreadable — a dozen reds, one cause.

Test design (the two opening questions, the four kinds in three waves, the two
shapes — atomic and workflow — and their numbering, seams, controllability):
`references/test-design.md`. Status semantics, computed blocking, the retrofit,
gap categories: `references/test-lifecycle.md`.

## 2. Dispatch — the loop's muscles

This skill designs, declares, sequences, and interprets. It does not compile,
flash, or drive instruments — it dispatches:

| Act | Skill |
|---|---|
| Amend the WHAT (new/changed requirement, contract fix) | `/define` update mode |
| Code · build · flash · monitor | `esp-idf-handling` / `esp-pio-handling` |
| Verify: WiFi, MQTT, BLE, logging, RF | `workbench-*` skills |
| Run the bench suite, operator prompts | `workbench-test-handling` |
| CI, release workflow | `setup-action` |

**Contracts flow down; spec defects flow up.** When a declaration or an
executable test proves a contract unsatisfiable, this skill *reports* the
finding and `/define` amends the spec. This skill never edits the WHAT.

## 3. Change request — how any new feature enters

**No code without a clause.** Work no requirement covers is refused and routed
through Definition first — the full procedure, including impact analysis and
the done-criterion (*requirement met AND the journey still runs*), is
`references/change-request.md`.

## 4. Audit — "are we actually done?"

Report the lifecycle state of every requirement and the gaps by the four
categories of `references/test-lifecycle.md` §2 — specification defects,
verification gaps, implementation gaps, execution/evidence gaps — each list
naming who resolves it. A requirement is **met** when every test that verifies
it is `successful`, including its prohibited-outcome checks. Derived, never
stored; expect most requirements below *met* mid-project — that is
information, not failure.

## 5. Reconcile — both directions, both lists empty

- Declared in the plan, absent from the code → the backlog.
- Implemented, absent from the plan → a test verifying something nobody wrote
  down, or a duplicate in the making. **This is the direction people forget.**

Behaviour found in code that no clause covers is proposed upward: document it
(a clause) or delete it (orphaned code) — the developer chooses, never this
skill.

## 6. Shipment — the loop never ships

- Dev builds are identified by `git describe`; **no tags are ever minted during
  Build**. The tag namespace holds only releases.
- `git tag` means "release this commit" and is the **user's act**, taken when
  this skill has announced Ready for shipment.
- The release workflow rebuilds the tagged commit in the pinned container, then
  the verify job flashes the released artifact to the testbench and runs the
  journey once. **Shipped = release published AND the journey green on the
  exact bytes users download.** A red journey publishes nothing.
- Testbench powered off at verify time is an unmet precondition: `not done`
  with the reason, never `failed`. Power it on, re-run the job.

## 7. Reference index

| File | Covers |
|---|---|
| `references/test-design.md` | The two opening questions, clause inventory, controllability, the four kinds gated in three waves, atomic vs workflow tests and the `JRN-`/`TC-` numbering, bring-up vs debugging aids, cleanup, seams |
| `references/test-lifecycle.md` | Test status, computed blocking, what artefacts prove, the code-exists retrofit, gap categories |
| `references/test-architecture.md` | Layering, tier taxonomy, component × tier matrix |
| `references/change-request.md` | Intake rule, routing, impact analysis, the done-criterion |
| `references/domains/esp32/` | Proposed test-case libraries (WiFi, MQTT, BLE, OTA, NVS, …) — a pack proposes, never adopts |
