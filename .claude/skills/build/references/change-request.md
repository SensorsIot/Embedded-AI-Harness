# Change request — how a feature enters a shipped or living project

The steady state of AI Closed-Loop Programming. The initial journey happens
once; this happens every week for the product's life. Same phases, scaled to
the delta — each phase asks "does this change touch me?"

## The intake rule

**No code without a clause.** When the user asks for behaviour no requirement
covers, the loop refuses to build it and routes it through Definition first.
Not an obstacle — the mechanism that makes drift impossible: the only road to
code runs through the FSD, so the spec cannot fall behind the product.

## The walk

1. **Refuse and route.** State plainly: no clause covers this; starting the
   Definition delta. Hand the ask to `/define` update mode.
2. **Definition, as a delta** — minutes, not an evening. `/define` asks only
   what the delta forces (architecture, interfaces, timing), then lands the
   requirement with its verification contract born attached, plus any data
   model or interface catalogue amendments.
3. **Harness delta — usually nothing.** Only if a declared test needs a
   capability the testbench never declared; then the plan computes the block
   rather than anyone discovering it mid-session.
4. **Commissioning delta — only if hardware arrived.** New sensor, new peer:
   its never-seen-working parts get a debugging-agenda entry and a bring-up
   test first. Pure-firmware changes skip this entirely.
5. **The chain, per requirement** — declare (this is where missing equipment
   and undecided interfaces surface, e.g. a test needing "simulated midnight"
   forces a clock-set seam as a development obligation), xfail, code, flash,
   verify, green.

## Impact analysis — checked at declaration, not discovered later

- Which existing requirements the delta contradicts or tightens.
- Which interfaces and catalogue entries it touches.
- **Whether it changes the standard run.** If the ordinary journey now looks
  different, the journey tests are amended in the same delta — a stale gate
  rots into ceremony.
- Which existing tests become obsolete (deprecate, never delete — IDs are
  stable).

## Done

**The requirement is met AND the journey still runs** — the feature's own
tests green including prohibited outcomes, and the standard run green, both
derived from the plan, never declared. Then the manual absorbs what an
operator would notice, and the user ships whenever they choose to tag.
