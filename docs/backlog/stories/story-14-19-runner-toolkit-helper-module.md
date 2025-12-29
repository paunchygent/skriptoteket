---
type: story
id: ST-14-19
title: "Runner: toolkit helper module for inputs/settings/actions"
status: ready
owners: "agents"
created: 2025-12-29
epic: "EPIC-14"
acceptance_criteria:
  - "Given a tool script runs in the runner, when it imports the toolkit module, then it can parse SKRIPTOTEKET_INPUTS, SKRIPTOTEKET_INPUT_MANIFEST, action.json, and memory.json settings via simple helpers."
  - "Given malformed env JSON, when helpers are used, then they fail safely and return predictable defaults (no crashes)."
  - "Given the toolkit exists, then it is documented and stable for tool authors."
dependencies:
  - "ST-14-03"
ui_impact: "No (runner-only)"
data_impact: "No"
---

## Notes

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
