---
type: task
id: TASK-SKRIPT-06-17-01
title: Resolve merge-revision parents in the migration idempotency support
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-15'
status: canceled
closeout_review:
  record: inline
  status: not_required
  decided_at: '2026-10-20'
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: 'The user decided on 2026-10-20 (AskUserQuestion, Hemma orchestrator session) to close this task as superseded by TASK-SKRIPT-06-17-02 (on main 3d3f867a), whose U5 resolves merge parents in the migration idempotency support. The repository-governance contract has no superseded status for tasks, so the task is canceled with TASK-SKRIPT-06-17-02 named as its successor.'
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
