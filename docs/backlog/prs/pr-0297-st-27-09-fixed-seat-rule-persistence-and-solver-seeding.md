---
type: pr
id: PR-0297
title: "ST-27-09: fixed-seat rule persistence and solver seeding"
status: ready
owners: "agents"
created: 2026-05-05
updated: 2026-05-05
stories:
  - "ST-27-09"
tags: ["backend", "domain", "smart-assignment", "solver", "klassrumskartan"]
dependencies:
  - "PR-0296"
acceptance_criteria:
  - "Given fixed-seat rules are persisted for a roster and room template, when the smart-rule API loads the current rule set, then it returns the fixed-seat rules without mixing them into near-teacher or relationship-rule semantics."
  - "Given a fixed-seat rule references a missing student, missing seat, wrong classroom template, duplicate student, or duplicate seat, when rules are saved or Smart seating runs, then validation fails with a teacher-safe error boundary and no partial draft assignment is persisted."
  - "Given fixed-seat rules exist and Smart seating runs, when the solver starts, then it seeds those student-to-seat placements as hard assignments before exact or greedy search chooses the remaining placements."
  - "Given a remaining candidate is scored, when fixed placements exist, then keep-near, keep-apart, teacher-distance, history, and rerun-diversity scoring all evaluate against the merged fixed + candidate mapping."
  - "Given fixed placements consume seats or students, when the roster has more students than remaining seats, then unplaced-student reporting still reflects only students that could not be assigned after honoring the fixed placements."
  - "Given a fixed-seat rule cannot be honored, when Smart seating is requested, then the handler returns a blocked or validation outcome and does not save a new draft revision."
---

## Problem

The current smart seating solver treats all visible rules as best-effort scoring inputs. `Fast
plats` is different: it binds one student to one physical seat and must be honored as a hard
invariant. A naive implementation that simply removes the student and seat from candidate pools
would make other rules blind to the fixed placement.

## Goal

Add a room-scoped fixed-seat rule model and wire it into smart seating as a score-aware seeded
mapping:

- persist fixed-seat rules as roster + classroom template + student + seat
- validate hard conflicts before persistence and before smart runs
- seed solver mappings with fixed placements
- run exact/greedy search only for remaining students and seats
- score every candidate against the merged fixed + candidate assignment
- fail the run without partial persistence when fixed placements are invalid or impossible

## Non-goals

- Frontend authoring UI for `Fast plats`; that belongs to `PR-0298`.
- Changing `Keep near`, `Keep apart`, or `Närmare läraren` from best-effort objectives into hard
  constraints.
- Building a generic constraint-solver framework.
- Applying fixed-seat rules to grouping.

## Implementation plan

1. Extend the domain smart-rule model with a dedicated fixed-seat rule shape.
   - Keep it separate from `StudentSeatingPreference` and `RelationshipRule`.
   - Preserve the roster-owned smart-rule revision model.
   - Scope each fixed placement to one classroom template.

2. Add persistence and API contract support.
   - Add migration coverage for fixed-seat rows or an equivalent normalized storage shape.
   - Update repository serialization/deserialization.
   - Update request/response DTOs with additive fields only.
   - Keep optimistic concurrency behavior unchanged.

3. Add validation.
   - Student must exist in the roster.
   - Template must match the active seating draft.
   - Seat must exist in the template.
   - One student may have at most one fixed seat per roster/template.
   - One seat may be reserved by at most one student per roster/template.
   - Fixed-seat rules must not be accepted for grouping-only runs.

4. Seed the smart seating solver.
   - Build a fixed mapping before `_solve_exact` or `_solve_greedy`.
   - Remove fixed students and fixed seats from remaining search inputs.
   - Score merged mappings so relation rules see fixed peers.
   - Ensure unplaced-student accounting still includes fixed assignments correctly.

5. Add focused tests.
   - Domain solver tests for seeded fixed placements with keep-near and keep-apart peers.
   - Validation tests for duplicate students/seats and missing room seats.
   - Application handler tests proving no draft revision is saved on hard fixed-placement failure.
   - Repository/API tests for additive contract round-trips.

## Test plan

- `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_solver.py`
- Add focused backend tests for the new fixed-seat validation and solver-seeding path.
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_smart_seating.py tests/unit/application/apps/classroom_planner/test_smart_rules.py`
- `pdm run pytest tests/unit/web/apps/classroom_planner/test_smart_rules_api.py tests/unit/infrastructure/repositories/test_classroom_planner_smart_rules.py`
- If a migration is added, run the repo migration/schema assertion gate required by
  `.codex/rules/054-alembic-migrations.md`.
- `pdm run lint`
- `pdm run typecheck`
- `pdm run docs-validate`

## Rollback plan

Before deployment, revert the additive model/API/migration and solver-seeding changes together. If
the migration has already reached a shared environment, add a forward migration that removes fixed
seat rows only after confirming no production rules depend on them.
