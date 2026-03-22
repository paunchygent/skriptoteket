---
type: pr
id: PR-0091
title: "Klassrumskartan: grouping workspace fundamentals"
status: ready
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
  - "Large groups render without clipping student cards inside the group panel."
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

- [ ] Add grouping-only `Slumpa` to the focused grouping workspace.
- [ ] Preserve current group count and teacher-defined group names when `Slumpa` runs.
- [ ] Add explicit `Nytt grupputkast` that starts blank rather than copying the current grouping.
- [ ] Keep manual drag/drop and group edits first-class after randomization.
- [ ] Fix large-group layout so student cards do not clip or overflow awkwardly.
- [ ] Add frontend tests for grouping fundamentals and layout behavior.

## Implementation plan

- Extend the grouping workspace controls with:
  - `Slumpa`
  - `Nytt grupputkast`
- Implement grouping randomize behavior against the current class roster and current group count
  only; do not infer seat assignments or classroom-only behavior.
- Keep group names stable when randomizing so teacher-defined structure survives.
- Refine `GroupBoard.vue` / `GroupCard.vue` layout so larger groups expand or reflow instead of
  clipping content.
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
