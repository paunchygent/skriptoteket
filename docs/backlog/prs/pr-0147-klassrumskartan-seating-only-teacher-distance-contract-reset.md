---
type: pr
id: PR-0147
title: "Klassrumskartan: seating-only teacher-distance contract reset"
status: done
owners: "agents"
created: 2026-03-26
updated: 2026-03-26
stories:
  - "ST-27-01"
tags: ["backend", "frontend-contract", "api", "migrations", "klassrumskartan", "smart-assignment"]
dependencies:
  - "ADR-0074"
  - "EPIC-27"
  - "PR-0145"
acceptance_criteria:
  - "Given the smart-assignment contract previously exposed seating-only `support_seat`, when this slice lands, then the authoritative backend/frontend contract instead uses a seating-only teacher-distance concept such as `near_teacher` with no compatibility shim for the old field."
  - "Given a client patches or reads draft workspace smart data after this slice, when the API serializes or validates the payload, then `seating_preferences[].near_teacher` is accepted and the old `smart_preferences[].support_seat` shape is rejected."
  - "Given draft workspaces, history snapshots, and persistence rows are stored after this slice, when smart seating preferences are loaded or saved, then the repo uses renamed seating-only persistence and history keys instead of the old smart-preference naming."
  - "Given the current notes-only SPA still loads and autosaves planner drafts before the later visual rule-authoring UI exists, when it hydrates or saves a workspace, then it preserves the renamed seating-only preference contract rather than dropping it on autosave."
---

## Problem

The accepted smart-assignment docs now say the teacher-facing product should not expose
`Support seat` and should not treat per-student metadata editing as the primary smart-rule model.

The codebase still carries the older backend-first naming:

- domain model: `StudentSmartPreference.support_seat`
- API contract: `smart_preferences[].support_seat`
- persistence table: `classroom_planner_student_smart_preferences`

That contract is now misleading in two ways:

- it implies a generic per-student smart-preference model rather than a seating-only rule
- it encodes product jargon that the approved docs no longer want in the teacher-facing concept

Before the class-wide toolbar/rule-authoring UI can be built honestly, the contract needs a clean
reset to a seating-only teacher-distance concept.

## Goal

Replace the old `support_seat` concept with a seating-only teacher-distance contract across domain,
API, persistence, migration coverage, and the thin frontend contract layer, so the later visual
rule-authoring UI can build on an honest backend shape.

## Non-goals

- Implementing the class-wide visual smart-rule toolbar UI.
- Shipping `Håll isär` / `Håll nära` authoring in the frontend.
- Reworking the student metadata drawer beyond keeping it secondary.
- Delivering solver behavior changes or explanation UX.
- Preserving backwards-compatible aliases for `support_seat` or `smart_preferences`.

## Implementation plan

1. Red phase: lock the renamed contract in tests first.
   - Update API tests to expect `seating_preferences[].near_teacher` and to reject the old
     `smart_preferences[].support_seat` payload.
   - Update repository/history tests to expect renamed workspace collections and snapshot keys.
   - Update migration schema assertions to expect the renamed seating-preference table/column and
     to fail if the old smart-preference table remains the authoritative schema.
   - Update the thin frontend store tests so the notes-only SPA preserves the renamed field during
     load/autosave.

2. Domain and application rename.
   - Replace `StudentSmartPreference` with `StudentSeatingPreference`.
   - Replace `smart_preferences` collections with `seating_preferences`.
   - Replace `support_seat` with `near_teacher`.
   - Keep the concept explicitly seating-only; grouping must not consume it as a shared rule.

3. API contract reset.
   - Rename DTOs and request/response fields to the new seating-only names.
   - Keep `extra="forbid"` and the no-shims posture so old payloads fail loudly.
   - Ensure PATCH handling, workspace serialization, and resumable/load flows all round-trip the
     new contract.

4. Persistence and history rename.
   - Rename ORM model/table/column usage to seating-only names.
   - Rename repository load/save/history snapshot keys so the bounded undo/redo stack remains
     aligned with the new contract.
   - Preserve the existing relational structure and per-draft uniqueness semantics.

5. Forward migration.
   - Add a new Alembic revision after the current head.
   - Create the renamed seating-preference table/column contract and drop the old smart-preference
     table as part of the continued burn-and-rebuild posture.
   - Do not add a compatibility bridge for old rows.

6. Thin frontend contract sync only.
   - Update the frontend types/store load-save layer so the current notes-only planner does not
     clobber the renamed backend field before the later visual rule-authoring slice lands.
   - Do not add new smart-rule UI in this PR.

## PR-sized execution checklist

- [x] Update unit tests first:
  - `tests/unit/web/apps/classroom_planner/test_api.py`
  - `tests/unit/infrastructure/repositories/test_classroom_planner_review_fixes.py`
  - `tests/integration/migration_schema_assertions.py`
  - `frontend/apps/skriptoteket/src/views/apps/useClassroomState.spec.ts`
- [x] Rename domain/application models:
  - `src/skriptoteket/domain/curated_apps/classroom_planner/models.py`
  - `src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py`
- [x] Rename API DTOs/contracts:
  - `src/skriptoteket/web/api/v1/apps_classroom_planner.py`
- [x] Rename ORM/repository mapping:
  - `src/skriptoteket/infrastructure/db/models/classroom_planner_plan_draft.py`
  - `src/skriptoteket/infrastructure/repositories/classroom_planner.py`
- [x] Add a new Alembic revision under `migrations/versions/`
- [x] Update frontend contract sync only:
  - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerTypes.ts`
  - `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts`
- [x] Run verification and record it in `.agents/handoff.md`

## Test plan

- `pdm run pytest tests/unit/web/apps/classroom_planner/test_api.py -q`
- `pdm run pytest tests/unit/infrastructure/repositories/test_classroom_planner_review_fixes.py -q`
- `pdm run pytest tests/integration/migration_schema_assertions.py -q`
- `pdm run pytest -m docker 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[<new_revision_id>]' -q`
- `pdm run fe-test -- --run src/views/apps/useClassroomState.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`

## Rollback plan

- Revert the new migration revision and contract rename together if the seating-only reset proves
  incorrectly specified.
- Do not reintroduce `support_seat` aliases as a rollback shortcut; rollback should restore the
  prior contract explicitly if needed.
- Preserve the docs/handoff notes so the product-direction decision is not rediscovered through
  trial and error.
