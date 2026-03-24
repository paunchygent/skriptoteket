---
type: story
id: ST-26-04
title: "Klassrumskartan — Grouping PDF export"
status: ready
owners: "agents"
created: 2026-03-24
epic: "EPIC-26"
dependencies: ["EPIC-24"]
acceptance_criteria:
  - "Given a teacher exports the current grouping draft as `PDF`, when the artifact is generated, then the result is a grouping-specific print artifact rather than a reused seating poster format."
  - "Given the grouping PDF is rendered, when the artifact is reviewed, then group labels, member ordering, and group boundaries remain deterministic and easy to scan without inheriting seating-specific geometry assumptions."
  - "Given grouping export ships, when the teacher reviews the artifact, then groups, member ordering, and teacher-facing labels remain easy to scan and print."
  - "Given grouping and seating exports both exist, when they are rendered, then each artifact follows its own presentation model rather than forcing one blended export contract."
  - "Given grouping PDF conversion runs, when the final document is produced, then the export path stays aligned to the dedicated Sir Convert-a-Lot service boundary rather than a parallel planner-owned conversion lane."
ui_impact: "Yes (grouping export action)"
data_impact: "Yes (explicit grouping PDF artifact)"
---

## Context

Grouping has a different teacher use case and visual grammar than seating. Its export should follow the same explicit-artifact principle while remaining a distinct print format.

## Notes

- Do not reuse the seating poster layout directly.
- Preserve grouping order and labels in a deterministic way so later exports remain trustworthy.
- Keep grouping export sequencing in the epic notes rather than encoding seating-export preferences as hard technical prerequisites.
