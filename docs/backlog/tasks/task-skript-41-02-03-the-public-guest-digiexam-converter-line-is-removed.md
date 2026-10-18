---
type: task
id: TASK-SKRIPT-41-02-03
title: The public guest DigiExam converter line is removed
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-18'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- The public guest DigiExam jobs table, routes, worker, artifacts, planner, PDF builder, QTI adapter and view are removed with no remaining reference
- DigiExam parsing is reached only through the workspace import
- TASK-SKRIPT-21-10-01 and ST-SKRIPT-21-10 are closed as superseded
story: ST-SKRIPT-41-02
backlog_document_profile: contract-derived
---

## Implementation Contract

Remove the public guest DigiExam line under ST-SKRIPT-41-02 P6 once the guest URL opens the public workspace (TASK-SKRIPT-41-02-02). Removal rule: a module, route, table or file goes when only the guest line uses it and nothing else imports or calls it; `parse_source_exam`/`DigiExamDxeParser` stay for the workspace import. Generic Conversion Hub `.dxe` intake (`apps_conversion_hub.py`) goes too if no caller uses it.

## Contract Inputs

- ST-SKRIPT-41-02 P6; ADR-SKRIPT-0085; User grilling 2026-10-18 in the Mac orchestration session (retained root 01a14ee0-903e-7423-b969-30e3661e9006); explorer maps of the DigiExam lines and paid AI call sites the same day.
- Guest-only modules: `public_exam_converter_jobs.py`, `public_exam_converter_local_execution.py`, `public_exam_converter_artifacts.py`, `exam_conversion_review_artifacts.py`, `digiexam_answer_key_completion.py`, `digiexam_examnet_qti_adapter.py`, `digiexam_examnet_pdf.py`, `workers/public_exam_converter.py`, table `public_exam_converter_jobs`, `ExamConverterPublicView.vue` and `views/apps/exam-converter-public/`.

## Core Vertical And Performance

The vertical is deletion plus one migration dropping `public_exam_converter_jobs`; the workspace DigiExam import keeps the parser. No performance concern.

## Validation

- The domain suites for curated apps and web pass; no import or route refers to removed code; migration test.
- Docs: ADR-SKRIPT-0085 marked superseded by EPIC-SKRIPT-41; the three docs of P6 closed; `pdm run docs-validate`.

## Stop Conditions

Stop and report if a removed module turns out to serve another caller, or if the generic hub `.dxe` intake has a live caller.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| X1  | ST-SKRIPT-41-02 P6 applies as written; no compatibility path or redirect for the old guest job routes. |
