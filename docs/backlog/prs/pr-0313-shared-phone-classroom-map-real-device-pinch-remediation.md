---
type: pr
id: PR-0313
title: "Shared phone classroom-map real-device pinch remediation"
status: done
owners: "agents"
created: 2026-05-10
updated: 2026-05-10
stories:
  - "ST-27-09"
  - "ST-29-16"
  - "ST-29-17"
tags: ["frontend", "ux", "klassrumskartan", "small-screen", "touch", "classroom-map"]
dependencies:
  - "PR-0310"
  - "PR-0312"
acceptance_criteria:
  - "Given the phone `Sittplatser` simplified classroom map renders on an iPhone-sized viewport, when the teacher performs a real two-finger pinch on the map, then the map visibly zooms without removing, moving, or swapping a seated student."
  - "Given the phone `Regler` `Fast plats` simplified classroom map renders on an iPhone-sized viewport, when the teacher performs a real two-finger pinch on the map, then the map visibly zooms without selecting, clearing, or saving a fixed-seat binding."
  - "Given a recognized pinch gesture ends on either simplified map, when the browser dispatches a follow-up tap/click, then the map suppresses that follow-up domain action exactly once."
  - "Given one-finger interaction is used on either simplified map, when the teacher taps or short/long-presses a seat, then the existing `PR-0310` seat selection, removal, move, and swap semantics remain unchanged."
  - "Given browser proof runs for the phone simplified map, when the proof asserts zoom, then it proves native/browser-level input ownership rather than only fabricated DOM `TouchEvent` handler invocation."
---

## Problem

`PR-0312` added a shared touch-gesture composable and proved handler behavior
with Chromium-level retained proof. Real iPhone testing now shows that the
room-template builder modal can be pinched, but the simplified phone classroom
maps in `Sittplatser` and `Regler` / `Fast plats` do not visibly respond to the
same touch gesture.

This is a phone usability blocker because those simplified maps are now the
primary small-screen representation for seating and fixed-seat authoring.
Teachers cannot rely on tiny controls or desktop-scale map affordances to
inspect the classroom on a phone.

## Goal

Make the simplified phone classroom map use the same real-device pinch behavior
that works in the room-template builder modal.

The fix must cover both consumers of `PlannerPhoneClassroomSeatMap.vue`:

- phone `Sittplatser`
- phone `Regler` / `Fast plats`

## Non-goals

- No solver, Smart seating, rule persistence, or marker semantics change.
- No room-template builder redesign; it is the working reference path.
- No desktop/tablet `RoomCanvas` replacement.
- No new third-party gesture dependency unless native touch and platform
  gesture events cannot satisfy the iPhone path.
- No removal of existing single-tap, short-press, or long-press semantics.

## Design Direction

Treat the room-template builder as the behavioral reference and the simplified
phone map as the broken consumer.

Implementation should:

- keep `useRoomViewportZoom` as the single zoom model
- keep `useRoomTouchViewportGestures` as the shared gesture owner
- ensure the simplified map target is bound with non-passive native gesture
  listeners where needed
- include iPhone/Safari-compatible gesture support where browser proof shows
  Chromium touch input is not enough
- keep one-finger seat interactions outside the two-finger gesture path

`touch-action` and `preventDefault()` must be treated as browser-arbitration
evidence, not as sufficient proof by themselves. The retained proof must still
assert the computed gesture contract, but the implementation must be verified
against the actual simplified-map zoom percent or visual scale state.

## Frontend Entry Points

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerPhoneClassroomSeatMap.vue`
- `frontend/apps/skriptoteket/src/views/apps/useRoomTouchViewportGestures.ts`
- `frontend/apps/skriptoteket/src/views/apps/useRoomViewportZoom.ts`
- `frontend/apps/skriptoteket/src/assets/klassrumskartan-phone-workspace.css`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerPhoneClassroomSeatMap.spec.ts`
- `scripts/_playwright_touch.py`
- `scripts/playwright_pr_0310_phone_fixed_seat_rules_map.py`

## Implementation Plan

1. Add a failing focused component test that exercises the simplified map
   native gesture path and verifies the zoom percent changes while the next
   click is suppressed.
2. Strengthen `useRoomTouchViewportGestures` so consumers can attach
   non-passive element-level touch listeners through the composable instead of
   relying only on template listeners.
3. Add platform gesture-event support only if needed for the iPhone path, while
   keeping it isolated in the shared composable.
4. Wire `PlannerPhoneClassroomSeatMap.vue` through the strengthened shared
   gesture binding without growing the component beyond the strict SRP/file
   size boundary.
5. Keep `PR-0310` single-tap, short-press removal, and long-press move/swap
   tests green.
6. Extend the retained phone proof so both phone `Fast plats` and phone
   `Sittplatser` assert that pinch changes the simplified map zoom state and
   does not trigger the next domain action.
7. Record live/manual iPhone verification in `.codex/handoff.md` if automation
   cannot fully reproduce WebKit gesture ownership.

## Test Plan

- `pdm run fe-test -- --run useRoomTouchViewportGestures PlannerPhoneClassroomSeatMap PlannerPhoneFixedSeatRulePanel PlannerSeatingWorkspacePane`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run pytest tests/unit/scripts/test_playwright_script_surface.py -q`
- `pdm run ruff check scripts/_playwright_touch.py scripts/playwright_pr_0310_phone_fixed_seat_rules_map.py`
- `pdm run python -m scripts.playwright_pr_0310_phone_fixed_seat_rules_map --start-backend --start-vite`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback Plan

Revert the simplified-map gesture binding changes while leaving `PR-0310`
phone maps, short/long-press seating semantics, fixed-seat authoring, and the
room-template builder modal untouched.

## Implementation Closeout

Implemented on 2026-05-10.

- Strengthened `useRoomTouchViewportGestures` so classroom-map surfaces can
  bind non-passive touch listeners directly to their viewport element through a
  reusable target-ref API.
- Added platform `gesturestart` / `gesturechange` support in the shared
  composable for iPhone/Safari-style pinch gesture dispatch while keeping
  existing two-touch distance handling for browser paths that expose
  `TouchEvent.touches`.
- Wired both `RoomTemplateBuilderSurface.vue` and
  `PlannerPhoneClassroomSeatMap.vue` through the same target-ref binding so the
  working builder path and simplified phone maps share one SRP-friendly gesture
  owner.
- Preserved `PR-0310` one-finger seat interactions: fixed-seat selection,
  short-press removal, and long-press move/swap remain outside the two-finger
  gesture path.

Verification:

- `pdm run fe-test -- --run useRoomTouchViewportGestures RoomTemplateBuilderSurface PlannerPhoneClassroomSeatMap PlannerPhoneFixedSeatRulePanel PlannerSeatingWorkspacePane RoomCanvas PlannerRulesMapCanvas PlannerRulesSeatNode`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run pytest tests/unit/scripts/test_playwright_script_surface.py -q`
- `pdm run ruff check scripts/_playwright_touch.py scripts/playwright_pr_0310_phone_fixed_seat_rules_map.py`
- `pdm run python -m scripts.playwright_pr_0310_phone_fixed_seat_rules_map --start-backend --start-vite`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`
