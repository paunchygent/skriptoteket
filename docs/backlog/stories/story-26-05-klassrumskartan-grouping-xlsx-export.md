---
type: story
id: ST-26-05
title: "Klassrumskartan — Grouping XLSX export"
status: ready
owners: "agents"
created: 2026-03-24
epic: "EPIC-26"
dependencies: ["EPIC-24"]
acceptance_criteria:
  - "Given a teacher exports the current grouping draft as `XLSX`, when the workbook is opened, then it is the default grouping export artifact and is editable, structured, and organized around groups rather than around seating positions."
  - "Given the grouping `XLSX` workbook is generated, when the teacher opens it, then it contains exactly two teacher-facing worksheets named `Redigera grupper` and `Dela och exportera`."
  - "Given the teacher uses `Redigera grupper`, when they sort or edit the workbook, then one explicit Excel table exposes the locked columns `Grupp`, `Gruppordning`, `Elevordning`, and `Elevnamn` so students can be moved, reordered, and swapped without reverse-engineering the file."
  - "Given the teacher uses `Dela och exportera`, when they share the workbook or save it as PDF from Excel, then the sheet presents clear document headings plus one visually bounded table per group in deterministic group/member order with `A4` portrait-friendly page setup."
  - "Given the grouping XLSX is used outside the app, when teachers edit or reformat it, then the workbook remains a practical collaboration artifact rather than a raw internal dump or a carrier for internal ids/debug data."
  - "Given grouping spreadsheet export is implemented, when document-generation seams are chosen, then the export path remains consistent with the dedicated conversion/export service boundary where applicable."
ui_impact: "Yes (grouping spreadsheet export choice)"
data_impact: "Yes (explicit grouping spreadsheet artifact)"
---

## Context

Editable spreadsheet export is the primary remaining grouping artifact because teachers often need to swap students, reorder members, and make final presentation edits after export before sharing the result outside the app.

## Notes

- Keep grouping XLSX separate from seating XLSX.
- Favor teacher-friendly structure and readability over backend-shaped raw data exports.
- Lock the visible workbook shape before implementation starts:
  - `Redigera grupper` is the flat editable sheet
  - `Dela och exportera` is the presentation sheet
- Do not expose internal ids on the teacher-facing sheets.
- Planned PR slices:
  - `PR-0139` for the shared grouping export action hierarchy and presentation contract
  - `PR-0140` for the grouping `XLSX` workbook renderer, sheet design, and delivery flow
