---
type: pr
id: PR-0180
title: "ST-29-02 follow-up: sticky toolbar topbar gap collapse"
status: done
owners: "agents"
created: 2026-03-31
updated: 2026-03-31
stories:
  - "ST-29-02"
tags: ["frontend", "ux", "klassrumskartan", "toolbar", "shell", "playwright"]
acceptance_criteria:
  - "Given the teacher scrolls inside `Grupper` or `Sittplatser`, when the detached shared workspace toolbar reaches sticky mode on desktop review widths, then it sits directly under the authenticated sticky topbar instead of leaving a visible vertical gap."
  - "Given the teacher returns to the start position, when the toolbar leaves sticky mode, then it returns to the same in-layout resting position below the compressed planner shell."
  - "Given browser proof is run against the live dev stack at `http://127.0.0.1:5173` plus `http://127.0.0.1:8000`, when the follow-up is reviewed, then both `Grupper` and `Sittplatser` prove first-class sticky alignment against the real authenticated shell topbar."
---

## Problem

`PR-0179` removed the original viewport-top offset from the detached workspace toolbar, but the
live authenticated shell still leaves a noticeable gap between the sticky topbar and the planner
toolbar in `Grupper` and `Sittplatser`. The toolbar now reads as sticky, yet it still feels
detached from the shell chrome instead of snapping cleanly under it.

## Goal

Collapse the remaining authenticated-topbar gap so the detached planner toolbar feels anchored to
the real shell edge while sticky.

## Non-goals

- Reopening the toolbar content split from `PR-0161`.
- Changing planner topbar copy, controls, or authenticated shell actions.
- Redesigning the rules workspace or non-sticky overview surfaces.

## Implementation plan

1. Revisit the planner shell sticky offset so the grouping and seating toolbars pin to the sticky
   topbar seam instead of only pinning to the raw viewport edge.
2. Keep the existing resting layout unchanged before the toolbar becomes sticky.
3. Update focused shell coverage so the new sticky offset contract is explicit.
4. Revalidate the sticky seam in the live dev stack and record the accepted proof source.

## Test plan

- `pdm run fe-test -- --run src/views/apps/components/PlannerWorkspaceShell.spec.ts`
- `pdm run docs-validate`
- Manual live inspection against the running dev stack on `http://127.0.0.1:5173` +
  `http://127.0.0.1:8000`

## Execution notes

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue` now applies a
  desktop-only negative sticky offset (`md:-top-4`) so the detached `Grupper` and `Sittplatser`
  toolbars tuck up against the authenticated shell topbar while still resting in the same
  in-layout position at scroll start.
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.spec.ts` now locks
  that tighter sticky-topbar class contract for both detached toolbars.
- Final proof for this follow-up is the accepted manual live inspection from the running dev stack
  on `2026-03-31`, after the focused shell spec and docs validation passed locally.

## Rollback plan

- Restore the previous sticky offset contract in `PlannerWorkspaceShell.vue` if the tighter shell
  alignment causes overlap or regressions under the authenticated topbar.
