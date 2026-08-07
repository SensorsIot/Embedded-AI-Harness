---
name: commission
description: >
  Phase 2 of AI Closed-Loop Programming — Commissioning: prove the testbench
  (workbench + DUT wiring + peers/simulators) and every never-seen-working part
  of the system, so that a failing test means the code and not the setup. Use
  this skill when the user mentions commissioning, bring-up, a new board or
  peer, wiring or polarity doubts, an untrusted or unstable test setup, or
  wants to burn down the debugging agenda. Exit milestone: Testbench trusted.
---

# Commission — Phase 2 door

A door into the Method skill: **the driver, the chain, and the dispatch map
live in `../build/SKILL.md`** — read that first. This door exists so the phase
can be entered by its own name; the phase itself is always derived from state.
If the debugging agenda is already burned down, say so and continue as
`/build` — typing the "wrong" door costs nothing.

## What commissioning is

The debugging agenda (`../build/references/test-design.md` §5, first question)
lists every part of system *and testbench* that has never been observed doing
its job **here** — whatever its reputation elsewhere. Until each is seen
working, every test result is unattributable and the suite measures the
environment.

- Work the agenda top-down; each item names *what proves it*. Drive known
  patterns (`0x55` survives inversion detection), read back pad configs, make
  the simulator emit one whole telegram.
- **Agenda items are debugging work, not test cases** — they never enter the
  plan. The separator: does it discharge a requirement, or interrogate the
  setup? Setup measurements go on the **capability**, with their consequence
  ("two bursts in six arrive clean → assert across several cycles").
- The bring-up work that *is* a test case (it discharges a requirement about
  the device) is `standard` in kind, ordered ahead of the journey.
- The DUT and testbench are not always powered. An unreachable bench is an
  unmet precondition — `not done` with the reason, never `failed`.

## Exit

**Testbench trusted** — derived, never declared: the agenda is empty, bring-up
tests are green, and setup limitations are recorded on their capabilities.
From here `/build` runs the journey tests as the gate and the loop proper
begins.
