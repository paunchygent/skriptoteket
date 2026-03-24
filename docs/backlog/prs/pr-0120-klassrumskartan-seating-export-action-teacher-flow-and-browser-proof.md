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

## Locked design decisions

- The seating workspace should introduce a compact `Export` subsection rather
  than a row of format-specific buttons.
- The primary CTA is `Exportera`, not `Exportera PDF` or another
  file-extension-led label.
- The happy-path default export is the existing poster artifact
  `Affisch (A3)`, which maps to `pretty_brutalist_poster` plus
  `a3_landscape`.
- The uncommon alternate is one click away through an adjacent export menu and
  is limited to `Affisch (A4)` in this slice.
- The UI must not introduce a modal, drawer, layout picker, or a flat line of
  equal-weight export choices.
- Export remains explicit and separate from autosave; the flow must flush
  pending draft saves before creating an export job.
- The export orchestration should live in a dedicated frontend composable and
  API helper, not inside the presentational seating pane and not inside the
  mutable draft store.

## Non-goals

- Layout picker UI.
- Grouping export UI.
- Import or XLSX flows.

## Implementation plan

- Add a compact `Export` action group inside the existing seating action row
  rather than creating a separate panel or drawer.
- Render a primary `Exportera` button that immediately runs the default
  `Affisch (A3)` path.
- Add a small adjacent export-options trigger that exposes `Affisch (A3)` and
  `Affisch (A4)` without teaching a generic layout-picker mental model.
- Keep export options artifact-first and hierarchy-driven so future `Excel` and
  `Word` exports can join the same family without turning the toolbar into
  `Exportera PDF` / `Exportera XLSX` / `Exportera DOCX`.
- Introduce a dedicated frontend export flow seam that:
  - flushes pending autosave before export
  - creates the async seating export job
  - polls status
  - auto-downloads the finished PDF on success
  - exposes compact success/error/download-again state to the seating UI
- Keep the seating pane presentational and route-shell driven, following the
  current Klassrumskartan composition boundaries.
- Add a dedicated browser proof for the live teacher export flow.

## Proposed UI shape

- Section label: `Export`
- Primary button: `Exportera`
- Adjacent alternate-options trigger: compact chevron/menu button
- Alternate options in this slice:
  - `Affisch (A3)`
  - `Affisch (A4)`
- Success affordance:
  - auto-download on success
  - compact success state plus `Ladda ned igen`
- Failure affordance:
  - one teacher-safe inline error near the export action group

## Proposed module placement

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerExportActionGroup.vue`
  for the compact presentational export cluster
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerExportApi.ts`
  for typed create/status/download requests
- `frontend/apps/skriptoteket/src/views/apps/useSeatingExportFlow.ts`
  for export orchestration, polling, and auto-download
- `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerRouteShell.ts`
  for wiring the flow into the planner shell without bloating
  `useClassroomState.ts`

## Test plan

- Focused frontend tests for the compact export action group and seating export
  flow state.
- Focused tests proving default click exports `Affisch (A3)` and the alternate
  menu path exports `Affisch (A4)`.
- Focused tests proving pending autosave is flushed before export starts and
  duplicate export clicks stay disabled while a job is active.
- Dedicated browser proof for the seating export flow.

## Rollback plan

- Remove the explicit export action while preserving the renderer and contract work if needed.
