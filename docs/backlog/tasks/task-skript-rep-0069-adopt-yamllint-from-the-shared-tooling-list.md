---
type: task
id: TASK-SKRIPT-REP-0069
title: Adopt yamllint from the shared tooling list
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-11-09'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - '`pdm run yamllint --version` reports 1.38.0.'
  - '`repository-governance-bindings check` reports no drift.'
backlog_document_profile: contract-derived
---

## Implementation Contract

The routine lint phase runs `pdm run yamllint` on changed YAML and this
repository had none.

## Contract Inputs

## Core Vertical And Performance

## Validation

## Stop Conditions

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
