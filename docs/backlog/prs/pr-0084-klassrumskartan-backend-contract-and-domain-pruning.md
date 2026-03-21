---
type: pr
id: PR-0084
title: "Klassrumskartan: backend contract pruning and domain cleanup"
status: done
owners: "agents"
created: 2026-03-21
updated: 2026-03-21
stories:
  - "ST-24-05"
adrs:
  - "ADR-0071"
  - "ADR-0072"
tags: ["backend", "api", "domain", "persistence"]
acceptance_criteria:
  - "The classroom planner backend no longer exposes superseded lesson-mode, validation, suggestions, finalize, snapshot, or whole-workspace randomize contracts."
  - "Removed planner concepts are deleted from the active domain, DI, router, repository seams, and persistence model rather than hidden behind unused code paths."
  - "The remaining backend contract describes approved fundamentals only."
---

## Problem

The classroom planner backend still publicly promises the superseded solver-first direction:

- lesson-mode bootstrap
- whole-workspace draft patching
- validate/suggestions/apply/finalize/snapshots
- whole-workspace randomize
- planning-profile and pair-constraint domain concepts

That is now the wrong product contract.

## Goal

Prune the planner backend so its public API, domain vocabulary, DI wiring, and persistence seams
match the approved fundamentals direction instead of preserving the abandoned solver-era model.

## Non-goals

- Final class-first UI flow
- Saved grouping/seating artifact implementation
- Full draft-kind lifecycle replacement

## Checklist

- [x] Remove lesson-mode bootstrap metadata from the classroom planner public contract if it is no longer part of the approved workflow.
- [x] Remove superseded planner endpoints for validation, suggestions, suggestion apply, finalize, snapshots, and whole-workspace randomize.
- [x] Delete the corresponding handlers, DTOs, DI providers, and router wiring instead of leaving unused registration behind.
- [x] Remove superseded planner concepts from the active domain model, including planning-profile, pair-constraint, suggestion, snapshot, and suggestion-engine metadata types that no longer belong to the approved fundamentals contract.
- [x] Remove obsolete persistence seams, ORM models, and database columns/tables tied only to removed planner concepts, with a forward migration that leaves no dead contract surface.
- [x] Update backend tests so they cover the reduced fundamentals contract rather than preserving removed APIs.

## Implementation plan

- Trim the router/API surface first so the public contract becomes explicit.
- Prune handler exports and DI next so removed endpoints cannot be reached internally.
- Reduce domain and repository contracts to fundamentals-only planner semantics.
- Ship a migration that removes obsolete planner persistence artifacts cleanly.

## Test plan

- Backend API tests
- Domain/application tests for remaining fundamentals handlers
- Migration test to latest head and no-op re-upgrade
- `pdm run pytest ...`
- `pdm run ruff check ...`

## Rollback plan

- Revert the pruning PR if it breaks the current fundamentals workflow, then re-land it in narrower backend slices without reintroducing deprecated routes or domain types.
