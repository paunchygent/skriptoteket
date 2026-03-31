---
type: story
id: ST-29-06
title: "Klassrumskartan — Rules workspace no-classroom fallback and organized off-map selection"
status: done
owners: "agents"
created: 2026-03-28
updated: 2026-03-31
epic: "EPIC-29"
dependencies:
  - "ST-27-07"
  - "ST-29-01"
  - "ST-29-02"
  - "ST-29-03"
  - "ST-29-10"
acceptance_criteria:
  - "Given the teacher enters `Regler` with a class selected but no classroom selected, when `Planeringskarta` is active, then the primary surface explains the optional classroom step with the exact copy `Välj ett klassrum i arbetsytan Sittplatser och placera ut eleverna om du vill arbeta med regler direkt utifrån klassrummets möblering.`"
  - "Given students cannot currently be shown on the planning map, when the workspace renders, then they appear in one compact organized selectable roster surface rather than as a loose wrapping pill cloud."
  - "Given the teacher selects or deselects students from that off-map roster while a smart-rule tool is active, when selection changes, then selection state, ordered selection, and pending-rule feedback remain clear without requiring a classroom."
  - "Given the teacher works in `Grupper`, when the workspace supporting hint renders, then it reads exactly `Slumpa eller placera eleverna och dra dem mellan grupperna tills du är nöjd.`"
  - "Given browser proof is run at the `EPIC-29` `laptop` (`1366x768`) and `desktop` (`1440x900`) review viewports, when the no-classroom rules state is checked, then the empty-map instruction is understandable at a glance and the off-map student surface reads as organized rather than as overflow debris."
ui_impact: "Yes (rules workspace empty-map state, organized off-map student selection, and one grouping helper-copy update)"
data_impact: "No"
---

## Context

The earlier `Regler` cut-over and later shared workspace work already delivered most of the
original rail-map-inspector redesign goal. The remaining visible gap is the no-classroom
planning-map state.

Today that state still mixes a map-oriented instruction with a loose cloud of small student pills.
Because teachers may legitimately want to work with rules before choosing a classroom, this surface
must feel like a valid rules-first workspace state rather than like leftover fallback UI.

## Notes

- This is a layout, organization, and teacher-language story, not a smart-rule contract story.
- `Regler` remains available as soon as a class exists; this story does not add a classroom
  prerequisite.
- The off-map student surface remains actionable for rule authoring; it is not a read-only list.
- This story absorbs one small `Grupper` workspace copy alignment because it touches the same
  planner-facing support language and introduces no behavior change.

## References

- Epic parent: [EPIC-29](../epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md)
- Rules-workspace baseline: [ST-27-07](story-27-07-klassrumskartan-rules-workspace-and-dual-map-authoring.md)
- Shared workspace primitives baseline: [ST-29-03](story-29-03-klassrumskartan-shared-desktop-workspace-composition-primitives.md)
- Workspace gating baseline: [ST-29-10](story-29-10-klassrumskartan-first-run-workspace-gating-and-prerequisite-guidance.md)
- Workspace doctrine: [REF-klassrumskartan-workspace-ui-doctrine-2026-03-28](../../reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md)
- Shared control language: [REF-shared-tool-control-language-v1](../../reference/ref-shared-tool-control-language-v1.md)
