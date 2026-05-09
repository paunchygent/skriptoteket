---
type: pr
id: PR-0312
title: "Shared phone classroom-map touch viewport gestures"
status: in_progress
owners: "agents"
created: 2026-05-10
updated: 2026-05-10
stories:
  - "ST-24-04"
  - "ST-27-09"
  - "ST-29-16"
  - "ST-29-17"
tags: ["frontend", "ux", "klassrumskartan", "small-screen", "touch", "classroom-map"]
dependencies:
  - "PR-0310"
  - "PR-0311"
acceptance_criteria:
  - "Given the room-template modal renders on a phone-sized viewport, when the teacher pinches on the classroom builder map, then the map zoom changes from the shared viewport zoom model without requiring the small `−`, `+`, or `Anpassa` buttons."
  - "Given the phone `Sittplatser` simplified classroom map renders, when the teacher pinches on the map, then the same shared touch viewport behavior zooms the classroom map without firing the seat short-press remove or long-press move/swap action."
  - "Given the phone `Regler` `Fast plats` classroom map renders, when the teacher pinches on the map, then the same shared touch viewport behavior zooms the seat picker without selecting or clearing the pending fixed-seat binding."
  - "Given a single tap happens on any supported phone classroom map, when no pinch gesture has been recognized, then existing tap placement, seat selection, removal, and fixed-seat binding semantics remain unchanged."
  - "Given a pinch or pan gesture has been recognized, when the browser dispatches a follow-up click/tap event, then the map suppresses that follow-up action so the teacher is not punished with an accidental seat placement, removal, or selection."
  - "Given desktop or laptop pointer-hover surfaces render, when the teacher uses a mouse or trackpad, then existing hover ghost previews, drag/drop behavior, scroll containment, and button zoom controls remain available."
  - "Given zoom controls remain visible, when touch gestures are implemented, then the buttons continue to work as accessible fallback controls and for users who do not use pinch gestures."
---

## Problem

`PR-0311` made the phone room-template modal usable by stabilizing the footer,
required-name recovery, and touch no-hover behavior. It did not add direct
touch viewport gestures. Phone users still have to rely on small `−`, `+`, and
`Anpassa` buttons to inspect or edit a classroom map.

That limitation now appears in several related surfaces:

- the create/edit classroom builder map in the room-template modal
- the phone `Sittplatser` simplified classroom map
- the phone `Regler` `Fast plats` fixed-seat classroom map

Each surface represents the same product idea: a classroom-relative map that
must be inspectable on a small touchscreen. Implementing pinch behavior in only
one component would create drift and would likely reintroduce gesture conflicts
with tap-to-place, short-press remove, long-press move/swap, or fixed-seat
selection.

## Goal

Add a shared touch viewport gesture contract for phone classroom-map surfaces.

The teacher should be able to pinch the map to inspect and edit the classroom
without depending on the tiny zoom buttons. The implementation should reuse the
existing room viewport zoom model and keep every map's domain interaction
unchanged unless a pinch gesture is actively in progress.

The shared behavior should cover:

- create/edit classroom builder map
- phone-only seating workspace classroom map
- phone `Fast plats` rule-authoring classroom map
- future small-screen classroom-map surfaces that use the same viewport model

## Non-goals

- No saved classroom-template data-model change.
- No solver, rule persistence, Smart seating, or share/export change.
- No desktop redesign and no removal of desktop hover previews.
- No replacement of existing button zoom controls; buttons remain as fallback.
- No new map engine, canvas renderer, or third-party gesture dependency unless
  native pointer/touch events prove insufficient during implementation.
- No attempt to make every desktop `RoomCanvas` map pinch-aware in this slice
  unless it is needed to share the phone implementation safely.

## Design Direction

Use a shared gesture abstraction rather than component-specific event logic.

Preferred shape:

- extend `useRoomViewportZoom` with a direct zoom API, such as
  `setManualZoomScale` or `adjustZoomByFactor`, while preserving the existing
  stepped `zoomIn`, `zoomOut`, and `resetZoom` API
- add a focused touch gesture composable, for example
  `useRoomTouchViewportGestures`
- let the composable own active touch/pointer tracking, pinch distance,
  gesture recognition, and follow-up tap suppression
- keep panning conservative at first: use the existing scroll container for map
  movement unless browser proof shows that one-finger or two-finger panning must
  be added to make pinch zoom usable
- expose a small prop/event contract so map components can opt into touch
  gestures without learning each other's domain actions

Gesture semantics:

- one finger: preserve existing tap, placement, selection, short-press, and
  long-press behavior
- two fingers: pinch zooms the viewport and suppresses domain actions until the
  gesture has ended cleanly
- after a recognized pinch: suppress the browser's follow-up click/tap event
  for the affected gesture sequence
- buttons: still call the same viewport zoom API and remain visible/reachable

## Current Frontend Entry Points

- Shared zoom model:
  `frontend/apps/skriptoteket/src/views/apps/useRoomViewportZoom.ts`
- Builder state using the shared zoom model:
  `frontend/apps/skriptoteket/src/views/apps/useRoomTemplateEditorState.ts`
- Create/edit classroom builder surface:
  `frontend/apps/skriptoteket/src/views/apps/components/RoomTemplateBuilderSurface.vue`
- Room-template modal shell:
  `frontend/apps/skriptoteket/src/views/apps/components/CreateRoomTemplateModal.vue`
- Simplified phone classroom map:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerPhoneClassroomSeatMap.vue`
- Phone fixed-seat panel using the simplified map:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerPhoneFixedSeatRulePanel.vue`
- Phone seating workspace using the simplified map:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.vue`
- Existing phone touch tests:
  `frontend/apps/skriptoteket/src/views/apps/components/CreateRoomTemplateModal.phone.spec.ts`
  and
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerPhoneClassroomSeatMap.spec.ts`
- Retained browser proofs:
  `scripts/playwright_pr_0310_phone_fixed_seat_rules_map.py` and
  `scripts/playwright_pr_0311_phone_room_template_modal.py`

## Implementation Plan

1. Add focused tests around the shared zoom model before changing component
   behavior.
   - direct scale adjustment clamps to the existing min/max zoom limits
   - stepped zoom buttons still use the same model
   - reset returns to fit-to-view
2. Add the shared touch gesture composable.
   - track active touch/pointer ids and positions
   - detect two-pointer pinch distance changes
   - convert pinch delta into direct zoom factor updates
   - expose whether a gesture is active or has just suppressed a tap
3. Integrate the gesture layer into `RoomTemplateBuilderSurface.vue`.
   - attach gesture handlers to the scroll/viewport region, not to every cell
   - keep single-tap `Sittplats` placement/removal unchanged
   - keep touch no-hover suppression from `PR-0311`
4. Integrate the same gesture layer into `PlannerPhoneClassroomSeatMap.vue`.
   - preserve short-press removal
   - preserve long-press move/swap
   - suppress both paths when a pinch gesture is recognized
   - preserve fixed-seat seat selection when a single tap is used
5. Keep button zoom controls as fallback.
   - no copy-heavy explanation in the UI
   - no hidden gesture-only affordance
6. Add focused component tests.
   - builder pinch changes zoom without placing a seat
   - builder single tap still creates/removes a real seat
   - phone seating map pinch does not emit remove/move/swap
   - phone fixed-seat map pinch does not emit seat selection
   - button zoom still emits or updates exactly as before
7. Extend retained browser proof.
   - phone room-template modal: pinch zoom changes the builder zoom percent and
     a following tap does not accidentally create/remove a seat
   - phone `Sittplatser`: pinch zoom changes map scale without firing
     short-press removal
   - phone `Regler` `Fast plats`: pinch zoom changes map scale without changing
     pending fixed-seat selection
   - assert the computed `touch-action` contract on each touched map target
     before dispatching the pinch input path
8. Update docs closeout with proof commands and artifact paths.

## Stop Conditions

Stop and ask before implementation continues if the slice requires:

- a third-party gesture library
- changing saved room-template, seating draft, or smart-rule payloads
- replacing the simplified phone classroom map renderer
- removing existing zoom buttons
- changing desktop hover previews, drag/drop, or mouse behavior
- broadening into a full pan/kinetic-scrolling system rather than a bounded
  pinch-zoom gesture layer

## Test Plan

- `pdm run fe-test -- --run useRoomViewportZoom useRoomTouchViewportGestures RoomTemplateBuilderSurface CreateRoomTemplateModal PlannerPhoneClassroomSeatMap PlannerPhoneFixedSeatRulePanel PlannerSeatingWorkspacePane`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run pytest tests/unit/scripts/test_playwright_script_surface.py -q`
- `pdm run ruff check scripts/_playwright_touch.py scripts/playwright_pr_0310_phone_fixed_seat_rules_map.py scripts/playwright_pr_0311_phone_room_template_modal.py`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`
- Retained browser proof:
  - extend `scripts/playwright_pr_0311_phone_room_template_modal.py` for the
    phone room-template builder pinch path
  - extend `scripts/playwright_pr_0310_phone_fixed_seat_rules_map.py` or add a
    new retained PR-0312 script for phone `Sittplatser` and `Regler` map pinch
    proof

## Rollback Plan

Revert the shared gesture composable and component integrations while leaving
the existing button-driven zoom model, phone no-hover placement behavior,
phone simplified classroom maps, fixed-seat rule authoring, and seating
short/long-press semantics intact.

## Implementation Closeout

Implemented and reviewed on 2026-05-10. `REV-PR-0312` requested changes for
the browser touch-arbitration proof path. The implementation now includes the
remediation below and is pending re-review.

- Extended `useRoomViewportZoom` with direct scale and zoom-factor APIs while
  preserving existing stepped zoom and fit-reset behavior.
- Added `useRoomTouchViewportGestures` as the shared two-finger touch gesture
  layer. It converts pinch distance changes into zoom factors and suppresses
  the browser's follow-up tap so domain actions do not fire accidentally.
- Wired the room-template builder map to the shared gesture layer. Phone pinch
  now changes the builder zoom percent, clears touch hover preview state, and
  suppresses the follow-up cell click before normal one-tap seat placement can
  continue.
- Wired the simplified phone classroom map to the same gesture layer. Phone
  `Sittplatser` and phone `Regler` / `Fast plats` now share pinch zoom while
  preserving fixed-seat selection, short-press removal, and long-press
  move/swap semantics.
- Declared `touch-action: pan-x pan-y` on the phone builder viewport and
  simplified phone classroom map so browser one-finger panning remains
  available while browser-owned pinch zoom is excluded from the app-owned map
  gesture.
- Replaced the retained pinch helper's fabricated DOM touch events with
  Chromium CDP `Input.dispatchTouchEvent` input and added computed
  `touch-action` assertions to both retained phone proof scripts.
- Kept the implementation native-event based with no third-party gesture
  dependency, no saved data-model changes, and no desktop hover-preview change.
- Extracted compact phone seat-name presentation helpers so the touched phone
  map component remains under the strict file-size/SRP boundary.

Verification:

- `pdm run fe-test -- --run useRoomViewportZoom useRoomTouchViewportGestures RoomTemplateBuilderSurface CreateRoomTemplateModal PlannerPhoneClassroomSeatMap PlannerPhoneFixedSeatRulePanel PlannerSeatingWorkspacePane`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run pytest tests/unit/scripts/test_playwright_script_surface.py -q`
- `pdm run ruff check scripts/_playwright_touch.py scripts/playwright_pr_0310_phone_fixed_seat_rules_map.py scripts/playwright_pr_0311_phone_room_template_modal.py`
- `pdm run python -m scripts.playwright_pr_0311_phone_room_template_modal --start-backend --start-vite`
- `pdm run python -m scripts.playwright_pr_0310_phone_fixed_seat_rules_map --start-backend --start-vite`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

Browser artifacts:

- `.artifacts/playwright-pr-0311-phone-room-template-modal/phone-create-modal-recovery.png`
- `.artifacts/playwright-pr-0311-phone-room-template-modal/phone-edit-modal-footer.png`
- `.artifacts/playwright-pr-0311-phone-room-template-modal/desktop-hover-ghost-preview.png`
- `.artifacts/playwright-pr-0310-phone-fixed-seat-rules-map/phone-fixed-seat-map.png`
- `.artifacts/playwright-pr-0310-phone-fixed-seat-rules-map/phone-capacity-shortfall-toast.png`
- `.artifacts/playwright-pr-0310-phone-fixed-seat-rules-map/phone-relationship-rule-selection.png`
