# {{PROJECT}} — Harness (HOW)

The **build contract**: the rules for how this project is built and changed.
Entry point for any task: **[`AI-Workflow.md`](AI-Workflow.md)**.

| Path | Contents |
|------|----------|
| `AI-Workflow.md` | The loop every change follows. Read it before touching code. |
| `standards/` | Portable rules, reusable on any project — engineering, testing, documentation governance. Ship as-is; trim what does not apply. |
| `project/` | {{PROJECT}}-specific bindings: layers, source layout, dependency rules, prohibitions, tool pointers. |

A rule belongs here when it constrains **how the code is written, structured, or
verified** without being observable from outside the running system. If a
black-box tester could verify it, it is a requirement and belongs in the FSD.

The plane map, authority order, and routing rule are in [`../00-Overview.md`](../00-Overview.md).
