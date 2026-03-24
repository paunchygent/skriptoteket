---
type: pr
id: PR-0117
title: "Klassrumskartan: seating workspace viewport zoom parity"
status: done
owners: "agents"
created: 2026-03-24
updated: 2026-03-24
stories:
  - "ST-24-04"
tags: ["frontend", "ux", "design"]
acceptance_criteria:
  - "On a typical laptop viewport, the live `Sittplatser` canvas opens fit-to-view without immediate horizontal or vertical scroll pressure."
  - "The teacher can zoom out, zoom in, and return to `Anpassa` in the live seating workspace with the same interaction model already used in the room builder."
  - "Zoom changes affect only the rendered seating viewport and never mutate saved seat or fixture coordinates."
  - "Changing classroom context in `Sittplatser` resets the canvas to a fresh fit-to-view baseline for the newly selected room."
  - "The room-builder flow keeps its current zoom behavior after the shared viewport composable extraction."
  - "Live browser verification proves seating-mode zoom works in the SPA and does not break seat assignment interactions."
---

## Problem

`PR-0103` introduced a strong desktop-first zoom model for `Redigera klassrum`, but the live
`Sittplatser` workspace still renders the classroom at a fixed scale.

That leaves a mismatch inside the same teacher workflow:

- the builder can zoom and return to `Anpassa`
- the live seating canvas cannot
- large classrooms are harder to inspect or fit comfortably in `Sittplatser`
- the viewport behavior feels inconsistent between editing the room and actually placing students

The result is not a missing polish detail. It is a missing parity slice inside the seating
fundamentals story.

## Goal

Mirror the existing room-builder zoom model into the live seating workspace so `Sittplatser`
supports the same deterministic viewport controls:

- fit-to-view by default
- explicit `−`
- explicit `+`
- explicit `Anpassa`

This should make the seating canvas feel like the same classroom surface teachers already learned
in the builder, without changing draft semantics or saved geometry.

## Non-goals

- New seating draft lifecycle, autosave, history, or `Slumpa` behavior.
- Persisting zoom in Pinia, backend payloads, or browser storage.
- Reworking the room-builder UX beyond the composable extraction needed to share viewport logic.
- Replacing seat assignment drag/drop or swap behavior.
- Introducing a new generic room-scene state layer beyond viewport zoom concerns.

## Assumptions

- `ST-24-04` remains the governing story because this is still seating-fundamentals ergonomics.
- Desktop and laptop remain the canonical viewports for this workflow.
- Viewport zoom is still a session-local view concern, not a saved classroom or seating-draft
  concern.
- Teachers should see the same conceptual controls in the same vocabulary in both room editing and
  live seating.

## Decisions

- Extract a shared `useRoomViewportZoom` composable and migrate both the room builder and live
  seating to it.
- Keep the pure scale math in `roomBuilderViewport.ts` and use the new composable for stateful
  session behavior:
  - viewport size
  - fit scale
  - manual zoom override
  - current effective scale
  - zoom in/out/reset actions
- Place the seating controls in the `RoomCanvas.vue` header so the controls stay visually attached
  to the canvas they affect.
- Keep seating zoom session-local only:
  - preserve it while the current canvas stays open
  - reset it on classroom/template change
  - do not persist it in draft or template data

## Options considered

### 1. Shared vs local zoom state

Options:

- keep seating zoom local to `PlannerSeatingWorkspacePane.vue` and leave the builder wiring alone
- extract a shared `useRoomViewportZoom` composable for builder and seating
- move zoom state into `RoomCanvas.vue`

Recommendation:

- Choose the shared `useRoomViewportZoom` composable.

Reasoning:

- The room builder and live seating canvas now want the same view-only behavior.
- Sharing the state model removes duplicate viewport wiring while keeping persistence concerns out
  of the store.
- This is real reuse, not speculative genericity.

### 2. Zoom control placement

Options:

- put zoom controls in the seating action bar
- put zoom controls in the `RoomCanvas.vue` header
- hide zoom controls in the overflow menu

Recommendation:

- Put zoom controls in the `RoomCanvas.vue` header.

Reasoning:

- The controls affect the canvas, not the draft lifecycle.
- This mirrors the room-builder pattern and keeps the UI conceptually consistent.
- Overflow would make a frequently useful spatial control too hidden.

### 3. Zoom persistence model

Options:

- keep zoom session-local only
- persist zoom in Pinia draft state
- persist zoom in local storage

Recommendation:

- Keep zoom session-local only.

Reasoning:

- `PR-0103` already established zoom as a view-layer concern.
- Persisting zoom would pollute draft semantics with a viewport preference.
- Resetting on classroom change gives a predictable fit baseline for the next room.

## Implementation plan

- Add `useRoomViewportZoom.ts` as the shared stateful viewport composable for room builder and live
  seating.
- Keep `roomBuilderViewport.ts` as the pure math/helper module used by that composable.
- Migrate `useRoomTemplateEditorState.ts` to the shared viewport composable without changing current
  room-builder behavior.
- Add live seating viewport state in `PlannerSeatingWorkspacePane.vue` and pass the zoom contract
  into `RoomCanvas.vue`.
- Expand `RoomCanvas.vue` to support:
  - zoom status chip
  - `−`
  - `+`
  - `Anpassa`
  - measured viewport size
  - scaled room surface framing
- Reset seating zoom to fit when the selected classroom/template changes.
- Preserve current drag/drop, seat swap, seating history, and action-row behavior.
- Extend the existing browser smoke so seating-mode zoom parity is verified alongside the builder.

## Implementation summary (2026-03-24)

- Extracted `useRoomViewportZoom.ts` so the room builder and live seating canvas now share one
  session-local zoom model.
- Migrated `useRoomTemplateEditorState.ts` off inline builder zoom state without changing the
  existing room-builder controls or fit-to-view behavior.
- Added live seating viewport zoom wiring in `PlannerSeatingWorkspacePane.vue` and mirrored the
  builder control pattern directly in `RoomCanvas.vue` with `−`, `+`, and `Anpassa`.
- Kept seating zoom local to the current canvas session and reset it when the selected
  classroom/template changes.
- Extended `scripts/playwright_classroom_planner_smoke.py` to prove seating zoom parity plus a real
  seat assignment on the scaled canvas in the local SPA.

## Test plan

- Frontend unit/integration tests:
  - `useRoomViewportZoom.ts` computes fit scale, manual overrides, and reset behavior correctly
  - the room-builder still uses the shared composable without behavioral regressions
  - `RoomCanvas.vue` renders the zoom controls and applies scale changes without mutating room data
  - switching classroom/template resets the seating viewport to fit
- Verification commands:
  - `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/components/RoomCanvas.spec.ts src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/useRoomViewportZoom.spec.ts`
  - `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/components/PlannerSeatingWorkspacePane.vue src/views/apps/components/RoomCanvas.vue src/views/apps/useRoomViewportZoom.ts src/views/apps/useRoomTemplateEditorState.ts src/views/apps/roomBuilderViewport.ts`
  - `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`
  - `pdm run docs-validate`
- Live/browser:
  - open `/apps/classroom.group-seating-studio`
  - enter `Sittplatser`
  - verify the canvas opens fit-to-view
  - zoom in, zoom out, and return to `Anpassa`
  - assign or move at least one student to confirm interactions still work while zoomed
  - switch classroom and confirm the new room reopens at fit-to-view

## Rollback plan

- Revert the shared viewport composable and seating zoom controls while preserving the current
  room-builder zoom behavior from `PR-0103`.
