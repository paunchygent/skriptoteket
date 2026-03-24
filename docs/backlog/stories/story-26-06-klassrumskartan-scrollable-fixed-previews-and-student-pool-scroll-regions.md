---
type: story
id: ST-26-06
title: "Klassrumskartan — Scrollable fixed previews and student-pool scroll regions"
status: ready
owners: "agents"
created: 2026-03-24
epic: "EPIC-26"
dependencies:
  - "EPIC-24"
  - "ST-24-03"
  - "ST-24-04"
  - "ST-24-07"
acceptance_criteria:
  - "Given the teacher is in `Översikt`, when the active class roster is longer than the fixed preview height, then the roster preview scrolls internally without changing the card height or breaking the balanced desktop layout."
  - "Given the overview class preview is fixed-height by design, when roster overflow appears, then the preview preserves the current symmetric card geometry instead of auto-growing or clipping names."
  - "Given the teacher is in `Grupper`, when the unassigned student list is longer than the visible pane height, then the student pool becomes a true local scroll region while the group board stays visible."
  - "Given the teacher is in `Sittplatser`, when the teacher places students into lower seats, then the student pool remains independently scrollable and usable without forcing page-level hunting back to top names."
  - "Given the scroll-region slice ships, when browser proof is run on the live local SPA, then it proves the fixed preview remains aligned and both task-local student pools are usable on common laptop/desktop viewports."
ui_impact: "Yes (overview preview overflow + grouping/seating workspace layout)"
data_impact: "No"
---

## Context

`ST-24-07` intentionally made `Oversikt` compact, fixed-height, and symmetric on desktop. That
design direction still stands. The issue to solve now is not card growth or overall shell
composition; it is overflow handling and local usability once class sizes become longer in real
teacher data.

At the same time, the shared student pool introduced during the shell decomposition is visually
correct but not yet structurally bounded enough to behave like a reliable local scroll container in
grouping and seating.

## Problem

Two distinct usability issues remain:

- the overview roster preview can clip instead of scrolling once the class grows beyond the preview
  height
- the grouping and seating student pools do not behave as dependable split-pane scroll regions,
  which makes lower groups and lower seats awkward to work with on laptop-sized viewports

These are desktop-first layout hardening issues rather than feature-direction changes.

## Decisions

- Keep the overview card heights fixed and visually balanced.
- Do not re-open the earlier decision to keep the overview previews symmetric on desktop.
- Prefer internal scroll containers over dynamic card growth.
- Treat grouping and seating as bounded split panes on desktop:
  - student list owns local overflow
  - board/canvas owns its own visible work surface
- Preserve current mobile stacking unless a strictly necessary responsive fix emerges during
  implementation.

## Notes

- This story is deliberately narrow:
  - no new planner features
  - no new teacher-note semantics
  - no redesign of the top shell or overview composition
- The intended comparison baseline remains the editor's stronger scroll-region discipline, not a
  mandate to copy the editor's exact layout.

## Recommended decomposition

### PR-0127

Focus:

- remove overview roster preview clipping/truncation behavior
- preserve the fixed-height overview card geometry
- add internal scrolling to the class preview only where overflow exists
- keep the classroom preview surface visually aligned with the class preview card

### PR-0128

Focus:

- harden grouping and seating into true desktop split panes
- make the shared student-pool list body independently scrollable
- keep the student-pool header fixed while the list body scrolls
- ensure lower groups and lower seats remain usable while top-of-list names stay reachable
- add focused browser proof for real local scroll behavior

## References

- Epic parent: [EPIC-26](../epics/epic-26-klassrumskartan-explicit-exports-and-class-list-import.md)
- Overview foundation: [ST-24-07](story-24-07-group-seating-studio-overview-first-workspace-management.md)
- Grouping foundation: [ST-24-03](story-24-03-group-seating-studio-grouping-fundamentals-and-saved-groupings.md)
- Seating foundation: [ST-24-04](story-24-04-group-seating-studio-seating-fundamentals-and-saved-arrangements.md)
- Shared planner shell decomposition: [PR-0114](../prs/pr-0114-klassrumskartan-planner-shell-decomposition-and-shared-ui-primitives.md)
- Seating zoom parity: [PR-0117](../prs/pr-0117-klassrumskartan-seating-workspace-viewport-zoom-parity.md)
- Frontend skill: [skriptoteket-frontend-specialist](../../../.claude/skills/skriptoteket-frontend-specialist/SKILL.md)
- Browser automation skill: [playwright-testing](../../../.claude/skills/playwright-testing/SKILL.md)
- Design-system rule: [045-huleedu-design-system](../../../.agents/rules/045-huleedu-design-system.md)
- Browser automation rule: [075-browser-automation](../../../.agents/rules/075-browser-automation.md)
- Sprint-planning workflow: [ref-sprint-planning-workflow](../../reference/ref-sprint-planning-workflow.md)
