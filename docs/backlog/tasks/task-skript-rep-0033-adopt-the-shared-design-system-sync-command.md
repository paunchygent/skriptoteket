---
type: task
id: TASK-SKRIPT-REP-0033
title: Adopt the shared design-system sync command
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-09-23'
status: canceled
dependencies:
- TASK-SKILL-REP-0171
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- Running repository-governance-frontend-catalog design-system sync against Skriptoteket
  copies the pinned huleedu-integrated package into the paths named in design-system-map.json
  (the tokens export into src/skriptoteket/web/static/css/huleedu-design-tokens.css,
  unused exports listed as not adopted), and Skriptoteket's named design-system validate
  command passes; Skriptoteket docs name the sync command instead of hand copying.
backlog_document_profile: contract-derived
---

## Implementation Contract

Canceled on 2026-09-27. The work continues as TASK-SKRIPT-40-01-01 under
ST-SKRIPT-40-01, because a story task needs the story-scoped identifier.

## Contract Inputs

- Retained plan `.orchestration/context/sessions/01a0e42e-f433-727d-a17f-f9eced6d04bc/evidence/planning/TASK-SKRIPT-REP-0033/plan.md`.

## Core Vertical And Performance

See TASK-SKRIPT-40-01-01.

## Validation

See TASK-SKRIPT-40-01-01.

## Stop Conditions

See TASK-SKRIPT-40-01-01.

## Decided Contract Terms

| ID  | Decided contract term                                     |
| --- | --------------------------------------------------------- |
| D1  | This task is canceled and continues as TASK-SKRIPT-40-01-01. |
