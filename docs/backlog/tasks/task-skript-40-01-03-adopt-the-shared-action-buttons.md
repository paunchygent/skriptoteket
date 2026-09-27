---
type: task
id: TASK-SKRIPT-40-01-03
title: Adopt the shared action buttons
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-09-27'
status: ready
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

Map action-buttons to
`frontend/apps/skriptoteket/src/styles/action-buttons.css`, using the 01-01
clean-map checkpoint sequence. Import it once in `src/assets/main.css` after
tokens and theme; sync from the admitted clean release.

Remove every local rule for `.btn-cta`, `.btn-ghost`, `.btn-primary`,
`.btn-inline-edit`, `.btn-inline-primary` and `.btn-inline-cancel` from main.css,
including shared selector shells, media/hover rules and later overrides.
All six classes render from the package file. Update
`tests/actionButtonContract.spec.ts` to assert the adopted CSS declaration
contract, rather than transplanting assertions for old Tailwind source text.

Restore the automatic hook after the admitted map-preparation checkpoint.
Validate and parent-commit the coherent result before the unchanged repeat sync.

## Contract Inputs

- Retained plan `.orchestration/context/sessions/01a0e42e-f433-727d-a17f-f9eced6d04bc/evidence/planning/TASK-SKRIPT-REP-0033/plan.md`, D13/D16 and admitted D24.
- TASK-SKRIPT-40-01-02; 0186's released inline-button promotion.
- EPIC-SKRIPT-40 review R6 and its action-rule/test observation.

## Core Vertical And Performance

Every application .btn-* use renders from one imported shared stylesheet.
Removal includes duplicate shell and interaction rules so local CSS cannot
silently override the release. No material performance concern is identified.

## Validation

- Actual sync and validator pass; parent-committed protected paths are clean; repeat sync against the same clean source release exits 0 with no changes.
- `pdm run fe-type-check`, `pdm run fe-test`, `pdm run fe-build` and `pdm run design-system-validate` pass, including the updated action-button contract test.
- Confirm no .btn-* definitions remain in main.css and the adopted file is imported after tokens/theme.
- Hemma staging walk covers forms and inline edit rows using all six classes and their relevant enabled/disabled/hover/focus/pressed states, using HuleEdu browser-session helpers/preflight.

## Stop Conditions

- Stop if any used .btn-* variant lacks a released counterpart, if clean checkpoint authority is absent, or if local overrides remain necessary to restore an accepted package behavior.

## Decided Contract Terms

| ID | Decided contract term |
| --- | --- |
| D1 | Adopt action-buttons and remove all inline .btn-* rules from main.css. Source: retained D13. |
| D2 | Inline-edit, inline-primary and inline-cancel come from the package. Source: retained D13/D15. |
| D3 | Parent-owned clean-map/result/repeat checkpoints and restored hook enforcement apply. Source: retained D24; R6. |
