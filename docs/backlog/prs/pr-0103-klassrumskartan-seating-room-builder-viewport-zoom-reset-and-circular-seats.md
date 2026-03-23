---
type: pr
id: PR-0103
title: "Klassrumskartan: seating room-builder viewport fit, zoom, reset, and circular seats"
status: done
owners: "agents"
created: 2026-03-23
updated: 2026-03-23
stories:
  - "ST-24-04"
tags: ["frontend", "ux", "design"]
acceptance_criteria:
  - "On a typical laptop viewport, the default classroom fits in the builder without forcing immediate horizontal or vertical scrolling."
  - "The room-builder modal uses more of the available screen estate while the left-hand tools column stays as narrow as the workflow safely allows."
  - "The teacher can zoom in and out in the room builder and return to a fit-to-view baseline without losing placement fidelity."
  - "A `Rensa` action clears seats and room objects from the current classroom draft without changing the classroom name or grid size."
  - "Seats render as circles rather than square tiles in the builder, preview, and live seating workspace."
  - "Live browser verification proves the builder remains readable and workable at the default zoom and after zoom changes in the SPA."
---

## Problem

The current room-builder canvas is functionally richer after `PR-0101` and `PR-0102`, but the
editing surface still wastes too much of the available laptop viewport:

- the classroom starts visually too zoomed in
- the modal gives too much width to the left tools column and too little to the actual room
- teachers cannot zoom out to inspect the full room comfortably when needed
- there is no fast way to clear the current room content and start over
- seats still read too much like square tiles instead of chairs/places

That makes the editor feel tighter and more technical than it needs to be.

## Goal

Make the room-builder modal feel like a spacious desktop-first planning surface:

- more canvas, less chrome
- explicit zoom controls
- one-step clear/reset of room contents
- circular seats that read as seats rather than blocks

## Non-goals

- New room-object types or new object-rendering fidelity beyond what `PR-0102` already covers.
- Rotatable perspective walls or a full isometric perspective switch.
- Smart placement logic around tables or benches.
- Changes to the saved room-template contract beyond what is needed to preserve existing geometry.
- Seating draft lifecycle/history work.

## Assumptions

- Desktop/laptop remains the canonical viewport for the room builder.
- The default builder view should prioritize seeing the whole room over maximizing individual cell size.
- Zoom is a view-layer concern, not a persistence concern.
- `Rensa` means clearing room contents, not deleting the classroom asset and not resetting room size.
- Seats should be visually circular in all seating surfaces, while their saved coordinates remain unchanged.

## Decisions

- Introduce explicit zoom controls in the room-builder modal:
  - `-`
  - `+`
  - `Anpassa`
- Keep zoom local to the current modal session; do not persist it in backend room-template data.
- Expand the modal footprint on desktop and shrink the left-hand tools column so the room surface gets the majority of the width.
- Add `Rensa` as a non-destructive room-content reset action:
  - clears seats
  - clears room fixtures
  - preserves classroom name
  - preserves grid dimensions
- Make seats circular in:
  - builder
  - preview
  - live seating canvas

## Options considered

### 1. Zoom model

Options:

- browser-native pinch/scroll only
- explicit zoom controls with a fit baseline
- freeform slider plus controls

Recommendation:

- Choose explicit zoom controls with a fit baseline.

Reasoning:

- The teacher needs deterministic, low-friction controls.
- A simple `Anpassa` action is clearer than a raw scale percentage alone.
- Sliders add UI weight without much extra value for this editor.

### 2. Reset behavior

Options:

- no reset action; teachers manually erase items
- destructive full classroom delete
- `Rensa` that clears room content only

Recommendation:

- Choose `Rensa` that clears room content only.

Reasoning:

- This matches the real teacher intention: start over in the same classroom.
- It avoids conflating content reset with classroom deletion.
- It is lower-friction than manual erase for medium/large rooms.

### 3. Seat shape

Options:

- keep square seats for consistency with the grid
- rounded squares
- fully circular seats

Recommendation:

- Choose fully circular seats.

Reasoning:

- Seats represent places/chairs, not room tiles.
- Circular seats distinguish seating from fixtures more clearly.
- The room already uses the grid as a placement aid; seats do not need to reinforce square geometry.

### 4. Modal layout

Options:

- preserve the current two-column balance
- make the whole modal larger and narrow the left tools column
- split tools into collapsible subsections to preserve current width

Recommendation:

- Make the whole modal larger and narrow the left tools column.

Reasoning:

- The canvas is the primary work surface and should win width by default.
- Collapsible subpanels would add interaction overhead to compensate for a layout problem.
- This keeps the desktop workflow clear and direct.

## Implementation plan

- Increase the effective desktop modal footprint so the room surface can use more of the viewport.
- Reduce the fixed width of the left-hand builder controls column to the minimum comfortable width.
- Add room-builder zoom state and controls in the modal:
  - zoom in
  - zoom out
  - fit to available space
- Apply zoom only to the room-builder viewport layer, not to saved room coordinates.
- Add a `Rensa` action that clears seats and fixtures in the current draft-in-modal state.
- Update seat rendering so seats are circular in:
  - room-builder placement view
  - preview pane
  - live seating canvas
- Keep wall-object and floor-object layering from `PR-0102` intact while applying zoom.

## Implementation summary (2026-03-23)

- Expanded the desktop modal footprint and narrowed the left-hand tools column so the builder
  viewport gets the dominant share of the screen.
- Added local zoom controls (`-`, `+`, `Anpassa`) with a fit-to-view baseline that does not touch
  saved room geometry.
- Added `Rensa`, which clears seats and fixtures while preserving classroom name and grid size.
- Introduced circular seat rendering across the builder, preview, and live seating canvas through
  shared seat-presentation helpers.
- Extended `scripts/playwright_classroom_planner_smoke.py` to verify the builder viewport fit,
  zoom reset, `Rensa`, and seat rendering on `http://127.0.0.1:5173`.

## Test plan

- Frontend unit/integration tests:
  - fit/default zoom shows the full room surface metrics in the modal viewport contract
  - zoom controls change the rendered scale without mutating saved seat/fixture coordinates
  - `Rensa` removes seats and fixtures while preserving name and grid size
  - seat nodes render as circular rather than square in all relevant surfaces
- Live/browser:
  - open `Nytt klassrum`
  - verify the default room fits without immediate scroll pressure on a laptop viewport
  - zoom in and out, then return to `Anpassa`
  - place a few seats/fixtures, click `Rensa`, verify the room content is cleared
  - confirm seats read as circles in builder and seating

## Rollback plan

- Revert zoom/reset/layout changes while keeping the object-rendering improvements from `PR-0102`.
