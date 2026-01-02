---
type: story
id: ST-14-14
title: "Editor: schema editor snippets + inline diagnostics"
status: ready
owners: "agents"
created: 2025-12-29
epic: "EPIC-14"
acceptance_criteria:
  - "Given a tool author edits settings_schema/input_schema, when they click Prettify, then the JSON is formatted consistently (2-space indentation) and preserves semantics."
  - "Given the JSON schema editor is available, when the author requests an example snippet, then the editor inserts a minimal valid snippet for settings_schema and input_schema."
  - "Given a tool author inserts a file example snippet, then the editor does not hardcode server upload limits (e.g. UPLOAD_MAX_FILES). Authors decide tool-level file count limits (min/max), while the server remains the source of truth for overall upload constraints (bytes, max files)."
  - "Given the author changes the input preset/selection, then the snippets and guidance update to match the selected preset."
  - "Given schema issues are detected (parse errors), then the editor provides actionable messages close to the source of the error."
dependencies:
  - "ST-14-13"
  - "ST-14-09"
ui_impact: "Yes"
data_impact: "No"
---

## Notes

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
