---
type: pr
id: PR-0226
title: "ST-29-11: shared planner shell parity and grouping viewport-height stabilization"
status: done
owners: "agents"
created: 2026-04-06
updated: 2026-04-06
stories:
  - "ST-29-11"
tags: ["frontend", "design-system", "klassrumskartan", "planner", "guest", "desktop-first"]
dependencies:
  - "EPIC-29"
  - "PR-0223"
  - "PR-0224"
  - "PR-0225"
acceptance_criteria:
  - "Given guest and authenticated Klassrumskartan now expose the same accessible grouping/seating surfaces, when a teacher uses those shared surfaces in either shell, then the visible layout and scroll behavior match instead of drifting by wrapper."
  - "Given the detached planner toolbar is supposed to read as the same sticky instrument in guest and authenticated mode, when the user scrolls, then the sticky offset and resting/stuck positions are derived from one shared viewport-relative shell contract rather than page-height or wrapper-specific positioning."
  - "Given `Grupper` currently collapses vertically when only a few groups exist, when the grouping workspace renders at the canonical `laptop` and `desktop` review widths, then the unassigned-student pool lane and grouping board lane both keep a shared `480px` minimum-height floor matching the current seating workspace viewport floor instead of shrinking to content."
  - "Given grouping buckets currently feel cramped, when the stabilized grouping workspace renders, then assigned student rows use a `56px` minimum height and empty group drop targets use a `112px` minimum height, replacing the current implicit `44px` and `88px` floors with one reviewable shared contract."
  - "Given a teacher starts a brand-new blank grouping draft in either guest or authenticated mode, when the new draft is seeded, then it starts with exactly 4 default groups instead of shell-specific defaults."
---

## Problem

Klassrumskartan already reuses many shared planner primitives across guest and
authenticated mode, but the overall shell contract is not frozen tightly
enough. Guest currently mirrors the authenticated planner through a parallel
wrapper instead of the exact same shell component, and that has already allowed
sticky-toolbar behavior and mode-switch layout parity to drift.

The grouping workspace also still sizes itself too much from current content.
When only a few groups exist, the unassigned-student pool becomes too short,
the board area feels twitchy, and the group cards read as cramped compared to
the calmer seating workspace.

Fresh grouping drafts also drift today: the guest/browser-owned seed path and
the authenticated/backend seed path do not agree on how many groups a brand-new
empty grouping draft should start with.

## Goal

Freeze one shared planner-layout tightening slice that keeps visible guest and
authenticated planner behavior aligned and stabilizes grouping height at common
desktop widths.

This task should:

- make guest/authenticated sticky-toolbar behavior feel like the same shell
- remove wrapper-specific sticky drift in favor of one shared offset contract
- give grouping a stable minimum vertical budget instead of content-collapse
- enlarge group buckets enough to reduce density without reopening the broader
  desktop-first workspace redesign

## Non-goals

- Reopening guest capability gating, auth upgrade behavior, or browser-owned
  guest-state semantics.
- Redesigning mobile layouts or changing the canonical desktop review widths.
- Reworking rules workspace composition or changing teacher workflow semantics.
- Using a guest-only patch when the visible behavior is supposed to be shared.

## Review gate

This slice requires
`docs/backlog/reviews/review-pr-0226-shared-planner-shell-parity-and-grouping-viewport-height-stabilization.md`
to clear before implementation begins.

## Frozen decisions

1. Accessible shared planner surfaces must behave the same in guest and
   authenticated mode.
   Guest may hide account-only controls, but any control or layout region that
   remains visible in both shells must follow the same layout and scroll
   behavior contract.

2. Sticky-toolbar positioning must be viewport-relative and shared.
   The sticky offset must not be derived from full page height, ad hoc wrapper
   padding, or a guest-only calculation. The authenticated shell is the
   current behavioral baseline, but the final rule must be shared by both
   shells rather than copied twice.

3. Grouping height must be stable.
   The grouping workspace must stop shrinking based on the current number of
   groups. At the canonical `laptop` and `desktop` review widths, the grouping
   board lane and unassigned-student pool lane must both keep a shared `480px`
   minimum-height floor, matching the current `RoomCanvas` viewport floor.

4. The unassigned student pool must keep the same stable vertical budget as
   the grouping board.
   It should not become visually tiny when there are only two to four groups,
   and it should satisfy the same `480px` minimum-height contract as the board.

5. Group cards must be taller.
   The current implicit `44px` assigned-row floor and `88px` empty drop-target
   floor should be replaced with explicit `56px` and `112px` floors. If these
   values move into shared tokens/utilities during implementation, the tests
   must assert the token-backed class or contract directly.

6. Fresh grouping drafts must start with 4 default groups in both guest and
   authenticated mode.
   This count is part of the parity contract and must not drift by shell or
   draft-owner path.

## Concrete sizing contract

- Desktop grouping board lane floor: `480px`
- Desktop grouping student-pool floor: `480px`
- Group-card assigned student row floor: `56px`
- Group-card empty drop-target floor: `112px`
- Fresh grouping draft default group count: `4`

## Implementation plan

1. Audit the current shell split and identify which sticky/layout rules are
   still duplicated between:
   - `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`
   - `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.vue`

2. Move the sticky-toolbar contract into one shared planner-shell rule path so
   both shells inherit the same viewport-relative sticky behavior.

3. Define a shared grouping height contract across:
   - `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.vue`
   - `frontend/apps/skriptoteket/src/views/apps/components/PlannerStudentPool.vue`
   - `frontend/apps/skriptoteket/src/views/apps/components/GroupBoard.vue`
   - `frontend/apps/skriptoteket/src/views/apps/components/GroupCard.vue`
   Freeze the grouping lane/pool floor at `480px` so the contract matches the
   current `RoomCanvas` seating viewport baseline rather than an inferred
   content-driven height.

4. Use the seating workspace vertical rhythm as the reference baseline where
   practical, so grouping does not feel like a shorter or more jittery sibling
   workspace.

5. Increase grouping bucket minimum heights to the explicit reviewable floors:
   - assigned student rows: `56px`
   - empty drop targets: `112px`
   Keep the result desktop-first and calm rather than cramped.

6. Add focused parity coverage for both authenticated and guest shells so
   shared behavior regressions are caught explicitly.

7. Add focused component-level assertions for the grouping-height contract so
   the slice does not rely on shell-only proof. The tests must verify the
   `480px` lane/pool floor and the `56px` / `112px` group-card floors directly.

8. Normalize the fresh grouping-draft seed count across guest and
   authenticated flows so both shells start a blank grouping draft with the
   same 4 default groups.

## Test plan

- Shell parity proof:
  - `pdm run fe-test src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/useClassroomPlannerGuestOverviewShell.spec.ts`
- Grouping-height contract proof:
  - `pdm run fe-test src/views/apps/components/GroupCard.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/PlannerGroupingWorkspacePane.smart-rules.spec.ts`
  - matching assertions must prove:
    - the grouping board lane and grouping student-pool lane keep the shared `480px` floor at the desktop breakpoint path
    - `GroupCard` uses `56px` assigned-row floors and `112px` empty drop-target floors
    - the shared min-height contract is asserted directly via the rendered class/token contract, not inferred only from screenshots
- Fresh grouping-draft parity proof:
  - `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py`
  - matching assertions must prove:
    - the guest grouping seed path preserves the classroom selection through grouping autosave
    - a fresh guest grouping draft starts with 4 groups
    - a fresh authenticated grouping draft also starts with 4 groups
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Live browser proof on both routes:
  - `http://127.0.0.1:5173/apps/classroom.group-seating-studio`
  - `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio`
- Manual review checklist:
  - verify the grouping and seating detached toolbars rest and stick at the
    same viewport-relative position in guest and authenticated mode
  - verify the sticky toolbar stays fully visible while scrolling and does not
    lag partly offscreen at the top edge
  - verify grouping with two to four groups keeps the documented `480px`
    student-pool/board floor instead of collapsing toward content height
  - verify group cards visibly reflect the documented `56px` / `112px` floors
    without clipping or breaking denser multi-group cases
  - verify a fresh grouping draft starts with 4 groups in both guest and
    authenticated mode

## Implementation Summary (as of 2026-04-06)

- Guest and authenticated planner shells now share one `PlannerWorkspaceModeSurface`
  wrapper plus the shared `plannerWorkspaceLayout.ts` contract for the detached
  sticky toolbar and pane shell.
- The grouping workspace now keeps a shared desktop `480px` lane floor and
  the group-card contract is frozen at `56px` assigned rows and `112px` empty
  drop targets.
- Guest grouping autosave now preserves the overview-selected classroom instead
  of clearing it to `null` during grouping saves, which keeps `Sittplatser`
  enabled after grouping mutations such as `Slumpa`.
- Fresh grouping drafts are now normalized to 4 default groups in both the
  guest/browser-owned seed path and the authenticated/backend lifecycle path.

## Rollback plan

- Revert the shared shell/sticky contract changes if they introduce new
  authenticated/guest drift or regress the accepted authenticated baseline.
- Revert the grouping height/card sizing changes if they cause clipping,
  overflow regressions, or unacceptable density loss at canonical desktop
  widths.
