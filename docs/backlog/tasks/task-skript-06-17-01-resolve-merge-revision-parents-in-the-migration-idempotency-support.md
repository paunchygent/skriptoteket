---
type: task
id: TASK-SKRIPT-06-17-01
title: Resolve merge-revision parents in the migration idempotency support
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-15'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- pdm run test-sequential -m 'integration and docker' tests/integration/test_migration_revision_coverage_idempotent.py
  passes with 0 failures; the merge case is covered by an explicit test; found on
  2026-10-15 during ST-SKRIPT-08-36 review repair F1 (pre-existing on main 8f2907a3).
story: ST-SKRIPT-06-17
backlog_document_profile: contract-derived
---

## Implementation Contract

## Contract Inputs

## Core Vertical And Performance

## Validation

## Stop Conditions

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
