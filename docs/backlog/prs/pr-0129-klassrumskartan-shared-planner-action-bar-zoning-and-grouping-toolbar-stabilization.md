---
type: pr
id: PR-0129
title: "Klassrumskartan: shared planner action-bar zoning and grouping toolbar stabilization"
status: ready
owners: "agents"
created: 2026-03-24
updated: 2026-03-24
stories:
  - "ST-29-03"
tags: ["frontend", "ux", "klassrumskartan", "toolbar", "refactor"]
dependencies:
  - "PR-0114"
  - "PR-0128"
acceptance_criteria:
  - "The shared planner action-bar seam supports explicit leading, primary, and secondary zones."
  - "Grouping adopts the zoned toolbar structure without losing any current workflow actions."
  - "Grouping controls remain visually stable across common laptop widths instead of reordering through wrap."
---

## Problem

The shared planner action bar exists, but it currently behaves more like a flexible row wrapper than
like a real toolbar contract. Grouping is the safest first adopter for a stable zoning model because
it does not also carry the explicit export cluster that seating now needs to preserve.

## Goal

Introduce a stronger shared toolbar structure and stabilize grouping around that structure first.

## Locked design decisions

- Use the shared planner action-bar seam instead of creating a second unrelated toolbar primitive.
- Keep grouping-specific semantics intact; this is a structure pass, not a fake generic abstraction.
- Prefer explicit zones over width-driven wrap order.
- Keep clearly secondary actions eligible for overflow instead of competing with main workflow
  controls.

## Non-goals

- No seating export-cluster work in this PR.
- No overview button hierarchy work in this PR.
- No new grouping capabilities.

## Implementation plan

- Extend the shared planner action-bar component API around stable layout zones.
- Update grouping to map setup/context, primary workflow, and secondary actions into those zones.
- Keep undo/redo visually anchored with the rest of the main workflow rather than drifting through
  row wrap.
- Tune grouping spacing for desktop/laptop widths before any mobile collapse behavior.
- Add focused component coverage for the zoned toolbar rendering.

## Proposed module focus

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceActionBar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarOverflowMenu.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarIconButton.vue`

## Test plan

- Focused frontend tests for zoned action-bar rendering and grouping toolbar behavior.
- Manual browser verification that grouping remains ordered and legible at common laptop widths.

## Rollback plan

- Revert the shared action-bar zoning API and restore the current grouping action row while keeping
  the broader shell decomposition from `PR-0114`.

## References

- Story parent: [ST-29-03](../stories/story-29-03-klassrumskartan-shared-desktop-workspace-composition-primitives.md)
- Planner shell/shared primitive baseline: [PR-0114](pr-0114-klassrumskartan-planner-shell-decomposition-and-shared-ui-primitives.md)
- Overview/shell simplification baseline: [PR-0112](pr-0112-klassrumskartan-overview-design-simplification-and-seamless-workspace-transitions.md)
- Frontend skill: [skriptoteket-frontend-specialist](../../../.claude/skills/skriptoteket-frontend-specialist/SKILL.md)
- Design-system rule: [045-huleedu-design-system](../../../.agents/rules/045-huleedu-design-system.md)
