---
type: story
id: ST-29-03
title: "Klassrumskartan — Shared desktop workspace composition primitives"
status: ready
owners: "agents"
created: 2026-03-28
epic: "EPIC-29"
dependencies:
  - "ST-29-01"
  - "ST-29-02"
acceptance_criteria:
  - "Given grouping and seating render at the `EPIC-29` `laptop` (`1366x768`) review viewport, when the shared desktop-composition slice ships, then selectors/context, undo/redo, primary workflow controls, and secondary/overflow actions remain in stable zones rather than drifting through wrap order."
  - "Given student pools or secondary panes overflow vertically in grouping or seating, when the slice ships, then they behave as true local scroll regions with fixed local headers while the main board or canvas remains visible."
  - "Given later workspace redesign stories build on the planner, when they reuse shared layout primitives, then they do not need to recreate toolbar zoning, split-pane framing, or local-scroll seams ad hoc."
  - "Given browser proof is run at the `EPIC-29` `laptop` (`1366x768`) and `desktop` (`1440x900`) review viewports, when the slice is reviewed, then the shared workspace primitives hold stable before any tablet or phone cutover begins."
ui_impact: "Yes (shared action-zoning, split-pane, and local-scroll layout primitives)"
data_impact: "No"
---

## Context

The redesign should not jump straight from doctrine to full workspace restyling. This story creates
the shared desktop composition seams that later workspace-specific slices can rely on.

## Notes

- This story absorbs the grouping/seating scroll-region and action-zoning execution scope from the
  older export-era redesign drafts and is now the only canonical planning surface for that work.
- The goal is reusable desktop composition discipline, not visual polish in isolation.

## References

- Epic parent: [EPIC-29](../epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md)
- Related task slice: [PR-0128](../prs/pr-0128-klassrumskartan-grouping-and-seating-student-pool-split-pane-scrolling.md)
- Related task slice: [PR-0129](../prs/pr-0129-klassrumskartan-shared-planner-action-bar-zoning-and-grouping-toolbar-stabilization.md)
- Related task slice: [PR-0130](../prs/pr-0130-klassrumskartan-seating-toolbar-stabilization-export-cluster-alignment-and-responsive-proof.md)
- Planner shell decomposition: [PR-0114](../prs/pr-0114-klassrumskartan-planner-shell-decomposition-and-shared-ui-primitives.md)
- Workspace doctrine: [REF-klassrumskartan-workspace-ui-doctrine-2026-03-28](../../reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md)
