---
type: pr
id: PR-0136
title: "Klassrumskartan: seat drag preview and room-editor same-tool toggle removal"
status: ready
owners: "agents"
created: 2026-03-25
updated: 2026-03-25
stories:
  - "ST-24-04"
tags: ["frontend", "ux", "klassrumskartan", "room-builder", "drag-drop", "playwright"]
dependencies:
  - "PR-0116"
  - "PR-0128"
acceptance_criteria:
  - "When a teacher drags a student from the seating student list, the drag preview reads as a seating token rather than as a list-row rectangle."
  - "When the teacher has a room-editor tool selected and clicks an empty valid target, the matching seat, floor fixture, or wall object is placed."
  - "When the teacher clicks an already placed object again with the same tool still selected, that same-kind object is removed instead of requiring the eraser."
  - "When the teacher clicks a conflicting occupied target with a different tool selected, the existing object remains unchanged and is not removed as a side effect."
  - "A focused browser proof verifies the drag-preview polish and same-tool placement/removal behavior on the live local SPA."
---

## Problem

The classroom planning surfaces already support the core mechanics, but two interaction details still
make the experience feel more prototype-like than product-like:

- dragging a student from the seating list still advertises the list-row shape instead of the seat
  token teachers are actually placing
- the classroom editor forces object removal through a separate eraser/clear path even when the
  teacher is clearly clicking the same already-placed object with the same tool

That leaves the seating workflow visually inconsistent and makes repeated room-editing actions feel
more laborious than the seat tool already proves they need to be.

## Goal

Polish the seating and classroom-editing interactions so drag/drop previews and repeated same-tool
clicks behave like one coherent classroom-planning system.

## Status note (2026-03-31)

`ST-24-04` is already closed, but this PR id is not called out in the story close-out or handoff.
Its status is intentionally left unchanged until someone confirms whether this slice shipped under a
different PR or should be marked superseded/dropped.

## Locked design decisions

- Keep this as one PR slice: the seating drag-preview polish and the classroom-editor toggle-off
  behavior ship together.
- Match the drag image to the seating token visual language rather than the student-list row.
- Extend the existing seat-style toggle-off behavior to same-kind room objects instead of inventing
  separate per-tool removal rules.
- Preserve current conflict rules: different-tool placement attempts must not silently delete the
  existing occupant.
- Validate both behaviors with live browser proof on the local SPA.

## Non-goals

- No redesign of the student pool or the planner shell layout.
- No change to saved room geometry or placement persistence contracts.
- No general conflict-resolution redesign beyond same-tool toggle-off behavior.
- No new room-object categories or editing tools.

## Implementation plan

- Use a seat-shaped drag preview for seating student drags so the drag affordance matches the seat
  token the teacher is targeting.
- Refine the room-editor placement reducer/helpers so clicking an already placed object with the
  same selected tool removes that object for:
  - seats
  - floor fixtures such as teacher desk, tables, and benches
  - wall objects such as whiteboard, door, and window
- Keep occupancy/conflict guards authoritative so different-tool clicks on occupied targets do not
  remove or mutate the existing object.
- Add focused browser proof covering:
  - seating student drag preview shape
  - same-seat click-to-remove
  - same-fixture click-to-remove
  - same-wall-object click-to-remove
  - conflicting different-tool click leaves the original object intact

## Proposed module focus

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/roomSeatDragPreview.ts`
- `frontend/apps/skriptoteket/src/views/apps/useRoomTemplateEditorState.ts`
- `frontend/apps/skriptoteket/src/views/apps/roomTemplateEditorDomain.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/RoomTemplateBuilderSurface.vue`
- `scripts/playwright_seating_drag_preview_check.py`

## Test plan

- Focused frontend tests for room-editor same-tool removal behavior across seats, fixtures, and
  wall objects.
- Manual/browser verification on the live local SPA proving:
  - seating drags use the seat-token preview
  - same-tool repeat clicks remove the matching placed object
  - conflicting different-tool clicks preserve the existing object

## Rollback plan

- Restore the current seating drag preview and the current room-editor removal behavior while
  keeping the broader room-editor modularization and split-pane layout work intact.

## References

- Story parent: [ST-24-04](../stories/story-24-04-group-seating-studio-seating-fundamentals-and-saved-arrangements.md)
- Room-editor modularization baseline: [PR-0116](pr-0116-klassrumskartan-room-template-editor-modularization-and-shared-room-scene.md)
- Student-pool seating workspace baseline: [PR-0128](pr-0128-klassrumskartan-grouping-and-seating-student-pool-split-pane-scrolling.md)
- Frontend skill: [integrated-frontend-stack](/Users/olofs_mba/Documents/Repos/skill-repository/skills/integrated-frontend-stack/SKILL.md)
- Browser automation skill: [playwright-testing](../../..//Users/olofs_mba/.codex/skills/playwright-testing/SKILL.md)
- Design-system rule: [045-huleedu-design-system](../../../.codex/rules/045-huleedu-design-system.md)
- Browser automation rule: [075-browser-automation](../../../.codex/rules/075-browser-automation.md)
