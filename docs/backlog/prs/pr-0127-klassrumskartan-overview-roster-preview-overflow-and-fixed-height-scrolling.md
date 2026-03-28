---
type: pr
id: PR-0127
title: "Klassrumskartan: overview roster preview overflow and fixed-height scrolling"
status: ready
owners: "agents"
created: 2026-03-24
updated: 2026-03-24
stories:
  - "ST-29-04"
tags: ["frontend", "ux", "klassrumskartan", "overview"]
dependencies:
  - "PR-0110"
  - "PR-0114"
acceptance_criteria:
  - "The overview class preview preserves its fixed desktop card geometry while roster overflow scrolls internally instead of clipping or growing the card."
  - "The class preview no longer relies on low-value truncation limits once the roster exceeds the preview's visible height."
  - "The classroom panel remains visually aligned with the class panel after the overflow fix."
---

## Problem

The overview class panel is intentionally fixed-height and symmetric with the classroom panel, but
the current roster preview stops being trustworthy once the class grows beyond the visible preview
height. The problem is overflow handling, not the fixed-height layout itself.

## Goal

Keep the approved overview geometry while making longer class rosters usable through internal
scrolling and removal of artificial clipping/truncation behavior.

## Locked design decisions

- Keep the current fixed-height desktop overview composition.
- Do not make the class panel auto-grow with roster length.
- Do not redesign the classroom preview to match roster overflow behavior; only keep its card
  aligned visually.
- Prefer a real scroll container over "show first N names" truncation logic.

## Non-goals

- No changes to top-level planner shell layout.
- No class-management workflow changes.
- No changes to grouping or seating workspaces in this PR.

## Implementation plan

- Remove artificial roster preview truncation/limit logic from the overview preview path.
- Introduce a bounded internal scroll container for the roster preview body.
- Keep the current three-column compact desktop presentation unless a narrow implementation detail
  requires a small internal adjustment.
- Preserve the same card height and action-row layout so the class/classroom overview pair stays
  visually balanced.
- Add focused component coverage for overflow-state rendering.

## Proposed module focus

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerClassWorkspace.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRosterOverviewPanel.vue`

## Test plan

- Focused frontend tests proving long rosters render without truncation and stay inside a bounded
  scroll region.
- Manual browser check on the local SPA with a longer roster to confirm:
  - class card height stays fixed
  - roster body scrolls
  - classroom card remains visually aligned

## Rollback plan

- Restore the current fixed preview with truncation while keeping the overview management surface
  otherwise unchanged.

## References

- Story parent: [ST-29-04](../stories/story-29-04-klassrumskartan-overview-hierarchy-and-class-first-dashboard-redesign.md)
- Overview baseline: [PR-0110](pr-0110-klassrumskartan-overview-compact-class-and-classroom-management.md)
- Planner shell/shared primitive baseline: [PR-0114](pr-0114-klassrumskartan-planner-shell-decomposition-and-shared-ui-primitives.md)
- Frontend skill: [skriptoteket-frontend-specialist](../../../.claude/skills/skriptoteket-frontend-specialist/SKILL.md)
- Design-system rule: [045-huleedu-design-system](../../../.agents/rules/045-huleedu-design-system.md)
