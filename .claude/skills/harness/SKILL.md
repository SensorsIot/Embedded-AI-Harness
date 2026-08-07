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
  none of the machinery to build against it. Exit milestone: AI harnessed.
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
| 4 | `testing/test-plan.yaml` created; **testbench capabilities declared** — slot assignment, what the bench can and cannot do. Blocked is computed from these, never typed | this skill |
| 5 | Firmware integration: UDP logging, WiFi provisioning, OTA, BLE command hooks — the loop's eyes inside the DUT | `workbench-integration` |
| 6 | CI: build on push, release on tag **plus the release-verify job** (flash the released artifact to the testbench, run the journey; red journey = no release) | `setup-action` |
| 7 | Devcontainer and toolchain, with the **GitHub Actions runner inside it** — see below | `esp-idf-handling` / `esp-pio-handling` (project + toolchain setup) |
| 8 | **Close with the two questions only the user can answer** — see below | this skill |

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

## Step 8 — the two unharvestable questions

Asked at the end, when the user knows the system's shape — and never
harvestable from any document:

1. **What has to be debugged before testing starts?** Which parts — of the
   system *and* of the testbench — have never been observed doing their job
   here. Becomes the **debugging agenda** that `/commission` burns down.
2. **What does one ordinary successful run look like, end to end?** Ordered
   steps, an observable at each. Becomes the **journey tests** — one test per
   step, seeded into the plan as the gate every hardware session runs behind,
   and the first tests of Wave 1 (*Build the running prototype* —
   `../build/references/test-design.md` §5).

These two answers are worth more than everything else typed this month; take
them slowly. Full rationale: `../build/references/test-design.md` §5.

## Exit

**AI harnessed** — derived, never declared: the planes exist, the plan holds
the journey tests and the declared capabilities, the agenda is written, CI is
wired, the runner answers. The next session starts with `/commission`.
