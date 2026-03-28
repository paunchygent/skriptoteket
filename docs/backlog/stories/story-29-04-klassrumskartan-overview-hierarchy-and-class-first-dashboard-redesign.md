---
type: story
id: ST-29-04
title: "Klassrumskartan — Overview hierarchy and class-first dashboard redesign"
status: ready
owners: "agents"
created: 2026-03-28
epic: "EPIC-29"
dependencies:
  - "ST-29-01"
  - "ST-29-02"
  - "ST-24-07"
acceptance_criteria:
  - "Given the teacher lands in `Översikt`, when the redesigned dashboard renders, then active class work and resume actions are primary while classroom management reads as secondary supporting context."
  - "Given the overview class preview exceeds its fixed desktop height, when the slice ships, then the roster preview scrolls internally without breaking the aligned overview geometry or forcing card growth."
  - "Given resume surfaces remain in the overview, when the slice ships, then they read as deliberate dashboard actions rather than as equal-weight cards competing with class and classroom management."
  - "Given create, continue, edit, and delete actions render in overview, when scanned at a glance, then their primary, secondary, and destructive hierarchy is obvious and consistent with the shared symbol/control system."
  - "Given browser proof is run at the `EPIC-29` `laptop` (`1366x768`) and `desktop` (`1440x900`) review viewports, when the overview redesign is reviewed, then it preserves the class-first direction without collapsing back into mobile-first stacked-card symmetry."
ui_impact: "Yes (overview layout, hierarchy, and affordances)"
data_impact: "No"
---

## Context

The overview currently works, but its hierarchy is still too card-heavy and too even in visual
weight. This story turns it into a real desktop dashboard aligned with the planner doctrine.

## Notes

- This is not a workflow-direction change; class-first remains the accepted product anchor.
- This story absorbs the overview hierarchy and fixed-preview overflow scope from the older
  export-era redesign drafts and is now the only canonical planning surface for that work.

## References

- Epic parent: [EPIC-29](../epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md)
- Overview-first baseline: [ST-24-07](story-24-07-group-seating-studio-overview-first-workspace-management.md)
- Related task slice: [PR-0127](../prs/pr-0127-klassrumskartan-overview-roster-preview-overflow-and-fixed-height-scrolling.md)
- Related task slice: [PR-0131](../prs/pr-0131-klassrumskartan-overview-button-hierarchy-and-destructive-action-de-emphasis.md)
- Related task slice: [PR-0132](../prs/pr-0132-klassrumskartan-resume-history-affordance-normalization-and-planner-control-polish.md)
- Workspace doctrine: [REF-klassrumskartan-workspace-ui-doctrine-2026-03-28](../../reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md)
