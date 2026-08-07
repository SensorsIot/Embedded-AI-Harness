# The Harness — documentation map

This repository implements **AI Closed-Loop Programming (AICLP)**: the AI
develops firmware in a closed loop — code, build, flash, verify on real
hardware, correct — until the tests, derived from the FSD, run clean. The
Harness is everything that closes that loop: the FSD discipline, the test
plan, the workbench, and the skills. The journey, its five phases, and their
normative milestones are defined in the
[FSD §1.1](Embedded-Workbench-FSD.md#11-purpose).

| Plane | Question | Document |
|-------|----------|----------|
| **WHAT** | What must be true? | [`Embedded-Workbench-FSD.md`](Embedded-Workbench-FSD.md) — Appendix D is the full HTTP API and MCP reference |
| **HOW** | How is it built and changed? | [`Method/`](Method/00-Overview.md) — entry point [`Method/AI-Workflow.md`](Method/AI-Workflow.md) |
| **OPERATE** | How do I run it? | [`Embedded-Workbench-User-Manual.md`](Embedded-Workbench-User-Manual.md) |

All three planes are present-state and single-home: state a fact once, link to
it from anywhere else. Routing rule and edge cases:
[`Method/standards/documentation.md`](Method/standards/documentation.md).
