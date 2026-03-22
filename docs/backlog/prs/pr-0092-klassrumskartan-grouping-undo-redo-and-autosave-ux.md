---
type: pr
id: PR-0092
title: "Klassrumskartan: grouping undo-redo and autosave UX"
status: ready
owners: "agents"
created: 2026-03-22
updated: 2026-03-22
stories:
  - "ST-24-03"
tags: ["frontend", "backend", "api"]
acceptance_criteria:
  - "The teacher can undo or redo recent grouping steps directly inside the grouping workspace without being exposed to separate saved-item jargon."
  - "Undo and redo operate on meaningful grouping actions such as move, swap, add/remove group, rename group, and randomize."
  - "Autosave feedback remains compact and clearly distinct from undo/redo controls."
  - "The grouping workspace respects the bounded recent-history limit and communicates when undo or redo is no longer available."
  - "Frontend and backend tests cover undo, redo, autosave feedback, and recent-history bounds."
---

## Problem

Even with a bounded grouping draft-history contract available, the teacher still needs a clean,
workspace-first way to use it:

- undo the last change
- redo a reverted change
- understand that work is autosaved
- avoid thinking in terms of separate saved drafts or artifact versions

If that experience is surfaced using technical lifecycle language, the app will again feel much
more complex than the current document-like workflow requires.

## Goal

Add the teacher-facing grouping workspace controls for undo/redo and autosave:

- undo and redo are simple workspace actions
- autosave remains compact status, not a big save panel
- recent history is visible through controls, not through a pile of saved items

## Non-goals

- File-vault projection/export delivery.
- Seating undo/redo flows.
- Exposing bounded recent history as a major class-level archive.
- Advanced compare/version browser UX.

## Checklist

- [ ] Add undo and redo controls to the grouping workspace.
- [ ] Keep autosave status compact and visually distinct from undo/redo.
- [ ] Record meaningful grouping actions into recent history.
- [ ] Respect the configured recent-history depth in the UI.
- [ ] Add frontend/backend tests for undo, redo, and autosave feedback behavior.

## Implementation plan

- Extend the grouping workspace controls with explicit undo/redo actions.
- Treat these actions as workspace editing controls rather than as navigation to older saved items.
- Keep autosave status compact and low-noise so it does not compete with the actual grouping board.
- Make availability explicit:
  - undo disabled when no earlier step exists
  - redo disabled when no later step exists
- Ensure actions like `Slumpa`, move, swap, rename, and add/remove group are treated as meaningful
  recent-history steps.

## Test plan

- Backend/API:
  - undo current grouping step
  - redo reverted grouping step
- Frontend:
  - undo/redo controls enable and disable correctly
  - autosave feedback stays compact
  - history bounds are respected
- Manual:
  - create a grouping, move students, rename groups, randomize, undo several times, redo several
    times, and confirm the flow remains understandable without any separate saved-item model

## Rollback plan

- Revert the grouping undo/redo UI if it confuses autosave with navigation or destabilizes
  grouping edits, while preserving the backend draft-history contract for later reintroduction.

## Follow-up direction

- `PR-0093` tightens grouping draft continuity and secondary class-history behavior so new-draft
  creation, resume, and prior draft browsing stay clear without competing with undo/redo.
