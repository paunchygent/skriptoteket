---
type: pr
id: PR-0302
title: "ST-29-11: planner toolbar Smart overflow default remediation"
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
  - "Given grouping or seating workspaces render in authenticated or public guest mode, when the toolbar loads at phone, tablet, laptop, or desktop widths, then the split Smart toggle/settings control lives in overflow by default instead of the first-row toolbar."
  - "Given width pressure increases, when the toolbar collapse ladder runs, then class/classroom context and reset keep their measured overflow behavior while Smart remains overflow-owned across all breakpoints."
  - "Given a new authenticated or public guest grouping/seating draft is created and the user has not opted out, when the workspace opens, then Smart is enabled by default."
  - "Given a teacher turns Smart off from the overflow control, when the toggle changes, then a short Swedish warning toast explains that Slumpa becomes ordinary randomization and no longer uses rules, fixed seats, near-teacher, or together/apart preferences."
  - "Given the planner overflow menu is open, when its content includes class/classroom, Smart, or settings controls, then the panel renders on an opaque canvas surface rather than a translucent panel."
  - "Given the small-screen toolbar rules apply, when the workspace is below the phone breakpoint, then the existing small-screen overflow behavior remains reachable without leaking its always-overflow assumptions into tablet or desktop widths."
---

## Problem

The small-screen seating/grouping toolbar work and the first remediation pass
left Smart placement ambiguous: the split Smart toggle/settings control could
return to the first-row toolbar at wider widths even though it is a secondary
teaching-choice control. The public and authenticated workspaces also still
started new drafts with Smart off in some paths, so teachers had to opt in
before Smart rules affected `Slumpa`.

The menu panel also inherits the translucent panel surface, which makes the
class/classroom and Smart controls visually bleed over the workspace canvas.

## Goal

Remediate the Smart control without reopening the workspace redesign:

- keep Smart plus Smart settings in the overflow menu by default for grouping
  and seating, authenticated and public guest, across phone/tablet/desktop
- preserve the remaining measured overflow ladder for class/classroom context
  and reset
- default new authenticated and public guest drafts to Smart on unless the user
  explicitly turns it off
- show teacher-friendly Swedish copy when Smart is turned off

## Non-goals

- No solver-algorithm, export, share-link, or artifact contract changes.
- No redesign of the small-screen workspace shell or mode switcher.
- No change to share/export, history, undo/redo, or reset semantics.
- No tablet or desktop breakpoint duplication in JavaScript.

## Module Focus

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspaceToolbar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspaceToolbar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarOverflowMenu.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/usePlannerToolbarOverflow.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerSmartDefaults.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerSmartRunActions.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerSmartRuleActions.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestDraftMutations.ts`
- `frontend/apps/skriptoteket/src/assets/main.css`
- `frontend/apps/skriptoteket/src/assets/klassrumskartan-responsive-workspace.css`
- `frontend/apps/skriptoteket/src/components/ui/denseToolPrimitives.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspaceToolbar.overflow.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspaceToolbar.overflow.spec.ts`
- `scripts/playwright_pr_0302_toolbar_overflow_parity.py`

## Test Plan

- `pdm run fe-test -- --run PlannerGroupingWorkspaceToolbar.overflow PlannerSeatingWorkspaceToolbar.overflow usePlannerToolbarOverflow classroomPlannerGuestDraftWorkspace`
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py -q`
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

Implemented first as a frontend-only responsive toolbar correction, then amended
as a small Smart-placement remediation:

- grouping and seating now register the measured overflow priority as
  class/classroom context first and reset after that lower-priority contextual
  control
- Smart plus Smart settings live in the overflow panel by default across
  authenticated and public guest workspaces at phone, tablet, laptop, and
  desktop widths
- new authenticated draft defaults and new public guest draft defaults now treat
  Smart as enabled unless the user explicitly opts out
- the frontend treats absent `smart_enabled` as enabled, preserving the
  "not opted out" default for older or partial payloads
- turning Smart off shows the Swedish warning copy:
  `Smart är avstängt. När du slumpar tas ingen hänsyn till regler, fasta platser, nära läraren eller ihop/isär.`
- class/classroom overflow copies are shown only when the selector has actually
  overflowed, while the inline measurement source remains mounted and inert so
  resize churn cannot drop the control from both placements
- phone mode keeps the same priority ladder near the breakpoint: the `767px`
  edge remains measured when the toolbar has usable width, then compact phone
  widths keep Smart overflow-owned while moving context and reset one contribution at a time instead of
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

- Smart overflow/default amendment: `pdm run fe-test -- --run
  PlannerGroupingWorkspaceToolbar.overflow PlannerSeatingWorkspaceToolbar.overflow
  usePlannerToolbarOverflow classroomPlannerGuestDraftWorkspace` passed: 4 files
  / 18 tests.
- Smart overflow/default amendment: `pdm run pytest
  tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py -q`
  passed: 20 tests.
- Smart overflow/default amendment: `pdm run fe-type-check` passed.
- Smart overflow/default amendment: `pdm run fe-lint` passed.
- Smart overflow/default amendment: broader Smart-state frontend test command
  `pdm run fe-test -- --run useClassroomState useSmartGroupingRun
  useSmartSeatingRun usePublicSmartGroupingRun usePublicSmartSeatingRun
  classroomPlannerSmartRunActions` still has pre-existing fixed-seat-rule
  payload assertion drift from the active `ST-27-09` local worktree changes; the
  Smart-run/public Smart files in that command passed.
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
