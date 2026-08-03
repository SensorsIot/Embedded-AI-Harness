# {{PROJECT}} — Documentation

Three planes, three questions, three readers. Every sentence belongs to exactly
one of them.

| Plane | Question | Directory | Reader |
|---|---|---|---|
| **WHAT** | What must be true of the system? | [`Functionality/`](Functionality/) | Anyone judging whether it is correct — reviewer, tester, future maintainer |
| **HOW** | How is it built and changed? | [`Harness/`](Harness/) | Whoever writes the next change, human or agent |
| **OPERATE** | How do I install and run it? | [`UserDocumentation/`](UserDocumentation/) | Whoever installs, drives, or recovers the running system |

**Authority order: the FSD defines the target; the Harness defines the method.**
On conflict the FSD wins on *what must be true*, the Harness wins on *how to get
there*. User documentation describes the system as built — if it disagrees with
either it is stale, which means reality or the spec moved.

None of the three carries history or rationale narrative. Those live in `git log`.

## Where to start

| If you are… | Read |
|---|---|
| Making a change | [`Harness/AI-Workflow.md`](Harness/AI-Workflow.md) — the loop every change follows |
| Judging correctness | `Functionality/{{FSD_FILE}}` — requirements, state model, verification contracts |
| Installing or running it | [`UserDocumentation/`](UserDocumentation/) |
| Wondering why | [`decisions.md`](decisions.md) — settled decisions with provenance, and the alternatives rejected |

## Routing a new sentence

Ask in order; the first yes wins:

1. Externally observable and must be true → **Functionality**
2. Constrains how code is written or verified → **Harness**
3. Tells a human how to run or recover the system → **UserDocumentation**
4. About collaborating with an AI assistant → `CLAUDE.md`, which is not a plane
5. Why a past decision was made → [`decisions.md`](decisions.md) or the commit message

Two questions settle the hard cases. *Could a black-box tester verify it?* — yes
means WHAT. *Would it survive a rewrite in another language?* — no means HOW.

Worked examples: *"reconnects within 30 s"* and *"rejects oversized payloads with
`-1`"* are Functionality. *"One module per component"* and *"lower layers never
import higher ones"* are Harness. *"Flash the SD card with Raspberry Pi Imager"*
is UserDocumentation.

## The document that is not a plane

[`decisions.md`](decisions.md) records what was settled and why, including the
alternatives that were considered and rejected. Consult it before proposing a
change that reverses one — a rejected alternative usually looks like an obvious
improvement in isolation, which is why the reason is written down.

All three planes are present-state and single-home: state a fact once, link to it
from anywhere else. See
[`Harness/standards/documentation.md`](Harness/standards/documentation.md).
