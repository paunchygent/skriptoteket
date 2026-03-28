---
type: story
id: ST-29-05
title: "Klassrumskartan — Grouping and seating desktop workspace overhaul"
status: ready
owners: "agents"
created: 2026-03-28
epic: "EPIC-29"
dependencies:
  - "ST-29-01"
  - "ST-29-02"
  - "ST-29-03"
  - "ST-24-03"
  - "ST-24-04"
acceptance_criteria:
  - "Given the teacher enters `Grupper`, when the redesigned desktop workspace renders, then the composition reads primarily as student pool plus group board, with chrome and summaries subordinate to the live grouping surface."
  - "Given the teacher enters `Sittplatser`, when the redesigned desktop workspace renders, then the composition reads primarily as student pool plus room canvas, with the room canvas clearly dominating the visual hierarchy."
  - "Given grouping or seating shows task-local summaries, setup context, or export state, when this slice ships, then those surfaces stay compact and local instead of consuming additional full-width bands above the main work area."
  - "Given browser proof is run at the `EPIC-29` `laptop` (`1366x768`) and `desktop` (`1440x900`) review viewports, when the slice is reviewed, then both workspaces remain orderly, dense, and legible without reverting to mobile-first card stacking."
ui_impact: "Yes (grouping and seating workspace layout and hierarchy)"
data_impact: "No"
---

## Context

Grouping and seating are where the current planner most clearly feels like a stack of UI sections
instead of one coherent instrument. This story applies the shared primitives to the two main
teacher workspaces.

## Notes

- This slice should preserve accepted planner logic and persistence behavior.
- The target is a denser desktop workspace, not a feature expansion.

## References

- Epic parent: [EPIC-29](../epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md)
- Grouping foundation: [ST-24-03](story-24-03-group-seating-studio-grouping-fundamentals-and-saved-groupings.md)
- Seating foundation: [ST-24-04](story-24-04-group-seating-studio-seating-fundamentals-and-saved-arrangements.md)
- Workspace doctrine: [REF-klassrumskartan-workspace-ui-doctrine-2026-03-28](../../reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md)
