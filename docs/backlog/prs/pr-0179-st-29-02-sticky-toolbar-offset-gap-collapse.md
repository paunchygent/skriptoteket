---
type: pr
id: PR-0179
title: "ST-29-02 follow-up: sticky toolbar offset gap collapse"
status: done
owners: "agents"
created: 2026-03-31
updated: 2026-03-31
stories:
  - "ST-29-02"
tags: ["frontend", "ux", "klassrumskartan", "toolbar", "shell", "playwright"]
acceptance_criteria:
  - "Given the teacher scrolls inside `Grupper` or `Sittplatser`, when the detached shared workspace toolbar reaches sticky mode, then it closes the viewport-top gap instead of preserving a visible offset above the toolbar."
  - "Given the teacher scrolls back to the start position, when the detached toolbar leaves sticky mode, then it returns to its original in-layout position below the compressed planner shell."
  - "Given browser proof is run at the `EPIC-29` `laptop` (`1366x768`) and `desktop` (`1440x900`) review viewports, when the follow-up is reviewed, then the toolbar reads as attached to the top of the screen while sticky without regressing the existing shell-compression layout."
---

## Problem

`PR-0161` correctly detached the shared `Grupper` and `Sittplatser` toolbars and made them sticky,
but the shell still mounts both toolbars with a positive viewport offset (`top-3`). In practice
that leaves a visible gap above the toolbar after it sticks, which weakens the intended
shell-compression effect on laptop-height screens.

## Goal

Keep the existing detached shared toolbar model while collapsing the viewport-top gap once the
toolbar enters sticky mode.

## Non-goals

- Reopening the rules-workspace rail behavior from `PR-0155`.
- Redesigning toolbar contents, zoning, or export/smart-rule behavior.
- Reworking planner scroll ownership beyond the sticky top offset.

## Implementation plan

1. Update the planner shell sticky-toolbar wrapper so `Grupper` and `Sittplatser` pin flush to the
   viewport top instead of preserving the current detached offset.
2. Keep the toolbar in normal document flow before it sticks so the original resting layout below
   `PlannerTopPanel` remains unchanged at the top of the page.
3. Add focused shell coverage that locks the sticky class/offset contract for both toolbars.
4. Run frontend + browser proof to verify the toolbar closes the gap while sticky and returns to the
   original position when scrolling back to the top.

## Execution notes

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue` now mounts the
  detached grouping and seating toolbars with `top-0` instead of the old positive sticky offset.
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.spec.ts` now locks the
  flush sticky class contract for both toolbars.
- Live proof runs through `scripts/playwright_pr_0179_sticky_toolbar_offset_check.py`, which records
  screenshots under `.artifacts/pr-0179-sticky-toolbar-offset-check/`.

## Test plan

- `pdm run fe-test -- --run src/views/apps/components/PlannerWorkspaceShell.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- `pdm run python -m scripts.playwright_pr_0179_sticky_toolbar_offset_check --base-url http://127.0.0.1:5173`

## Rollback plan

- Restore the previous sticky offset in `PlannerWorkspaceShell.vue` if the top-pinned behavior
  causes overlap or regression in the compressed shell.
