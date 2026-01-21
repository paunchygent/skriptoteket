---
type: story
id: ST-19-01
title: "Runner request envelope: /work/request.json (replace env payloads)"
status: ready
owners: "agents"
created: 2026-01-20
epic: "EPIC-19"
acceptance_criteria:
  - "Given a runner-based tool run (initial or action), when the container starts, then the tool can read a single `/work/request.json` containing inputs, action payload (if any, including server-owned session state), and a file manifest."
  - "Given `/work/request.json` exists, when a tool uses `skriptoteket_toolkit`, then it can read inputs/action/manifest without reading any `SKRIPTOTEKET_*` env vars."
  - "Given the platform is upgraded, then the backend no longer sets `SKRIPTOTEKET_INPUTS`, `SKRIPTOTEKET_INPUT_MANIFEST`, or `SKRIPTOTEKET_ACTION` for runner containers."
  - "Given the platform upgrade is complete, then the script bank and starter templates are updated and no in-repo scripts depend on the removed env vars."
dependencies:
  - "ADR-0024"
  - "ST-14-19"
  - "ADR-0063"
ui_impact: "No"
data_impact: "No"
---

## Context

Today the platform injects JSON payloads via environment variables:

- initial run inputs: `SKRIPTOTEKET_INPUTS`
- input file metadata: `SKRIPTOTEKET_INPUT_MANIFEST`
- action runs: `SKRIPTOTEKET_ACTION`

This is workable but fragile (size limits, encoding/quoting issues) and makes it hard to evolve the runtime payload
shape coherently (e.g., file references).

## Notes

- This story is explicitly **breaking** by design (no migration path). Runner/app/tool scripts are upgraded together.
- `memory.json` remains the settings transport for now (`SKRIPTOTEKET_MEMORY_PATH`), since it is already file-based
  and stable.

## Proposed request schema (v1)

Write `/work/request.json` (UTF-8 JSON) containing at minimum:

- `schema_version: 1`
- `inputs: { values: {...} }`
- `action: { action_id: str, input: {...}, state: {...} } | null`
- `files: [{ name, path, bytes, ref? }]` (the canonical file manifest; `ref` is introduced in ST-19-02)

## Implementation plan

1) Runner/container I/O

- Inject `request.json` into `/work/` alongside `script.py` and `memory.json`.
- Stop setting env vars for `inputs/action/manifest` in the Docker runner.

2) Runner toolkit

- Update `runner/skriptoteket_toolkit.py` so the public helpers read from `/work/request.json`.
- Keep predictable defaults (missing/malformed JSON must not crash tools; return `{}` / `None`).

3) Script bank + templates

- Update all in-repo scripts + starter templates to stop reading env vars and use the toolkit.

## Test plan

- Unit: toolkit parsing on missing/invalid request.json.
- Integration: docker runner injects `request.json` and tools can read inputs/action/manifest.
