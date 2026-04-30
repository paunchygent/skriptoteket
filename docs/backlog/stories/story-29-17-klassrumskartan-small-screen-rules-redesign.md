---
type: story
id: ST-29-17
title: "Klassrumskartan small-screen rules redesign"
status: ready
owners: "agents"
created: 2026-04-30
updated: 2026-04-30
epic: "EPIC-29"
dependencies:
  - "ST-29-13"
acceptance_criteria:
  - "Given the teacher opens `Regler` on a phone-sized viewport, when the view renders, then rule tools are presented as a compact task list or sheet-driven authoring flow instead of a cramped rail beside a map."
  - "Given selected students are part of rule authoring, when the teacher selects students on phone, then selected state and remove actions remain visible without overlapping the map or tool controls."
  - "Given the rules apply to the whole class, when the reduced rules layout renders, then this scope is clear in a compact status row without adding explanatory panels."
  - "Given the story is reviewed, when screenshots are captured, then visual inspection compares the result to the rules panel in `docs/mockups/st-29-small-screen-workspace-redesign/small-screen-workspaces-mode-sheet-mockup.png`."
ui_impact: "Yes (small-screen rules workspace)"
data_impact: "No"
---

## Context

The current rules rail is especially fragile on small screens because it tries
to keep tools, selected students, feedback, and map context visible at once.
This story gives `Regler` its own reduced authoring pattern.

## Notes

- Build after `ST-29-13`.
- Keep smart-rule persistence and solver contracts unchanged.
