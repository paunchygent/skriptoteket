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
  - "Given seating export options are shown in the workspace, when the teacher opens the export menu, then `PDF` remains the default seating export path while `Excel (.xlsx)` appears as a secondary menu option rather than replacing the poster export default."
  - "Given a teacher exports the current seating draft as `XLSX`, when the artifact is generated, then the workbook is editable, structured, generated locally inside Skriptoteket, and clearly tied to the current class and seating arrangement."
  - "Given the seating `XLSX` workbook is generated, when the teacher opens it, then it contains exactly two teacher-facing worksheets named `Redigera sittplatser` and `Dela och exportera`, with `Redigera sittplatser` as the first tab and the operational editing sheet."
  - "Given the teacher uses `Redigera sittplatser`, when they review the workbook, then one explicit Excel table presents full student names plus teacher-facing seat/location columns so room semantics stay visible in a table-first way rather than as a raw debug dump."
  - "Given the teacher uses `Dela och exportera`, when they share the workbook or save it as PDF from Excel, then the sheet presents a cleaner secondary presentation view with placed and unplaced students separated clearly and `A4` landscape page setup."
  - "Given unplaced students exist, when the workbook is generated, then they are included explicitly rather than silently omitted."
  - "Given seating PDF and seating XLSX both exist, when the teacher chooses between them, then PDF remains the poster-grade print artifact while XLSX remains the editable structured export."
  - "Given seating `XLSX` is produced, when the file is delivered, then it does not call Sir Convert-a-Lot and instead uses a lightweight local workbook generation path."
ui_impact: "Yes (additional seating export choice)"
data_impact: "Yes (explicit seating spreadsheet artifact)"
---

## Context

The seating PDF solves the whiteboard poster use case. The next teacher-visible need is an editable export that can be adjusted, reformatted, or shared in spreadsheet workflows without diluting the poster PDF or replacing the current poster-first default.

## Notes

- Keep this separate from the PDF renderer.
- Do not treat XLSX as a fallback for the poster use case.
- Favor a stylized, teacher-friendly workbook over a raw data dump.
- Lock the workbook before implementation starts:
  - `Redigera sittplatser` is the operational sheet and first tab
  - `Dela och exportera` is the cleaner secondary presentation sheet
- Use full student names, not poster-style shortened labels.
- Preserve room semantics in a table-first way instead of trying to recreate the visual room canvas.
- Unplaced students must be explicit in the artifact.
- Planned PR slices:
  - `PR-0142` for the seating `XLSX` menu option, local export contract, and flow wiring
  - `PR-0143` for the seating `XLSX` workbook renderer, sheet design, and delivery flow
