---
type: story
id: ST-27-04
title: "Klassrumskartan — Smart grouping v1"
status: ready
owners: "agents"
created: 2026-03-25
epic: "EPIC-27"
dependencies: ["ST-27-01", "ST-27-02"]
acceptance_criteria:
  - "Given the teacher is in `Grupper` and `Smart` is `off`, when they use `Slumpa`, then grouping remains the current random reshuffle behavior."
  - "Given the teacher is in `Grupper` and `Smart` is `on`, when they use `Slumpa`, then the planner requests a backend-owned smart grouping result that reuses the same relation model as smart seating."
  - "Given the teacher wants room-informed grouping, when the grouping smart surface is shown, then the seat-distance signal is controlled by one explicit toggle such as `Ska hur nära de sitter räknas?` rather than by a vague classroom-awareness label."
  - "Given seat-distance is disabled or usable seating context does not exist, when smart grouping runs, then `Support seat` does not silently influence grouping."
  - "Given eligible seating checkpoints exist, when seat-distance or relation carry-over is enabled in grouping, then smart grouping may consume those checkpoints without treating raw drafts as history."
  - "Given `Use history` is enabled but no eligible grouping or seating checkpoints exist for the requested grouping history inputs, when the teacher tries to run smart grouping, then the planner does not silently fall back to no-history behavior and instead blocks that history-enabled run with a short teacher-facing explanation."
ui_impact: "Yes (smart grouping toggle and seat-distance toggle)"
data_impact: "Yes (smart grouping request/response contract)"
---

## Context

Grouping should benefit from the same underlying relation model as seating, but the teacher needs a
clearer explanation than "classroom-aware." An explicit seat-distance question is easier to
understand and easier to turn off.

## Notes

- Keep the grouping smart flow separate from seating even when they share backend primitives.
- The seat-distance toggle is a mode-specific addition, not a new global planning panel.
- Grouping should stay understandable even when no usable seating checkpoints exist.
- If later grouping export checkpoints exist, they should become the primary grouping-history lane,
  while seating checkpoints remain a secondary source for relation carry-over and optional
  seating-distance signals.
