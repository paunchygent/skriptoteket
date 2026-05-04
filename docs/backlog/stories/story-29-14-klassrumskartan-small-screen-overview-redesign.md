---
type: story
id: ST-29-14
title: "Klassrumskartan small-screen overview redesign"
status: done
owners: "agents"
created: 2026-04-30
updated: 2026-05-04
epic: "EPIC-29"
dependencies:
  - "ST-29-13"
acceptance_criteria:
  - "Given the teacher opens `Översikt` on a phone-sized viewport, when the view renders, then class status, class list, classroom context, and the `Dela` distribution entry point are arranged as a reduced dashboard rather than stacked desktop panels."
  - "Given links or file export actions exist for active grouping or seating work, when `Översikt` renders on phone, then the single `Dela` / `Dela och exportera` affordance is reachable as a compact row or action without taking over the default workspace."
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

## Planned PR Slices

- [PR-0285: ST-29-14 small-screen overview dashboard](../prs/pr-0285-st-29-14-small-screen-overview-dashboard.md)
