---
name: commission
description: >
  Phase 2 of AI Closed-Loop Programming — Commissioning: prove the project's
  OWN never-seen-working parts (its board, its wiring, its peers/simulators),
  so that a failing test means the code and not the setup. The workbench
  itself is never commissioned by a project — its quality is depended on, and
  fixed in its own repo only when DUT testing disproves it. Use this skill
  when the user mentions commissioning, bring-up, a new board or peer, wiring
  or polarity doubts, or wants to burn down the debugging agenda. Exit
  milestone: Testbench trusted.
---

# Commission — Phase 2 door

A door into the Method skill: **the driver, the chain, and the dispatch map
live in `../build/SKILL.md`** — read that first. This door exists so the phase
can be entered by its own name; the phase itself is always derived from state.
If the debugging agenda is already burned down, say so and continue as
`/build` — typing the "wrong" door costs nothing.

## The law: no project tests the testbench

**A project depends on the workbench's quality; it never proves it.** The
bench is infrastructure, like the compiler — nobody tests gcc before
compiling. Its quality is the workbench repo's own responsibility: its FSD,
its suite, its acceptance run. A project consumes the bench's declared
capabilities at face value, `available: yes` as declared.

**If DUT testing disproves the bench, fix the bench — but only then.** When a
red is exonerated of the product by evidence, the bench fault becomes a
workbench change request, is fixed at its source, ideally lands as a test in
the *workbench's own* suite, and every future project inherits the fix.
Attempting to verify the bench upfront — when nothing yet exists that could
expose its errors — buys ceremony, not trust. Real work is the only
instrument that finds real bench faults.

## What commissioning is, under the law

The debugging agenda (`../build/references/test-design.md` §5, first question)
lists every **project-side** part that has never been observed doing its job
*here* — whatever its reputation elsewhere:

- the DUT board itself — this unit, this slot, first flash, first boot
- project peers and simulators (an M-Bus simulator feeding telegrams)
- project-specific wiring and its polarity
- the project firmware's first contact with each path it uses

Until each is seen working, a failing test measures the environment. The
workbench's instruments are **not** on this list.

- Work the agenda top-down; each item names *what proves it*. Drive known
  patterns (`0x55` survives inversion detection), make the simulator emit one
  whole telegram.
- **Agenda items are debugging work, not test cases** — they never enter the
  plan. The separator: does it discharge a requirement, or interrogate the
  setup? Setup measurements go on the **capability**, with their consequence
  ("two bursts in six arrive clean → assert across several cycles").
- The `unproven` capability state applies to **project-side equipment only** —
  bench-declared capabilities are trusted by the law above.
- The bring-up work that *is* a test case (it discharges a requirement about
  the device) is `standard` in kind, ordered ahead of the journey.
- The DUT and testbench are not always powered. An unreachable bench is an
  unmet precondition — `not done` with the reason, never `failed`.
- **The operator's hands are for physical acts — plug, wire, power, swap.
  Observations belong to instruments.** Never design a step where a human
  reads a measurement by eye. If no instrument can make the observation, that
  is a workbench change request.

## Exit

**Testbench trusted** — derived, never declared: the workbench by law, the
project-side parts by proof — the agenda is empty, bring-up tests are green,
and setup limitations are recorded on their capabilities. From here `/build`
runs the journey tests as the gate and the loop proper begins. For a project
with no new hardware and no peers, this phase is minutes, not days.
