---
type: pr
id: PR-0087
title: "Klassrumskartan: class-first landing and workspace state machine"
status: ready
owners: "agents"
created: 2026-03-21
updated: 2026-03-21
stories:
  - "ST-24-02"
tags: ["frontend"]
acceptance_criteria:
  - "The default app flow is class-first: the teacher selects a class and then lands in a class workspace instead of opening the planner directly."
  - "The top-level `resume most recent work` affordance remains available before class selection and is not folded into the class workspace."
  - "The SPA uses one clean view-state flow inside the classroom planner view rather than layering multiple page-level workspaces prematurely."
  - "Frontend tests cover class selection, top-level resume visibility, and the transition from landing view to class workspace."
---

## Problem

The current frontend is still organized around a symmetric class/classroom launcher in
`PlannerSelectionGate.vue`. That transitional shape is now explicitly wrong for the approved
product direction because it treats `Class` and `Classroom` as equal first-step objects and skips
the class workspace entirely.

## Goal

Replace the symmetric launch flow with a class-first state machine inside the existing
`ClassroomPlannerView.vue` surface:

- landing view
- class workspace
- planner

This keeps the app easy to reason about while matching the teacher's real workflow hierarchy.

## Non-goals

- Task-specific draft start rules and opt-in classroom-aware grouping flow.
- Planner exit/return semantics.
- Task-specific history drawers and presentation polish.
- Multi-route or multi-page workspace decomposition unless later work proves it necessary.

## Checklist

- [ ] Replace the current symmetric selection gate with a class-first landing flow.
- [ ] Keep `resume most recent work` at the top level before class selection.
- [ ] Add a class workspace state inside `ClassroomPlannerView.vue`.
- [ ] Load and render the class workspace summary after class selection.
- [ ] Keep classrooms manageable from the app, but demote them from equal first-step prominence.
- [ ] Add frontend tests for landing-to-class-workspace transitions and top-level resume behavior.

## Implementation plan

- Refactor the root planner view into a small state machine, for example:
  - `landing`
  - `class_workspace`
  - `planner`
- Replace the existing launch card that requires `selected class + selected classroom` with:
  - class selection as the primary interaction
  - top-level resume CTA above that interaction
- Introduce a class-workspace shell/component that consumes the backend summary from `PR-0086`.
- Keep the implementation in one view-state flow for now so the orchestration remains simple and
  local.

## Test plan

- Frontend:
  - top-level resume CTA still appears before class selection
  - selecting a class opens the class workspace, not the planner directly
  - classrooms are not presented as equal launch prerequisites on the landing flow
- Manual:
  - open Klassrumskartan, resume from the top level if desired, otherwise choose a class and
    confirm the class workspace appears before any planner surface

## Rollback plan

- Revert the new state machine and restore the symmetric landing launcher if the class workspace
  flow proves unstable, while preserving the `PR-0086` backend summary contract for reuse.

## Follow-up direction

- `PR-0088` will make the class workspace actionable by wiring task-specific draft entry and
  planner return behavior.
