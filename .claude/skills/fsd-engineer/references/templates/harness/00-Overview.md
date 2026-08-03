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

1. **Harness (HOW)** — how to build. This directory.
2. **FSD (WHAT)** — what must be true. `{{FSD_PATH}}`
3. **Handbook (OPERATE)** — how to run it. `{{HANDBOOK_PATH}}`

The FSD defines the target; the Harness defines the method. Neither carries
history or rationale — those live in `git log`.

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
