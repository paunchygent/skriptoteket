---
type: pr
id: PR-0140
title: "Klassrumskartan: grouping XLSX workbook layout and artifact delivery"
status: done
owners: "agents"
created: 2026-03-25
updated: 2026-03-26
stories:
  - "ST-26-05"
tags: ["backend", "xlsx", "klassrumskartan", "export", "grouping"]
acceptance_criteria:
  - "Given a grouping export job is created with `export_kind=xlsx`, when the workbook is generated, then Skriptoteket produces the file locally with `openpyxl` from the shared `GroupingExportPresentation` model rather than routing the job through Sir Convert-a-Lot."
  - "Given the workbook is opened, when the teacher inspects it, then it contains exactly two visible teacher-facing worksheets named `Redigera grupper` and `Dela och exportera` in that order."
  - "Given the teacher uses `Redigera grupper`, when they open the workbook, then one protected student table exposes `Nr i grupp`, `Elev`, and `Grupp (välj)` while a separate protected `Gruppregister` table exposes `Grupp` and `Gruppordning (välj)` with a frozen header row and no merged cells."
  - "Given the teacher edits rows for already assigned students in `Redigera grupper`, when they move students between groups through the `Grupp (välj)` dropdown or change group ordering through `Gruppordning (välj)`, then `Dela och exportera` updates accordingly from workbook formulas."
  - "Given rows in `Redigera grupper` have blank `Grupp`, when the teacher opens or prints `Dela och exportera`, then those rows are excluded from the presentation sheet."
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
- The workbook has exactly two visible teacher-facing sheets:
  - `Redigera grupper`
  - `Dela och exportera`
- Sheet order is fixed as above.
- One hidden helper sheet is allowed to support workbook formulas and sorting for the presentation
  view.
- The active sheet on open is `Dela och exportera` so the workbook presents well when opened from
  Teams or Google Classroom, while the flat edit sheet still remains the first tab.
- `Redigera grupper` uses two teacher-facing table surfaces:
  - one protected student table with the exact visible columns `Nr i grupp`, `Elev`, and
    `Grupp (välj)`
  - one protected `Gruppregister` table with the exact visible columns `Grupp` and
    `Gruppordning (välj)`
- The edit sheet only unlocks teacher-intended cells:
  - student reassignment in `Grupp (välj)`
  - group-order changes in `Gruppordning (välj)`
- Group reassignment uses Excel list validation against the current `Gruppregister` values.
- Group ordering uses Excel list validation against the available one-based ordering values.
- The sheet includes short in-workbook instructions that explain what to edit and what not to edit.
- `Dela och exportera` is formula-linked for assigned rows only.
- Reassigning already assigned students between groups and changing group/member order must update
  `Dela och exportera`.
- Assigning previously ungrouped students inside the workbook is not a guaranteed supported
  workflow in this slice.
- `Dela och exportera` must not contain internal ids, debug data, or hidden planner semantics.

## Non-goals

- Importing the edited workbook back into Klassrumskartan.
- Treating offline completion of previously ungrouped students as a fully supported workflow.
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

- One protected student table starting at `A1`.
- One protected `Gruppregister` table separated from the main edit grid on the same sheet.
- Freeze panes at `A2`.
- Turn on autofilter through the Excel table, not through ad hoc row styling.
- Student table columns:
  - `Nr i grupp`
  - `Elev`
  - `Grupp (välj)`
- `Gruppregister` columns:
  - `Grupp`
  - `Gruppordning (välj)`
- One row per student in the student table.
- Students without a current group render with:
  - populated `Nr i grupp`
  - populated `Elev`
  - blank `Grupp (välj)`
- The student table is pre-sorted by current group/member order at export time.
- Only the dropdown-backed group-selection cells and group-order cells are editable.
- The sheet protection must prevent broader worksheet edits such as adding/removing students or
  editing the non-dropdown student data directly.
- Include short in-sheet guidance that makes the intended use explicit:
  - move students by using the `Grupp (välj)` list
  - reorder groups by changing `Gruppordning (välj)`
  - export a new workbook for larger roster changes
- No merged cells.
- No internal ids.

### Hidden helper sheet

- One hidden helper sheet is allowed.
- It may derive sorted assigned rows, group boundaries, and presentation line types from
  the student table plus `Gruppregister`.
- Helper formulas must ignore rows with blank `Grupp`.
- The helper sheet is implementation detail only and must not be teacher-facing.

### Sheet 2: `Dela och exportera`

- Row 1: document title `Gruppindelning`
- Row 2: class name
- Row 3: export timestamp or generated date label
- The presentation sheet is formula-linked to `Redigera grupper` through the hidden helper sheet.
- Only rows with non-blank `Grupp` participate in the presentation.
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
  - exact visible worksheet names
  - hidden helper sheet presence/state
  - exact visible column names on `Redigera grupper`
  - rows with blank `Grupp` are excluded from the presentation-linked helper data
  - reassigning already assigned students and changing group/member order update the presentation
    references
  - deterministic group/member ordering
  - `A4` portrait page setup on `Dela och exportera`
- Application tests for successful local generation, Vault persistence, and download metadata.
- Open the produced workbook in a real spreadsheet editor during manual verification and confirm:
  - the workbook opens on `Dela och exportera`
  - the protected edit sheet exposes only the intended dropdown/order edits
  - moving already assigned students between groups through `Grupp (välj)` updates
    `Dela och exportera`
  - changing `Gruppordning (välj)` updates the group order on `Dela och exportera`
  - blank-group rows remain absent from `Dela och exportera`
  - saving `Dela och exportera` as PDF from Excel yields a clean result

## Rollback plan

- Remove the `XLSX` renderer and keep the grouping export contract in place for later work.
