---
type: pr
id: PR-0143
title: "Klassrumskartan: seating XLSX workbook layout and artifact delivery"
status: done
owners: "agents"
created: 2026-03-25
updated: 2026-03-26
stories:
  - "ST-26-03"
tags: ["backend", "xlsx", "klassrumskartan", "export", "seating"]
acceptance_criteria:
  - "Given a seating export job succeeds with `export_kind=xlsx`, when the workbook is opened, then it contains exactly one teacher-facing worksheet named `Sittplacering`."
  - "Given the teacher uses `Sittplacering`, when they review the workbook, then the sheet preserves the seating plan as a spatial classroom grid where rows, columns, empty seats, and aisle gaps remain visually readable."
  - "Given unplaced students exist, when the workbook is opened, then they are included explicitly instead of being omitted."
  - "Given the teacher shares the workbook or saves it as PDF from Excel, when they use the same `Sittplacering` sheet, then the workbook remains clean enough to use directly without a duplicate presentation tab."
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
- The workbook has exactly one visible sheet:
  - `Sittplacering`
- Use full student names exactly as shown in the app, not poster-style shortened labels.
- Preserve room semantics by recreating the seating arrangement as a spatial grid in Excel.
- Keep empty seats and visible aisle gaps explicit so the workbook still reads like the classroom.
- Keep the sheet visually focused on the classroom map; do not add decorative title blocks, helper
  coordinates, or a duplicate presentation sheet.
- Unplaced students must stay explicit in a minimal secondary section below the map.
- The single sheet page setup is `A4` landscape.

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

### Sheet 1: `Sittplacering`

- Start rendering the seating plan at `A1` with no title block above it.
- Render the seating plan as a classroom-shaped grid instead of a flat list.
- Every seat position in the current template gets one visible seat cell.
- Assigned seats show the full student name inside the seat cell.
- Unassigned seats stay visible as empty seat cells rather than disappearing.
- Missing seat positions between occupied columns/rows stay blank so aisle gaps remain legible.
- Use wrapped text, centered alignment, and bounded seat boxes so the sheet can be read at a
  glance without opening the app.
- Place `Ej placerade elever` below the grid as a separate section, one student name per row.
- Do not add row/column helper notes outside the map; the spatial layout is the teacher-facing
  reference.
- Page setup:
  - `A4`
  - landscape
  - fit to width `1`
  - unlimited page height

## File naming

- Final `XLSX` filename pattern:
  - `<class-slug>-sittplacering.xlsx`
- Example:
  - `sa24d-sittplacering.xlsx`

## Test plan

- Renderer tests proving:
  - exact worksheet name
  - spatial seat placement matches classroom row/column order
  - aisle gaps stay visible
  - empty seats stay visible
  - full-name usage
  - explicit unplaced-student handling
  - `A4` landscape page setup on `Sittplacering`
- Application tests proving local generation, Vault persistence, and download metadata.
- Manual spreadsheet verification:
  - operational sheet opens as the first tab
  - seat/location semantics are obvious without opening the app
  - presentation sheet saves cleanly to PDF from Excel

## Rollback plan

- Remove the `XLSX` workbook renderer while preserving the existing seating PDF export lane.
