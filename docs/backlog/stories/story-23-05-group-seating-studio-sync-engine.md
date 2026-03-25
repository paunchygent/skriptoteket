---
type: story
id: ST-23-05
title: "Klassrumskartan — Cross-View Synchronization and Invariants"
status: done
owners: "agents"
created: 2026-03-20
updated: 2026-03-25
epic: "EPIC-23"
acceptance_criteria:
  - "Given both boards are visible, when a single normalized draft assignment is dispatched, both views correctly reflect the update without duplicate rendering."
  - "Given aggressive drag actions, reactivity loops do not crash the browser because derived lists are cleanly rebuilt."
---

## Context
Finalizing the architecture to prevent `vue-draggable-plus` from destructively mutating arrays.

## Implementation Plan

### [ ] PR 1: Reducer Sync Engine
- **Intent**: Prevent duplicate entries, ghost items, and memory leaks by protecting array manipulation.
- **Code Choice**: Ensure the `GroupView` and `RoomView` do not own DOM state arrays. Action drops fire strict explicit reducers in Pinia `useClassroomState`:
  - `assignStudentToGroup(studentId, groupId)`
  - `removeStudentFromGroup(studentId)`
  - `assignStudentToSeat(studentId, seatId)`
  - `clearSeatAssignment(studentId)`
  - `swapSeatAssignments(seatIdA, seatIdB)`
- **Data Normalization**: Define `studentsById`, `groupsById`, `seatsById`, `groupAssignmentsByStudentId`, and `seatAssignmentsByStudentId` references.
- **Testing**: Write unit tests ensuring an assignment automatically untethers the previous state (e.g. assigning to a new seat unassigns the old seat without duplicating the student).

## Implementation Summary (as of 2026-03-25)

- The normalized reducer-based planner state shipped and remains the invariant-preserving seam behind both grouping and seating views.
- Group and seat surfaces rebuild from canonical draft state instead of letting drag/drop arrays become the source of truth.
- This shipped sync model is the foundation the later draft-history, continuity, and export stories continue to use.
