---
type: story
id: ST-14-10
title: "Editor: schema JSON QoL (prettify + examples + guidance)"
status: ready
owners: "agents"
created: 2025-12-29
epic: "EPIC-14"
acceptance_criteria:
  - "Given a tool author edits settings_schema/input_schema, when they click Prettify, then the JSON is formatted consistently (2-space indentation) and preserves semantics."
  - "Given a tool author edits settings_schema/input_schema, when they click Insert example, then the editor inserts a minimal valid example for the current mode and explains how to adapt it."
  - "Given schemas are invalid JSON, when the author attempts to save or run sandbox, then the editor shows actionable errors and blocks the operation."
dependencies:
  - "ADR-0027"
ui_impact: "Yes (tool editor schema panel)"
data_impact: "No"
---

## Notes

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
