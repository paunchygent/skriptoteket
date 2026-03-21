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
- [x] [ST-23-06: PlanDraft persistence and autosave](../stories/story-23-06-group-seating-studio-draft-persistence.md)
- [x] [ST-23-07: Management Modals (Rosters & Rooms)](../stories/story-23-07-group-seating-studio-management-modals.md)

## Implementation Summary (as of 2026-03-20)

- **ST-23-01**: The curated app route and bespoke bootstrap contract ship through `classroom.group-seating-studio`, with bootstrap-defined lesson modes and feature flags owned by the backend.
- **ST-23-02**: Reusable roster and room-template CRUD now use dedicated relational persistence, and room templates carry classroom fixtures (`whiteboard`, `teacher_desk`, `window`, `door`) as part of the canonical layout model.
- **ST-23-03 / ST-23-04 / ST-23-05**: The manual planner remains centered on decoupled group and seat views, but the frontend has been upgraded to a richer whiteboard-style classroom scene with responsive layout, improved drag/drop affordances, and stable group lifecycle operations.
- **ST-23-06**: Draft persistence moved from a minimal Slice 1 autosave contract to a hydrated workspace model with draft-scoped groups, optimistic revision handling, same-session resume, conflict reload UX, and authoritative backend patch validation.
- **ST-23-07**: Management modals now cover create, edit, and delete for both class lists and classroom templates, so teachers can maintain reusable assets without leaving Klassrumskartan.
