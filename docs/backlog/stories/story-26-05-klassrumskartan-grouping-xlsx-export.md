---
type: story
id: ST-26-05
title: "Klassrumskartan — Grouping XLSX export"
status: ready
owners: "agents"
created: 2026-03-24
epic: "EPIC-26"
dependencies: ["EPIC-24", "ST-26-04"]
acceptance_criteria:
  - "Given a teacher exports the current grouping draft as `XLSX`, when the workbook is opened, then it is editable, structured, and organized around groups rather than around seating positions."
  - "Given the grouping `XLSX` workbook is generated, when the teacher opens it, then worksheet organization, group ordering, and member rows are explicit enough that implementation can be verified against a stable export shape."
  - "Given the grouping XLSX is used outside the app, when teachers edit or reformat it, then the workbook remains a practical collaboration artifact rather than a raw internal dump."
  - "Given grouping spreadsheet export is implemented, when document-generation seams are chosen, then the export path remains consistent with the dedicated conversion/export service boundary where applicable."
ui_impact: "Yes (grouping spreadsheet export choice)"
data_impact: "Yes (explicit grouping spreadsheet artifact)"
---

## Context

After grouping PDF exists, the remaining teacher-facing need is an editable spreadsheet version that supports school workflows outside the app.

## Notes

- Keep grouping XLSX separate from seating XLSX.
- Favor teacher-friendly structure and readability over backend-shaped raw data exports.
- Make explicit during implementation review what worksheets and tables are required so this story remains testable at `ready` status.
