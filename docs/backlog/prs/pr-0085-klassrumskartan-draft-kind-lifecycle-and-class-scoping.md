---
type: pr
id: PR-0085
title: "Klassrumskartan: draft-kind lifecycle and class-scoped invariants"
status: done
owners: "agents"
created: 2026-03-21
updated: 2026-03-21
stories:
  - "ST-24-05"
  - "ST-24-02"
adrs:
  - "ADR-0072"
tags: ["backend", "persistence", "api"]
acceptance_criteria:
  - "The planner no longer enforces one active draft per owner; instead draft lifecycle semantics align with one active draft per class per draft kind."
  - "Grouping and seating are represented as separate draft kinds in the active contract."
  - "The lifecycle semantics support the later class-first workspace without leaving behind the superseded owner-global invariant."
---

## Problem

Even after other old planner contracts are removed, the draft lifecycle still points developers in
the wrong direction if it remains owner-global and planner-wide. The approved model is class-first
with separate grouping and seating work, not one owner-level mutable planner draft.

## Goal

Replace the owner-global active-draft invariant with class-scoped draft kinds so the codebase is
structurally aligned before the class-first workspace story ships.

## Non-goals

- Final class workspace UI
- Saved grouping/seating history UI
- Smart placement logic

## Checklist

- [x] Introduce explicit planner draft kinds for grouping and seating.
- [x] Make seating drafts classroom-bound and grouping drafts classroom-optional in the active contract.
- [x] Replace the owner-global single-active-draft invariant with one active draft per class per draft kind.
- [x] Update resolve/resume semantics so starting a new draft of the same class and kind demotes the previous active draft of that same class and kind to history.
- [x] Remove owner-global lifecycle locks, repository methods, schema constraints, and tests that encode the superseded invariant.
- [x] Update delete guards and resumable-draft logic so they reason about class-scoped draft kinds instead of one owner-global active draft.
- [x] Add migration coverage for the new invariant and lifecycle transition behavior.

## Implementation plan

- Add draft kind and class-scoped lifecycle semantics to the domain and persistence model.
- Replace owner-global repository queries and constraints with class-and-kind scoped equivalents.
- Update resolve/resume/delete guard behavior around the new invariant.
- Leave the final class-first UI consumption to `ST-24-02`, but ensure the backend contract is ready for it.

## Test plan

- Lifecycle handler tests for resolve/resume/demotion behavior
- API tests for class-and-kind scoped draft flows
- Migration tests to latest head and repeat upgrade
- Manual live check that multiple classes can each hold active work without conflicting

## Rollback plan

- Revert the invariant change if it destabilizes draft lifecycle behavior, then re-land it in narrower schema-plus-handler slices without restoring the owner-global contract long-term.
