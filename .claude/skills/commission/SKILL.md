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
  gate: DUT ready.
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

## The worked shape — a typical ESP32 project on the workbench

1. **Discover the testbench**; record hostname, last-seen IP and portal
   version as dated observations. Tests still select by identity — the
   record is memory, never a hardcoded address.
2. **Find the DUT and verify it is what the project expects** — slot, chip
   type and revision, flash size, MAC against the FSD's unit. Mismatch =
   stop: wrong board in the slot.
3. **Project peers**, if any (a meter simulator): present, answers one basic
   command; record its slot.
4. **Prove the forward path with a trivial known-good program** — CI
   compiles it, the artifact is flashed to the DUT's slot, and its output is
   observed. **Print alternating `ON` / `OFF` on serial rather than blinking
   an LED**: no GPIO need be wired, no camera or eye is required, and the
   bench observes it directly with a serial pattern match. One pass proves
   the whole pipeline — toolchain, artifact flow, flash, boot, observation —
   with code that cannot itself be the problem. When the project's first real
   build fails later, the pipeline is above suspicion.

Nothing else. Items 1–3 are seconds; item 4 is one CI cycle. Everything
beyond this list is bench-side and covered by the law.

### Running the four checks

Discover the bench, then hold its URL in `$WB` — never write an address into a
committed file.

```bash
# 1 · testbench: answers, and in the mode the project needs
curl -s $WB/api/info                     # hostname, slots configured/running
curl -s $WB/api/wifi/mode                # wifi-testing, if the project uses WiFi

# 2 · DUT: the right board, in a free slot
curl -s $WB/api/devices                  # select by detected_chip, not by label
curl -s -X POST $WB/api/chip/info -H 'Content-Type: application/json' \
     -d '{"slot":"<SLOT>"}'              # chip, revision, flash size, MAC
# Compare with the unit the FSD records. A mismatch stops the phase.
# Check `debugging` as well as `state`: a live OpenOCD session holds the port
# while the slot still reads idle, and on native-USB parts a session on ANY
# such slot blocks the others (shared VID:PID).

# 3 · project peers, if any: present, and answering one basic command

# 4 · forward path: CI artifact → flash → observed marker
gh run download <run-id> -D fw           # the same bytes CI built
curl -s -X POST $WB/api/flash -F slot=<SLOT> -F chip=<chip> -F baud=460800 \
     -F "bin@<offset>=@<image>" ...      # one part per image
curl -s -X POST $WB/api/serial/monitor -H 'Content-Type: application/json' \
     -d '{"slot":"<SLOT>","pattern":"<marker>","timeout":30}'
```

**Take the flash offsets from the build, never from memory.** An ESP-IDF
build ships `flash_args` beside the images with the authoritative offsets;
they move whenever the partition table changes — dropping a `factory`
partition shifts the app from `0x10000` to `0x20000`, and `otadata` from
`0xd000` to `0xf000`. Guessing produces a *successful* flash with a
hash-verified write and a device that then reports `invalid magic byte
(nothing flashed here?)` and refuses to boot. Read `flash_args`; the flash
succeeding is not evidence that it landed where the partition table expects.

**Monitor with a pattern and start it before the reset**, or match a periodic
marker instead: a boot banner has already scrolled past by the time a monitor
opened afterwards, so a missed match may mean *late*, not *absent*. A
heartbeat line (`alive 1`, `alive 2`, …) is observable at any moment, which is
why item 4's program prints one.

## Exit

### Deliverables — what Phase 2 hands to Phase 3

All of it lives in `testing/test-plan.yaml` as dated observations; none of it
is prose in a document nobody reads again.

| Deliverable | Content |
|---|---|
| **Testbench record** | hostname, last-seen IP, portal version, date. Memory, never an address tests connect to |
| **DUT record** | slot, chip type and revision, flash size, MAC — the unit this project is verified against, matching the FSD |
| **Peer records** | each project peer: what it is, its slot or address, the command it answered |
| **Forward-path evidence** | the CI run id, the artifact, the flash offsets used (from `flash_args`), and the marker observed |
| **Capability updates** | every project-side `unproven` resolved to `yes` or `no`; each `no` carries its consequence, each `yes` its observation |
| **Agenda** | empty of project-side items; anything left is bench-side and belongs to the workbench repo, named with its issue |

### The gate

**Run the four checks in a fresh checker** with this project's gate file
(`../build/references/gate-checks.md`) — the session that flashed the board is
the one most likely to read a half-observed marker as proof.

**The gate loops, it does not wave through.** A failed check sends the work
back to the act that owns it — a DUT that is not the expected unit, a peer
that will not answer, a forward path that does not reach its marker — and the
whole check runs again. Wave 1 does not start on a partial commissioning.

**DUT ready** — derived, never declared: the testbench commissioned (by law,
not by proof), the DUT connected and verified as the unit the FSD names, the
project's peers answering, and the forward path proven to deliver code to it. From here `/build` runs the journey
tests as the gate and the loop proper begins. For a project with no new
hardware and no peers, this phase is minutes, not days.
