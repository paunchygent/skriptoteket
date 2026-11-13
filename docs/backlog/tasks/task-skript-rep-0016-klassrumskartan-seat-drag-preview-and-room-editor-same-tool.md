---
type: task
id: TASK-SKRIPT-REP-0016
title: 'Klassrumskartan: seat drag preview and room-editor same-tool toggle removal'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- When a teacher drags a student from the seating student list, the drag preview reads
  as a seating token rather than as a list-row rectangle.
- When the teacher has a room-editor tool selected and clicks an empty valid target,
  the matching seat, floor fixture, or wall object is placed.
- When the teacher clicks an already placed object again with the same tool still
  selected, that same-kind object is removed instead of requiring the eraser.
- When the teacher clicks a conflicting occupied target with a different tool selected,
  the existing object remains unchanged and is not removed as a side effect.
- A focused browser proof verifies the drag-preview polish and same-tool placement/removal
  behavior on the live local SPA.
---

## Context

### Context

### Source: Problem

The classroom planning surfaces already support the core mechanics, but two interaction details still
make the experience feel more prototype-like than product-like:

- dragging a student from the seating list still advertises the list-row shape instead of the seat
  token teachers are actually placing
- the classroom editor forces object removal through a separate eraser/clear path even when the
  teacher is clearly clicking the same already-placed object with the same tool

That leaves the seating workflow visually inconsistent and makes repeated room-editing actions feel
more laborious than the seat tool already proves they need to be.

### Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

### Story Contract Slice

### Source: Goal

Polish the seating and classroom-editing interactions so drag/drop previews and repeated same-tool
clicks behave like one coherent classroom-planning system.

### Contract Inputs

### Source: References

- Story parent: [ST-24-04](../stories/story-24-04-group-seating-studio-seating-fundamentals-and-saved-arrangements.md)
- Room-editor modularization baseline: [PR-0116](pr-0116-klassrumskartan-room-template-editor-modularization-and-shared-room-scene.md)
- Student-pool seating workspace baseline: [PR-0128](pr-0128-klassrumskartan-grouping-and-seating-student-pool-split-pane-scrolling.md)
- Frontend skill: `integrated-frontend-stack`
- Browser automation skill: `playwright-testing`
- Design-system rule: [045-huleedu-design-system](../../../.codex/rules/045-huleedu-design-system.md)
- Browser automation rule: [075-browser-automation](../../../.codex/rules/075-browser-automation.md)

### Plan

### Source: Implementation plan

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

### Implementation Steps

### Source: Proposed module focus

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/roomSeatDragPreview.ts`
- `frontend/apps/skriptoteket/src/views/apps/useRoomTemplateEditorState.ts`
- `frontend/apps/skriptoteket/src/views/apps/roomTemplateEditorDomain.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/RoomTemplateBuilderSurface.vue`
- `scripts/playwright_seating_drag_preview_check.py`

### Proof

### Source: Test plan

- Focused frontend tests for room-editor same-tool removal behavior across seats, fixtures, and
  wall objects.
- Manual/browser verification on the live local SPA proving:
  - seating drags use the seat-token preview
  - same-tool repeat clicks remove the matching placed object
  - conflicting different-tool clicks preserve the existing object

### Validation

Validation follows the focused test and verification material recorded above.

### Stop Conditions

### Source: Non-goals

- No redesign of the student pool or the planner shell layout.
- No change to saved room geometry or placement persistence contracts.
- No general conflict-resolution redesign beyond same-tool toggle-off behavior.
- No new room-object categories or editing tools.

### Source: Rollback plan

- Restore the current seating drag preview and the current room-editor removal behavior while
  keeping the broader room-editor modularization and split-pane layout work intact.

### Lessons Learned

No separate lessons learned were recorded in the source snapshot.

### Notes

No additional task-local notes were recorded in the source snapshot.

### Plan Document Review

No separate plan document review was recorded in the source snapshot.

### Implementation Review

### Source: Status note (2026-03-31)

`ST-24-04` is already closed, but this PR id is not called out in the story close-out or handoff.
Its status is intentionally left unchanged until someone confirms whether this slice shipped under a
different PR or should be marked superseded/dropped.

### Source: Locked design decisions

- Keep this as one PR slice: the seating drag-preview polish and the classroom-editor toggle-off
  behavior ship together.
- Match the drag image to the seating token visual language rather than the student-list row.
- Extend the existing seat-style toggle-off behavior to same-kind room objects instead of inventing
  separate per-tool removal rules.
- Preserve current conflict rules: different-tool placement attempts must not silently delete the
  existing occupant.
- Validate both behaviors with live browser proof on the local SPA.

## Impact And Escalation

The migrated source records no separate statement for this section.

## Decision And Assumption Ledger

The migrated source records no separate statement for this section.

## Plan

The migrated source records no separate statement for this section.

## Implementation Steps

The migrated source records no separate statement for this section.

## Proof

The migrated source records no separate statement for this section.

## Validation

The migrated source records no separate statement for this section.

## Stop Conditions

The migrated source records no separate statement for this section.

## Lessons Learned

The migrated source records no separate statement for this section.

## Notes

The migrated source records no separate statement for this section.

## Readiness

The migrated source records no separate statement for this section.

## Closeout

The migrated source records no separate statement for this section.
