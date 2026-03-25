---
type: story
id: ST-23-04
title: "Klassrumskartan — Seat Assignment Canvas"
status: done
owners: "agents"
created: 2026-03-20
updated: 2026-03-25
epic: "EPIC-23"
acceptance_criteria:
  - "Given a student is assigned to Seat 1, when the student is dragged to Seat 2, then Seat 1 becomes empty and the student occupies Seat 2."
  - "Given Seat 2 is occupied, when another student is dropped onto Seat 2, then the student explicitly swaps seats with the previous occupant."
  - "Given a student changes seats, when the move completes, then the group assignment remains unchanged."
---

## Context
The Seat Assignment axis. Operates entirely independently of Group assignments.

## Implementation Plan

### [ ] PR 1: Seat Collision & Grid View
- **Intent**: Map a physical room and allow drag-and-drop of individual seats.
- **Code Choice**: Build `RoomCanvas.vue`. Intercept `vue-draggable-plus` drops to trigger a `swapSeatAssignments(studentId, targetSeatId)` state reducer. Use normalized `seatAssignmentsByStudentId` mapped to `seatsById`.

## Implementation Summary (as of 2026-03-25)

- The seating canvas shipped as a distinct seat-assignment surface with teacher-visible room geometry rather than a grouped-list derivative.
- Seat moves and swaps remain independent from grouping state, preserving the two-axis planner model established in Slice 1.
- Later seating ergonomics, history, and export work build on this shipped canvas rather than replacing it with a different contract.
