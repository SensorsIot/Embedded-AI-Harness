# Universal Embedded Workbench

Raspberry Pi-based test instrument for ESP32 firmware: serial proxy (RFC2217), WiFi AP/STA, BLE, MQTT, GPIO, RF signal generation, SDR receive, GDB debug — all via one REST API on `:8080`.

## Start here

**Read [`docs/Harness/AI-Workflow.md`](docs/Harness/AI-Workflow.md) before making any change.** It is the build contract: how to find the rule a change serves, how to verify it, and how to keep the documentation in sync.

This file is assistant configuration, not project documentation. It holds no rules of its own — everything below is a pointer.

## The three planes

| Plane | Question | Document |
|-------|----------|----------|
| **WHAT** | What must be true of the bench? | [`docs/Embedded-Workbench-FSD.md`](docs/Embedded-Workbench-FSD.md) — FRs by subsystem; **Appendix D** is the complete HTTP API + MCP tool reference |
| **HOW** | How is it built and changed? | [`docs/Harness/`](docs/Harness/) — [workflow](docs/Harness/AI-Workflow.md), [architecture](docs/Harness/project/architecture.md), [conventions](docs/Harness/project/conventions.md), [standards](docs/Harness/standards/) |
| **OPERATE** | How do I run it? | [`docs/Embedded-Workbench-User-Manual.md`](docs/Embedded-Workbench-User-Manual.md) |

Route every sentence you write to exactly one plane. Externally observable ⇒ FSD. Constrains how code is written ⇒ Harness. Tells a human how to run it ⇒ Handbook. Don't add a fourth document, and don't restate a fact that already lives in one of them — link to it.

`README.md` is the GitHub landing page only.

## Layout

```
pi/            Portal + one controller module per instrument   (see Harness → architecture)
pytest/        WorkbenchDriver + the bench-tier test suite
mcp/           MCP server (70 tools) + Claude Desktop .mcpb
test-firmware/ ESP-IDF firmware that exercises the whole bench
.claude/       skills/ (one per instrument or workflow) + agents/
docs/          FSD · Harness/ · User Manual
```

## Commands

```bash
cd pi && bash install.sh                                    # install on the Pi
rfc2217-learn-slots                                         # discover USB slot keys
pytest pytest/ --wt-url http://workbench.local:8080         # bench tests (needs a live Pi)
ruff check . && mypy --strict .                             # neither is clean — see Harness → conventions
```

## Non-negotiables

- **Never SSH into the Pi to operate the bench.** Every operation has an HTTP endpoint; `pytest/workbench_driver.py` wraps them all. SSH is only for deploying code — see [AI-Workflow](docs/Harness/AI-Workflow.md#deploying-a-change-to-the-bench).
- **The service runs from `/usr/local/bin/`, not the git checkout.** Editing the repo on the Pi changes nothing until you copy and restart.
- **Always release GPIO pins after use**: `gpio_set(pin, "z")`. A pin left LOW stops the DUT booting.
- `SERIAL_PI=192.168.0.87` is set in the devcontainer.

## Host access

See the `remote-connections` skill for SSH, InfluxDB, Grafana, and Docker details.
