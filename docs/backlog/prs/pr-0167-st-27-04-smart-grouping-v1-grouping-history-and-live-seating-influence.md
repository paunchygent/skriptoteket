---
type: pr
id: PR-0167
title: "Klassrumskartan: smart grouping v1 grouping history, live seating influence, and backend run contract"
status: ready
owners: "agents"
created: 2026-03-29
updated: 2026-03-29
stories:
  - "ST-27-04"
tags:
  [
    "backend",
    "frontend",
    "api",
    "planner",
    "smart-assignment",
    "klassrumskartan",
    "grouping",
    "history",
  ]
dependencies:
  - "ADR-0074"
  - "EPIC-27"
  - "PR-0150"
  - "PR-0151"
  - "PR-0152"
  - "PR-0154"
  - "PR-0155"
acceptance_criteria:
  - "Given the teacher is in `Grupper` and `Smart` is `off`, when they use `Slumpa`, then grouping keeps the current local random reshuffle behavior and preserves the current group count plus teacher-defined group names."
  - "Given the teacher is in `Grupper` and `Smart` is `on`, when they use `Slumpa`, then the planner calls one backend-owned smart grouping run endpoint and persists the returned grouping result instead of performing a frontend-only random shuffle."
  - "Given roster-global `Keep apart` and `Keep near` rules exist, when smart grouping runs, then the backend interprets those same visible rules at grouping level without introducing a second grouping-only rule model."
  - "Given grouping `Use history` is enabled, when the smart run evaluates prior grouping outcomes, then it uses grouping-specific similarity history rather than treating seating continuity as grouping history."
  - "Given grouping history contains exact or near-repeat groupings, when smart grouping runs with `Use history` enabled, then it penalizes repeated student co-memberships and not only exact repeated group ids."
  - "Given the explicit grouping seat-continuity toggle is enabled and an active seating draft exists for the same class, when smart grouping runs, then that live seating arrangement is the first continuity source and outranks rotational diversity preferences while still respecting explicit relation rules."
  - "Given the explicit grouping seat-continuity toggle is enabled but no active seating draft exists, when eligible seating checkpoints exist, then smart grouping may use those checkpoints as a fallback continuity source without treating them as grouping history."
  - "Given `Use history` is enabled but no eligible grouping checkpoints exist, when the teacher tries to run smart grouping, then the run is blocked with a short teacher-facing explanation and the draft assignments stay unchanged."
---

## Problem

`ST-27-04` is the remaining core smart-assignment slice, but the currently approved package still
leans too heavily on seating checkpoints as the grouping fallback story. That is no longer precise
enough for the actual product intent.

The clarified teacher model is:

- grouping history must be distinct from seating continuity
- `Keep apart` and `Keep near` remain one shared visible rule model across seating and grouping
- grouping may optionally be influenced by the current seating arrangement to reduce transition
  disorder during class-to-group work
- that seating continuity signal is not the same thing as grouping history
- when live seating continuity is explicitly enabled and a current seating draft exists, it should
  outrank rotational anti-repeat pressure rather than behaving like one more soft historical hint

Without this explicit split, the implementation will either:

- overfit grouping history onto seating checkpoints
- violate the accepted "no raw drafts as history" rule by accident
- or hide the actual precedence model inside the solver instead of documenting it up front

## Goal

Ship one implementation-ready smart-grouping slice that makes the source-of-truth lanes explicit
before code lands:

- `Use history` means grouping anti-repeat memory
- `Ska hur nära de sitter räknas?` means seating-continuity input
- shared relation rules remain roster-global and mode-shared
- the backend owns smart grouping orchestration and scoring
- grouping history is label-insensitive and similarity-aware
- live seating continuity can read the active seating draft as a current input without redefining
  that live draft as history

## Non-goals

- Building a generic shared smart-assignment framework before smart grouping exists.
- Replacing the current `Regler` workspace or reopening drawer-first rule editing.
- Treating autosave, undo/redo, or abandoned grouping drafts as grouping history.
- Treating `Närmare läraren` as a grouping rule.
- Adding a new teacher-facing "rotation strength" or "continuity weight" control.
- Building a teacher-facing checkpoint browser in this slice.
- Redefining the grouping workspace around seating-first behavior when the explicit seat-continuity
  toggle is off.

## Precedence Rules

The smart grouping solver and handler must use this precedence model:

1. Explicit visible relation rules are strongest.
   - `Keep near` in grouping means "prefer the same group."
   - `Keep apart` in grouping means "spread across different groups whenever possible, otherwise
     maximize spread and minimize collisions."

2. Group structure invariants come next.
   - Preserve the current group count.
   - Preserve current teacher-defined group names and order.
   - Do not let smart grouping silently create/remove groups or rename them.

3. Live seating continuity is the first optional continuity source.
   - This source is enabled only by the explicit grouping seat-continuity toggle.
   - If an active seating draft exists for the same class, use that draft first.
   - This live seating signal outranks grouping-history anti-repeat and rerun-diversity pressure.
   - This live seating signal does not override explicit relation rules.

4. Grouping history is separate and comes after live seating continuity.
   - This source is enabled only by grouping `Use history`.
   - Grouping history penalizes exact and near-repeat groupings.
   - Grouping history must compare normalized student partitions and repeated student
     co-memberships, not raw `group_id` or group-name matches.

5. Seating checkpoints are fallback continuity input only.
   - If the explicit grouping seat-continuity toggle is enabled and no active seating draft exists,
     the solver may consume the latest eligible seating checkpoint data as a fallback continuity
     source.
   - Those seating checkpoints are not grouping history and must not satisfy the grouping-history
     lane by themselves.

6. Rerun diversity is last.
   - Prefer a materially different strong candidate from the current grouping assignment when the
     valid search space allows it.
   - Diversity must not override stronger explicit rules, live seating continuity, or grouping
     history constraints.

## Source-Of-Truth Rules

The implementation should treat the inputs as four distinct lanes:

- Shared roster-global rule lane:
  - `Keep apart`
  - `Keep near`
- Draft-local grouping controls:
  - `Smart`
  - `Use history`
  - `grouping_seating_distance_enabled`
- Grouping-history lane:
  - dedicated grouping checkpoints or equivalent export-backed grouping-history records
  - similarity-aware, label-insensitive
- Live seating-continuity lane:
  - active seating draft first
  - latest eligible seating checkpoint second

The critical rule is:

- active seating draft may be a live grouping input
- active seating draft is not grouping history

## Doc Adjustments Before Code

Before implementation begins, update the approved docs so the slice stays explicit instead of
relying on verbal context:

- `docs/adr/adr-0074-klassrumskartan-smart-assignment-v1.md`
  - clarify that grouping history is separate from live seating continuity
  - clarify that the active seating draft may be consumed as a current input when the explicit
    grouping seat-continuity toggle is enabled
  - clarify the precedence order listed in this PR doc
- `docs/backlog/stories/story-27-04-klassrumskartan-smart-grouping-v1.md`
  - add the grouping-history vs live-seating split to the acceptance criteria/notes
  - state that grouping history is label-insensitive and similarity-aware
  - state that live seating continuity outranks rotational diversity when explicitly enabled
- `docs/backlog/reviews/review-epic-27-klassrumskartan-smart-assignment-v1.md`
  - append a post-approval refinement note so the final implementation review has an audit trail
    for this clarified precedence model

## Implementation Plan

1. Lock the grouping contract in docs and tests first.
   - Land the doc refinements above before writing the smart grouping code.
   - Add domain/application/web tests that encode the precedence order rather than only the
     endpoint shape.

2. Add the dedicated grouping-history lane.
   - Introduce one normalized grouping-history contract that compares partitions without depending
     on group ids or group labels.
   - Record exact repeat identity plus near-repeat similarity through repeated student
     co-memberships.
   - Persist grouping-history records from successful explicit grouping exports so history stays
     checkpoint-backed.

3. Add the live seating-continuity read seam.
   - Read the active seating draft for the same class when the explicit grouping seat-continuity
     toggle is enabled and the teacher has one.
   - Fall back to the latest eligible seating checkpoint when no active seating draft exists.
   - Keep this lane separate from grouping `Use history`.

4. Add the backend-owned smart grouping run.
   - Introduce one pure smart-grouping domain module that scores:
     - shared relation rules
     - live seating continuity
     - grouping-history anti-repeat
     - rerun diversity
   - Add one application handler that loads:
     - the active grouping draft workspace
     - roster-global smart rules
     - grouping-history inputs
     - live seating input
   - Block honestly when `Use history` is enabled but no eligible grouping-history records exist.

5. Add the bespoke web/API contract.
   - Add `POST /api/v1/apps/classroom.group-seating-studio/drafts/grouping/{draft_id}/smart-run`
   - Request body:
     - `expected_revision: int`
   - `200` applied response:
     - `status: "applied"`
     - `workspace: DraftWorkspaceResponse`
     - `used_history: bool`
     - `used_live_seating: bool`
     - `message: str | null`
   - `200` blocked response:
     - `status: "blocked"`
     - `reason: "no_history"`
     - `workspace: null`
     - `used_history: false`
     - `used_live_seating: bool`
     - `message: str`
   - Use HTTP errors only for true request failures such as `404`, `409`, and `422`.

6. Wire the grouping workspace onto the smart run.
   - Branch grouping `Slumpa`:
     - `Smart` off -> current local random behavior
     - `Smart` on -> backend smart grouping run
   - Add the missing draft-local setter and autosave serialization for
     `grouping_seating_distance_enabled`.
   - Show the explicit grouping seat-continuity toggle in the grouping toolbar.
   - Keep `Use history` semantically separate from that toggle.

## Exact Files To Change

- Docs:
  - `docs/adr/adr-0074-klassrumskartan-smart-assignment-v1.md`
  - `docs/backlog/stories/story-27-04-klassrumskartan-smart-grouping-v1.md`
  - `docs/backlog/reviews/review-epic-27-klassrumskartan-smart-assignment-v1.md`
  - `docs/backlog/prs/pr-0167-st-27-04-smart-grouping-v1-grouping-history-and-live-seating-influence.md`

- Backend domain and protocols:
  - `src/skriptoteket/domain/curated_apps/classroom_planner/smart_grouping.py`
  - `src/skriptoteket/domain/curated_apps/classroom_planner/smart_grouping_scoring.py`
  - `src/skriptoteket/domain/curated_apps/classroom_planner/grouping_checkpoints.py`
  - `src/skriptoteket/protocols/classroom_planner.py`

- Backend application and DI:
  - `src/skriptoteket/application/curated_apps/classroom_planner/handlers/smart_grouping.py`
  - `src/skriptoteket/application/curated_apps/classroom_planner/handlers/grouping_export_job_completion.py`
  - `src/skriptoteket/application/curated_apps/classroom_planner/handlers/grouping_export_jobs.py`
  - `src/skriptoteket/application/curated_apps/classroom_planner/__init__.py`
  - `src/skriptoteket/di/curated_apps.py`

- Backend web/API:
  - `src/skriptoteket/web/api/v1/apps_classroom_planner_grouping.py`

- Backend persistence:
  - `src/skriptoteket/infrastructure/db/models/classroom_planner_grouping_export_checkpoint.py`
  - `src/skriptoteket/infrastructure/repositories/classroom_planner_grouping_export_checkpoints.py`
  - `migrations/versions/<new_revision>_classroom_planner_grouping_export_checkpoints.py`

- Frontend:
  - `frontend/apps/skriptoteket/src/views/apps/useSmartGroupingRun.ts`
  - `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts`
  - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerSmartRuleActions.ts`
  - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerTypes.ts`
  - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerStateSupport.ts`
  - `frontend/apps/skriptoteket/src/views/apps/useDraftPersistenceLane.ts`
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspaceToolbar.vue`

- Tests:
  - `tests/unit/domain/curated_apps/classroom_planner/test_smart_grouping_solver.py`
  - `tests/unit/application/apps/classroom_planner/test_smart_grouping.py`
  - `tests/unit/web/apps/classroom_planner/test_smart_grouping_api.py`
  - `tests/unit/infrastructure/repositories/test_classroom_planner_grouping_export_checkpoints.py`
  - `tests/integration/migration_schema_assertions.py`
  - `frontend/apps/skriptoteket/src/views/apps/useSmartGroupingRun.spec.ts`
  - `frontend/apps/skriptoteket/src/views/apps/useClassroomState.spec.ts`
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.spec.ts`

## Test Plan

- Docs:
  - `pdm run docs-validate`

- Backend:
  - `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_grouping_solver.py tests/unit/application/apps/classroom_planner/test_smart_grouping.py tests/unit/web/apps/classroom_planner/test_smart_grouping_api.py tests/unit/infrastructure/repositories/test_classroom_planner_grouping_export_checkpoints.py -q`
  - `pdm run pytest -m docker 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[<new_revision>]' -q`
  - `pdm run typecheck`

- Frontend:
  - `pdm run fe-test -- --run src/views/apps/useSmartGroupingRun.spec.ts src/views/apps/useClassroomState.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts`
  - `pdm run fe-type-check`

- Live proof:
  - `ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local`
  - add one new Playwright proof for grouping smart-run semantics on `http://127.0.0.1:5173`

## Rollback Plan

- Revert the smart-grouping backend endpoint, frontend branch, and grouping-history persistence as
  one slice while keeping `PR-0151`, `PR-0152`, `PR-0154`, and `PR-0155` intact.
- If live seating continuity proves too ambiguous, keep the dedicated grouping-history lane and
  temporarily disable only the grouping seat-continuity toggle while preserving the backend
  grouping smart-run contract.
