---
type: story
id: ST-29-15
title: "Klassrumskartan small-screen grouping redesign"
status: done
owners: "agents"
created: 2026-04-30
updated: 2026-05-04
epic: "EPIC-29"
dependencies:
  - "ST-29-13"
acceptance_criteria:
  - "Given the teacher opens `Grupper` on a phone-sized viewport, when the view renders, then group work is presented as a focused reduced workspace instead of desktop student-pool plus board panels stacked together."
  - "Given group count and repeated actions are needed on phone, when the grouping toolbar renders, then add, shuffle, overflow, and group switching use compact icon-supported controls with usable touch targets."
  - "Given students and groups cannot both dominate phone portrait at once, when the reduced layout ships, then the slice explicitly chooses the primary grouping surface and moves secondary context behind controls or sheets."
  - "Given the story is reviewed, when screenshots are captured, then visual inspection compares the result to the grouping panel in `docs/mockups/st-29-small-screen-workspace-redesign/small-screen-workspaces-mode-sheet-mockup.png`."
ui_impact: "Yes (small-screen grouping workspace)"
data_impact: "No"
---

## Context

Grouping is a real workspace, not a page of cards. On phone it needs a reduced
composition that keeps group manipulation legible without pretending the full
desktop split-pane can fit.

## Notes

- Build after `ST-29-13`.
- Any deferred action must be explicit in the story task that implements it.

## Planned PR Slices

- [PR-0288: ST-29-15 small-screen grouping workspace](../prs/pr-0288-st-29-15-small-screen-grouping-workspace.md)
