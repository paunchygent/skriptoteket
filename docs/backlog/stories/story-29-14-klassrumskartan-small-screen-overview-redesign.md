---
type: story
id: ST-29-14
title: "Klassrumskartan small-screen overview redesign"
status: ready
owners: "agents"
created: 2026-04-30
updated: 2026-04-30
epic: "EPIC-29"
dependencies:
  - "ST-29-13"
acceptance_criteria:
  - "Given the teacher opens `Översikt` on a phone-sized viewport, when the view renders, then class status, class list, classroom context, and shared-link entry points are arranged as a reduced dashboard rather than stacked desktop panels."
  - "Given shared links exist for the active class or draft, when `Översikt` renders on phone, then `Delade länkar` is reachable as a compact row or action without taking over the default workspace."
  - "Given the teacher needs class or classroom management from phone, when the overview surface renders, then those actions are visible but visually subordinate to the active class context."
  - "Given the story is reviewed, when screenshots are captured, then visual inspection compares the result to the overview panel in `docs/mockups/st-29-small-screen-workspace-redesign/small-screen-workspaces-mode-sheet-mockup.png`."
ui_impact: "Yes (small-screen overview workspace)"
data_impact: "No"
---

## Context

`Översikt` needs its own small-screen composition. It should not inherit the
desktop dashboard as a vertical stack, and it should not bury mode switching or
class context under repeated full-width panels.

## Notes

- Build after `ST-29-13` defines the shared phone shell.
- Keep production data and draft semantics unchanged.
