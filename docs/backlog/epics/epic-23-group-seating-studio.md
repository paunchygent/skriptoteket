---
type: epic
id: EPIC-23
title: "Curated app: Klassrumskartan (Slice 1)"
status: active
owners: "agents"
created: 2026-03-20
updated: 2026-03-20
outcome: "Teachers can open the bespoke planner, load or create a roster and room template, choose a required lesson mode, and manually assign students to groups and seats through synchronized views backed by a single normalized draft state."
dependencies: ["ADR-0022", "ADR-0023", "ADR-0069"]
---

## Scope

- **Frontend**: Implement `classroom.group-seating-studio` Curated App and its bespoke SPA view (`views/apps/ClassroomPlannerView.vue`).
- **Backend**: Provide a dedicated API surface at `/api/v1/apps/classroom.group-seating-studio/*`.
  - `GET /bootstrap` initialization endpoint provisioning app-specific data (lesson modes, default geometries).
  - True Backend CRUD endpoints for reusable `Roster` and `RoomTemplate` models.
- **State**: Implement a normalized draft state using variables like `studentsById`, `groupAssignmentsByStudentId`, and `seatAssignmentsByStudentId`.
- **UI**: Decoupled drag-and-drop Views enforcing strict invariants via reducers. Slice 1 is strictly manual drafting (no automated suggestion engine).

## Out of scope

- Slice 2: Suggestion engine, Validation Panel, Immutable Finalization snapshots, Hard/Soft constraint engine.
- Slice 3: Export services (PDF/XLSX), History-aware scoring.

## Stories

- [x] [ST-23-01: Registry, app route, bootstrap endpoint](../stories/story-23-01-group-seating-studio-skeleton.md)
- [x] [ST-23-02: Roster and room template persistence + lesson mode selection](../stories/story-23-02-group-seating-studio-manual-planner.md)
- [x] [ST-23-03: Group assignment board](../stories/story-23-03-group-seating-studio-drag-drop-canvas.md)
- [x] [ST-23-04: Seat assignment canvas](../stories/story-23-04-group-seating-studio-seat-canvas.md)
- [x] [ST-23-05: Cross-view synchronization and invariants](../stories/story-23-05-group-seating-studio-sync-engine.md)
- [ ] [ST-23-06: PlanDraft persistence and autosave](../stories/story-23-06-group-seating-studio-draft-persistence.md)

## Implementation Summary (as of 2026-03-20)

- **ST-23-01**: Delivered the backend skeleton for the Classroom Planner (Klassrumskartan). This includes the `classroom.group-seating-studio` registration in the curated app registry, the `ClassroomPlannerBootstrapService` for provisioning lesson modes (Standard, Test, Group Work, Lab), and the `GET /api/v1/apps/classroom.group-seating-studio/bootstrap` API endpoint. Verified functionality with unit tests and live curl requests against a running dev server.
- **ST-23-02**: Implemented relational persistence for `Roster` and `RoomTemplate` models. This included SQLAlchemy models, a new migration (verified with an idempotency integration test using Testcontainers), repositories, application services, and full CRUD API endpoints.
- **ST-23-03**: Delivered the interactive Group Assignment Board. Implemented a normalized Pinia state in `useClassroomState.ts` with strict reducers. Created `GroupBoard.vue` and `GroupCard.vue` components using TailwindCSS and brutalist styling. Students can be dragged between the unassigned pool and groups, with all state changes handled via reducers. Verified with Vitest unit tests.
- **ST-23-04**: Delivered the Seat Assignment Canvas. Implemented `RoomCanvas.vue` and `SeatNode.vue` with absolute positioning based on `x`/`y` coordinates. Connected seat assignment logic (`assignStudentToSeat`, `clearSeatAssignment`, `swapSeatAssignments`) to drag-and-drop events. Added cross-view indicators showing seated status in the group board. Tested with Vitest.
- **ST-23-05**: Validated and marked complete. The normalized Pinia architecture and explicit reducers built during ST-23-03/04 fully satisfied the invariant requirements. Used native HTML5 drag-and-drop to completely bypass destructive array mutations, ensuring rock-solid cross-view synchronization.
