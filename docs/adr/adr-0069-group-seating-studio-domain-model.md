---
type: adr
id: ADR-0069
title: "Klassrumskartan Domain Model and Data Persistence"
status: accepted
owners: "agents"
deciders: ["architect"]
created: 2026-03-20
links: ["PRD-group-seating-studio-v0.1", "ADR-0023", "EPIC-23"]
---

## Context
The "Klassrumskartan" (Group Seating Studio) app requires a complex planning model that typical scripts lack. We need a domain model that separates *drafting* from *final records*, and decouples *seating* from *grouping*. The data requires explicit invariants and relational boundaries.

## Decision

We will introduce a distinct bounded context `classroom_planner` under `src/skriptoteket/domain/apps/classroom_planner/` implementing the following structural rules:

### 1. App-Specific Relational Persistence
**Decision**: We will NOT use the generic `tool_sessions` approach for primary persistence.
We will create **app-specific relational tables** for the following core entities:
- `Roster`
- `RoomTemplate` (Seat geometry, zones)
- `PlanDraft` (Mutable autosaved workspace)
- `ArrangementSnapshot` (Immutable final state)
- `GroupAssignment` (Scoped to a specific `PlanDraft` or `ArrangementSnapshot`)
- `SeatAssignment` (Scoped to a specific `PlanDraft` or `ArrangementSnapshot`)

Reusable assets (Rosters, RoomTemplates) will utilize proper backend CRUD. Lesson Modes are bootstrapped catalog presets, not CRUD entities.

### 2. Normalized Immutable Data Representation
**Decision**: The state model will manage assignments through explicit relational mapping keyed by `student_id`, never display names.
- A student has **at most one** group assignment **within a draft/snapshot context**.
- A student has **at most one** seat assignment **within a draft/snapshot context**.
- A seat has **at most one** student **within a draft/snapshot context**.

### 3. Decouple Groups from Seats
**Decision**: `GroupAssignment` and `SeatAssignment` are distinct assignment models. Dragging in the UI targets one explicit assignment axis at a time. The room view and group view are just two projections of the same normalized draft state.

### 4. Separate View Models
**Decision**:
- `StudentCardViewModel`: Contains only `student_id`, `display_name`, and optional visual UI fields.
- `StudentPlanningMeta`: Contains teacher-only planning factors, relationship rules, and notes. This is strict metadata and is NEVER passed directly into the draggable card presentation components.

### 5. Snapshot Independence
**Decision**: Because snapshots must be immutable for historical accuracy, a finalized `ArrangementSnapshot` will store a deep copy of the `Roster` and `RoomTemplate` content used at finalization. It does not rely on foreign keys to mutable templates that could change later.

### 6. Defer Solver Decisions
**Decision**: Slice 1 supports manual drafting only. Generative suggestion strategies are deferred to a later ADR.

## Consequences

### Benefits
- First-class support for history-aware scheduling (e.g. "Do not sit X next to Y").
- Eliminates "ghost entries" and drag/drop duplication errors by strictly normalizing UI state across axes.
- Clean backend schemas for auditing and reuse without shoehorning into `tool_sessions`.

### Tradeoffs / Risks
- Significant initial domain complexity compared to simple "tool inputs/outputs".
- Increased initial API surface (requires full CRUD logic explicitly built out for these endpoints).
