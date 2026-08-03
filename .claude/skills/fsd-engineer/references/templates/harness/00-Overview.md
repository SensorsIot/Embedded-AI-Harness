# {{PROJECT}} — Harness (HOW)

The Harness is the **build contract**: the rules for how this project is built and
changed. Entry point for any task: **[`AI-Workflow.md`](AI-Workflow.md)**.

## Layout

| Path | Contents |
|------|----------|
| `AI-Workflow.md` | The loop every change follows. Read it before touching code. |
| `standards/` | Portable rules, reusable on any project — engineering, testing, documentation governance. Ship as-is; trim what does not apply. |
| `project/` | {{PROJECT}}-specific bindings: layers, source layout, dependency rules, prohibitions, tool pointers. |

## Authority order

1. **FSD (WHAT)** — what must be true. The contract. `{{FSD_PATH}}`
2. **Harness (HOW)** — how to build it. This directory. It cannot change the target.
3. **Handbook (OPERATE)** — the running system as built. `{{HANDBOOK_PATH}}`

On conflict the FSD wins on *what must be true* and the Harness wins on *how to
get there*. If the Handbook disagrees with either it is stale — it describes
reality, so a disagreement means either reality or the spec moved.

None of the three carries history or rationale narrative; those live in `git log`.

## What belongs here

A rule belongs in the Harness when it constrains **how the code is written,
structured, or verified** without being observable from outside the running
system. If a black-box tester could verify it, it is a requirement and belongs in
the FSD instead.

- Belongs here: "one module per component", "lower layers never import higher
  ones", "every change ships its test", "extract pure cores for host testing".
- Belongs in the FSD: "reconnects within 30 s", "rejects oversized payloads with
  `-1`", "resumes advertising within 2 s of disconnect".
- Belongs in the Handbook: "flash the SD card with Raspberry Pi Imager".

## Documentation rule

All three planes are present-state and single-home: state a fact once, link to it
from anywhere else. See `standards/documentation.md`.
