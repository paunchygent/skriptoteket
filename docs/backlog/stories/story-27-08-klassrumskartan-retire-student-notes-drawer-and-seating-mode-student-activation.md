---
type: story
id: ST-27-08
title: "Klassrumskartan — Retire student notes drawer and seating-mode student activation"
status: done
owners: "agents"
created: 2026-04-01
updated: 2026-04-01
epic: "EPIC-27"
dependencies:
  - "ST-27-01"
  - "ST-27-06"
  - "ST-27-07"
acceptance_criteria:
  - "Given the teacher is in `Sittplatser`, when they click a seated or unplaced student token, then no drawer opens, no active student state is created, no selected styling appears, and no click-only feedback implies that anything happened."
  - "Given the teacher is working in `Sittplatser`, when they want to move a student, then drag/drop and the explicit remove action remain the only direct student interactions in that workspace."
  - "Given the teacher opens `Regler`, when they click students there, then rule-authoring click behavior remains scoped to `Regler` and is not reintroduced through `Sittplatser`."
  - "Given the planner frontend or backend hydrates, serializes, or patches draft workspace state, when the active contract is read or written, then student-notes metadata is absent from the SPA types, frontend store, draft persistence lane, API DTOs, and application/domain workspace models."
  - "Given draft persistence or bounded history is replayed after this slice ships, when the active repository contract is used, then no student-notes snapshot payload, repository mapping, or dedicated database table remains in the live planner contract."
  - "Given focused browser proof is run against `http://127.0.0.1:5173/apps/classroom.group-seating-studio`, when the teacher clicks students in `Sittplatser`, then nothing happens visually until they drag a student, drop a student, or explicitly remove one."
ui_impact: "Yes (remove seating drawer and seat-click activation semantics)"
data_impact: "Yes (remove draft-scoped student-notes contract and persistence)"
---

## Context

Klassrumskartan already moved the real smart-rule authoring flow into `Regler`, but one older
interaction seam is still present: in `Sittplatser`, clicking a student still routes through a
notes-drawer/active-student path that no longer matches the approved product model.

That leftover behavior creates two kinds of drift:

- the teacher can still trigger a hidden “something happened” interaction in a workspace that is
  now supposed to be calm and direct
- the codebase still carries `student_planning_meta` through frontend state, API contracts,
  repository snapshots, and database persistence even though the visible notes semantics were
  already superseded by the `Regler` workspace direction

This story removes the seam fully instead of merely hiding the drawer UI.

## Notes

- This is a hard removal slice, not a drawer-visibility tweak.
- In `Sittplatser`, student click should become a genuine no-op in both UX and code:
  - no active student
  - no selected styling
  - no hidden click handler chain that still mutates state
- `Regler` remains the only click-based student authoring surface in the planner.
- Do not replace the removed drawer with an inline popover, inspector panel, hover card, or
  secondary notes surface in this slice.
- Remove obsolete planner-note persistence without compatibility shims or migration-forward
  translation logic; there are still no real users to preserve here.

## Implementation Summary (as of 2026-04-01)

- `PR-0186` is implemented locally.
- `PlannerMetadataDrawer.vue` is deleted, `Sittplatser` student click no longer creates any active
  or selected state, and the seating lane now keeps only drag/drop plus explicit removal.
- The active draft workspace contract no longer carries `student_planning_meta` through frontend
  types/state, draft PATCH serialization, API DTOs, domain/application models, repository
  snapshots/history, or the live database schema.
- Migration `b7f9c2d4e1a6_drop_classroom_planner_student_notes.py` removes
  `classroom_planner_student_planning_meta` and strips the retired key from stored draft history
  payloads.

## Planned PR slices

- [PR-0186: ST-27-08 retire student notes drawer and seating-mode student activation](../prs/pr-0186-st-27-08-retire-student-notes-drawer-and-seating-mode-student-activation.md)

## References

- Epic parent: [EPIC-27](../epics/epic-27-klassrumskartan-smart-assignment-v1.md)
- Smart-assignment ADR: [ADR-0074](../../adr/adr-0074-klassrumskartan-smart-assignment-v1.md)
- Contract-reset baseline: [ST-27-01](story-27-01-klassrumskartan-smart-assignment-contract-reset-and-control-model.md)
- Session-lane baseline: [ST-27-06](story-27-06-klassrumskartan-planner-session-lanes-and-transition-matrix-remediation.md)
- Rules-workspace baseline: [ST-27-07](story-27-07-klassrumskartan-rules-workspace-and-dual-map-authoring.md)
