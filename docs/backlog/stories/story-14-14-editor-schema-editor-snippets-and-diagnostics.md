---
type: story
id: ST-14-14
title: "Editor: schema editor snippets + inline diagnostics"
status: ready
owners: "agents"
created: 2025-12-29
epic: "EPIC-14"
acceptance_criteria:
  - "Given the JSON schema editor is available, when the author requests an example snippet, then the editor inserts a minimal valid snippet for settings_schema and input_schema."
  - "Given the author changes the input mode, then the snippets and guidance update to match the selected mode."
  - "Given schema issues are detected (parse errors), then the editor provides actionable messages close to the source of the error."
dependencies:
  - "ST-14-13"
ui_impact: "Yes"
data_impact: "No"
---

## Notes

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
