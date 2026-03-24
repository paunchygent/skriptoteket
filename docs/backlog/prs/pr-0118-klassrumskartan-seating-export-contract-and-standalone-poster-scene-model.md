---
type: pr
id: PR-0118
title: "Klassrumskartan: seating export contract and standalone poster scene model"
status: done
owners: "agents"
created: 2026-03-24
updated: 2026-03-24
stories:
  - "ST-26-01"
tags: ["backend", "frontend", "contract", "klassrumskartan", "export"]
acceptance_criteria:
  - "A typed seating export contract exists for explicit artifact generation and is distinct from draft autosave or undo/redo mechanics, with the request identifying the export target explicitly by `seatingDraftId`."
  - "The export contract is layout-ready from day one, including a stable `layout_id`, but only one approved layout is exposed initially."
  - "A standalone poster-scene model exists that translates seating draft data plus room geometry into export-ready composition inputs without relying on live planner DOM structure."
  - "The standalone poster-scene model preserves the export-critical room markers where present: whiteboard, teacher desk, door, windows, benches, and tables."
  - "The contract and poster-scene model encode a deterministic student-label formatter for poster output using `first name + last initial` only."
  - "The standalone poster-scene model is suitable for later export-specific HTML/CSS rendering and does not assume direct PDF drawing primitives as the canonical intermediate source."
---

## Problem

Klassrumskartan does not yet have an explicit export artifact contract for seating, and the export lane must not inherit SPA layout constraints.

## Goal

Establish the explicit seating export contract and standalone poster-scene model needed for later HTML/CSS generation and PDF rendering.

## Non-goals

- Rendering the final branded PDF artifact.
- Adding multiple teacher-selectable layouts.
- Shipping XLSX export.

## Implementation plan

- Define explicit seating export request/response models.
- Use explicit `seatingDraftId` targeting rather than implicit current-draft resolution.
- Define the first layout identifier: `pretty_brutalist_poster`.
- Introduce a standalone poster-scene translation layer from seating draft + room geometry to export composition inputs.
- Keep the poster scene aligned to a later export-specific HTML/CSS rendering path that Sir Convert-a-Lot can consume.
- Treat room markers as first-class export inputs:
  - whiteboard
  - teacher desk if present
  - door if present
  - windows if present
  - benches/tables if present
- Define one deterministic poster-name formatter: `first name + last initial`.
- Keep the scene model independent from planner DOM/CSS assumptions.

## Implemented contract

- Route: `POST /api/v1/apps/classroom.group-seating-studio/drafts/seating/{draft_id}/exports`
- Request body:
  - `export_kind`: `pdf`
  - `layout_id`: `pretty_brutalist_poster`
- Response body:
  - `seating_draft_id`
  - `roster_id`
  - `roster_name`
  - `template_id`
  - `template_name`
  - `export_kind`
  - `layout_id`
  - `poster_scene`
- `poster_scene` currently exposes:
  - logical room grid dimensions (`grid_cols`, `grid_rows`)
  - logical seat placements with canonical poster labels
  - logical room markers with normalized fixture kinds and wall-side metadata where relevant

## Implementation notes

- The poster-scene model lives in `src/skriptoteket/application/curated_apps/classroom_planner/exports/` rather than the classroom-planner domain core.
- The translator normalizes stored room geometry into logical grid units so the contract stays renderer-independent and ready for export-specific HTML/CSS generation in `PR-0119`.
- Table fixtures are normalized to the export kind `table` while preserving shape as `round` or `square`.
- The export handler currently accepts active seating drafts only and fails loudly when seating assignments or wall-bound fixtures leave the exportable room scene.

## Test plan

- Contract tests for the seating export request/response shape.
- Translation tests proving room geometry, required fixtures, seats, and canonical student labels map into the poster scene model deterministically.

## Rollback plan

- Remove the explicit export contract and poster-scene model without touching existing seating draft mechanics.
