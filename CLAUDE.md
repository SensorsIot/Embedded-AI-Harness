# The Harness

AI Closed-Loop Programming for embedded systems: the AI develops firmware
against tests derived from the FSD, on real hardware, until they run clean.
This repo holds the method skills (`/define` · `/harness` · `/commission` ·
`/build`), the workbench (a Raspberry Pi test instrument behind one REST API
on `:8080`), and the three documentation planes.

This file is assistant configuration, not project documentation. It states no
rules of its own: everything below is a pointer, except the one repo hazard at
the end, which is recorded nowhere else.

## Start here

**Read [`docs/Method/AI-Workflow.md`](docs/Method/AI-Workflow.md) before making
any change.** It is the build contract — how to find the rule a change serves,
how to verify it, and how to keep the documentation in sync.

The plane map — WHAT / HOW / OPERATE, one document per question — is
[`docs/00-Overview.md`](docs/00-Overview.md). Route every sentence to exactly
one plane, and link rather than restate; the routing rule and its edge cases
are in [`docs/Method/standards/documentation.md`](docs/Method/standards/documentation.md).

`README.md` is the GitHub landing page only.

## Layout

```
pi/            Portal + one controller module per instrument
pytest/        WorkbenchDriver, host tier, and the bench suite
mcp/           MCP server + Claude Desktop .mcpb
test-firmware/ ESP-IDF firmware that exercises the whole bench
.claude/       skills/ (method + instruments) + agents/
docs/          00-Overview · FSD · Method/ · User Manual
```

Commands, install steps and environment variables are in the User Manual.
Module boundaries and dependency rules are in
[`docs/Method/project/architecture.md`](docs/Method/project/architecture.md).

## One hazard recorded nowhere else

- **Host access** — SSH, InfluxDB, Grafana and Docker details are in the
  `remote-connections` skill.

(`gplug-mini/` used to sit here as a nested second git repository, which is why
`git add -A` was banned. It moved to its own container on 2026-08-05 and the
directory is gone, so that hazard no longer applies.)
