---
name: setup-action
description: Use this skill whenever continuous integration for this repo comes up — creating or changing a GitHub Actions workflow, adding a pre-merge gate, wiring lint or the host-tier tests into CI, adding a self-hosted runner, or answering "why isn't this checked automatically". It knows which of the two test tiers can run on a hosted runner and which cannot, and how to land a gate that is green on day one instead of red and ignored. Triggers on "GitHub Action", "CI", "workflow", "pipeline", "pre-merge check", "run the tests automatically", ".github/workflows", "self-hosted runner", "lint on push".
---

# CI for the workbench

There is no CI today. `docs/Harness/standards/testing.md` says so plainly, and
that honesty is the starting point: any gate added here has to be one that stays
green, or it teaches everyone to ignore a red tick.

## What can and cannot run on a hosted runner

The repo has two test tiers, and only one of them is CI-able:

| Tier | Command | Hosted runner? |
|---|---|---|
| **host** — 22 tests, pure logic | `pytest pytest/host/` | **Yes.** 0.16 s, no hardware |
| **bench** — 67 tests over HTTP | `pytest pytest/ --wt-url …` | **No.** Needs a live Pi with DUTs plugged in; a GitHub-hosted runner cannot reach `workbench.local` |

So a hosted workflow gates roughly a fifth of the suite. That is worth having —
it catches the RF synthesis maths, where a bug puts the bench on the wrong
frequency silently — but do not let a green tick be read as "the bench works".
Say so in the workflow name and in the README badge.

**Dependencies are trivially small.** The host tier is stdlib-only apart from
pytest itself — verified in a clean venv on Python 3.11: `pip install pytest`,
then `pytest pytest/host/` gives 22 passed. Do not install
`requirements-dev.txt` in CI; it pulls `smbus2` and `paho-mqtt`, which only the
Pi needs.

## The lint trap — read this before adding `ruff check .`

`ruff check .` finds **36 errors today**. A gate that is red from its first run
gets muted within a week. The 36 are not one problem, they are three:

| Where | Count | What to do |
|---|---|---|
| `pi/scripts/espota.py` | 12 | **Exclude.** Vendored upstream Arduino code — not ours to restyle. It even has a genuine `except e:` (`F821`, undefined name) on line 220, but fixing upstream code invites a merge conflict on the next vendor bump |
| `pi/` proper | 21 | **Fix.** 12 bare-except, 8 unused-import, 1 unused-variable. `ruff check pi --fix` clears 8; the bare-excepts want a real exception type and a minute of thought each |
| `.claude/` helper scripts | 3 | **Fix.** Two ambiguous `l` loop variables and one auto-fixable |

`pytest/`, `mcp/`, `test-firmware/` and `container/` are already clean.

**The recommendation: fix the 24 and exclude the vendored file, then gate the
whole repo.** It is about an hour, it leaves a gate that means something
permanently, and it avoids the alternative — linting only changed files — which
is more workflow machinery and silently skips a push straight to `main`.

If that hour is not available now, gate only the directories that are already
clean and widen later. That is honest and green; a repo-wide `continue-on-error`
lint step is neither.

Do not add `mypy --strict` to CI. It has never been clean here, and the same
argument applies with a far bigger bill.

## The workflow

Put it at `.github/workflows/ci.yml`:

```yaml
name: host tests + lint      # NOT the bench suite — that needs the Pi

on:
  push:
    branches: [main]
  pull_request:

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'   # matches Raspberry Pi OS bookworm
      - run: pip install pytest ruff
      - run: ruff check .
      - run: pytest pytest/host/ -q
```

Pin the Python version to what the Pi actually runs (bookworm ships 3.11) so CI
cannot pass on syntax the bench will reject.

Add the exclusion to `pyproject.toml` — the repo has no ruff config yet, so this
creates one:

```toml
[tool.ruff]
# Vendored from the Arduino project; restyling it would conflict on every bump.
exclude = ["pi/scripts/espota.py"]
```

## Gating the bench tier

The only way is a **self-hosted runner on a machine that can reach the Pi** —
the Pi itself, or a box on the lab network. That is a real commitment: the runner
needs the bench idle, and a test run physically drives hardware, so a queued
second job will fight the first. Raise it as a choice rather than building it
unasked; a `workflow_dispatch` job that a human triggers when the bench is free
is usually the right first step, not a `push` trigger.

## When CI lands, fix the docs

`docs/Harness/standards/testing.md` currently states there is no CI and that
"green before commit" is a convention rather than an enforced gate. That sentence
becomes false the moment this workflow merges. Update it in the same commit —
the Harness describes the build contract as it is, not as it was.

A README badge is worth adding at the same time, with a name that does not
overclaim:

```markdown
![CI](https://img.shields.io/github/actions/workflow/status/SensorsIot/Universal-Embedded-Workbench/ci.yml?branch=main&label=host%20tests)
```
