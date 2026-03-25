---
type: pr
id: PR-0141
title: "Klassrumskartan: grouping PDF A4 portrait presentation renderer and delivery"
status: ready
owners: "agents"
created: 2026-03-25
updated: 2026-03-25
stories:
  - "ST-26-04"
tags: ["backend", "frontend", "pdf", "klassrumskartan", "export", "grouping"]
acceptance_criteria:
  - "Given a grouping export job is created with `export_kind=pdf`, when the artifact is rendered, then the renderer consumes the shared `GroupingExportPresentation` model and produces export-owned HTML/CSS instead of reusing the live planner DOM or converting the `XLSX` workbook to PDF."
  - "Given the PDF is generated, when the teacher opens it, then `A4` portrait is the default and only page contract in this slice."
  - "Given the PDF spans one or more pages, when groups are laid out, then class/document headings, group labels, member ordering, and section boundaries remain deterministic and easy to scan on screen and on paper."
  - "Given a group section is near a page break, when pagination occurs, then the renderer avoids orphaning a group heading at the bottom of a page without at least the first member row."
  - "Given the PDF succeeds, when the teacher downloads it, then the file is delivered through the explicit grouping export job lane with a teacher-safe filename and `Ladda ned igen` support from the grouping workspace."
---

## Problem

The grouping PDF is important for presentation, but without a locked page contract it could drift
into either a weak spreadsheet dump or an inappropriate seating-style poster.

## Goal

Render the first grouping `PDF` as an `A4` portrait digital handout that is clean to post in Teams
or Google Classroom and still printable when needed.

## Locked design decisions

- The grouping `PDF` is not a poster. Do not reuse seating poster layout, sizing, or naming.
- The grouping `PDF` must be rendered from export-owned HTML/CSS and converted through
  Sir Convert-a-Lot.
- The renderer input is the shared `GroupingExportPresentation` model, not the generated workbook.
- `A4` portrait is the only supported grouping PDF page contract in this slice.
- The document may span multiple pages. Do not force a one-page artifact at the cost of legibility.
- The PDF must keep the same deterministic group order and member order as the `Dela och exportera`
  workbook sheet from `PR-0140`.

## Non-goals

- Supporting `A3`, landscape, or teacher-selectable paper sizes.
- Adding poster-style room geometry, seating markers, or classroom fixtures.
- Introducing multiple PDF themes or branding variants.

## Implementation plan

1. Build a PDF renderer view model from the shared presentation contract:
   - add `src/skriptoteket/application/curated_apps/classroom_planner/exports/grouping_pdf_view_model.py`
2. Implement the export-owned HTML/CSS renderer:
   - add `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/grouping_pdf_renderer.py`
3. Wire the renderer into the grouping export job flow:
   - update `src/skriptoteket/application/curated_apps/classroom_planner/handlers/grouping_export_jobs.py`
   - update the grouping export completion/download helper under
     `src/skriptoteket/application/curated_apps/classroom_planner/handlers/`
4. Extend the SPA grouping export flow only where this artifact needs PDF-specific wording or
   status handling:
   - update `frontend/apps/skriptoteket/src/views/apps/useGroupingExportFlow.ts`
   - update `frontend/apps/skriptoteket/src/views/apps/components/PlannerExportActionGroup.vue`
   - update `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.vue`

## PDF layout specification

- Page size: `A4`
- Orientation: portrait
- Page posture: digital handout first, printout second
- Header block at the top of each page:
  - document title `Gruppindelning`
  - class name
  - export date
- Group sections are stacked vertically in group order.
- Each group section contains:
  - group heading
  - a simple two-column member table with `Nr` and `Elev`
- Use generous white space and clear rules/borders, not poster-style oversized geometry.
- Keep light branding only, if any.
- Pagination rule:
  - never leave a group heading alone at the bottom of a page
  - move the heading to the next page if the first member row does not fit with it

## File naming

- Filename stem comes from `GroupingExportPresentation.filename_stem`.
- Final PDF filename pattern:
  - `<filename_stem>-a4-portrait.pdf`
- Example:
  - `sa24d-gruppindelning-a4-portrait.pdf`

## Test plan

- Rendering tests proving:
  - `A4` portrait contract
  - deterministic group/member order
  - pagination guard against orphaned headings
- Application tests for create-job, Sir Convert submission, callback completion or terminal polling,
  Vault persistence, and download metadata.
- Frontend tests proving the grouping export menu still defaults to `Excel (.xlsx)` while the PDF
  path remains available as `PDF (A4 stående)`.
- Live browser/manual proof:
  - open grouping workspace
  - export `PDF (A4 stående)`
  - confirm download succeeds
  - visually inspect the artifact for digital readability and clean page breaks

## Rollback plan

- Remove grouping PDF rendering while preserving the grouping `XLSX` artifact and the shared
  grouping export contract.
