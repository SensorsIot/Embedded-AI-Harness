---
name: define
description: >
  Phase 0 of AI Closed-Loop Programming — Definition: engineers the WHAT the
  loop converges on. Writes and evolves the FSD — atomic, falsifiable,
  provenance-tagged requirements each carrying its verification contract —
  plus architecture, data model, interface definitions, state models,
  configuration catalogues, and a security profile; installs the three
  documentation planes (FSD / Method / UserDocumentation). Works for embedded,
  cloud, mobile, networking, and SDR projects. Use this skill whenever the
  user mentions an FSD, functional spec, requirements, a spec delta or
  amendment, the three planes, a runbook or handbook — even if they never say
  "FSD". Exit gate: Load defined. Test design, the test plan, audit and
  reconcile live in /build, not here.
---

# Define — Phase 0 (FSD skill)

Creates and maintains the **WHAT**: what the system must do, stated so that
compliance can be demonstrated. Every approved Must/Should carries a
**verification contract** — the requirement and its proof are co-engineered,
because attempting the contract *is* the quality gate: a requirement whose
stimulus cannot be stated is not finished.

**Interface with the loop:** contracts flow down — `/build` consumes them,
never edits them. Spec-defect findings flow up — when a declaration or an
executable test proves a contract unsatisfiable, `/build` reports and this
skill amends. A change request's Definition delta lands here
(`/build` → `../build/references/change-request.md`).

## 0. Scope — what this skill does and does not do

**Three things it must never do**: claim a requirement is verified because
code or a test merely exists; turn a recommendation into an approved
requirement silently; invent a normative threshold, tolerance, security
assumption, or failure behaviour.

| Activity | This skill | `/build` (Method) | Dev skills | Workbench skills |
|---|:--:|:--:|:--:|:--:|
| Define scope, requirements, states, interfaces | Yes | No | No | No |
| Write verification contracts | Yes | Consumes | No | No |
| Architecture decisions | Yes (records) | No | May propose | No |
| Design and declare tests, own the plan | No | Yes | No | No |
| Generate firmware and executable tests | No | Dispatches | Yes | Support |
| Execute tests, capture evidence | No | Sequences | Processes | Captures |
| Decide unresolved product questions | No | No | No | No |

**GitHub is the system of record.** The FSD, the plan, tests, and evidence are
version-controlled artefacts; chat history is not authoritative. If the
project has no repository, create it as the first act — `git init`, the §10
skeleton, an initial commit — and commit each artefact as it is finished. An
untracked Method plane is unshared and therefore undocumented.

## 1. Scale and reach

Depth scales to inferred complexity. The core is domain-neutral — embedded,
networking, SDR, IoT, cloud, mobile, hybrid — with optional packs (§14).

## 2. Invocation

**The path to a new FSD is three steps**: sketch the rough idea → `/grill-me`
(shipped in this repo) until the design tree is resolved → this skill writes
it up.
`/harness` sequences this as the journey's Phase 0 when a project starts from
nothing.

Grilling sits outside this skill because the person being interviewed is the
right judge of when it is done. Step 2 must end with the decisions **absorbed
into the planes** — a decision living only in a transcript is re-assumed next
session, and there is **no decisions file**: a settled decision leaves its
*effect* as present-state content in the plane it governs (a rejected
alternative that is load-bearing becomes a stated negative requirement; mere
preferences leave no residue and may be legitimately re-decided when the
environment changes).

Four modes. Pick by what already exists and what the user is asking for.

| Mode | Invoke | Use when |
|------|--------|----------|
| **create** | `/define` + description | No FSD yet. **Harvest first** (§4), then ask only what is still open — 1–3 questions per round — and generate. |
| **update** | `/define update <path>` + delta | An FSD exists. Apply the delta surgically — never regenerate the whole file, never renumber a stable ID. Change-request deltas land here. |
| **grill** | `/define --grill` + description | **Cold start only** — no prior conversation, a brief too thin to infer architecture from. One question at a time, depth-first, each with a recommended answer. |
| **planes** | `/define --planes [path]` | Write the Method and UserDocumentation planes, or retrofit an existing doc set into the three planes. Preview the move plan and get confirmation **before** moving anything. |

Test design, audit, and reconcile are `/build` modes — the loop's, not the
spec's.

One rule holds across every mode: **never renumber a stable ID.** Obsolete
items are `deprecated` or `superseded`, never deleted. A value this skill
proposed stays `status: proposed` until accepted
(`references/requirement-quality.md` §2).

Per-mode steps, the `update` search order, and grill discipline:
`references/authoring.md`.

## 3. Tools

Use **Edit** rather than **Write** in `update` mode so unaffected chapters
stay byte-identical, and **AskUserQuestion** for clarifications so each one
carries its recommended answer.

## 4. Clarifying questions

**Harvest before asking.** Look in order: decisions settled earlier in the
conversation (a `/grill-me` session), a prior FSD, then the repo itself —
config files, protocol usage, `README.md`, `CLAUDE.md`. Tag each harvested
decision `[user]` so it is never mistaken for something the skill assumed.
Re-asking an answered question earns a shorter answer the second time.

Then ask only when what is *still* missing affects architecture, protocol
choice, interface definition, safety or regulatory constraints, phase
decomposition, platform, or an external integration. Everything else is
inferred and marked `(assumed)`.

**Every question carries a recommended answer.**

(The two unharvestable questions — the debugging agenda and the standard run —
belong to the journey, not the spec: `/harness` asks them at the end of Phase
1, and `/build` consumes the answers.)

## 5. Complexity scaling

Low / Medium / High, judged from component count, protocol count, external
integrations, real-time constraints, and domain:
`references/complexity-scaling.md`.

## 6. Information extraction and inference

### 6.4 Functional Requirements

- **State each requirement in the chapter of the component it constrains** —
  no global FR section in the Parts scheme (§7).
- Two ID conventions (pick one per project; `references/canonical-fsd-structure.md`):
  `FR-x.y`/`NFR-x.y [Must/Should/May]`, or stable clause IDs.
- Priorities **Must** / **Should** / **May**; "shall" language.

#### 6.4.1 Atomic and falsifiable

**Atomic** — one obligation. Split anything joining two verbs, a behaviour and
a deadline, a success and a failure path, or a list of outputs.

**Falsifiable** — a competent stranger can build a rig that returns pass or
fail: precondition, stimulus, observable response, deadline, tolerance,
failure behaviour, tier. Reject weasel words outright — *appropriate,
graceful, user-friendly, as needed, reasonable, sufficient, robust, seamless,
acceptable, normal operation, best effort* — and vacuous quantifiers.

Full rules, the 13-check gate, worked examples, and the verification contract
schema: **`references/requirement-quality.md`**.

### 6.5 Non-Functional Requirements

Performance, reliability, accuracy, scalability, power, security — all
obeying §6.4.1. "95th percentile API response under 200 ms at 50 concurrent
clients", never "responsive".

#### 6.5.1 Security profile before security requirements

Establish the **threat model first**, then derive. Where the profile does not
justify a protection, record an accepted risk in §5 — an honest "we do not
claim confidentiality at rest" beats a requirement nobody implements.
**Obfuscation is never encryption.** Checklist: `references/system-models.md` §7.

### 6.9 Verification contracts — the WHAT side of testing

On every approved Must/Should, beside the requirement in the FSD:
preconditions, stimulus, expected observations, timing, tolerance,
**prohibited outcomes**, tier, evidence, cleanup. The contract establishes
normative intent — schema in `references/requirement-quality.md` §4.

Everything downstream of the contract — the plan entry, test design, the four
kinds, the chain, status, gaps — is `/build`'s. There is **no separate
test-specification layer** between contract and plan entry.

#### 6.9.1 State model — mandatory for stateful systems

Modes that persist between events — provisioning, connecting, operational,
degraded, recovery — get a formal state model. The **transition table is
normative** (from · event · guard · to · action · limit); every (state ×
event) pair handled, explicitly ignored, or impossible-by-construction with a
stated reason. Every normative row is a requirement. Bugs live in the
transitions, and a requirement list that never names a state cannot express
what happens when WiFi drops *during* provisioning.
`references/system-models.md` §3.

### 6.10 Component layering

Every FSD gets a layered component architecture in §2.4 — **L0 foundation →
L1 interfaces → L2 application logic**, strict one-way dependency; the L0/L1
line is ownership. The FSD body mirrors the layers; §x.0 Test Architecture
maps layers to tiers and references the generated matrix. Layer profiles and
tier taxonomy: `../build/references/test-architecture.md`. Source-layout rules
are HOW and live in the Method plane, not here.

### 6.11 The three planes

| Plane | Question | Document |
|-------|----------|----------|
| **WHAT** | What must be true? | the FSD |
| **HOW** | How is it built and changed? | `docs/Method/` |
| **OPERATE** | How do I run it? | `docs/UserDocumentation/` |

Ask in order, first yes wins: externally observable ⇒ FSD; constrains how code
is written or verified ⇒ Method; tells a human how to run or recover it ⇒
UserDocumentation; about collaborating with the assistant ⇒ `CLAUDE.md` (not a
plane); why a past decision was made ⇒ commit message.

Two questions settle hard cases: *could a black-box tester verify it?* (yes ⇒
WHAT); *would it survive a rewrite in another language?* (no ⇒ HOW).

Planes are roles, not filenames — bind to a document that already fills the
role. The Method plane must be committed. Never invent a fourth plane.

Full model, retrofit procedure, templates: **`references/three-planes.md`**,
`references/templates/`.

## 7. Canonical FSD structure

Layer-grouped **Parts** scheme: front matter (§1 Overview, §2 Architecture
incl. §2.4, §3 Phases, §4 Risks), then Part A Application logic · Part B
Interfaces · Part C Foundation · Part D Cross-cutting · Part E Operations &
Verification, then appendices. Each component is a self-contained chapter;
numbering flat; depth ≤ `####`. No global FR or Interface section. Full
skeleton: `references/canonical-fsd-structure.md`.

## 8. Traceability

Computed by `/build`'s report from the plan — never a hand-maintained
Covered/GAP column in the FSD. The FSD carries requirement IDs and contracts;
the plan carries the tests that cite them and what they last produced.

## 10. Output layout

```text
docs/00-Overview.md       the plane map — at the docs root
docs/Functionality/       WHAT   — the FSD (or single FSD file, small projects)
docs/Method/              HOW    — 00-Overview · AI-Workflow · standards/ · project/
docs/UserDocumentation/   OPERATE — one user manual with chapters, from day one

testing/test-plan.yaml    every test, what it needs, what it produced (/build owns)
tests/{host,target,bench}/   executable tests (written by dev skills)
test-results/<run-id>/       evidence (captured by workbench skills)
```

**Create all three plane directories on the first commit, including the empty
one.** The user manual ships from the start with an honest status line
(`references/templates/user-documentation/`). **The OPERATE plane is one
manual with chapters, not a directory** — add a chapter, never a sibling.
There is no decisions file (§2). **Match the repo** — bind to existing
documents filling a plane's role rather than creating competitors.

## 11–12. Example output · evolve mode

Worked FSD excerpt: `references/example-output.md`. Preserve / update / add /
remove rules for deltas: `references/evolve-mode.md`.

## 12.5 Exit — Load defined

### Deliverables

| Deliverable | Content |
|---|---|
| **FSD** | requirements — atomic, falsifiable, provenance-tagged — each Must/Should carrying its verification contract; architecture (§2.4 layers); data model; interface definitions; state model where the system is stateful; configuration catalogue; security profile |
| **Method plane** | `docs/Method/` — build contract, standards, project bindings |
| **User manual** | `docs/UserDocumentation/` — from day one, with an honest status line |
| **Plane map** | `docs/00-Overview.md` |

The test plan is **not** here — it is Phase 1's (`/harness` step 4).

### The check — run it, report every failure

```bash
test -f docs/00-Overview.md && ls docs/Method/ docs/UserDocumentation/   # planes exist
grep -c "shall" <fsd>                                                    # requirements present
```

Then, per requirement, the gate that cannot be automated: **does it carry a
verification contract, and could a competent stranger build a rig from it that
returns pass or fail?** A requirement without a contract is unfinished; a
contract nobody could execute is a specification defect, not a test problem.

Then, per phase, the same question asked of §3: **can each phase be entered
using only what an earlier phase delivered?** Walk the phases in order and, for
each exit criterion, name the phase that supplies every capability it rests on.
A phase whose exit needs something a later phase builds is a sequencing defect
and returns to §3 — the requirements can all be perfect while the order in
which they are met is impossible. The failure is invisible per-requirement,
because each one is individually satisfiable; only the sequence is wrong. A
device configured solely through a portal cannot publish before the portal
exists, however well FR-PUB-01 is written.

Finally run the full quality checklist in `references/finalisation.md` §1 —
the 13 checks, weasel words, provenance, unbound `{{parameters}}` — and
**report each failure rather than shipping past it**.

**Run it in a fresh checker** using this project's `testing/gates/` file once
it exists (`../build/references/gate-checks.md`); on a project too young to
have one, run the checklist yourself and say so.

**The gate loops, it does not wave through.** Any check that fails sends the
work back to the step that owns it — a requirement without a contract returns
to requirement writing, a failed finalisation item to the section it belongs
to — and the whole check runs again afterwards. Phase 1 does not start on a
partial FSD.

**Load defined** — derived, never declared: every Must/Should has a contract,
every phase is enterable from the one before it, the three planes exist and are
committed, and no `(assumed)` marker remains on anything architecture-critical.

## 13. Finalisation

Before delivering, run the quality gate and fill the lifecycle metadata block:
**`references/finalisation.md`**. Report every failed check — a checklist run
silently and reported as passed is worth nothing.

## 13.1 Reference index

| File | Covers |
|------|--------|
| `references/finalisation.md` | Pre-delivery checklist, lifecycle metadata. Load at the end |
| `references/requirement-quality.md` | Statement types, provenance and status, the 13-check gate, the verification contract |
| `references/system-models.md` | Context, components, state model, interfaces, configuration and data catalogues, security profile |
| `references/three-planes.md` | WHAT / HOW / OPERATE model, routing, retrofit |
| `references/templates/` | `00-Overview` (docs root), the Method set, the user-manual stub |
| `references/canonical-fsd-structure.md` | Parts scheme and chapter skeleton |
| `references/complexity-scaling.md` | Depth scaling |
| `references/evolve-mode.md` | Delta rules |
| `references/example-output.md` | Worked FSD excerpt |
| `references/domains/` | Domain packs (ESP32) — requirement proposals |

## 14. Domain packs

Domains with recurring shapes get a pack under
`references/domains/<domain>.md`, loaded only when the project matches:
**detect** from description and code, **apply** its layer profile and tier
names, and **propose — never adopt**. Detecting `esp_mqtt` proves the project
speaks MQTT, not that it owes anyone offline buffering. Present matches via
`AskUserQuestion` with a recommendation, write only what is accepted, record
declines under *Explicitly out of scope*, tag provenance
(`[user]`/`[derived]`/`[code]`/`[pack:<domain>]`), bind every `{{parameter}}`.
**Run the pack backwards too** — what it detected that the decisions never
mention is either out of scope or a capability nobody thought of.

| Pack | Domain |
|------|--------|
| `esp32` | ESP-IDF / Arduino-ESP32: WiFi, BLE, MQTT, OTA, NVS, captive portal, watchdog, logging — test-case libraries live with `/build` (`../build/references/domains/esp32/`) |
