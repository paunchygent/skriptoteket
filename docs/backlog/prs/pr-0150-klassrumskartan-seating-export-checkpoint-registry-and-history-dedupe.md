---
type: pr
id: PR-0150
title: "Klassrumskartan: seating export checkpoint registry and history dedupe"
status: ready
owners: "agents"
created: 2026-03-27
updated: 2026-03-27
stories:
  - "ST-27-02"
tags: ["backend", "persistence", "exports", "history", "migrations", "klassrumskartan", "smart-assignment"]
dependencies:
  - "ADR-0074"
  - "EPIC-27"
  - "PR-0146"
  - "PR-0151"
acceptance_criteria:
  - "Given a seating export completes successfully, when the exported seating state differs from the last eligible checkpoint for the same roster and room/template context, then one new seating checkpoint is recorded for smart-history use."
  - "Given a teacher repeats a seating export without changing the normalized seating state, when the export succeeds again, then no duplicate checkpoint is created."
  - "Given the system computes the seating assignment hash, when students are seated or left unplaced, then the hash includes normalized placed assignments plus normalized unplaced students and excludes export presentation/layout details."
  - "Given draft autosave, undo/redo, or abandoned draft mechanics occur without a successful seating export, when history eligibility is evaluated, then those states are not recorded as seating checkpoints."
  - "Given teacher-distance fairness later depends on room context, when checkpoint dedupe is evaluated, then the checkpoint identity includes room/template context rather than merging states from meaningfully different rooms."
  - "Given roster-global smart rules already exist for the same class, when checkpoints are stored, then those checkpoints remain separate history artifacts and do not own, duplicate, or redefine the smart-rule set."
---

## Problem

The smart-assignment docs now say that history must come from explicit export-backed checkpoints,
not from autosave, undo/redo, or abandoned draft state. They also now say that smart rules are
roster-global and separate from draft-local arrangement state.

The current codebase has seating export delivery, but no dedicated checkpoint registry or
normalized assignment-hash dedupe layer that can serve as an honest smart-history source once that
ownership boundary is corrected.

Without that layer, the next smart-seating behavior slices would have to either:

- consume draft mechanics that the docs already reject as history, or
- ship teacher-distance fairness as aspirational behavior with no approved data source.

## Goal

Create the first seating checkpoint/history foundation so later smart-seating slices can consume
teacher-approved export history honestly:

- one eligible checkpoint per successful seating export state
- normalized seating assignment hashing
- dedupe of unchanged exported seating states
- export-backed checkpoints as the only valid seating smart-history source
- a persistence shape that stays separate from roster-global smart-rule ownership

## Non-goals

- Implementing backend smart seating solver behavior.
- Replacing `Smart + Slumpa` with a backend smart-seating run path.
- Shipping new major teacher-facing checkpoint UI.
- Consuming checkpoints for teacher-distance fairness in this PR.
- Creating grouping checkpoints.
- Adding explanation/debug surfaces beyond minimal eligibility semantics.
- Moving smart-rule ownership from draft scope to roster scope; that boundary reset is `PR-0151`.

## Implementation plan

1. Lock checkpoint semantics in tests first.
   - Add unit coverage for normalized seating assignment hashing.
   - Prove that seated assignments plus unplaced students affect the hash.
   - Prove that export presentation/layout details do not affect the hash.

2. Lock lifecycle behavior in application tests.
   - Successful seating export completion creates one eligible checkpoint.
   - Repeated identical seating export completion does not create a duplicate checkpoint.
   - Autosave/undo/redo/abandon flows do not create checkpoints.

3. Introduce the checkpoint domain/persistence boundary.
   - Add a seating checkpoint model/value shape that stores:
     - roster identity
     - optional source-draft provenance only if needed for audit/debug
     - template/room context
     - normalized seating snapshot
     - assignment hash
     - created/export timestamps
   - Add protocol and repository support for recording/fetching checkpoints.
   - Keep checkpoint persistence separate from roster-global smart-rule persistence.

4. Add persistence + migration support.
   - Add an ORM model and Alembic revision for seating checkpoints.
   - Add schema assertions and migration idempotency coverage.
   - Keep the initial retention posture simple and append-only unless a repo-wide retention rule
     forces something stricter.

5. Wire checkpoint creation to successful seating export completion only.
   - Hook checkpoint recording into the export-success path, not export request acceptance.
   - Keep the export path idempotent with respect to unchanged seating state.

## PR-sized execution checklist

- [ ] Add/update unit tests for normalized seating assignment hashing
- [ ] Add/update application tests for export-success checkpoint creation and dedupe
- [ ] Add checkpoint domain/protocol/repository layers
- [ ] Add ORM model + Alembic revision
- [ ] Add migration schema assertion coverage
- [ ] Wire seating export completion to checkpoint recording
- [ ] Run verification and record it in `.agents/handoff.md`

## Test plan

- `pdm run pytest tests/unit/application/apps/classroom_planner/ -q`
- `pdm run pytest tests/unit/infrastructure/repositories/ -q`
- `pdm run pytest tests/integration/migration_schema_assertions.py -q`
- `pdm run pytest -m docker 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[<new_revision_id>]' -q`
- `pdm run docs-validate`

## Rollback plan

- Revert the checkpoint model/repository/migration/export hook together if the checkpoint shape is
  found to be incorrect.
- Do not fall back to draft autosave/undo/redo as a shortcut history source.
- Preserve the docs/backlog decision trail so later smart-seating work still starts from the
  export-backed history rule.
