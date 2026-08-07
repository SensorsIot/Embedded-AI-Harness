# System models

Prose alone cannot express a state machine, an interface contract, or a
configuration surface without leaving holes. Build the models the project
actually needs — not all of them for every project, but each one that applies.

---

## 1. System context

- users and operators
- external systems
- physical environment
- trust boundaries
- communication channels
- lifecycle stages (manufacture, provisioning, operation, service, decommission)

## 2. Component and responsibility model

Major components and their ownership boundaries. Layers may be used, but they are
presented as **architecture**, not as external behaviour — so the layering lives
in §2.4 of the FSD while the rules that make source mirror it live in the Method
(`three-planes.md`).

---

## 3. State-transition model — mandatory for stateful systems

**Required when** the system provisions or pairs, maintains a connection it can
lose, has a recovery/safe/degraded mode, persists mode across reboot, or behaves
differently depending on what happened before. Skip only for stateless
request/response services.

This is where connected devices actually fail. Bugs rarely live on the happy
path; they live in the transitions — WiFi dropping *during* provisioning, a
backoff timer surviving a reconnect, which state a watchdog reset lands in. A
requirement list that never names a state cannot express any of it, and the tests
inherit the blindness.

Define:

- **states** — exhaustive, mutually exclusive, failure states named separately
  ("WiFi unavailable" and "broker unavailable" behave differently; "error" hides
  the difference)
- **entry conditions** and **entry/exit actions**
- **events**, **guards**, **next state**, **actions**, **limits**
- **timeouts, retry and backoff** — initial delay, growth, ceiling, what resets it
- **persistent vs transient state** — what survives a reboot, and where it is
  stored. A device that reboots into Provisioning because it forgot it was
  configured is a state-persistence bug.
- **prohibited transitions** — stated, not left implicit

The **transition table is normative**; a Mermaid `stateDiagram-v2` is generated
from it for humans. If they disagree, the table wins.

| Current state | Event | Guard | Next state | Action | Limit |
|---|---|---|---|---|---|
| Unconfigured | Boot | — | Provisioning | Start setup AP and portal | 10 s |
| WiFi connected | MQTT unavailable | retries < 5 | MQTT recovery | Retry without blocking normal operation | backoff 2^n s |
| WiFi connected | MQTT unavailable | retries ≥ 5 | Recovery | Stop client, log `mqtt: giving up` | 1 s |
| MQTT recovery | Broker reachable | — | Operational | Reconnect, publish availability | 30 s |
| Operational | WiFi lost | — | WiFi recovery | Stop dependent MQTT operation, retry WiFi | defined limit |

**Completeness rule.** Every (state × event) pair is handled, explicitly ignored,
or impossible-by-construction with a stated reason. Blank cells are where field
bugs live. State the unhandled-event default once — e.g. "events not listed are
logged at debug and discarded".

**Verification.** Every normative row is a requirement, atomic by construction and
already carrying its stimulus, guard, response and deadline. Every row maps to at
least one state-transition test. Cover **transitions, not states**: reaching a
state proves nothing about the five edges into it.

---

## 4. Interface model

Per interface: protocol · direction · endpoint / topic / characteristic /
command / pin · payload schema · units and encoding · authentication and
authorization · timing · errors · retries · idempotency where relevant ·
availability assumptions.

---

## 5. Configuration catalogue

Every configurable item is listed. Configuration is where undocumented behaviour
accumulates fastest, because each field is individually too small to specify and
collectively decisive.

| Field | Required content |
|-------|------------------|
| Name | Stable identifier |
| Type | String, integer, enum, boolean, address, … |
| Default | A defined value, or explicitly none |
| Valid range | Length, numeric range, enum values, format |
| Persistence | Volatile, retained, NVS, file, database |
| Sensitivity | Secret, personal, operational, public |
| Configuration interface | Portal, API, build-time, CLI, … |
| Validation | Acceptance and rejection rules |
| Change effect | Immediate, next reconnect, next reboot |
| Reset behaviour | Retained, cleared, factory-defaulted |

Each row with a validation rule owes a negative test; each with a range owes
boundary tests; each with a persistence rule owes a persistence test.

---

## 6. Data catalogue

For each important data item: origin · type and units · range and precision ·
lifecycle · storage · transport · confidentiality · integrity requirements ·
retention · **representation when invalid or unavailable**.

That last one is routinely omitted and routinely causes field defects — a sensor
reading of `0` meaning "zero" and "no reading" at once.

---

## 7. Security profile — before any security requirement

Never import individual security requirements. Establish the threat model first,
then derive. "Credentials shall be encrypted at rest" is meaningless until you
know who the attacker is, what physical access they have, and what the platform
actually offers.

Establish:

- threat actors
- physical-access assumptions
- trusted networks
- remote-access exposure
- confidentiality and integrity requirements
- credential lifecycle
- firmware authenticity requirements
- secure-boot and flash-encryption assumptions
- recovery and factory-reset behaviour

Then state a named profile and derive from it. Where the profile does not justify
a protection, say so explicitly and record it in §5 Risks as an accepted risk. An
honest "we do not claim confidentiality at rest" beats a requirement nobody
implements.

**Obfuscation is never equivalent to encryption.** Never accept base64, XOR, or a
renamed key as satisfying an encryption requirement, and never write an
acceptance criterion of the form "encrypted or obfuscated" — it cannot fail.
