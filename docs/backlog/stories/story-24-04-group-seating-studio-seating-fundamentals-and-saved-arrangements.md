---
type: story
id: ST-24-04
title: "Klassrumskartan — Seating fundamentals, room-builder ergonomics, and draft history"
status: done
owners: "agents"
created: 2026-03-21
updated: 2026-03-25
epic: "EPIC-24"
acceptance_criteria:
  - "Given the teacher is in a class workspace, when they open or create a seating draft, then the seating workflow is clearly tied to that class and the selected classroom."
  - "Given the teacher enters `Sittplatser`, when the workspace opens, then the active seating draft remains primary and the classroom remains secondary support rather than a competing launcher surface."
  - "Given the teacher is editing a classroom for seating, when they need a different room size, then they can grow or shrink the room one row or one column at a time in either dimension."
  - "Given the teacher is about to place a room object, when they move the pointer over the room builder, then a ghost preview shows the exact resting position and footprint before placement."
  - "Given a wall-bound object is being placed, when the pointer moves near the room boundary, then the nearest wall determines the object's orientation and anchoring rather than the object's own footprint causing surprising wall-switches."
  - "Given the teacher places `Whiteboard`, `Fönster`, or `Dörr`, when the object is rendered, then it reads as a wall object and does not consume classroom floor space."
  - "Given the teacher places `Kateder`, `Runt bord`, `Fyrkantigt bord`, or `Bänk`, when the object is rendered, then it behaves as a floor object and remains visually distinct from separate student seats."
  - "Given multiple benches are placed flush in a row, when they share an edge, then they visually coalesce into one continuous bench while student seats still remain separate objects."
  - "Given the teacher works in the seating editor, when objects render in either the builder or the seating canvas, then `Whiteboard` and `Kateder` remain recognizable and clearly labeled while `Dörr` and `Fönster` rely primarily on shape rather than intrusive text."
  - "Given the teacher places a round table, when the object renders in the builder and in seating, then it reads as truly round rather than as a square tile with a circular mark."
  - "Given the teacher opens the room builder on a typical laptop viewport, when the modal loads, then the default classroom fits without immediate scroll pressure and the builder can zoom in, zoom out, or return to a fit-to-view baseline."
  - "Given the teacher wants to restart the room layout, when they click `Rensa`, then seats and room objects are removed while the classroom name and grid size remain unchanged."
  - "Given seats render in the room builder and in seating, when the teacher looks at the layout, then seats read as circular places rather than square room tiles."
  - "Given the class already has an active seating draft, when the teacher returns later, then that seating draft can be resumed as the active seating work for that class."
  - "Given the teacher starts a new seating draft for the same class, when the new draft is created, then the previous active seating draft is demoted to class history automatically."
  - "Given the teacher changes the current seating draft, when they use undo or redo, then the recent seating history can be stepped backward or forward inside the seating workspace without exposing those steps as separate saved items."
  - "Given the seating draft changes repeatedly, when draft history is retained for undo and redo, then the history depth stays bounded and configurable rather than growing without limit."
  - "Given the teacher leaves seating and returns later, when the draft has been autosaved, then the latest seating state is resumed without requiring a separate teacher-facing save action."
---

## Context

This story defines `Sittplatser` as a class-scoped teacher workflow with its own draft lifecycle,
its own desktop-first editor ergonomics, and a classroom builder that behaves like a clear
planning tool rather than like a generic grid toy.

The room builder is part of the teacher workflow, not a separate technical subtool. Its
interaction model therefore needs to be understandable at a glance:

- resize the room incrementally
- preview objects before placing them
- keep wall objects on walls
- keep floor objects on the floor
- make the rendered objects read like an actual classroom

## Problem

The current seating/editor surface is directionally useful but still too ambiguous in the places
where teachers need immediate spatial confidence:

- room size is fixed
- placement previews are not strong enough
- wall-object anchoring can switch in surprising ways
- object visuals are not yet descriptive enough
- some visible UI copy still speaks more to the implementation than to the teacher

If we keep adding seating behavior without tightening that foundation, the workflow will feel more
technical and less trustworthy.

## Assumptions

- Desktop and laptop viewports are the canonical design source for this app.
- Tablet and phone layouts are ports of the desktop workflow, not the other way around.
- `Sittplatser` remains a separate task from `Grupper`, even if both live in the same class
  workspace shell.
- The classroom builder is a practical editing surface, not a CAD tool and not a solver UI.
- Student seats remain explicit separate placements; tables and benches provide room context but do
  not contain or auto-generate seats.
- Wall-bound objects are boundary features, not floor fixtures.
- Autosave plus bounded in-draft undo/redo remain draft mechanics rather than teacher-facing
  “saved files.”

## Decisions

- Keep `Sittplatser` as the mode name in the toggle and use `Sittschema` for the active seating
  work inside the workspace.
- Keep `Klassrum` as the visible room term and remove `Rumsmall` from teacher-facing copy.
- Treat `Whiteboard`, `Fönster`, and `Dörr` as wall-bound objects that do not consume floor space.
- Treat `Kateder`, `Runt bord`, `Fyrkantigt bord`, and `Bänk` as floor objects.
- Keep seats separate from tables and benches; no smart seat-container logic is introduced here.
- Let benches coalesce visually when adjacent, but never coalesce student seats.
- Split the implementation into two PR-sized slices:
  - editor behavior and placement model
  - rendering fidelity and object visuals

## Follow-up PR Slices

- [PR-0311: ST-24-04 phone room-template modal stabilization](../prs/pr-0311-st-24-04-phone-room-template-modal-stabilization.md)
  (`done` 2026-05-09): stabilizes the phone room-template editor modal with
  compact sticky footer actions, required-name focus/recovery, aligned name
  panel spacing, and touch/coarse-pointer ghost-preview suppression while
  preserving desktop hover previews.
- [PR-0312: Shared phone classroom-map touch viewport gestures](../prs/pr-0312-shared-phone-classroom-map-touch-viewport-gestures.md)
  (`done` 2026-05-10): adds reusable pinch/touch zoom on the
  room-template builder map and other phone classroom-map surfaces.

## Options considered

### 1. Canonical viewport model

Options:

- desktop-first editor as the canonical model
- mobile-first editor with desktop as an enhancement

Recommendation:

- Choose desktop-first.

Reasoning:

- Teachers use this tool primarily on work laptops.
- The seating workflow depends on spatial overview, secondary controls, and visible context.
- A mobile-first model would distort the main workflow and lead to worse desktop UX.

### 2. Room-resize interaction

Options:

- freeform drag-resize from edges
- stepwise add/remove one row or column at a time
- modal-based width/height inputs

Recommendation:

- Choose stepwise add/remove one row or column at a time.

Reasoning:

- It is simple, reversible, and easy to verify visually.
- It avoids hidden geometry jumps.
- It keeps the builder aligned with the grid mental model already in use.

### 3. Placement preview model

Options:

- no preview until click
- highlight only the anchor cell
- full ghost preview of the object footprint and orientation

Recommendation:

- Choose full ghost preview.

Reasoning:

- Teachers need to know exactly where the object will end up before committing.
- This is especially important for multi-cell objects and wall-bound objects.

### 4. Wall-object orientation model

Options:

- let the object's own footprint decide the nearest viable wall
- use the pointer's nearest wall as the authority
- require explicit rotate controls during placement

Recommendation:

- Use the pointer's nearest wall as the authority.

Reasoning:

- It matches what the teacher is actually aiming at.
- It removes confusing wall-switches caused by the object's size.
- It keeps placement direct without adding extra rotate ceremony.

### 5. Object labeling model

Options:

- label everything
- label only the objects that need help to remain understandable
- remove labels entirely and rely only on visuals

Recommendation:

- Label only the objects that need help, primarily `Whiteboard` and `Kateder`.

Reasoning:

- `Dörr` and `Fönster` should read through shape.
- Too many labels make the grid noisy and less classroom-like.
- Some objects still benefit from a restrained centered label.

### 6. Table-and-seat relationship model

Options:

- tables own seats implicitly
- tables reserve automatic seat slots around themselves
- tables remain furniture and seats remain separate

Recommendation:

- Keep tables as furniture and seats as separate placements.

Reasoning:

- Teachers care who sits beside whom and on which side of a table.
- Seat ownership inside the table would hide that control.
- Separate seats also matches the existing seating mental model.

## Recommended decomposition

### PR-0101

Focus:

- room resize controls
- ghost placement preview
- stable nearest-wall anchoring
- room-builder interaction behavior

### PR-0102

Focus:

- object visuals
- label strategy
- contiguous rendering above the grid
- bench coalescing
- true round tables

### PR-0103

Focus:

- larger desktop-first room-builder modal footprint
- explicit zoom in/out plus `Anpassa`
- `Rensa` that clears room content without resetting classroom identity or size
- circular seats across builder, preview, and seating canvas

### PR-0105

Focus:

- seating continuity drawer inside `Sittplatser`
- `Nytt sitschema` lifecycle for the same class and selected classroom
- reopen/delete historic seating drafts from the drawer

### PR-0106

Focus:

- seating-specific undo/redo
- bounded seating in-draft history
- backend history generalization from grouping-only to draft-kind-aware behavior where needed

## Critical questions

No critical open product questions remain from the current explanation.

The latest clarified direction is specific enough to implement safely:

- wall objects snap to the outer boundary
- door/window rely on shape over labels
- whiteboard may keep a restrained label
- tables do not contain seats
- benches may coalesce visually
- seats must remain separate

## Close-out review (2026-03-23)

Shipped in this story so far:

- `PR-0101`: room resize, ghost placement preview, and corrected wall anchoring
- `PR-0102`: wall-vs-floor rendering, object artwork, labels, bench coalescing, and true round
  tables
- `PR-0103`: larger desktop-first builder modal, zoom, `Anpassa`, `Rensa`, and circular seats
- `PR-0105`: seating continuity drawer in `Sittplatser`, classroom-required `Nytt sittschema`,
  reopen/delete of historic seating drafts, and dedicated live browser proof of the new lifecycle
- `PR-0106`: seating-specific `Ångra` / `Gör om`, bounded in-draft history shared with grouping,
  backend-owned undo/redo status, and a targeted browser proof that the continuity drawer remains
  draft-level while classroom switching stays outside seating undo/redo

`ST-24-04` is now closed. The shipped work covers the remaining acceptance criteria for
seating-specific undo/redo, bounded in-draft history, and resumed autosaved seating state.

`PR-0113` later completed the remaining in-place reset affordance by adding `Börja om` for the
active seating draft without creating a new draft or changing classroom context.

## Notes

- This story starts only after `ST-24-05` and `ST-24-02` have removed superseded planner
  contracts and established the class-first workspace.
- Draft autosave keeps live seating work alive, while a bounded recent history supports undo and
  redo inside the seating workspace.
- The recent-history depth should be configurable and simple to tune; the current planning target
  is 10 steps.
- Durable export/file-vault artifacts belong to a later flow and must not be conflated with draft
  autosave or undo/redo history.
- Static room presentation should follow the design system rather than hard-coded one-off visuals,
  while dynamic geometry remains data-driven.
- Seating history and active-draft continuity should mirror the grouping model where that improves
  teacher clarity, but without importing grouping-specific controls into the seating workspace.
