# Project — Conventions

## Language and style

- Python 3.9+ on the Pi (the oldest supported target), 3.11 in the devcontainer.
  Do not use syntax newer than 3.9 in `pi/`.
- `snake_case` for functions and variables.
- Format and lint with `ruff`.

## API conventions

- All endpoints live under `/api/`.
- Every response is JSON carrying `"ok"`: `{"ok": true, ...}` or
  `{"ok": false, "error": "..."}`.
- `GET` takes query parameters; `POST` and `DELETE` take a JSON body; file
  transfers are `multipart/form-data`.
- Slot-addressed operations take `{"slot": "SLOT1"}` — the label, not an index.
- A new endpoint is not finished until it appears in **FSD Appendix D** and, if it
  is client-callable, in `mcp/workbench_mcp.py`'s `SPECS` table. The two udev
  callbacks (`/api/hotplug`, `/api/wifi/lease_event`) are deliberately absent from
  MCP — they fire on the Pi, not from a client.

## Verification commands

```bash
ruff check .
mypy --strict .
pytest pytest/ --wt-url http://workbench.local:8080
```

**Current state, stated honestly:** `ruff check .` reports 36 findings and
`mypy --strict pi/` reports 864 across 16 files. Neither is clean, so neither
gates a commit today. The standing rule is therefore *do not make it worse*:
a change must not add findings in the files it touches. Treat clean lint and
types as a debt to pay down, not a gate to pretend exists.

There is no ruff or mypy configuration file; both run on defaults.

## Commits

- Conventional-commit style prefixes (`docs:`, `fix(...):`, `portal:`).
- Never commit `tmp/`, `__pycache__/`, build output, or secrets.
- The `.mcpb` bundle is generated — rebuild it (`npx @anthropic-ai/mcpb pack .`)
  rather than hand-editing, and commit the rebuilt artifact when
  `mcp/workbench_mcp.py` changes.

## Skills

Skills under `.claude/skills/` are part of the product, not scratch notes. When an
endpoint's contract changes, update the skills that name it in the same change as
the FSD — a skill quoting a dead endpoint is a defect. The full skill list is in
`CLAUDE.md`; the FSD and Handbook describe what each drives.
