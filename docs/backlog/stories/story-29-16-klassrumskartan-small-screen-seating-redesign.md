---
type: story
id: ST-29-16
title: "Klassrumskartan small-screen seating redesign"
status: ready
owners: "agents"
created: 2026-04-30
updated: 2026-05-04
epic: "EPIC-29"
dependencies:
  - "ST-29-13"
acceptance_criteria:
  - "Given the teacher opens `Sittplatser` on a phone-sized viewport, when the view renders, then the classroom map remains the primary surface instead of being pushed below stacked chrome."
  - "Given zoom and fit controls are needed on phone, when the seating map renders, then those controls are compact, touch-safe, and do not overlap student seats or room fixtures."
  - "Given the full student pool is too large for the default phone view, when the reduced seating layout ships, then student access is handled through a deliberate sheet/drawer/action rather than a squeezed side rail."
  - "Given share/export is available on phone, when the teacher opens distribution from `Sittplatser`, then one compact `Dela` affordance opens the merged `Dela och exportera` surface with both link and file actions."
  - "Given the story is reviewed, when screenshots are captured, then visual inspection compares the result to the seating panel in `docs/mockups/st-29-small-screen-workspace-redesign/small-screen-workspaces-mode-sheet-mockup.png`."
ui_impact: "Yes (small-screen seating workspace)"
data_impact: "No"
---

## Context

The phone seating workspace should still read as a classroom map. The reduced
layout must protect the spatial surface and move secondary student/context
operations out of the way.

## Notes

- Build after `ST-29-13`.
- Preserve the `PR-0286` single `Dela och exportera` distribution model on
  small screens; do not split links and file export into separate phone rows.
- This is separate from the public share-page renderer work in `PR-0276`.
