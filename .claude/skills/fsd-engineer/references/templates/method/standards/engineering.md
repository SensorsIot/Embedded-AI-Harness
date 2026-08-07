# Standard — Engineering conventions (portable)

Project-agnostic build rules. Trim what does not apply; keep each as a single
present-state rule.

- **Reuse before adding** — search for an existing helper, module, or skill before
  writing new code.
- **Smallest change that satisfies the rule** — no speculative scope, no drive-by
  refactors bundled with a fix.
- **One module per component** — never fold an interface into its only consumer.
  A component that cannot be named cannot be tested.
- **Dependencies point one way** — lower layers never import higher ones. Where
  the need seems to invert, invert it properly at the composition root rather than
  reaching upward.
- **Extract pure cores** — separate the decision from the I/O. A size check, a
  parser, a state transition, or a unit conversion should be a free function with
  no hardware, network, or filesystem dependency, so the cheapest test tier can
  reach it.
- **Verification before commit** — the project's build, lint, and test commands
  all pass. <Name them here.>
- **Errors fail loudly** — actionable messages, no silent catches, no swallowed
  return codes. An ignored error is a defect even when nothing breaks yet.
- **Secrets are never in code or documentation** — only their *location* is
  documented. Validate all external input. Least privilege by default.
- **Commits** — <convention>. Never commit generated output, build artifacts,
  temporary directories, or secrets.
