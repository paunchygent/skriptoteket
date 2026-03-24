---
type: pr
id: PR-0128
title: "Klassrumskartan: grouping and seating student-pool split-pane scrolling"
status: ready
owners: "agents"
created: 2026-03-24
updated: 2026-03-24
stories:
  - "ST-26-06"
tags: ["frontend", "ux", "klassrumskartan", "scrolling", "playwright"]
dependencies:
  - "PR-0114"
  - "PR-0117"
acceptance_criteria:
  - "Grouping and seating use bounded desktop split-pane layouts so the student pool becomes a true local scroll region."
  - "The student-pool header stays fixed while only the list body scrolls."
  - "Lower groups and lower seats remain usable while teachers can still reach top-of-list names without page-level hunting."
  - "A focused browser proof verifies the split-pane scrolling behavior on the live local SPA."
---

## Problem

The shared student-pool component already exposes a scrollable list body, but the surrounding layout
does not consistently bound the pool height. In practice that means the list can fail to behave as a
reliable local scroll region, especially when the teacher needs to place top-of-list students into
lower seating rows or lower grouping targets.

## Goal

Turn grouping and seating into true bounded split panes on desktop so the student pool becomes a
usable local working region rather than a page-flow side column.

## Locked design decisions

- Keep the current desktop-first planner direction.
- Do not replace the student-pool component with task-specific duplicates.
- Keep grouping and seating semantically different even if they share the same split-pane
  discipline.
- Preserve the seating zoom behavior introduced earlier; scrolling fixes must not regress canvas
  usability.

## Non-goals

- No toolbar redesign in this PR.
- No changes to overview cards.
- No new seating/grouping actions.

## Implementation plan

- Refactor grouping workspace layout so the student pool and group board share a bounded desktop
  height.
- Refactor seating workspace layout so the student pool and room canvas share a bounded desktop
  height.
- Keep the pool header outside the scrolling list body.
- Ensure the room canvas still owns its own viewport/overflow behavior and does not steal the pool's
  scroll responsibility.
- Add focused browser proof that exercises real student placement with longer lists on the local
  SPA.

## Proposed module focus

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerStudentPool.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/GroupBoard.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/RoomCanvas.vue`

## Test plan

- Focused frontend tests for the bounded student-pool layout contract.
- Manual browser verification on the live local SPA at common laptop/desktop widths proving:
  - grouping list scrolls independently
  - seating list scrolls independently
  - lower seats/groups remain usable while the top names remain reachable

## Rollback plan

- Revert the split-pane bounding changes while keeping the shared student-pool primitive and the
  earlier zoom behavior intact.

## References

- Story parent: [ST-26-06](../stories/story-26-06-klassrumskartan-scrollable-fixed-previews-and-student-pool-scroll-regions.md)
- Planner shell/shared primitive baseline: [PR-0114](pr-0114-klassrumskartan-planner-shell-decomposition-and-shared-ui-primitives.md)
- Seating zoom baseline: [PR-0117](pr-0117-klassrumskartan-seating-workspace-viewport-zoom-parity.md)
- Frontend skill: [skriptoteket-frontend-specialist](../../../.claude/skills/skriptoteket-frontend-specialist/SKILL.md)
- Browser automation skill: [playwright-testing](../../../.claude/skills/playwright-testing/SKILL.md)
- Design-system rule: [045-huleedu-design-system](../../../.agents/rules/045-huleedu-design-system.md)
- Browser automation rule: [075-browser-automation](../../../.agents/rules/075-browser-automation.md)
