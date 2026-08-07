# Gate checks — run by a fresh checker, never by the author

A gate that the working session grades itself is not a gate. The session knows
what it *meant*; it reads its own intent into half-written artefacts and opens
the gate on a project that is not ready. **Every gate check runs in a fresh
subagent that did not author the work and has not seen the conversation.**

## The protocol

1. **The check is generated once, at project start.** `/harness` writes one
   file per gate under `testing/gates/`, filled with *this* project's
   specifics — its FSD path, its requirement id scheme, its DUT and slot, its
   capabilities, its markers, its CI workflow. A generic checklist cannot
   catch a project-specific omission; a generated one can.
2. **When a gate is reached, spawn a checker** with exactly two inputs: the
   gate file, and the repository. No summary of what was done, no reassurance,
   no "we already verified X" — those are the author's claims, and the point
   is to test them.

   **The checker must not read memory.** Not the assistant's memory directory,
   not a prior session's transcript, not `decisions` notes of any kind — and
   the spawning session must not paste their contents into the prompt. Memory
   records what was *decided*; a checker that reads it starts believing
   decisions were executed, which is the exact bias it exists to remove. It
   would then confirm a requirement because someone wrote down that they
   intended it. **Only committed artefacts are evidence**: the spec, the plan,
   the code, the tests, CI results, and what the bench answers right now.
   A checker that cannot find something in the repository has found that it is
   not there — that is a finding, not a reason to go looking elsewhere.
3. **The checker returns a verdict, never a fix.** `OPEN`, or `SHUT` with each
   unmet requirement named, the evidence it looked for, and what it found
   instead. A checker that edits files has stopped being an instrument.
4. **On `SHUT`, the driver loops back** to the step that owns each finding,
   fixes, and re-runs the **whole** check with a **new** checker — a checker
   that has seen the first round is no longer fresh.
5. **The verdict is recorded** in the plan with its date and commit, so a gate
   opened weeks ago against different code is visibly stale rather than
   assumed current.

## What every gate file contains

| Section | Content |
|---|---|
| **Gate** | its name (`Load defined`, `AI harnessed`, `DUT ready`, `Ready for shipment`, `Shipped`) and the phase it closes |
| **Requirements** | one row per thing that must be true, each with *where to look* and *what counts as evidence* — project-specific paths, not categories |
| **Mechanical checks** | commands whose exit status decides — file existence, counts, greps, a CI query, a bench call |
| **Judgement checks** | what cannot be automated, phrased as a question the checker answers with evidence (*"could a competent stranger build a rig from this contract without reading the code?"*) |
| **Traps** | the ways this project could look ready and not be — written from what has actually gone wrong here |
| **Verdict format** | `OPEN` · `SHUT` + findings, nothing else |
| **Standing exclusion** | every generated gate file repeats it: *evidence is committed artefacts and live bench answers only — never memory, transcripts, or the author's account* |

## Writing the checks (this is `/harness`'s job)

- **Name the artefact, not the category.** "Every Must/Should in
  `docs/Functionality/FSD.md` has a `verification:` block" beats "requirements
  are verifiable".
- **Prefer a command over a paragraph** wherever a command can decide.
- **Make the judgement checks answerable with evidence**, not opinion: the
  checker must quote what it read.
- **Grow the traps.** Every time a gate opened on something that turned out
  unready, add the trap that would have caught it. The files improve with the
  project; that is the loop applied to its own gates.

## The five gates and what they demand

| Gate | Demands |
|---|---|
| **Load defined** | requirements atomic, falsifiable, provenance-tagged; every Must/Should carrying a verification contract; architecture, data model, interfaces, state model, config, security profile present; three planes committed |
| **AI harnessed** | plan with capabilities and the journey tests; debugging agenda; testing standard; firmware hooks matching the FSD's scope (no module the spec never asked for); CI green once; runner installed. Behavioural check: a fresh `/build` session states its position without asking anything |
| **DUT ready** | testbench record, DUT record matching the FSD's unit, peer records, forward-path evidence (CI run → flash offsets from `flash_args` → observed marker), project-side capabilities resolved, agenda empty of project-side items |
| **Ready for shipment** | every requirement met — each verifying test `successful`, prohibited outcomes checked; journey green; reconcile empty both directions; every declared test carrying `impl:`; user manual current |
| **Shipped** | release published from a tagged commit rebuilt in the pinned container, and the journey green on the released bytes |

A gate demanding a layer that phase does not own is a bug in the gate file —
see the layer/gate map in `../SKILL.md`.
