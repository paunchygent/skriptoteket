---
type: story
id: ST-14-27
title: "Layout editor v1: drag/drop interactions (library-based)"
status: ready
owners: "agents"
created: 2025-12-29
epic: "EPIC-14"
acceptance_criteria:
  - "Given the layout editor renders student 'chips' and slots, when a user drags a student onto an empty slot, then the UI assigns the student locally and marks unsaved changes."
  - "Given a slot is occupied, when dragging a different student onto it, then the UI supports a swap (or a clear, documented behavior) without losing either student."
  - "Given a user cancels a drag, when dropping outside valid targets, then no assignment changes occur."
  - "Given touch input, when dragging, then the interaction works on mobile/touch devices or the UI clearly encourages click-to-assign instead."
dependencies:
  - "ST-14-26"
ui_impact: "Yes (layout editor interactions)"
data_impact: "No"
---

## Notes

Use a well-known drag/drop library to avoid reinventing DnD edge cases and improve cross-browser behavior.

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
