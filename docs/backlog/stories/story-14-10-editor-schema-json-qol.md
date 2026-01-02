---
type: story
id: ST-14-10
title: "Editor: schema JSON guardrails (shared parsing + save blocking)"
status: done
owners: "agents"
created: 2025-12-29
epic: "EPIC-14"
acceptance_criteria:
  - "Given a tool author edits settings_schema/input_schema, schema parsing/validation uses a shared helper (no duplication drift vs save logic)."
  - "Given schemas are invalid JSON or not a JSON array, when the author attempts to save, then the editor shows actionable errors and blocks the operation."
  - "Given settings_schema is blank/whitespace, then it is treated as null; given input_schema is blank/whitespace, then it is treated as []."
dependencies:
  - "ADR-0027"
ui_impact: "Yes (tool editor schema panel)"
data_impact: "No"
---

## Notes

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`

Deferred to ST-14-14/15/16:

- Schema editor UI actions (Prettify / Insert example / preset selector)
- Structured schema validation endpoint + UX
