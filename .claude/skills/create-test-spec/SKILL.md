---
name: create-test-spec
description: Create structured test specification documents with machine-checkable preconditions, step tables, pass criteria, and automation notes. Supports web, API, CLI, mobile, and embedded/IoT projects. Use when asked to write a test spec, test plan, test cases, QA document, verification plan, test matrix, hardware test spec, firmware test plan, or any structured testing documentation.
---

# Create Test Spec

Produce professional test specification documents with machine-checkable preconditions, repeatable step tables, and clear pass/fail criteria. Every test case follows a consistent 5-element format that supports both manual execution and automation.

## 1. Workflow

Follow these four steps in order:

1. **Gather context** — Identify the system under test, audience, interfaces, and scope (see Section 2)
2. **Select sections** — Pick from 12 core sections + 4 optional embedded/IoT sections (see Section 3)
3. **Write the document** — Apply the test case format (Section 4), precondition rules (Section 5), and writing guidelines (Section 6) using templates from `references/section-templates.md`
4. **Review** — Run the post-writing checklist (Section 9)

## 2. Context Gathering

Before writing, answer these eight questions. Explore the codebase, read the FSD, or ask the user:

| # | Question | Why |
|---|----------|-----|
| 1 | What is the system under test (SUT)? | Drives scope and terminology |
| 2 | Who is the audience? (QA team, developer, client) | Sets detail level and tone |
| 3 | Is there a Functional Specification Document? | Primary source for expected behavior |
| 4 | What interfaces does the SUT expose? (REST API, CLI, UART, MQTT, UI) | Determines precondition verification methods |
| 5 | Are there existing tests? (unit, integration, e2e) | Avoid duplication; reference for coverage gaps |
| 6 | What test tools are available? (pytest, curl, browser, serial monitor) | Shapes automation notes |
| 7 | Is this an embedded/IoT project? | Adds hardware setup, serial state, watchdog sections |
| 8 | What environments exist? (dev, staging, production, bench) | Defines test environment section |

For embedded/IoT projects, also determine:
- DUT hardware and connections (USB, UART, JTAG)
- Flash/erase procedures
- Boot states and serial output patterns
- OTA update mechanism
- **GPIO pins sampled at boot or runtime** — Search the firmware source for `digitalRead`, `gpio_get_level`, `INPUT_PULLUP`, `INPUT_PULLDOWN`, and button/pin definitions. Any GPIO that the DUT reads to decide behavior (e.g. enter config mode, select boot mode, trigger factory reset) is a candidate for automated toggling from the test harness. For each such pin, record: pin number, active level (LOW/HIGH), pull resistor (up/down/none), when sampled (boot only or continuous), and what behavior it triggers. Propose a wiring connection from a Serial Portal Pi GPIO to each DUT pin so tests can drive them programmatically instead of requiring manual button presses.

## 3. Document Structure

### Core Sections (all projects)

| # | Section | When to Include | Template |
|---|---------|-----------------|----------|
| 1 | Document Information | Always | `references/section-templates.md` §1 |
| 2 | Overview | Always | §2 |
| 3 | Test Environment | Always | §3 |
| 4 | Setup Test Cases | Always (TC-000, TC-001) | §4 |
| 5 | Standard Test Cases | Always | §5 |
| 6 | Edge Case Tests | When SUT has error paths | §6 |
| 7 | Long Duration / Stress Tests | When stability matters | §7 |
| 8 | Test Commands Reference | When CLI tools are used | §8 |
| 9 | Test Report Template | Always | §9 |
| 10 | Automated Test Coverage | When automated tests exist | §10 |
| 11 | Test Classification & Execution Sequence | When >20 test cases *and* sections are not in execution order | §11 |
| 12 | Revision History | Always | §12 |
| 13 | Automated Test Edge Cases | When automated tests cover edge cases worth documenting | §13 |

### Embedded/IoT Sections (optional)

Include these when the SUT involves firmware, hardware, or connectivity protocols. Templates are in `references/embedded-iot-sections.md`.

| # | Section | When to Include |
|---|---------|-----------------|
| E1 | Hardware Setup & Infrastructure Rules | Physical DUT with peripherals |
| E2 | Serial State Detection & Recovery | DUT has serial/UART output |
| E3 | OTA Update Tests | Firmware update mechanism exists |
| E4 | WiFi / BLE / MQTT Protocol Tests | Wireless connectivity or message broker |
| E5 | GPIO Wiring & Automated Pin Control | DUT has GPIOs that affect behavior (boot mode, config trigger, factory reset) |

## 4. Test Case Format

Every test case has exactly five elements. No exceptions.

### 4.1 The Five Elements

1. **Title** — `#### {ID}: {Descriptive Name}`
2. **Precondition** — Machine-checkable assertions (see Section 5)
3. **Step Table** — Numbered actions with expected results
4. **Pass Criteria** — One-sentence summary of what "pass" means
5. **Automation** — Tool, framework, or command to automate this test

### 4.2 ID Scheme

Assign IDs by category with room to insert tests later:

| Prefix | Category | Starting Number |
|--------|----------|-----------------|
| `TC-` | Setup & Standard | TC-000 (setup), TC-100+ (standard) |
| `EC-` | Edge Cases | EC-100+ |
| `WEB-` | Web UI & API | WEB-100+ |
| `CP-` | Captive Portal / Provisioning | CP-100+ |
| `LD-` | Long Duration / Stress | LD-001+ |
| `WIFI-` | WiFi / BLE Integration | WIFI-100+ |
| `SEC-` | Security | SEC-100+ |
| `PERF-` | Performance | PERF-100+ |

Choose prefixes that match the project. Not every prefix is needed.

### 4.3 Complete Example

```markdown
#### TC-102: MQTT Subscription Receives Wallbox Data

**Precondition:**
- DUT reachable: `GET /api/status` returns 200
- MQTT connected: `/api/status` field `mqtt_connected` is `true`
- Baseline error count: record `/api/status` field `wallbox_errors` as `E_before`

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Publish `{"power": 3500}` to `{TOPIC}` | Message accepted by broker |
| 2 | Wait 2 seconds | DUT processes message |
| 3 | `GET /api/status` | `wallbox_power` is `3500` (within +/-1) |
| 4 | Check `wallbox_errors` field | Value equals `E_before` (no new errors) |

**Pass Criteria:** DUT receives MQTT message and exposes correct power value via API with no errors.

**Automation:** `pytest test_mqtt.py::test_wallbox_power -v`
```

### 4.4 Step Table Rules

- Number steps sequentially starting at 1
- Each step has exactly one action and one expected result
- Use specific values, not "some value" or "a valid input"
- Include wait/delay steps explicitly when timing matters
- Reference baseline values captured in preconditions
- Final step should verify the primary assertion

## 5. Precondition Rules

Preconditions are the signature feature of this format. Every precondition must be **machine-checkable**: a human or script can verify it with a single command or observation.

### 5.1 Core Rules

1. **Verifiable** — Every precondition includes the exact check (command, API call, UI element, file path)
2. **Record baselines** — Capture counters and metrics before the test so pass criteria can compare against them
3. **Chain dependencies** — Reference prior test IDs when state depends on them (e.g., "TC-000 passed")
4. **Infrastructure first** — List infrastructure availability (broker running, database accessible) before SUT state

### 5.2 Precondition Patterns by Interface

**REST API:**
```
- Service healthy: `GET /health` returns 200
- User authenticated: `POST /login` with test credentials returns token
- Record baseline: `GET /api/metrics` field `request_count` as `R_before`
```

**CLI / Shell:**
```
- Tool installed: `mytool --version` exits 0
- Config file present: `test -f ~/.config/mytool.yaml` exits 0
- Database running: `pg_isready -h localhost` exits 0
```

**File System:**
```
- Build artifacts exist: `ls dist/bundle.js` exits 0
- Config writable: `test -w /etc/app/config.json` exits 0
- Log directory empty: `ls /var/log/app/*.log` returns no files
```

**Database:**
```
- Schema current: `SELECT version FROM migrations ORDER BY id DESC LIMIT 1` returns expected version
- Test data loaded: `SELECT COUNT(*) FROM users WHERE test=true` returns expected count
```

**UI / Browser:**
```
- Page loaded: element `#login-form` is visible
- User logged in: element `#user-menu` contains username
```

**Embedded / Serial:**
```
- DUT running: serial output contains `boot:0xc (SPI_FAST_FLASH_BOOT)`
- UART idle: serial slot state is `idle`
- NVS clean: boot count at default (1)
```

**GPIO Control (via Serial Portal):**
```
- DUT in special mode: `wt.gpio_set(PI_PIN, 0)` + `wt.serial_reset(SLOT)` triggered mode entry
- GPIO released: `wt.gpio_set(PI_PIN, "z")` after mode confirmed via serial output
```

### 5.3 Infrastructure Rules

**Principle: Tests are consumers of infrastructure, not managers of it.** If a test needs a service in a specific state, that is a precondition — not a test step.

For projects with shared infrastructure (brokers, databases, external services), define which tests may restart or modify infrastructure and which assume it is running. State this in the Test Environment section:

```markdown
### Infrastructure Rules
- **MQTT broker**: always running. Only TC-000 and EC-100 may restart it.
- **Database**: always running. Only TC-000 may reset schema.
- **WiFi Tester**: always available. Tests WIFI-* may reconfigure AP settings.
```

## 6. Writing Guidelines

1. **Imperative voice** — "Click the login button" not "The login button should be clicked"
2. **Specific values** — "`3500`" not "a valid power value"; "`http://localhost:8080`" not "the server URL"
3. **Consistent tables** — Every step table has exactly three columns: Step, Action, Expected Result
4. **Automation-first** — Write the automation note even if the test is manual today; describe what would be needed
5. **Test independence** — Each test should be runnable in isolation given its preconditions are met. Never assume prior test side effects unless explicitly stated in preconditions
6. **Edge case thinking** — For edge case sections, use this checklist:
   - Malformed input (invalid JSON, wrong types, truncated)
   - Oversized input (exceed buffer/limit)
   - Empty input (null, empty string, zero-length)
   - Concurrent operations (parallel requests, race conditions)
   - Disconnect/reconnect (network drop mid-operation)
   - Rapid-fire (burst of requests within short window)
   - Special characters (`<>&"'`, unicode, null bytes)
   - Timeout (slow responses, hung connections)
   - Resource exhaustion (memory, disk, connections)
7. **Section intro paragraphs** — After each `## Section` heading, add a one-line description of what the section validates in plain language. This goes before the first test case, e.g.: *"These tests verify the DUT handles WiFi AP outages gracefully — reconnecting automatically and not leaking memory."*
8. **Section-level `Run:` blocks** — At the top of each test section, add a `**Run:**` code block with the exact command to run that section's tests. Readers should be able to run a section's tests immediately without hunting through a global reference.
9. **Boundary values** — When testing thresholds, test the exact boundary, one below, and one above (e.g., max payload size: 255, 256, 257 bytes)
10. **Duration field** — For long-duration tests, add a `**Duration:**` field after Pass Criteria
11. **Random identifiers for provisioning tests** — When testing credential provisioning on an isolated/artificial network, use a random SSID and password generated at test time. This proves the DUT actually used the provisioned credentials, not a cached or known network. Does NOT apply to home network tests where the DUT connects to known infrastructure (real WiFi, MQTT broker).
12. **Group by feature, not by prefix** — If tests from different ID prefixes cover the same feature (e.g., CP-101 and WIFI-4xx both test captive portal), combine them into one section. ID prefixes organize the namespace; sections organize the reader's journey.
13. **Test case format in overview** — In the overview section (§1), briefly describe the anatomy of a test case (precondition, step table, pass criteria, automation) so readers know the format before encountering §3+.

## 7. Reference Pointers

Load reference files on demand, not upfront:

| File | When to Read |
|------|-------------|
| `references/section-templates.md` | When writing any core section (1-12). Contains markdown templates with `{PLACEHOLDER}` variables to fill in. |
| `references/embedded-iot-sections.md` | When the project involves firmware, hardware, serial, OTA, WiFi, BLE, or MQTT. Contains templates for sections E1-E4. |

## 8. Anti-Patterns

Avoid these common mistakes:

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| Vague preconditions | "System is running" | Specify exact check: "`GET /health` returns 200" |
| Missing expected results | Step table has empty Expected Result cells | Every action has an observable outcome |
| No automation notes | Tests are write-once, run-never | Always specify tool + command, even if aspirational |
| Order-dependent tests | Test B silently relies on Test A's side effects | Make dependency explicit in preconditions or eliminate it |
| Oversized test cases | Single test with 15+ steps | Split into focused tests of 3-8 steps each |
| Copy-paste preconditions | Same 10 preconditions on every test | Extract common state to Setup test (TC-000/TC-001) and reference it |
| Untestable pass criteria | "System behaves correctly" | Specify measurable outcome: "Response time < 200ms" |
| Missing negative tests | Only testing happy paths | Add edge case section with malformed, empty, oversized inputs |
| Hardcoded environments | "Connect to prod-server.example.com" | Use `{PLACEHOLDER}` variables defined in Test Environment |
| No classification | 80 tests with no execution order | Add classification table grouping by phase and dependency |
| Fixed test credentials | SSID "TestAP" hardcoded in provisioning test — DUT may connect from cache | Generate random SSID/password per run for artificial network tests (not home network) |

## 9. Post-Writing Checklist

Run through this checklist before delivering the document:

- [ ] Every test case has all 5 elements (title, precondition, step table, pass criteria, automation)
- [ ] Every precondition is machine-checkable (includes exact command or verification method)
- [ ] Baseline values are captured in preconditions when pass criteria compare against them
- [ ] Test IDs follow the naming scheme with no duplicates
- [ ] Step tables use specific values, not vague descriptions
- [ ] Edge case section covers at least 5 of the 9 edge case categories
- [ ] Setup tests (TC-000, TC-001) establish a clean, known starting state
- [ ] Test Commands Reference lists all CLI commands used across tests
- [ ] Test Classification table exists if there are more than 20 test cases (unless sections are in execution order)
- [ ] Each test section has a one-line intro paragraph and a `**Run:**` block
- [ ] Overview (§1) includes test case format description (precondition, step table, pass criteria, automation)
- [ ] Edge case section includes a coverage checklist mapping categories to EC test IDs
- [ ] Revision History has an initial entry with date and author
- [ ] (Embedded) GPIO pins that affect DUT behavior are identified and wiring to Serial Portal Pi is proposed (Section E5)
