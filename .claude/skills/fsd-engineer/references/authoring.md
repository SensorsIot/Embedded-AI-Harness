# Authoring reference

Detail lifted out of `SKILL.md` to keep it inside the progressive-disclosure
budget. Read the section you need when you reach that step.

## Contents

- Context gathering and diff discipline
- Interaction model — clarifying questions
- Extraction rules — name, purpose, components
- Extraction rules — interfaces, phases, operations
- Formatting and style rules
- Output paths and file naming

---

## Context gathering and diff discipline

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

## Interaction model — clarifying questions

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

## Extraction rules — name, purpose, components

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

## Extraction rules — interfaces, phases, operations

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

## Formatting and style rules

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

## Output paths and file naming

### 10.1 Default Location

If the user does not specify a target path:

```text
docs/
├── Functionality/                WHAT — the FSD + the interface specs it cites
├── Harness/                      HOW  — 00-Overview, AI-Workflow, standards/, project/
├── UserDocumentation/            OPERATE — 00-Overview from the first commit,
│                                 even when nothing is deployable yet
├── decisions.md                  settled decisions with provenance — not a plane
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


## Per-mode behaviour (detail)

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

Create the Harness and UserDocumentation alongside the FSD, or split an existing document
set into the three planes (§6.11).

```
/fsd-engineer --planes [<path-to-existing-fsd-or-docs-dir>]
```

Behaviour:

1. **Inventory.** List every existing document and the plane role it currently
   fills. A single "spec" almost always fills two or three at once.
2. **Bind roles to files.** `[SPEC]`, `[HARNESS]`, `[OPERATE]` — bind to what
   already exists before proposing new files. An existing user manual *is* the
   OPERATE plane; do not create a second one beside it.
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

A project may legitimately have little to say in a plane — a library with no
operators has a thin OPERATE plane. Create the directory anyway with an honest
status line: an unwritten plane that exists is a visible gap, while one that was
never created is invisible. What you must not do is manufacture *content* for a
plane that has no reader.

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
