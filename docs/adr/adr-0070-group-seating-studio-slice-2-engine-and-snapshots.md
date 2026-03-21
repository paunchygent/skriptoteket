---
type: adr
id: ADR-0070
title: "Klassrumskartan Slice 2 Engine, Constraints, and Snapshot Contract"
status: accepted
owners: "agents"
deciders: ["architect"]
created: 2026-03-20
links: ["ADR-0069", "EPIC-23", "EPIC-24", "REV-EPIC-24"]
---

## Context

Slice 1 established Klassrumskartan as a manual planner with reusable rosters and room templates, draft persistence, and synchronized group/seat views. Slice 2 adds teacher-only planning metadata, rule toggles, randomization, explainable suggestion generation, authoritative validation, and immutable snapshot finalization.

We need one contract that keeps the backend as the rule authority, preserves draft-scoped planning inputs separately from roster identity, and keeps future export stories aligned with the same room/fixture model.

## Decision

### 1. Draft-scoped typed planning inputs

We store planning inputs as dedicated draft-scoped concepts, not on roster cards:

- `DraftGroup`
- `StudentPlanningMeta`
- `PairConstraint`
- `PlanningProfile`

These are persisted through dedicated planner tables and hydrated as one workspace contract via `GET /drafts/{draft_id}/workspace`.

### 2. Rule engine authority stays on the backend

The authoritative planner engine runs server-side in Python. The SPA may offer cheap local hints for drag/drop ergonomics, but it must not duplicate the full scoring or validation logic.

Authoritative endpoints:

- `POST /drafts/{draft_id}/validate`
- `POST /drafts/{draft_id}/suggestions`
- `POST /drafts/{draft_id}/suggestions/{suggestion_id}/apply`
- `POST /drafts/{draft_id}/randomize`
- `POST /drafts/{draft_id}/finalize`

### 3. Randomization is a first-class planning action

Teachers may start from a pure random layout via the explicit `randomize` action (`Slumpa`). This action assigns all currently loaded students to groups and seats without applying the weighted solver profile. It exists alongside, not inside, the explainable profile suggestions.

### 4. Rule toggles live in `PlanningProfile`

Future placement rules are modeled as explicit toggles and weights on `PlanningProfile`, including:

- `enable_student_meta`
- `enable_pair_constraints`
- `enable_zone_preferences`
- `enable_history_rules`

This keeps future rule expansion additive and auditable while allowing teachers to switch individual rule families off.

### 5. Room templates include visual fixtures

Reusable room templates include fixture geometry for:

- `whiteboard`
- `teacher_desk`
- `window`
- `door`

These fixtures are part of the room template source of truth so the planner canvas and later PDF/XLSX export stories share the same classroom scene model.

### 6. Finalization creates immutable deep-copy snapshots

Finalization is a transactional backend use case. `ArrangementSnapshot` stores a deep-copied payload containing:

- draft root metadata
- roster snapshot content
- room template snapshot content including fixtures
- groups
- group assignments
- seat assignments
- student planning metadata
- pair constraints
- planning profile
- engine metadata
- validation findings at finalize time

Snapshots are read through `GET /snapshots` and `GET /snapshots/{snapshot_id}` and do not rely on mutable roster/template records as their historical source of truth.

## Consequences

### Benefits

- Clear backend authority for explainable planning behavior.
- Teacher-only metadata stays out of draggable presentation models.
- Random placement and weighted planning can coexist without contract ambiguity.
- Room layout fidelity now supports later export epics without inventing a second geometry model.

### Tradeoffs / Risks

- Larger planner API surface and more draft-scoped persistence than Slice 1.
- Snapshot payloads duplicate roster/template content by design.
- Additional frontend coordination is required to keep responsive workspace UI and autosave conflict handling understandable.
