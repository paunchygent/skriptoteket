---
type: story
id: ST-14-17
title: "Editor: version diff view (code + schemas + instructions)"
status: ready
owners: "agents"
created: 2025-12-29
epic: "EPIC-14"
acceptance_criteria:
  - "Given two visible tool versions, when a reviewer opens the diff view, then they can compare source_code, entrypoint, settings_schema, input_schema, and usage_instructions."
  - "Given the reviewer lacks access to a version, then they cannot diff it and the UI is explicit about the restriction."
  - "Given diffs are large, then the UI remains usable and allows copy/download of compared content."
dependencies:
  - "ADR-0027"
ui_impact: "Yes"
data_impact: "No (read-only view)"
---

## Notes

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
