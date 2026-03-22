---
type: pr
id: PR-0088
title: "Klassrumskartan: task entry and planner return semantics"
status: done
owners: "agents"
created: 2026-03-21
updated: 2026-03-22
stories:
  - "ST-24-02"
tags: ["frontend", "api"]
acceptance_criteria:
  - "Inside a class workspace, the teacher explicitly chooses `Grupper` or `Sittplatser` rather than having one task auto-foregrounded."
  - "Starting seating work opens the seating workspace directly, and classroom selection stays inside that workspace."
  - "Starting grouping work is classroom-agnostic by default, with a clear opt-in control for classroom-aware grouping."
  - "Leaving the planner returns to the class workspace without abandoning the active draft by default."
  - "Discard remains explicit and separate from normal planner exit."
---

## Problem

Even after a class workspace exists, the current planner entry and exit semantics are still
transitional:

- start planning still assumes room choice too early in the seating path
- grouping without classroom is not yet a first-class teacher flow
- leaving the planner currently abandons the draft instead of returning to the class workspace

That keeps the app closer to the old launcher than to the approved class-first model.

## Goal

Wire the actual task-specific behavior of the class workspace so the teacher can:

- choose grouping or seating explicitly each time
- start grouping without a classroom by default
- opt into classroom-aware grouping when desired
- start seating directly, then choose or change classroom inside the seating workspace
- leave the planner back to the class workspace without discarding active work

## Non-goals

- Task-specific history drawers and final workspace polish.
- Saved grouping / saved seating artifact flows from later stories.
- Split task-specific `Slumpa` controls from `ST-24-03` / `ST-24-04`.

## Checklist

- [x] Add explicit task choice inside the class workspace.
- [x] Make seating entry require classroom selection.
- [x] Make grouping entry default classroom-agnostic with a visible opt-in classroom-aware toggle.
- [x] Reuse `POST /drafts/resolve` with explicit `draft_kind` and optional `template_id` rather
      than inventing parallel draft creation semantics.
- [x] Change normal planner exit from `abandon` to `return to class workspace`.
- [x] Keep explicit draft discard available as a separate action.
- [x] Add frontend tests for task selection, start-flow semantics, and planner return behavior.

## Implementation plan

- Extend the class workspace UI with two explicit task entry actions:
  - `Grupper`
  - `Sittplatser`
- For grouping:
  - default to `template_id = null`
  - offer a visible opt-in control for classroom-aware grouping
- For seating:
  - allow `resolveDraft(..., "seating")` with `template_id = null`
  - keep classroom selection and later classroom switching inside the seating workspace itself
- Refactor the planner shell exit action so it navigates back to the class workspace without
  calling `abandonDraft()` by default.
- Keep explicit draft discard outside the planner shell so `Avsluta` can mean “leave the class
  workspace” rather than “abandon the draft”.

## Test plan

- Frontend:
  - grouping can start without classroom
  - grouping classroom-aware opt-in is visible and explicit
  - seating opens directly and supports classroom selection/switching inside the seating workspace
  - normal planner exit keeps active work resumable and returns the teacher to the landing flow
  - discard still abandons the active draft intentionally from the landing CTA
- Manual:
  - choose a class, start grouping without classroom, leave the class view, and confirm the draft
    remains resumable from the landing surface
  - choose seating, open the workspace without a room, then assign or switch classroom inside the
    seating workspace

## Rollback plan

- Revert the new task-entry and planner-return semantics if they create ambiguous draft state, but
  do not fall back to implicit discard-on-leave without an explicit documented decision.

## Follow-up direction

- `PR-0089` adds the secondary history surfaces and workspace polish once the core task-entry flow
  is stable.
