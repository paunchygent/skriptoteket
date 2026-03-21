---
type: adr
id: ADR-0069
title: "Klassrumskartan Domain Model and Data Persistence"
status: accepted
owners: "agents"
deciders: ["architect"]
created: 2026-03-20
updated: 2026-03-21
links: ["PRD-group-seating-studio-v0.3", "ADR-0023", "ADR-0071", "ADR-0072", "EPIC-23", "EPIC-24"]
---

## Context
The "Klassrumskartan" (Group Seating Studio) app requires a complex planning model that typical scripts lack. We need a domain model that separates *drafting* from *final records*, and decouples *seating* from *grouping*. The data requires explicit invariants and relational boundaries.

Later product-direction work in ADR-0071 and ADR-0072 refines the teacher-facing workflow into a
class-first model with separate grouping and seating draft kinds. That later workflow update does
not invalidate the normalized persistence principles in this ADR; it refines how the teacher uses
them.

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
**Decision**: `GroupAssignment` and `SeatAssignment` are distinct assignment models. Dragging in the
UI targets one explicit assignment axis at a time. Later workflow slices may expose those
assignments through separate grouping and seating draft kinds, but the underlying assignment axes
remain distinct and normalized.

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
