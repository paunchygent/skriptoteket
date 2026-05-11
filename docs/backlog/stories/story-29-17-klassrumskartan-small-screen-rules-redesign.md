---
type: story
id: ST-29-17
title: "Klassrumskartan small-screen rules redesign"
status: done
owners: "agents"
created: 2026-04-30
updated: 2026-05-09
epic: "EPIC-29"
dependencies:
  - "ST-29-13"
acceptance_criteria:
  - "Given the teacher opens `Regler` on a phone-sized viewport, when the view renders, then rule tools are presented as a compact task list or sheet-driven authoring flow instead of a cramped rail beside a map."
  - "Given selected students are part of rule authoring, when the teacher selects students on phone, then selected state and remove actions remain visible without overlapping the map or tool controls."
  - "Given the rules apply to the whole class, when the reduced rules layout renders, then this scope is clear in a compact status row without adding explanatory panels."
  - "Given saved rules or pending authoring actions need management controls, when the reduced rules layout renders, then edit, delete, clear, and save appear through compact row actions, menus, or subordinate sheets rather than persistent management panels."
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
- Preserve the desktop `PR-0155` rail/map/inspector workspace at laptop and
  desktop widths.

## Follow-up PR Slices

- [PR-0310: ST-27-09 phone fixed-seat rules map affordance](../prs/pr-0310-st-27-09-phone-fixed-seat-rules-map-affordance.md)
  (`done` 2026-05-09): adds the phone `Fast plats` classroom-seat map while
  preserving the reduced relationship-rule student-selection flow. The
  post-review addition adds collision-free symbolic rule markers through the
  shared rules-map marker contract and clearer Smart outcome toast copy on
  phone.
- [PR-0312: Shared phone classroom-map touch viewport gestures](../prs/pr-0312-shared-phone-classroom-map-touch-viewport-gestures.md)
  (`done` 2026-05-10) adds reusable pinch/touch zoom for the phone `Fast
  plats` map without changing fixed-seat selection semantics.
- [PR-0313: Shared phone classroom-map real-device pinch remediation](../prs/pr-0313-shared-phone-classroom-map-real-device-pinch-remediation.md)
  follows up on real iPhone evidence that the simplified phone `Fast plats`
  map did not visibly zoom even after the shared gesture layer shipped.
- [PR-0314: Solver-owned rule marker semantics](../prs/pr-0314-solver-owned-rule-marker-semantics.md)
  follows up on marker-tone drift so soft-rule colors in `Regler` reflect
  solver-owned diagnostics or remain neutral.
- [PR-0315: Phone rules active-rule management and delete affordances](../prs/pr-0315-st-29-17-phone-rules-active-rule-management.md)
  follows up on the reduced phone rules workflow by adding compact edit/delete
  affordances for persisted `Nära läraren`, `Håll nära`, `Håll isär`, and
  active-template `Fast plats` rules.
