---
type: pr
id: PR-0228
title: "ST-29-11 follow-up: desktop student-pool rail stickiness restoration"
status: done
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
  - "Given the teacher scrolls deeper through grouping or seating at the named desktop proof widths, when the large top panel leaves the viewport, then the page/workspace scroll remains the primary vertical path, the toolbar becomes the sticky working band, the student-pool rail stays visually attached below it, and the board/canvas does not collapse into a tiny competing internal scroller."
  - "Given guest and authenticated planner shells share the same visible grouping/seating layout contract through the shared shell primitives and focused guest/auth shell specs, when the retained real-data browser proof is run on the authenticated route, then the student-pool rail still behaves as one shared contract without requiring a second guest-only live proof lane for this bounded slice."
  - "Given the planner shell crosses the failing intermediate desktop cutover band below `xl`, when browser proof is run, then the split workspace does not silently collapse into long stacked page content without an explicit breakpoint decision."
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

## Current implementation baseline

The local implementation is now materially healthier than the earlier rejected bounded-pane pass.
The large top panel can scroll away, the toolbar becomes the sticky working band, grouping and
seating both use the same `480px` class-list rail pattern, and shared planner geometry is now
defined through named CSS primitives instead of runtime pane-height math.

That baseline is worth preserving, and this PR now closes on that corrected contract. The written
task/review trail now matches the CSS-owned page/workspace scroll model, and the retained
guest/authenticated parity obligation is satisfied by the shared shell implementation plus focused
guest/auth shell specs while the retained live browser proof stays on the stronger authenticated
real-data lane.

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
   The main page/workspace scroller should own the outer vertical path, the large top panel may
   scroll away, the toolbar should become the sticky working band, the student pool should keep its
   own `480px` local list scroller, and the board/canvas should stay on the main page/workspace
   scroll path instead of collapsing into a tiny competing internal scroller.

6. Keep planner geometry CSS-owned.
   Size, position, sticky behavior, overflow ownership, and breakpoint cutover should come from the
   shared layout contract. Persistent `window.innerHeight`, `getBoundingClientRect()`,
   `ResizeObserver`, or scroll-driven pane sizing/alignment are out of scope for this follow-up
   unless an explicit exception is approved.

7. Close this slice on one retained live-proof lane.
   The authenticated real-data Playwright path is the retained browser proof for this bounded PR.
   Guest/auth parity still matters, but it is enforced here through the shared shell primitives and
   focused guest/auth shell specs rather than a second retained guest live-proof script.

## Implementation plan

1. Audit where the student-pool rail lost local stickiness in the current desktop planner layout,
   especially across:
   - `frontend/apps/skriptoteket/src/views/apps/components/PlannerStudentPool.vue`
   - `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.vue`
   - `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.vue`
   - `frontend/apps/skriptoteket/src/views/apps/plannerWorkspaceLayout.ts`

2. Restore one shared sticky-rail contract at the desktop breakpoint path so grouping and seating
   consume the same fix rather than drifting again.

3. Restore the shell through CSS containment first:
   - fix containment, track sizing, `min-h-0`, and overflow ownership before adding any new runtime
     logic
   - define breakpoint cutover once in the shared layout tokens instead of re-encoding it in JS
   - keep the corrected page/workspace scroll model and sticky toolbar band rather than reintroducing
     a measured bounded-pane scroller

4. Keep the sticky behavior bounded to the local workspace seam:
   - the rail should stay visible beside the board/canvas while the teacher scrolls the workspace
   - the rail header should remain fixed
   - the list body should remain the only scrolling region inside the panel

5. Add focused frontend coverage that proves:
   - the rail/lane keeps the expected sticky desktop classes
   - the internal scroll body contract stays intact
   - guest/authenticated shared shells do not diverge on the affected surfaces

6. Extend the existing targeted planner Playwright proof lane rather than creating a disconnected
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
  - the shell contract using the real local `SA24D` roster and `G20` classroom when they are
    available, rather than ad hoc toy review fixtures
  - the authenticated route on the corrected page/workspace scroll model as the current baseline
  - grouping student-pool rail remains sticky while scrolling deeper into the board
  - seating student-pool rail remains sticky while scrolling deeper into the canvas workspace
  - seating rail-to-right-lane alignment remains preserved during deeper canvas scrolling, not only
    the fixed-header behavior
  - the student-pool header remains fixed
  - the authenticated route remains the retained real-data browser proof lane, while shared-shell
    guest/auth parity is locked by the focused guest/auth shell specs that exercise the same pane
    and toolbar contract without requiring a separate retained guest live-proof script
  - the named `laptop` (`1366x768`) and `desktop` (`1440x900`) review widths plus the currently
    failing intermediate pre-`xl` resize band

## Rollback plan

- Revert only the student-pool rail sticky-layout changes if they create overlap, clipping, or
  shell-specific drift, while preserving the already accepted toolbar and grouping-height contracts
  from `PR-0226` and `PR-0227`.

## References

- Retained review gate: [REV-PR-0228](../reviews/review-pr-0228-planner-workspace-shell-breakpoint-and-overflow-contract.md)
- Story parent: [ST-29-11](../stories/story-29-11-klassrumskartan-shared-site-and-app-dense-control-primitive-tightening.md)
- Canonical desktop composition owner: [ST-29-03](../stories/story-29-03-klassrumskartan-shared-desktop-workspace-composition-primitives.md)
- User-facing grouping/seating composition owner: [ST-29-05](../stories/story-29-05-klassrumskartan-grouping-and-seating-desktop-workspace-overhaul.md)
- Original split-pane/local-scroll execution slice: [PR-0128](pr-0128-klassrumskartan-grouping-and-seating-student-pool-split-pane-scrolling.md)
- Recent planner hardening slices: [PR-0226](pr-0226-st-29-11-shared-planner-shell-parity-and-grouping-viewport-height-stabilization.md), [PR-0227](pr-0227-st-29-11-exact-two-row-grouping-board-height-contract-at-desktop-baseline.md)
