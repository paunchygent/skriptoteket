---
type: task
id: TASK-SKRIPT-REP-0033
title: Adopt the shared design-system sync command
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-09-23'
status: proposed
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

## Contract Inputs

## Core Vertical And Performance

## Validation

## Stop Conditions

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
