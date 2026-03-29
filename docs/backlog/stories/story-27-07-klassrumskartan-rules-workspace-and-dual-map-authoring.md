---
type: story
id: ST-27-07
title: "Klassrumskartan — Dedicated rules workspace and dual-map authoring"
status: done
owners: "agents"
created: 2026-03-27
epic: "EPIC-27"
dependencies: ["ST-27-01", "ST-27-06"]
acceptance_criteria:
  - "Given the planner shell is visible, when the teacher wants to work with smart rules, then `Regler` exists as a first-class workspace beside `Översikt`, `Grupper`, and `Sittplatser`."
  - "Given the teacher opens `Regler`, when the desktop workspace loads, then it presents one dedicated rule-authoring layout with a tool rail, one central classroom map, and one rule summary/inspector rather than an always-open seating or grouping side panel."
  - "Given `Planeringskarta` is active in `Regler`, when the map renders, then it preserves the real classroom geometry while ordering students alphabetically onto seats sorted in simple reading order."
  - "Given `Sittschema` is active in `Regler` and a current seating arrangement exists, when the teacher switches to that view, then the map mirrors the current seating draft without resetting the active tool or current temporary selection."
  - "Given no current seating arrangement exists, when the teacher tries to use `Sittschema`, then the workspace keeps that view unavailable with one short teacher-facing explanation instead of showing a misleading empty projection."
  - "Given the teacher uses one smart rule tool, when they hover or select students, then active-tool state, cursor state, hover state, and ordered selection feedback are all clearly visible before they commit the rule."
  - "Given one existing smart rule is shown in the rule summary, when the teacher chooses `Redigera`, then the correct tool is reactivated, the relevant students are preselected on the current map, and saving updates that rule rather than forcing remove-and-recreate; `Nära läraren` still persists as one consolidated rule rather than per-student cards."
  - "Given the teacher is in `Sittplatser` or `Grupper`, when smart controls are shown near `Slumpa`, then those task panes keep only a compact smart summary plus a small settings affordance near `Smart` that routes rule editing to `Regler`."
  - "Given a compact or collapsed task-pane smart drawer exists in `Sittplatser` or `Grupper`, when the teacher opens it, then it may show read-only rule summaries and mode-local smart toggles such as `Use history`, but it does not allow inline rule creation or rule editing."
ui_impact: "Yes (new `Regler` workspace, shared rule-authoring surface, and compact task-pane summaries)"
data_impact: "No"
---

## Context

The current smart-rule surface proved the roster-global rule model, but it still couples rule
authoring too tightly to the seating task pane. Teachers need a calmer desktop-first workflow where
rule editing feels like its own whole-class planning task rather than a clunky side panel inside
`Sittplatser` or a future duplicate panel inside `Grupper`.

## Notes

- `Regler` is now the only primary rule-authoring home in the planner shell.
- The default authoring view is `Planeringskarta`, not `Sittschema`.
- `Planeringskarta` should feel spatial, but still be easy to scan:
  - keep the room geometry
  - map students alphabetically onto seats in reading order
- `Sittschema` is a user preference view, not a separate workflow.
- The interaction model is shared across both map views:
  - selection is student-based, not seat-based
  - switching view does not clear the active tool or pending selection
- Use canonical iconography for tool identity rather than text-only active state.
- Strong pre-commit feedback matters more than extra features:
  - hover state
  - selected state
  - ordered multi-select badges
  - active-tool cursor/status feedback
- Rules must be editable from the main summary/inspector surface, not only removable.
- `Nära läraren` follows the same rail-owned pending count/chip/create-save flow as the
  relationship rules, even though it remains one seating-only rule at the data level.
- `Sittplatser` and `Grupper` may keep compact smart summaries and mode-local toggles, but they
  must not keep or introduce full rule-editing drawers.
