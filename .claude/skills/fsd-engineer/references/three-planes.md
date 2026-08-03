# The three documentation planes — WHAT / HOW / OPERATE

A project's documentation answers three different questions for three different
readers. Mixing them is the single most common reason specs rot: a document that
tries to be all three is edited by everyone, owned by no one, and contradicts
itself within a release.

| Plane | Question | Document | Reader |
|-------|----------|----------|--------|
| **WHAT** | What must be true of this system? | **FSD** | Anyone judging whether the system is correct — reviewer, tester, auditor, future maintainer |
| **HOW** | How is this system built and changed? | **Harness** | Whoever writes the next change — a person or an AI agent |
| **OPERATE** | How do I run it? | **User documentation** (`docs/UserDocumentation/`) | Whoever installs, drives, or recovers the running system |

## Authority order

1. **FSD (WHAT)** defines the target. It is the contract.
2. **Harness (HOW)** defines the method. It cannot change the target.
3. **User documentation (OPERATE)** describes the running system as built.

On conflict: the FSD wins on *what must be true*; the Harness wins on *how to get
there*. If the user documentation disagrees with either, it is stale — it
describes reality, so a disagreement means either reality or the spec moved.

None of the three carries history, rationale narrative, or temporal comparison.
That is what `git log` is for. Every plane is written in the present tense about
the current state.

## Routing rule — where does this sentence go?

Ask in order; the first "yes" wins:

1. Does it state something that must be **externally observable and true** of the
   running system? → **FSD**. ("Reconnects within 30 s." "Rejects payloads over
   1 KB with `-1`.")
2. Does it constrain **how the code is written, structured, or verified**, without
   being observable from outside? → **Harness**. ("One module per component."
   "Lower layers never import higher ones." "Every change ships its test.")
3. Does it tell a human **how to run, install, or recover** the system? →
   **UserDocumentation**. ("Flash the SD card." "If the dongle wedges, POST /api/sdr/reset.")
4. Is it about **how to collaborate with the AI assistant** rather than about the
   project? → `CLAUDE.md`, which is *not* project documentation and is not a
   plane.
5. Is it **why a past decision was made**? → the commit message or an ADR. Not
   the planes.

### The tests that decide the hard cases

- **"Could a black-box tester verify it?"** If yes it is WHAT; if it needs to read
  the source, it is HOW. *"Serial reconnects within 2 s"* is WHAT. *"The reconnect
  logic lives in one module"* is HOW.
- **"Would this survive a rewrite in another language?"** If yes it is WHAT. Layer
  diagrams, module boundaries, and naming conventions would not survive — HOW.
- **"Is the reader holding hardware right now?"** Then it is OPERATE.

## What each plane contains

**FSD (WHAT)** — purpose, architecture *as observable behaviour*, interfaces and
their contracts, requirements (atomic, falsifiable, provenance-tagged), the state
model, acceptance criteria and verification tiers, risks and assumptions. It names
the tier a requirement is verified at; it does not contain test steps.

**Harness (HOW)** — the build contract:
- `00-Overview.md` — the plane map and authority order.
- `AI-Workflow.md` — the loop every change follows. This is the entry point.
- `standards/` — portable rules reusable on any project (engineering conventions,
  testing, documentation governance, naming).
- `project/` — this project's bindings: layer definitions, source layout, module
  boundaries, dependency direction, prohibitions, tool and credential pointers.

**User documentation (OPERATE)** — installation, wiring, day-to-day procedures, diagnostics,
recovery. Step-by-step detail lives here and nowhere else.

## Topology

The planes are roles, not filenames. Bind them to whatever the project already
has rather than forcing new files:

| Role | Typical binding |
|------|-----------------|
| `[SPEC]` | `docs/Functionality/` — the FSD, or a set of per-component FSDs |
| `[HARNESS]` | `docs/Harness/` (must be committed — an untracked harness is unshared, therefore undocumented) |
| `[OPERATE]` | `docs/UserDocumentation/` — created from the first commit, even when empty |

The WHAT plane may be a single FSD or a set of per-component FSDs; the other two
planes are shared either way. If the project already has a document filling a
role, **bind to it** — do not create a competing parallel file.

## Applying this to an existing project

1. **Inventory.** List every existing document and the role it currently fills.
2. **Triage each section** with the routing rule above. An existing FSD almost
   always has HOW and OPERATE content mixed in — layer conventions, build
   commands, install steps.
3. **Preview the plan** before moving anything: every move as `from → to`, every
   new file, every section being scrubbed of history. Get confirmation.
4. **Move content, don't rewrite it.** Use `git mv` for whole files so history
   follows. For sections, cut and paste verbatim, then scrub tense.
5. **Leave a pointer** where content used to live if anything links to it.
6. **Verify** no cross-references broke and no content was lost — diff the sorted
   non-blank lines of before and after; only headings should differ.

## Anti-patterns

| Pattern | Why it fails |
|---------|--------------|
| A fourth plane ("Design", "Notes", "Architecture") | Content that fits none of three fits none at all — it is HOW with a different hat. |
| Harness kept untracked or in a private config | Unversioned ⇒ unshared ⇒ effectively undocumented. |
| The same fact stated in two planes | They diverge on the first edit. Link, never restate. |
| Test steps in the FSD | The FSD names the tier and criterion; the test skills own the steps. |
| History in any plane | "Previously the API used X" belongs in `git log`. |
| `CLAUDE.md` used as the Harness | It is assistant configuration, not project documentation, and is often gitignored. |
