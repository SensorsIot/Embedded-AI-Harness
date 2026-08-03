---
name: fsd-engineer
description: >
  Engineers the whole specification-and-verification contract for any system —
  embedded, cloud back-end, mobile, networking, SDR, or hybrid. Owns both sides:
  WHAT the system must do (the FSD), HOW it is built (the Harness), HOW it is
  operated (the Handbook), and HOW compliance is demonstrated (verification
  contracts, complete test specifications, traceability, evidence, and gap
  reports). Produces atomic, falsifiable, typed, provenance-tagged requirements
  with state models, interface and configuration catalogues, a security profile,
  host/target/bench tier allocation, and a seven-state verification lifecycle that
  never mistakes a tag or a coverage hit for proof. Modes: create, update, tests,
  audit, reconcile, planes. Loads optional domain packs (e.g. ESP32) that propose —
  never silently adopt — requirements and test libraries. Triggers on "FSD", "fsd",
  "write FSD", "create FSD", "generate FSD", "update FSD", "evolve FSD",
  "functional spec", "specification document", "requirements", "test spec",
  "test specification", "test design", "design tests from FSD", "traceability",
  "traceability matrix", "coverage audit", "gap report", "verification",
  "reconcile spec with code", "harness", "build contract", "handbook", "runbook",
  "three planes", "WHAT HOW OPERATE".
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

**It does:** inspect the repository · establish scope, actors, context,
constraints, assumptions · create and evolve the FSD, Harness, and Handbook ·
express requirements as stable, atomic, measurable, typed obligations · model
states, interfaces, data, configuration, and failures · validate the quality and
testability of every normative requirement · attach a verification contract to
every Must and Should · derive complete test specifications · allocate each test
to host, target, or bench · define stimuli, observations, evidence, and cleanup ·
maintain traceability across clause, test, implementation, execution, and
evidence · report ambiguity, inconsistency, and coverage gaps by category ·
produce structured handoffs.

**It does not:** implement production code · write executable tests · execute
tests · operate the workbench · claim a requirement is verified because code or a
test merely exists · turn recommendations into approved requirements silently ·
invent normative thresholds, tolerances, security assumptions, or failure
behaviour.

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

## 1. Purpose

This skill:

- Generates a canonical FSD from a rough description (**create**, §2.1).
- Updates or expands an existing FSD from a delta (**update**, §2.2).
- Interviews depth-first when the input is too thin (**grill**, §2.3).
- Writes the **Harness** (HOW) and **Handbook** (OPERATE) planes, and retrofits an
  existing doc set into the three planes (**planes**, §2.4).
- Designs complete test specifications from the FSD (**tests**, §2.5).
- Reports the verification lifecycle state of every requirement (**audit**, §2.6).
- Reconciles documents against drifted code (**reconcile**, §2.7).
- Scales depth to inferred system complexity.
- Maintains traceability across clause, test, implementation, execution, evidence.
- Surfaces risks, assumptions, constraints, and open decisions as first-class.
- Produces deterministic, agent-consumable Markdown and YAML.

It supports embedded systems, networking, SDR, IoT, cloud backends, mobile apps,
multi-service orchestrations, and hybrid hardware/software projects.

## 2. Invocation

### 2.1 Mode A — Initial Generation

Start a new FSD from scratch.

```
/fsd-engineer
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
/fsd-engineer update <path-to-existing-fsd>
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
/fsd-engineer --grill
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
/fsd-engineer --planes [<path-to-existing-fsd-or-docs-dir>]
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

### 2.5 Mode E — Tests (design or refresh test specifications)

```
/fsd-engineer tests <fsd-path>
```

Creates or refreshes detailed test specifications without rewriting unaffected
FSD content. Runs the clause inventory, tier allocation, controllability
analysis, and the required test classes
(`references/test-design.md`), emitting specs in the canonical schema
(`references/test-spec-schema.md`) plus an updated traceability matrix.

Use when the FSD is stable but its verification is not — or after a `tests`-only
delta such as adding boundary cases.

### 2.6 Mode F — Audit (what is actually verified?)

```
/fsd-engineer audit
```

Compares the FSD, requirement inventory, test specifications, executable tests,
source mappings, and available evidence, then reports the **lifecycle state of
every requirement** (`references/traceability.md` §1) and the gaps by category.

This is the mode that answers "are we done?" honestly. Expect most requirements
to sit below *Requirement verified*; that is information, not failure.

### 2.7 Mode G — Reconcile (documents and code drifted)

```
/fsd-engineer reconcile
```

Used when code, tests, or documents changed independently. Identifies
undocumented behaviour, obsolete tests, stale evidence, missing mappings, and
contradictions, then **proposes** FSD changes.

It does not silently adopt what the code happens to do — detected behaviour is
adjudicated per `references/requirement-quality.md` §2, and the four outcomes are
document / demote to Harness / fix the code / delete it.

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

The same split drives the clause inventory in `references/test-design.md` §1.
Splitting late means the requirements and the test suite disagree about how many
promises exist, so do it once, here.

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
first**, then derive. "Credentials shall be encrypted at rest" is meaningless
until you know who the attacker is, what physical access they have, and what the
platform actually costs you to provide it.

Where the profile does not justify a protection, say so and record it in §5 Risks
as an accepted risk. An honest "we do not claim confidentiality at rest" beats a
requirement nobody implements. **Obfuscation is never encryption**, and
"encrypted or obfuscated" is not an acceptance criterion — it cannot fail.

Full profile checklist: `references/system-models.md` §7.

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

### 6.9 Verification & Validation — this skill owns test design end to end

Requirements and their verification are **co-engineered**. A requirement is not
complete because it reads well; it is complete when a test can be derived from
it. Attempting to derive that test *is* the quality check — which is why design
happens here and is not delegated to another skill.

Two artefacts, at two levels of detail:

1. **Verification contract** — attached to every approved Must/Should, in the FSD
   next to the requirement. Preconditions, stimulus, expected observations,
   timing, tolerance, **prohibited outcomes**, tier, evidence, cleanup. This
   establishes normative verification *intent*.
   → `references/requirement-quality.md` §4
2. **Test specification** — the executable-ready design: test data, equipment,
   pass and failure criteria, required evidence, cleanup, failure recovery, and
   the automation handoff. Kept as separate artefacts from the readable FSD, but
   generated and maintained by this skill.
   → `references/test-design.md`, `references/test-spec-schema.md`

The FSD body stays readable: it carries requirements and their verification
contracts. The full specs live under `verification/test-specs/` and are linked,
not inlined.

**Where this skill stops.** It designs and documents. Development skills write
executable tests; workbench skills operate hardware and capture evidence. See the
responsibility table in §0.

Everything ships in this repo — `.claude/skills/fsd-engineer/`,
`.claude/skills/workbench-*/`, `.claude/agents/fsd-compliance-checker.md` — so the
chain works from a clone with nothing installed at user level. Skills resolve **by
name**, not by path.

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

## 8. Traceability (mandatory, generated, seven states)

Traceability separates **mapping** from **verification**. Collapsing them is the
most consequential error this skill can make, because it turns "we wrote something
down" into "it works" without anyone deciding to.

A requirement moves through seven states, each a separate field — **never** a
single `covered` flag:

```text
Specified → Test designed → Implementation mapped → Executable test implemented
          → Test executed → Evidence captured → Requirement verified
```

An `@fsd` tag proves only that a source location *claims* responsibility. Coverage
proves only that lines executed. Neither proves the behaviour was correct, and a
passing test proves nothing about assertions it does not contain — which is why
`prohibited_outcomes` is part of the contract.

Rules:
- Every **Must**/**Should** requirement is stated with a stable ID in its component
  chapter, carries a verification contract, and is referenced by ≥ 1 test spec.
- Every test references the requirement IDs it validates.
- The matrix, the lifecycle states, and the four gap categories are **computed**,
  never typed into the FSD. The FSD's V&V chapter references their paths.
- Evidence records the commit and environment, so staleness is computed rather
  than guessed.
- **May**-priority requirements may have coverage; it is not mandatory.
- In evolve mode, changing a requirement or test re-runs the generation; no manual
  matrix edits, ever.

Full model, `@fsd` tag rules, evidence fields, the four gap categories, and the
optional coverage check: **`references/traceability.md`**.

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

```text
docs/
├── <project>-fsd.md              WHAT — requirements + verification contracts
├── Harness/                      HOW  — 00-Overview, AI-Workflow, standards/, project/
├── <project>-handbook.md         OPERATE
├── architecture-decisions.md     approved structural choices
└── open-issues.md                unresolved product/architecture decisions

verification/                     machine-readable WHAT + verification design
├── requirements.yaml
├── states.yaml
├── interfaces.yaml
├── configuration.yaml
├── test-specs/<area>.yaml
├── traceability.yaml
├── implementation-handoff.yaml
└── gaps.md

tests/{host,target,bench}/        executable tests (written by dev skills)
test-results/<run-id>/            evidence (captured by workbench skills)
├── manifest.yaml                 commit, build, environment, hardware, timestamp
├── results.json
├── logs/
└── evidence/
```

`verification/` is not a fourth plane — it is the machine-readable form of the
WHAT plane, and `test-results/` is evidence, not documentation. Small projects may
use fewer files; the **information model stays the same**.

Match the repo if it already uses `Documents/` or another convention — do not
impose one.

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
- [ ] **Typed** (§6.4 / `requirement-quality.md` §1): every statement is classified,
      and architecture decisions / implementation recommendations are in the
      Harness, not stated as functional requirements.
- [ ] **Verification contract** on every approved Must/Should, including
      `prohibited_outcomes` — a recovery requirement without them passes when the
      device recovers by rebooting.
- [ ] **Test specifications** exist for every applicable clause, in the canonical
      schema, each with pass criteria, failure criteria, required evidence, and
      cleanup. Negative, boundary, state-transition, persistence and recovery
      variants generated where relevant.
- [ ] Every test is allocated to **host / target / bench** with a stated
      controllability method; no failure mode was dropped because it was awkward.
- [ ] **Lifecycle states** are tracked per requirement (seven, not a `covered`
      flag), and no `@fsd` tag or coverage figure is presented as proof of
      verification.
- [ ] **Gaps reported by category** — specification, verification, implementation,
      execution/evidence — with `pending` and `philosophical` clauses listed
      separately so they are not mistaken for gaps.
- [ ] The readable FSD carries requirements and contracts; full test specs live in
      `verification/test-specs/` and are linked, not inlined.
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
