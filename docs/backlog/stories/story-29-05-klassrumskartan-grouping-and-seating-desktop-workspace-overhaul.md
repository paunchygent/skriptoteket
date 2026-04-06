---
type: story
id: ST-29-05
title: "Klassrumskartan — Grouping and seating desktop workspace overhaul"
status: done
owners: "agents"
created: 2026-03-28
updated: 2026-04-06
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
  - "Given the teacher scrolls within `Grupper` or `Sittplatser` at the `laptop` or `desktop` review widths, when the workspace remains active, then the class-list/student-pool panel stays as a stable locally sticky side surface instead of dropping away like ordinary page content."
  - "Given grouping or seating shows task-local summaries, setup context, or export state, when this slice ships, then those surfaces stay compact and local instead of consuming additional full-width bands above the main work area."
  - "Given browser proof is run at the `EPIC-29` `laptop` (`1366x768`) and `desktop` (`1440x900`) review viewports, when the slice is reviewed, then both workspaces remain orderly, dense, and legible without reverting to mobile-first card stacking."
ui_impact: "Yes (grouping and seating workspace layout and hierarchy)"
data_impact: "No"
---

## Context

This story now records the current shipped grouping and seating workspace behavior. The live planner
already reads as desktop-first work surfaces rather than one long stacked page: grouping centers on
student pool plus group board, seating centers on student pool plus room canvas, and both surfaces
keep chrome, helper copy, and continuity affordances subordinate to the main work area.

## Notes

- This slice should preserve accepted planner logic and persistence behavior.
- The target is a denser desktop workspace, not a feature expansion.
- The shipped behavior spans several slices rather than one dedicated `ST-29-05` PR chain: the
  current split-pane/local-scroll structure comes from `ST-29-03`, the detached sticky compact
  shell comes from `ST-29-02`, and later feedback/visibility polish lands through `ST-29-09`.
- The class-list/student-pool panel is part of the shipped desktop composition contract, not an
  incidental implementation detail. If that rail loses local stickiness in grouping or seating,
  treat the issue as a regression against the current desktop workspace overhaul rather than as a
  new design direction.
- Remaining EPIC-29 work should not re-open grouping/seating composition as a new layout project.
  The follow-on lane is now shared site/app primitive tightening, canonical symbol completion, and
  discoverability governance.

## References

- Epic parent: [EPIC-29](../epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md)
- Grouping foundation: [ST-24-03](story-24-03-group-seating-studio-grouping-fundamentals-and-saved-groupings.md)
- Seating foundation: [ST-24-04](story-24-04-group-seating-studio-seating-fundamentals-and-saved-arrangements.md)
- Shared desktop composition baseline: [ST-29-03](story-29-03-klassrumskartan-shared-desktop-workspace-composition-primitives.md)
- Shell compression baseline: [ST-29-02](story-29-02-klassrumskartan-workspace-shell-compression-and-low-value-feedback-band-reduction.md)
- Rule/feedback continuity follow-on: [ST-29-09](story-29-09-klassrumskartan-rule-visibility-and-tool-feedback-continuity.md)
- Workspace doctrine: [REF-klassrumskartan-workspace-ui-doctrine-2026-03-28](../../reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md)
