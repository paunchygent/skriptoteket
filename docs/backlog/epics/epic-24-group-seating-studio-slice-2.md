---
type: epic
id: EPIC-24
title: "Curated app: Klassrumskartan (Slice 2)"
status: active
owners: "agents"
created: 2026-03-20
updated: 2026-03-20
outcome: "Teachers can reopen a draft-scoped classroom planning workspace, manage group structure and planning metadata, randomize or generate explainable placement suggestions, validate hard/soft findings, and finalize immutable snapshots from a richer classroom canvas."
dependencies: ["ADR-0069", "ADR-0070", "EPIC-23"]
---

## Scope

- Add a hydrated draft workspace contract and same-session resume flow.
- Persist draft-scoped `DraftGroup`, `StudentPlanningMeta`, `PairConstraint`, and `PlanningProfile`.
- Add classroom fixtures (`whiteboard`, `teacher_desk`, `window`, `door`) to reusable room templates.
- Add teacher-facing CRUD for editing and deleting both class lists and classroom templates.
- Add authoritative backend validation, suggestion generation, randomization (`Slumpa`), suggestion apply, and snapshot finalization.
- Add responsive planner UI with breakpoint-aligned metadata drawer, planning-rule toggles, improved whiteboard-style drag/drop surfaces, and snapshot history read.

## Out of scope

- Duplicate snapshot back into a new draft.
- Cross-browser draft history beyond same-session resume.
- PDF/XLSX export generation itself (planned later, but this epic prepares the data model and visuals).

## Planned story set

1. EPIC-23 closure: draft group lifecycle, workspace hydrate, and doc/code alignment.
2. EPIC-23 closure: `StudentPlanningMeta` foundation and teacher-only metadata drawer.
3. Slice 2: constraint persistence plus authoritative validate endpoint.
4. Slice 2: explainable suggestion engine plus suggestion apply flow.
5. Slice 2: random group/seat assignment (`Slumpa`) with future rule-toggle path.
6. Slice 2: room-template fixtures, improved classroom whiteboard visuals, and responsive breakpoint polish.
7. Slice 2: edit/delete UI for reusable classes and classrooms.
8. Slice 2: snapshot finalization plus snapshot list/read history.

## Implementation Summary (as of 2026-03-20)

- Added draft workspace hydration, draft groups, teacher-only student metadata, pair constraints, planning profiles, suggestion metadata, and arrangement snapshots to the backend contract.
- Added backend validation, suggestions, randomization, suggestion apply, finalize, and snapshot read endpoints under `/api/v1/apps/classroom.group-seating-studio/*`.
- Added room template fixtures and richer planner frontend surfaces for randomization, rule toggles, metadata editing, improved classroom visuals, and class/classroom management CRUD.
