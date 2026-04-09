---
type: pr
id: PR-0229
title: "ST-29-11 follow-up: desktop-first planner toolbar breakpoint overflow escalation and undo/redo shortcut parity"
status: ready
owners: "agents"
created: 2026-04-06
updated: 2026-04-09
stories:
  - "ST-29-11"
tags: ["frontend", "design-system", "klassrumskartan", "planner", "toolbar", "keyboard"]
dependencies:
  - "PR-0225"
  - "PR-0228"
acceptance_criteria:
  - "Given the authenticated planner shell is rendered near the shared desktop breakpoint, when the viewport is `1279px` wide, then the left nav stays collapsed with the mobile header owning the chrome; when the viewport reaches `1280px`, then the desktop sidebar pins and the stacked mobile header is gone."
  - "Given the grouping or seating toolbar is rendered in authenticated or guest shells, when the viewport shrinks through its exact live cutoff widths, then the toolbar stays one row and lower-priority actions collapse into overflow before any control is pushed outside the visible bar or wraps onto a second row."
  - "Given the shared planner toolbar reaches its first overflow breakpoint, when secondary actions must collapse, then undo and redo move into overflow before primary workflow, export, or required context controls."
  - "Given width pressure increases after undo/redo are already overflowed, when the one-row desktop strip still cannot hold, then `Börja om` collapses next into overflow before more critical workflow controls are displaced."
  - "Given undo or redo are no longer visibly pinned in the toolbar, when the teacher uses canonical planner shortcuts outside editable text fields or menu focus traps, then the same undo/redo actions still fire in grouping and seating without requiring the buttons to stay visible."
  - "Given browser proof is run on the shared planner toolbar, when each lane is checked just above and just below its exact live cutoffs, then the overflow ladder is deliberate, monotonic, and reviewable rather than spill-driven or accidental."
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

- freeze explicit shell and toolbar breakpoint behavior for the shared planner workspace
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
- `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.vue`
- `frontend/apps/skriptoteket/src/views/apps/usePlannerUndoRedoShortcuts.ts`

## Proof focus

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceActionBar.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.shortcuts.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.shortcuts.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/usePlannerUndoRedoShortcuts.spec.ts`

## Implementation plan

1. Freeze an explicit shared shell and toolbar breakpoint ladder.
   - keep the authenticated planner shell compact below `1280px` and pinned at `1280px` and above
   - derive exact toolbar cutoffs from live geometry instead of a coarse review-width matrix
   - define which controls are always-visible, which collapse first, and which collapse second

2. Escalate overflow intentionally instead of letting the strip spill.
   - move `undo` / `redo` into overflow first
   - move `Börja om` into overflow next if more width must be reclaimed
   - keep the more critical workflow/export/context controls visible for longer

3. Add canonical keyboard shortcut parity for `undo` / `redo`.
  - support planner-scoped undo/redo shortcuts when focus is not inside a text input, textarea, or
    menu interaction that should keep the key event
  - keep authenticated and guest grouping/seating on the same shortcut contract
  - prove the negative path explicitly so the shared listener never steals `Cmd/Ctrl+Z` while the
    teacher is typing or navigating overflow/menu focus traps
  - if `PR-0232` lands first and introduces the shared shortcut composable to unblock guest
    parity, this PR owns the follow-up polish and alignment work:
     - keep authenticated and guest toolbar surfaces on one deliberate shortcut contract
     - align shortcut discoverability with overflow behavior once undo/redo are no longer pinned
     - absorb any post-`PR-0232` toolbar-shell cleanup needed to keep the shared command strip
       coherent across guest/auth lanes

4. Strengthen proof at the shared toolbar seam.
   - add focused component/spec coverage for overflow-order behavior plus shared shortcut handling
     in authenticated and guest shells
   - add direct shared-composable proof for positive and negative shortcut paths
   - add live browser proof that binary-searches the exact shell and toolbar cutoffs, then records
     just-above / just-below evidence for authenticated and guest routes

## Coordination note

`PR-0232` is allowed to introduce the shared planner undo/redo shortcut composable early so the
guest boundary slice can ship real shortcut parity without waiting on the toolbar overflow lane.

That early shortcut wiring does not close this PR. `PR-0229` still owns the desktop-first toolbar
shape, overflow escalation order, and any final shortcut/discoverability polish required after the
guest slice lands.

## Test plan

- `pdm run fe-test -- --run src/views/apps/components/PlannerWorkspaceActionBar.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerWorkspaceShell.shortcuts.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.shortcuts.spec.ts src/views/apps/usePlannerUndoRedoShortcuts.spec.ts`
- `pdm run fe-type-check`
- `pdm run python -m scripts.playwright_pr_0229_toolbar_overflow_threshold_check --dotenv .env.prod-smoke`
- `pdm run docs-validate`
- Live threshold proof expectations from `.artifacts/pr-0229-toolbar-overflow-thresholds/threshold-results.json`:
  - authenticated shell cutover: compact at `1279px`, desktop sidebar pinned at `1280px`
  - authenticated grouping overflow: `undo/redo` at `1237px`, `Börja om` at `1156px`, `Nytt utkast` at `1080px`, roster context at `991px`, `Smart` at `568px`
  - authenticated seating overflow: `undo/redo` at `1237px`, `Börja om` at `1156px`, `Nytt utkast` at `1080px`, template context at `966px`, `Smart` at `459px`
  - guest grouping overflow: `undo/redo` at `969px`, `Börja om` at `888px`, `Nytt utkast` at `812px`, roster context at `692px`, `Smart` at `552px`
  - guest seating overflow: `undo/redo` at `933px`, `Börja om` at `852px`, `Nytt utkast` at `776px`, template context at `631px`, `Smart` at `443px`
  - in every lane, verify just-above / just-below evidence for the exact cutoff, one-row stability, and menu parity for the newly hidden contribution
- Shortcut negative-path proof expectations:
  - the shared composable spec must prove the listener stays inert for `input`, `textarea`, `select`, `contenteditable`, `[role="textbox"]`, and `[role="menu"]` targets, plus already-prevented, disabled, no-draft, and no-history-capability cases
  - the focused auth and guest shell shortcut specs must prove one allowed neutral-toolbar path and two blocked real-shell paths: focused actions-menu item and focused input probe

## Rollback plan

- Revert only the toolbar breakpoint-priority and shortcut wiring if it causes action loss, focus
  conflicts, or discoverability regressions, while preserving the existing shared toolbar shell and
  the corrected page/workspace scroll model from `PR-0228`.

## References

- Retained review gate: [REV-PR-0229](../reviews/review-pr-0229-planner-toolbar-breakpoint-overflow-escalation-and-undo-redo-shortcut-parity.md)
- Parent story: [ST-29-11](../stories/story-29-11-klassrumskartan-shared-site-and-app-dense-control-primitive-tightening.md)
- Earlier toolbar hardening slice: [PR-0225](pr-0225-st-29-11-desktop-first-planner-toolbar-priority-and-overflow-hardening.md)
- Shared shell follow-up baseline: [PR-0228](pr-0228-st-29-11-follow-up-desktop-student-pool-rail-stickiness-restoration.md)
