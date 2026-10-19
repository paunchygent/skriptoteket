---
type: story
id: ST-SKRIPT-06-18
title: The SPA Vitest wrapper runs exactly the spec files its targets name
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-19'
status: proposed
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-06
acceptance_criteria:
- Every vitest-run path target contributes all its spec files; a target that matches
  no spec file exits non-zero; a run without targets discovers all of src/**/*.spec.ts.
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

`frontend/apps/skriptoteket/scripts/vitest-run.mjs` is the only entry for the SPA package test scripts (`test`, `test:watch`, `test:coverage`, `test:ui`) and for `pdm run fe-test`. It holds this contract:

- Every path target (spec file, folder or glob; app-local, repo-root or absolute) contributes all of its spec files to the run.
- A target that matches no spec file stops the run with a non-zero exit before Vitest starts, in run, watch and coverage mode.
- A run without targets leaves `vitest.config.ts` in charge, which discovers all of `src/**/*.spec.ts`.

## Contract Inputs

- Commits `900db302` and `5e7c646b` (merged to main in `bf79abce`, 2026-10-19, without review) introduced the include-target approach.
- Independent review ecea35b6 (2026-10-19, changes_requested), retained in session root `01a15524-776a-7857-8a94-c2c3e11dce51`.

## Tasks

- TASK-SKRIPT-06-18-01: repair target resolution (F1), separator handling (F2) and the include transport type (F3).

## Verification

Real-collection matrix (`vitest list --filesOnly` counts and small runs) before and after the repair, plus default discovery equal to the full `src/**/*.spec.ts` set. No full frontend suite.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| S1  | The three contract bullets above are the wrapper's acceptance; the task's decided terms D1-D7 implement them. |
