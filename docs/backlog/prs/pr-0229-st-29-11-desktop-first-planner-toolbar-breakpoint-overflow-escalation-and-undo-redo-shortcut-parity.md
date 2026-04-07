---
type: pr
id: PR-0229
title: "ST-29-11 follow-up: desktop-first planner toolbar breakpoint overflow escalation and undo/redo shortcut parity"
status: ready
owners: "agents"
created: 2026-04-06
updated: 2026-04-06
stories:
  - "ST-29-11"
tags: ["frontend", "design-system", "klassrumskartan", "planner", "toolbar", "keyboard"]
dependencies:
  - "PR-0225"
  - "PR-0228"
acceptance_criteria:
  - "Given the grouping or seating toolbar is rendered at the `EPIC-29` `desktop` (`1440x900`), `laptop` (`1366x768`), or the failing intermediate pre-`xl` desktop band, when width pressure increases, then the toolbar stays one row and lower-priority actions collapse into overflow before any control is pushed outside the visible bar or wraps onto a second row."
  - "Given the shared planner toolbar reaches its first overflow breakpoint, when secondary actions must collapse, then undo and redo move into overflow before primary workflow, export, or required context controls."
  - "Given width pressure increases after undo/redo are already overflowed, when the one-row desktop strip still cannot hold, then `Börja om` collapses next into overflow before more critical workflow controls are displaced."
  - "Given undo or redo are no longer visibly pinned in the toolbar, when the teacher uses canonical planner shortcuts outside editable text fields or menu focus traps, then the same undo/redo actions still fire in grouping and seating without requiring the buttons to stay visible."
  - "Given browser proof is run on the shared planner toolbar, when grouping and seating are checked at `1279x900`, `1366x768`, and `1440x900`, then the breakpoint ladder is deliberate and reviewable rather than spill-driven or accidental."
---

## Problem

`PR-0225` hardened the planner toolbar priority model, but the current toolbar still reaches a width
band where visible buttons get pushed out of the strip before enough actions collapse into the
overflow menu.

That behavior is especially problematic in a desktop-first workspace: the toolbar should not solve
width pressure by becoming a multi-row bar or by silently clipping/detaching right-edge controls.
The breakpoint behavior needs to be explicit, deliberate, and ordered by action priority.

## Goal

Define and implement the next toolbar hardening step for the planner-family desktop workspace:

- freeze explicit breakpoint/width-pressure behavior for the shared planner toolbar
- preserve a one-row desktop command strip
- move lower-priority actions into overflow in a deliberate order instead of waiting for visual spill
- collapse `undo` / `redo` first, then `Börja om`
- preserve undo/redo discoverability and speed with canonical keyboard shortcuts

## Non-goals

- Allowing multi-row planner toolbars as the fallback answer.
- Reopening the page/workspace scroll model from `PR-0228`.
- Reordering core workflow priorities beyond the explicit overflow sequence frozen here.
- Turning overflow into a hidden graveyard for primary workflow actions without a separate product
  decision.

## Module focus

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceActionBar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspaceToolbar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspaceToolbar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarOverflowMenu.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`

## Implementation plan

1. Freeze an explicit shared breakpoint ladder for planner toolbar width pressure.
   - keep the toolbar one row at the named desktop proof widths and the current failing intermediate
     band
   - define which controls are always-visible, which collapse first, and which collapse second

2. Escalate overflow intentionally instead of letting the strip spill.
   - move `undo` / `redo` into overflow first
   - move `Börja om` into overflow next if more width must be reclaimed
   - keep the more critical workflow/export/context controls visible for longer

3. Add canonical keyboard shortcut parity for `undo` / `redo`.
   - support planner-scoped undo/redo shortcuts when focus is not inside a text input, textarea, or
     menu interaction that should keep the key event
   - keep grouping and seating on the same shortcut contract

4. Strengthen proof at the shared toolbar seam.
   - add focused component/spec coverage for overflow-order behavior and shortcut handling
   - add live browser proof that shows the toolbar staying one row while overflow content grows at
     the named width bands

## Test plan

- `pdm run fe-test src/views/apps/components/PlannerWorkspaceActionBar.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Live desktop proof:
  - `http://127.0.0.1:5173/apps/classroom.group-seating-studio`
  - verify grouping and seating at `1279x900`, `1366x768`, and `1440x900`
  - verify the toolbar never wraps to multiple rows and no button is pushed outside the visible bar
  - verify `undo` / `redo` overflow before `Börja om`
  - verify `undo` / `redo` shortcuts still work when those controls are no longer visibly pinned

## Rollback plan

- Revert only the toolbar breakpoint-priority and shortcut wiring if it causes action loss, focus
  conflicts, or discoverability regressions, while preserving the existing shared toolbar shell and
  the corrected page/workspace scroll model from `PR-0228`.

## References

- Retained review gate: [REV-PR-0229](../reviews/review-pr-0229-planner-toolbar-breakpoint-overflow-escalation-and-undo-redo-shortcut-parity.md)
- Parent story: [ST-29-11](../stories/story-29-11-klassrumskartan-shared-site-and-app-dense-control-primitive-tightening.md)
- Earlier toolbar hardening slice: [PR-0225](pr-0225-st-29-11-desktop-first-planner-toolbar-priority-and-overflow-hardening.md)
- Shared shell follow-up baseline: [PR-0228](pr-0228-st-29-11-follow-up-desktop-student-pool-rail-stickiness-restoration.md)
