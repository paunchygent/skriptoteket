---
type: pr
id: PR-0120
title: "Klassrumskartan: seating export action, teacher flow, and browser proof"
status: ready
owners: "agents"
created: 2026-03-24
updated: 2026-03-24
stories:
  - "ST-26-01"
tags: ["frontend", "ux", "klassrumskartan", "export", "playwright"]
acceptance_criteria:
  - "Teachers can trigger seating poster export from the approved seating workflow without introducing a cluttered export surface."
  - "The UI exposes only the first approved poster layout in this story and does not imply that draft autosave is equivalent to export."
  - "A focused browser proof verifies the explicit export teacher flow end to end on the live local SPA."
---

## Problem

Teachers need a clear export action in the seating workflow, but the first slice must stay minimal and avoid clutter.

## Goal

Add the narrow teacher-facing export action and browser proof for seating PDF poster export.

## Non-goals

- Layout picker UI.
- Grouping export UI.
- Import or XLSX flows.

## Implementation plan

- Add a narrow seating export action in the approved seating workspace.
- Keep copy and UI aligned with explicit export semantics.
- Add a dedicated browser proof for the export flow.

## Test plan

- Focused frontend tests for export action state.
- Dedicated browser proof for the seating export flow.

## Rollback plan

- Remove the explicit export action while preserving the renderer and contract work if needed.
