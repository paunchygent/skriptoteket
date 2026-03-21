---
type: pr
id: PR-0083
title: "Klassrumskartan: frontend store and types contract cleanup"
status: done
owners: "agents"
created: 2026-03-21
updated: 2026-03-21
stories:
  - "ST-24-05"
tags: ["frontend", "state", "api"]
acceptance_criteria:
  - "The frontend planner store and TypeScript contract no longer encode superseded lesson-mode, solver-profile, suggestion, snapshot, or whole-workspace planner semantics."
  - "Only approved fundamentals remain in active frontend state and DTOs."
  - "Removed concepts are deleted cleanly rather than left behind as aliases, optional leftovers, or dormant helper code."
---

## Problem

The live frontend state contract still carries old-direction concepts in the store, mutation helpers,
tests, and TypeScript DTOs. Even where the UI no longer foregrounds those concepts, they still
shape the codebase and encourage future reuse of superseded planner semantics.

## Goal

Reduce the frontend planner contract to the approved fundamentals so later class-first workspace,
grouping, and seating work do not inherit solver-era baggage.

## Non-goals

- Backend/domain/API cleanup
- Draft-kind persistence refactor
- Saved grouping/seating artifact implementation

## Checklist

- [x] Remove `LessonMode`, `PlanningProfile`, `PairConstraint`, `SuggestionPlan`, `ArrangementSnapshot`, `SuggestionEngineMetadata`, and related planner-only label helpers from the active frontend planner contract.
- [x] Reduce `PlanDraft`, workspace DTOs, and related request/response typing to approved fundamentals only.
- [x] Remove advanced planner state, methods, and autosave payload fields from `useClassroomState.ts`.
- [x] Simplify or split `classroomPlannerStoreMutations.ts` so it no longer owns removed planner concepts.
- [x] Delete tests that preserve removed advanced planner state instead of converting them into compatibility coverage.
- [x] Update remaining tests to assert the reduced fundamentals-first contract.

## Implementation plan

- Start with the shared TypeScript contract and work inward from the current UI usage.
- Remove advanced store fields and methods in one pass so the planner no longer advertises dead capabilities.
- Delete any helper or test code that only exists to support removed planner concepts.

## Test plan

- Frontend store/unit tests
- `pnpm -C frontend --filter @skriptoteket/spa exec vitest run ...`
- `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`
- `pnpm -C frontend --filter @skriptoteket/spa build`

## Rollback plan

- Revert the store/type cleanup if it breaks the shipped fundamentals UI, then re-land it in smaller removals without restoring deprecated planner DTOs or store methods.
