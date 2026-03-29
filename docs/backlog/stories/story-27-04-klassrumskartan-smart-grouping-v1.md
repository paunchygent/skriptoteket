---
type: story
id: ST-27-04
title: "Klassrumskartan — Smart grouping v1"
status: ready
owners: "agents"
created: 2026-03-25
updated: 2026-03-29
epic: "EPIC-27"
dependencies: ["ST-27-01", "ST-27-02", "ST-27-06", "ST-27-07"]
acceptance_criteria:
  - "Given the teacher is in `Grupper` and `Smart` is `off`, when they use `Slumpa`, then grouping remains the current random reshuffle behavior."
  - "Given the teacher is in `Grupper` and `Smart` is `on`, when they use `Slumpa`, then the planner requests a backend-owned smart grouping result that reuses the same relation model as smart seating."
  - "Given the teacher reruns `Slumpa` in `Grupper` with `Smart` still `on`, when multiple good rule-respecting grouping candidates exist, then the backend prefers a materially different valid result over repeating the current assignment hash."
  - "Given the teacher authors `Keep apart` or `Keep near` in the shared `Regler` workspace, when they create one rule, then they can commit one visible cluster covering two or more students rather than being restricted to pair-only relations."
  - "Given one grouping `Keep near` cluster exists, when smart grouping runs, then it tries to keep those students in the same group whenever the current group structure and stronger rules allow it."
  - "Given one grouping `Keep apart` cluster exists, when smart grouping runs, then it tries to spread those students across different groups whenever possible and otherwise maximizes spread rather than failing hard."
  - "Given the teacher tries to place one student into multiple visible relationship clusters, when they attempt to commit the later grouping relation rule, then V1 blocks overlapping `Keep apart` / `Keep near` cluster membership."
  - "Given the teacher wants room-informed grouping, when the grouping smart surface is shown, then the seat-distance signal is controlled by one explicit toggle such as `Ska hur nära de sitter räknas?` rather than by a vague classroom-awareness label."
  - "Given `Närmare läraren` is a seating-only rule, when smart grouping runs, then grouping does not expose or consume that teacher-distance preference as though it were a shared cross-mode control."
  - "Given the explicit grouping seat-distance signal is enabled and an active seating draft exists for the same class, when smart grouping runs, then that live seating arrangement is consumed as a continuity input without treating the draft itself as history."
  - "Given the explicit grouping seat-distance signal is enabled but no active seating draft exists, when eligible seating checkpoints exist, then smart grouping may consume those checkpoints as fallback continuity input without treating them as grouping history."
  - "Given `Use history` is enabled, when smart grouping evaluates prior outcomes, then grouping history is label-insensitive and penalizes exact or near-repeat student co-memberships rather than raw group ids."
  - "Given `Use history` is enabled but no eligible grouping checkpoints exist for the requested grouping history inputs, when the teacher tries to run smart grouping, then the planner does not silently fall back to no-history behavior and instead blocks that history-enabled run with a short teacher-facing explanation."
ui_impact: "Yes (smart grouping toggle and seat-distance toggle)"
data_impact: "Yes (smart grouping request/response contract)"
---

## Context

Grouping should benefit from the same underlying relation model as seating, but the teacher needs a
clearer explanation than "classroom-aware." An explicit seat-distance question is easier to
understand and easier to turn off.

## Notes

- Keep the grouping smart flow separate from seating even when they share backend primitives.
- The seat-distance toggle is a mode-specific addition, not a new global planning panel.
- The class-wide visual authoring model is shared through `Regler`, but seating-only
  teacher-distance rules must not be presented as grouping inputs.
- `Use history` in grouping means grouping anti-repeat memory, not seating continuity.
- The explicit grouping seat-distance toggle is a separate live continuity lane:
  - active seating draft first when one exists for the same class
  - eligible seating checkpoints second when no active seating draft exists
  - this continuity lane outranks rerun-diversity pressure but does not override explicit
    `Keep apart` / `Keep near` rules
- Grouping should keep only compact smart summary/settings affordances in its own task pane:
  - the small settings affordance near `Smart` routes rule editing to `Regler`
  - do not introduce a grouping-local editing drawer or always-open rule panel
- Smart reruns should favor diversity among good candidates without becoming a teacher-facing
  randomness setting.
- `Keep apart` / `Keep near` are cluster rules for 2+ students in V1; overlapping visible
  relationship clusters are intentionally blocked rather than reconciled.
- Grouping history should be label-insensitive:
  - compare normalized student partitions and repeated student co-memberships
  - do not treat raw `group_id` or group-name matches as the real history identity
- Grouping should stay understandable even when no usable seating checkpoints exist.
- This story depends on `ST-27-06`; do not add smart grouping behavior on top of the old
  planner-wide flush/save-status/shared-timer contract.
- Grouping checkpoints are the primary grouping-history lane, while seating checkpoints remain a
  secondary fallback continuity source only when the explicit grouping seat-distance signal is on.
