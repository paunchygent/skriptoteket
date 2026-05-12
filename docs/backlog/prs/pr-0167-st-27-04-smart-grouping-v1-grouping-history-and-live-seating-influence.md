---
type: pr
id: PR-0167
title: "Klassrumskartan: smart grouping v1 grouping history, live seating influence, and backend run contract"
status: ready
owners: "agents"
created: 2026-03-29
updated: 2026-05-11
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
  - "Given the grouping toolbar renders, when the teacher works in `Grupper`, then the command row stays single-height and organized into a left action cluster plus a right class/export cluster."
  - "Given the grouping toolbar renders, when the teacher scans the right side, then the compact class selector sits between the group-count stepper and export instead of in a separate context band."
  - "Given grouping rules are already visible through `Regler` and the student markers, when the grouping toolbar renders, then it does not show a redundant active-rule count pill."
  - "Given roster-global `Keep apart` and `Keep near` rules exist, when smart grouping runs, then the backend interprets those same visible rules at grouping level without introducing a second grouping-only rule model."
  - "Given the teacher tunes smart grouping behavior, when they open `Smart-inställningar`, then `Historik`, `Klassrum`, and `Sittschemat` are available there rather than as first-row toolbar controls."
  - "Given grouping `Historik` is enabled inside `Smart-inställningar`, when the smart run evaluates prior grouping outcomes, then it uses grouping-specific similarity history only and does not treat classroom awareness or seating continuity as grouping history."
  - "Given grouping history contains exact or near-repeat groupings, when smart grouping runs with `Use history` enabled, then it penalizes repeated student co-memberships and not only exact repeated group ids."
  - "Given `Klassrum` is selected and `Sittschemat` is enabled inside `Smart-inställningar`, when an active seating draft exists for the same class, then that live seating arrangement becomes the first compactness source and uses seat-topology distance to penalize same-group spread quadratically beyond a local elastic radius while still respecting explicit relation rules."
  - "Given `Klassrum` is selected and `Sittschemat` is enabled inside `Smart-inställningar` but no active seating draft exists, when eligible seating checkpoints exist, then smart grouping may use those checkpoints as a fallback compactness source without treating them as grouping history."
  - "Given `Klassrum` is selected and `Sittschemat` is enabled but no usable seating context exists, when smart grouping runs, then it falls back honestly to rules plus any enabled history lane instead of pretending the classroom-aware lane was used."
  - "Given `Use history` is enabled but no eligible grouping checkpoints exist, when the teacher runs smart grouping, then the run applies without history, reports `used_history=false`, and does not treat draft state, seating compactness, or public guest local state as grouping history."
  - "Given the teacher needs to adjust rules, when they navigate to `Regler`, then rules remain a workspace-level setting surface and do not appear as a duplicate toolbar shortcut in `Grupper`."
  - "Given the teacher switches between `Grupper` and `Sittplatser`, when they scan the first row, then both workspaces follow the same single-row action grammar with a right-side selector/export cluster and Smart tuning moved into `Smart-inställningar`."
---

## Problem

`ST-27-04` is the remaining core smart-assignment slice, but the currently approved package still
leans too heavily on seating checkpoints as the grouping fallback story. That is no longer precise
enough for the actual product intent.

The clarified teacher model is:

- grouping history must be distinct from seating continuity
- `Keep apart` and `Keep near` remain one shared visible rule model across seating and grouping
- the grouping toolbar may include one compact class switch, but not a second context band
- `Smart` decides backend smart grouping vs local random
- classroom-aware grouping is a separate compactness lane configured through `Klassrum` +
  `Sittschemat` inside Smart-inställningar
- `Historik` is a separate anti-repeat lane inside smart settings and is not a synonym for
  classroom awareness
- `Regler` is workspace navigation, not a toolbar action shortcut
- classroom-aware grouping may use the current seating arrangement to reduce transition disorder and
  avoid groups whose members are visibly split across the room
- classroom-aware compactness should be a soft objective rather than a brittle hard failure rule

Without this explicit split, the implementation will either:

- overfit grouping history onto seating checkpoints
- violate the accepted "no raw drafts as history" rule by accident
- or hide the actual precedence model inside the solver instead of documenting it up front

## Goal

Ship one implementation-ready smart-grouping slice that makes the source-of-truth lanes explicit
before code lands:

- `Historik` means grouping anti-repeat memory and belongs to smart settings, not to the first-row
  action toolbar
- classroom-aware grouping is tuned through `Klassrum` + `Sittschemat` in Smart-inställningar
- the teacher-facing grouping shell separates first-row actions from secondary Smart settings
  clearly
- shared relation rules remain roster-global and mode-shared
- the backend owns smart grouping orchestration and scoring
- grouping history is label-insensitive and similarity-aware
- classroom-aware grouping uses seat-topology distance and a soft compactness penalty
- live seating continuity can read the active seating draft as a current compactness input without
  redefining that live draft as history

## Approved UI Snapshot (2026-03-30)

This section freezes the approved desktop-first grouping control ownership before more UI
implementation lands. It supersedes the earlier shared context-row proposal, the verbose
classroom-helper experiments, the first-row history toggle, and the duplicate `Regler` toolbar
shortcut.

Artifacts:

- `docs/reference/reports/artifacts/pr-0167-grouping-layout-exploration-v2/toolbar-class-settings.png`
- `docs/reference/reports/artifacts/pr-0167-grouping-layout-exploration-v2/all-overflow-settings.png`

Approved layout:

```text
+--------------------------------------------------------------------------------------------------+
| PR0167 Klass d59552                                                                  [Avsluta]   |
| [ ÖVERSIKT ] [ GRUPPER ] [ SITTPLATSER ] [ REGLER ]                                              |
|--------------------------------------------------------------------------------------------------|
| [↶] [↷] [Nytt utkast] [Slumpa] [Smart|settings] [Börja om] [ - | 6 | + ]     [Klass v] [Exportera▼] [⋮] |
+--------------------------------------------------------------------------------------------------+

+--------------------------------------------------------------------------------------------------+
| Ej grupperade                         | Grupp 1                    | Grupp 2                     |
| student list                          |                            |                             |
|                                       | Grupp 3                    | Grupp 4                     |
+--------------------------------------------------------------------------------------------------+
```

Smart settings ownership:

```text
+---------------------------------------------+
| Smart-inställningar                         |
|---------------------------------------------|
| Historik   [på/av]                          |
| Undvik att samma elever hamnar i samma      |
| grupp gång på gång.                         |
|                                             |
| Klassrum                                    |
| [ PR0167 Sal d59552 · 4 platser          v ]|
|                                             |
| Sittschemat [på/av]                         |
| Om det finns ett sittschema för det         |
| valda klassrummet kan Smart ta hänsyn       |
| till det.                                   |
|                                             |
| Regler                                      |
| Du lägger till och ändrar regler i          |
| arbetsytan Regler.                          |
| [Öppna Regler]                              |
+---------------------------------------------+
```

Ownership rationale:

- `Översikt` owns class-list and classroom resource management.
- The grouping toolbar owns immediate actions plus one compact class switch on the right.
- `Sittplatser` follows the same first-row grammar, but keeps its compact classroom selector on the right.
- The first row must stay a single-height desktop command strip with a left action cluster and a
  right class/export cluster.
- `Historik` is a smart-behavior setting, not a first-row grouping tool.
- `Klassrum` and `Sittschemat` are Smart settings, not command-row clutter.
- `Regler` is workspace navigation and rule tuning, not a grouping-toolbar action.
- `Klassrum` without `Sittschemat` is just stored context.
- `Klassrum` plus enabled `Sittschemat` turns on the classroom-aware compactness lane.

Implementation guardrails from this snapshot:

- Keep the class selector compact and place it in the grouping toolbar's right cluster.
- Do not place classroom selection in the first-row grouping toolbar.
- Do not place `Historik` in the first-row grouping toolbar.
- Do not duplicate `Regler` as both a workspace mode and a grouping-toolbar shortcut.
- Do not add explanatory/instructional button labels for settings behavior in the toolbar.
- Mirror the same first-row grammar in `Sittplatser`; do not leave one workspace on the older stacked toolbar pattern.
- Keep rows level and single-height on the desktop shell:
  - no accidental second row for one stray control
  - no uneven vertical alignment between selector, toolbar actions, steppers, and export cluster

## Non-goals

- Building a generic shared smart-assignment framework before smart grouping exists.
- Replacing the current `Regler` workspace or reopening drawer-first rule editing.
- Treating autosave, undo/redo, or abandoned grouping drafts as grouping history.
- Treating `Närmare läraren` as a grouping rule.
- Adding a new teacher-facing "rotation strength" or "compactness weight" control.
- Building a teacher-facing checkpoint browser in this slice.
- Redefining the grouping workspace around seating-first behavior when classroom-aware grouping is
  off.

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

3. Classroom-aware compactness is the first optional spatial source.
   - This source is enabled when `Klassrum` is selected and `Sittschemat` is on in Smart-inställningar.
   - If an active seating draft exists for the same class, use that draft first.
   - If no active seating draft exists, use the latest eligible seating checkpoint as fallback.
   - This lane uses seat-topology distance and penalizes same-group spread quadratically beyond a
     local elastic radius.
   - This lane outranks grouping-history anti-repeat and rerun-diversity pressure.
   - This lane does not override explicit relation rules.
   - The exact radius and weight curve stay intentionally tunable through simulations and review of
     outcomes versus the desired classroom behavior.

4. Grouping history is separate and comes after classroom-aware compactness.
   - This source is enabled only by grouping `Use history`.
   - Grouping history penalizes exact and near-repeat groupings.
   - Grouping history must compare normalized student partitions and repeated student
     co-memberships, not raw `group_id` or group-name matches.
   - History must not be widened into classroom awareness by accident.

5. Rerun diversity is last.
   - Prefer a materially different strong candidate from the current grouping assignment when the
     valid search space allows it.
   - Diversity must not override stronger explicit rules, classroom-aware compactness, or grouping
     history constraints.

## Source-Of-Truth Rules

The implementation should treat the inputs as four distinct lanes:

- Shared roster-global rule lane:
  - `Keep apart`
  - `Keep near`
- Draft-local grouping controls:
  - `Smart`
  - smart settings such as `Historik`
  - selected classroom context plus the `Sittning` switch in Smart-inställningar
- Grouping-history lane:
  - dedicated grouping checkpoints or equivalent export-backed grouping-history records
  - similarity-aware, label-insensitive
- Classroom-aware compactness lane:
  - active seating draft first
  - latest eligible seating checkpoint second
  - seat-topology distance and elastic quadratic spread penalties when usable seating context exists

The critical rule is:

- active seating draft may be a live classroom-aware grouping input
- active seating draft is not grouping history
- no usable seating context means honest fallback, not fake classroom-aware success

## Doc Adjustments Before Code

Before implementation begins, update the approved docs so the slice stays explicit instead of
relying on verbal context:

- `docs/adr/adr-0074-klassrumskartan-smart-assignment-v1.md`
  - clarify that grouping history is separate from classroom-aware compactness
  - clarify that the active seating draft may be consumed as a current compactness input when the
    Smart settings drawer enables classroom-aware grouping
  - clarify the precedence order listed in this PR doc
- `docs/backlog/stories/story-27-04-klassrumskartan-smart-grouping-v1.md`
  - add the `Smart` vs classroom-aware vs history split to the acceptance criteria/notes
  - state that grouping history is label-insensitive and similarity-aware
  - state that classroom-aware compactness outranks rotational diversity when enabled
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

3. Add the classroom-aware compactness input seam.
   - Read the active seating draft for the same class when classroom-aware grouping is enabled
     through `Klassrum` + `Sittning` in Smart-inställningar.
   - Fall back to the latest eligible seating checkpoint when no active seating draft exists.
   - Derive seat-topology distance from that seating context and penalize same-group spread
     quadratically beyond one local elastic radius.
   - Keep this lane separate from grouping `Use history`.
   - Keep the exact radius and weight curve intentionally tunable through simulations and outcome
     review instead of freezing them in prose.

4. Add the backend-owned smart grouping run.
   - Introduce one pure smart-grouping domain module that scores:
     - shared relation rules
     - classroom-aware compactness
     - grouping-history anti-repeat
     - rerun diversity
   - Add one application handler that loads:
     - the active grouping draft workspace
     - roster-global smart rules
     - grouping-history inputs
     - live seating input
   - Run without history when `Use history` is enabled but no eligible grouping-history records
     exist, while still reporting `used_history=false` and keeping checkpoint-only source
     semantics.

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
   - `PR-0316` removes the stale blocked response branch if `no_history` is the
     only blocked business result. The normal no-checkpoint first-run case must
     return the applied response above with `used_history=false`.
   - Historical `200` blocked response shape, retained here only as superseded
     context until `PR-0316` lands:
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
   - Keep one compact class selector in the grouping toolbar's right cluster near export.
   - Move `Klassrum`, `Sittning`, and `Historik` into the `Smart` settings drawer instead of the
     first-row toolbar.
   - Keep `Smart` plus the adjacent settings trigger as the only first-row grouping intelligence
     controls.
   - Keep `Regler` only in workspace navigation and rules tuning, not as a duplicate toolbar
     shortcut in `Grupper`.
   - Remove the redundant grouping active-rule count pill from the toolbar.
   - Keep smart-run feedback honest when classroom-aware grouping had no usable seating context.

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
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerClassWorkspace.vue`
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`
  - `frontend/apps/skriptoteket/src/views/apps/useSmartGroupingRun.ts`
  - `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts`
  - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerSmartRuleActions.ts`
  - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerTypes.ts`
  - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerStateSupport.ts`
  - `frontend/apps/skriptoteket/src/views/apps/useDraftPersistenceLane.ts`
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspaceToolbar.vue`
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspaceToolbar.vue`

- Tests:
  - `tests/unit/domain/curated_apps/classroom_planner/test_smart_grouping_solver.py`
  - `tests/unit/domain/curated_apps/classroom_planner/test_smart_grouping_solver_g20_sa24d.py`
  - `tests/unit/domain/curated_apps/classroom_planner/test_smart_grouping_solver_bf25_g104.py`
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
  - `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_grouping_solver.py tests/unit/domain/curated_apps/classroom_planner/test_smart_grouping_solver_g20_sa24d.py tests/unit/domain/curated_apps/classroom_planner/test_smart_grouping_solver_bf25_g104.py tests/unit/application/apps/classroom_planner/test_smart_grouping.py tests/unit/web/apps/classroom_planner/test_smart_grouping_api.py tests/unit/infrastructure/repositories/test_classroom_planner_grouping_export_checkpoints.py -q`
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
- If classroom-aware compactness proves too ambiguous or too weakly tuned at first, keep the
  dedicated grouping-history lane and temporarily disable only the classroom-aware grouping lane
  while preserving the backend grouping smart-run contract.
