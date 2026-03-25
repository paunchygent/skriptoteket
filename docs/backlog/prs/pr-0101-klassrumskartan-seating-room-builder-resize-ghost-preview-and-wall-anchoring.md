---
type: pr
id: PR-0101
title: "Klassrumskartan: seating room-builder resize, ghost preview, and wall anchoring"
status: done
owners: "agents"
created: 2026-03-22
updated: 2026-03-25
stories:
  - "ST-24-04"
tags: ["frontend", "integration", "ux"]
acceptance_criteria:
  - "The classroom builder can grow or shrink by one row or one column at a time in either dimension."
  - "Before placement, a ghost preview shows the exact object footprint and orientation under the pointer."
  - "Wall-bound objects use the pointer's nearest wall as the anchoring authority instead of switching walls because of their own footprint."
  - "Wall-bound objects remain restricted to the room boundary and do not consume floor space."
  - "Live browser verification proves the resize and placement behavior in the current SPA."
---

## Problem

The current seating room builder makes placement decisions too late and too opaquely:

- room size is fixed
- placement is harder to predict than it should be
- wall objects can appear to switch direction unexpectedly

That makes the builder feel more technical than teacher-friendly.

## Goal

Make the room builder physically readable before we invest further in visual fidelity:

- resize the room incrementally
- preview placement before clicking
- anchor wall objects according to the pointer's nearest wall

## Non-goals

- Final visual polish for doors, windows, whiteboards, benches, and tables.
- Bench coalescing and true round-table rendering.
- Seating draft history UI.
- Smart seat-around-table logic.

## Implementation plan

- Add explicit row/column growth and shrink controls in the classroom builder.
- Keep the default room size as the current baseline, but let the teacher grow or shrink from it.
- Introduce a ghost preview layer that follows the pointer and shows the exact placement result.
- Base wall-object orientation on the pointer's nearest room edge.
- Keep wall objects boundary-bound and non-floor-consuming.
- Preserve floor-object placement rules for `Kateder`, `Runt bord`, `Fyrkantigt bord`, and
  `Bänk`.
- Keep the model desktop-first and verify the interaction in the live SPA rather than only in unit
  tests.

## Test plan

- Frontend unit/integration tests:
  - room can grow and shrink in each dimension
  - ghost preview updates as the pointer moves
  - nearest-wall anchoring stays stable until the pointer is closer to another wall
  - wall objects do not consume floor cells
- Live/browser:
  - resize room
  - preview and place door/window/whiteboard on different walls
  - confirm stable anchoring and boundary-only placement

## Rollback plan

- Revert the new resize and preview interactions if they destabilize room placement, while keeping
  the newer wall-vs-floor object model intact.
