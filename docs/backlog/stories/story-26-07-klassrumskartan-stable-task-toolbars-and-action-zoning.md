---
type: story
id: ST-26-07
title: "Klassrumskartan — Stable task toolbars and action zoning"
status: ready
owners: "agents"
created: 2026-03-24
epic: "EPIC-26"
dependencies:
  - "EPIC-24"
  - "ST-24-03"
  - "ST-24-04"
  - "ST-26-01"
  - "ST-26-06"
acceptance_criteria:
  - "Given the teacher is in `Grupper`, when the viewport narrows across common laptop widths, then selectors, undo/redo, task actions, and overflow controls remain in stable zones rather than visually reordering through wrap."
  - "Given the teacher is in `Sittplatser`, when the explicit export controls are present, then the export cluster remains visible and subordinate to the main task workflow rather than competing with setup selectors."
  - "Given grouping and seating share a task-toolbar structure, when the slice ships, then the planner uses a stable zoning model that improves order and readability without flattening real task differences."
  - "Given the toolbar story ships, when browser proof is run on the live local SPA, then grouping and seating remain legible and orderly at common desktop/laptop widths before the mobile breakpoint."
ui_impact: "Yes (grouping/seating task toolbar structure)"
data_impact: "No"
---

## Context

`PR-0114` created a shared planner action-bar wrapper, which was the right decomposition step, but
the current grouping and seating toolbars still behave like wrap-prone action strips rather than
deliberate work toolbars. This becomes more noticeable now that the planner also hosts explicit
teacher I/O actions such as seating export.

The editor remains the strongest internal comparison point because it separates context, workflow,
and secondary actions into stable zones instead of letting the toolbar order collapse under width
pressure.

## Problem

Grouping and seating currently put too many controls into one flexible row:

- selectors and setup context compete with task actions
- undo/redo can visually drift relative to the main workflow
- seating export risks feeling bolted on instead of intentionally placed
- control order becomes less trustworthy as width tightens

This makes the planner feel less product-settled than the editor even when the underlying features
already exist.

## Decisions

- Keep grouping and seating visually related, but do not force them into a fake-generic toolbar.
- Use explicit layout zones inside the shared planner action-bar seam:
  - leading/context
  - primary workflow
  - secondary/overflow
- Preserve the explicit seating export cluster introduced under `ST-26-01`.
- Keep overflow actions available rather than removing controls to avoid wrap.
- Optimize for desktop/laptop first, with responsive collapse only after the toolbar remains orderly
  at the canonical desktop widths.

## Notes

- This story is about structure, grouping, and hierarchy, not about inventing new planner actions.
- The intended win is stability:
  - clearer scan path
  - more reliable muscle memory
  - less row-order drift

## Recommended decomposition

### PR-0129

Focus:

- introduce stable zoning support in the shared planner action bar
- adopt the zoned structure in grouping first
- keep grouping-specific workflow semantics intact while removing wrap-order instability
- move clearly secondary actions into a more deliberate overflow posture where appropriate

### PR-0130

Focus:

- adopt the zoned action-bar structure in seating
- keep the explicit export cluster visible and orderly relative to classroom selection and primary
  task actions
- tune spacing and breakpoint behavior against real desktop/laptop widths
- add a browser proof for toolbar order and viewport behavior

## References

- Epic parent: [EPIC-26](../epics/epic-26-klassrumskartan-explicit-exports-and-class-list-import.md)
- Export action baseline: [ST-26-01](story-26-01-klassrumskartan-seating-pdf-poster-export-with-standalone-renderer.md)
- Scroll-region prerequisite: [ST-26-06](story-26-06-klassrumskartan-scrollable-fixed-previews-and-student-pool-scroll-regions.md)
- Shared planner shell decomposition: [PR-0114](../prs/pr-0114-klassrumskartan-planner-shell-decomposition-and-shared-ui-primitives.md)
- Overview/shell simplification: [PR-0112](../prs/pr-0112-klassrumskartan-overview-design-simplification-and-seamless-workspace-transitions.md)
- Seating export action baseline: [PR-0120](../prs/pr-0120-klassrumskartan-seating-export-action-teacher-flow-and-browser-proof.md)
- Editor comparison reference: [ST-14-32](story-14-32-editor-cohesion-pass-input-selectors.md)
- Frontend skill: [skriptoteket-frontend-specialist](../../../.claude/skills/skriptoteket-frontend-specialist/SKILL.md)
- Browser automation skill: [playwright-testing](../../../.claude/skills/playwright-testing/SKILL.md)
- Design-system rule: [045-huleedu-design-system](../../../.agents/rules/045-huleedu-design-system.md)
- Browser automation rule: [075-browser-automation](../../../.agents/rules/075-browser-automation.md)
- Sprint-planning workflow: [ref-sprint-planning-workflow](../../reference/ref-sprint-planning-workflow.md)
