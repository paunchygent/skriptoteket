---
type: review
id: REV-EPIC-24
title: "Review: Klassrumskartan Slice 2 Planning"
status: approved
owners: "agents"
created: 2026-03-20
updated: 2026-03-20
reviewer: "external-architect"
epic: EPIC-24
adrs:
  - ADR-0069
  - ADR-0070
stories: []
---

## TL;DR

Slice 2 should build on the approved Slice 1 review record in `REV-EPIC-23` and move Klassrumskartan toward a backend-authoritative planning engine. The implementation direction is approved: typed draft-scoped constraints, explicit validate/suggest/randomize/finalize endpoints, immutable deep-copy snapshots, richer room fixtures, and responsive teacher-first planner UI.

## Scope of this review

This document is intentionally forward-looking. Slice 1 retrospective findings and closure context live in:

- [REV-EPIC-23](review-epic-23-group-seating-studio.md)
- [review-epic-23-vertical-slice.md](review-epic-23-vertical-slice.md)

## Approved architectural guidance

### 1. Suggestion engine location

Approved: authoritative rule evaluation lives server-side in Python.

- Domain layer owns pure scoring/evaluation logic.
- Application layer loads draft, roster, template, and constraint context.
- Web layer exposes bespoke planner endpoints only.
- Frontend renders results and applies chosen suggestions back into the draft.

### 2. Constraint model

Approved: draft-scoped typed constraint aggregate separated from roster identity and student card presentation.

- `StudentPlanningMeta`
- `PairConstraint`
- `PlanningProfile`

Dedicated persistence is preferred and now considered the canonical Slice 2 direction.

### 3. Validation UX

Approved: hybrid.

- Cheap immediate client hints for local drag/drop ergonomics.
- Authoritative backend `validate` pass for hard/soft findings.
- `finalize` must re-run the same authoritative validation before snapshot creation.

### 4. Snapshot finalization

Approved: transactional backend finalization that deep-copies the full arrangement context into immutable `ArrangementSnapshot` records.

Snapshots must include copied roster/template content, groups, assignments, constraints, planning profile, and engine metadata, rather than pointing at mutable assets as historical truth.

### 5. Random assignment and future rule toggles

Approved: an explicit `Slumpa` action may randomize all current students into groups and seats as a fast teacher starting point. Future sorting rules should remain explicit toggles on `PlanningProfile`, allowing each rule family to be switched on or off independently.

### 6. Responsive whiteboard UI

Approved: the planner should follow the existing HuleEdu brutalist academic design rules, use responsive breakpoint-aware composition, and render room fixtures that make later PDF/XLSX export stories visually credible.

## Requirements for EPIC-24

- Add workspace hydration and same-session draft restore.
- Persist draft groups instead of relying on `group_count`.
- Add teacher-only metadata editing surfaces.
- Add edit/delete flows for reusable classes and classrooms.
- Add fixtures for `whiteboard`, `teacher_desk`, `window`, and `door`.
- Add backend validation, suggestions, suggestion apply, randomize, finalize, and snapshot read endpoints.
- Keep optimistic concurrency and conflict reload UX intact as the planner surface expands.

## Decision approvals

- [x] Suggestion Engine Location
- [x] Constraint Model
- [x] Validation UX
- [x] Snapshot Finalization Contract
- [x] Randomizer + Future Rule Toggles
- [x] Responsive Whiteboard UI Direction
