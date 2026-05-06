---
type: pr
id: PR-0302
title: "ST-29-11: planner toolbar overflow priority regression"
status: done
owners: "agents"
created: 2026-05-06
updated: 2026-05-06
stories:
  - "ST-29-11"
tags: ["frontend", "ux", "design-system", "klassrumskartan", "toolbar", "responsive"]
dependencies:
  - "PR-0225"
  - "PR-0287"
acceptance_criteria:
  - "Given the grouping or seating toolbar has enough desktop or tablet width, when the overflow menu opens, then the class/classroom selector is not duplicated in the menu while it remains inline."
  - "Given the grouping or seating toolbar has enough desktop or tablet width for Smart controls, when Smart and Smart settings fit after the class/classroom selector, then the split Smart control remains inline instead of living permanently in overflow."
  - "Given width pressure increases, when the toolbar collapse ladder runs, then the class/classroom selector moves to overflow before Smart, and Smart moves to overflow only after it no longer fits inline."
  - "Given the planner overflow menu is open, when its content includes class/classroom, Smart, or settings controls, then the panel renders on an opaque canvas surface rather than a translucent panel."
  - "Given the small-screen toolbar rules apply, when the workspace is below the phone breakpoint, then the existing small-screen overflow behavior remains reachable without leaking its always-overflow assumptions into tablet or desktop widths."
---

## Problem

The small-screen seating/grouping toolbar work accidentally leaked into the
tablet and desktop overflow contract. Class/classroom selectors are rendered in
both the toolbar and overflow menu while still inline, and Smart plus Smart
settings are rendered only inside overflow even when there is enough room for
the split Smart control in the toolbar.

The menu panel also inherits the translucent panel surface, which makes the
class/classroom and Smart controls visually bleed over the workspace canvas.

## Goal

Restore the desktop-first priority ladder without reopening the small-screen
workspace redesign:

- keep the class/classroom selector inline while it fits
- move the class/classroom selector into overflow first under width pressure
- keep Smart plus Smart settings inline after the selector while they fit
- move Smart into overflow only after the selector has already moved
- keep phone behavior available through the existing small-screen CSS contract
- render overflow menu content on an opaque canvas surface

## Non-goals

- No backend, API, draft, solver, or persistence changes.
- No redesign of the small-screen workspace shell or mode switcher.
- No change to share/export, history, undo/redo, or reset semantics.
- No tablet or desktop breakpoint duplication in JavaScript. The only explicit
  breakpoint override is the dedicated phone contract at `max-width: 767px`;
  tablet and desktop placement stays owned by the measured toolbar ladder.

## Module Focus

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspaceToolbar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspaceToolbar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarOverflowMenu.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/usePlannerToolbarOverflow.ts`
- `frontend/apps/skriptoteket/src/assets/main.css`
- `frontend/apps/skriptoteket/src/assets/klassrumskartan-responsive-workspace.css`
- `frontend/apps/skriptoteket/src/components/ui/denseToolPrimitives.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspaceToolbar.overflow.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspaceToolbar.overflow.spec.ts`
- `scripts/playwright_pr_0302_toolbar_overflow_parity.py`

## Test Plan

- `pdm run fe-test -- --run PlannerGroupingWorkspaceToolbar.overflow PlannerSeatingWorkspaceToolbar.overflow usePlannerToolbarOverflow`
- `pdm run python -m scripts.playwright_pr_0302_toolbar_overflow_parity --start-backend --start-vite`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `pdm run ruff check scripts/playwright_pr_0302_toolbar_overflow_parity.py tests/unit/scripts/test_playwright_script_surface.py`
- `pdm run pytest tests/unit/scripts/test_playwright_script_surface.py -q`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Implementation Summary

Implemented as a frontend-only responsive toolbar correction:

- grouping and seating now register the measured overflow priority as
  class/classroom context first, Smart second, and reset after those lower-priority
  contextual controls
- Smart plus Smart settings render as an inline split control on tablet/desktop
  while it fits, instead of living permanently in the overflow panel
- class/classroom overflow copies are shown only when the selector has actually
  overflowed, while the inline measurement source remains mounted and inert so
  resize churn cannot drop the control from both placements
- phone mode keeps the same priority ladder near the breakpoint: the `767px`
  edge remains measured when the toolbar has usable width, then compact phone
  widths move context, Smart, and reset one contribution at a time instead of
  dumping multiple controls into overflow
- toolbar measurement now sums real child control widths instead of stretched
  flex-zone widths, and reschedules on window resize so controls return when the
  viewport grows after phone mode
- shared dense menu panels now use opaque `bg-canvas` rather than translucent
  `bg-panel`
- added a retained Playwright proof that runs the authenticated and public guest
  surfaces through grouping and seating desktop -> laptop -> tablet -> phone
  breakpoint -> staged compact phone widths -> tablet -> laptop -> desktop
  roundtrips

## Verification

- `pdm run fe-test -- --run PlannerGroupingWorkspaceToolbar.overflow PlannerSeatingWorkspaceToolbar.overflow usePlannerToolbarOverflow`
  plus `denseToolPrimitives` passed: 4 files / 14 tests.
- `pdm run python -m scripts.playwright_pr_0302_toolbar_overflow_parity
  --start-backend --start-vite` passed. It exercised authenticated and public
  guest shells, both grouping and seating workspaces, full desktop -> phone ->
  desktop roundtrips, the `767px` breakpoint-adjacent state, staged one-control
  compact-phone overflow, priority-prefix assertions, no toolbar horizontal
  overflow, no lost controls, and opaque overflow-menu backgrounds. Screenshots
  were saved under `.artifacts/playwright-pr-0302-toolbar-overflow-parity/`.
- `pdm run fe-type-check` passed.
- `pdm run fe-lint` passed.
- `pdm run fe-build` passed; the existing large chunk-size warnings remain.
- `pdm run ruff check scripts/playwright_pr_0302_toolbar_overflow_parity.py
  tests/unit/scripts/test_playwright_script_surface.py` passed.
- `pdm run pytest tests/unit/scripts/test_playwright_script_surface.py -q`
  passed: 3 tests.
- `pdm run docs-validate` passed.
- `pdm run handoff-validate` passed.
- `git diff --check` passed.

## Rollback Plan

Restore the prior toolbar rendering rules and dense menu panel class. Because
this slice is frontend-only, rollback must not require database, API, share,
export, or solver changes.

## References

- Parent primitive story:
  [ST-29-11](../stories/story-29-11-klassrumskartan-shared-site-and-app-dense-control-primitive-tightening.md)
- Prior toolbar hardening:
  [PR-0225](pr-0225-st-29-11-desktop-first-planner-toolbar-priority-and-overflow-hardening.md)
- Smart settings persistence:
  [PR-0287](pr-0287-st-29-11-smart-settings-popover-persistence.md)
