# Standard — Testing (portable)

Testing is part of the build contract, not an afterthought. Every behaviour rule
in the FSD is verifiable, and every change ships the test that proves it.

## Tiers

Order tests by cost. Use the cheapest tier that can catch the failure, and reserve
the expensive ones for behaviour no cheaper tier can reach. Name the tiers for the
platform — an embedded project typically uses:

| Tier | Runs on | Speed | Catches |
|------|---------|-------|---------|
| **host** | Dev machine, plain compiler | ms, every commit | Pure logic: parsing, encoding, math, bounds, state transitions. No hardware, no framework. |
| **target** | The real device | seconds, pre-merge | Bus timing, persistence, servers, RTOS behaviour. |
| **bench** | Device plus real peers | minutes, pre-release | End-to-end: recovery, reconnection, wall-clock timing. |

A cloud project substitutes unit / integration / staging; the structure is the
same. Every component maps to the tier that owns it, and the mapping is published
as a component × tier matrix.

## Rules

- **Every Must/Should rule has a test case.** A rule with no case is an untested
  contract — surface it as a gap rather than leaving it silent.
- **Every change ships its test.** Not done until the case is written and the test
  passes. Bug fixes write the regression test **first**, and it must fail before
  the fix — a regression test that never failed proves nothing.
- **Test cases trace to rule IDs.** Each case names the requirement(s) it
  verifies, so coverage is computed rather than asserted.
- **Coverage is generated, never hand-maintained.** A hand-filled "Covered / GAP"
  column is stale the moment a test changes.
- **State machines are covered per transition, not per state.** Reaching a state
  proves nothing about the five edges into it.
- **No silent gaps.** A specified-but-unbuilt case is marked with its prerequisite
  so the coverage picture stays honest.
- **The suite is green before commit.** A failing suite blocks the commit.

## Security testing

Security cases are grounded in published standards rather than ad-hoc checks, and
are written for the threat model the FSD declares — not imported wholesale.

| Standard | Role |
|----------|------|
| **OWASP ASVS** | Requirements catalogue — each verification requirement is a candidate case |
| **OWASP Top 10** / **WSTG** | Common risk classes and the procedures that test them |
| **CWE** | Classify each finding by weakness ID |
| **CVSS** | Score severity |
| **NIST SP 800-115** | Methodology for technical security testing |

- Every security-relevant rule — authentication, authorization, input validation,
  secrets handling, cryptography — has a case tagged with its standard reference.
- A security criterion must be able to **fail**. "Encrypted or obfuscated" cannot;
  "the literal credential does not appear in a raw partition dump" can.
- Where the threat model does not justify a protection, record that as an accepted
  risk rather than writing a requirement nobody implements.
