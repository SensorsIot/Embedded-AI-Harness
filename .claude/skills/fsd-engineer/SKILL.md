---
name: fsd-engineer
description: >
  Engineers a system's specification and its verification together — what the
  system must do, and how compliance will be demonstrated. Writes and evolves the
  FSD, the Harness (build contract) and the Handbook (operations); turns vague
  intent into atomic, falsifiable, provenance-tagged requirements with state
  models, interface and configuration catalogues, a security profile, complete
  test specifications, host/target/bench tiers, and traceability that never
  mistakes a code tag or a coverage hit for proof. Works for embedded, cloud,
  mobile, networking, and SDR projects. Use this skill whenever the user mentions
  an FSD, functional spec, requirements, test specs or test design, traceability,
  coverage gaps, verification, a runbook or handbook, or wants a spec reconciled
  against drifted code — even if they never say "FSD".
---

# FSD Engineer Skill

Creates and maintains the **engineering contract** from which both implementation
and verification are derived:

```text
What the system must do  +  How compliance will be demonstrated
```

It is not a document generator. It engineers requirements, testability,
verification specifications, traceability, lifecycle updates, and the handoffs to
whoever implements and executes.

## 0. Scope — what this skill does and does not do

**Three things it must never do**, none of which the table below can express:
claim a requirement is verified because code or a test merely exists; turn a
recommendation into an approved requirement silently; invent a normative
threshold, tolerance, security assumption, or failure behaviour.

| Activity | This skill | Development skills | Workbench skills |
|---|:--:|:--:|:--:|
| Inspect repository | Yes | As needed | No |
| Define scope, requirements, states, interfaces | Yes | No | No |
| Architecture decisions | Yes (records) | May propose | No |
| Design test specifications | Yes | No | No |
| Define required evidence | Yes | No | No |
| Generate production firmware | No | Yes | No |
| Generate executable tests | Handoff only | Yes | Support |
| Build and flash | No | Yes | Support |
| Operate WiFi, MQTT, BLE, GPIO, RF | No | Coordinates | Yes |
| Execute tests, capture raw evidence | Defines | Processes | Captures |
| Maintain traceability | Yes | Supplies mappings | Supplies results |
| Decide unresolved product questions | No | No | No |

**GitHub is the system of record.** The FSD, decisions, test specifications,
traceability, executable tests, evidence, and corrections are ordinary
version-controlled artefacts. Chat history is not authoritative.

## 1. Scale and reach

Depth scales to inferred complexity. The core is domain-neutral — embedded,
networking, SDR, IoT, cloud, mobile, hybrid — with optional packs (§14) for
domains that have recurring shapes.

## 2. Invocation

**The path to a new FSD is three steps, and this skill is the third:** sketch the
rough idea → `/grill-me` it until the design tree is resolved → `/fsd-engineer`
writes it up.

Grilling sits outside this skill because the person being interviewed is the
right judge of when it is done; a skill deciding that for itself either stops
early and assumes, or asks past the point of value. Step 2 must end with the
decisions **written down** — a decision living only in a transcript is re-assumed
next session.

Seven modes. Pick by what already exists and what the user is asking for.

| Mode | Invoke | Use when |
|------|--------|----------|
| **create** | `/fsd-engineer` + description | No FSD yet. **Harvest first** (§4), then ask only what is still open — 1–3 questions per round — and generate. |
| **update** | `/fsd-engineer update <path>` + delta | An FSD exists. Apply the delta surgically — never regenerate the whole file, never renumber a stable ID. |
| **grill** | `/fsd-engineer --grill` + description | **Cold start only** — invoked with no prior conversation and no decisions file, on a brief too thin to infer architecture from. If step 2 above already happened, use `create` instead. One question at a time, depth-first, each with a recommended answer. |
| **planes** | `/fsd-engineer --planes [path]` | Write the Harness and Handbook, or retrofit an existing doc set into the three planes. Preview the move plan and get confirmation **before** moving anything. |
| **tests** | `/fsd-engineer tests <path>` | The FSD is stable but its verification is not. Runs clause inventory → tier allocation → controllability → required test classes, emitting specs plus an updated matrix. |
| **audit** | `/fsd-engineer audit` | Answers "are we actually done?" — reports the lifecycle state of every requirement and the gaps by category. Expect most requirements to sit below *verified*; that is information, not failure. |
| **reconcile** | `/fsd-engineer reconcile` | Code, tests, and documents drifted apart. Identifies undocumented behaviour, obsolete tests, stale evidence, contradictions — and **proposes**, never silently adopts. |

Two rules hold across every mode, because violating either quietly destroys trust
in the document: **never renumber a stable ID** (obsolete items are `deprecated`
or `superseded`, never deleted, so historical results stay readable), and **never
silently invent a normative value** (report it; a proposal stays
`status: proposed` until accepted — `references/requirement-quality.md` §2).

Per-mode steps, the `update` search order, and grill discipline:
`references/authoring.md`.

## 3. Tools

Standard Claude Code tooling. Two notes that matter: use **Edit** rather than
**Write** in `update` mode so unaffected chapters stay byte-identical, and use
**AskUserQuestion** for clarifications so each one carries its recommended answer.

Context-gathering order and evolve-mode diff discipline: `references/authoring.md`.

## 4. Clarifying questions

**Harvest before asking.** Most answers already exist by the time this skill
runs. Look in order: decisions settled earlier in the conversation (a
`/grill-me` session), a `decisions.md` / `open-issues.md`, a prior FSD, then the
repo itself — config files, protocol usage, `README.md`, `CLAUDE.md`. Treat what
they settle as settled, and tag each harvested decision `[user]` so it is never
later mistaken for something the skill assumed.

Re-asking a question the user has already answered is the fastest way to make a
spec feel like a form to fill in — and it earns a shorter answer the second time.

Then ask only when what is *still* missing affects architecture, protocol choice,
interface definition, safety or regulatory constraints, phase decomposition,
platform, or an external integration. Everything else is inferred and marked
`(assumed)`.

**Every question carries a recommended answer**, so the user can accept with one
word. A bare list of options pushes the work back onto them.

When to ask, how to phrase, safe inferences, and worked examples:
`references/authoring.md`.

## 5. Complexity scaling

Scale FSD depth to inferred complexity (Low / Medium / High), judged from
component count, protocol count, external integrations, real-time constraints,
and domain.

For the full complexity tiers table, complexity signals, and per-section scaling behavior matrix, read `references/complexity-scaling.md`.

## 6. Information Extraction & Inference Rules

Given the rough description, the skill must extract or infer the following:

### 6.4 Functional Requirements (FR)

Convert each described behavior into a stated requirement:
- **State each requirement in the chapter of the component it constrains** — there
  is no global Functional Requirements section in the Parts scheme (Section 7). A
  requirement about the meter decoder lives in the meter-decoder interface chapter;
  one about the control loop lives in that L2 feature chapter.
- **Two conventions** (pick one per project; see
  `references/canonical-fsd-structure.md`): `FR-x.y`/`NFR-x.y [Must/Should/May]`
  (the lightweight default), or **stable clause IDs + generated traceability** (a
  finer-grained, higher-assurance alternative for large FSDs — every assertion gets
  a stable ID, tests cite it, code is `@fsd`-tagged, a tool generates the matrix).
- Assign priority: **Must** / **Should** / **May**
- Use "shall" language: "The system shall..."

Example:
> "Device sends sensor readings every minute and on threshold events."

Becomes:
- **FR-1.1** [Must]: The device shall send periodic sensor measurements at a
  configurable interval (default: 60 s).
- **FR-1.2** [Must]: The device shall send an immediate measurement when a
  threshold condition is met.

#### 6.4.1 Atomic and falsifiable

Two properties decide whether a requirement is finished.

**Atomic** — one obligation. Split anything joining two verbs, a behaviour and a
deadline, a success and a failure path, or a list of outputs. "Convert text to HID
reports and deliver within 50 ms" is three obligations that fail independently.

**Falsifiable** — a competent stranger can build a rig that returns pass or fail.
That needs a precondition, stimulus, observable response, deadline, tolerance,
failure behaviour, and verification tier. Attempting to write those *is* the
quality check, which is why it happens here and not downstream.

Reject weasel words outright — *appropriate, graceful, user-friendly, as needed,
reasonable, sufficient, robust, seamless, acceptable, normal operation, best
effort* — and vacuous quantifiers: "no data loss" needs a window and a delivery
guarantee.

Full rules, the 13-check gate, worked before/after examples, and the verification
contract schema: **`references/requirement-quality.md`**.

### 6.5 Non-Functional Requirements (NFR)

Extract or infer key NFRs with priorities:
- Performance (latency, throughput)
- Reliability / uptime
- Accuracy / precision
- Scalability
- Power consumption (embedded)
- Security and privacy (authentication, encryption, access control)

NFRs obey §6.4.1 too. "The system shall be responsive" is not an NFR; "95th
percentile API response under 200 ms at 50 concurrent clients" is.

#### 6.5.1 Security profile before security requirements

Never import individual security requirements — establish the **threat model
first**, then derive. "Credentials shall be encrypted at rest" is meaningless
until you know who the attacker is, what physical access they have, and what the
platform actually costs you to provide it.

Where the profile does not justify a protection, say so and record it in §5 Risks
as an accepted risk. An honest "we do not claim confidentiality at rest" beats a
requirement nobody implements. **Obfuscation is never encryption**, and
"encrypted or obfuscated" is not an acceptance criterion — it cannot fail.

Full profile checklist: `references/system-models.md` §7.

### 6.9 Verification — this skill owns test design end to end

Requirements and their verification are **co-engineered**. A requirement is not
complete because it reads well; it is complete when a test can be derived from
it. Attempting that derivation *is* the quality check — which is why design
happens here rather than in a downstream skill.

Two artefacts, two levels of detail:

1. **Verification contract** — on every approved Must/Should, in the FSD beside
   the requirement: preconditions, stimulus, expected observations, timing,
   tolerance, **prohibited outcomes**, tier, evidence, cleanup. Establishes
   normative intent. → `references/requirement-quality.md` §4
2. **Test specification** — the executable-ready design: test data, equipment,
   pass and failure criteria, required evidence, cleanup, failure recovery, and
   the automation handoff. → `references/test-design.md`,
   `references/test-spec-schema.md`

The readable FSD carries requirements and contracts; full specs live under
`verification/test-specs/` and are linked, not inlined. This skill designs them;
who implements and runs them is in §0.

#### 6.9.1 State model — mandatory for stateful systems

If the system has modes that persist between events — provisioning, connecting,
operational, degraded, recovery — the FSD **must** carry a formal state model.
Not optional prose, not a nice-to-have diagram.

This is where connected devices actually fail. Bugs rarely live on the happy
path; they live in the transitions. A requirement list that never names a state
cannot express what happens when WiFi drops *during* provisioning, and the tests
inherit the blindness.

The **transition table is normative** (from · event · guard · to · action ·
limit); any diagram is generated from it. Every (state × event) pair is handled,
explicitly ignored, or impossible-by-construction with a stated reason. Every
normative row is a requirement and maps to at least one state-transition test —
cover **transitions, not states**.

Trigger conditions, required contents, persistence rules, and the completeness
rule: `references/system-models.md` §3.

### 6.10 Component layering and test architecture

Give every FSD a layered component architecture in §2.4 that the test strategy
falls out of. Classify each component into a layer with a strict one-way
dependency — **L0 foundation → L1 interfaces → L2 application logic** — where the
L0/L1 line is ownership: a managed client to an external service is foundation, a
hand-written decoder or driver is an interface. Three layers is the common
default; add more when the system genuinely has more one-way-dependent tiers.

The FSD body mirrors these layers: each component is a self-contained chapter
grouped under layer Parts. §x.0 Test Architecture then maps layers to tiers and
references a generated component × tier matrix.

**Source-layout rules are HOW, so they live in the Harness**, not here — one
module per component, lower layers never importing higher ones, pure cores
extracted. None is observable from outside a running system.

Layer profiles, tier definitions, the diagram convention, and the matrix:
**`references/test-architecture.md`**.

### 6.11 The three planes

Documentation answers three questions for three readers, and mixing them is why
specs rot. Route every sentence to exactly one:

| Plane | Question | Document |
|-------|----------|----------|
| **WHAT** | What must be true? | FSD |
| **HOW** | How is it built and changed? | Harness |
| **OPERATE** | How do I run it? | Handbook |

Ask in order, first yes wins: externally observable ⇒ **FSD**; constrains how
code is written or verified ⇒ **Harness**; tells a human how to run or recover it
⇒ **Handbook**; about collaborating with the assistant ⇒ `CLAUDE.md`, which is not
a plane; why a past decision was made ⇒ commit message or ADR.

Two questions settle the hard cases: *could a black-box tester verify it?* (yes ⇒
WHAT) and *would it survive a rewrite in another language?* (no ⇒ HOW).

Planes are roles, not filenames — bind to a document that already fills the role
rather than creating a competitor. The Harness must be committed. Never invent a
fourth plane; content fitting none of the three is HOW wearing a hat.

Full model, retrofit procedure, anti-patterns, and the templates to instantiate:
**`references/three-planes.md`** and `references/templates/`.

## 7. Canonical FSD Structure (Layer-grouped "Parts" scheme)

FSDs are organized **by architectural layer**, not by document-section type. After
the front matter (§1 Overview, §2 Architecture incl. §2.4 Component Layering, §3
Phases, §4 Risks), the body is grouped under unnumbered **Part** dividers that
mirror the §2.4 layers — **Part A** Application logic (L2), **Part B** Interfaces
(L1), **Part C** Foundation/transport (L0), **Part D** Cross-cutting concerns,
**Part E** Operations & Verification — followed by Appendices and an optional
Related (`[[wikilinks]]`) section.

Each interface, feature, and concern is its **own self-contained chapter**
(requirements + interface + behavior + failure modes together); chapters are
numbered flat across the whole document; depth is capped at four heading levels
(`####`). There is **no global Functional Requirements or Interface
Specifications section** — those dissolve into the component chapters.

For Low-complexity projects the Part dividers may be dropped (list the few
chapters directly, still in layer order). For the full skeleton, the
chapter-internal structure, section-inclusion rules, complexity scaling, and the
migration map from the older flat layout, read
`references/canonical-fsd-structure.md`.

## 8. Traceability — generated, seven states

Traceability separates **mapping** from **verification**. Collapsing them is the
most consequential error this skill can make: it turns "we wrote something down"
into "it works" without anyone deciding to.

```text
Specified → Test designed → Implementation mapped → Executable test implemented
          → Test executed → Evidence captured → Requirement verified
```

Each is a separate field, never one `covered` flag. An `@fsd` tag proves only
that a source location *claims* responsibility; coverage proves only that lines
ran; a passing test proves nothing about assertions it does not contain — which
is why `prohibited_outcomes` exists.

The matrix, lifecycle states, and gap categories are **computed**; the FSD
references their paths and never hand-maintains a Covered/GAP column. Evidence
records commit and environment so staleness is computed, not guessed.

Full model, tag rules, evidence fields, gap categories, optional coverage check:
**`references/traceability.md`**.

## 10. Output layout

Three readable planes plus machine-readable verification data:

```text
docs/    <project>-fsd.md · Harness/ · <project>-handbook.md
         architecture-decisions.md · open-issues.md
verification/   requirements · states · interfaces · configuration ·
                test-specs/ · traceability · implementation-handoff · gaps
tests/{host,target,bench}/      executable tests (written by dev skills)
test-results/<run-id>/          evidence (captured by workbench skills)
```

`verification/` is **not** a fourth plane — it is the machine-readable form of
WHAT; `test-results/` is evidence, not documentation. Small projects may use
fewer files, but the information model stays the same.

**Match the repo.** If it already uses `Documents/` or another convention, follow
it. If a document already fills a plane's role, bind to it — never create a
competitor.

Default paths, explicit-path handling, and evolve-mode targeting:
`references/authoring.md`.

## 11. Example Output Snippet

For a complete example FSD snippet (medium-complexity BLE HID Keyboard project) showing expected tone, structure, and detail level, read `references/example-output.md`.

## 12. Evolve Mode -- Detailed Behavior

When updating an existing FSD, follow strict rules for what to preserve, update, add, and remove. Key principles: never renumber existing IDs, keep the traceability matrix generated (never hand-edited), flag contradictions before overwriting. For the complete evolve mode rules (preserve/update/add/remove/conflict resolution), read `references/evolve-mode.md`.

## 13. Quality checklist

Run before finalising; report any failure to the user rather than shipping past it.

**Requirements**
- [ ] Every Must/Should has a stable ID in its component chapter and ≥ 1 test.
- [ ] **Atomic** — nothing joins two verbs, a behaviour and a deadline, or a
      success and a failure path.
- [ ] **Falsifiable** — precondition, stimulus, observable response, deadline,
      tolerance, failure behaviour, tier.
- [ ] **No weasel words** — grep for *appropriate, graceful, user-friendly, as
      needed, if possible, reasonable, sufficient, robust, properly, seamless,
      optimal, acceptable, normal operation, best effort*.
- [ ] **Typed** — architecture decisions and implementation recommendations are in
      the Harness, not written as functional requirements.
- [ ] **Provenance tagged**; nothing a pack proposed was adopted unaccepted;
      declines recorded in §5. No unbound `{{parameters}}`.

**Models**
- [ ] **State model** present if stateful, with a complete transition table —
      every (state × event) pair handled, ignored, or excluded with a reason.
- [ ] **Security profile** stated before any security requirement; no
      "encrypted or obfuscated"-style criterion, which cannot fail.
- [ ] §2.4 Component Layering (with diagram) and §x.0 Test Architecture present.

**Verification**
- [ ] **Verification contract** on every approved Must/Should, including
      `prohibited_outcomes` — without them a recovery requirement passes when the
      device recovers by rebooting.
- [ ] **Test specs** for every applicable clause in the canonical schema, each
      with pass criteria, failure criteria, evidence, and cleanup; negative,
      boundary, state-transition, persistence and recovery variants where relevant.
- [ ] Every test allocated to **host / target / bench** with a stated
      controllability method — no failure mode dropped for being awkward.
- [ ] **Seven lifecycle states** tracked per requirement; no `@fsd` tag or coverage
      figure presented as proof. Traceability is a pointer to generated artefacts,
      never a hand-filled Covered/GAP column.
- [ ] **Gaps by category** (specification / verification / implementation /
      evidence), with `pending` and `philosophical` clauses listed separately.

**Document**
- [ ] **Planes separated** (§6.11): no build conventions, install steps, or history
      in the FSD. Every fact in exactly one plane; the others link.
- [ ] Body grouped by layer Parts mirroring §2.4; chapters self-contained.
- [ ] Full test specs live in `verification/test-specs/`, linked not inlined.
- [ ] Chapter numbering sequential, heading depth ≤ `####`, phases carry scope,
      deliverables and exit criteria, no `<placeholder>` or `TODO` left.
- [ ] Written to the correct path; in update mode, unaffected chapters byte-identical.

## 13.1 Lifecycle metadata

The FSD carries or links to:

```yaml
document_status:
fsd_version:
repository:
baseline_commit:
applicable_firmware_version:
author:
reviewers:
approval_status:
created:
last_updated:
change_history:
superseded_requirements:
open_decisions:
related_test_baseline:
```

This is the one sanctioned place for dated history — everywhere else the planes
are present-state. It exists so a historical test result can be tied to the exact
spec, firmware, and bench that produced it.

## 13.2 Reference index

| File | Covers |
|------|--------|
| `references/requirement-quality.md` | Statement types, provenance and status, the 13-check quality gate, the verification contract |
| `references/system-models.md` | Context, components, state-transition model, interfaces, configuration and data catalogues, security profile |
| `references/test-design.md` | Clause inventory, tiers, controllability (Drive/Feed/Emulate/Observe/Rig), observability, required test classes, independence and cleanup, test data and secrets |
| `references/test-spec-schema.md` | The canonical test-specification schema, field by field |
| `references/test-spec/` | Human-readable test-document format and section templates |
| `references/traceability.md` | Seven lifecycle states, `@fsd` tags, evidence fields, four gap categories, coverage check |
| `references/three-planes.md` | WHAT / HOW / OPERATE model, routing rule, retrofit procedure |
| `references/templates/` | Harness and Handbook templates to instantiate |
| `references/canonical-fsd-structure.md` | The Parts scheme and chapter skeleton |
| `references/test-architecture.md` | Layering, tier profiles, component × tier matrix |
| `references/complexity-scaling.md` | Depth scaling by inferred complexity |
| `references/evolve-mode.md` | Preserve / update / add / remove rules for deltas |
| `references/example-output.md` | Worked FSD excerpt |
| `references/domains/` | Domain packs (ESP32) |

## 14. Domain packs

The core is domain-neutral. Domains with recurring components, detection signals,
layer profiles, and standard test libraries get a pack under
`references/domains/<domain>.md`, loaded only when the project matches.

1. **Detect** the domain from the description, codebase, and config files — each
   pack lists its own signals.
2. **Apply** the matching pack: its layer profile (L0/L1/L2 contents for §2.4),
   its tier names, and its test libraries.
3. **No match?** Use the core only; pick tier names that fit the platform
   (cloud: unit / integration / staging).

**A pack proposes; it never adopts.** Detecting `esp_mqtt` proves the project
speaks MQTT — not that the product owes anyone offline buffering, ordered replay,
or command acknowledgement. Silent adoption is how a 12-requirement device
acquires 60 requirements nobody asked for, each then demanding tests and
maintenance.

So: present matched items as a proposal via `AskUserQuestion` with a
recommendation, write only what is accepted, record declines under *Explicitly out
of scope* in §5, tag every requirement with its provenance (`[user]`,
`[derived]`, `[code]`, `[pack:<domain>]`), and bind every `{{parameter}}` the
accepted items carry — an unbound parameter fails the §13 checklist.

| Pack | Domain |
|------|--------|
| `esp32` | ESP-IDF / Arduino-ESP32: WiFi, BLE, MQTT, OTA, NVS, captive portal, watchdog, logging |

To add one, follow the same shape — detection signals · layer profile · tier
names · a feature-detection table pointing at spec files under
`references/domains/<domain>/` — and add a row above.
