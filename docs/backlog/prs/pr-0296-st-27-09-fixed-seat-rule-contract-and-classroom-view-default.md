---
type: pr
id: PR-0296
title: "ST-27-09: fixed-seat rule contract and classroom-view default"
status: done
owners: "agents"
created: 2026-05-05
updated: 2026-05-05
stories:
  - "ST-27-09"
tags: ["docs", "planning", "smart-assignment", "klassrumskartan", "ux"]
dependencies:
  - "EPIC-27"
  - "ST-27-03"
  - "ST-27-07"
  - "ST-27-08"
acceptance_criteria:
  - "Given the fixed-seat discussion has been accepted, when the governed docs are updated, then `ST-27-09` records the hard fixed-seat invariant, classroom-view-first authoring model, and fixed-seat prompt copy."
  - "Given `EPIC-27` and the smart-assignment decision memo previously named `Planeringskarta` as the default rules map, when this slice closes, then those docs explicitly record the 2026-05-05 refinement that the physical classroom view is the default when a classroom exists."
  - "Given implementation has not started, when the story is decomposed, then backend and frontend work are separated into PR-sized slices with clear validation gates and stop conditions."
  - "Given the docs index is the durable entry point, when this slice closes, then it links the new story and PR tasks."
---

## Problem

The current smart-assignment docs predate the fixed-seat rule discussion. They also still describe
`Planeringskarta` as the default rules map, which now conflicts with the accepted classroom-view
first authoring shape for geometry-aware rules.

## Goal

Create the governed docs spine for fixed-seat rules:

- add `ST-27-09`
- add backend and frontend implementation slices
- update `EPIC-27`
- update the smart-assignment decision memo
- update `docs/index.md`
- update `.codex/handoff.md`

## Non-goals

- Implementing persistence, migrations, solver changes, API DTOs, or frontend UI.
- Reopening the completed `ST-27-07` implementation beyond documenting the refined default-view
  contract for future work.
- Changing the existing abstract behavior of `Planeringskarta` when it is deliberately selected.

## Implementation plan

1. Add `ST-27-09` with the accepted UX and solver contract.
2. Add `PR-0297` for backend persistence and score-aware solver seeding.
3. Add `PR-0298` for frontend `Fast plats` authoring and classroom-view-first UX.
4. Update `EPIC-27`, the smart-assignment decision memo, `docs/index.md`, and handoff.

## Test plan

- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback plan

Revert this docs slice if product direction changes before implementation starts. No runtime
behavior changes are introduced by this slice.
