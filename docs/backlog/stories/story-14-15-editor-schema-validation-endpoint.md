---
type: story
id: ST-14-15
title: "Editor: schema validation endpoint (settings_schema/input_schema)"
status: ready
owners: "agents"
created: 2025-12-29
epic: "EPIC-14"
acceptance_criteria:
  - "Given an author has draft schema JSON, when calling the validation endpoint, then the backend validates JSON shape, Pydantic parsing, and domain normalization rules."
  - "Given validation fails, then the response includes structured errors suitable for UI display (including field paths where possible)."
  - "Given validation succeeds, then the endpoint returns a success response without creating/updating versions."
dependencies:
  - "ST-14-04"
ui_impact: "Indirect (enables UI feedback)"
data_impact: "No (no persistence; new API only)"
---

## Notes

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
