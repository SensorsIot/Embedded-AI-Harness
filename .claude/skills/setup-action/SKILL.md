---
name: setup-action
description: Sets up GitHub Actions for ESP32 projects — building ESP-IDF firmware in a pinned container, taking the version from the git tag, proving a production image is not a simulated build, and publishing artefacts and a release when a tag is pushed. Also covers the pre-merge gate: lint plus the tests a hosted runner can actually run, and which tiers it cannot reach. Use this skill whenever CI comes up for an ESP32 or workbench project — a new project needing a build workflow, a release that should publish firmware, a gate that keeps turning red, or the question "why isn't this checked automatically". Triggers on "GitHub Action", "CI", "workflow", "pipeline", "build firmware in CI", "publish a release", "release on tag", ".github/workflows", "pre-merge check", "self-hosted runner", "lint on push".
---

# CI for ESP32 projects

Two workflows with different jobs, and most projects want both:

| Workflow | Trigger | Answers |
|---|---|---|
| **build** | a version tag | Can this be flashed, and where is the artefact? |
| **gate** | every push and PR | May this change land? |

The build workflow is the substantial one and comes first below. The gate is
simpler but has a rule that decides whether it is worth having at all: **a gate
must be green from its first run**, or it teaches everyone to ignore a red tick.

Neither replaces hardware testing. A green tick means it compiles and the pure
logic passes.

---

# Part 1 — Build and publish firmware

Put this at `.github/workflows/build.yml` and change the three placeholders:
`<firmware-dir>`, `<app-name>`, `<target>`. Drop `working-directory` if the
ESP-IDF project sits at the repository root.

```yaml
name: Build Firmware

env:
  IDF_TAG: v6.0.2          # keep in step with the container tag below

on:
  push:
    tags: ['v*.*.*']
  workflow_dispatch:
    inputs:
      version:
        description: 'Version number (e.g. 1.2.0)'
        required: true

permissions:
  contents: write          # required to create the release

jobs:
  build:
    runs-on: ubuntu-latest
    container: espressif/idf:v6.0.2
    defaults:
      run:
        working-directory: <firmware-dir>
        shell: bash

    steps:
      # Must come first, and must not be skipped. The container runs as root
      # while the workspace belongs to the runner user, so every git call in a
      # `run:` step dies with "detected dubious ownership" — see "The container
      # runs as the wrong user" below.
      - name: Trust the workspace
        working-directory: ${{ github.workspace }}
        run: git config --global --add safe.directory '*'

      - uses: actions/checkout@v4
        with:
          fetch-depth: 0     # see "Versioning" below — tags are needed

      - name: Show the IDF version actually used
        run: . $IDF_PATH/export.sh >/dev/null && idf.py --version

      - name: Resolve version
        id: version
        run: |
          if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
            VERSION="${{ github.event.inputs.version }}"
          else
            VERSION=${GITHUB_REF#refs/tags/v}
          fi
          echo "version=$VERSION" >> $GITHUB_OUTPUT

      # -DSDKCONFIG per variant — see "Two builds, one sdkconfig" below.
      - name: Build production firmware
        run: |
          . $IDF_PATH/export.sh >/dev/null
          V="${{ steps.version.outputs.version }}"
          ARGS="-B build/prod -DSDKCONFIG=$PWD/build/prod/sdkconfig -DPROJECT_VER=$V"
          idf.py $ARGS set-target <target>
          idf.py $ARGS build

      - name: Build simulated firmware
        run: |
          . $IDF_PATH/export.sh >/dev/null
          V="${{ steps.version.outputs.version }}"
          ARGS="-B build/sim -DSDKCONFIG=$PWD/build/sim/sdkconfig \
                -DSIM_BUILD=1 -DPROJECT_VER=$V-sim"
          idf.py $ARGS set-target <target>
          idf.py $ARGS build

      - name: Verify the two variants are actually different
        run: |
          if grep -q "<SIM-MARKER>" build/prod/<app-name>.bin; then
            echo "FATAL: production image contains simulated-data code"; exit 1; fi
          if ! grep -q "<SIM-MARKER>" build/sim/<app-name>.bin; then
            echo "FATAL: simulated image lacks simulated-data code"; exit 1; fi

      - name: Collect artefacts
        run: |
          V="${{ steps.version.outputs.version }}"
          cp build/prod/<app-name>.bin firmware_v${V}.bin
          cp build/prod/<app-name>.elf firmware_v${V}.elf
          cp build/sim/<app-name>.bin  firmware_v${V}-sim.bin
          mkdir -p coldflash
          cp build/prod/<app-name>.bin                      coldflash/firmware.bin
          cp build/prod/bootloader/bootloader.bin           coldflash/bootloader.bin
          cp build/prod/partition_table/partition-table.bin coldflash/partitions.bin
          cp build/prod/sdkconfig sdkconfig.generated

      - uses: actions/upload-artifact@v4
        with:
          name: firmware-v${{ steps.version.outputs.version }}
          path: |
            <firmware-dir>/firmware_v*.bin
            <firmware-dir>/firmware_v*.elf
            <firmware-dir>/sdkconfig.generated
            <firmware-dir>/coldflash/*.bin

      - uses: softprops/action-gh-release@v1
        if: startsWith(github.ref, 'refs/tags/')
        with:
          files: |
            <firmware-dir>/firmware_v*.bin
            <firmware-dir>/firmware_v*.elf
          generate_release_notes: true
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Why each part is the way it is

**Run inside `espressif/idf`, pinned to an exact tag.** No toolchain install, no
cache to get wrong, and the tag is the only honest statement of what built the
binary. Do not use `latest`. Under PlatformIO the IDF version is chosen
indirectly by the platform package, which lags the current IDF release — a
container tag removes that indirection entirely.

Echo `idf.py --version` in its own step. When a build behaves differently from a
developer's machine, that line is the first thing worth reading.

**The container runs as the wrong user, and git refuses.** Choosing a container
buys the toolchain and costs this: the runner checks the workspace out as its own
user, the `espressif/idf` image runs as root, and since git 2.35.2 a repository
owned by somebody else is refused outright:

```
fatal: detected dubious ownership in repository at '/__w/<repo>/<repo>'
Error: Process completed with exit code 128
```

`actions/checkout` exempts the workspace for itself, which is why checkout is
green and the failure lands later — on the first `run:` step that touches git,
usually the version resolution. The single line in the template fixes it for
every step:

```yaml
- run: git config --global --add safe.directory '*'
```

Use `'*'`, not `$GITHUB_WORKSPACE`: submodules and `$IDF_PATH` are git
repositories too, and the IDF build system reads them. Keep it as the first step
so it applies to checkout as well, and give it
`working-directory: ${{ github.workspace }}` — a job-level `working-directory`
pointing at `<firmware-dir>` would make it fail, because that directory does not
exist until checkout has run.

This is a container-only failure. It never appears on a plain `ubuntu-latest`
runner, so it cannot be reproduced by testing the steps locally.

**Versioning: prefer `PROJECT_VER` over `sed`.** ESP-IDF puts the version in
`esp_app_desc_t`, readable at runtime, so the same string reaches the device page,
the OTA log and the release asset and cannot disagree. Pass it explicitly:

```yaml
idf.py -B build/prod -DPROJECT_VER="${{ steps.version.outputs.version }}" build
```

Left unset, ESP-IDF falls back to `git describe`, and **the default shallow
checkout has no tags** — so the version silently degrades to a bare hash. Set
`fetch-depth: 0` whenever the version comes from git, as the template above does.

Only reach for the `sed` route when the project has already committed to a version
macro in a header. Then the `grep -q` after it is not optional: a `sed` whose
pattern stops matching after a refactor exits 0 having changed nothing, and the
release ships firmware reporting the *previous* version — invisible until someone
tries to work out whether an OTA actually applied.

**Verify the variants differ, in both directions.** A project with a simulated or
debug build needs proof that the shipped image is not it: shipping a simulated
build publishes synthetic data that looks entirely real to whatever consumes it.
Gate the behaviour at compile time. Two mechanisms, and the project's own
architecture decides which:

```cmake
# CMake option — good when the flag only guards C/C++ code
option(SIM_BUILD "Simulated data and debug logging (never ship)" OFF)
```
```bash
# Kconfig symbol — required when the flag must also reach sdkconfig,
# menuconfig, or component configuration. Select it with a second
# defaults file rather than -D:
idf.py -B build/sim -DSDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.sim.defaults" build
```

A `-DCONFIG_FOO=y` on the command line does **not** set a Kconfig symbol; it
defines a CMake variable of that name and the build silently keeps the default.
Then grep the **built binary**, not the source, for a marker string only the
simulated variant contains. Checking the artefact survives a broken `#ifdef`, a
stale build directory, or an option that quietly stopped being passed. The second
direction matters as much as the first: a simulated build that stopped being one
makes every bench run meaningless while looking fine.

**Two builds, one sdkconfig — give each variant its own.** `-B build/prod` and
`-B build/sim` separate the *build* directories, but not the config: ESP-IDF
keeps `sdkconfig` in the **project root**, so both variants write the same file.
An existing `sdkconfig` outranks `sdkconfig.defaults` for symbols it already
mentions, so the second build can inherit the first variant's configuration and
produce two images that differ only in their version string. What prevents it
today is a side effect — `set-target` deletes `sdkconfig` before regenerating it
— and dropping `set-target` on a second run, or reordering the steps, removes
that protection with nothing to show for it.

State it instead, and pass the same flags to `set-target` and `build`:

```bash
ARGS="-B build/prod -DSDKCONFIG=$PWD/build/prod/sdkconfig -DPROJECT_VER=$V"
idf.py $ARGS set-target <target>
idf.py $ARGS build
```

Absolute, because `idf.py` does not resolve it against the project directory.
This also puts the file where the artefact step can find it — `build/*/sdkconfig`
does not exist otherwise, and `cp` fails the job at the very last step.

**Publish three things, not one.** The loose `.bin` is what OTA fetches; the
`.elf` is what symbolises a crash dump months later; the **cold-flash bundle**
(`bootloader.bin`, `partitions.bin`, `firmware.bin`) is what a first USB flash
needs. Ship the three parts at their offsets rather than a merged image — that is
what flashing tools expect.

Publish the generated `sdkconfig` too. It is derived from `sdkconfig.defaults`
and not committed, so once the runner is gone the effective configuration of a
release is otherwise unrecoverable.

**Tags publish; `workflow_dispatch` does not.** Building on demand without
cutting a release is what you want when a bench run needs an artefact. Do not add
a `push: branches` trigger to this workflow — a release should be a deliberate
act.

## ESP-IDF 6 specifics

- **`cmake_minimum_required` must be 3.22 or later.** A 3.16 line copied from a
  5.x template fails to configure, and the failure is in CMake output nobody
  reads closely.
- **cJSON and mDNS are no longer bundled.** Anything using them needs
  `espressif/cjson` or `espressif/mdns` in `idf_component.yml`, and the first
  build needs network access to the component registry — which the container has,
  but an air-gapped runner would not.
- **Commit `dependencies.lock`, never `managed_components/`.** Without the lock a
  rebuild of an old tag can resolve different component versions.
- **Do not commit `sdkconfig`.** It is generated; `sdkconfig.defaults` is the
  source. Publishing the generated file as an artefact (above) covers the
  diagnostic need.

## Setting this up before the code exists

A project can be fully specified with no source yet, and that changes which
workflow may land:

- **The build workflow can.** It is tag-triggered, so it stays dormant until
  someone pushes a version tag — which nobody does before the firmware builds
  locally. Committing it early encodes the release requirements in executable
  form and tells whoever implements the firmware what layout to produce. Say in a
  header comment that it has never run and which names are guesses.
- **The gate cannot.** `pytest <dir>` on a missing directory exits 4, and a bare
  `pytest` with no tests exits 5. Either fails the job, so the gate would be red
  from its first run — the one thing that makes a gate worthless. Add it with the
  first test, not before.

Note also that **git does not track empty directories**, so a `tests/host/`
created locally will not exist in a fresh clone. A gate that passes on your
machine and fails on the runner usually means exactly this.

---

# Part 2 — The gate

A second workflow at `.github/workflows/ci.yml`, running on every push and pull
request. Its content depends on what the project has that a hosted runner can
actually run.

```yaml
name: host tests + lint     # name it for what it covers, not "CI"

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
          python-version: '3.11'
      - run: pip install 'pytest==8.*' 'ruff==0.16.1'
      - run: ruff check .
      - run: pytest <host-test-dir> -q
```

**Name the workflow for what it covers.** A tick labelled "CI" gets read as "it
works". One labelled "host tests + lint" cannot be. The same applies to the README
badge — set `label=host%20tests`, not `label=build`.

**Pin the linter version and its rule selection.** Ruff's default selection
changes between releases: on one tree the same `ruff check .` reported 36 errors
at one point and 416 later, with no config file present and `--isolated` giving
the same 416. An unpinned gate turns red on rules nobody chose, which is exactly
how a gate becomes something everyone ignores.

```toml
# pyproject.toml
[tool.ruff]
target-version = "py311"
exclude = ["<vendored-file>"]      # upstream code is not yours to restyle

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F"]   # ruff's documented default, pinned
```

Widen the selection deliberately, with the fixes in the same commit — never as a
side effect of an upgrade. Do not add `mypy --strict` to a gate unless it is
already clean; the same argument applies with a far bigger bill.

**Fix the findings rather than suppressing them.** If the current tree is not
clean, gate only the directories that are, and widen as they get fixed. That is
honest and green. A repo-wide `continue-on-error` lint step is neither.

**Install only what the gate needs.** A dev-requirements file usually pulls
hardware libraries that fail to build on a runner, and the failure then looks
like a test failure.

## What a hosted runner cannot reach

Anything needing the hardware. A runner cannot talk to a device over USB, reach a
bench on your LAN, or drive a radio. Those tests stay a pre-release step run
against real hardware, and the gate should say so in its name.

Gating them at all needs a **self-hosted runner on a machine that can reach the
hardware**, and that is a real commitment: the runner owns the bench while it
runs, so a queued second job fights the first. Raise it as a choice rather than
building it unasked — a `workflow_dispatch` job a human triggers when the bench
is free is usually the right first step, not a `push` trigger.

## Keep the docs true

When a gate lands or its scope changes, the project's build contract changes with
it. Update the testing standard in the same commit — documentation describes what
is enforced now, not what was planned.

The workbench's own gate, its tiers, and its lint debt are in
[`references/workbench-gate.md`](references/workbench-gate.md).
