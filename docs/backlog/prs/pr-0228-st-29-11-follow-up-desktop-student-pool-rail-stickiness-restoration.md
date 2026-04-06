---
type: pr
id: PR-0228
title: "ST-29-11 follow-up: desktop student-pool rail stickiness restoration"
status: in_progress
owners: "agents"
created: 2026-04-06
updated: 2026-04-06
stories:
  - "ST-29-03"
  - "ST-29-05"
  - "ST-29-11"
tags: ["frontend", "klassrumskartan", "planner", "scrolling", "sticky", "playwright"]
dependencies:
  - "PR-0128"
  - "PR-0226"
  - "PR-0227"
acceptance_criteria:
  - "Given the teacher works inside `Grupper` or `Sittplatser` at the `EPIC-29` `laptop` (`1366x768`) and `desktop` (`1440x900`) review viewports, when the live workspace overflows vertically, then the student-pool rail and the active board/canvas lane remain preserved as a stable desktop split workspace instead of drifting apart through page-level scroll."
  - "Given the student-pool rail is locally sticky, when the teacher works with long class lists, then the student-pool header remains fixed and only the list body scrolls."
  - "Given the desktop split workspace remains aligned, when the teacher scrolls deeper into grouping or seating, then that deeper movement happens inside the active board/canvas lane rather than by displacing the whole split-workspace relationship."
  - "Given guest and authenticated planner shells share the same visible grouping/seating layout contract, when the stickiness fix ships, then the student-pool rail behaves the same in both routes instead of drifting by wrapper."
  - "Given browser proof is run on the live local SPA, when the follow-up is reviewed, then the proof extends the existing planner Playwright lane instead of introducing a disconnected one-off script path."
---

## Problem

The student-pool/class-list rail used by `Grupper` and `Sittplatser` used to read as a stable local
working surface: the rail stayed beside the board or canvas, the header stayed fixed, and only the
list body scrolled. That behavior is still implied by the older desktop-composition stories and by
`PR-0128`, but it is no longer frozen tightly enough in the more recent planner-hardening lane.

The result is a regression risk: after the latest shared shell/grouping sizing work, the class-list
panel can lose its local stickiness and start behaving like normal page content instead of a stable
desktop tool rail.

## Goal

Restore and explicitly freeze the desktop student-pool rail stickiness contract across grouping and
seating, while keeping the current shared guest/authenticated shell direction and the recently
accepted desktop height contracts.

## Non-goals

- Reopening the detached top-toolbar sticky contract from `ST-29-02`.
- Reworking the grouping board `480px` / `234px` sizing rules from `PR-0226` and `PR-0227`.
- Redesigning mobile/tablet behavior or forcing the desktop rail contract onto reduced breakpoints.
- Forking the student-pool into separate grouping-only and seating-only implementations.

## Frozen decisions

1. The sticky class-list rail is part of the older shared desktop-composition contract.
   `ST-29-03` owns the canonical local-scroll/local-stickiness behavior and `ST-29-05` reinforces
   it as shipped desktop workspace composition. This PR exists because the regression surfaced in
   the current `ST-29-11` hardening lane, not because stickiness became a new feature.

2. The contract is desktop-first.
   Freeze behavior at the named `laptop` and `desktop` review widths. Smaller breakpoint behavior
   may reduce or reshape the rail later without being blocked by this PR.

3. Keep the existing shared student-pool primitive.
   Fix the sticky rail at the shared layout/component seam instead of inventing task-specific copies
   of the pool for grouping and seating.

4. Preserve the existing internal-scroll contract.
   The student-pool header stays fixed and only the list body scrolls; stickiness should strengthen
   that behavior, not replace it with page-level scroll hunting.

5. Keep the desktop split workspace stable at the shell seam.
   The pane shell should bound the visible desktop workspace, the student pool should keep its own
   internal list scroller, and deeper grouping/seating movement should happen inside the active
   right-hand lane rather than by letting the full workspace chrome drift out of alignment.

## Implementation plan

1. Audit where the student-pool rail lost local stickiness in the current desktop planner layout,
   especially across:
   - `frontend/apps/skriptoteket/src/views/apps/components/PlannerStudentPool.vue`
   - `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.vue`
   - `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.vue`
   - `frontend/apps/skriptoteket/src/views/apps/plannerWorkspaceLayout.ts`

2. Restore one shared sticky-rail contract at the desktop breakpoint path so grouping and seating
   consume the same fix rather than drifting again.

3. Keep the sticky behavior bounded to the local workspace seam:
   - the rail should stay visible beside the board/canvas while the teacher scrolls the workspace
   - the rail header should remain fixed
   - the list body should remain the only scrolling region inside the panel

4. Add focused frontend coverage that proves:
   - the rail/lane keeps the expected sticky desktop classes
   - the internal scroll body contract stays intact
   - guest/authenticated shared shells do not diverge on the affected surfaces

5. Extend the existing targeted planner Playwright proof lane rather than creating a disconnected
   brand-new script. Reuse the current classroom-planner helpers and whichever of the existing
   `PR-0179` or `PR-0227` scripts gives the cleanest route to live stickiness measurement.

## Test plan

- `pdm run fe-test src/views/apps/components/PlannerGroupingWorkspacePane.smart-rules.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Live browser proof at:
  - `http://127.0.0.1:5173/apps/classroom.group-seating-studio`
  - `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio`
- Playwright proof should extend an existing planner script/helper path and verify, at minimum:
  - grouping student-pool rail remains sticky while scrolling deeper into the board
  - seating student-pool rail remains sticky while scrolling deeper into the canvas workspace
  - the student-pool header remains fixed
  - both authenticated and guest shells preserve the same visible stickiness behavior

## Rollback plan

- Revert only the student-pool rail sticky-layout changes if they create overlap, clipping, or
  shell-specific drift, while preserving the already accepted toolbar and grouping-height contracts
  from `PR-0226` and `PR-0227`.

## References

- Story parent: [ST-29-11](../stories/story-29-11-klassrumskartan-shared-site-and-app-dense-control-primitive-tightening.md)
- Canonical desktop composition owner: [ST-29-03](../stories/story-29-03-klassrumskartan-shared-desktop-workspace-composition-primitives.md)
- User-facing grouping/seating composition owner: [ST-29-05](../stories/story-29-05-klassrumskartan-grouping-and-seating-desktop-workspace-overhaul.md)
- Original split-pane/local-scroll execution slice: [PR-0128](pr-0128-klassrumskartan-grouping-and-seating-student-pool-split-pane-scrolling.md)
- Recent planner hardening slices: [PR-0226](pr-0226-st-29-11-shared-planner-shell-parity-and-grouping-viewport-height-stabilization.md), [PR-0227](pr-0227-st-29-11-exact-two-row-grouping-board-height-contract-at-desktop-baseline.md)
