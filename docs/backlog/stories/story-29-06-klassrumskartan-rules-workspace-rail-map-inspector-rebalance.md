---
type: story
id: ST-29-06
title: "Klassrumskartan — Rules workspace rail-map-inspector rebalance"
status: ready
owners: "agents"
created: 2026-03-28
epic: "EPIC-29"
dependencies:
  - "ST-29-01"
  - "ST-29-02"
  - "ST-29-03"
  - "ST-27-07"
acceptance_criteria:
  - "Given the teacher enters `Regler`, when the redesigned desktop layout renders, then the workspace reads as tool rail plus dominant map plus supporting inspector rather than as three equal-weight bordered cards."
  - "Given map controls, status, and view switching render inside `Regler`, when this slice ships, then those controls stay compact and local to the map surface rather than introducing extra full-width explanatory panels."
  - "Given the inspector lists or edits active rules, when the slice ships, then it supports the map task without matching the map in visual mass or button density."
  - "Given browser proof is run at the `EPIC-29` `laptop` (`1366x768`) and `desktop` (`1440x900`) review viewports, when the slice is reviewed, then the map hierarchy is obvious at a glance and the rail/inspector remain clearly secondary."
ui_impact: "Yes (rules workspace layout and hierarchy)"
data_impact: "No"
---

## Context

The dedicated rules workspace was the correct product move, but its current composition still feels
too card-equal and too wrapped in chrome. This story rebalances the workspace without reopening the
smart-rule product direction.

## Notes

- This is a layout and hierarchy story, not a smart-rule contract story.
- The shared interaction model from the shipped rules workspace remains intact.

## References

- Epic parent: [EPIC-29](../epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md)
- Rules-workspace baseline: [ST-27-07](story-27-07-klassrumskartan-rules-workspace-and-dual-map-authoring.md)
- Workspace doctrine: [REF-klassrumskartan-workspace-ui-doctrine-2026-03-28](../../reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md)
