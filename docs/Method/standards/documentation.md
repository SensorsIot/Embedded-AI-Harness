# Standard — Documentation governance (portable)

All project documentation is **present-state**, lives in **one canonical home**,
and is routed by the **WHAT / HOW / OPERATE** triage.

## The three rules

**Present-state.** Write what is true now, in the present tense. No history, no
rationale narrative, no temporal comparison. Delete on sight: "now uses",
"previously", "as of v2", "we decided to", "legacy", "this was changed because".
Version history belongs in `git log`; a dated revision-history table is the one
sanctioned exception, and only in the FSD.

**One canonical home.** Every fact is stated once. Anywhere else that needs it,
link. Two copies of a fact are two facts the moment one is edited, and the reader
has no way to tell which is current.

**Routed by plane.** Before writing a sentence, decide which plane owns it:

1. Externally observable and must be true → **FSD**
2. Constrains how code is written or verified → **Method**
3. Tells a human how to run or recover the system → **Handbook**
4. About collaborating with the AI assistant → `CLAUDE.md` (not a plane, not
   project documentation)
5. Why a past decision was made → commit message or ADR

## Procedures

**A — Authoring.** Route with the rule above, place it in that plane's existing
chapter (create one only if none fits), and link rather than restate anything
already documented elsewhere.

**B — After a change.** The WHAT absorbs new behaviour (verify against the code,
don't transcribe it); the Handbook absorbs anything an operator sees; the Method
changes only if the lesson is universally true for the project. Then reconcile:
walk the doc against the implementation and classify each rule as compliant,
deviating, or missing. Deviations fix the code. Finally, scrub tense.

## Review checklist

- [ ] No history, rationale narrative, or temporal words
- [ ] No fact stated in two places
- [ ] Every section is in the right plane
- [ ] All cross-references resolve
- [ ] No placeholder or `TODO` text left behind
