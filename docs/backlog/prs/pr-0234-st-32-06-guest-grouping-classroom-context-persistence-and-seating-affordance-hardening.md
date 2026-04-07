---
type: pr
id: PR-0234
title: "ST-32-06 follow-up: guest grouping classroom-context persistence and seating affordance hardening"
status: done
owners: "agents"
created: 2026-04-07
updated: 2026-04-07
stories:
  - "ST-32-06"
tags:
  [
    "frontend",
    "klassrumskartan",
    "public-access",
    "guest-workspace",
    "grouping",
    "seating",
    "regression-hardening",
  ]
dependencies:
  - "ADR-0079"
  - "ADR-0080"
  - "ST-32-06"
  - "PR-0223"
  - "PR-0231"
acceptance_criteria:
  - "Given the public guest overview already has a selected roster and classroom, when the user opens `Grupper`, then the browser-owned guest shell preserves that classroom as the current selected classroom until the user explicitly changes or clears it."
  - "Given the grouping draft remains classroom-aware from overview context, when guest grouping draft hydration, autosave, or overview round-trips run, then neither `ui_state.selected_template_local_id` nor the grouping draft/template context is silently cleared."
  - "Given guest grouping no longer has a classroom context, when the planner shell renders `Sittplatser`, then the segmented toggle shows the seating affordance as disabled/greyed out with the approved prerequisite hint instead of appearing clickable while doing nothing."
  - "Given the regression is investigated through docs-as-code first, when implementation starts, then focused frontend regression specs already fail on both the lost-classroom state seam and the stale seating-affordance seam."
---

## Problem

The public guest Klassrumskartan shell currently regressed in one classroom
context boundary:

- select a class and a classroom in overview
- enter `Grupper`
- return to overview or look at the planner shell state

The selected classroom has been silently cleared even if the user did not
change it, and `Sittplatser` may still look enabled in the planner rail even
though clicking it no longer opens the seating workspace.

This is not an acceptable teacher-facing compromise because the shell presents
false affordance state and silently loses a user decision that should remain
stable until explicitly changed.

## Root cause assessment

The regression comes from two connected frontend ownership mistakes inside the
public guest shell.

1. The overview-to-grouping transition discards the classroom selection.
   - [PlannerClassWorkspace.vue](../../../frontend/apps/skriptoteket/src/views/apps/components/PlannerClassWorkspace.vue)
     currently emits `open-grouping` with `templateId: null`.
   - [useClassroomPlannerGuestController.ts](../../../frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerGuestController.ts)
     then resolves the grouping draft with `templateId = null` instead of the
     selected overview classroom.
   - [classroomPlannerGuestDraftWorkspace.ts](../../../frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestDraftWorkspace.ts)
     and [classroomPlannerGuestDraftMutations.ts](../../../frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestDraftMutations.ts)
     persist that null context back into both the grouping draft and
     `ui_state.selected_template_local_id`.

2. The guest planner shell computes seating availability from stale pending ids.
   - [ClassroomPlannerGuestWorkspaceShell.vue](../../../frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.vue)
     seeds `pendingGroupingTemplateId` and `pendingSeatingTemplateId` from the
     old selection and then treats those refs as higher priority than the live
     prop-driven selection state.
   - After the real selected classroom has been cleared, the shell can still
     think a classroom exists and therefore leaves `Sittplatser` visually
     enabled even though the controller can no longer open it.

3. The defect is frontend-local.
   - No backend route, authenticated seam, or guest-upgrade transport change is
     involved in this regression.
   - `PR-0233` did not introduce this behavior; it exposed a nearby workflow
     during local verification, but the actual defect lives in the public guest
     planner state seam.

## Goal

Repair the public guest classroom-context seam so overview selection,
grouping-context hydration, and seating prerequisite affordances all describe
the same truth.

## Non-goals

- Changing authenticated planner behavior.
- Reopening the approved guest/auth export or upgrade boundaries.
- Redesigning the grouping task model into a mandatory-classroom flow.
- Bundling guest undo/redo or export implementation into this remediation.

## Implementation plan

1. Lock the regression with focused failing specs before changing production code.
   - Add a controller regression for overview -> grouping entry that proves the
     selected classroom is currently lost.
   - Add a workspace-shell regression that proves `Sittplatser` can remain
     visually enabled after classroom context is gone.

2. Repair the grouping-entry contract at the first seam.
   - Preserve the selected overview classroom when opening grouping from the
     public guest class workspace.
   - Keep that context through grouping draft creation/reuse and overview
     round-trips unless the user explicitly clears or changes it.

3. Repair the seating-affordance truth source.
   - Make the shell derive seating availability from the real live context, not
     stale pending refs left over from an earlier selection.
   - Keep the approved prerequisite hint and disabled styling aligned with the
     actual controller behavior.

4. Re-prove the public guest flow live.
   - Use the local public route
     `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio`.
   - Verify class + classroom selection survives entry into `Grupper`.
   - Verify `Sittplatser` greys out immediately whenever classroom context is
     truly absent.

## Test plan

- Failing-first regression proof:
  - `pdm run fe-test -- --run src/views/apps/useClassroomPlannerGuestGroupingContext.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts`
- After the fix:
  - rerun the same regression command until green
  - rerun any touched guest overview/workspace shell specs
  - `pdm run fe-type-check`
  - `pdm run docs-validate`
- Live public browser proof on `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio`

## Current evidence

The new regression specs are already added locally and currently fail in the
expected way:

- [useClassroomPlannerGuestGroupingContext.spec.ts](../../../frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerGuestGroupingContext.spec.ts)
  proves `openGroupingWorkspace()` clears `selectedTemplateId` to `null`
  instead of preserving the selected classroom.
- [ClassroomPlannerGuestWorkspaceShell.spec.ts](../../../frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts)
  proves the guest shell still reports no seating disabled reason after the
  classroom context has been cleared.

## Local implementation state

The assessed remediation patch is now implemented locally and the regression
lane itself is green:

- [frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerGuestController.ts](../../../frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerGuestController.ts)
  now opens brand-new or reused guest grouping drafts with the current selected
  classroom context instead of always forcing `templateId = null`.
- [frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.vue](../../../frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.vue)
  now derives seating availability from the live selected classroom context
  instead of stale pending template refs.
- [frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestTemplateContext.ts](../../../frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestTemplateContext.ts)
  centralizes the public guest rule for which classroom is currently selected.

Targeted verification now passes:

- `pdm run fe-test -- --run src/views/apps/useClassroomPlannerGuestGroupingContext.spec.ts src/views/apps/useClassroomPlannerGuestOverviewShell.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts`
- `pdm run fe-type-check`
- Live public browser proof on `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio`
  confirmed:
  - overview -> `Grupper` preserved `ui_state.selected_template_local_id = template-1`
  - the persisted grouping draft also kept `template_local_id = template-1`
  - a forced grouping-without-classroom state rendered `Sittplatser` as
    disabled with title `Skapa eller välj först ett klassrum.`

Full frontend verification is now green after the documented follow-up lanes:

- [PR-0235](pr-0235-st-24-04-shared-room-viewport-fit-scale-contract-reassessment-and-test-realignment.md)
  closed the shared framed viewport fit-scale contract and restored the
  explicit `100%` fit cap for smaller rooms.
- [PR-0236](pr-0236-st-32-06-overview-action-capability-test-realignment-and-import-boundary-assertions.md)
  realigned the stale isolated roster-overview spec with the capability-gated
  action-footer contract.
- `pdm run fe-test` now passes across the full frontend suite.

## Rollback plan

- Revert only the public guest grouping-context and prerequisite-affordance
  patch if it unexpectedly changes the approved guest grouping model.
- Do not roll back unrelated guest export, authenticated upgrade, or Smart
  parity seams as part of this remediation.

## References

- Story owner:
  [ST-32-06](../stories/story-32-06-klassrumskartan-demo-adoption-on-the-public-browser-workspace-profile.md)
- Public browser-workspace baseline:
  [PR-0223](pr-0223-st-32-06-public-klassrumskartan-demo-capability-matrix-and-browser-workspace-adoption.md)
- Guest Smart parity slice:
  [PR-0231](pr-0231-st-32-06-guest-regler-workspace-solver-smart-parity-and-expandable-smart-settings-drawer.md)
- Guest local continuity/export slice that follows this resolved remediation:
  [PR-0232](pr-0232-st-32-06-guest-local-draft-parity-direct-download-export-and-account-only-history-affordance-polish.md)
