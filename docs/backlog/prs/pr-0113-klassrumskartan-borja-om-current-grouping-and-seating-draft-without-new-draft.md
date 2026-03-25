---
type: pr
id: PR-0113
title: "Klassrumskartan: börja om current grouping and seating draft without new draft"
status: done
owners: "agents"
created: 2026-03-23
updated: 2026-03-25
stories:
  - "ST-24-03"
  - "ST-24-04"
tags: ["frontend", "ux", "workflow"]
acceptance_criteria:
  - "Given the teacher is working in `Grupper`, when they choose `Börja om`, then all current group assignments in the active draft are cleared and every student returns to `Ej grupperade` without creating a new draft."
  - "Given the teacher is working in `Sittplatser`, when they choose `Börja om`, then all current seat assignments in the active draft are cleared and every student returns to `Ej placerade` without creating a new draft."
  - "Given the teacher uses `Börja om`, when the current draft already contains work, then the app confirms the action before clearing assignments."
  - "Given `Börja om` clears the current draft, when the teacher changes their mind, then the action is reversible through the existing draft-scoped `Ångra` / `Gör om` history."
  - "Given `Börja om` is available, when the teacher keeps the same class and classroom context, then the current draft identity, current classroom selection, and existing draft continuity remain intact."
---

## Problem

The current planner only offers two imperfect ways to start over:

- manually drag every student back out of groups or seats
- create `Nytt grupputkast` or `Nytt sittschema`, which creates a new draft even when the teacher
  only wants to clear the current one

That forces draft lifecycle and reset semantics to mean the same thing, even though they are
different teacher intents.

## Goal

Add an explicit `Börja om` action in both live planner modes so teachers can clear the current
grouping or seating work in place and immediately re-place or `Slumpa` students from a clean state.

## Non-goals

- Creating another draft or changing draft continuity semantics.
- Resetting class/classroom selection.
- Resetting room-template geometry or room-builder content.
- Introducing smart-placement logic or changing the existing `Slumpa` contract.
- Clearing student planning metadata unless a later slice explicitly decides to widen the reset
  scope.

## Product decisions

- `Börja om` clears only the current mode's placement assignments:
  - `Grupper`: group assignments only
  - `Sittplatser`: seat assignments only
- The active draft stays the same draft; no new draft is created.
- The current classroom context stays unchanged.
- The action should be undoable through the existing draft history.
- Use the existing app-native confirmation dialog pattern when there is anything to clear.

## Implementation plan

- Toolbar actions:
  - add a visible `Börja om` action to the grouping toolbar
  - add a visible `Börja om` action to the seating toolbar
  - keep the action text explicit rather than icon-only
- Confirmation:
  - reuse the planner-native confirmation dialog rather than browser `confirm()`
  - only prompt when the current draft actually contains group or seat assignments
- State mutation:
  - add explicit store actions for clearing all group assignments in place
  - add explicit store actions for clearing all seat assignments in place
  - mark the draft dirty through the existing autosave path rather than creating a new lifecycle flow
- History:
  - ensure `Börja om` participates in the current backend-owned undo/redo behavior because it is an
    in-draft mutation, not a new draft lifecycle step
- UX copy:
  - make the distinction clear:
    - `Börja om` = clear this draft and continue here
    - `Nytt grupputkast` / `Nytt sittschema` = create a separate new draft

## Test plan

- Frontend unit/integration:
  - grouping `Börja om` returns all students to `Ej grupperade`
  - seating `Börja om` returns all students to `Ej placerade`
  - the action does not create a new draft or emit the new-draft events
  - confirmation only appears when there is something to clear
  - the current classroom remains selected after seating reset
  - `Ångra` restores the cleared assignments after `Börja om`
- Live/browser:
  - open a real grouping draft, make assignments, trigger `Börja om`, confirm that all students are
    back in the ungrouped list, then `Ångra`
  - open a real seating draft, place students, trigger `Börja om`, confirm that all students are
    back in `Ej placerade`, then `Ångra`

## Rollback plan

- Remove the explicit `Börja om` controls and revert to the prior draft-lifecycle-only behavior
  while keeping `Slumpa`, undo/redo, and continuity intact.
