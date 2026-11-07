---
type: task
id: TASK-SKRIPT-REP-0067
title: Skriptoteket typechecks with pyrefly and retires mypy
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
  - '`pdm run typecheck` runs pyrefly and passes.'
  - mypy and `[tool.mypy]` are removed.
  - '`pdm run check` passes.'
backlog_document_profile: contract-derived
---

## Implementation Contract

TASK-SKRIPT-REP-0066 adopts the shared `[tool.pyrefly]` table and pin while
mypy with the `pydantic.mypy` plugin stays the type checker. Pyrefly supports
Pydantic v2 natively (BaseModel, Field, ConfigDict, BaseSettings, Pydantic
dataclasses; https://pyrefly.org/en/docs/migrate/mypy/plugins). This task runs
pyrefly over the configured includes, fixes its diagnostics, verifies aliases,
validators, settings models and nested containers, moves the
`backend-typecheck` producer to pyrefly, and removes mypy, its config and the
plugin.

## Contract Inputs

- User decision, 7 Nov 2026 (TASK-SKRIPT-REP-0066 round 3).

## Core Vertical And Performance

No product code changes beyond what pyrefly diagnostics require; no intended
behavior change.

## Validation

- `pdm run typecheck`, then `pdm run check`.

## Stop Conditions

- A pyrefly diagnostic needs a product-behavior change, or a pyrefly
  limitation blocks the migration: bring it to the user.

## Decided Contract Terms

| ID  | Decided contract term                                                                            |
| --- | ------------------------------------------------------------------------------------------------ |
| D1  | Pyrefly replaces mypy in a task of its own after the shared block is adopted (user, 7 Nov 2026). |
