---
type: pr
id: PR-0140
title: "Klassrumskartan: grouping XLSX workbook layout and artifact delivery"
status: ready
owners: "agents"
created: 2026-03-25
updated: 2026-03-25
stories:
  - "ST-26-05"
tags: ["backend", "xlsx", "klassrumskartan", "export", "grouping"]
acceptance_criteria:
  - "Given a grouping export job is created with `export_kind=xlsx`, when the workbook is generated, then Skriptoteket produces the file locally with `openpyxl` from the shared `GroupingExportPresentation` model rather than routing the job through Sir Convert-a-Lot."
  - "Given the workbook is opened, when the teacher inspects it, then it contains exactly two visible worksheets named `Redigera grupper` and `Dela och exportera` in that order."
  - "Given the teacher uses `Redigera grupper`, when they sort, filter, or edit rows, then one explicit Excel table exposes the locked columns `Grupp`, `Gruppordning`, `Elevordning`, and `Elevnamn` with a frozen header row and no merged cells."
  - "Given the teacher uses `Dela och exportera`, when they save the sheet as PDF from Excel or share the workbook as-is, then the sheet uses clear document headings, one visually bounded table per group, deterministic ordering, and `A4` portrait page setup."
  - "Given the workbook artifact succeeds, when the teacher downloads it, then the file is stored as a Vault-backed export artifact with a teacher-safe filename instead of a generic `output.xlsx`."
---

## Problem

The story now says the grouping workbook must be editable and presentation-ready, but that still
leaves too many implementation decisions unless we lock the workbook shape and renderer choices.

## Goal

Generate the first teacher-quality grouping `XLSX` artifact with a stable workbook layout that is
easy to edit and still clean enough to share directly.

## Locked design decisions

- Use `openpyxl`, which already exists in this repo, for workbook generation.
- Do not use `pandas` to render the final teacher workbook.
- Generate `XLSX` locally inside Skriptoteket. Do not route `XLSX` through Sir Convert-a-Lot.
- The workbook has exactly two visible sheets:
  - `Redigera grupper`
  - `Dela och exportera`
- Sheet order is fixed as above.
- The active sheet on open is `Dela och exportera` so the workbook presents well when opened from
  Teams or Google Classroom, while the flat edit sheet still remains the first tab.
- `Redigera grupper` contains one Excel table only, with the exact visible columns:
  - `Grupp`
  - `Gruppordning`
  - `Elevordning`
  - `Elevnamn`
- `Dela och exportera` must not contain internal ids, debug data, or hidden planner semantics.

## Non-goals

- Importing the edited workbook back into Klassrumskartan.
- Adding formulas that attempt to keep the presentation sheet live-synced to user edits after
  export.
- Supporting alternate workbook themes or teacher-selectable styles in this slice.

## Implementation plan

1. Build a renderer-facing workbook model from the shared presentation contract:
   - add `src/skriptoteket/application/curated_apps/classroom_planner/exports/grouping_xlsx_view_model.py`
2. Implement the workbook renderer:
   - add `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/grouping_xlsx_renderer.py`
3. Wire the renderer into the grouping export job flow:
   - update `src/skriptoteket/application/curated_apps/classroom_planner/handlers/grouping_export_jobs.py`
   - add or update a grouping export completion/download helper under
     `src/skriptoteket/application/curated_apps/classroom_planner/handlers/`
4. Persist/download the finished workbook through the grouping export-job seam:
   - update `src/skriptoteket/infrastructure/repositories/classroom_planner_grouping_export_jobs.py`
   - update `src/skriptoteket/web/api/v1/apps_classroom_planner_grouping.py`

## Workbook specification

### Sheet 1: `Redigera grupper`

- One table only.
- Table starts at `A1`.
- Freeze panes at `A2`.
- Turn on autofilter through the Excel table, not through ad hoc row styling.
- Exact visible columns:
  - `Grupp`
  - `Gruppordning`
  - `Elevordning`
  - `Elevnamn`
- One row per student.
- Rows are pre-sorted by:
  1. `Gruppordning`
  2. `Elevordning`
  3. `Elevnamn`
- No merged cells.
- No internal ids.

### Sheet 2: `Dela och exportera`

- Row 1: document title `Gruppindelning`
- Row 2: class name
- Row 3: export timestamp or generated date label
- One group section after another in deterministic order.
- Each group section contains:
  - one styled heading row with the group label
  - one header row with `Nr` and `Elev`
  - one row per student in member order
- Use borders/fill/typography for section separation rather than merged decorative blocks.
- Page setup:
  - `A4`
  - portrait
  - fit to width `1`
  - unlimited page height
  - repeat rows `1:3` when printed

## File naming

- Filename stem comes from `GroupingExportPresentation.filename_stem`.
- Final `XLSX` filename pattern:
  - `<filename_stem>.xlsx`
- Example:
  - `sa24d-gruppindelning.xlsx`

## Test plan

- Unit tests for the renderer proving:
  - exact worksheet names
  - exact visible column names on `Redigera grupper`
  - deterministic group/member ordering
  - `A4` portrait page setup on `Dela och exportera`
- Application tests for successful local generation, Vault persistence, and download metadata.
- Open the produced workbook in a real spreadsheet editor during manual verification and confirm:
  - the workbook opens on `Dela och exportera`
  - sorting/editing the flat sheet is straightforward
  - saving `Dela och exportera` as PDF from Excel yields a clean result

## Rollback plan

- Remove the `XLSX` renderer and keep the grouping export contract in place for later work.
