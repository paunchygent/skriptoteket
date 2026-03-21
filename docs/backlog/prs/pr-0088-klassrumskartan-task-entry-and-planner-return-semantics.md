---
type: pr
id: PR-0088
title: "Klassrumskartan: task entry and planner return semantics"
status: ready
owners: "agents"
created: 2026-03-21
updated: 2026-03-21
stories:
  - "ST-24-02"
tags: ["frontend", "api"]
acceptance_criteria:
  - "Inside a class workspace, the teacher explicitly chooses `Grupper` or `Sittplatser` rather than having one task auto-foregrounded."
  - "Starting seating work requires classroom selection before the seating planner opens."
  - "Starting grouping work is classroom-agnostic by default, with a clear opt-in control for classroom-aware grouping."
  - "Leaving the planner returns to the class workspace without abandoning the active draft by default."
  - "Discard remains explicit and separate from normal planner exit."
---

## Problem

Even after a class workspace exists, the current planner entry and exit semantics are still
transitional:

- start planning is effectively a seating-first launch
- grouping without classroom is not yet a first-class teacher flow
- leaving the planner currently abandons the draft instead of returning to the class workspace

That keeps the app closer to the old launcher than to the approved class-first model.

## Goal

Wire the actual task-specific behavior of the class workspace so the teacher can:

- choose grouping or seating explicitly each time
- start grouping without a classroom by default
- opt into classroom-aware grouping when desired
- start seating only after choosing a classroom
- leave the planner back to the class workspace without discarding active work

## Non-goals

- Task-specific history drawers and final workspace polish.
- Saved grouping / saved seating artifact flows from later stories.
- Split task-specific `Slumpa` controls from `ST-24-03` / `ST-24-04`.

## Checklist

- [ ] Add explicit task choice inside the class workspace.
- [ ] Make seating entry require classroom selection.
- [ ] Make grouping entry default classroom-agnostic with a visible opt-in classroom-aware toggle.
- [ ] Reuse `POST /drafts/resolve` with explicit `draft_kind` and optional `template_id` rather
      than inventing parallel draft creation semantics.
- [ ] Change normal planner exit from `abandon` to `return to class workspace`.
- [ ] Keep explicit draft discard available as a separate action.
- [ ] Add frontend tests for task selection, start-flow semantics, and planner return behavior.

## Implementation plan

- Extend the class workspace UI with two explicit task entry actions:
  - `Grupper`
  - `Sittplatser`
- For grouping:
  - default to `template_id = null`
  - offer a visible opt-in control for classroom-aware grouping
- For seating:
  - require classroom selection before `resolveDraft(..., "seating")`
- Refactor the planner shell exit action so it navigates back to the class workspace without
  calling `abandonDraft()` by default.
- Add a separate explicit discard path in the class workspace or planner shell that still calls the
  abandon flow intentionally.

## Test plan

- Frontend:
  - grouping can start without classroom
  - grouping classroom-aware opt-in is visible and explicit
  - seating cannot start without classroom selection
  - normal planner exit returns to class workspace while preserving active work
  - discard still abandons the active draft intentionally
- Manual:
  - choose a class, start grouping without classroom, leave planner, and confirm the draft remains
    resumable from the class workspace
  - choose seating, require classroom, and confirm the planner only opens after room selection

## Rollback plan

- Revert the new task-entry and planner-return semantics if they create ambiguous draft state, but
  do not fall back to implicit discard-on-leave without an explicit documented decision.

## Follow-up direction

- `PR-0089` adds the secondary history surfaces and workspace polish once the core task-entry flow
  is stable.
