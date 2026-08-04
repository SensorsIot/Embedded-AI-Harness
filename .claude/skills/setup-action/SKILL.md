---
name: setup-action
description: Use this skill whenever continuous integration comes up for the workbench or for an ESP-IDF firmware project — creating or changing a GitHub Actions workflow, adding a pre-merge gate, wiring lint or host-tier tests into CI, building firmware in Actions, publishing a release on a tag, proving a production image is not a test build, adding a self-hosted runner, or answering "why isn't this checked automatically". It knows which test tiers a hosted runner can reach and which it cannot, and how to land a gate that is green on day one instead of red and ignored. Triggers on "GitHub Action", "CI", "workflow", "pipeline", "pre-merge check", "run the tests automatically", ".github/workflows", "self-hosted runner", "lint on push", "build firmware in CI", "release on tag".
---

# CI

Two jobs, and they answer different questions. **Gating** decides whether a change
may land — lint and the tests a hosted runner can actually run. **Building**
turns a tag into an artefact someone can flash. The workbench needs the first;
an ESP-IDF firmware project needs both.

One rule governs everything below: a gate must be green from its first run, or it
teaches everyone to ignore a red tick.

Part 1 is the workbench's gate. Part 2 is firmware builds, and it is where a
firmware project should start.

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

**Pin the rule selection before you count anything.** Ruff's default selection
changes between releases: on this tree the same `ruff check .` reported 36 errors
at one point and 416 a few weeks later, with no config file present and
`--isolated` giving the same 416. Any count below is meaningless without a pinned
selection, and an unpinned gate turns red on rules nobody chose.

```toml
# pyproject.toml
[tool.ruff]
target-version = "py311"
exclude = ["pi/scripts/espota.py"]

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F"]     # ruff's documented default, pinned
```

Pin the ruff *version* in the workflow too. Widen the selection deliberately,
with the fixes in the same commit — never as a side effect of an upgrade.

With that selection pinned, `ruff check .` finds **36 errors**. A gate that is red from its first run
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

## The gate workflow

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

## Keep the docs true

`docs/Harness/standards/testing.md` describes what the gate covers and what it
does not. Any change to the workflow's scope changes that section in the same
commit — the Harness describes the build contract as it is, not as it was.

The README badge is deliberately labelled `host tests` rather than `build` or
`CI`, so a green tick cannot be read as a claim about the bench:

```markdown
[![host tests](https://img.shields.io/github/actions/workflow/status/SensorsIot/Universal-Embedded-Workbench/ci.yml?branch=main&label=host%20tests)](https://github.com/SensorsIot/Universal-Embedded-Workbench/actions/workflows/ci.yml)
```

---

# Part 2 — Building ESP-IDF firmware

A firmware repo's CI has a different job: turn a tag into something flashable,
reproducibly, without anyone needing a toolchain installed.

## Run the job inside Espressif's image

```yaml
env:
  IDF_TAG: v6.0.2

jobs:
  build:
    runs-on: ubuntu-latest
    container: espressif/idf:v6.0.2      # keep in step with IDF_TAG
    defaults:
      run:
        working-directory: <firmware-dir>
        shell: bash
    steps:
      - uses: actions/checkout@v4
      - run: . $IDF_PATH/export.sh >/dev/null && idf.py --version
```

No toolchain install step, no caching to get wrong. **Pin the exact tag.** Under
PlatformIO the IDF version is chosen indirectly by the platform package, which
typically lags the current IDF release by one or two patch versions. A container
tag says exactly what built the binary.

Echo `idf.py --version` in its own step. When a build behaves differently from a
developer's machine, that line is the first thing worth reading.

## Take the version from the tag, and verify the substitution

```yaml
- name: Extract version from tag
  id: version
  run: |
    if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
      VERSION="${{ github.event.inputs.version }}"
    else
      VERSION=${GITHUB_REF#refs/tags/v}
    fi
    echo "version=$VERSION" >> $GITHUB_OUTPUT

- name: Update firmware version
  run: |
    VERSION="${{ steps.version.outputs.version }}"
    sed -i "s/^#define FW_VERSION \".*\"/#define FW_VERSION \"$VERSION\"/" <version-header>
    grep -q "^#define FW_VERSION \"$VERSION\"" <version-header>
```

The `grep -q` is the part people skip. A `sed` whose pattern stops matching after
a refactor exits 0 having changed nothing, and the release then ships firmware
reporting the previous version — which is invisible until someone tries to work
out whether an OTA actually landed. Assert the edit happened.

`esp_app_desc_t` picking the version up from git is the alternative and needs no
`sed` at all; use it where the project has not already committed to a macro.

## Prove a production image is not a test build

This is the most valuable step in the whole workflow, and the failure it prevents
is not hypothetical: a device shipped with its simulated-data build publishes
synthetic readings that look entirely real to whatever consumes them.

A compile-time option gates the test behaviour:

```cmake
option(SIM_BUILD "Simulated sensor data and debug logging (never ship)" OFF)
```

Both variants are built into separate directories, then the *binaries* are
checked for a string only the test build can contain:

```yaml
- name: Build production firmware
  run: . $IDF_PATH/export.sh >/dev/null && idf.py -B build/prod set-target esp32c3 && idf.py -B build/prod build

- name: Build test firmware
  run: |
    . $IDF_PATH/export.sh >/dev/null
    idf.py -B build/test -DSIM_BUILD=1 set-target esp32c3
    idf.py -B build/test -DSIM_BUILD=1 build

- name: Verify the test build really is a test build
  run: |
    if grep -q "<SIM-MARKER>" build/prod/<app>.bin; then
      echo "FATAL: production image contains simulated-data code"; exit 1; fi
    if ! grep -q "<SIM-MARKER>" build/test/<app>.bin; then
      echo "FATAL: test image lacks simulated-data code"; exit 1; fi
```

Both directions matter. The first catches a shipped test build; the second
catches a test build that silently stopped being one, which would make every
bench run meaningless while looking fine.

The check works on the artefact rather than the source, so it survives a broken
`#ifdef`, a stale build directory, or an option that quietly stopped being
passed. Any project with a simulated or debug variant wants this, and the marker
string costs nothing.

## Publish on a tag, artefacts always

```yaml
on:
  push:
    tags: ['v*.*.*']
  workflow_dispatch:
    inputs:
      version: { description: 'Version number', required: true }

permissions:
  contents: write        # required to create the release
```

`workflow_dispatch` alongside the tag trigger gives a way to produce a build
without cutting a release — useful when a bench run needs an artefact.

Upload the loose `.bin` and `.elf` for OTA and for symbolising a crash dump, and
a **cold-flash bundle** — `bootloader.bin`, `partitions.bin`, `firmware.bin` —
for the first USB flash. Three parts at their offsets, not a merged image: that
is what a flashing tool expects.

Publish the generated `sdkconfig` as an artefact. It is derived from
`sdkconfig.defaults` and not committed, so when a build misbehaves the effective
configuration is otherwise unrecoverable after the runner is gone.

```yaml
- uses: softprops/action-gh-release@v1
  if: startsWith(github.ref, 'refs/tags/')
  with:
    files: |
      <firmware-dir>/firmware_*.bin
      <firmware-dir>/firmware_*.elf
    generate_release_notes: true
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## What this does not do

It builds; it does not test. A firmware repo still needs a host tier for the
logic that can be tested without hardware, gated the way Part 1 describes, and
hardware tests that no hosted runner can reach. A green build badge means it
compiles.
