---
type: story
id: ST-29-16
title: "Klassrumskartan small-screen seating redesign"
status: done
owners: "agents"
created: 2026-04-30
updated: 2026-05-09
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

## Follow-up Alignment

- [PR-0310: ST-27-09 phone fixed-seat rules map affordance](../prs/pr-0310-st-27-09-phone-fixed-seat-rules-map-affordance.md)
  (`done` 2026-05-09) extended the phone seating workspace by reusing the
  simplified classroom map from phone fixed-seat rule authoring. The phone
  `Sittplatser` map now preserves classroom-relative seat geometry while
  simplifying labels and wall fixtures for touch use.
- The phone seating map deliberately avoids a per-seat remove button. A short
  press on an occupied phone seat removes the assignment, while a long press
  followed by release over another seat moves or swaps students. Same-first-name
  students remain distinguishable through centered last-name initials below the
  first-name row.
- Desktop and tablet seating remain on the full `RoomCanvas`; the simplified
  classroom map is a phone-only companion surface.
