---
type: pr
id: PR-0186
title: "Klassrumskartan: retire student notes drawer and seating-mode student activation"
status: done
owners: "agents"
created: 2026-04-01
updated: 2026-04-01
stories:
  - "ST-27-08"
tags: ["frontend", "backend", "klassrumskartan", "cleanup", "rules"]
acceptance_criteria:
  - "The remaining `PlannerMetadataDrawer` surface is removed from the active planner shell, and `Sittplatser` no longer tracks or renders any selected/active student click state."
  - "Seating student interactions remain limited to drag/drop and explicit removal, while `Regler` retains its own click-based rule-authoring behavior."
  - "The active draft workspace contract no longer includes `student_planning_meta` in frontend types, store serialization, API DTOs, application/domain models, repository snapshots, or database persistence."
  - "Focused automated tests plus browser proof confirm that clicking students in `Sittplatser` produces no visible effect and that drag/drop behavior still works."
---

## Problem

The remaining student-notes drawer in Klassrumskartan is now a superseded interaction path. It
keeps outdated per-student click activation alive inside `Sittplatser` and forces the planner to
carry `student_planning_meta` through the frontend, API, repository, and database layers even
though the approved smart-rule model has moved to `Regler`.

## Goal

Remove the notes drawer and all seating-mode student activation semantics so the codebase matches
the current product truth:

- `Sittplatser` is drag/drop plus explicit remove
- `Regler` is the only click-based student authoring workspace
- old visible planner-note semantics are no longer part of the active contract

## Non-goals

- Adding a replacement notes UI, inspector, or secondary student-detail surface
- Changing `Regler` rule-authoring behavior beyond preserving its current click path
- Redesigning the seating workspace layout beyond the removal-driven cleanup
- Preserving old student-note data through compatibility shims or forward-mapping logic

## Implementation plan

1. Remove the seating notes UI path:
   - delete `PlannerMetadataDrawer.vue`
   - remove drawer-local state from `PlannerWorkspaceShell.vue`
   - remove seating-only click-to-open behavior from the seating lane
2. Remove obsolete seating activation semantics:
   - stop treating seat/student click as a selectable interaction in `Sittplatser`
   - remove selected-student plumbing that exists only for the drawer path
   - keep drag/drop and explicit remove actions intact
3. Remove the draft notes contract:
   - delete `StudentPlanningMeta` / `student_planning_meta` from SPA types and state support
   - remove API request/response DTO fields and application/domain workspace handling
   - remove repository snapshot/history serialization and replay support for student notes
4. Remove persistence:
   - add the migration that drops `classroom_planner_student_planning_meta`
   - delete the related SQLAlchemy model and repository mapping
5. Update docs/handoff:
   - keep `EPIC-27`, the new story, `docs/index.md`, and `.agents/handoff.md` aligned with the
     removal decision and verification evidence

## Test plan

- `pdm run docs-validate`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-test -- --run src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.spec.ts src/views/apps/useClassroomState.spec.ts`
- `pdm run pytest tests/unit/application/apps/classroom_planner tests/unit/web/apps/classroom_planner tests/unit/infrastructure/repositories/test_classroom_planner* -q`
- Focused live proof on `http://127.0.0.1:5173/apps/classroom.group-seating-studio` confirming:
  - clicking students in `Sittplatser` causes no visible state change
  - drag/drop still moves students
  - `Regler` still owns click-based student rule authoring

## Implementation Summary (as of 2026-04-01)

- Deleted `frontend/apps/skriptoteket/src/views/apps/components/PlannerMetadataDrawer.vue` and
  removed all seating-mode selected-student/drawer state from the live planner shell.
- Removed `student_planning_meta` from the active frontend store contract, backend DTOs,
  domain/application workspace models, repository serialization/history, and generated frontend API
  types.
- Added migration `b7f9c2d4e1a6_drop_classroom_planner_student_notes.py` to drop
  `classroom_planner_student_planning_meta` and scrub the retired history key from persisted draft
  snapshots.
- Focused frontend, backend, and migration checks passed, and live browser proof confirmed that a
  real `Sittplatser` student click keeps the pool button in `planner-choice-button-strong` with
  zero active student buttons before and after the click.

## Rollback plan

Revert the slice as one clean rollback if needed. Do not reintroduce a half-kept compatibility
contract; either the old notes drawer contract exists end-to-end or it is removed end-to-end.
