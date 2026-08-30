---
type: task
id: TASK-SKRIPT-39-03-01
title: Cut over the authenticated Exam Converter to Skriptoteket-owned execution
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-08-30'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- An authenticated teacher completes the existing Exam Converter workflow through
  Skriptoteket-owned submission, jobs, review and correction state, and artifact delivery
  without an exam-conversion request reaching Sir Convert
story: ST-SKRIPT-39-03
backlog_document_profile: contract-derived
---

## Implementation Contract

Replace the authenticated SPA's Sir Convert submission, polling, review,
correction, replay, and artifact path with Skriptoteket-owned APIs and state.

- Preserve the existing authenticated inputs, teacher-review provenance,
  warnings, manual follow-ups, correction behavior, target-readiness decisions,
  and downloadable outputs.
- Use the implemented in-process conversion engine, execution-worker
  enrichment, Luna/GLM provider line, Postgres lease, local job ledger, and
  local artifact ownership.
- Machine-proposed keys remain proposals under the existing teacher-review
  contract.
- Keep the Sir lane available only until the local product path is confirmed
  live. Deletion belongs to `TASK-SKRIPT-39-03-03`.

## Contract Inputs

- `ST-SKRIPT-39-03` terms S1-S5.
- Local conversion and job surfaces from `ST-SKRIPT-39-01`.
- Worker enrichment, provider, lease, proposal, and failure behavior from
  `ST-SKRIPT-39-02`.
- The current authenticated SPA workflow is the product behavior to preserve.

## Core Vertical And Performance

An authenticated teacher enters through the HuleEdu browser-session ceremony,
submits a real `.dxe` through the SPA, follows the locally owned job, reviews or
corrects the result when required, and downloads the completed bundle without
an exam-conversion request reaching Sir Convert.

Remote provider work remains in the execution worker and does not turn the web
request into a provider-bound synchronous operation.

## Validation

- Focused backend and frontend checks cover local submission, asynchronous
  enrichment, polling, review/correction, and artifact download.
- A live authenticated conversion through the deployed Hemma product surface
  exercises the complete user workflow with a real `.dxe`.
- Repository-required lint, typecheck, focused tests, browser proof, docs
  validation, and `git diff --check` pass or are reported truthfully against a
  pre-existing baseline.

## Stop Conditions

- Stop rather than narrow or remove an existing authenticated capability to
  simplify cutover.
- Do not complete the task while a required authenticated exam-conversion
  operation still depends on Sir Convert.
- A material change to teacher-review, correction, readiness, or provider
  behavior returns to the parent authority.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| T1 | The task is a consumer and adapter cutover over the implemented local conversion and enrichment vertical. |
| T2 | Existing authenticated inputs, review/correction behavior, readiness decisions, warnings, follow-ups, and outputs are preserved. |
| T3 | The complete authenticated product path stops reaching Sir for exam conversion; Sir removal waits for Task 03. |
| T4 | Remote completion remains worker-owned and machine keys remain teacher-review proposals. |
