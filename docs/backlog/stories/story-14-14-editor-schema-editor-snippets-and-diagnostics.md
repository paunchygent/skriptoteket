---
type: story
id: ST-14-14
title: "Editor: schema editor snippets + inline diagnostics"
status: done
owners: "agents"
created: 2025-12-29
updated: 2026-01-03
epic: "EPIC-14"
acceptance_criteria:
  - "Given a tool author edits settings_schema/input_schema, when they click Prettify, then the JSON is formatted consistently (2-space indentation) and preserves semantics."
  - "Given the JSON schema editor is available, when the author requests an example snippet, then the editor inserts a minimal valid snippet for settings_schema and input_schema."
  - "Given a tool author inserts a file example snippet, then the editor does not hardcode server upload limits (e.g. UPLOAD_MAX_FILES). Authors decide tool-level file count limits (min/max), while the server remains the source of truth for overall upload constraints (bytes, max files)."
  - "Given the author changes the input preset/selection, then the snippets and guidance update to match the selected preset."
  - "Given schema issues are detected (JSON parse errors), then the editor provides actionable messages close to the source of the error (e.g. line/column) without performing semantic validation."
dependencies:
  - "ST-14-13"
  - "ST-14-09"
ui_impact: "Yes"
data_impact: "No"
---

## Notes

Scope: “inline diagnostics” here refers to JSON syntax/parse diagnostics. Backend-authoritative semantic validation and
structured error reporting is handled by ST-14-15/16.

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
