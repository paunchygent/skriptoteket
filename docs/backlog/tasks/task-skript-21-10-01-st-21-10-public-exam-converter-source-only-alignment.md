---
type: task
id: TASK-SKRIPT-21-10-01
title: ST-21-10 public Exam Converter source-only alignment
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: canceled
closeout_review:
  record: inline
  status: not_required
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: User confirmed 2026-10-20 the removal of the public guest DigiExam converter line (ST-SKRIPT-41-02 term P6, user grilling 2026-10-18, retained root 01a14ee0-903e-7423-b969-30e3661e9006); P6 closes TASK-SKRIPT-21-10-01 and ST-SKRIPT-21-10 as superseded by TASK-SKRIPT-41-02-03.
story: ST-SKRIPT-21-10
task_kind: story
acceptance_criteria:
  - Given the public one-time Exam Converter lane remains available, when the public upload surface renders, then it requires only the governed `.dxe` source file and shows no optional graded-result/supporting PDF upload or early target selection controls.
  - Given the public browser runtime submits a job, when Skriptoteket builds the public multipart request and backend job spec, then it sends no `graded_result_pdf`, no `targets_json`, and requests the currently supported target artifacts by default.
  - Given the public route and upstream-client contracts still expose historical graded-result or target-selection fields, when this slice lands, then the frontend, public API handlers, and focused backend tests are updated together so the public lane matches the authenticated source-only product contract.
dependencies:
  - ST-SKRIPT-21-03
  - ST-SKRIPT-21-10
  - REF-SKRIPT-GENERAL-current-product-lanes-and-sir-convert-boundary
backlog_document_profile: contract-derived
---

## Implementation Contract

Superseded by TASK-SKRIPT-41-02-03 (ST-SKRIPT-41-02 P6), user decision
2026-10-20. This task would have aligned the public one-time Exam Converter
lane with the source-only intake contract. TASK-SKRIPT-41-02-03 removes that
public guest DigiExam converter instead; the exam workspace, with DigiExam as
one import, replaces it, and the guest URL opens the public exam workspace.
No work under this task remains.

## Contract Inputs

- ST-SKRIPT-41-02 P6; TASK-SKRIPT-41-02-03; ADR-SKRIPT-0085 (superseded by EPIC-SKRIPT-41).
- The pre-migration legacy body of this task is retained at `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a15f53-3b1b-7dcd-8cae-f7e114f55406/evidence/legacy-profile-history/task-skript-21-10-01.pre-migration.md`.

## Core Vertical And Performance

None: the task closes without implementation.

## Validation

None: the task closes without implementation.

## Stop Conditions

None.

## Decided Contract Terms

| ID  | Decided contract term                                                                                     |
| --- | --------------------------------------------------------------------------------------------------------- |
| S1  | The task is canceled as superseded by TASK-SKRIPT-41-02-03; its public-lane alignment is not implemented. |
