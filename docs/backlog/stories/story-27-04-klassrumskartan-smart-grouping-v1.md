---
type: story
id: ST-27-04
title: "Klassrumskartan — Smart grouping v1"
status: ready
owners: "agents"
created: 2026-03-25
updated: 2026-03-30
epic: "EPIC-27"
dependencies: ["ST-27-01", "ST-27-02", "ST-27-06", "ST-27-07"]
acceptance_criteria:
  - "Given the teacher is in `Grupper` and `Smart` is `off`, when they use `Slumpa`, then grouping remains the current random reshuffle behavior."
  - "Given the teacher is in `Grupper` and `Smart` is `on`, when they use `Slumpa`, then the planner requests a backend-owned smart grouping result that reuses the same relation model as smart seating."
  - "Given the grouping toolbar renders, when active smart rules are already visible through `Regler` and student markers, then no separate active-rule count pill is shown in `Grupper`."
  - "Given the teacher reruns `Slumpa` in `Grupper` with `Smart` still `on`, when multiple good rule-respecting grouping candidates exist, then the backend prefers a materially different valid result over repeating the current assignment hash."
  - "Given the teacher authors `Keep apart` or `Keep near` in the shared `Regler` workspace, when they create one rule, then they can commit one visible cluster covering two or more students rather than being restricted to pair-only relations."
  - "Given one grouping `Keep near` cluster exists, when smart grouping runs, then it tries to keep those students in the same group whenever the current group structure and stronger rules allow it."
  - "Given one grouping `Keep apart` cluster exists, when smart grouping runs, then it tries to spread those students across different groups whenever possible and otherwise maximizes spread rather than failing hard."
  - "Given the teacher tries to place one student into multiple visible relationship clusters, when they attempt to commit the later grouping relation rule, then V1 blocks overlapping `Keep apart` / `Keep near` cluster membership."
  - "Given the teacher wants room-informed grouping, when the grouping smart surface is shown, then classroom-aware grouping is controlled through the classroom control itself rather than by history or a separate free-floating generic toggle."
  - "Given `Närmare läraren` is a seating-only rule, when smart grouping runs, then grouping does not expose or consume that teacher-distance preference as though it were a shared cross-mode control."
  - "Given classroom-aware grouping is enabled and an active seating draft exists for the same class, when smart grouping runs, then it uses seat-topology distance to prefer spatially compact groups and penalizes same-group spread quadratically beyond a local elastic radius without treating that seating input as history."
  - "Given classroom-aware grouping is enabled but no active seating draft exists, when eligible seating checkpoints exist, then smart grouping may consume those checkpoints as fallback compactness input without treating them as grouping history."
  - "Given classroom-aware grouping is enabled but no usable seating context exists, when smart grouping runs, then the planner falls back honestly to rules plus any enabled history lane and tells the teacher that no seating-based classroom signal was available for that run."
  - "Given `Use history` is enabled, when smart grouping evaluates prior outcomes, then grouping history only handles anti-repeat rotation, stays label-insensitive, and penalizes exact or near-repeat student co-memberships rather than raw group ids."
  - "Given `Use history` is enabled but no eligible grouping checkpoints exist for the requested grouping history inputs, when the teacher tries to run smart grouping, then the planner does not silently fall back to no-history behavior and instead blocks that history-enabled run with a short teacher-facing explanation."
ui_impact: "Yes (smart grouping toggle, classroom-aware grouping control semantics, and history)"
data_impact: "Yes (smart grouping request/response contract)"
---

## Context

Grouping should benefit from the same underlying relation model as seating, but the teacher also
needs three lanes to stay honest:

- `Smart` decides backend smart grouping vs local random
- classroom-aware grouping is a separate compactness lane tied to the classroom control
- `Use history` handles grouping anti-repeat rotation only

## Notes

- Keep the grouping smart flow separate from seating even when they share backend primitives.
- The classroom control owns classroom-aware grouping state:
  - it must not be hidden inside `Use history`
  - it should not require a second generic smart toggle if the classroom selector or a composite
    selector/toggle control can communicate the state more clearly
- The class-wide visual authoring model is shared through `Regler`, but seating-only
  teacher-distance rules must not be presented as grouping inputs.
- `Use history` in grouping means grouping anti-repeat memory only, not seating continuity or
  classroom awareness.
- Classroom-aware grouping is a separate compactness lane:
  - active seating draft first when one exists for the same class
  - eligible seating checkpoints second when no active seating draft exists
  - it uses seat-topology distance rather than raw pixel distance
  - same-group spread is penalized quadratically beyond a local elastic radius
  - this compactness lane outranks rerun-diversity pressure but does not override explicit
    `Keep apart` / `Keep near` rules
  - if no usable seating context exists, the run should say so honestly instead of pretending the
    classroom-aware lane was applied
- Grouping should keep only compact smart summary/settings affordances in its own task pane:
  - the small settings affordance near `Smart` routes rule editing to `Regler`
  - do not introduce a grouping-local editing drawer or always-open rule panel
- Grouping should not show a redundant active-rule count pill in the toolbar when the richer rule
  surfaces already communicate the same information.
- Smart reruns should favor diversity among good candidates without becoming a teacher-facing
  randomness setting.
- `Keep apart` / `Keep near` are cluster rules for 2+ students in V1; overlapping visible
  relationship clusters are intentionally blocked rather than reconciled.
- Grouping history should be label-insensitive:
  - compare normalized student partitions and repeated student co-memberships
  - do not treat raw `group_id` or group-name matches as the real history identity
- Grouping should stay understandable even when no usable seating context exists.
- The exact elastic radius and compactness weight curve should stay intentionally tunable during
  implementation through simulations and review of outcomes against the desired classroom behavior.
- This story depends on `ST-27-06`; do not add smart grouping behavior on top of the old
  planner-wide flush/save-status/shared-timer contract.
- Grouping checkpoints are the primary grouping-history lane, while seating checkpoints remain a
  secondary fallback compactness source only when classroom-aware grouping is enabled through the
  classroom control.
