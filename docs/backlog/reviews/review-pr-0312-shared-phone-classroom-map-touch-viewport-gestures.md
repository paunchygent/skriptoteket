---
type: review
id: REV-PR-0312
title: "Review: PR-0312 shared phone classroom-map touch viewport gestures"
status: changes_requested
owners: "agents"
created: 2026-05-10
updated: 2026-05-10
reviewer: "codex"
prs:
  - PR-0312
links:
  - ST-24-04
  - ST-27-09
  - ST-29-16
  - ST-29-17
  - PR-0310
  - PR-0311
---

## TL;DR

`PR-0312` is not approved yet. The shared Vue gesture shape is small and the
focused tests are green, but the phone pinch contract is still not proven on
the real browser path because the touch targets do not declare touch gesture
arbitration and the retained browser helper fabricates DOM touch events.

## Problem Statement

This review checks whether `PR-0312` can safely close the shared phone
classroom-map pinch-zoom lane across the room-template builder, phone
`Sittplatser`, and phone `Regler` / `Fast plats` maps without regressing the
existing tap, short-press, long-press, fixed-seat selection, desktop hover, or
button-zoom contracts.

## Proposed Solution

The implementation adds `useRoomTouchViewportGestures`, extends
`useRoomViewportZoom` with direct zoom-factor APIs, wires the room-template
builder viewport and simplified phone classroom map to native touch events, and
extends the retained PR-0310/PR-0311 browser proofs with synthetic pinch
gestures.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0312-shared-phone-classroom-map-touch-viewport-gestures.md` | Scope, acceptance criteria, proof obligations | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/useRoomViewportZoom.ts` | Direct zoom-factor API and clamp semantics | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/useRoomTouchViewportGestures.ts` | Gesture recognition and tap suppression | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/components/RoomTemplateBuilderSurface.vue` | Builder pinch integration and single-tap preservation | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerPhoneClassroomSeatMap.vue` | Phone seating/fixed-seat pinch integration and domain-action suppression | 15 min |
| `frontend/apps/skriptoteket/src/assets/klassrumskartan-phone-workspace.css` | Phone map geometry and browser touch arbitration | 5 min |
| `scripts/_playwright_touch.py` | Retained browser proof helper fidelity | 10 min |
| `scripts/playwright_pr_0310_phone_fixed_seat_rules_map.py` | Phone `Sittplatser` and `Fast plats` proof scope | 10 min |
| `scripts/playwright_pr_0311_phone_room_template_modal.py` | Phone room-template builder proof scope | 10 min |

**Total estimated time:** ~85 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Use a shared composable instead of component-local gesture code | Keeps the three phone map surfaces from drifting | [x] |
| Extend the existing viewport zoom model with direct scale/factor APIs | Reuses the existing clamp and fit-to-view model | [x] |
| Preserve one-finger domain actions unless a two-finger gesture is recognized | Matches the PR acceptance criteria and PR-0310/PR-0311 contracts | [x] |
| Treat synthetic touch-event browser proof as sufficient live mobile proof | It bypasses browser gesture arbitration and is not enough for this contract | [ ] |

## Review Checklist

- [x] Scope is bounded to phone classroom-map viewport gestures.
- [x] Docs-as-code authority exists under `PR-0312`.
- [x] Shared zoom-factor clamp behavior has focused tests.
- [x] Builder and simplified map tap suppression has focused tests.
- [x] Existing desktop hover-preview behavior remains covered.
- [ ] Browser touch arbitration is declared and proven on the touched targets.

## Review Feedback

**Reviewer:** `codex`
**Date:** `2026-05-10`
**Verdict:** `changes_requested`

### Required Changes

1. Add browser touch-arbitration CSS and proof for the real phone pinch path.

   `RoomTemplateBuilderSurface.vue` binds `touchstart`, `touchmove`,
   `touchend`, and `touchcancel` directly on the builder viewport, and
   `PlannerPhoneClassroomSeatMap.vue` does the same on the phone classroom map.
   The phone map CSS only declares overflow and momentum scrolling. None of
   the touched targets declare `touch-action`, so the browser can still reserve
   native panning or pinch handling before the Vue touch handlers call
   `preventDefault()`.

   That is a contract gap for this PR because the acceptance criteria require
   phone pinch zoom to work on real classroom-map surfaces, not only in jsdom or
   fabricated event paths. The retained proof helper in
   `scripts/_playwright_touch.py` constructs plain DOM `Event` instances and
   injects `touches`, `targetTouches`, and `changedTouches`; it proves the app's
   handler logic responds to a synthetic touch list, but it does not prove that
   a mobile browser will let the app own the gesture sequence.

   Required shape:

   - Declare an explicit touch-action contract on the builder viewport and the
     simplified phone classroom map. Preserve intended one-finger scrolling by
     choosing the narrowest value that disables browser-owned pinch while
     keeping the map scrollable, for example `touch-action: pan-x pan-y` if
     validated on the target browsers.
   - Extend focused tests or retained browser proof to assert the computed
     touch-action on both targets.
   - Keep the synthetic pinch helper if needed, but label it as handler proof,
     not as the only browser proof for native gesture ownership.
   - Add a live/manual or automation-backed mobile proof note for iPhone-sized
     Chromium/WebKit behavior before approving the lane.

   Files to fix:

   - `frontend/apps/skriptoteket/src/views/apps/components/RoomTemplateBuilderSurface.vue`
   - `frontend/apps/skriptoteket/src/views/apps/components/PlannerPhoneClassroomSeatMap.vue`
   - `frontend/apps/skriptoteket/src/assets/klassrumskartan-phone-workspace.css`
   - `scripts/playwright_pr_0310_phone_fixed_seat_rules_map.py`
   - `scripts/playwright_pr_0311_phone_room_template_modal.py`

   Proof requirement:

   - `pdm run fe-test -- --run useRoomViewportZoom useRoomTouchViewportGestures RoomTemplateBuilderSurface CreateRoomTemplateModal PlannerPhoneClassroomSeatMap PlannerPhoneFixedSeatRulePanel PlannerSeatingWorkspacePane`
   - `pdm run fe-type-check`
   - `pdm run fe-lint`
   - `pdm run ruff check scripts/_playwright_touch.py scripts/playwright_pr_0310_phone_fixed_seat_rules_map.py scripts/playwright_pr_0311_phone_room_template_modal.py`
   - retained browser proof for the phone builder, phone `Sittplatser`, and
     phone `Regler` / `Fast plats` targets, with computed touch-action evidence

### Suggestions (Optional)

- Consider surfacing visible zoom controls on the simplified phone classroom
  map in a follow-up if the team wants the "buttons remain accessible fallback"
  criterion to apply uniformly to every phone map surface, not only the
  room-template builder.

### Passing Checks Observed

- `pdm run fe-test -- --run useRoomViewportZoom useRoomTouchViewportGestures RoomTemplateBuilderSurface CreateRoomTemplateModal PlannerPhoneClassroomSeatMap PlannerPhoneFixedSeatRulePanel PlannerSeatingWorkspacePane`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run pytest tests/unit/scripts/test_playwright_script_surface.py -q`
- `pdm run ruff check scripts/_playwright_touch.py scripts/playwright_pr_0310_phone_fixed_seat_rules_map.py scripts/playwright_pr_0311_phone_room_template_modal.py`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0312` | Recorded retained review verdict as `changes_requested` with the browser touch-arbitration blocker and observed verification evidence. |
| 2 | `PR-0312` | Remediation added `touch-action: pan-x pan-y` to the phone builder and simplified phone map targets, replaced fabricated retained pinch events with CDP touch input, and added computed `touch-action` assertions to the retained phone proofs. Pending re-review. |
