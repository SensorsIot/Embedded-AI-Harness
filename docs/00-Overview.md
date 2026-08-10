# The Harness — documentation map

This repository implements **AI Closed-Loop Programming (AICLP)**: the AI
develops firmware in a closed loop — code, build, flash, verify on real
hardware, correct — until the tests, derived from the FSD, run clean. The
Harness is everything that closes that loop: the FSD discipline, the test
plan, the testbench, and the skills.

## The journey

Five phases. Each ends at a **gate derived from project state, never
declared** — if any requirement is unmet the work loops back to the step that
owns it and the whole check runs again. A phase never starts on a shut gate,
and every gate is graded by a fresh checker that did not do the work.

| # | Phase | Command | What it is |
|---|---|---|---|
| **P0** | Definition | `/define` | Engineers the WHAT: atomic, falsifiable, provenance-tagged requirements, each carrying the contract that proves it. Installs the three documentation planes. |
| **M0** | | | **Load defined** — every Must/Should carries a verification contract a competent stranger could build a rig from, and the planes are committed. |
| **P1** | Harness | `/harness` | Straps the AI to this load: test plan, declared capabilities, the journey tests, a firmware skeleton, CI with release verification, the gate files. **Never touches the DUT.** |
| **M1** | | | **AI harnessed** — a fresh session can open, state its position, and name the next act without asking anyone anything. |
| **P2** | Commissioning | `/commission` | Proves the project's own never-seen-working parts: this board, this wiring, its peers and simulators. A project never commissions the testbench. |
| **M2** | | | **DUT ready** — testbench recorded, the DUT verified as the unit the FSD names, peers answering, the forward path proven to deliver code to it. A failing test now means the code, not the setup. |
| **P3** | Build | `/build` | Runs the loop: locate the position, design and declare the tests, dispatch code, flash and verify, correct until they run clean. |
| **M3** | | | **Ready for shipment** — every requirement met with its prohibited outcomes checked, the journey green, reconcile empty in both directions. |
| **P4** | Shipment | `git tag` | Publishes a release built from the tagged commit in the pinned container. |
| **M4** | | | **Shipped** — the release published, and the journey green on the released bytes rather than on a rebuild. |

Two rules bind the loop. **No code without a clause** — work no requirement
covers enters through Definition or not at all. **A change is done when its
requirement is met and the journey still runs.**


| Plane | Question | Document |
|-------|----------|----------|
| **WHAT** | What must be true? | [`Harness-FSD.md`](Harness-FSD.md) — Appendix D is the full HTTP API and MCP reference |
| **HOW** | How is it built and changed? | [`Method/`](Method/00-Overview.md) — entry point [`Method/AI-Workflow.md`](Method/AI-Workflow.md) |
| **OPERATE** | How do I run it? | [`Harness-User-Manual.md`](Harness-User-Manual.md) |

All three planes are present-state and single-home: state a fact once, link to
it from anywhere else. Routing rule and edge cases:
[`Method/standards/documentation.md`](Method/standards/documentation.md).

## One machine, two spellings

The machine is a **testbench**, and after the first mention each document
calls it **the bench**. It was called a *workbench* for a year, and a handful
of names still say so on purpose — every one of them is a contract with
something outside this repository, and changing it here alone would break the
thing at the other end:

| Still `workbench` | Why it cannot move alone |
|---|---|
| `workbench.local` | the Pi's actual mDNS hostname; renaming needs the Pi **and** every project pointing at it, in the same moment |
| `workbench-*` skills | invoked by name from other repositories |
| `workbench_driver.py`, `workbench_test.py`, `workbench_mcp.py`, `pi/config/workbench.json` | imported, collected and read by path |
| `WORKBENCH_URL`, `WorkbenchDriver`, `WorkbenchError` | still work — the code reads `TESTBENCH_URL` first and falls back, and the old class names are aliases |
| `"service": "workbench"` in the discovery beacon | what `discover-workbench.py` matches on |

A rename that breaks a caller to fix a spelling is not an improvement. These
move when the Pi and the dependent repositories move together.

One document sits under WHAT without being about the bench itself:
[`test-partner.md`](test-partner.md) states what the **bench's own ESP32** must do,
test by test. The bench cannot verify half its requirements alone — it has one
radio, one serial port per slot, and no way to answer its own `ping` — so the
suite needs a counterpart, and that counterpart's obligations are requirements
like any other. The firmware discharging them is `test-firmware/`, built by CI
as `test-partner-<target>`.
