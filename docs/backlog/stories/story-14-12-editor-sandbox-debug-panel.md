---
type: story
id: ST-14-12
title: "Editor: sandbox debug panel UX (copyable diagnostics)"
status: ready
owners: "agents"
created: 2025-12-29
updated: 2026-01-01
epic: "EPIC-14"
acceptance_criteria:
  - "Given a sandbox run has debug details available, when viewing sandbox results in the editor, then the user can expand a Debug panel showing stdout/stderr."
  - "Given the Debug panel is shown, then the user can copy stdout/stderr and identifiers (run_id, snapshot_id) for support/debugging."
  - "Given debug details are not available due to permissions, then the Debug panel is hidden or shows a clear access message."
  - "Given the Debug panel is shown, when the user clicks Copy debug bundle, then the UI copies a single, stable text bundle (ids + truncation flags + stdout/stderr) suitable for pasting into support or an AI assistant."
dependencies:
  - "ST-14-11"
ui_impact: "Yes (SandboxRunner)"
data_impact: "No"
---

## Notes

AI alignment: provide a single “copy bundle” action so future chat UX can attach sandbox diagnostics without re-inventing formatting.

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
