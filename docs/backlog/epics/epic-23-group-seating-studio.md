---
type: epic
id: EPIC-23
title: "Curated app: Klassrumskartan (Slice 1)"
status: active
owners: "agents"
created: 2026-03-20
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

- [ST-23-01: Registry, app route, bootstrap endpoint](../stories/story-23-01-group-seating-studio-skeleton.md)
- [ST-23-02: Roster and room template persistence + lesson mode selection](../stories/story-23-02-group-seating-studio-manual-planner.md)
- [ST-23-03: Group assignment board](../stories/story-23-03-group-seating-studio-drag-drop-canvas.md)
- [ST-23-04: Seat assignment canvas](../stories/story-23-04-group-seating-studio-seat-canvas.md)
- [ST-23-05: Cross-view synchronization and invariants](../stories/story-23-05-group-seating-studio-sync-engine.md)
- [ST-23-06: PlanDraft persistence and autosave](../stories/story-23-06-group-seating-studio-draft-persistence.md)
