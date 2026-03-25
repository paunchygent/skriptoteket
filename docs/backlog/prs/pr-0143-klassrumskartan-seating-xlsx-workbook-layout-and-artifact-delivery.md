---
type: pr
id: PR-0143
title: "Klassrumskartan: seating XLSX workbook layout and artifact delivery"
status: ready
owners: "agents"
created: 2026-03-25
updated: 2026-03-25
stories:
  - "ST-26-03"
tags: ["backend", "xlsx", "klassrumskartan", "export", "seating"]
acceptance_criteria:
  - "Given a seating export job succeeds with `export_kind=xlsx`, when the workbook is opened, then it contains exactly two teacher-facing worksheets named `Redigera sittplatser` and `Dela och exportera`, with `Redigera sittplatser` as the first tab."
  - "Given the teacher uses `Redigera sittplatser`, when they review the workbook, then one explicit Excel table presents full student names, placed/unplaced status, and teacher-facing seat/location columns so room semantics stay visible in a table-first form."
  - "Given unplaced students exist, when the workbook is opened, then they are included explicitly instead of being omitted."
  - "Given the teacher uses `Dela och exportera`, when they share the workbook or save it as PDF from Excel, then the sheet presents a cleaner secondary view with placed students and unplaced students separated clearly and `A4` landscape page setup."
  - "Given the workbook artifact is downloaded, when the filename is inspected, then it uses a teacher-safe seating filename instead of a generic `output.xlsx`."
---

## Problem

The current seating `XLSX` story still leaves the workbook shape underspecified. Without a locked
sheet design, the next implementation team would have to invent the operational table, decide how
to represent room semantics, and decide what to do with unplaced students.

## Goal

Generate a local seating workbook that is operational first, presentation second, and explicit
enough that a junior developer can implement it without making product decisions.

## Locked design decisions

- Use `openpyxl`, which already exists in the repo, for workbook generation.
- Do not use `pandas` for the final teacher workbook.
- The workbook has exactly two visible sheets:
  - `Redigera sittplatser`
  - `Dela och exportera`
- `Redigera sittplatser` is the first tab and the operational sheet.
- Use full student names exactly as shown in the app, not poster-style shortened labels.
- Preserve room semantics in a table-first way. Do not try to recreate the visual seating map in
  Excel.
- Unplaced students must be explicit in both the operational and presentation sheet.
- The presentation sheet page setup is `A4` landscape.

## Non-goals

- Re-importing edited seating workbooks back into the planner.
- Rendering a mini room map in Excel.
- Replacing the poster PDF as the preferred presentation artifact.

## Implementation plan

1. Build a renderer-facing workbook model for seating `XLSX`:
   - add `src/skriptoteket/application/curated_apps/classroom_planner/exports/seating_xlsx_view_model.py`
2. Implement the workbook renderer:
   - add `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/seating_xlsx_renderer.py`
3. Wire renderer output into the seating export job flow:
   - update `src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_jobs.py`
   - update `src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_job_completion.py`
4. Keep delivery/Vault behavior aligned with the existing seating export download lane:
   - update `src/skriptoteket/infrastructure/repositories/classroom_planner_export_jobs.py`
   - update `src/skriptoteket/web/api/v1/apps_classroom_planner_seating.py`

## Workbook specification

### Sheet 1: `Redigera sittplatser`

- One Excel table only.
- Freeze panes at `A2`.
- Exact visible columns:
  - `Status`
  - `Elevnamn`
  - `Plats`
  - `Rad`
  - `Kolumn`
- `Status` values in this slice:
  - `Placerad`
  - `Ej placerad`
- `Plats` uses the same teacher-facing seat label model as the app.
- `Rad` and `Kolumn` are blank for unplaced students.
- Full student names only.
- One row per student.

### Sheet 2: `Dela och exportera`

- Row 1: document title `Sittplacering`
- Row 2: class name
- Row 3: classroom name if one exists, otherwise a teacher-safe placeholder such as `Inget klassrum valt`
- Main placed-student table with columns:
  - `Plats`
  - `Elevnamn`
  - `Rad`
  - `Kolumn`
- Separate secondary table below for `Ej placerade elever`.
- Page setup:
  - `A4`
  - landscape
  - fit to width `1`
  - unlimited page height
  - repeat rows `1:3` when printed

## File naming

- Final `XLSX` filename pattern:
  - `<class-slug>-sittplacering.xlsx`
- Example:
  - `sa24d-sittplacering.xlsx`

## Test plan

- Renderer tests proving:
  - exact worksheet names
  - exact operational-sheet columns
  - full-name usage
  - explicit unplaced-student handling
  - `A4` landscape page setup on `Dela och exportera`
- Application tests proving local generation, Vault persistence, and download metadata.
- Manual spreadsheet verification:
  - operational sheet opens as the first tab
  - seat/location semantics are obvious without opening the app
  - presentation sheet saves cleanly to PDF from Excel

## Rollback plan

- Remove the `XLSX` workbook renderer while preserving the existing seating PDF export lane.
