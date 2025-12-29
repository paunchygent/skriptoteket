---
type: story
id: ST-14-26
title: "UI renderer: layout editor v1 (click-to-assign + apply)"
status: ready
owners: "agents"
created: 2025-12-29
epic: "EPIC-14"
acceptance_criteria:
  - "Given a run returns a layout_editor_v1 output, when the UI renders it, then it shows a room, desk groups/rows, and student slots with current assignments."
  - "Given the layout_editor_v1 output includes a palette and prefabs, when the user enters placement/edit mode, then they can place room objects/furniture or prefabs into valid grid/edge positions with snapping and without overlap."
  - "Given the user moves or deletes placed objects, when editing, then the UI enforces swap-by-convention (same swap_group) or rejects invalid placements (no stacking)."
  - "Given a user selects a slot, when choosing a student (or unassign), then the UI updates the local layout state and marks it as 'unsaved changes'."
  - "Given a user applies changes, when the UI submits an action back to the tool, then the tool receives the updated layout payload and the UI re-renders based on the tool's returned output/state."
  - "Given a user does not use a mouse, when editing, then they can complete the flow via keyboard-only controls (click-to-assign path)."
dependencies:
  - "ST-14-25"
ui_impact: "Yes (new interactive output component)"
data_impact: "No"
---

## Context

We want a “layout editor” that enables seating-style planning and fine-tuning while keeping the platform security posture
intact (platform-rendered UI, no tool-provided JS).

## Goal

Ship a minimal, keyboard-accessible layout editor renderer with click-to-assign editing and a batch “apply changes” action
back to the tool.

## Notes

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
