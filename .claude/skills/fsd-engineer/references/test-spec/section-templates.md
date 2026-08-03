# Section Templates

Markdown templates for each core section of a test specification. Replace `{PLACEHOLDER}` values with project-specific content. Remove any sections that don't apply.

## Table of Contents

1. [Document Information](#1-document-information)
2. [Overview](#2-overview)
3. [Test Environment](#3-test-environment)
4. [Setup Test Cases](#4-setup-test-cases)
5. [Standard Test Cases](#5-standard-test-cases)
6. [Edge Case Tests](#6-edge-case-tests)
7. [Long Duration / Stress Tests](#7-long-duration--stress-tests)
8. [Test Commands Reference](#8-test-commands-reference)
9. [Test Report Template](#9-test-report-template)
10. [Automated Test Coverage](#10-automated-test-coverage)
11. [Test Classification & Execution Sequence](#11-test-classification--execution-sequence)
12. [Revision History](#12-revision-history)

---

## 1. Document Information

```markdown
# {PROJECT_NAME} Test Specification

| Field | Value |
|-------|-------|
| **Version** | {VERSION} |
| **Date** | {DATE} |
| **Author** | {AUTHOR} |
| **Status** | Draft / Review / Approved |
| **SUT** | {SYSTEM_UNDER_TEST} |
| **FSD Reference** | {FSD_FILE_OR_URL} |
```

---

## 2. Overview

```markdown
## 1. Overview

### 1.1 System Context

{ASCII_DIAGRAM_OR_DESCRIPTION}

Example ASCII diagram:

    +-----------+      +-------+      +----------+
    |  Client   | ---> |  SUT  | ---> | Backend  |
    +-----------+      +-------+      +----------+
                           |
                       +-------+
                       |  DB   |
                       +-------+

### 1.2 Key Features Under Test

1. {FEATURE_1} — {one-line description}
2. {FEATURE_2} — {one-line description}
3. {FEATURE_3} — {one-line description}

### 1.3 Test Strategy

Testing uses two complementary approaches:

**Automated test suites** are executable tests you *run* ({TEST_RUNNERS}). All {TOTAL_AUTOMATED} tests execute without human intervention; the runner reports pass/fail. They catch regressions on every code change.

**Test case specifications** are the {TOTAL_SPEC} test cases defined in {SPEC_SECTIONS}. Each specifies preconditions, step-by-step actions, and machine-checkable pass criteria. Most are implemented by the automated suites above; {N_REVIEW} are verified by code review only ({REVIEW_IDS}). The specifications define *what* is verified and *why*, independent of the test code.

The two overlap intentionally: the automated suites *implement* most specifications, so running the test commands also executes the verification tests.

#### Automated Test Suites — {TOTAL_AUTOMATED} tests

| Suite | Tests | Runner | Hardware needed |
|-------|------:|--------|-----------------|
| {SUITE_1} | {N} | `{RUNNER_1}` | {HARDWARE_1} |
| {SUITE_2} | {N} | `{RUNNER_2}` | {HARDWARE_2} |

**How to run:**
```
{FULL_TEST_COMMAND}
```

#### Test Case Specifications — {TOTAL_SPEC} test cases

Defined in {SPEC_SECTIONS}, organized by execution order. Every test case follows the same structure:

- **Precondition** — machine-checkable conditions that must hold before the test starts. A test runner can assert these programmatically.
- **Step table** (Step / Action / Expected Result) — numbered sequence of actions with concrete expected outcomes.
- **Pass Criteria** — one-sentence summary of what constitutes a pass.
- **Automation notes** — tools, commands, or scripts needed to run the test without human intervention.

| Section | Tests | What it covers |
|---------|------:|----------------|
| {SECTION_1} | {N} | {DESCRIPTION} |
| {SECTION_2} | {N} | {DESCRIPTION} |
| **Total** | **{TOTAL_SPEC}** | **{N_RUNTIME} runtime + {N_REVIEW} code review** |
```

---

## 3. Test Environment

```markdown
## 2. Test Environment

### 2.1 Infrastructure

| Component | Address / Location | Role |
|-----------|--------------------|------|
| {COMPONENT_1} | {ADDRESS} | {ROLE} |
| {COMPONENT_2} | {ADDRESS} | {ROLE} |
| {SUT} | {ADDRESS} | System under test |

### 2.2 Infrastructure Rules

- **{SERVICE_1}**: always running. Only {TEST_IDS} may restart it.
- **{SERVICE_2}**: always running. Only {TEST_IDS} may modify its state.
- **{SUT}**: may be restarted by any test, but must be restored to clean state after.

### 2.3 Initial State

Before running any test, the SUT must be in this state:
- {STATE_1}: {how to verify}
- {STATE_2}: {how to verify}
- {STATE_3}: {how to verify}

### 2.4 Test Tools

| Tool | Version | Purpose | Install |
|------|---------|---------|---------|
| {TOOL_1} | {VER} | {PURPOSE} | `{INSTALL_CMD}` |
| {TOOL_2} | {VER} | {PURPOSE} | `{INSTALL_CMD}` |

### 2.5 Endpoints / Topics / Channels

| Name | Address | Description |
|------|---------|-------------|
| {ENDPOINT_1} | `{URL_OR_TOPIC}` | {DESCRIPTION} |
| {ENDPOINT_2} | `{URL_OR_TOPIC}` | {DESCRIPTION} |
```

---

## 4. Setup Test Cases

```markdown
## 3. Setup Test Cases

These tests establish a clean, known starting state for all subsequent tests.

#### TC-000: {Provision / Deploy / Install} {SUT}

**Precondition:**
- {DEPLOYMENT_ARTIFACTS_EXIST}: `{CHECK_COMMAND}`
- {TARGET_ACCESSIBLE}: `{CHECK_COMMAND}`

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | {Deploy/install the SUT} | {Deployment succeeds, no errors} |
| 2 | {Reset state/database/config to defaults} | {State is clean} |
| 3 | {Verify SUT is running} | `{HEALTH_CHECK}` returns {EXPECTED} |
| 4 | {Verify version} | Version matches `{EXPECTED_VERSION}` |

**Pass Criteria:** SUT is deployed, running, and reporting correct version with clean state.

**Automation:** `{DEPLOY_COMMAND}`

---

#### TC-001: Verify Clean State

**Precondition:**
- TC-000 passed
- {SUT_RUNNING}: `{HEALTH_CHECK}` returns {EXPECTED}

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | {Check default configuration} | {All defaults are correct} |
| 2 | {Check empty data state} | {No stale data from previous runs} |
| 3 | {Check service connections} | {All dependencies are connected} |
| 4 | {Check logs for errors} | {No error-level log entries} |

**Pass Criteria:** SUT is in a known clean state with all defaults applied and no residual data.

**Automation:** `{VERIFY_COMMAND}`
```

---

## 5. Standard Test Cases

```markdown
## 4. Standard Test Cases

{SECTION_INTRO — one line describing what this section validates in plain language.}

**Run:**
```
{TEST_COMMAND_FOR_THIS_SECTION}
```

#### TC-{NNN}: {Test Name}

**Precondition:**
- {SUT_RUNNING}: `{CHECK_COMMAND}`
- {DEPENDENCY_MET}: `{CHECK_COMMAND}`
- Baseline: record `{METRIC}` as `{VARIABLE_NAME}`

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | {Action} | {Expected result} |
| 2 | {Action} | {Expected result} |
| 3 | {Verify primary assertion} | {Expected outcome} |

**Pass Criteria:** {One-sentence summary of what constitutes a pass.}

**Automation:** `{TEST_COMMAND}`
```

---

## 6. Edge Case Tests

```markdown
## 5. Edge Case Tests

{SECTION_INTRO — e.g., "Tests for error handling, boundary conditions, and recovery from unexpected inputs."}

**Run:**
```
{TEST_COMMAND_FOR_EDGE_CASES}
```

#### EC-{NNN}: {Edge Case Name}

**Precondition:**
- {SUT_RUNNING}: `{CHECK_COMMAND}`
- Baseline error count: record `{ERROR_METRIC}` as `E_before`

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | {Send malformed/invalid/extreme input} | {SUT handles gracefully, no crash} |
| 2 | {Verify error response or log} | {Appropriate error code/message} |
| 3 | {Verify SUT still operational} | `{HEALTH_CHECK}` returns {EXPECTED} |
| 4 | {Check error count} | Error count is `E_before + 1` |

**Pass Criteria:** {SUT rejects invalid input, reports error, and continues normal operation.}

**Automation:** `{TEST_COMMAND}`

### Edge Case Checklist

Use this checklist to ensure coverage. Mark which EC test covers each category:

| Category | Covered By | Description |
|----------|-----------|-------------|
| Malformed input | EC-{NNN} | Invalid JSON, wrong types, truncated data |
| Oversized input | EC-{NNN} | Exceeds buffer, payload, or field limits |
| Empty input | EC-{NNN} | Null, empty string, zero-length body |
| Concurrent operations | EC-{NNN} | Parallel requests, race conditions |
| Disconnect/reconnect | EC-{NNN} | Network drop mid-operation |
| Rapid-fire | EC-{NNN} | Burst of requests within short window |
| Special characters | EC-{NNN} | `<>&"'`, unicode, null bytes in input |
| Timeout | EC-{NNN} | Slow responses, hung connections |
| Resource exhaustion | EC-{NNN} | Memory, disk, connection pool limits |
```

---

## 7. Long Duration / Stress Tests

```markdown
## 6. Long Duration / Stress Tests

Stability and endurance tests run over extended periods.

#### LD-{NNN}: {Long Duration Test Name}

**Precondition:**
- {SUT_RUNNING}: `{CHECK_COMMAND}`
- Baseline metrics: record {HEAP/CPU/DISK/CONNECTIONS} as `{VARIABLE}`

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | {Start continuous load or monitoring} | {Load generation begins} |
| 2 | {Run for {DURATION}} | {No errors during run} |
| 3 | {Check metrics at end} | {Metrics within {THRESHOLD} of baseline} |
| 4 | {Verify SUT health} | `{HEALTH_CHECK}` returns {EXPECTED} |

**Pass Criteria:** {SUT remains stable for {DURATION} with no degradation beyond {THRESHOLD}.}

**Duration:** {HOURS}h / {DAYS}d

**Automation:** `{TEST_COMMAND} --duration {DURATION}`
```

---

## 8. Test Commands Reference

```markdown
## 7. Test Commands Reference

### Setup Commands

```bash
# Deploy / provision SUT
{DEPLOY_COMMAND}

# Reset to clean state
{RESET_COMMAND}

# Verify health
{HEALTH_CHECK_COMMAND}
```

### Test Execution

```bash
# Run all automated tests
{FULL_TEST_COMMAND}

# Run specific test category
{CATEGORY_TEST_COMMAND}

# Run single test
{SINGLE_TEST_COMMAND}
```

### Monitoring

```bash
# Watch logs
{LOG_COMMAND}

# Check metrics
{METRICS_COMMAND}

# Check resource usage
{RESOURCE_COMMAND}
```

### Troubleshooting

```bash
# Restart SUT
{RESTART_COMMAND}

# Clear state
{CLEAR_STATE_COMMAND}

# Debug mode
{DEBUG_COMMAND}
```
```

---

## 9. Test Report Template

```markdown
## 8. Test Report Template

Use this template for recording test execution results.

```
================================================================
         {PROJECT_NAME} — Test Execution Report
================================================================
Date     : {DATE}
Tester   : {TESTER}
FW / Ver : {VERSION}
Environment: {ENVIRONMENT}
================================================================

SETUP
  TC-000  Provision SUT          [ PASS / FAIL / SKIP ]
  TC-001  Verify Clean State     [ PASS / FAIL / SKIP ]

STANDARD
  TC-100  {Test Name}            [ PASS / FAIL / SKIP ]
  TC-101  {Test Name}            [ PASS / FAIL / SKIP ]

EDGE CASES
  EC-100  {Test Name}            [ PASS / FAIL / SKIP ]

LONG DURATION
  LD-001  {Test Name}            [ PASS / FAIL / SKIP ]

================================================================
Summary: {PASS}/{TOTAL} passed, {FAIL} failed, {SKIP} skipped
Notes:
  -
================================================================
```
```

---

## 10. Automated Test Coverage

```markdown
## 9. Automated Test Coverage

### Test Files

| Test File | Tests | Source Under Test | Framework |
|-----------|------:|-------------------|-----------|
| `{TEST_FILE_1}` | {N} | `{SOURCE_FILE}` | {FRAMEWORK} |
| `{TEST_FILE_2}` | {N} | `{SOURCE_FILE}` | {FRAMEWORK} |
| **Total** | **{N}** | | |

### Coverage Gaps

These areas are tested manually only (no automated tests yet):

- {AREA_1}: {reason automation is missing}
- {AREA_2}: {reason automation is missing}
```

---

## 11. Test Classification & Execution Sequence

> **When to omit:** If document sections are already ordered by execution phase (Setup → Functional → Edge Cases → Long Duration), this table is redundant — the document structure itself conveys the sequence. Only include it when sections are organized differently (e.g., by feature, by component, or by date added).

```markdown
## 10. Test Classification & Execution Sequence

### Execution Phases

| Phase | Category | Tests | Requires Human | Requires {INFRA} | Duration |
|-------|----------|------:|:--------------:|:-----------------:|----------|
| 1 | Setup | {N} | {Yes/No} | {Yes/No} | {TIME} |
| 2 | Standard | {N} | {Yes/No} | {Yes/No} | {TIME} |
| 3 | Edge Cases | {N} | {Yes/No} | {Yes/No} | {TIME} |
| 4 | {CATEGORY} | {N} | {Yes/No} | {Yes/No} | {TIME} |
| 5 | Long Duration | {N} | No | {Yes/No} | {TIME} |

### Classification Criteria

- **Phase 1** tests run first because they establish the SUT state
- **Phase 2** tests validate core functionality in isolation
- **Phase 3** tests stress error paths and require Phase 2 baseline
- **Phase 4** tests require specific infrastructure ({DETAILS})
- **Phase 5** tests run last due to extended duration

### Manual-Only Tests

These tests require human interaction and cannot be fully automated:

| Test ID | Reason |
|---------|--------|
| {TEST_ID} | {Requires physical interaction / visual inspection / special firmware} |
```

---

## 12. Revision History

```markdown
## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | {DATE} | {AUTHOR} | Initial test specification |
```

---

## 13. Automated Test Edge Cases

When automated tests cover edge cases that are worth documenting (boundary values, special inputs, protocol quirks), add a section describing what the test suites cover. This goes beyond the file-level counts in §10 (Automated Test Coverage) by describing the *specific edge cases* tested.

```markdown
## {N}. Automated Test Edge Cases

### {N}.1 {Test Suite 1} Edge Cases

These edge cases are covered by the {TEST_SUITE} tests ({HARDWARE_REQUIREMENT}):

#### {Module or Test File} (`{test_file}`)
- {EDGE_CASE_1}: {specific values and behavior tested}
- {EDGE_CASE_2}: {specific values and behavior tested}
- {EDGE_CASE_3}: {specific values and behavior tested}

#### {Module or Test File} (`{test_file}`)
- {EDGE_CASE_1}: {specific values and behavior tested}
- {EDGE_CASE_2}: {specific values and behavior tested}

### {N}.2 {Test Suite 2} Edge Cases

These edge cases are covered by the {TEST_SUITE} tests ({HARDWARE_REQUIREMENT}):

#### {Module or Test File} (`{test_file}`)
- {EDGE_CASE_1}: {specific values and behavior tested}
- {EDGE_CASE_2}: {specific values and behavior tested}
```
