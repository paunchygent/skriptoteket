---
type: task
id: TASK-SKRIPT-REP-0062
title: skriptoteket.hule.education serves the shared theme-sample page at /theme-sample from huleedu-integrated 0.1.40
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-30'
status: proposed
closeout_review:
  record: inline
  status: not_started
dependencies:
  - TASK-SKILL-17-01-01
task_kind: repository
acceptance_criteria:
  - skriptoteket syncs huleedu-integrated 0.1.40 through the shared design-system sync and design-system-validate passes
  - GET /theme-sample returns the built theme-sample page and every other route behaves as before, shown by a focused route test
  - No existing page loads the theme head script, so every app screen stays light
  - The frontend typecheck and lint pass, and production is deployed through the approved route after the user approves it
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
