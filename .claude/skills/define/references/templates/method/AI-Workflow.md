# {{PROJECT}} — AI Workflow (the build contract)

Read this before any change. It is how new functionality is built and how the
documentation stays in sync with it.

## The loop

**1. Locate the contract.** Find the FSD rule the work serves in `{{FSD_PATH}}`.
If none exists, the work starts by defining the **WHAT** — a new, atomic,
falsifiable requirement — not by writing code. A change with no rule behind it is
either scope creep or an undocumented requirement; both need resolving before
implementation.

**2. Build per the Method.** Follow `standards/` and `project/`. Reuse an
existing module, helper, or skill before adding new code. Make the smallest change
that satisfies the rule — no speculative scope, no drive-by refactors.

**3. Test — the gate, not an afterthought.** A change is **not done** until its
test exists and passes. Per `standards/testing.md`: add or update the test case in
the owning spec's test chapter, add the test beside the code, and run the suite
green. A bug fix writes its **regression test first**, and that test must fail
before the fix and pass after — a regression test that never failed proves
nothing.

**4. Reconcile the documentation.**
- The **FSD** absorbs new or changed behaviour — *verify, don't transcribe*. If
  the code deviates from the intended spec, fix the code; do not enshrine the
  defect as a requirement.
- The **user documentation** absorbs anything an operator would notice.
- The **Method stays put** unless the change taught a rule that is *universally*
  true for this project, not just for this change.
- All present-state. No "now uses", no "previously".

**5. Verify both directions.** Confirm the implementation matches the FSD, and
that no FSD rule is silently unimplemented. Deviations fix the code; genuine gaps
get documented as such; contradictions get escalated rather than guessed at.

## Requirement quality gate

Before a new requirement enters the FSD it must be:

- **Atomic** — one obligation. Split anything joining two verbs, a behaviour and a
  deadline, or a success and a failure path.
- **Falsifiable** — precondition, stimulus, observable response, deadline,
  tolerance, failure behaviour, verification tier.
- **Free of weasel words** — *appropriate, graceful, user-friendly, reasonable,
  sufficient, robust, seamless, acceptable, normal operation, best effort*.
- **Provenance-tagged** — `[user]`, `[derived]`, `[code]`, or `[pack:<domain>]`.

## Roles

<Who may change which plane; which changes need review; who arbitrates a
contradiction between planes.>
