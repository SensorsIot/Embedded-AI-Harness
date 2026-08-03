---
name: fsd-writer
description: >
  Generates or updates a project's specification documentation across three planes
  — the FSD (WHAT must be true), the Harness (HOW it is built and changed), and the
  Handbook (HOW to operate it) — for any kind of system: embedded, cloud back-end,
  mobile, networking, SDR, or hybrid. Converts rough project descriptions into
  atomic, falsifiable, provenance-tagged requirements with a state model,
  verification tiers, and generated traceability; splits build conventions into the
  Harness and operator procedures into the Handbook so the FSD stays behavioural.
  Supports initial generation, incremental evolution, and retrofitting an existing
  doc set into the three planes. Loads optional domain packs (e.g. ESP32) that
  propose — never silently adopt — domain requirements and test libraries. Triggers
  on "FSD", "fsd", "write FSD", "create FSD", "generate FSD", "new FSD",
  "update FSD", "evolve FSD", "functional spec", "specification document",
  "harness", "build contract", "handbook", "runbook", "operator manual",
  "three planes", "WHAT HOW OPERATE", "split spec into planes".
---

# FSD Writer Skill

A general-purpose skill that turns a rough, unstructured project description into
a structured Functional Specification Document (FSD) in Markdown, or surgically
updates an existing FSD with new requirements, corrections, or expansions.

## 1. Purpose

This skill:

- Generates a canonical FSD from a rough description (**initial mode**).
- Updates or expands an existing FSD using a delta description (**evolve mode**).
- Writes the **Harness** (HOW) and **Handbook** (OPERATE) planes alongside it, and
  retrofits an existing doc set into the three planes (**plane mode**, §2.4).
- Dynamically adjusts depth and verbosity based on inferred system complexity.
- Ensures full requirement traceability (FR / NFR <-> test coverage).
- Surfaces risks, assumptions, and constraints as first-class content.
- Produces deterministic, agent-consumable Markdown.

It supports embedded systems, networking, SDR, IoT, cloud backends, mobile apps,
multi-service orchestrations, and hybrid hardware/software projects.

## 2. Invocation

### 2.1 Mode A — Initial Generation

Start a new FSD from scratch.

```
/fsd-writer
<rough description text>
```

Behavior:
1. Parse the rough description.
2. Ask clarifying questions if critical information is missing (Section 5).
3. Infer complexity tier (Section 6).
4. Generate the complete FSD (Section 7).
5. Write the file (Section 10).

### 2.2 Mode B — Evolve Existing FSD

Update, expand, refactor, or correct an already existing FSD.

```
/fsd-writer update <path-to-existing-fsd>
<delta description — changes, additions, clarifications, new constraints>
```

If no path is given, search the project for an existing FSD:
1. Check `Documents/*-fsd.md`
2. Check `Documents/*-FSD.md`
3. Check `docs/*-fsd.md`
4. Check project root for `*-fsd.md`

Behavior:
1. Read the existing FSD in full using the **Read** tool.
2. Parse the delta description.
3. Ask clarifying questions only if the delta introduces architectural ambiguity.
4. Apply changes surgically — preserve all unaffected sections verbatim.
5. Regenerate only the sections affected by the delta.
6. Maintain numbering and cross-references; the traceability matrix is
   **regenerated** by the traceability tool, never hand-edited in the FSD.
7. Write the updated file using the **Edit** tool (preferred) or **Write** tool
   (if changes are too extensive for surgical edits).

### 2.3 Mode C — Grill (deep interview for thin inputs)

Use when the rough description is too thin to infer architecture safely:
fewer than ~3 sentences, no codebase to explore, or no clarity on
protocol/platform/operator. The default behaviour for Mode A is to ask 1-3
questions per round and infer aggressively; Mode C escalates that into a
depth-first interview that resolves the design tree branch by branch.

```
/fsd-writer --grill
<rough description text>
```

Behaviour:

1. Identify the highest-impact unresolved decision (the one that gates the
   most downstream choices — usually connectivity, platform, or operator).
2. Ask **one question at a time**. Wait for the answer before asking the next.
3. Every question must come with the skill's **recommended answer**, not
   just a list of options. The user should be able to accept with one word.
4. Resolve dependencies in order. Do not ask about a downstream choice
   (e.g. OTA mechanism) until its prerequisite (connectivity) is fixed.
5. If a question is answerable from the codebase, config files, or
   `CLAUDE.md` — **explore, do not ask** (see Section 4.3).
6. Stop grilling once the design tree is resolved enough to generate the
   FSD without `(assumed)` markers on architecture-critical fields.
7. Generate the FSD (Section 7) and write the file (Section 10).

Mode C is for the initial interview only. Once the FSD exists, switch to
Mode B (evolve) for incremental changes.

### 2.4 Mode D — Planes (write or retrofit HOW / OPERATE)

Create the Harness and Handbook alongside the FSD, or split an existing document
set into the three planes (§6.11).

```
/fsd-writer --planes [<path-to-existing-fsd-or-docs-dir>]
```

Behaviour:

1. **Inventory.** List every existing document and the plane role it currently
   fills. A single "spec" almost always fills two or three at once.
2. **Bind roles to files.** `[SPEC]`, `[HARNESS]`, `[HANDBOOK]` — bind to what
   already exists before proposing new files. An existing user manual *is* the
   Handbook; do not create a second one beside it.
3. **Triage each section** with the §6.11 routing rule. Produce a move plan:
   every `from → to`, every new file, every section to be present-state-scrubbed.
4. **Preview the plan and get confirmation before moving anything.** This step is
   not optional — the user may have reasons for the current layout.
5. **Move content, do not rewrite it.** `git mv` whole files so history follows;
   for sections, move text verbatim and then fix only tense and cross-references.
6. **Instantiate missing plane files** from `references/templates/`.
7. **Verify**: no cross-reference broken, no content lost. Diff the sorted
   non-blank lines before and after — only headings should differ. Report the
   result.

A project may legitimately want only two planes (a library with no operators
needs no Handbook). Do not manufacture a plane that has no reader.

## 3. Tool Usage

This skill uses the following Claude Code tools:

| Tool | When |
|------|------|
| **Read** | Read existing FSD (evolve mode), read project files for context |
| **Glob** | Find existing FSD files, scan project structure for architecture clues |
| **Grep** | Search for protocols, frameworks, dependencies in project source |
| **Write** | Create new FSD file (initial mode) or full rewrite |
| **Edit** | Surgical updates to existing FSD sections (evolve mode) |
| **AskUserQuestion** | Clarifying questions when critical info is missing |
| **Task** (Explore) | Deep codebase exploration when the project has existing source code |

### 3.1 Context Gathering (Before Generation)

Before writing the FSD, the skill should gather context from the project when
source code exists:

1. **Glob** for project structure — `**/*.c`, `**/*.h`, `**/*.py`, `**/*.ts`,
   `**/Cargo.toml`, `**/package.json`, `**/CMakeLists.txt`, `**/go.mod`, etc.
2. **Grep** for protocols and frameworks — BLE, WiFi, MQTT, HTTP, gRPC, REST,
   WebSocket, LoRa, OCPP, etc.
3. **Read** key config files — `sdkconfig.defaults`, `platformio.ini`,
   `docker-compose.yml`, `Makefile`, build configs.
4. Use findings to pre-fill architecture sections and reduce clarifying questions.

### 3.2 Evolve Mode — Diff Discipline

When updating an existing FSD:

- **Never regenerate the entire file.** Only touch sections affected by the delta.
- Use the **Edit** tool with precise `old_string` / `new_string` pairs.
- If a delta adds a new phase, insert it and renumber subsequent phases.
- If a delta adds new requirements, assign the next available ID (FR/NFR or clause,
  per the FSD's convention) in the owning component chapter.
- The traceability matrix is generated — when FRs or tests change, ensure it is
  regenerated; never hand-edit coverage status in the FSD.
- If the delta invalidates existing content, remove or revise it — do not leave
  contradictions.

## 4. Interaction Model (Clarifying Questions)

### 4.1 When to Ask

The skill must ask clarifying questions when critical architecture-affecting
information is missing. "Critical" means it affects:

- System architecture or component decomposition
- Protocol selection (BLE vs WiFi vs LoRa vs cellular)
- Interface definitions (API style, command format)
- Safety or regulatory constraints
- Multi-phase decomposition
- Hardware or platform selection
- External integrations (MQTT broker, cloud service, Home Assistant, etc.)

### 4.2 How to Ask

Use the **AskUserQuestion** tool with:
- 1-3 precise questions per round in Mode A; **one question at a time** in Mode C.
- **Every question must include the skill's recommended answer**, not just
  a list of options. The user must be able to accept with one word.
- Order questions by dependency. Do not ask about a decision whose
  prerequisite is still open (e.g. don't ask about OTA mechanism before
  connectivity is fixed).
- Phrase questions to unblock the FSD, not to explore nice-to-haves.

Example (good — recommendation up front):

```
Q: How does the device connect?
Recommended: WiFi — matches the dashboard requirement and existing infra.
Other options: BLE, LoRa, Cellular, USB-only.
```

Example (bad — options without a pick):

```
Q: How does the device connect? WiFi / BLE / LoRa / Cellular / USB-only?
```

Multi-question rounds (Mode A only):

```
Questions:
1. How does the device connect?
   Recommended: WiFi. Other: BLE, LoRa, Cellular, USB-only.
2. Do you need OTA firmware updates?
   Recommended: Yes (WiFi). Other: Yes (BLE DFU), No.
3. Who is the primary operator?
   Recommended: Installer/technician. Other: End user, Automated backend.
```

### 4.3 When to Explore or Infer Instead of Asking

**Explore before asking.** Before asking ANY question, check whether it is
answerable from project artefacts:

- Read config files: `sdkconfig.defaults`, `platformio.ini`, `package.json`,
  `Cargo.toml`, `CMakeLists.txt`, `docker-compose.yml`.
- Grep for protocol/framework usage in source (HTTP/REST, gRPC, WebSocket,
  message queues, DB/auth SDKs, BLE/WiFi, etc.) and check whether a domain pack
  matches (Section 14) for domain-specific detection patterns.
- Read `README.md`, `CLAUDE.md`, and any existing FSD or design docs.

If the answer is in the codebase, **explore — do not ask the user**. Asking
a question whose answer is already in the repo wastes attention and
signals that the skill did not gather context (Section 3.1).

**Infer silently** only when:
- The detail does not significantly change high-level architecture, AND
- The cost of being wrong is low.

Safe inferences:
- "web API" mentioned → assume HTTP + JSON
- "logs" mentioned → assume structured logging to console / file / serial
- "dashboard" mentioned → describe generic "dashboard system" without naming tools
- "database" mentioned without type → assume PostgreSQL for relational, SQLite for embedded

When inferring, mark the inference in the FSD with `(assumed)` or group them in
**Section 5: Risks, Assumptions & Dependencies**.

## 5. Complexity Scaling Rules

The skill dynamically scales FSD depth based on inferred system complexity (Low / Medium / High). Complexity is inferred from component count, protocol count, external integrations, real-time constraints, and domain.

For the full complexity tiers table, complexity signals, and per-section scaling behavior matrix, read `references/complexity-scaling.md`.

## 6. Information Extraction & Inference Rules

Given the rough description, the skill must extract or infer the following:

### 6.1 Project Name

Derive a short, descriptive name:
- "ESP32 BLE HID Keyboard" (embedded)
- "Multi-Tenant Billing API" (cloud back-end)
- "Offline-First Notes App" (mobile)

### 6.2 System Purpose & Goals

Extract in 2-4 sentences: what problem is solved, for whom, in what environment.

### 6.3 System Components

Identify major components:
- Hardware / platforms (MCU, SBC, server, cloud)
- Software services / apps / daemons
- User-facing components (mobile app, web UI, CLI)
- External integrations (Home Assistant, OCPP backend, MQTT broker)

If components are implied but not explicit, infer and mark as assumptions.

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

#### 6.4.1 Atomicity — one obligation per requirement

A requirement states **one** obligation. A sentence that promises several things
is several requirements, because they are implemented, fail, and are tested
independently.

This is the same split `test-designer` performs in its Phase 1 clause inventory;
apply it here so the downstream skill has nothing left to split. Splitting late
means the FSD and the test suite disagree about how many promises exist.

> "Convert received text into USB HID reports and deliver them within 50 ms."

is three obligations — conversion correctness, delivery, and timing — and becomes
three requirements with suffixed IDs (`FR-3.1a/b/c`). Keep the IDs adjacent so the
grouping stays visible.

Split when the sentence contains: "and" joining two verbs, a behaviour plus a
deadline, a success path plus a failure path, or a list of outputs.

#### 6.4.2 Requirement shape — mandatory for Must / Should

Every **Must** and **Should** requirement must be falsifiable: a competent tester
who has never spoken to the author must be able to build a rig that returns pass
or fail. State these fields — inline for simple requirements, as a table when the
behaviour is involved:

| Field | Meaning |
|-------|---------|
| **Precondition** | The state the system is in before the stimulus |
| **Stimulus** | The event or input that triggers the behaviour |
| **Observable response** | What an outside observer sees — a message, a pin level, a log line, an API response |
| **Deadline** | Maximum time from stimulus to response |
| **Tolerance** | Permitted deviation (timing jitter, measurement error, retry count) |
| **Failure behaviour** | What happens when the response cannot be produced |
| **Verification tier** | Which test tier (§x.0 Test Architecture) proves it |

Not measurable — reject these:

> The device shall reconnect automatically.
> The system shall use an appropriate QoS level.
> Invalid input shall be rejected gracefully with user-friendly messages.
> Normal operation continues. · Possible packet loss. · No data loss.

Measurable — the same intent, executable on a bench:

> **FR-4.2** [Must]: Given the MQTT broker was unreachable and the device holds
> valid WiFi credentials (**precondition**), when the broker becomes reachable
> again (**stimulus**), the device shall establish a new MQTT session and resume
> publishing to the configured telemetry topic (**observable response**) within
> 30 s (**deadline**, ±5 s **tolerance**), without restarting the ESP32. If no
> session is established within 5 attempts the device shall log
> `mqtt: giving up` and enter Recovery (**failure behaviour**). Verified on the
> **bench** tier (**verification tier**).

Words that signal an unfalsifiable requirement — treat each as a defect to fix
before the FSD is written, not a style preference: *appropriate, graceful(ly),
user-friendly, as needed, if possible, reasonable, sufficient, robust, properly,
seamless, optimal, minimal, acceptable, normal operation, best effort*.

Quantifiers that are vacuous without a bound are the same defect: "no data loss"
needs a window and a delivery guarantee; "possible packet loss" is an observation,
not an expected result — say how many packets may be lost before the test fails.

If a genuinely subjective quality matters (a UI "feels responsive"), state it as a
**May** with a named human-judgement acceptance step, so it is never mistaken for
something a rig can decide.

### 6.5 Non-Functional Requirements (NFR)

Extract or infer key NFRs with priorities:
- Performance (latency, throughput)
- Reliability / uptime
- Accuracy / precision
- Scalability
- Power consumption (embedded)
- Security and privacy (authentication, encryption, access control)

NFRs obey §6.4.2 too. "The system shall be responsive" is not an NFR; "95th
percentile API response under 200 ms at 50 concurrent clients" is.

#### 6.5.1 Security profile before security requirements

Never import individual security requirements — establish the **threat model
first**, then let the requirements follow from it. "Credentials shall be
encrypted at rest" is meaningless until you know who the attacker is, what
physical access they have, and what the platform actually offers.

Ask for, or infer and mark `(assumed)`, these four things, and state them in the
FSD before any security requirement:

1. **Who is the attacker?** Nobody (controlled site) · someone holding the device ·
   someone who can read the flash · someone on the network path.
2. **What does physical access get them?** Depends on enclosure, secure boot, and
   flash encryption — not on wishes.
3. **What is actually being protected, and for how long?** A WiFi PSK on a
   segregated test VLAN is not a customer database.
4. **What does the platform give you for free, and what does it cost?** Enabling
   flash encryption changes flashing, OTA, and RMA. Say so before requiring it.

Then state a named profile (the ESP32 pack defines P0/P1/P2 as a worked example)
and derive from it. Where the profile does *not* justify a protection, say so
explicitly and record it in §5 Risks as an accepted risk. An honest "we do not
claim confidentiality at rest" beats a requirement nobody implements.

**Obfuscation is not encryption.** Never accept base64, XOR, or a renamed key as
satisfying an encryption requirement, and never write an acceptance criterion of
the form "encrypted or obfuscated" — it cannot fail.

### 6.6 Interfaces & Data Models

Each interface becomes its **own L1 chapter** (Part B) — there is no global
Interface Specifications section in the Parts scheme. Per interface chapter:
- Identify the protocol (BLE, WiFi, USB HID, HTTP, MQTT, LoRa, OCPP, etc.)
- Describe endpoints, characteristics, topics, commands (commands/opcodes only
  for custom protocols)
- Define payload structures (fields, units, types)
- Specify direction (client -> server, device -> cloud, etc.)
- Keep the interface's requirements, schema, handlers, and failure modes together
  in that chapter (see `references/canonical-fsd-structure.md`).

### 6.7 Phases

At minimum define:
- **Phase 1**: Infrastructure / Foundation
- **Phase 2**: Core Functional Features
- **Phase 3+** (optional): Optimization, UX, analytics, etc.

Each phase must include: Scope, Deliverables, Exit Criteria, Dependencies.

### 6.8 Operational Procedures

Extract or infer:
- Deployment / flashing / installation
- Configuration / provisioning
- Normal operation workflows
- Failure recovery (reset, re-provisioning, safe-mode)

If not covered in the description, provide a generic but plausible set for the
domain.

### 6.9 Verification & Validation — what this skill owns

This skill states **what must be true and how it will be judged**. It does not
author the test suite. Three skills share this pipeline and each stops at a
defined line:

| Skill | Produces | Stops at |
|-------|----------|----------|
| **fsd-writer** (this) | Atomic requirements, acceptance criteria, verification tier per requirement, the stimuli and observations a test will need, and the intent of which requirements are tested together | Naming a tier and a criterion. It writes no test steps. |
| **test-designer** | Detailed test specifications, positive / negative / boundary / state-transition variants, the traceability YAML, gap reports, `@fsd` code mappings | Designing and documenting. It runs nothing. |
| **create-test-spec** | Structured test-spec documents with machine-checkable preconditions, step tables, and pass criteria | Authoring the document. |
| **workbench-\* skills** | Python test implementations, hardware actions, observations, test reports | Execution against real hardware. |

All four ship in this repo — `.claude/skills/{fsd-writer,test-designer,create-test-spec,workbench-*}/` and
`.claude/agents/fsd-compliance-checker.md` — so the chain works from a clone with
nothing installed at user level. Skills resolve **by name**, not by path; if a
name here does not resolve, the copy step in the README was incomplete.

So in the V&V chapter, this skill writes:

- Per requirement: its **verification tier** (from §x.0 Test Architecture) and its
  **acceptance criterion** — the observable that decides pass or fail.
- The **stimuli and observations** the tier must be able to produce and capture
  (e.g. "requires the bench to drop the broker and watch the telemetry topic").
- A **pointer** to the generated traceability matrix and gap report — never a
  hand-filled coverage column (Section 8).

It must **not** write Objective / Preconditions / Steps / Expected Result tables.
If the user asks for those in the same breath, generate the FSD first, then say
that `test-designer` (for traceability-linked suites) or `create-test-spec` (for a
standalone test-spec document) takes it from there.

#### 6.9.1 State Model — mandatory for stateful systems

If the system has modes that persist between events — provisioning, connecting,
operational, degraded, recovery — the FSD **must** carry a formal state model. It
is not optional prose and not a nice-to-have diagram.

This is where connected devices actually fail. Bugs rarely live in the happy path;
they live in the transitions — what happens when WiFi drops *during* provisioning,
whether a backoff timer survives a reconnect, which state a watchdog reset lands
in. A requirement list that never names a state cannot express any of that, and
the tests inherit the blindness.

**Trigger.** Required when any of these hold: the system provisions or pairs; it
maintains a connection it can lose; it has a recovery, safe, or degraded mode; it
persists mode across reboot; or its behaviour depends on what happened before.
For a stateless request/response service, skip it.

**Contents.** One chapter (or a section of the owning component's chapter) with:

- **States** — exhaustive and mutually exclusive. Name the failure states too;
  "WiFi unavailable" and "broker unavailable" are different states with different
  behaviour, and collapsing them into "error" hides the difference.
- **A transition table** — the normative artefact. One row per transition:

  | From | Event | Guard | To | Actions | Deadline |
  |------|-------|-------|----|---------|----------|
  | Connecting | `WIFI_DISCONNECTED` | retries < 5 | Connecting | backoff 2^n s, log attempt | — |
  | Connecting | `WIFI_DISCONNECTED` | retries >= 5 | Recovery | stop radio, log `wifi: giving up` | within 1 s |

- **A diagram** — Mermaid `stateDiagram-v2`, generated *from* the table. The table
  is normative; the picture is for humans. If they disagree, the table wins.
- **Entry and exit actions** per state, where they exist.
- **Timers and backoff** — initial delay, growth, ceiling, and what resets them.
- **Persistence** — which states survive a reboot and which do not, and where that
  is stored. A device that reboots into Provisioning because it forgot it was
  configured is a state-persistence bug.
- **Behaviour in every failure state** — what still works, what is suspended, what
  the user sees.

**Completeness rule.** Every (state × event) pair is accounted for: handled,
explicitly ignored, or impossible-by-construction with a stated reason. Blank
cells are where the field bugs live. State the unhandled-event default once
(e.g. "events not listed are logged at debug and discarded") rather than leaving
readers to guess.

**Verification.** Each transition row is an FR — atomic by construction (§6.4.1)
and already carrying its stimulus, guard, response, and deadline (§6.4.2), so it
drops straight into `test-designer`'s state-transition variants. Require coverage
of every row, not merely every state: reaching a state proves nothing about the
five edges into it.

### 6.10 Component Layering & Test Architecture

Give every FSD a layered component architecture (§2.4) that the test strategy
falls out of (§x.0 Test Architecture, in the V&V chapter under Part E):

- Classify each component into a layer with a strict one-way dependency —
  **L0 Foundation/platform → L1 Interfaces → L2 Application logic**. The L0-vs-L1
  line is **ownership** ("did we implement and test the protocol?"): a
  library/managed client to an external service is foundation; a hand-written
  decoder/driver/handler is an interface. Three layers is the common default, but
  the model is **open-ended (L0..Ln)** — add layers when a complex system genuinely
  has more distinct, one-way-dependent tiers (e.g. orchestration over domain logic,
  or a shared-services layer). Each layer becomes its own body Part.
- Draw a layered component diagram in §2.4 (stacked layer boxes, components on one
  row per layer).
- **The FSD body mirrors these layers**: each component becomes a self-contained
  chapter, grouped under layer **Part** dividers (L2 → L1 → L0 → cross-cutting →
  operations & verification). The §2.4 layering is the spine; the body Parts are
  its projection. See `references/canonical-fsd-structure.md` (the Parts scheme).
- **Source layout is HOW — it belongs in the Harness, not the FSD.** The rules
  that make code mirror the layers (one module per component, lower layers never
  importing higher ones, pure cores extracted for the fast tier) constrain how the
  code is written, not what the system does. None of them is observable from
  outside a running system, and none would survive a rewrite in another language.
  Write them to `[HARNESS]/project/architecture.md`; §2.4 of the FSD states the
  layering and links to it. See `references/three-planes.md`.
- In §x.0 Test Architecture, define the test tiers (cost-ordered execution
  environments, named per platform), map them to the layers, and reference a
  **generated** component × tier coverage matrix. This skill declares the
  structure; a traceability tool fills in status.

Platform-independent — contents differ for embedded / cloud / mobile. For the
profiles, the diagram convention (and the Mermaid layout gotcha), and the matrix,
read `references/test-architecture.md`.

### 6.11 The Three Planes — what this skill writes, and where

Documentation answers three questions for three readers, and mixing them is why
specs rot. This skill owns all three planes and routes every sentence to exactly
one of them.

| Plane | Question | Document | Written when |
|-------|----------|----------|--------------|
| **WHAT** | What must be true of the system? | **FSD** | Always |
| **HOW** | How is it built and changed? | **Harness** | When the project has, or is acquiring, a codebase |
| **OPERATE** | How do I run it? | **Handbook** | When a human installs, drives, or recovers it |

**Routing rule** — ask in order, first "yes" wins:

1. Externally observable and must be true? → **FSD**
2. Constrains how code is written, structured, or verified? → **Harness**
3. Tells a human how to run, install, or recover it? → **Handbook**
4. About collaborating with the AI assistant? → `CLAUDE.md` — not a plane, not
   project documentation
5. Why a past decision was made? → commit message or ADR — never a plane

Two tests settle the hard cases: *could a black-box tester verify it?* (yes ⇒
WHAT), and *would it survive a rewrite in another language?* (no ⇒ HOW).

**Binding.** Planes are roles, not filenames. If the project already has a
document filling a role — a user manual, a runbook, an existing spec — bind to it
rather than creating a competing file. The Harness must be **committed**; an
untracked harness is unshared and therefore undocumented.

**Do not create a fourth plane.** Content that fits none of the three is HOW
wearing a different hat.

For the full model — plane contents, authority order, topology, the procedure for
retrofitting an existing project, and the anti-patterns — read
`references/three-planes.md`. Templates to instantiate:
`references/templates/harness/` (`00-Overview.md`, `AI-Workflow.md`,
`standards/{engineering,testing,documentation}.md`) and
`references/templates/handbook/Handbook.md`. Substitute `{{PROJECT}}`,
`{{FSD_PATH}}`, `{{HARNESS_PATH}}`, `{{HANDBOOK_PATH}}` on instantiation.

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

## 8. Traceability (Mandatory, generated)

Every FSD must carry traceability — but as a **pointer to generated artifacts**,
never a hand-filled status table.

Rules:
- Every **Must**/**Should** requirement — whether an `FR`/`NFR` item or a stable
  **clause** (§6.4 conventions) — must be stated with a stable ID in its component
  chapter and referenced by >= 1 test in the specs.
- Every test case must reference the FR(s) / NFR(s) / clause(s) it validates.
- The traceability tool computes coverage and emits the **coverage matrix**
  (component × tier) and a **gap report** (requirements with no test). `GAP` is
  *computed*, not typed into the FSD.
- **May**-priority requirements may have coverage but it is not mandatory.
- The FSD's V&V chapter (§x.2 Traceability) references the matrix/gap-report paths;
  it must **not** hand-maintain a "Status: Covered / GAP" column — that drifts from
  the code the moment a test changes (see `references/test-architecture.md` §4).
- In evolve mode, adding/removing/changing a requirement or test just means the
  generated matrix is re-run; no manual matrix edits.

## 9. Formatting & Style Rules

- Output pure Markdown — no HTML tags.
- Heading levels: Part dividers are `#` (unnumbered); chapters are `##` (numbered
  flat across the document); sub-sections `###`/`####`. **Cap depth at `####`** —
  four levels. Keep chapter numbering sequential with no gaps across all Parts.
- Use bullet lists for requirements; tables for tests, interfaces, and diagnostics.
- Use concise, unambiguous engineering language.
- Use **"shall"** for requirements ("The system shall...").
- Use **"must"** for constraints ("The device must operate on 3.3V").
- Avoid marketing language, filler, and subjective qualifiers.
- Keep requirement IDs stable across evolve updates — never renumber existing IDs
  unless explicitly asked to refactor numbering.
- Use `(assumed)` inline for inferred details.

## 10. Output File Naming & Location

### 10.1 Default Location

If the user does not specify a target path:

```
Documents/<project-name-kebab-case>-fsd.md          # WHAT
Documents/Harness/00-Overview.md                    # HOW  (+ AI-Workflow.md,
                                                    #       standards/, project/)
Documents/<project-name-kebab-case>-handbook.md     # OPERATE
```

Create the `Documents/` directory if it does not exist. If the project already
uses `docs/`, follow that instead — match the repo, do not impose a convention.

**Bind before creating.** If a document already fills a plane's role — a user
manual, a runbook, an existing spec — bind to it and extend it. Never create a
second file competing for the same role. The Harness must be committed to the
repo; an untracked harness is unshared and therefore undocumented.

Examples:
- `Documents/esp32-ble-hid-keyboard-fsd.md`
- `Documents/multi-tenant-billing-api-fsd.md`
- `Documents/offline-first-notes-app-fsd.md`

### 10.2 Explicit Path

If the user provides a path, use it exactly. Do not relocate or rename the file.

### 10.3 Evolve Mode

When updating, write to the same file that was read. Confirm the path before
writing if it was auto-detected.

## 11. Example Output Snippet

For a complete example FSD snippet (medium-complexity BLE HID Keyboard project) showing expected tone, structure, and detail level, read `references/example-output.md`.

## 12. Evolve Mode -- Detailed Behavior

When updating an existing FSD, follow strict rules for what to preserve, update, add, and remove. Key principles: never renumber existing IDs, keep the traceability matrix generated (never hand-edited), flag contradictions before overwriting. For the complete evolve mode rules (preserve/update/add/remove/conflict resolution), read `references/evolve-mode.md`.

## 13. Quality Checklist

After generating or updating an FSD, the skill must verify:

- [ ] The body is grouped by layer Parts (or chapters in layer order for Low
      complexity), mirroring §2.4; chapters are self-contained.
- [ ] **Planes are separated** (§7.1): the FSD contains no build conventions, no
      install or operating procedures, and no history. Source-layout rules live in
      `[HARNESS]/project/`; operator steps live in the Handbook. §2.4 states the
      layering and links to the Harness rather than restating it.
- [ ] Every fact appears in **exactly one** plane; the others link to it.
- [ ] Every **Must**/**Should** requirement (FR/NFR item or stable clause) is
      stated with a stable ID in its component chapter and referenced by >= 1 test.
- [ ] **Atomic** (§6.4.1): no requirement joins two verbs, a behaviour and a
      deadline, or a success and a failure path.
- [ ] **Falsifiable** (§6.4.2): every Must/Should has a precondition, stimulus,
      observable response, deadline, tolerance, failure behaviour, and tier.
- [ ] **No weasel words** anywhere in a requirement or acceptance criterion:
      *appropriate, graceful(ly), user-friendly, as needed, if possible,
      reasonable, sufficient, robust, properly, seamless, optimal, acceptable,
      normal operation, best effort*. Grep for them before finalising.
- [ ] **Provenance tagged** (§14): every requirement carries `[user]`,
      `[derived]`, `[code]`, or `[pack:<domain>]`; nothing a pack proposed was
      adopted without the user accepting it; declined items are recorded in §5.
- [ ] **No unbound `{{parameters}}`** remain from a domain pack.
- [ ] **State model** (§6.9.1) present if the system is stateful, with a complete
      transition table; every (state × event) pair handled, ignored, or excluded.
- [ ] **Security profile** (§6.5.1) stated before any security requirement; no
      "encrypted or obfuscated"-style criterion exists.
- [ ] The V&V chapter declares tiers and acceptance criteria but contains **no
      test step tables** — those belong to `test-designer` / `create-test-spec`
      (§6.9).
- [ ] V&V traceability is a **pointer to the generated matrix/gap report** — no
      hand-filled "Status: Covered / GAP" column in the FSD.
- [ ] No `<placeholder>` or `TODO` text remains (flag to user if unresolvable).
- [ ] Chapter numbering is sequential with no gaps across all Parts; heading depth
      does not exceed `####`.
- [ ] All phases have scope, deliverables, and exit criteria.
- [ ] §2.4 Component Layering (with a layered diagram) and §x.0 Test Architecture
      are present.
- [ ] The file has been written to the correct path.
- [ ] (Evolve mode) Unaffected chapters are identical to the original.

Report any checklist failures to the user before finalizing.

## 14. Domain Packs

The skill core is **domain-neutral**. Some domains have recurring components,
detection signals, layer profiles, and standard test libraries; these live in
**domain packs** under `references/domains/<domain>.md` and are loaded only when
the project matches that domain — keeping the core applicable to any system.

### Selecting a pack

1. Detect the domain from the description, the codebase, and config files (each
   pack lists its own detection signals).
2. If a pack matches, **read `references/domains/<domain>.md`** and apply it:
   its **layer profile** (concrete L0/L1/L2 contents for §2.4 — which becomes the
   body's Part/chapter spine), its **tier names** (for the §x.0 Test Architecture),
   and its **standard test libraries**.

   **A pack proposes; it never adopts.** Detecting a feature proves the project
   uses a technology — it does not prove the product owes anyone the behaviours
   the pack associates with it. Present matched requirements and tests as a
   proposal (via `AskUserQuestion`, with a recommendation per §4.2), write only
   what the user accepts, and record what they declined under *Explicitly out of
   scope* in §5. Tag every requirement with its provenance — `[user]`,
   `[derived]`, `[code]`, or `[pack:<domain>]` — so a later reader can tell a
   product decision from a library suggestion. Bind every `{{parameter}}` the
   accepted items carry; an unbound parameter fails the §13 checklist.
3. If no pack matches, use the platform-independent core only — the architecture
   layering and test tiers from `references/test-architecture.md` still apply; pick
   tier names that fit the platform (e.g. cloud: unit / integration / staging).

### Available packs

| Pack | Domain | File |
|------|--------|------|
| `esp32` | ESP32 firmware (ESP-IDF / Arduino-ESP32): WiFi, BLE, MQTT, OTA, NVS, captive portal, watchdog, logging | `references/domains/esp32.md` |

### Adding a pack

Create `references/domains/<domain>.md` following the same shape: **detection
signals · layer profile (§2.4) · tier names (§x.0 Test Architecture) · standard test libraries**
(a feature-detection table pointing to spec files under
`references/domains/<domain>/`). Then add a row to the table above.
