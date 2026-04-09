---
type: story
id: ST-29-02
title: "Klassrumskartan — Workspace shell compression and low-value feedback band reduction"
status: done
owners: "agents"
created: 2026-03-28
updated: 2026-03-31
epic: "EPIC-29"
dependencies:
  - "ST-29-01"
acceptance_criteria:
  - "Given the teacher enters `Översikt`, `Grupper`, `Sittplatser`, or `Regler`, when the redesigned shell renders, then title, mode switch, compact context, status, and exit live inside one stable compressed shell rather than a large shell plus additional redundant full-width header cards."
  - "Given planner helper or status feedback is non-critical, when this slice ships, then it is expressed inline, locally, or through toast/inbox patterns instead of stacking a new page-wide band ahead of the work surface."
  - "Given teachers switch between workspaces, when the shell compression slice ships, then the mode switch, compact status area, and exit control remain in fixed locations that support muscle memory."
  - "Given browser proof is run at the `EPIC-29` `laptop` (`1366x768`) and `desktop` (`1440x900`) review viewports, when the slice is reviewed, then the teacher reaches the main workspace materially earlier with less vertical chrome."
ui_impact: "Yes (planner shell and status/help surfaces)"
data_impact: "No"
---

## Context

The current planner often reaches the real work surface too late because too many full-width framed
bands stack before the board, map, or canvas. This story reduces shell weight before deeper
workspace redesign begins.

## Notes

- This story is about shell compression and feedback placement, not about redesigning individual
  grouping, seating, or rules compositions yet.
- The slice should remove or merge low-value bands before adding any new visual treatment.

## Planned PR slices

- [PR-0161: ST-29-02 shared sticky workspace toolbar and transient feedback cutover](../prs/pr-0161-st-29-02-shared-sticky-workspace-toolbar-and-transient-feedback-cutover.md)
- [PR-0179: ST-29-02 follow-up sticky toolbar offset gap collapse](../prs/pr-0179-st-29-02-sticky-toolbar-offset-gap-collapse.md)
- [PR-0180: ST-29-02 follow-up sticky toolbar topbar gap collapse](../prs/pr-0180-st-29-02-sticky-toolbar-topbar-gap-collapse.md)
- [PR-0248: ST-29-02 follow-up: recovered export silence, rules rail stickiness, and overview copy cleanup](../prs/pr-0248-st-29-02-recovered-export-silence-rules-rail-stickiness-and-overview-copy-cleanup.md)

## References

- Epic parent: [EPIC-29](../epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md)
- Workspace doctrine: [REF-klassrumskartan-workspace-ui-doctrine-2026-03-28](../../reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md)
- Design-system rule: [045-huleedu-design-system](../../../.agents/rules/045-huleedu-design-system.md)
- Toast/system-message baseline: [EPIC-13](../epics/epic-13-toast-and-system-messages.md)
