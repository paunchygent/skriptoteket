---
type: task
id: TASK-SKRIPT-REP-0068
title: Skriptoteket tests run without the log_level override
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-11-07'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: repository
dependencies:
  - TASK-SKRIPT-REP-0066
acceptance_criteria:
  - The full default suite passes with no `--log-level=INFO` in the `backend-test` producer arguments.
  - '`pdm run check` passes.'
backlog_document_profile: contract-derived
---

## Implementation Contract

TASK-SKRIPT-REP-0066 moved `--log-level=INFO` from pytest's `log_level`
setting into the `backend-test` producer arguments, because the shared pytest
block has no place for it. pytest's `log_level` is unset by default, so
capture follows the root logger's level, WARNING by default. This task gives
each test that asserts on INFO records `caplog.set_level(logging.INFO)`, then
removes `--log-level=INFO` from the producer arguments. The work is mechanical
and runs as cheap junior or refactoring-specialist units.

## Contract Inputs

- User decision, 7 Nov 2026 (TASK-SKRIPT-REP-0066 round 1 and 2).

## Core Vertical And Performance

No product code changes.

## Validation

- `pdm run test` (the full default suite), then `pdm run check`.

## Stop Conditions

None.

## Decided Contract Terms

| ID  | Decided contract term                                                       |
| --- | --------------------------------------------------------------------------- |
| D1  | The log_level drift is removed by a mechanical refactor (user, 7 Nov 2026). |
