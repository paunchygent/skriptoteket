---
type: pr
id: PR-0115
title: "Klassrumskartan: route-shell orchestration and catalog-home state extraction"
status: in_progress
owners: "agents"
created: 2026-03-24
updated: 2026-03-24
stories: []
tags: ["frontend", "refactor", "srp", "pinia", "workflow"]
acceptance_criteria:
  - "`frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.vue` is reduced below 500 LOC by extracting non-draft route-shell orchestration into dedicated state/orchestration modules."
  - "Catalog/home state for rosters, templates, selected overview context, workspace summary, and overview-local resumable-card state no longer lives as an implicit second store inside `ClassroomPlannerView.vue`."
  - "Repeated 'flush pending save, inspect save status, then continue or block' guard logic is extracted into reusable route-shell orchestration helpers instead of being duplicated across planner transitions."
  - "The active draft Pinia store remains focused on draft workspace state, while catalog/home state is handled separately through a dedicated Pinia store or tightly scoped orchestration module."
  - "The shipped cutover behavior remains unchanged: overview-first entry, planner entry, history reopen/delete, and exit-to-origin all still behave the same."
  - "Focused frontend tests pass for the extracted route-shell state/orchestration, and a live browser proof confirms overview-first entry plus exit-to-origin still work on the local SPA."
---

## Problem

`ClassroomPlannerView.vue` currently acts like a second hidden store on top of the real planner
Pinia store. It owns:

- catalog loading
- selected roster / selected classroom context
- workspace-summary loading and refresh
- bootstrapping and resumable-home logic
- modal and delete-confirmation state
- planner screen routing
- entry-origin exit orchestration
- repeated save-guard branches before transitions

That makes the route shell harder to reason about, harder to test, and harder to extend cleanly
before export/checkpoint flows arrive.

## Goal

Move Klassrumskartan's non-draft route-shell and overview/catalog orchestration into a clearer
state model so the route view becomes a thin composition layer and the existing draft store can stay
focused on active workspace concerns.

## Non-goals

- Changing teacher-visible cutover behavior or route semantics.
- Refactoring the room-template editor internals.
- Reworking grouping/seating UI decomposition beyond what is strictly needed for the extracted
  route-shell contract.
- Shipping export/checkpoint flows in this PR.

## Implementation plan

- State split:
  - introduce a dedicated overview/catalog state owner for:
    - rosters
    - templates
    - selected roster id
    - selected overview classroom id
    - class workspace summary
    - overview-local resumable dismiss state
    - bootstrapping / loading / error state
  - keep `useClassroomState` focused on the active draft workspace only
- Route-shell extraction:
  - slim `ClassroomPlannerView.vue` into a composition layer that wires child components to the new
    route-shell state
  - move bootstrapping and overview-opening logic into dedicated orchestration helpers
  - move exit-to-origin orchestration into a dedicated route-shell helper/composable
- Save guards:
  - extract the repeated "flush save then continue or block with message" logic into reusable
    helpers so transitions are consistent and less error-prone
  - preserve current teacher-facing error copy unless a small wording improvement is clearly
    justified
- API boundaries:
  - centralize route-shell-facing catalog/workspace-summary transport behind a planner-specific API
    module or dedicated orchestration layer
  - avoid leaving fresh direct API calls in the view

## Test plan

- Frontend unit/integration:
  - bootstrapping with resumable draft still opens the expected overview/home state
  - opening grouping and seating from overview still chooses the correct draft path
  - switching back to overview still flushes save state and blocks correctly on conflict/error
  - exit-to-origin still returns to dashboard, catalog, and catalog-fallback as currently defined
  - delete/create/update flows still keep overview selection and summary state coherent
- Live/browser:
  - open Klassrumskartan from the catalog and verify overview-first entry
  - continue into grouping and seating, then return to overview
  - verify `Avsluta` still returns to the correct origin and still falls back to catalog on missing
    trusted origin state

## Rollback plan

- Revert to the current route-shell local-ref orchestration while preserving the active
  cutover-ready UI and the existing draft workspace store behavior.

## Implementation summary

- `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.vue` is now a 217-line composition
  layer that wires the overview shell, planner shell, and planner modals instead of acting as a
  second hidden store.
- Overview/catalog state now lives in
  `frontend/apps/skriptoteket/src/views/apps/classroomPlannerOverviewStore.ts` and owns:
  - rosters/templates catalog
  - selected overview roster/template
  - overview summary + resumable-card dismiss state
  - overview-first boot/loading/error state
- Route-shell orchestration is split into planner-local modules:
  - `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerRouteShell.ts`
  - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerCatalogApi.ts`
  - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerRouteShellErrors.ts`
  - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerRouteShellSaveGuards.ts`
  - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerRouteShellExit.ts`
  - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerRouteShellWorkspace.ts`
  - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerRouteShellOverviewCrud.ts`
- The repeated flush-and-block transition behavior now goes through
  `classroomPlannerRouteShellSaveGuards.ts` instead of being duplicated inside the root view.
- The active draft Pinia store in `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts`
  remains focused on active planner workspace state only.

## Verification

- `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/classroomPlannerOverviewStore.spec.ts src/views/apps/classroomPlannerRouteShellSaveGuards.spec.ts`
- `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/classroomPlannerOverviewStore.spec.ts src/views/apps/classroomPlannerRouteShellSaveGuards.spec.ts`
- `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/ClassroomPlannerView.vue src/views/apps/useClassroomPlannerRouteShell.ts src/views/apps/classroomPlannerCatalogApi.ts src/views/apps/classroomPlannerOverviewStore.ts src/views/apps/classroomPlannerRouteShellErrors.ts src/views/apps/classroomPlannerRouteShellExit.ts src/views/apps/classroomPlannerRouteShellWorkspace.ts src/views/apps/classroomPlannerRouteShellOverviewCrud.ts`
- `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`
- `pdm run docs-validate`
- Live/browser:
  - verified overview-first entry from catalog-state navigation, entered `Grupper`, returned to
    `Översikt`, entered `Sittplatser`, and confirmed `Avsluta` returned to `/browse`
  - artifact: `.artifacts/pr-0115-live-check/pr0115-overview-exit-proof.png`
