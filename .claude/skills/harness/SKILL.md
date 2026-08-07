---
name: harness
description: >
  Phase 1 of AI Closed-Loop Programming — harness the AI for a project: the
  one-time setup that straps the AI to this particular load so the loop can
  run. Sequences Definition (via /define) when no FSD exists, then installs
  the three planes, the testing standard, the test plan seeded with the
  journey tests, declared testbench capabilities, firmware integration, CI
  with release verification, and the devcontainer with its per-repo runner.
  Use this skill for a new project, "set up this project", "harness this
  project", "integrate with the workbench", or when a project has an FSD but
  none of the machinery to build against it. Exit gate: AI harnessed.
---

# Harness — Phase 1 sequencer

Runs **once per project**. This skill owns only the **order** and the
checklist of what "harnessed" means; every step delegates to the skill that
does the work. A harness is the coupling between horse and load: after this
phase, a `/build` session can open, state its position, and act.

## The sequence

| # | Step | Delegate to |
|---|------|-------------|
| 1 | **Definition first.** No FSD → run Phase 0 now: `/define` (grill → create). FSD exists → verify every Must/Should carries a verification contract; missing ones are the first act | `/define` |
| 2 | Three planes installed or bound: FSD home, `docs/Method/`, `docs/UserDocumentation/` + `docs/00-Overview.md` at the docs root | `/define` planes mode |
| 3 | Testing standard stamped (setup/teardown/evidence rules + shared procedures, one file) | `/define` templates |
| 4 | `testing/test-plan.yaml` created; **capabilities declared** — bench capabilities copied from what the bench reports (`available: yes` as declared — a project never proves them), plus this project's own peers and equipment. Blocked is computed from these, never typed | this skill |
| 5 | Firmware integration — **only the modules the FSD requires.** UDP logging always (the loop's eyes inside the DUT); WiFi provisioning, OTA, BLE hooks only when the FSD carries the corresponding requirements. A module the spec never asked for is silent pack adoption | `workbench-integration` |
| 6 | CI: build on push, release on tag **plus the release-verify job** (flash the released artifact to the testbench, run the journey; red journey = no release) | `setup-action` |
| 7 | Devcontainer and toolchain, with the **GitHub Actions runner inside it** — see below | `esp-idf-handling` / `esp-pio-handling` (project + toolchain setup) |
| 8 | **Generate this project's gate checks** — one file per gate under `testing/gates/`, filled with this project's paths, ids, DUT, capabilities, markers and CI. A generic checklist cannot catch a project-specific omission | this skill · `../build/references/gate-checks.md` |
| 9 | **Close with the two questions only the user can answer** — see below | this skill |

## Step 7 — the runner lives in the project's devcontainer

One project, one container — no separate infrastructure. The devcontainer
already holds the pytest bench tier, WorkbenchDriver, discovery, and slot
config, which is everything the verify job needs (it downloads an artifact and
speaks HTTP; it never builds). **Installation is automated; registration is a
human grant** — a registered runner accepts and executes workflow code that
then physically drives the bench, a standing outward-facing authority like
the release tag itself. This skill installs the runner and the registration
script, states what registering means, and waits for the user's yes.
Register **per-repo**, labels `[self-hosted, testbench]`, ephemeral
registration in a restart loop, verify job triggered by tag push only,
approval required for outside contributors. Declare it as a capability:

```yaml
release-verification:
  what:      tag-triggered journey run against the released artifact
  available: yes   # the container runs 24/7; the bench may not — an absent
                   # bench at verify time is an unmet precondition (not done)
```

## Step 9 — the two unharvestable questions

Asked at the end, when the user knows the system's shape — and never
harvestable from any document:

1. **What has to be debugged before testing starts?** Which **project-side**
   parts — this board, its wiring, its peers and simulators — have never been
   observed doing their job here. Becomes the **debugging agenda** that
   `/commission` burns down. **The workbench is not on this list**: a project
   depends on its quality, never proves it (`../commission/SKILL.md`).
2. **What does one ordinary successful run look like, end to end?** Ordered
   steps, an observable at each. Becomes the **journey tests** — one test per
   step, seeded into the plan as the gate every hardware session runs behind,
   and the first tests of Wave 1 (*Build the running prototype* —
   `../build/references/test-design.md` §5).

These two answers are worth more than everything else typed this month; take
them slowly. Full rationale: `../build/references/test-design.md` §5.

## Exit — AI harnessed

### Deliverables

| Deliverable | Content |
|---|---|
| **Test plan** | `testing/test-plan.yaml` — capabilities (bench as declared, project equipment own-state), the journey tests seeded from question 2, `phase`/`wave` fields |
| **Debugging agenda** | the project-side parts from question 1, each with *unproven because* and *proven by* |
| **Testing standard** | one file: setup/teardown/evidence rules plus shared procedures |
| **Firmware hooks** | only the modules the FSD requires; UDP logging always |
| **CI** | build on push, release on tag, release-verify job present |
| **Devcontainer + runner** | toolchain builds; runner installed, registration awaiting the user's grant |
| **Gate checks** | `testing/gates/` — one generated file per gate, project-specific, run by a fresh checker at each gate |

### The check — a dry run of the next session

```bash
test -f testing/test-plan.yaml && test -f testing/debugging-agenda.md
ls .github/workflows/                       # build + release-verify present
gh run list -L 1                            # CI has actually run green once
```

Then the only check that matters: **open a `/build` session and see whether it
can state its position and name the next act without asking you anything.**
If it can — the plan is readable, the capabilities are declared, the agenda
exists — the AI is harnessed. If it stalls, the missing input is the finding,
and it belongs to whichever step above left it out.

**Run the check in a fresh checker, not in this session** — the session that
built the harness is the worst judge of whether it landed
(`../build/references/gate-checks.md`). Spawn it with `testing/gates/` and the
repo, nothing else — **never memory, transcripts, or a summary of what this
session did**: a checker told what was decided will confirm it was done.

**The gate loops, it does not wave through.** If the checker returns `SHUT`,
go back to the step above that owns each finding, fix it, and re-run the whole
check with a **new** checker. Commissioning does not start on a partial
harness.

**AI harnessed** — derived, never declared. The next session starts with
`/commission`.
