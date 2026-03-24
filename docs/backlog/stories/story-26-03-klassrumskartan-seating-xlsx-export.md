---
type: story
id: ST-26-03
title: "Klassrumskartan — Seating XLSX export"
status: ready
owners: "agents"
created: 2026-03-24
epic: "EPIC-26"
dependencies: ["EPIC-24", "ST-26-01"]
acceptance_criteria:
  - "Given a teacher exports the current seating draft as `XLSX`, when the artifact is generated, then the workbook is editable, structured, and clearly tied to the current class and seating arrangement."
  - "Given the seating `XLSX` workbook is generated, when the teacher opens it, then it contains a clearly named primary worksheet for seat assignments and any additional worksheet remains narrowly focused on export-supporting seating data rather than generic debug/state dumps."
  - "Given the seating XLSX is opened in a spreadsheet editor, when the teacher reviews it, then the data is organized for practical editing and printing rather than as a raw internal dump."
  - "Given seating PDF and seating XLSX both exist, when the teacher chooses between them, then PDF remains the poster-grade print artifact while XLSX remains the editable structured export."
  - "Given seating export implementation uses document-generation infrastructure, when the workbook is produced, then the export path remains compatible with the dedicated conversion/export service boundary instead of introducing ad hoc planner-owned file-generation seams where avoidable."
ui_impact: "Yes (additional seating export choice)"
data_impact: "Yes (explicit seating spreadsheet artifact)"
---

## Context

The seating PDF solves the whiteboard poster use case. The next teacher-visible need is an editable export that can be adjusted, reformatted, or shared in spreadsheet workflows without diluting the poster PDF.

## Notes

- Keep this separate from the PDF renderer.
- Do not treat XLSX as a fallback for the poster use case.
- Favor a stylized, teacher-friendly workbook over a raw data dump.
- Keep worksheet shape explicit during implementation review so the story does not drift into an under-specified spreadsheet dump.
