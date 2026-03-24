---
type: pr
id: PR-0114
title: "Klassrumskartan: planner shell decomposition and shared workspace UI primitives"
status: done
owners: "agents"
created: 2026-03-24
updated: 2026-03-24
stories: []
tags: ["frontend", "refactor", "srp", "ux", "performance"]
acceptance_criteria:
  - "`frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue` is reduced below 500 LOC via cohesive decomposition into a thin shell plus task-specific workspace panes."
  - "`frontend/apps/skriptoteket/src/views/apps/components/PlannerClassWorkspace.vue` is reduced below 500 LOC via cohesive decomposition into overview-focused subcomponents."
  - "A shared planner student-pool component is introduced so grouping and seating stop duplicating the same unassigned-student list structure and interaction model."
  - "A shared planner action-bar / toolbar composition is introduced for task-local actions where it reduces duplicated shell logic without flattening real task differences."
  - "The visible teacher workflow remains unchanged: `Översikt`, `Grupper`, and `Sittplatser` still behave the same, with no new feature semantics introduced by the refactor."
  - "Focused frontend tests pass for the extracted planner shell/components, and a live browser check confirms the planner still renders and transitions correctly on the local SPA."
---

## Problem

Klassrumskartan now works well enough that the main frontend debt is structural rather than product
direction. Two components are carrying too many responsibilities:

- `PlannerWorkspaceShell.vue` mixes shell chrome, mode-local UI state, seating-specific setup,
  history-drawer orchestration, metadata-drawer orchestration, reset-dialog orchestration, and
  task action bars.
- `PlannerClassWorkspace.vue` mixes top-level overview shell, resumable draft cards, class
  management, classroom management, and compact room-preview rendering.

At the same time, grouping and seating still duplicate adjacent UI concepts such as the unassigned
student pool and action-row structure.

## Goal

Split the planner shell and overview shell into smaller, clearer components before export/checkpoint
work begins, so future features can land without growing the current large files again.

## Non-goals

- Changing planner behavior, copy hierarchy, or current workflow semantics.
- Reworking the root route-shell orchestration in `ClassroomPlannerView.vue`.
- Reworking the room-template editor modal internals.
- Introducing export/checkpoint actions in this PR.

## Implementation plan

- Planner workspace decomposition:
  - extract a thin shell from `PlannerWorkspaceShell.vue`
  - move grouping-specific surface composition into a dedicated grouping workspace pane
  - move seating-specific surface composition into a dedicated seating workspace pane
  - keep history drawer / metadata drawer wiring explicit and easy to follow
- Overview decomposition:
  - extract resumable draft cards into a dedicated overview-resume component
  - extract the class panel into a dedicated roster overview panel
  - extract the classroom panel into a dedicated template overview panel
  - keep `PlannerClassWorkspace.vue` focused on overview composition only
- Shared UI primitives:
  - introduce a shared planner student-pool component for `Ej grupperade` / `Ej placerade`
  - introduce a shared planner action-bar composition where it genuinely removes duplicated shell
    structure
  - preserve task-specific buttons and semantics rather than forcing grouping and seating into one
    fake generic abstraction
- Boundaries:
  - leaf UI components stay rendering-focused
  - store orchestration remains in the existing store/composition layer for now
  - no direct API behavior changes are introduced in this PR

## Implementation summary (2026-03-24)

- Implemented locally and verified on the canonical local SPA.
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue` is now a
  340-line shell that keeps top-panel state, current-mode routing, and drawer wiring while
  delegating the task surfaces to:
  - `PlannerGroupingWorkspacePane.vue`
  - `PlannerSeatingWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerClassWorkspace.vue` is now a
  206-line overview composer that delegates overview content to:
  - `PlannerOverviewResumeCards.vue`
  - `PlannerRosterOverviewPanel.vue`
  - `PlannerTemplateOverviewPanel.vue`
- Added local shared planner primitives without broadening the surface into fake-generic UI:
  - `PlannerStudentPool.vue` for `Ej grupperade` / `Ej placerade`
  - `PlannerWorkspaceActionBar.vue` for the shared task action-row wrapper only
- Narrowed the existing task surfaces instead of deleting them:
  - `GroupBoard.vue` now focuses on ordered group-card composition
  - `RoomCanvas.vue` now focuses on the room canvas only
- Focused specs were updated so the shell still proves task-local workflow behavior while the
  simplified `GroupBoard.spec.ts` now asserts the narrower board boundary.

## Verification (2026-03-24)

- `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/ClassroomPlannerView.spec.ts`
- `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/components/PlannerWorkspaceShell.vue src/views/apps/components/PlannerClassWorkspace.vue src/views/apps/components/GroupBoard.vue src/views/apps/components/RoomCanvas.vue`
- `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`
- `pdm run docs-validate`
- Extra lint sweep on the new planner subcomponents passed.
- Live local browser check passed against `http://127.0.0.1:5173/apps/classroom.group-seating-studio`:
  - `Översikt` still rendered class/classroom panels and resumable cards
  - `Grupper` still rendered the grouping student pool and accepted a small in-workspace interaction
  - returning to `Översikt` still restored the overview shell
  - `Sittplatser` still rendered the classroom setup row and seating action row
  - artifact: `.artifacts/pr-0114-live-check/pr0114-overview-groups-seating.png`

## Test plan

- Frontend unit/integration:
  - extracted grouping workspace pane still renders grouping controls, reset, undo/redo, and
    history entry points correctly
  - extracted seating workspace pane still renders classroom selection, reset, `Slumpa`,
    undo/redo, and overflow actions correctly
  - extracted overview panels still render roster/classroom selection and resumable draft cards
    correctly
  - shared student-pool component still supports selection, drag start, and empty-state rendering
- Live/browser:
  - open Klassrumskartan on the local SPA
  - verify `Översikt` renders class/classroom management and resumable draft cards
  - enter `Grupper`, perform a small interaction, and return
  - enter `Sittplatser`, verify the seating setup/action row still behaves correctly

## Rollback plan

- Revert to the current monolithic planner-shell and overview-shell components while preserving the
  current cutover behavior and task-local workflow semantics.
