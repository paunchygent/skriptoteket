---
type: story
id: ST-26-04
title: "Klassrumskartan — Grouping PDF export"
status: ready
owners: "agents"
created: 2026-03-24
epic: "EPIC-26"
dependencies: ["EPIC-24", "ST-26-05"]
acceptance_criteria:
  - "Given a teacher exports the current grouping draft as `PDF`, when the artifact is generated, then the result is a grouping-specific print artifact rather than a reused seating poster format."
  - "Given the grouping PDF is rendered, when the teacher opens it, then `A4` portrait is the default page contract and the document reads first as a digital handout for Teams / Google Classroom and only secondarily as a printout."
  - "Given the grouping PDF is rendered, when the artifact is reviewed, then group labels, member ordering, group boundaries, and left-right row pairing remain deterministic and easy to scan without inheriting seating-specific geometry assumptions."
  - "Given grouping export ships, when the teacher reviews the artifact, then groups, member ordering, teacher-facing labels, and page breaks remain easy to scan on screen and on paper."
  - "Given grouping `XLSX` already exists, when the PDF is generated, then the PDF mirrors the same group ordering and teacher-facing naming as the approved presentation sheet rather than inventing a second contradictory presentation order."
  - "Given grouping and seating exports both exist, when they are rendered, then each artifact follows its own presentation model rather than forcing one blended export contract."
  - "Given grouping PDF conversion runs, when the final document is produced, then the export path uses the lightweight local HTML/CSS-to-PDF lane that best fits this renderer-owned handout artifact instead of forcing the heavier document-conversion service boundary."
  - "Given the grouping PDF is rendered, when the teacher opens it, then it uses a restrained Skriptoteket-branded letterhead and a two-column grid of framed group cards that reduces page count while keeping scan order intuitive."
ui_impact: "Yes (grouping export action)"
data_impact: "Yes (explicit grouping PDF artifact)"
---

## Context

Grouping has a different teacher use case and visual grammar than seating. Its PDF should follow the same explicit-artifact principle while remaining a distinct presentation format that comes after the editable workbook.

## Notes

- Do not reuse the seating poster layout directly.
- Do not reuse seating poster defaults such as `A3` landscape or wall-poster composition.
- Preserve grouping order and labels in a deterministic way so later exports remain trustworthy.
- The presentation should now read as:
  - restrained letterhead first
  - two-column left-right group pairing second
  - framed cards rather than one long stack of loose tables
- Treat this as the second grouping export artifact:
  - `ST-26-05` (`XLSX`) is the editable teacher workflow artifact
  - this story is the presentation/share artifact
- Planned PR slices:
  - `PR-0139` for the shared grouping export action hierarchy and presentation contract
  - `PR-0141` for the grouping `PDF` renderer, `A4` portrait layout, and delivery flow
