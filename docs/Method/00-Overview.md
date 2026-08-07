# The Harness — Method (HOW)

The Method is the **build contract**: the rules for how this project is built and
changed. Entry point for any task: **[`AI-Workflow.md`](AI-Workflow.md)**.

## Layout

| Path | Contents |
|------|----------|
| [`AI-Workflow.md`](AI-Workflow.md) | The loop every change follows. Read it before touching code. |
| [`standards/`](standards/) | Portable rules — [engineering](standards/engineering.md), [testing](standards/testing.md), [documentation](standards/documentation.md). Reusable on any project. |
| [`project/`](project/) | Workbench-specific bindings — [architecture](project/architecture.md), [conventions](project/conventions.md). |

## The three planes

| Plane | Question | Document |
|-------|----------|----------|
| **WHAT** | What must be true of the bench? | [`../Harness-FSD.md`](../Harness-FSD.md) |
| **HOW** | How is it built and changed? | This directory |
| **OPERATE** | How do I run it? | [`../Harness-User-Manual.md`](../Harness-User-Manual.md) |

The FSD defines the target; the Method defines the way there; the User Manual describes
the running system. On conflict the FSD wins on *what must be true* and the
Method wins on *how to get there*. If the User Manual disagrees with either, the
the User Manual is stale.

`CLAUDE.md` is **not** a plane. It configures the AI assistant and points here; it
holds no project rules of its own.

## What belongs here

A rule belongs in the Method when it constrains **how the code is written,
structured, or verified** without being observable from outside the running
system.

| Sentence | Plane | Why |
|----------|-------|-----|
| "Serial reconnects within 2 s of replug" | FSD | A black-box tester can verify it |
| "One controller module per instrument" | Method | Invisible from outside; would not survive a rewrite |
| "Flash the SD card with Raspberry Pi Imager" | User Manual | The reader is holding hardware |
| "Deploy with `scp portal.py … && systemctl restart`" | Method | It is how the system is changed |

## Documentation rule

All three planes are present-state and single-home: state a fact once, link to it
everywhere else. See [`standards/documentation.md`](standards/documentation.md).
