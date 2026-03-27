---
type: pr
id: PR-0155
title: "Klassrumskartan: rules workspace, dual-map authoring, and summary-link cutover"
status: ready
owners: "agents"
created: 2026-03-27
updated: 2026-03-27
stories:
  - "ST-27-07"
tags:
  [
    "frontend",
    "planner",
    "smart-assignment",
    "klassrumskartan",
    "ux",
  ]
dependencies:
  - "ADR-0074"
  - "EPIC-27"
  - "PR-0149"
  - "PR-0151"
  - "PR-0152"
  - "PR-0154"
acceptance_criteria:
  - "Given the planner shell renders its workspace navigation, when the teacher works with smart rules, then `Regler` appears as a dedicated top-level workspace rather than keeping primary rule editing inside `Sittplatser` or `Grupper`."
  - "Given the teacher opens `Regler`, when the desktop layout loads, then it provides one vertical tool rail, one central rules map surface, and one rule summary/inspector rather than an embedded seating-panel editor."
  - "Given `Planeringskarta` is selected, when the map renders, then it preserves room geometry while assigning students alphabetically onto seats sorted in reading order."
  - "Given `Sittschema` is selected and a current seating arrangement exists, when the teacher toggles views, then the map switches projections without resetting the active tool, temporary selection, or current edit session."
  - "Given smart tools are visible, when the teacher changes tools or selects students, then icon-based active-tool state, cursor state, hover state, and ordered selection feedback are all clear before rule commit."
  - "Given a saved smart rule is listed in the inspector, when the teacher chooses to edit it, then the correct tool and student selection are restored and saving updates the existing rule."
  - "Given the teacher is in `Sittplatser` or `Grupper`, when smart controls are shown near `Slumpa`, then those task panes expose only compact summary/settings affordances and route rule editing to `Regler` through a small settings icon near `Smart`."
  - "Given a compact or collapsed task-pane smart drawer exists, when the teacher opens it, then it may show read-only rule summaries plus mode-local smart toggles such as `Use history`, but it never hosts inline rule creation or rule editing."
---

## Problem

The current smart-rule authoring surface proved the roster-global rule contract, but it still keeps
too much rule-editing weight inside `Sittplatser`. That creates three UX problems:

- the seating task pane feels heavier than the teacher task at hand
- grouping risks inheriting the same always-open rule-panel pattern
- the current selection/tool feedback is too weak for a tool-based authoring workflow

Without a deliberate cut-over, later smart seating/grouping work would keep accreting around the
wrong editing home.

## Goal

Ship one shared frontend cut-over that makes `Regler` the dedicated smart-rule authoring workspace
while keeping `Sittplatser` and `Grupper` calm:

- add `Regler` as a first-class planner workspace
- provide the desktop-first three-part authoring layout
- support `Planeringskarta` and `Sittschema` as two projections of the same rule-selection model
- strengthen tool identity and selection feedback
- make existing rules editable from the main summary surface
- replace task-pane rule editors with compact smart summaries and a small settings-link affordance
  near `Smart`

## Non-goals

- Changing the backend smart-rule contract or rule persistence model from `PR-0151`
- Reworking backend smart seating run behavior from `PR-0154`
- Introducing search, filters, batch operations, or a new command palette for V1
- Turning task-pane drawers or overflow menus into full rule editors
- Adding a separate mobile-first rules workflow; this slice is desktop-first

## Implementation plan

1. Add the dedicated `Regler` workspace shell.
   - Extend the planner workspace selector to include `Regler`.
   - Update the workspace shell routing/rendering so `Regler` is first-class rather than a modal
     or drawer.

2. Split the current smart-rule surface into explicit desktop components.
   - Add `PlannerRulesWorkspacePane.vue`.
   - Add `PlannerRulesToolRail.vue`.
   - Add `PlannerRulesMapPanel.vue`.
   - Add `PlannerRulesMapCanvas.vue`.
   - Add `PlannerRulesSeatNode.vue`.
   - Add `PlannerRulesInspector.vue`.

3. Introduce the dual-map projection model.
   - `Planeringskarta`:
     - preserve classroom geometry
     - sort seats by reading order
     - place students alphabetically onto those seat positions
   - `Sittschema`:
     - mirror the current seating draft
   - Keep one shared interaction model keyed by `studentId` so view switches do not reset
     authoring state.

4. Strengthen the authoring affordances.
   - Move tool identity onto canonical iconography from the shared icon library.
   - Add explicit active-tool styling, hover/selection states, ordered multi-select badges, and a
     short status line.
   - Support editing existing rules by rehydrating the correct tool and selection state.

5. Cut over task-pane smart chrome.
   - Replace the seating-embedded full rule editor with a compact smart summary surface.
   - Add the same compact smart summary surface to grouping.
   - Keep any compact drawer read-only for rules, while still allowing mode-local smart toggles
     such as `Use history`.
   - Add one small settings affordance near `Smart` that routes rule editing into `Regler`.

## Test plan

- `pdm run fe-test -- --run src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts`
- Add or update focused Vitest coverage for:
  - rules workspace shell switching
  - `Planeringskarta` / `Sittschema` view retention
  - rule edit rehydration
  - compact task-pane smart summaries
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Live proof against `http://127.0.0.1:5173` covering:
  - open `Regler`
  - switch between `Planeringskarta` and `Sittschema`
  - create and edit one rule
  - verify seating/grouping task panes expose compact summary + settings-link affordance only

## Rollback plan

- Revert the `Regler` workspace addition and restore the previous smart-rule surface only if the
  cut-over blocks core planner use.
- If partial rollback is needed, preserve the roster-global smart-rule API and revert only the
  frontend workspace/surface changes.
