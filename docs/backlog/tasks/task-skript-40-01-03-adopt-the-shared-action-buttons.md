---
type: task
id: TASK-SKRIPT-40-01-03
title: Adopt the shared action buttons
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-09-27'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- action-buttons is adopted through sync, main.css carries no .btn-* rules, and every button class renders from the package file
- Frontend type check, unit tests, build and the shared `repository-governance-frontend-catalog design-system validate`, plus a Hemma staging walk of the screens the task touches, pass
dependencies:
- TASK-SKRIPT-40-01-02
story: ST-SKRIPT-40-01
backlog_document_profile: contract-derived
---

## Implementation Contract

Skriptoteket adopts the package `action-buttons` export and removes its inline
`.btn-*` rules from `frontend/apps/skriptoteket/src/assets/main.css`.

- Map `action-buttons` to a Skriptoteket CSS path imported by `main.css`
  after the tokens and theme, then run the sync.
- Remove the `.btn-cta`, `.btn-ghost`, `.btn-primary`, `.btn-inline-edit`,
  `.btn-inline-primary` and `.btn-inline-cancel` rules from `main.css`; the
  inline buttons come from the package after TASK-SKILL-REP-0186.
- Update `frontend/apps/skriptoteket/tests/actionButtonContract.spec.ts` to
  assert against the adopted file.

## Contract Inputs

- Retained plan `.orchestration/context/sessions/01a0e42e-f433-727d-a17f-f9eced6d04bc/evidence/planning/TASK-SKRIPT-REP-0033/plan.md` (D13).
- Dependency: TASK-SKRIPT-40-01-02.

## Core Vertical And Performance

Every `.btn-*` use renders from the adopted package file. No performance
concern.

## Validation

- A second sync changes no file; the validate command passes.
- Frontend type check, unit tests, build and the shared `repository-governance-frontend-catalog design-system validate`, plus a Hemma staging walk of the screens the task touches: forms and inline edit rows using each button class.

## Stop Conditions

- Stop if a Skriptoteket `.btn-*` variant has no package counterpart.

## Decided Contract Terms

| ID  | Decided contract term                                                                  |
| --- | -------------------------------------------------------------------------------------- |
| D1  | `action-buttons` is adopted; the inline `.btn-*` rules leave `main.css`.              |
| D2  | The inline-edit, inline-primary and inline-cancel buttons come from the package.       |
