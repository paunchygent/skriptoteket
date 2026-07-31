---
type: task
id: TASK-SKRIPT-27-09-03
title: Shared phone classroom-map real-device pinch remediation
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: in_progress
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-27-09
task_kind: story
acceptance_criteria:
- Given the phone `Sittplatser` simplified classroom map renders on an iPhone-sized
  viewport, when the teacher performs a real two-finger pinch on the map, then the
  map visibly zooms without removing, moving, or swapping a seated student.
- Given the phone `Regler` `Fast plats` simplified classroom map renders on an iPhone-sized
  viewport, when the teacher performs a real two-finger pinch on the map, then the
  map visibly zooms without selecting, clearing, or saving a fixed-seat binding.
- Given the teacher pinches around a visible map location, when zoom changes, then
  that gesture target remains centered under the same screen point instead of drifting
  toward the canvas origin.
- Given the simplified phone map receives a continuous pinch gesture, when gesture
  events arrive quickly, then zoom and scroll compensation are coalesced through one
  gesture-camera update loop rather than chained through stale scroll/scale state.
- Given the simplified phone map renders at its default zoom, when seats have assigned
  students and rule markers, then names, initials, and marker symbols remain readable
  without requiring a preliminary zoom.
- Given the simplified phone map zooms, when seat containers grow or shrink, then
  seat ordinals, student names, initials, and marker symbols scale from bounded CSS
  variables derived from `--planner-phone-seat-cell-size` instead of staying fixed-size.
- Given a recognized pinch gesture ends on either simplified map, when the browser
  dispatches a follow-up tap/click, then the map suppresses that follow-up domain
  action exactly once.
- Given one-finger interaction is used on either simplified map, when the teacher
  taps or short/long-presses a seat, then the existing `PR-0310` seat selection, removal,
  move, and swap semantics remain unchanged.
- Given browser proof runs for the phone simplified map, when the proof asserts zoom,
  then it proves native/browser-level input ownership rather than only fabricated
  DOM `TouchEvent` handler invocation.
---

## Context


`PR-0312` added a shared touch-gesture composable and proved handler behavior
with Chromium-level retained proof. Real iPhone testing now shows that the
room-template builder modal can be pinched, but the simplified phone classroom
maps in `Sittplatser` and `Regler` / `Fast plats` do not visibly respond to the
same touch gesture.

This is a phone usability blocker because those simplified maps are now the
primary small-screen representation for seating and fixed-seat authoring.
Teachers cannot rely on tiny controls or desktop-scale map affordances to
inspect the classroom on a phone.

## Decision And Assumption Ledger

| source | semantic | carried_forward | Source material is retained in the sections above. | source |

## Story Contract Slice


Make the simplified phone classroom map use the same real-device pinch behavior
that works in the room-template builder modal.

The fix must cover both consumers of `PlannerPhoneClassroomSeatMap.vue`:

- phone `Sittplatser`
- phone `Regler` / `Fast plats`

## Contract Inputs

No separate contract inputs is stated in the source.

## Plan


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

## Implementation Steps

No separate implementation steps is stated in the source.

## Proof


- `pdm run fe-test -- --run useRoomTouchViewportGestures PlannerPhoneClassroomSeatMap PlannerPhoneFixedSeatRulePanel PlannerSeatingWorkspacePane`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run pytest tests/unit/scripts/test_playwright_script_surface.py -q`
- `pdm run ruff check scripts/_playwright_touch.py scripts/playwright_pr_0310_phone_fixed_seat_rules_map.py`
- `pdm run python -m scripts.playwright_pr_0310_phone_fixed_seat_rules_map --start-backend --start-vite`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Validation

No separate validation is stated in the source.

## Stop Conditions


Revert the simplified-map gesture binding changes while leaving `PR-0310`
phone maps, short/long-press seating semantics, fixed-seat authoring, and the
room-template builder modal untouched.

## Lessons Learned

No separate lessons learned is stated in the source.

## Notes

No separate notes is stated in the source.

### Source: Non-goals


- No solver, Smart seating, rule persistence, or marker semantics change.
- No room-template builder redesign; it is the working reference path.
- No desktop/tablet `RoomCanvas` replacement.
- No new third-party gesture dependency unless native touch and platform
  gesture events cannot satisfy the iPhone path.
- No removal of existing single-tap, short-press, or long-press semantics.

### Source: Design Direction


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

### Source: Frontend Entry Points


- `frontend/apps/skriptoteket/src/views/apps/components/PlannerPhoneClassroomSeatMap.vue`
- `frontend/apps/skriptoteket/src/views/apps/useRoomTouchViewportGestures.ts`
- `frontend/apps/skriptoteket/src/views/apps/useRoomViewportZoom.ts`
- `frontend/apps/skriptoteket/src/assets/klassrumskartan-phone-workspace.css`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerPhoneClassroomSeatMap.spec.ts`
- `scripts/_playwright_touch.py`
- `scripts/playwright_pr_0310_phone_fixed_seat_rules_map.py`

### Source: Implementation Closeout


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

### Source: Post-Review Field Finding


Real-device testing reported on 2026-05-10 that touch gesture zoom in/out still
does not work on the simplified phone classroom maps. The retained Chromium and
unit proof was therefore not sufficient to close the real-device acceptance
criterion. The remediation below reopens the lane for re-review and still needs
actual phone confirmation before final `done` closeout.

### Source: Review Remediation


Applied on 2026-05-10; second-pass code proof accepted the visible zoom binding,
but final closeout still requires real-device iPhone confirmation.

- Fixed the simplified map's visual zoom binding so pinch-derived scale updates
  set the viewport-level `--planner-phone-seat-cell-size` used by the rendered
  seat grid, not only the hidden zoom percent.
- Kept the shared `useRoomTouchViewportGestures` path unchanged; this
  remediation targets the broken simplified-map consumer where zoom state was
  not visibly affecting the map cells.
- Added focused component proof that a 125% pinch changes both the displayed
  zoom percent and the rendered phone-seat cell-size style while suppressing
  the follow-up seat-removal click.

Second-pass review verified the component proof, but this PR remains
`in_progress` until the same behavior is confirmed on the actual phone path for
both `Sittplatser` and `Regler` / `Fast plats`.

Verification:

- `pdm run fe-test -- --run classroomPlannerSeatRuleMarkers PlannerPhoneClassroomSeatMap useRoomTouchViewportGestures`

### Source: Field Follow-up: Anchored Zoom And Readability


Real-device testing after the visible zoom fix confirmed pinch zoom now works,
but the simplified map grows from the canvas origin. That makes the map drift
toward the upper-left corner and disorients the teacher because the visible
gesture target is not preserved across the scale change. The same field pass
also showed that default-size student names, initials, and rule symbols are too
small before zoom.

Follow-up remediation:

- Extend the shared gesture payload with a viewport-relative gesture centroid.
- Add a small anchored zoom helper for scrollable map viewports so the content
  coordinate under the gesture midpoint remains under that midpoint after the
  new scale is applied.
- Replace incremental scroll compensation with a reusable gesture-camera model:
  on gesture start, capture the content coordinate under the pinch centroid;
  during gesture movement, derive scroll from that captured content coordinate,
  the latest centroid, and the target scale.
- Coalesce camera updates with `requestAnimationFrame` so fast iPhone gesture
  streams do not compound against stale `scrollLeft` / `scrollTop` values.
- Feed platform `gesturestart` / `gesturechange` `clientX` and `clientY` into
  the same camera path when available; never fall back to viewport center when
  the browser supplies a real gesture location.
- Make the phone map a contained two-axis pan/zoom viewport so zoom growth is
  compensated through `scrollLeft` / `scrollTop` rather than page drift.
- Treat simplified-map typography and symbol scaling as acceptance, not polish:
  derive seat ordinal, first-name, initials, marker-box, and marker-icon sizes
  from bounded CSS variables based on `--planner-phone-seat-cell-size`.

Additional verification:

- Focused composable proof that anchored zoom adjusts scroll position from the
  pre-zoom content coordinate.
- Component proof that a pinch around a known phone-map point changes zoom
  without pushing that point toward the origin and still suppresses the
  follow-up click.
- Component or browser proof that scaled seat cells also scale readable text
  and marker symbols within bounded min/max values.

### Source: Anchored Zoom Remediation Closeout


Implemented on 2026-05-10; ready for retained review plus real-device
confirmation.

- Extended the shared gesture payload so both two-touch and platform
  `gesturestart` / `gesturechange` paths carry a viewport-relative centroid
  when the browser exposes `clientX` and `clientY`.
- Replaced active-pinch `nextTick` scroll correction with a reusable
  gesture-camera model in `useAnchoredRoomViewportZoom`: gesture start captures
  the content coordinate under the centroid, gesture updates derive scroll from
  that original content coordinate plus the latest centroid and target scale,
  and fast updates coalesce through one `requestAnimationFrame`.
- Kept discrete button zoom on the anchored viewport helper while reserving the
  gesture camera for continuous pinch streams.
- Wired `PlannerPhoneClassroomSeatMap.vue` to begin and end the gesture camera
  around recognized pinch gestures while preserving one-finger short-press and
  long-press semantics from `PR-0310`.
- Review remediation flushed the final queued gesture-camera scroll before
  clearing pinch state, so a normal `touchmove` then `touchend` sequence cannot
  leave the last scale frame unanchored.
- Scaled phone-map ordinals, first names, initials, marker boxes, and marker
  icons from bounded CSS variables derived from
  `--planner-phone-seat-cell-size`, and restored high-contrast token color for
  smaller text.

Additional verification:

- `pdm run fe-test -- --run classroomPlannerSeatRuleMarkers classroomPlannerStateSupport useAnchoredRoomViewportZoom useRoomTouchViewportGestures PlannerPhoneClassroomSeatMap`
- `pdm run pytest tests/unit/scripts/test_klassrumskartan_surface_tokens.py -q`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

Real-device note:

- This closes the code-level drift and readability remediation, but final
  `done` closeout still requires iPhone confirmation that pinch centering feels
  smooth in both phone `Sittplatser` and phone `Regler` / `Fast plats`.

## Plan Document Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.

## Implementation Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.
