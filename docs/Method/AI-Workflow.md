# Embedded Workbench — AI Workflow (the build contract)

Read this before any change. It is how new functionality is built and how the
documentation stays in sync with it.

## The loop

**1. Locate the contract.** Find the FSD rule the work serves in
[`../Embedded-Workbench-FSD.md`](../Embedded-Workbench-FSD.md) — by FR number, or
via Appendix D for anything API-shaped. If no rule covers it, the work starts by
defining the **WHAT** (a new atomic, falsifiable requirement), not by writing
code.

**2. Build per the Method.** Follow [`standards/`](standards/) and
[`project/`](project/). Reuse an existing endpoint, controller, or skill before
adding new code. Make the smallest change that satisfies the rule.

**3. Test — the gate.** A change is not done until it is verified against real
hardware. This project's tests are almost entirely **bench tier**: they drive a
live Pi over HTTP (see [`standards/testing.md`](standards/testing.md)). At
minimum, exercise the changed endpoint against the bench and paste the result.
A bug fix reproduces the failure first.

**4. Reconcile the three planes.**
- **FSD** absorbs new or changed behaviour — new endpoints go in the owning FR
  *and* Appendix D. Verify against the code; do not transcribe a defect into a
  requirement.
- **Handbook** absorbs anything an operator would notice — a new command, a new
  failure mode, a new troubleshooting row.
- **Method** changes only when the lesson is universally true for this project.
- All present-state. No "now uses", no "previously".

**5. Verify both directions.** Every endpoint in `pi/portal.py` appears in
Appendix D, and every endpoint in Appendix D exists in the code. This is
mechanically checkable — do it rather than assuming:

```bash
for p in $(grep -oE "/api/[a-zA-Z0-9_/-]+" pi/portal.py | sort -u); do
  grep -qF "$p" docs/Embedded-Workbench-FSD.md || echo "UNDOCUMENTED $p"
done
```

## Requirement quality gate

Before a new requirement enters the FSD it must be **atomic** (one obligation),
**falsifiable** (precondition, stimulus, observable response, deadline, tolerance,
failure behaviour, tier), **free of weasel words** (*appropriate, graceful,
user-friendly, reasonable, sufficient, robust, seamless, acceptable, normal
operation, best effort*), and **provenance-tagged** (`[user]`, `[derived]`,
`[code]`, `[pack:esp32]`).

## Deploying a change to the bench

The service runs from `/usr/local/bin/`, **not** from the git checkout — editing
the repo on the Pi changes nothing until you copy it across.

```bash
scp pi/portal.py pi@workbench.local:/tmp/portal.py
ssh pi@workbench.local 'sudo cp /tmp/portal.py /usr/local/bin/rfc2217-portal && sudo systemctl restart rfc2217-portal'
```

Other modules install under their own names (`debug_controller.py`,
`wifi_controller.py`, …) — same pattern, same restart.

**SSH is for deploying code and nothing else.** Never drive the bench over SSH:
every operation has an HTTP endpoint, and `pytest/workbench_driver.py` wraps them
all. Reaching for SSH to *do* something means the API is missing a capability —
add the endpoint instead.

## Roles

Any change may touch the FSD and Handbook. Changing the Method itself is a
deliberate act: it re-scopes every future change, so state what rule you are
adding and why it is universal, not local to the task in hand.
