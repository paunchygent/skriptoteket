---
type: pr
id: PR-0130
title: "Klassrumskartan: seating toolbar stabilization, export-cluster alignment, and responsive proof"
status: ready
owners: "agents"
created: 2026-03-24
updated: 2026-03-24
stories:
  - "ST-26-07"
tags: ["frontend", "ux", "klassrumskartan", "toolbar", "export", "playwright"]
dependencies:
  - "PR-0120"
  - "PR-0129"
acceptance_criteria:
  - "Seating adopts the zoned toolbar structure without regressing the explicit export flow introduced earlier."
  - "The classroom selector remains a clear setup/context control while primary seating actions and the export cluster stay visually ordered."
  - "A focused browser proof verifies seating-toolbar stability at common desktop/laptop widths."
---

## Problem

Seating now carries more kinds of actions than grouping:

- setup context through classroom selection
- draft workflow actions
- explicit export controls
- secondary overflow actions

Without a stable zoning model, that mix risks feeling improvised as widths tighten.

## Goal

Apply the zoned planner toolbar to seating in a way that keeps the explicit export cluster usable
and intentional.

## Locked design decisions

- Preserve the explicit export cluster from `PR-0120`.
- Keep the classroom selector visually anchored as setup context, not as part of the primary action
  cluster.
- Do not flatten all seating actions into one equal-weight row.
- Validate the final structure against real desktop/laptop widths with browser proof.

## Non-goals

- No changes to the export job contract or export artifact behavior.
- No overview action hierarchy work in this PR.
- No classroom-management redesign.

## Implementation plan

- Apply the zoned action-bar structure to seating.
- Keep export controls in their own stable cluster relative to classroom selection and main draft
  actions.
- Tune spacing, wrapping thresholds, and overflow posture against common laptop widths.
- Add focused browser proof for the live seating toolbar on the local SPA.

## Proposed module focus

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceActionBar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarOverflowMenu.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarIconButton.vue`

## Test plan

- Focused frontend tests for seating toolbar zoning and export-cluster rendering.
- Manual browser verification on the live local SPA at desktop/laptop widths proving:
  - classroom selector stays stable
  - main seating actions stay grouped
  - export cluster remains visible and ordered

## Rollback plan

- Restore the current seating action row while preserving the underlying explicit export flow from
  `PR-0120`.

## References

- Story parent: [ST-26-07](../stories/story-26-07-klassrumskartan-stable-task-toolbars-and-action-zoning.md)
- Export action baseline: [PR-0120](pr-0120-klassrumskartan-seating-export-action-teacher-flow-and-browser-proof.md)
- Grouping zoning baseline: [PR-0129](pr-0129-klassrumskartan-shared-planner-action-bar-zoning-and-grouping-toolbar-stabilization.md)
- Frontend skill: [skriptoteket-frontend-specialist](../../../.claude/skills/skriptoteket-frontend-specialist/SKILL.md)
- Browser automation skill: [playwright-testing](../../../.claude/skills/playwright-testing/SKILL.md)
- Design-system rule: [045-huleedu-design-system](../../../.agents/rules/045-huleedu-design-system.md)
- Browser automation rule: [075-browser-automation](../../../.agents/rules/075-browser-automation.md)
