# Universal Embedded Workbench

Raspberry Pi test instrument for ESP32 firmware — serial proxy, WiFi, BLE, MQTT, GPIO, RF, SDR and GDB debug behind one REST API on `:8080`.

This file is assistant configuration, not project documentation. It states no rules of its own: everything below is a pointer, except the two repo hazards at the end, which are recorded nowhere else.

## Start here

**Read [`docs/Harness/AI-Workflow.md`](docs/Harness/AI-Workflow.md) before making any change.** It is the build contract — how to find the rule a change serves, how to verify it, and how to keep the documentation in sync.

## The three planes

| Plane | Question | Document |
|-------|----------|----------|
| **WHAT** | What must be true of the bench? | [`docs/Embedded-Workbench-FSD.md`](docs/Embedded-Workbench-FSD.md) — **Appendix D** is the full HTTP API and MCP tool reference |
| **HOW** | How is it built and changed? | [`docs/Harness/`](docs/Harness/) |
| **OPERATE** | How do I run it? | [`docs/Embedded-Workbench-User-Manual.md`](docs/Embedded-Workbench-User-Manual.md) — install, commands, environment |

Route every sentence to exactly one plane, and link rather than restate. The routing rule and its edge cases are in [`docs/Harness/standards/documentation.md`](docs/Harness/standards/documentation.md).

`README.md` is the GitHub landing page only.

## Layout

```
pi/            Portal + one controller module per instrument
pytest/        WorkbenchDriver, host tier, and the bench suite
mcp/           MCP server + Claude Desktop .mcpb
test-firmware/ ESP-IDF firmware that exercises the whole bench
.claude/       skills/ + agents/
docs/          FSD · Harness/ · User Manual
```

Commands, install steps and environment variables are in the User Manual. Module boundaries and dependency rules are in [`docs/Harness/project/architecture.md`](docs/Harness/project/architecture.md).

## Two hazards recorded nowhere else

- **`gplug-mini/` is a separate git repository nested in this one**, and shows as untracked here. Add explicit paths when committing — `git add -A` would swallow it.
- **Host access** — SSH, InfluxDB, Grafana and Docker details are in the `remote-connections` skill.
