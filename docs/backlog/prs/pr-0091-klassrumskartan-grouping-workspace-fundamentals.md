---
type: pr
id: PR-0091
title: "Klassrumskartan: grouping workspace fundamentals"
status: done
owners: "agents"
created: 2026-03-22
updated: 2026-03-22
stories:
  - "ST-24-03"
tags: ["frontend"]
acceptance_criteria:
  - "Grouping operates as a standalone class task: manual grouping, group count changes, and group renaming work without seating leaking into the flow."
  - "Grouping gets its own `Slumpa` action that creates a first draft of groups without randomizing seats."
  - "A new grouping draft starts blank and can be created explicitly from the grouping workspace."
  - "Default group names stay positional (`Grupp 1`, `Grupp 2`, ...) and renumber automatically on reorder/delete until a teacher sets a custom name."
  - "Large groups render without clipping student cards inside the group panel."
  - "Group-card up/down controls update a meaningful persisted order that later export flows can trust."
  - "Frontend tests cover grouping randomize behavior, blank new-draft semantics, and group-panel rendering behavior."
---

## Problem

The class-first workspace from `ST-24-02` can open grouping cleanly, but grouping still lacks the
teacher fundamentals that make it feel complete:

- no grouping-specific `Slumpa`
- no explicit blank `Nytt grupputkast`
- group-card layout still risks clipping when groups get larger

Until those basics are in place, saved-grouping work would rest on an incomplete workspace.

## Goal

Make the grouping workspace fully usable as a standalone teacher task before layering in the
saved-grouping flows:

- manual control stays primary
- `Slumpa` becomes a grouping-only starting point
- `Nytt grupputkast` creates a blank new grouping draft
- group panels grow or lay themselves out cleanly for larger groups

## Non-goals

- Draft-history persistence and undo/redo UI.
- Durable export/file-vault artifact flows.
- Seating randomization or seating save flows.
- Export formatting.

## Checklist

- [x] Add grouping-only `Slumpa` to the focused grouping workspace.
- [x] Preserve current group count and teacher-defined group names when `Slumpa` runs.
- [x] Add explicit `Nytt grupputkast` that starts blank rather than copying the current grouping.
- [x] Keep manual drag/drop and group edits first-class after randomization.
- [x] Keep default group names positional until a teacher enters a custom name.
- [x] Fix large-group layout so student cards do not clip or overflow awkwardly.
- [x] Ensure group reorder controls update meaningful persisted `sort_order` values.
- [x] Add frontend tests for grouping fundamentals and layout behavior.

## Implementation plan

- Extend the grouping workspace controls with:
  - `Slumpa`
  - `Nytt grupputkast`
- Implement grouping randomize behavior against the current class roster and current group count
  only; do not infer seat assignments or classroom-only behavior.
- Keep group names stable when randomizing so teacher-defined structure survives.
- Treat untouched default names as system-managed labels that renumber with visible order, while
  custom teacher-entered names remain fixed.
- Refine `GroupBoard.vue` / `GroupCard.vue` layout so larger groups expand or reflow instead of
  clipping content.
- Make group-card up/down controls drive stable `sort_order` updates so later export slices can
  trust the visible group order.
- Keep all grouping behavior isolated from seating and from future saved-artifact UI concerns.

## Test plan

- Frontend:
  - `Slumpa` affects grouping only
  - current group count is respected
  - manual renames survive randomization
  - `Nytt grupputkast` starts blank
  - large groups render without clipped cards
- Manual:
  - open grouping, randomize several times, rename groups, add/remove groups, and confirm manual
    control remains intact throughout

## Rollback plan

- Revert the grouping workspace fundamentals if they destabilize group editing, while preserving
  the underlying class-first workspace and saved-grouping backend contract.

## Follow-up direction

- `PR-0092` uses the now-complete grouping workspace to add bounded undo/redo history and compact
  autosave feedback.
