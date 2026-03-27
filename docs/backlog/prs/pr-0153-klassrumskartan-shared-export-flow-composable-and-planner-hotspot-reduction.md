---
type: pr
id: PR-0153
title: "Klassrumskartan: shared export-flow composable and planner hotspot reduction"
status: done
owners: "agents"
created: 2026-03-27
updated: 2026-03-27
stories: []
tags: ["frontend", "refactor", "srp", "klassrumskartan", "export"]
dependencies:
  - "PR-0120"
  - "PR-0139"
  - "PR-0142"
  - "PR-0152"
acceptance_criteria:
  - "`frontend/apps/skriptoteket/src/views/apps/useSeatingExportFlow.ts` is reduced below 200 LOC by moving the shared export state machine into a dedicated planner export-flow module."
  - "`frontend/apps/skriptoteket/src/views/apps/useGroupingExportFlow.ts` is reduced below 200 LOC by reusing that shared export-flow module instead of carrying a second near-duplicate state machine."
  - "The shared export-flow module preserves the current teacher-visible semantics: pending-save flush before export, bounded foreground polling with background recovery, draft-scoped reload restoration, and explicit later-download affordances."
  - "Route-shell call sites and frontend flow specs keep the same public API and teacher copy unless the PR doc explicitly records an approved wording change."
  - "Focused frontend verification and a live planner smoke are re-run and recorded in `.agents/handoff.md`."
---

## Problem

`useSeatingExportFlow.ts` and `useGroupingExportFlow.ts` now sit near the top of the remaining
planner-local hotspot list. They implement the same state machine with only a few real differences:

- draft kind (`seating` vs `grouping`)
- API entry points
- teacher-facing copy and fallback filenames
- locked default export option

Keeping both copies inflates review surface, makes future export fixes easy to miss in one lane, and
pushes the planner cleanup effort into repeated work instead of real composition improvements.

## Goal

Extract one shared export-flow composable/factory for the planner route shell and keep seating and
grouping as thin adapters that inject their own API wiring and wording.

## Non-goals

- Changing export contract behavior or route-shell semantics.
- Reworking the presentational export components.
- Broad repo-wide hotspot cleanup outside the current planner lane.

## Implementation plan

1. Add a shared planner export-flow module that owns:
   - active-draft scoping
   - pending-save flush before export
   - bounded polling + timeout-to-background recovery
   - reload restoration of recoverable export jobs
   - browser download triggering
2. Keep seating and grouping wrappers thin:
   - inject API helpers from `classroomPlannerExportApi.ts`
   - inject teacher-facing status/error copy and fallback filenames
   - preserve the current wrapper return shape for `useClassroomPlannerRouteShell.ts`
3. Re-run focused export-flow/frontend verification and the live planner smoke.

## Implementation Summary

- Added `frontend/apps/skriptoteket/src/views/apps/classroomPlannerExportFlow.ts` as the shared
  planner export state machine for scoped create/poll/recovery/download behavior.
- Reduced both `useSeatingExportFlow.ts` and `useGroupingExportFlow.ts` to thin adapters that only
  supply draft-kind, API helpers, fallback filenames, and teacher-facing copy.
- Preserved the public wrapper API so `useClassroomPlannerRouteShell.ts` and existing specs did not
  need contract changes.

## Test plan

- `pdm run fe-test -- --run src/views/apps/useSeatingExportFlow.spec.ts src/views/apps/useGroupingExportFlow.spec.ts src/views/apps/classroomPlannerRouteShellSaveGuards.spec.ts src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts`
- `pdm run fe-type-check`
- `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173`

## Rollback plan

- Remove the shared export-flow module and restore the previous seating/grouping wrappers if the
  abstraction proves to hide meaningful behavior differences.
- Do not keep a partial split where one export lane uses the shared state machine and the other
  keeps a forked copy.
