---
type: pr
id: PR-0109
title: "Klassrumskartan: seating `Slumpa` fundamentals"
status: in_progress
owners: "agents"
created: 2026-03-23
updated: 2026-03-23
stories:
  - "ST-24-06"
tags: ["frontend", "backend", "integration", "ux"]
acceptance_criteria:
  - "The seating action row exposes `Slumpa` as a task-local action inside `Sittplatser`."
  - "When `Slumpa` is triggered with a selected classroom, the full active seating draft is reshuffled across the available seats."
  - "If there are more students than seats, overflow students remain unplaced instead of causing the action to fail."
  - "Seating `Slumpa` participates in the existing seating autosave and bounded undo/redo history."
  - "The slice does not introduce smart placement toggles, rule settings, or advanced teacher-facing controls."
  - "Targeted browser proof proves seating `Slumpa` on top of the current seating continuity and undo/redo surface."
---

## Problem

`EPIC-24` already approved mode-local `Slumpa`, but only grouping currently ships it. Seating still
requires fully manual reassignment even though the surrounding draft mechanics are now in place.

## Goal

Add the missing seating-side `Slumpa` as a narrow, fully random helper inside `Sittplatser`:

- use the current seating action row
- keep the change inside the active seating draft
- reuse autosave and undo/redo rather than introducing parallel state

## Non-goals

- Smart placement, tunable rules, or classroom-optimization settings.
- Any redesign of grouping `Slumpa`.
- Landing-page or overview management changes.
- New continuity-drawer semantics.

## Implementation plan

- Frontend/store:
  - add seating randomization helpers alongside the existing grouping mutation pattern
  - expose `Slumpa` in the seating action row
  - keep the action unavailable when no classroom is selected
- Backend/domain:
  - reuse existing draft patch/history mechanics if sufficient
  - only add backend contract changes if the current seating persistence path needs one
- Verification:
  - unit coverage for seating randomization behavior
  - browser proof that `Slumpa` reshuffles seating and remains undoable

## Test plan

- Frontend unit/integration:
  - seating action row renders `Slumpa` correctly
  - seating randomization updates assignments and respects missing-seat overflow
  - seating undo/redo still works after `Slumpa`
- Backend/API:
  - add focused coverage only if a backend contract seam changes
- Live/browser:
  - open `Sittplatser`
  - trigger `Slumpa`
  - verify assignments change
  - verify undo/redo around the reshuffle

## Rollback plan

- Revert seating `Slumpa` while keeping the already shipped seating continuity and undo/redo
  mechanics from `PR-0105` and `PR-0106`.

## Implementation notes (local draft)

- The slice stays frontend-local:
  - seating randomization reuses the current draft mutation/autosave path
  - no new backend endpoint or history contract was required
- `PlannerWorkspaceShell.vue` now exposes a seating `Slumpa` action that is disabled until a
  classroom with seats exists.
- Deterministic unit coverage now proves the approved full-draft reshuffle contract, including that
  an already seated student can move to a different seat.
- The live Playwright proof treats seating `Slumpa` as browser-level wiring proof:
  - the action is available in the seating toolbar
  - reshuffle integrates with autosave
  - reshuffle remains undoable/redoable
  - the exact full-reshuffle contract is enforced by unit tests rather than flaky browser-level
    randomness assertions
