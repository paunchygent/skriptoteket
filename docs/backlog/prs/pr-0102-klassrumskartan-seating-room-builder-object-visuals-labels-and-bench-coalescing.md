---
type: pr
id: PR-0102
title: "Klassrumskartan: seating room-builder object visuals, labels, and bench coalescing"
status: done
owners: "agents"
created: 2026-03-22
updated: 2026-03-23
stories:
  - "ST-24-04"
tags: ["frontend", "design", "ux"]
acceptance_criteria:
  - "Whiteboard, door, window, and teacher-desk visuals are recognizable without relying on cluttered text."
  - "Objects render as continuous shapes above the grid instead of as broken-up cell fragments."
  - "Whiteboard and teacher-desk labels remain readable and visually centered when labels are shown."
  - "Adjacent benches visually coalesce into one continuous bench while student seats remain separate objects."
  - "Round tables render as truly round in both the builder and the seating workspace."
  - "Live browser verification proves that the updated visuals remain understandable in the current SPA."
---

## Problem

The current room-builder visuals still read too much like generic colored blocks:

- some important objects are hard to recognize
- object shapes are fragmented by the grid
- labels are either missing or visually awkward
- adjacent benches do not yet read as one bench
- round tables still do not look truly round enough

That makes the room less legible than teachers need when mapping a real classroom.

## Goal

Improve the visual language of the room builder and seating canvas so the classroom reads like a
stylized planning drawing instead of a debug grid.

## Non-goals

- Room-resize controls and ghost placement behavior.
- Seating draft history and continuity work.
- Auto-generated seat slots around furniture.
- A full illustration system outside the seating builder/canvas.

## Implementation plan

- Render wall objects as coherent boundary-attached shapes instead of fragmented floor fixtures.
- Render wall objects on dedicated wall bands around the classroom floor so they never consume floor tiles.
- Render floor objects as continuous forms above the grid.
- Keep labels restrained:
  - `Whiteboard` and `Kateder` may use centered labels
  - `Dörr` and `Fönster` should read through shape instead
- Introduce visual coalescing for adjacent benches only.
- Keep student seats visually separate even when they are adjacent.
- Tighten round-table rendering so the object reads as round in both builder and seating canvas.

## Implementation summary (2026-03-23)

- Introduced `roomFixturePresentation.ts` plus `RoomFixtureArtwork.vue` so the builder and live
  seating canvas share one coherent room-object rendering layer.
- Wall objects now render on dedicated wall bands instead of consuming floor tiles.
- `Whiteboard` and `Kateder` keep restrained centered labels, while `Dörr` and `Fönster` rely on
  shape.
- Adjacent benches now coalesce visually, and round tables render as truly round on both seating
  surfaces.
- Live verification passed on `http://127.0.0.1:5173/apps/classroom.group-seating-studio`.

## Test plan

- Frontend unit/integration tests:
  - labels appear only where intended
  - adjacent benches merge visually
  - seats do not merge visually
  - round tables use the updated round rendering in both relevant surfaces
- Live/browser:
  - place whiteboard, door, window, kateder, bench, and both table types
  - verify clarity, label placement, and bench coalescing in the SPA

## Rollback plan

- Revert the new rendering layer if it reduces clarity or breaks placement feedback, while keeping
  the room-builder interaction changes from `PR-0101`.
