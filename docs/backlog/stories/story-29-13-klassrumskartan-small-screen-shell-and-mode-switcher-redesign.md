---
type: story
id: ST-29-13
title: "Klassrumskartan small-screen shell and mode-switcher redesign"
status: ready
owners: "agents"
created: 2026-04-30
updated: 2026-04-30
epic: "EPIC-29"
dependencies:
  - "ST-29-07"
acceptance_criteria:
  - "Given the viewport is at the `EPIC-29` phone review width, when the planner shell renders, then it does not show a four-option segmented workspace rail."
  - "Given the teacher is on a small screen, when a workspace is active, then the active mode is shown as a compact primary affordance and all modes are reachable through a `Lägen` bottom sheet."
  - "Given the `Lägen` bottom sheet opens, when the teacher inspects available modes, then `Översikt`, `Grupper`, `Sittplatser`, and `Regler` are listed with clear labels, icons, and current-mode state."
  - "Given laptop and desktop review widths render, when this shell slice ships, then the existing desktop-first workspace selector is not regressed by the phone companion layout."
  - "Given production implementation begins, when the first code slice is planned, then it is grounded in the approved mockup at `docs/mockups/st-29-small-screen-workspace-redesign/small-screen-workspaces-mode-sheet-mockup.png` and any updated mockup iteration is captured before code changes."
ui_impact: "Yes (small-screen planner shell and mode switching)"
data_impact: "No"
---

## Context

The existing small-screen rail fails because it tries to preserve the full
desktop workspace selector in a phone-width surface. This story replaces the
cramped segmented rail with a phone-specific shell pattern: show the active
workspace and open all workspaces through a bottom sheet.

## Notes

- This is the shared prerequisite for the workspace-specific small-screen
  stories.
- The goal is not full desktop parity on phone. It is a credible companion
  shell that lets each workspace own a reduced layout.
- The approved visual direction is retained in
  `docs/mockups/st-29-small-screen-workspace-redesign/`.

## Planned PR Slices

- [PR-0284: ST-29-13 small-screen mode sheet shell](../prs/pr-0284-st-29-13-small-screen-mode-sheet-shell.md)
