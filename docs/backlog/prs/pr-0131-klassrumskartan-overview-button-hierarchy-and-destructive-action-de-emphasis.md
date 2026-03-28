---
type: pr
id: PR-0131
title: "Klassrumskartan: overview button hierarchy and destructive-action de-emphasis"
status: ready
owners: "agents"
created: 2026-03-24
updated: 2026-03-24
stories:
  - "ST-29-04"
tags: ["frontend", "ux", "klassrumskartan", "overview", "buttons"]
dependencies:
  - "PR-0110"
  - "PR-0112"
acceptance_criteria:
  - "The overview class and classroom panels present create as the clear primary action."
  - "Edit is visually demoted to a secondary action without becoming hidden or ambiguous."
  - "Delete remains explicit but reads as a lower-emphasis destructive action rather than an equal-weight sibling."
---

## Problem

The overview cards are compositionally solid, but the action rows still look too prototype-like.
Create, edit, and delete currently read too much like equal peers, which weakens scanability and
puts destructive actions too close to the main CTA in visual weight.

## Goal

Rebalance the overview management actions so the hierarchy is obvious at a glance while keeping the
existing compact card layout.

## Locked design decisions

- Keep the current overview card layout and fixed-height symmetry.
- Make create the dominant CTA in both the class and classroom panels.
- Keep edit and delete visible within the same management surface.
- Do not hide destructive actions inside unrelated selectors or menus just to reduce weight.

## Non-goals

- No new overview capabilities.
- No resumable-card affordance work in this PR.
- No toolbar zoning changes in this PR.

## Implementation plan

- Rework the class/classroom panel action rows so create is the primary button.
- Demote edit to a lighter secondary treatment that still reads as intentional.
- Demote delete to a destructive treatment with lower overall emphasis than create.
- Reuse shared planner/button language where possible rather than inventing panel-specific button
  styles.

## Proposed module focus

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRosterOverviewPanel.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerTemplateOverviewPanel.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarIconButton.vue`

## Test plan

- Focused frontend tests for overview button ordering and treatment.
- Manual browser check confirming the overview still feels balanced while action hierarchy is more
  legible.

## Rollback plan

- Restore the current equal-weight overview action rows while preserving the current card
  composition.

## References

- Story parent: [ST-29-04](../stories/story-29-04-klassrumskartan-overview-hierarchy-and-class-first-dashboard-redesign.md)
- Overview management baseline: [PR-0110](pr-0110-klassrumskartan-overview-compact-class-and-classroom-management.md)
- Overview simplification baseline: [PR-0112](pr-0112-klassrumskartan-overview-design-simplification-and-seamless-workspace-transitions.md)
- Frontend skill: [skriptoteket-frontend-specialist](../../../.claude/skills/skriptoteket-frontend-specialist/SKILL.md)
- Design-system rule: [045-huleedu-design-system](../../../.agents/rules/045-huleedu-design-system.md)
