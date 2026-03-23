---
type: pr
id: PR-0105
title: "Klassrumskartan: seating draft continuity and new seating-draft lifecycle"
status: done
owners: "agents"
created: 2026-03-23
updated: 2026-03-23
stories:
  - "ST-24-04"
tags: ["frontend", "backend", "ux", "integration"]
acceptance_criteria:
  - "When the teacher is inside `Sittplatser`, the seating continuity drawer can be opened from the seating action row as a secondary overlay."
  - "The seating continuity drawer presents `Aktuellt sittschema` separately from `Tidigare sittscheman`."
  - "Historic seating drafts can be reopened from the seating continuity drawer and become the active seating draft for that class."
  - "Historic seating drafts can be deleted from the seating continuity drawer with confirmation, while the active seating draft remains free of delete controls in the main workspace."
  - "A `Nytt sitschema` action exists in the seating action row and creates a fresh seating draft for the same class and currently selected classroom."
  - "If no classroom is selected, `Nytt sitschema` does not create a draft and instead routes or focuses the teacher to choose a classroom first."
  - "Creating a new seating draft demotes the previous active seating draft to class history automatically."
  - "Live browser verification proves the seating continuity drawer and `Nytt sitschema` lifecycle on the current SPA."
---

## Problem

`ST-24-04` now has a clean room builder, but the seating draft lifecycle is still incomplete:

- the class summary already exposes `active_seating_draft` and `seating_history`
- the teacher can resume the active seating draft
- but there is no teacher-facing seating continuity drawer
- there is no explicit `Nytt sitschema` action
- historic seating drafts cannot yet be reopened or deleted

That leaves seating behind grouping in one important way: grouping already has a coherent continuity
surface and explicit new-draft lifecycle, while seating still relies too much on implicit resume.

## Goal

Complete the seating continuity surface without mixing it into `Översikt`:

- keep seating continuity secondary in an overlay drawer
- add a clear `Nytt sitschema` action in the seating action row
- keep seating room-bound by requiring a selected classroom for new seating drafts
- let historic seating drafts be reopened or deleted from the drawer

## Non-goals

- Seating-specific undo/redo inside the seating workspace.
- Bounded seating in-draft history mechanics.
- Changes to room-builder geometry, zoom, visuals, labels, or seat shapes.
- Shared-file/export concepts or file-vault semantics.
- Any delete control for the active seating draft in the main seating workspace.

## Assumptions

- `Sittplatser` may still be entered without a selected classroom.
- Seating work is more room-bound than grouping work, so a new seating draft should have a stable
  classroom identity from creation time.
- The right-side overlay drawer remains the canonical continuity surface on desktop/laptop
  viewports.
- Historic draft management belongs in that drawer, not in `Översikt` and not in the active
  seating workspace chrome.

## Decisions

- Add the seating continuity trigger to the same seating action row that already contains
  seating-relevant controls.
- Add `Nytt sitschema` to that seating action row.
- `Nytt sitschema` requires a currently selected classroom:
  - if a classroom is selected, create a fresh seating draft for the same class + classroom
  - if no classroom is selected, do not create a draft and instead direct the teacher to choose a
    classroom first
- Keep the active seating draft visually separate from historic seating drafts in the drawer.
- Allow historic seating drafts to be deleted with confirmation from the drawer only.

## Options considered

### 1. New seating draft without classroom

Options:

- allow `Nytt sitschema` to create a draft without a classroom
- require a classroom for `Nytt sitschema`
- remove `Nytt sitschema` and rely only on clearing the current draft

Recommendation:

- Require a classroom for `Nytt sitschema`.

Reasoning:

- Seating drafts need a stable room identity from creation time.
- Otherwise the draft’s meaning changes later when a classroom is chosen.
- That would make history labels and continuity harder to understand.

### 2. Seating continuity surface

Options:

- keep seating continuity in `Översikt`
- add a drawer trigger inside `Sittplatser`
- add a persistent side panel for seating history

Recommendation:

- Add a drawer trigger inside `Sittplatser`.

Reasoning:

- It matches the grouping continuity model already shipped.
- It keeps continuity secondary and desktop-first.
- It avoids duplicating navigation or cluttering `Översikt`.

### 3. Historic seating-draft delete

Options:

- reopen only
- reopen and delete
- reopen/delete/archive with more file-management controls

Recommendation:

- Reopen and delete only.

Reasoning:

- It is enough management for the continuity surface.
- It stays aligned with the grouping drawer without turning the UI into a file manager.

## Implementation plan

- Backend:
  - add explicit seating-history activate/delete handlers and routes
  - add explicit `new seating draft` handler/route
  - keep the one-active-draft-per-class-per-kind invariant intact
  - demote the previous active seating draft to history when a new one is created
- Frontend store/view:
  - add `startNewSeatingDraft()`
  - add `activateSeatingHistoryDraft()`
  - add `deleteSeatingHistoryDraft()`
  - wire these through `ClassroomPlannerView.vue`
- Workspace UI:
  - extend the seating action row in `PlannerWorkspaceShell.vue`
  - add `Historik`
  - add `Nytt sitschema`
  - reuse `PlannerHistoryDrawer.vue` for seating continuity
  - present `Aktuellt sittschema` and `Tidigare sittscheman`
- Empty-classroom edge case:
  - if no classroom is selected, `Nytt sitschema` must not create a draft
  - instead surface or focus the existing classroom selector in `Sittplatser`

## Test plan

- Backend unit/API:
  - creating a new seating draft supersedes the previous active seating draft
  - activating a historic seating draft makes it active
  - deleting a historic seating draft does not affect the active seating draft
- Frontend unit/integration:
  - seating continuity drawer opens from `Sittplatser`
  - `Nytt sitschema` is available only when it makes lifecycle sense
  - `Nytt sitschema` without classroom does not create a draft
  - reopening/deleting a historic seating draft updates the workspace state cleanly
- Live/browser:
  - open `Sittplatser`
  - create or resume a seating draft with classroom selected
  - create `Nytt sitschema`
  - verify previous seating draft moves to history
  - reopen it from the drawer
  - delete a historic seating draft with confirmation

## Rollback plan

- Revert seating continuity/new-draft actions while keeping the already shipped room-builder
  ergonomics and visual improvements from `PR-0101` to `PR-0103`.

## Implementation summary (2026-03-23)

- Backend now exposes explicit seating lifecycle routes for:
  - `POST /drafts/seating/new`
  - `POST /drafts/seating/{draft_id}/activate`
  - `DELETE /drafts/seating/{draft_id}`
- Seating continuity is now teacher-facing inside `Sittplatser`, not hidden in overview summary
  data only.
- `PlannerWorkspaceShell.vue` reuses the existing right-side overlay drawer to show:
  - `Aktuellt sittschema`
  - `Tidigare sittscheman`
- `Nytt sittschema` now creates a fresh seating draft for the same class and selected classroom.
- If no classroom is selected, `Nytt sittschema` does not create a draft and instead focuses the
  classroom picker with a teacher-facing hint.
- Historic seating drafts can be reopened or deleted with confirmation from the seating drawer.
- Seating lifecycle actions are guarded against duplicate in-flight interaction, and the drawer
  disables row actions while a seating transition is still running.
- Live browser proof is now dedicated to `PR-0105` via
  `scripts/playwright_pr_0105_seating_continuity.py`, proving:
  - classroom-required `Nytt sittschema`
  - a new seating draft clears seat assignments in the same room
  - reopening historic seating restores the earlier seat placement
  - deleting the remaining historic seating draft keeps the active draft intact
