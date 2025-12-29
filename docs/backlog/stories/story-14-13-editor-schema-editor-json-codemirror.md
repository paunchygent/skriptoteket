---
type: story
id: ST-14-13
title: "Editor: CodeMirror JSON editor for tool schemas"
status: ready
owners: "agents"
created: 2025-12-29
epic: "EPIC-14"
acceptance_criteria:
  - "Given a tool author edits settings_schema/input_schema, when using the editor, then schemas are edited in a JSON-aware CodeMirror surface with syntax highlighting."
  - "Given the schema JSON is invalid, when edited, then the editor shows inline syntax errors without crashing."
  - "Given a schema is valid, when running sandbox preview, then the unsaved schema is used (snapshot preview parity)."
dependencies:
  - "ADR-0027"
ui_impact: "Yes (tool editor schema panel)"
data_impact: "No"
---

## Notes

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
