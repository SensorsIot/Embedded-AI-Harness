# Finalisation — the quality gate and the lifecycle block

Read this when a document is about to be delivered, not while planning it.
Everything here is a last check on work already done.

Report any failure to the user rather than shipping past it. A checklist run
silently and reported as passed is worth nothing — name what failed and what you
did about it.

---

## 1. Quality checklist

### Requirements

- [ ] Every Must/Should has a stable ID in its component chapter and ≥ 1 test.
- [ ] **Atomic** — nothing joins two verbs, a behaviour and a deadline, or a
      success and a failure path.
- [ ] **Falsifiable** — precondition, stimulus, observable response, deadline,
      tolerance, failure behaviour, tier.
- [ ] **No weasel words** — grep the requirement lines against the list in
      `requirement-quality.md` §3. Restrict the grep to requirement text: a
      document that *names* the banned words in order to ban them will otherwise
      report itself as failing.
- [ ] **Typed** — architecture decisions and implementation recommendations are in
      the Harness, not written as functional requirements.
- [ ] **Provenance tagged**; nothing a pack proposed was adopted unaccepted;
      declines recorded under *Explicitly out of scope*. No unbound
      `{{parameters}}`.

### Models

- [ ] **State model** present if stateful, with a complete transition table —
      every (state × event) pair handled, ignored, or excluded with a reason.
- [ ] **Security profile** stated before any security requirement; no
      "encrypted or obfuscated"-style criterion, which cannot fail.
- [ ] §2.4 Component Layering (with diagram) and §x.0 Test Architecture present.

### Verification

- [ ] **Verification contract** on every approved Must/Should, including
      `prohibited_outcomes` — without them a recovery requirement passes when the
      device recovers by rebooting.
- [ ] **Test specs** for every applicable clause in the canonical schema, each
      with pass criteria, failure criteria, evidence, and cleanup; negative,
      boundary, state-transition, persistence and recovery variants where relevant.
- [ ] Every test allocated to a tier with a stated controllability method — no
      failure mode dropped for being awkward.
- [ ] **Seven lifecycle states** tracked per requirement; no `@fsd` tag or coverage
      figure presented as proof. Traceability is a pointer to generated artefacts,
      never a hand-filled Covered/GAP column.
- [ ] **Gaps by category** (specification / verification / implementation /
      evidence), with `pending` and `philosophical` clauses listed separately.

### Document

- [ ] **Planes separated**: no build conventions, install steps, or history in the
      FSD. Every fact in exactly one plane; the others link.
- [ ] Body grouped by layer Parts mirroring §2.4; chapters self-contained.
- [ ] Every test is declared in the plan file, linked not inlined.
- [ ] Chapter numbering sequential, heading depth ≤ `####`, phases carry scope,
      deliverables and exit criteria, no `<placeholder>` or `TODO` left.
- [ ] Written to the correct path and **committed**; in update mode, unaffected
      chapters byte-identical.

### Reporting the run

State the requirement count, how many carry full verification contracts versus
compact ones, and which checks failed. If the inferred complexity turned out to
disagree with the document that was produced — a "Medium" project that emitted 85
requirements — say so; the estimate was wrong, and a reader planning phases from
it needs to know.

---

## 2. Lifecycle metadata

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

`open_decisions` earns its place: each entry names the requirement it gates, so a
reader can see which parts of the document are provisional. An open decision with
no gated requirement is either resolved or was never load-bearing.
