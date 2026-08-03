# Standard — Testing

Testing is part of the build contract, not an afterthought. Every behaviour rule
in the FSD is verifiable, and every change ships the evidence that it works.

## Tiers

| Tier | Runs on | Speed | Catches |
|------|---------|-------|---------|
| **host** | Dev machine, no hardware | ms | Pure logic: parsing, framing, timing arithmetic, slot-key derivation, decision functions |
| **bench** | A live Pi plus real DUTs, driven over HTTP | seconds to minutes | Everything else: hotplug, serial, flashing, WiFi, RF, debug, end-to-end recovery |

Use the cheapest tier that can catch the failure.

**Current state, stated honestly:** the host tier exists but is thin — 22 tests
in `pytest/host/`, covering the RF synthesis maths (Si5351 dividers, GPCLK
frequency set, Morse keying). They run in under a second with nothing plugged in:

```bash
pytest pytest/host/          # no --wt-url, no hardware
```

The other 67 tests in `pytest/workbench_test.py` still drive a live bench over
HTTP and collect nothing useful without `--wt-url` pointing at a real Pi.

The largest remaining gap is `portal.py`: it imports `gpiod`, so it cannot be
imported on a dev machine at all, and slot-key derivation and phantom-port
filtering — the identity logic the whole product rests on — are unreachable from
the host tier until they are extracted or `gpiod` is installable here.

There is still no CI, so "green before commit" remains a convention rather than
an enforced gate. The host tier is what makes CI possible when it is wanted.

The lever that fixes it is in [`../project/architecture.md`](../project/architecture.md):
**extract pure cores**. Slot-key derivation from a USB path, flap-window
arithmetic, rtl_433 output parsing, and Morse timing are all decidable without
hardware and all currently welded to I/O. Each extraction moves a test down a
tier. Do this opportunistically when touching such code — do not treat a
bench-only suite as the natural order of things.

## Rules

- **Every Must/Should rule has a test case.** A rule with no case is an untested
  contract — surface it as a gap rather than leaving it silent.
- **Every change ships its evidence.** For bench-tier work that means the actual
  command and its output, not an assertion that it works. A bug fix reproduces the
  failure first; a fix whose failure was never reproduced has not been shown to
  fix anything.
- **Test cases trace to FR IDs**, so coverage is computed rather than claimed.
- **Coverage is generated, never hand-maintained.** A hand-filled
  "Covered / GAP" column is stale the moment a test changes.
- **State machines are covered per transition, not per state.** The flap-recovery
  and WiFi-mode machines have edges that only appear under failure; reaching a
  state proves nothing about the five edges into it.
- **Mark unbuilt cases** with their prerequisite so the coverage picture stays
  honest.
- **Tests that need a DUT are marked `requires_dut`** and skipped unless
  `--run-dut` is passed. Do not silently depend on hardware being present.

## Verifying against the bench

Never SSH into the Pi to check something — every observation has an endpoint.

```bash
pytest pytest/ --wt-url http://workbench.local:8080            # no DUT needed
pytest pytest/ --wt-url http://workbench.local:8080 --run-dut  # full
```

## Security testing

The workbench has **no authentication** — that is a deliberate, documented
position for an instrument on a trusted lab network, not an oversight, and it is
recorded as such in the FSD and the Handbook. The corresponding rule is therefore
about honesty rather than hardening: do not add a security requirement the product
does not meet, and do not write an acceptance criterion that cannot fail.

Where security cases *are* written (for DUT firmware the bench provisions, for
instance), anchor them to a published standard — OWASP ASVS for requirements, CWE
to classify a finding, CVSS to score it — and to the threat model the FSD
declares. "Encrypted or obfuscated" is not a criterion; "the literal credential
does not appear in a raw partition dump" is.
