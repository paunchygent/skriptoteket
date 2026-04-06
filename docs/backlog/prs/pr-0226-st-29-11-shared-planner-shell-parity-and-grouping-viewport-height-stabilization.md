---
type: pr
id: PR-0226
title: "ST-29-11: shared planner shell parity and grouping viewport-height stabilization"
status: ready
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
  - "Given `Grupper` currently collapses vertically when only a few groups exist, when the grouping workspace renders with a low group count, then the unassigned-student pool and group board keep a stable minimum viewport-oriented height aligned to the seating workspace baseline instead of shrinking to content."
  - "Given grouping buckets currently feel cramped, when the stabilized grouping workspace renders, then each group card and empty drop target is materially taller (about 25 percent taller than the current baseline) so the desktop workspace reads calmer and less twitchy."
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
   groups. Its minimum height should be anchored to a seating-workspace or
   viewport budget so the workspace reads like one stable desktop instrument.

4. The unassigned student pool must keep the same stable vertical budget as
   the grouping board.
   It should not become visually tiny when there are only two to four groups.

5. Group cards must be taller.
   Each group bucket and its empty drop zone should be about 25 percent taller
   than the current baseline so the workspace is less cramped and less twitchy.

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

4. Use the seating workspace vertical rhythm as the reference baseline where
   practical, so grouping does not feel like a shorter or more jittery sibling
   workspace.

5. Increase grouping bucket minimum heights and empty drop-target heights by
   roughly 25 percent, keeping the result desktop-first and calm rather than
   cramped.

6. Add focused parity coverage for both authenticated and guest shells so
   shared behavior regressions are caught explicitly.

## Test plan

- `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts`
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
  - verify grouping with two to four groups keeps a stable, tall enough student
    pool and board area
  - verify group cards read about 25 percent taller than the prior cramped
    baseline without breaking denser multi-group cases

## Rollback plan

- Revert the shared shell/sticky contract changes if they introduce new
  authenticated/guest drift or regress the accepted authenticated baseline.
- Revert the grouping height/card sizing changes if they cause clipping,
  overflow regressions, or unacceptable density loss at canonical desktop
  widths.
