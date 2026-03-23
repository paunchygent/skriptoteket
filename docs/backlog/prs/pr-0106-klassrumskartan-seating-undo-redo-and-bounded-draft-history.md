---
type: pr
id: PR-0106
title: "Klassrumskartan: seating undo/redo and bounded draft history"
status: ready
owners: "agents"
created: 2026-03-23
updated: 2026-03-23
stories:
  - "ST-24-04"
tags: ["frontend", "backend", "integration", "ux"]
acceptance_criteria:
  - "The seating action row exposes `Historik`, `Ångra`, `Gör om`, `Nytt sitschema`, and `Redigera klassrum` in a cohesive desktop-first control strip."
  - "When the teacher changes the active seating draft, `Ångra` and `Gör om` step backward and forward through bounded seating draft history inside the seating workspace."
  - "Seating undo/redo uses backend-owned history state after flushing pending autosave first, rather than introducing a parallel client-only history model."
  - "Seating undo/redo applies to seating draft state only and does not include room-template editing inside `CreateRoomTemplateModal.vue`."
  - "The seating draft-history depth remains bounded and configurable rather than growing without limit."
  - "Historic seating drafts remain secondary in the overlay continuity drawer and are not confused with undo/redo steps."
  - "Live browser verification proves seating undo/redo and continuity on the current SPA."
---

## Problem

After `PR-0101` through `PR-0103`, seating has a much better editor, but it still lacks the most
important draft mechanics that grouping already has:

- no seating-specific `Ångra` / `Gör om`
- no bounded in-draft seating history
- no consistent backend/frontend contract for seating undo/redo

That leaves `ST-24-04` only partially fulfilled and creates an unnecessary asymmetry between
grouping and seating.

## Goal

Finish the seating draft mechanics by extending the already shipped grouping history model where it
genuinely applies:

- bounded in-draft history
- autosave-flush-first undo/redo
- backend-owned truth for `can_undo` / `can_redo`
- clear separation between continuity/history drawer and in-draft undo/redo

## Non-goals

- Room-builder geometry, object visuals, zoom, labels, or seat rendering.
- Treating room-template editing as part of seating draft undo/redo.
- Introducing a file-vault/save-as/archive model for seating drafts.
- Renaming, tagging, or archiving historical seating drafts beyond reopen/delete.
- Reworking grouping history unless a small shared internal refactor is necessary.

## Assumptions

- `PR-0105` has already added the seating continuity drawer and `Nytt sitschema` lifecycle.
- The current grouping implementation is the correct baseline for how draft-local history should
  behave.
- Seating draft history and continuity are different layers:
  - continuity drawer = active vs historical drafts
  - undo/redo = bounded history inside the current active draft
- Room templates remain shared assets, not seating-draft snapshots.

## Decisions

- Generalize the current draft-history mechanism rather than invent a separate seating-only
  mechanism.
- Keep room-template edits outside seating undo/redo.
- Keep outward seating routes/handlers explicit enough to stay readable, even if shared internals
  are generalized.
- Reuse the same seating action row for:
  - `Historik`
  - `Ångra`
  - `Gör om`
  - `Nytt sitschema`
  - `Redigera klassrum`

## Options considered

### 1. Seating history implementation model

Options:

- build a separate seating-only history mechanism
- generalize the current draft-history mechanism to both draft kinds

Recommendation:

- Generalize the current draft-history mechanism to both draft kinds.

Reasoning:

- The semantics are the same:
  - bounded history
  - autosave flush first
  - backend-owned truth
- A second mechanism would duplicate logic and create more drift.

### 2. Boundary between seating draft and classroom asset

Options:

- include room-template editing in seating undo/redo
- keep room-template editing outside seating undo/redo

Recommendation:

- Keep room-template editing outside seating undo/redo.

Reasoning:

- Seating draft state and shared classroom/template state are different ownership layers.
- Teachers expect seat placements to undo inside the draft they are editing.
- Shared classroom edits belong to the room-template editing workflow, not to a class-scoped
  seating draft timeline.

### 3. Backend structure

Options:

- add seating-specific handlers/routes mirroring grouping for everything
- fully refactor all history handlers/routes to one generic `draft_kind` abstraction
- keep outward seating handlers/routes explicit, with shared internals where the logic is truly identical

Recommendation:

- Keep outward seating handlers/routes explicit, with shared internals where the logic is truly
  identical.

Reasoning:

- This keeps the code honest and easier to read.
- It avoids speculative abstractions while still reducing duplication where the behavior is
  actually shared.

## Implementation plan

- Backend/domain:
  - generalize the bounded history contract so seating drafts can persist and step through history
    like grouping drafts
  - keep the draft-history depth configurable and shared across draft kinds where practical
  - expose explicit seating undo/redo handlers/routes
- Frontend store:
  - extend `useClassroomState.ts` so `canUndo` / `canRedo` become draft-kind-aware rather than
    grouping-only
  - preserve the existing flush-pending-autosave-first orchestration pattern
  - rehydrate seating workspaces from backend `history_status` after undo/redo
- Frontend workspace:
  - extend the seating action row in `PlannerWorkspaceShell.vue`
  - add `Ångra` and `Gör om` beside the already planned `Historik`, `Nytt sitschema`, and
    `Redigera klassrum`
  - keep undo/redo unavailable while the workspace is busy or while no seating history exists
- History boundaries:
  - ensure continuity drawer items are still draft-level history
  - ensure undo/redo steps are never rendered as drawer items
  - ensure room-template edits remain outside seating undo/redo

## Test plan

- Backend unit/API:
  - seating patches push bounded history snapshots
  - seating undo rejects invalid states and non-seating misuse as expected
  - seating redo rehydrates the current draft workspace correctly
- Frontend unit/integration:
  - seating `canUndo` / `canRedo` follow backend `history_status`
  - pending seating autosave flushes before undo/redo
  - room-template edits are not part of seating undo/redo
  - the seating action row renders and disables controls correctly
- Live/browser:
  - open seating for a class + classroom
  - place/move seats or assignments
  - wait through autosave and verify `Ångra` remains available afterward
  - undo and redo seating changes
  - verify the continuity drawer still represents only draft-level history

## Rollback plan

- Revert seating undo/redo and bounded history changes while keeping the already shipped continuity
  drawer/new seating-draft lifecycle from `PR-0105` and the room-builder improvements from
  `PR-0101` to `PR-0103`.
