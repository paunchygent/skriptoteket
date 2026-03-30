---
type: story
id: ST-29-09
title: "Klassrumskartan — Rule visibility and tool-feedback continuity"
status: in_progress
owners: "agents"
created: 2026-03-30
epic: "EPIC-29"
dependencies:
  - "ST-27-07"
  - "ST-29-01"
  - "ST-29-02"
  - "ST-29-05"
acceptance_criteria:
  - "Given the teacher works in `Sittplatser`, when active smart rules are already legible in the room canvas and `Regler`, then the seating toolbar does not repeat that state through a redundant active-rule count pill."
  - "Given the teacher opens `Redigera klassrum`, when they switch room-editor tools, then the tool palette exposes an explicit active-tool feedback surface that matches the stronger selection language already established in `Regler` instead of relying on button styling alone."
  - "Given active smart rules exist, when the teacher scans student bars in `Grupper` or `Sittplatser`, then the same rule markers appear directly on the student bars, and in `Grupper` those markers remain visible after a student has been assigned into a group card."
  - "Given browser proof is run at the `EPIC-29` `laptop` (`1366x768`) and `desktop` (`1440x900`) review viewports, when the slice is reviewed, then toolbar cleanup, room-editor tool feedback, and grouped-student rule-marker continuity all remain legible without reintroducing extra chrome."
ui_impact: "Yes (toolbar affordances, room-editor tool palette, grouping/seating student bars)"
data_impact: "No"
---

## Context

The current Klassrumskartan UI still has three small continuity breaks that make the tool feel less
trustworthy than it should:

- `Sittplatser` repeats active-rule state with a toolbar pill even though the room canvas and
  `Regler` already carry the more informative signal.
- the classroom editor tool palette does not give the same explicit active-tool feedback as the
  rules rail despite being a similarly tool-driven interaction surface.
- grouping loses smart-rule visibility once a student leaves the ungrouped pool and is assigned to
  a group card.

## Notes

- This is a UI continuity slice only; smart-rule contracts, persistence, and assignment behavior
  stay unchanged.
- The grouped-student marker work should reuse the existing smart-rule marker language rather than
  inventing a second summary format for group cards.
- The room-editor tool palette should follow the shared dense-tool control language from
  `ST-29-01`, not create a modal-only affordance dialect.

## Planned PR slices

- [PR-0177: ST-29-09 rule visibility and tool-feedback continuity](../prs/pr-0177-st-29-09-rule-visibility-and-tool-feedback-continuity.md)

## References

- Epic parent: [EPIC-29](../epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md)
- Rules-workspace baseline: [ST-27-07](story-27-07-klassrumskartan-rules-workspace-and-dual-map-authoring.md)
- Shared control-language baseline: [ST-29-01](story-29-01-klassrumskartan-canonical-operation-symbols-and-planner-control-primitives.md)
- Grouping/seating workspace baseline: [ST-29-05](story-29-05-klassrumskartan-grouping-and-seating-desktop-workspace-overhaul.md)
- Workspace doctrine: [REF-klassrumskartan-workspace-ui-doctrine-2026-03-28](../../reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md)
- Shared control matrix: [REF-shared-tool-control-language-v1](../../reference/ref-shared-tool-control-language-v1.md)
