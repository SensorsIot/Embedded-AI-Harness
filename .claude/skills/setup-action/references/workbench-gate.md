# The workbench's own gate

The instance of SKILL.md Part 2 that runs in this repository. Read when changing
`.github/workflows/ci.yml` here; ignore when setting CI up for another project.

## What it covers

`.github/workflows/ci.yml` runs `ruff check .` and the host tier on every push to
`main` and every pull request.

| Tier | Command | On a hosted runner? |
|---|---|---|
| **host** — 22 tests, pure logic | `pytest pytest/host/` | **Yes.** 0.16 s, no hardware |
| **bench** — 67 tests over HTTP | `pytest pytest/ --wt-url …` | **No.** Needs a live Pi with DUTs attached; a runner cannot reach the bench |

So the gate covers roughly a fifth of the suite. It catches the RF synthesis
maths, where a bug puts the bench on the wrong frequency silently — but a green
tick is not a claim that the bench works, which is why the workflow is named
`host tests + lint` and the badge reads `host tests`.

## Dependencies

The host tier is stdlib-only apart from pytest — verified in a clean venv on
Python 3.11. **Do not install `requirements-dev.txt` in CI**: it pulls `smbus2`
and `paho-mqtt`, which only the Pi needs, and a failure to build them would
present as a test failure.

Python is pinned to 3.11 to match Raspberry Pi OS bookworm, so CI cannot pass on
syntax the bench would reject. `pi/debug_controller.py` and `pi/ble_controller.py`
use `X | None` annotations without `from __future__ import annotations`, so 3.10
is the hard floor.

## Lint state

Clean, under the selection pinned in `pyproject.toml`. Getting there took fixing
24 findings:

| Where | Was | Resolution |
|---|---|---|
| `pi/serial_proxy.py` | 12 bare excepts | Given real types — `OSError` for socket and sysfs work, which also covers `serial.SerialException`; `(UnicodeError, OSError)` for the log's text-decode path |
| `pi/wifi_controller.py` | 1 unused binding | Removed |
| across `pi/`, `.claude/` | 8 unused imports, 1 multi-import line | Auto-fixed |
| `.claude/skills/*/discover-workbench.py` | 2 ambiguous `l` loop variables | Renamed |

`pi/scripts/espota.py` is **excluded**: vendored Arduino code, including a genuine
`except e:` that raises `NameError` instead of logging. Its defects are
upstream's, and restyling it would conflict on the next vendor bump.

`pytest/`, `mcp/` and `test-firmware/` were already clean.

## What is not gated

There is no build workflow here — the workbench is a Python service on a Pi, not
firmware, so SKILL.md Part 1 does not apply. `test-firmware/` is built by
developers against a live bench, not in CI.

Gating the bench tier would need a self-hosted runner with the bench idle. Not
built; see SKILL.md Part 2.
