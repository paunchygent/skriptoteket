---
type: story
id: ST-14-28
title: "Layout editor v1: UX polish + accessibility + tests"
status: ready
owners: "agents"
created: 2025-12-29
epic: "EPIC-14"
acceptance_criteria:
  - "Given keyboard-only usage, when editing assignments, then all layout editor operations are possible without drag/drop (focus order, enter/escape, clear actions)."
  - "Given a layout is large (e.g. 40–60 students), when rendering and editing, then interactions remain responsive (no obvious jank)."
  - "Given basic unit/component tests exist for interactive tool UI, when adding the layout editor, then it includes tests for click-to-assign and at least one drag/drop scenario."
  - "Given invalid layout_editor_v1 specs, when rendering, then the UI shows a clear error state without breaking the run view."
dependencies:
  - "ST-14-27"
ui_impact: "Yes"
data_impact: "No"
---

## Notes

Keep drag/drop as an enhancement; click/keyboard assignment remains the baseline supported path.

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
