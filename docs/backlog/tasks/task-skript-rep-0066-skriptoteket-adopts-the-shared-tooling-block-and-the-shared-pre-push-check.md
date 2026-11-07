---
type: task
id: TASK-SKRIPT-REP-0066
title: Skriptoteket adopts the shared tooling block and the shared pre-push check
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
acceptance_criteria:
  - "`pdm run check` passes its bindings:complete phase: the reserved tooling dependency, tooling settings and pre-push hook markers each occur once and match the shared package."
  - "The shared pre-push hook (`check --pushed`) is installed, so a push to main runs the shared test selection."
  - "Each ruff, pyrefly and pytest setting that the shared block does not hold is either moved to a place the block offers or removed, by a user decision per setting."
backlog_document_profile: contract-derived
---

## Implementation Contract

Since TASK-SKRIPT-REP-0065 removed Skriptoteket's own pre-push check, the
repository has no pre-push test check: the shared pre-push block is part of
the bindings that `check` reports as drifted (bindings:complete fails on main
`9c67c78da` with tooling dependency drift, tooling settings drift in
`tool.ruff.exclude`, `tool.ruff.src`, `tool.ruff.lint.select`,
`tool.pyrefly.*` and `tool.pytest.ini_options`, and missing pre-push hook
markers). This task lists every differing setting, the user decides each, and
`repository-governance-bindings sync` then writes the shared block and the
pre-push hook.

## Contract Inputs

- TASK-SKRIPT-REP-0065 merge gate, 7 Nov 2026.
- User decision, 7 Nov 2026: consumer tooling adoption runs as its own task.

## Core Vertical And Performance

No product code changes.

## Validation

- `pdm run check` once after the sync.

## Stop Conditions

- A setting changes which tests run by default: bring it to the user before removal.

## Decided Contract Terms

| ID  | Decided contract term                                              |
| --- | ------------------------------------------------------------------ |
| D1  | Consumer tooling adoption runs as its own task (user, 7 Nov 2026). |
