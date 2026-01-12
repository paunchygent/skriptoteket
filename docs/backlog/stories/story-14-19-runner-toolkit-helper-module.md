---
type: story
id: ST-14-19
title: "Runner: toolkit helper module for inputs/settings/actions"
status: in_progress
owners: "agents"
created: 2025-12-29
updated: 2026-01-12
epic: "EPIC-14"
acceptance_criteria:
  - "Given a tool script runs in the runner, when it imports the toolkit module, then it can parse SKRIPTOTEKET_INPUTS, SKRIPTOTEKET_INPUT_MANIFEST, SKRIPTOTEKET_ACTION, and memory.json settings via simple helpers."
  - "Given malformed env JSON, when helpers are used, then they fail safely and return predictable defaults (no crashes)."
  - "Given the toolkit exists, then it is documented and stable for tool authors."
  - "Given the toolkit will be referenced by editor intelligence and AI assistants, then the toolkit API surface is intentionally small and uses clear, stable names with concise docstrings and examples."
dependencies:
  - "ST-14-03"
ui_impact: "No (runner-only)"
data_impact: "No"
---

## Notes

AI alignment: a stable toolkit reduces prompt size and increases reliability for chat-based “create from scratch” and “fix this error” flows.

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`

Follow-up: migrate curated script bank tools to use the toolkit helpers (tracked in ST-14-33).
