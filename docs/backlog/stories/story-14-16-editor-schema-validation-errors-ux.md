---
type: story
id: ST-14-16
title: "Editor: structured schema validation errors UX"
status: ready
owners: "agents"
created: 2025-12-29
updated: 2026-01-03
epic: "EPIC-14"
acceptance_criteria:
  - "Given the validation endpoint reports structured errors, when viewing schemas in the editor, then the UI renders them in a user-actionable format (what/where/how to fix)."
  - "Given the schema JSON is parseable but fails backend validation, when attempting to save or run sandbox, then the editor blocks the action and points to the validation errors."
  - "Given validation is expensive, then the UI throttles calls (no per-keystroke spam)."
dependencies:
  - "ST-14-15"
ui_impact: "Yes"
data_impact: "No"
---

## Notes

Scope: ST-14-16 covers backend validation errors for parseable JSON. JSON parse errors are handled by the schema editor
(ST-14-13/14) and should block actions without calling the validation endpoint.

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
