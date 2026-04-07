---
type: pr
id: PR-0235
title: "ST-24-04 follow-up: shared room viewport fit-scale contract reassessment and test realignment"
status: done
owners: "agents"
created: 2026-04-07
updated: 2026-04-07
stories:
  - "ST-24-04"
tags: ["frontend", "klassrumskartan", "viewport", "zoom", "tests", "contract-drift"]
dependencies:
  - "ST-24-04"
  - "PR-0103"
  - "PR-0117"
acceptance_criteria:
  - "Given the shared room viewport helper is used by the builder, seating canvas, and rules map, when the fit-to-view baseline is defined, then the repo explicitly chooses whether the contract subtracts one padding edge or the full framed surface and whether fit-to-view may upscale smaller rooms."
  - "Given `pdm run fe-test -- --run src/views/apps/useRoomViewportZoom.spec.ts` currently fails on hard-coded numeric expectations, when this follow-up lands, then the focused unit coverage names the intended fit-scale semantics instead of preserving stale magic numbers from an older frame model."
  - "Given the helper is shared across multiple planner surfaces, when remediation is implemented, then at least one focused component/browser proof confirms the chosen fit-to-view contract still avoids immediate scroll pressure on the canonical laptop baseline."
  - "Given the current failure may reflect broader contract drift, when remediation starts, then the work decides whether the production math or the stale expectations are wrong before changing either."
---

## Problem

`pdm run fe-test -- --run src/views/apps/useRoomViewportZoom.spec.ts` now
fails on both assertions:

- fit scale resolves to `0.465714...` instead of the old `0.5`
- zoom-in resolves to `0.565714...` instead of the old `0.6`

This is not a narrow spec typo. The shared viewport math changed after the
original zoom-parity slice:

- [roomBuilderViewport.ts](../../../frontend/apps/skriptoteket/src/views/apps/roomBuilderViewport.ts)
  now subtracts `ROOM_VIEWPORT_FRAME_PADDING * 2` instead of one padding edge
  and no longer clamps fit-to-view with `Math.min(..., 1)`.
- [RoomTemplateBuilderSurface.vue](../../../frontend/apps/skriptoteket/src/views/apps/components/RoomTemplateBuilderSurface.vue),
  [RoomCanvas.vue](../../../frontend/apps/skriptoteket/src/views/apps/components/RoomCanvas.vue),
  and
  [PlannerRulesMapCanvas.vue](../../../frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesMapCanvas.vue)
  now all render the framed surface inside a `px-6 py-6` shell and compute
  overflow anchoring from that framed width.

The failing spec is therefore exposing a broader contract drift: the shared
helper semantics moved, but the explicit fit-scale contract and its focused
tests were not re-frozen afterward.

## Goal

Decide and document the real shared fit-scale contract before any code or test
change is made, then realign the focused viewport coverage to that contract.

## Non-goals

- No opportunistic changes to unrelated planner toolbar, drag/drop, or seating
  assignment behavior.
- No silent assertion-only update that treats the current numbers as correct
  without proving the layout contract.
- No broad redesign of room-builder or seating UI beyond the fit-scale
  semantics already owned by the shared helper.

## Implementation plan

1. Reproduce the current failing numeric deltas with the focused Vitest lane.
2. Freeze the intended shared contract in docs and tests:
   - does fit-to-view subtract one padding edge or the full framed shell?
   - may fit-to-view upscale smaller rooms above `100%`, or should it remain
     capped?
3. Add or move the sharpest assertions to the pure math seam in
   [roomBuilderViewport.ts](../../../frontend/apps/skriptoteket/src/views/apps/roomBuilderViewport.ts)
   so the repo names the intended semantics directly instead of relying on
   indirect composable numbers alone.
4. Re-prove the chosen contract against the shared consumers:
   - room builder
   - seating canvas
   - rules map seating view
5. Only after that decision, either update the production helper or realign
   the stale expectations.

## Implementation summary (2026-04-07)

- Kept the current framed-surface fit model in
  [roomBuilderViewport.ts](../../../frontend/apps/skriptoteket/src/views/apps/roomBuilderViewport.ts)
  rather than reverting to the older one-edge padding math.
- Reintroduced the explicit `100%` fit cap so default fit-to-view does not
  auto-upscale smaller rooms above their authored size.
- Added
  [roomBuilderViewport.spec.ts](../../../frontend/apps/skriptoteket/src/views/apps/roomBuilderViewport.spec.ts)
  to freeze the shared contract at the pure helper seam:
  - fit uses the full framed viewport
  - fit is capped at `1`
- Realigned
  [useRoomViewportZoom.spec.ts](../../../frontend/apps/skriptoteket/src/views/apps/useRoomViewportZoom.spec.ts)
  so the composable tests the stateful zoom behavior on top of the shared
  helper instead of preserving stale legacy numbers from the pre-framed model.

## Test plan

- Current assessment proof:
  - `pdm run fe-test -- --run src/views/apps/useRoomViewportZoom.spec.ts`
- Required remediation proof:
  - `pdm run fe-test -- --run src/views/apps/useRoomViewportZoom.spec.ts src/views/apps/components/RoomTemplateBuilderSurface.spec.ts src/views/apps/components/RoomCanvas.spec.ts src/views/apps/components/PlannerRulesMapCanvas.spec.ts`
  - live local browser check on `http://127.0.0.1:5173/apps/classroom.group-seating-studio`
    covering builder, `Sittplatser`, and `Regler` seating view on a laptop-sized
    viewport
  - `pdm run fe-type-check`
  - `pdm run docs-validate`

## Verification summary (2026-04-07)

- `pdm run fe-test -- --run src/views/apps/roomBuilderViewport.spec.ts src/views/apps/useRoomViewportZoom.spec.ts src/views/apps/components/RoomTemplateBuilderSurface.spec.ts src/views/apps/components/RoomCanvas.spec.ts src/views/apps/components/PlannerRulesMapCanvas.spec.ts`
  (pass)
- `pdm run fe-type-check` (pass)
- Live local browser proof on
  `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio` (pass):
  - builder modal rendered with `data-test="builder-zoom-percent"` showing
    `100%` for a fresh small-room state
  - builder scroll frame reported `data-overflow-anchor="center"`
  - local Playwright Chrome session was explicitly closed after the check
- `pdm run docs-validate` (pass)

## Rollback plan

- If the reassessment shows the newer framed-surface math is wrong, revert the
  fit-scale helper semantics while keeping the clarified docs/tests that
  freeze the contract.
- If the reassessment proves the newer math is correct, keep production code
  and remove only the stale expectations that still encode the older baseline.
