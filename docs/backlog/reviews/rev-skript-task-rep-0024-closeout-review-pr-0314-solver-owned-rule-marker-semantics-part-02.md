---
type: review
id: REV-SKRIPT-TASK-REP-0024-CLOSEOUT-PART-02
title: 'Review: PR-0314 solver-owned rule marker semantics — part 02'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: REV-SKRIPT-TASK-REP-0024-CLOSEOUT
part: 2
---

- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerSmartRuleActions.ts:119`
     through `frontend/apps/skriptoteket/src/views/apps/classroomPlannerSmartRuleActions.ts:292`
     smart-rule mutations call `syncVisibleSessionBindings()` and
     `smartRuleLane.markDirty()`, but receive no diagnostic-clear callback.
   - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerStateSupport.ts:275`
     through `frontend/apps/skriptoteket/src/views/apps/classroomPlannerStateSupport.ts:278`
     shows `syncVisibleSessionBindings()` only syncs draft and roster lane
     bindings.
   - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerSeatRuleMarkers.ts:168`
     through `frontend/apps/skriptoteket/src/views/apps/classroomPlannerSeatRuleMarkers.ts:190`
     still accepts any diagnostic that matches the current target rule shape and
     visible assignment, even when the surrounding smart-rule set is locally
     dirty.

   Required fix:

   Clear stored diagnostics on every local smart-rule mutation before marking
   the smart-rule lane dirty, or carry a solver-input revision through the
   diagnostics and require that revision to match the current smart-rule/draft
   state before marker coloring.

2. Blocker: `PR-0313` still lacks the required real-device iPhone confirmation.

   Evidence:

   - `docs/backlog/prs/pr-0313-shared-phone-classroom-map-real-device-pinch-remediation.md:157`
     through `docs/backlog/prs/pr-0313-shared-phone-classroom-map-real-device-pinch-remediation.md:181`
     explicitly keeps `PR-0313` `in_progress` until actual iPhone confirmation
     is recorded.
   - The focused component proof is useful and now checks rendered cell-size
     changes, but it is still synthetic DOM touch input rather than the failing
     real phone path.

   Required fix:

   Record successful real-device confirmation for phone `Sittplatser` and phone
   `Regler` / `Fast plats`, or attach a browser-proof path that genuinely
   exercises the same WebKit gesture ownership failure mode.

### Third-Pass Remediation Notes

Implemented after the second-pass `changes_requested` verdict on 2026-05-10.
This review record remains `changes_requested` until a new review confirms the
fix and `PR-0313` receives real-device phone proof.

- `classroomPlannerSmartRuleActions.ts` now accepts the shared diagnostic-clear
  callback and calls it for local smart preference, near-teacher,
  relationship-rule, and fixed-seat rule mutations before dirty smart-rule
  state can reuse stale diagnostics.
- `classroomPlannerSmartRuleActions.spec.ts` now proves direct smart-rule
  mutations clear stored diagnostics.
- The near-limit frontend files were split into SRP modules instead of being
  line-shaved:
  `classroomPlannerFixedSeatRuleActions.ts`,
  `classroomPlannerDerivedState.ts`,
  `classroomPlannerGuestDraftHistoryActions.ts`,
  `phoneClassroomSeatMapLayout.ts`, and
  `useClassroomPlannerRuleDiagnostics.ts`.

### Second-Pass Verification

- `pdm run fe-test -- --run classroomPlannerSeatRuleMarkers PlannerPhoneClassroomSeatMap useRoomTouchViewportGestures`
- `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_keep_near_geometry.py tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_solver.py -m simulation --override-ini addopts='' -q`

### Third-Pass Re-review

**Reviewer:** `codex`
**Date:** `2026-05-10`
**Verdict:** `changes_requested`

### Accepted Fixes

- `PR-0314` diagnostic rehydration is accepted. `GetDraftWorkspaceHandler` now
  recomputes seating diagnostics from persisted draft, roster, template,
  smart-rule, and assignment truth; grouping workspaces do not touch the
  smart-rule repository.
- Authenticated Smart-run, public Smart-run, and authenticated workspace-load
  diagnostics now carry additive `freshness_key` values, and OpenAPI frontend
  types include the expanded workspace/diagnostic contract.
- Frontend marker rendering now refuses soft-rule diagnostics without a
  freshness key and still requires current rule shape plus current assignment
  matches before applying tones.

### Remaining Required Changes

1. Blocker: `PR-0313` can drop the final gesture-camera scroll update when a
   touch gesture ends before the queued animation frame runs.

   Evidence:

   - `frontend/apps/skriptoteket/src/views/apps/useAnchoredRoomViewportZoom.ts`
     schedules active gesture-camera scroll compensation through
     `requestAnimationFrame`.
   - `endGestureCamera()` clears the pending point/scale and cancels the pending
     frame before applying it.
   - `useRoomTouchViewportGestures.ts` invokes `onGestureEnd` as soon as the
     touch count drops below two, so a normal `touchmove` -> `touchend` sequence
     can leave the latest scale applied without the matching scroll correction.

   Required fix:

   Flush the pending camera update before clearing/canceling gesture-camera
   state, or leave the queued frame with the captured camera data needed to
   apply the final scroll. Add a focused test where `zoomByFactor()` queues a
   frame, `endGestureCamera()` runs before the frame callback, and the viewport
   still receives the final anchored scroll. Mirror that at component level with
   `touchmove` followed by `touchend` before RAF.

2. Blocker: `PR-0313` still lacks the required real-device iPhone confirmation.

   Required fix:

   After the final-frame flush is repaired, record successful phone
   confirmation for both phone `Sittplatser` and phone `Regler` / `Fast plats`,
   or attach proof that exercises the same WebKit gesture ownership path.

### Third-Pass Verification

- `pdm run fe-test -- --run classroomPlannerSeatRuleMarkers classroomPlannerStateSupport useAnchoredRoomViewportZoom useRoomTouchViewportGestures PlannerPhoneClassroomSeatMap`
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_smart_rule_diagnostic_freshness.py tests/unit/application/apps/classroom_planner/test_draft_workspace_diagnostics.py tests/unit/web/apps/classroom_planner/test_draft_workspace_api.py tests/unit/web/apps/classroom_planner/test_smart_seating_api.py -q`
