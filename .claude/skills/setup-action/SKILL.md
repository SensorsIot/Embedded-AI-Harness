---
name: setup-action
description: Sets up GitHub Actions for ESP32 projects — building ESP-IDF firmware in a pinned container, taking the version from the git tag, proving a published image is the variant it claims to be, and publishing artefacts and a release when a tag is pushed. Also covers the pre-merge gate: lint plus the tests a hosted runner can actually run, and which tiers it cannot reach. Use this skill whenever CI comes up for an ESP32 or testbench project — a new project needing a build workflow, a release that should publish firmware, a gate that keeps turning red, or the question "why isn't this checked automatically". Triggers on "GitHub Action", "CI", "workflow", "pipeline", "build firmware in CI", "publish a release", "release on tag", ".github/workflows", "pre-merge check", "self-hosted runner", "lint on push".
---

# CI for ESP32 projects

Two workflows with different jobs, and most projects want both:

| Workflow | Trigger | Answers |
|---|---|---|
| **build** | every push; publishes on a version tag | Can this be flashed, and where is the artefact? |
| **gate** | every push and PR | May this change land? |

The build workflow is the substantial one and comes first below. The gate is
simpler but has a rule that decides whether it is worth having at all: **a gate
must be green from its first run**, or it teaches everyone to ignore a red tick.

Neither replaces hardware testing. A green tick means it compiles and the pure
logic passes.

---

# Part 1 — Build and publish firmware

Put this at `.github/workflows/build.yml` and fill in `<firmware-dir>`,
`<app-name>` and `<target>`. Drop `working-directory` if the ESP-IDF project sits
at the repository root.

**One build per run.** Most projects have one firmware, and the template defaults
to that: `MULTI_VARIANT: 'false'` pins every run to production, and `<marker>`
and `<alt-variant>` are then never read. Flip it to `'true'` only for a project
that genuinely ships a second image, and read "Variants" below before you do.

```yaml
name: Build Firmware

env:
  IDF_TAG: v6.0.2          # keep in step with the container tag below
  # The one switch for variant handling. Leave 'false' unless this project
  # really builds a second image; then set <marker> too.
  MULTI_VARIANT: 'false'
  VARIANT_MARKER: <marker>  # a string only the non-production image contains

on:
  push:
    branches: [main]
    tags: ['v*.*.*']
  workflow_dispatch:
    inputs:
      version:
        description: 'Version number (e.g. 1.2.0)'
        required: true
      variant:                       # inert while MULTI_VARIANT is 'false'
        description: 'Which firmware to build'
        type: choice
        options: [production, <alt-variant>]
        default: production

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

      - name: Decide what to build
        id: plan
        run: |
          VARIANT="${{ github.event.inputs.variant || 'production' }}"
          [ "$MULTI_VARIANT" = "true" ] || VARIANT=production

          if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
            VERSION="${{ github.event.inputs.version }}"
          elif [[ "$GITHUB_REF" == refs/tags/v* ]]; then
            VERSION=${GITHUB_REF#refs/tags/v}
          else
            VERSION="0.0.0-$(git rev-parse --short HEAD)"
          fi

          DEFAULTS="sdkconfig.defaults"
          if [ "$VARIANT" != "production" ]; then
            DEFAULTS="sdkconfig.defaults;sdkconfig.$VARIANT.defaults"
            VERSION="$VERSION-$VARIANT"
          fi

          { echo "variant=$VARIANT"; echo "version=$VERSION"
            echo "defaults=$DEFAULTS"; } >> $GITHUB_OUTPUT
          echo "Building the $VARIANT firmware as $VERSION"

      # -DSDKCONFIG: keep the config in the build dir — see "sdkconfig" below.
      - name: Build firmware
        run: |
          . $IDF_PATH/export.sh >/dev/null
          ARGS="-B build -DSDKCONFIG=$PWD/build/sdkconfig \
                -DSDKCONFIG_DEFAULTS=${{ steps.plan.outputs.defaults }} \
                -DPROJECT_VER=${{ steps.plan.outputs.version }}"
          idf.py $ARGS set-target <target>
          idf.py $ARGS build

      - name: Verify the image matches the variant asked for
        if: env.MULTI_VARIANT == 'true'
        run: |
          grep -q "$VARIANT_MARKER" build/<app-name>.bin && FOUND=yes || FOUND=no
          WANT=no; [ "${{ steps.plan.outputs.variant }}" = "production" ] || WANT=yes
          if [ "$FOUND" != "$WANT" ]; then
            echo "FATAL: ${{ steps.plan.outputs.variant }} image, marker found=$FOUND, expected=$WANT"
            exit 1
          fi
          echo "verified: ${{ steps.plan.outputs.variant }} image, marker $FOUND"

      - name: Collect artefacts
        run: |
          V="${{ steps.plan.outputs.version }}"
          cp build/<app-name>.bin firmware_v${V}.bin
          cp build/<app-name>.elf firmware_v${V}.elf
          # Cold-flash set, taken from flash_args rather than named here —
          # see "Never hand-write the image list" below.
          mkdir -p coldflash
          cp build/flash_args coldflash/
          awk '$1 ~ /^0x/ {print $2}' build/flash_args | while read -r f; do
            cp "build/$f" coldflash/ || { echo "FATAL: missing build/$f"; exit 1; }
          done
          cp build/sdkconfig sdkconfig.generated

      - uses: actions/upload-artifact@v4
        with:
          name: firmware-v${{ steps.plan.outputs.version }}
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
idf.py -B build -DPROJECT_VER="${{ steps.plan.outputs.version }}" build
```

Left unset, ESP-IDF falls back to `git describe`, and **the default shallow
checkout has no tags** — so the version silently degrades to a bare hash. Set
`fetch-depth: 0` whenever the version comes from git, as the template above does.

Only reach for the `sed` route when the project has already committed to a version
macro in a header. Then the `grep -q` after it is not optional: a `sed` whose
pattern stops matching after a refactor exits 0 having changed nothing, and the
release ships firmware reporting the *previous* version — invisible until someone
tries to work out whether an OTA actually applied.

## Variants

Skip this section entirely when the project builds one firmware, which is most of
them. `MULTI_VARIANT: 'false'` is not a stub to fill in later — it pins every run
to production, skips the marker check, and makes the `variant` input inert. The
cost of leaving the machinery in place unused is a `[ ... ] || VARIANT=production`
and one skipped step.

A **variant** is a second image carrying behaviour production must not have.
Whatever the project's is — a synthetic data source standing in for hardware that
is not there, verbose logging, a staging endpoint, factory-test commands, relaxed
certificate checking — it has the same two properties: somebody needs it
occasionally, and shipping it would be a quiet disaster rather than a loud one.
Name it whatever it is (`debug`, `staging`, `factory`) and substitute that for
`<alt-variant>`; the template only assumes there is one such image and that
`sdkconfig.<alt-variant>.defaults` selects it.

**Build one variant per run, chosen when the run starts.** Building every variant
on every push doubles the runner time to produce an image nobody asked for. A
variant is wanted at a specific moment — when somebody is about to flash it — so
put it behind a `workflow_dispatch` choice input, and let pushes and tags build
production. A tag must always be production: a release is the one thing that must
never be anything else.

Put the variant name in the version string (`1.2.0-debug`) so an artefact that
escapes into the wrong hands identifies itself, and so the device reports what it
is at runtime rather than requiring someone to remember.

**Verify the image matches the variant asked for.** Gate the behaviour at compile
time. Two mechanisms, and the project's own architecture decides which:

```cmake
# CMake option — good when the flag only guards C/C++ code
option(ALT_BUILD "Behaviour that must never ship" OFF)
```
```bash
# Kconfig symbol — required when the flag must also reach sdkconfig,
# menuconfig, or component configuration. Select it with a second
# defaults file rather than -D:
idf.py -DSDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.<alt-variant>.defaults" build
```

A `-DCONFIG_FOO=y` on the command line does **not** set a Kconfig symbol; it
defines a CMake variable of that name and the build silently keeps the default.

Then grep the **built binary**, not the source, for a marker string only the
non-production image contains. Checking the artefact is what makes the test worth
running: it survives a broken `#ifdef`, a stale build directory, a defaults file
that stopped being applied, and an option that quietly stopped being passed —
every failure mode where the source still reads correctly.

Assert in **both** directions: production lacks the marker, and the variant
carries it. The second is not symmetry for its own sake. A variant that silently
reverted to production behaviour is worse than a broken one, because it keeps
working — it just stops being the thing under test, and every result taken from
it afterwards is meaningless while looking perfectly healthy. With one build per
run, each run checks its own image, so the run that produces the bad artefact is
the run that catches it.

**Keep `sdkconfig` in the build directory.** `-B` moves the *build* output but
not the config: ESP-IDF writes `sdkconfig` to the **project root**, and an
existing one outranks `sdkconfig.defaults` for every symbol it already mentions.
So a leftover from an earlier run — a previous variant, a developer's local
build, anything restored from a cache — silently overrides the defaults file and
the job cheerfully produces the wrong variant. What prevents it today is a side
effect: `set-target` deletes `sdkconfig` before regenerating it. Nothing states
that, and dropping `set-target` from a second invocation removes the protection
with no visible change.

State it instead, and pass the same flags to `set-target` and `build`:

```bash
ARGS="-B build -DSDKCONFIG=$PWD/build/sdkconfig -DPROJECT_VER=$V"
idf.py $ARGS set-target <target>
idf.py $ARGS build
```

Absolute, because `idf.py` does not resolve it against the project directory.
This also puts the file where the artefact step can find it — `build/sdkconfig`
does not exist otherwise, and `cp` fails the job at the very last step.

**The artefact still has to reach a device.** This skill ends where the upload
does. Fetching a run's artefact and flashing it belongs to
[`esp-idf-handling`](../esp-idf-handling/SKILL.md) — Step 3b for the download,
Step 4 for the flash. Worth knowing while designing the artefact set: it is the
consumer of everything published below, and it needs the explicit-offset form of
`/api/flash`, because a CI artefact carries no `flash_args`.

**Publish three kinds of thing.** The loose `.bin` is what OTA fetches; the
`.elf` is what symbolises a crash dump months later; the **cold-flash bundle** is
what a first USB flash needs. Ship the parts at their offsets rather than a
merged image — that is what flashing tools expect.

**Never hand-write the image list.** ESP-IDF emits `build/flash_args` holding the
exact offsets and filenames for this configuration; copy that and the files it
names. A list written by hand is right until the partition table changes, and
then wrong in a way nothing reports: turning on OTA adds a fourth image
(`ota_data_initial.bin` at `0xf000`) and moves the app from `0x10000` to
`0x20000`. A flash missing the first leaves the bootloader reading stale
OTA-select data; one using the old app offset writes into the wrong partition and
boots the previous firmware. Both look like a successful flash.

Keep the build's own filenames in the bundle: `flash_args` refers to each image
by basename, and the testbench's `/api/flash` pairs them on it.

Publish the generated `sdkconfig` too. It is derived from `sdkconfig.defaults`
and not committed, so once the runner is gone the effective configuration of a
release is otherwise unrecoverable.

**Build on every push; publish only on a tag.** Building early tells you a
change does not compile while it is still the change you are looking at. What
must stay deliberate is the *release*, so the release step alone is gated on
`refs/tags/`; a push and a manual run produce artefacts nobody outside the
project can reach. `workflow_dispatch` is then the way to get a flashable image
without cutting a release.

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

Anything needing the hardware. A runner cannot talk to a device over USB, reach
equipment on your LAN, or drive a radio. Those tests stay a pre-release step run
against real hardware, and the gate should say so in its name.

Gating them at all needs a **self-hosted runner on a machine that can reach the
hardware**, and that is a real commitment: a test run physically drives the
hardware, so the runner owns it for the duration and a queued second job fights
the first. Raise it as a choice rather than building it unasked — a
`workflow_dispatch` job a human triggers when the hardware is free is usually the
right first step, not a `push` trigger.

## Release verification — the journey on the shipped bytes

The one hardware job that *does* belong in CI, because it closes the weakest
link in every firmware release: the tested build and the shipped build are
different binaries (same source, same pinned toolchain, but a rebuild). The
release workflow gains a verify job between build and publish:

```yaml
verify:
  needs: build
  runs-on: [self-hosted, testbench]     # the project's devcontainer
  steps:
    - uses: actions/download-artifact@v4          # the bytes from THIS run
    - run: |                                      # discover the bench, read the
        pytest tests/bench --journey \            # slot from harness config,
          --firmware "$MERGED_BIN"                # flash, run the journey
release:
  needs: verify                          # red journey ⇒ nothing publishes
```

**The runner lives inside the project's devcontainer** — one project, one
container; the devcontainer already holds the bench tier, TestbenchDriver,
discovery and slot config, which is everything this job needs (it never
builds). Register per-repo, ephemeral, labels `[self-hosted, testbench]`;
trigger on tag push only; approval required for outside contributors — the
public-repo self-hosted trap is real.

The devcontainer runs 24/7; the testbench and DUT may not. An unreachable
bench is an **unmet precondition**: the job reports `not done` with the
reason and publishes nothing — power the bench, re-run the job. Never retry
blind.

**Shipped = release published AND the journey green on the exact bytes users
download.** Dev builds never mint tags — `git describe` identifies them — so
the tag namespace stays what users browse: releases only.

## Keep the docs true

When a gate lands or its scope changes, the project's build contract changes with
it. Update the testing standard in the same commit — documentation describes what
is enforced now, not what was planned.

The testbench's own gate, its tiers, and its lint debt are in
[`references/testbench-gate.md`](references/testbench-gate.md).
