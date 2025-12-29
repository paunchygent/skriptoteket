---
type: story
id: ST-14-12
title: "Editor: sandbox debug panel UX (copyable diagnostics)"
status: ready
owners: "agents"
created: 2025-12-29
epic: "EPIC-14"
acceptance_criteria:
  - "Given a sandbox run has debug details available, when viewing sandbox results in the editor, then the user can expand a Debug panel showing stdout/stderr."
  - "Given the Debug panel is shown, then the user can copy stdout/stderr and identifiers (run_id, snapshot_id) for support/debugging."
  - "Given debug details are not available due to permissions, then the Debug panel is hidden or shows a clear access message."
dependencies:
  - "ST-14-11"
ui_impact: "Yes (SandboxRunner)"
data_impact: "No"
---

## Notes

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
