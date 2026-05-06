---
type: pr
id: PR-0304
title: "ST-27-09: seating workspace fixed-seat lock marker"
status: done
owners: "agents"
created: 2026-05-06
updated: 2026-05-06
stories:
  - "ST-27-09"
tags: ["frontend", "ux", "smart-assignment", "klassrumskartan", "seating-workspace"]
dependencies:
  - "PR-0297"
  - "PR-0298"
acceptance_criteria:
  - "Given a fixed-seat rule exists for the active classroom template and Smart seating places the fixed student in that exact seat, when `Sittplatser` renders the normal room canvas, then that occupied seat shows the fixed-seat lock marker and accessible title without hiding the normal student name, seat label, drag affordance, or remove affordance."
  - "Given a fixed-seat rule exists but the fixed student is not currently sitting in the fixed seat, when `Sittplatser` renders the normal room canvas, then the lock marker is not shown on that seat or on the wrong occupant."
  - "Given fixed-seat rules exist for another classroom template, when `Sittplatser` renders the active classroom, then those rules do not create lock markers or `Fast plats` student markers in the active seating workspace."
  - "Given ordinary smart-rule labels such as `Nära läraren`, `Håll isär`, and `Håll nära` are shown in the seating workspace, when a fixed-seat rule applies to the same active student, then the compact `Fast plats` marker participates in the same marker pipeline."
---

## Problem

`PR-0298` added explicit fixed-seat lock feedback in the `Regler` classroom map, but the normal
`Sittplatser` room canvas still treats a student placed by Smart seating like any other occupied
seat. Teachers therefore lose the visual proof that a hard `Fast plats` invariant was honored at
the moment they review the generated seating schema.

The missing marker is especially risky because the fixed-seat rule is a hard rule, not a soft
preference. Showing the lock on the wrong occupied seat would be just as misleading as omitting it,
so the seating workspace must only render the lock when the fixed student is actually sitting in the
fixed seat for the active classroom template.

## Goal

Show fixed-seat rule state in the normal `Sittplatser` canvas without changing the authoring model:

- filter fixed-seat rules to the active classroom template
- pass active fixed-seat rules through the seating workspace and room canvas
- render the lock marker on `SeatNode` only when the fixed rule's student occupies the fixed rule's
  seat
- keep the shared compact `Fast plats` student marker aligned with the existing smart-rule marker
  pipeline

## Non-goals

- No solver, persistence, or API contract changes.
- No new rule authoring controls.
- No warning state for currently violated fixed-seat rules; this slice only avoids misleading
  positive lock markers.
- No redesign of the room token, drag/drop, or remove-button interactions.

## Implementation plan

1. Derive active-template fixed-seat rules in `PlannerSeatingWorkspacePane.vue`.
2. Pass active fixed-seat rules to both `buildSmartRuleMarkersByStudentId` and `RoomCanvas`.
3. Teach `RoomCanvas.vue` to match fixed-seat rules by `seat_id` and current occupant.
4. Add a small lock overlay to `SeatNode.vue`, reusing the existing `IconLock` treatment from the
   rules map.
5. Add focused Vitest coverage for matching, non-matching, and wrong-template cases.

## Test plan

- `pdm run fe-test -- --run RoomCanvas PlannerSeatingWorkspacePane.smart-rules`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `git diff --check`

## Implementation summary

Implemented on 2026-05-06.

- `PlannerSeatingWorkspacePane.vue` now filters fixed-seat rules to the active classroom template
  and passes that active rule set to both the smart-rule marker helper and the normal seating
  `RoomCanvas`.
- `RoomCanvas.vue` now matches fixed-seat rules by seat and current occupant before producing an
  accessible lock title. A lock is emitted only when the fixed rule's student is actually sitting
  in the fixed rule's seat.
- `SeatNode.vue` now renders the existing `IconLock` marker over honored fixed-seat placements
  without changing the student token, drag/drop behavior, or remove button.
- Focused tests prove the honored-placement lock, wrong-occupant suppression, active-template
  filtering, and compact `Fast plats` marker pipeline.

## Verification

- `pdm run fe-test -- --run RoomCanvas PlannerSeatingWorkspacePane.smart-rules`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `git diff --check`

## Rollback plan

Revert the seating-workspace lock marker plumbing. The existing fixed-seat rule authoring,
persistence, and solver behavior from `PR-0297`/`PR-0298` remains valid; only the normal seating
canvas loses the extra visual confirmation until the marker can be corrected.
