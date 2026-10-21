---
type: task
id: TASK-SKRIPT-40-04-25
title: The Import view shows a question's Word source lines once
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-21'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - In the exam workspace Import view, I provfilen for a Word import shows each source line of a question once; Fråga 2 of the poangvarning walk shows its heading, a) and b) lines once
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

Mac staging walk finding W4 (2026-10-22, at `e2f12bcc`, Mac `.artifacts/staging-walk-closure-ede1ea0d/walk-record.md`). The proof admin imported `poangvarning.docx` as document `b8ea2e5b…`. In the Import view, "I provfilen · Word" for Fråga 2 shows "Fråga 2 (4 p)", then the a) and b) lines, then the same a) and b) lines again. The converted Frågetext is right: it keeps "a) Ange ordklassen …" and "b) Motivera …" once each.

First establish where the doubling comes from, from the staging document's stored import record and the code that builds the source view: whether the source text stored for the question repeats lines (for example, the question's own anchors plus a shared or part chunk that also covers them), or whether the view renders the same lines twice. Then make the smallest fix so each source line shows once. If the Word file itself prints those lines twice, stop and report; that is not a defect.

Non-goals: the converted text, points, grouping prompts.

## Contract Inputs

- Staging document `b8ea2e5b…` on Skriptoteket staging (rootless docker, `skriptoteket-dev-db-1`), its import record.
- The Import view's source pane in `frontend/apps/skriptoteket/src/views/apps/exam-workspace/` and the backend that stores the question's source text.

## Core Vertical And Performance

A Word import whose question's source lines are covered twice shows each line once in "I provfilen". No performance change.

## Validation

- A fail-first focused test (backend or Vitest, wherever the doubling is) that shows the repeat before the fix and one copy after.
- The neighbouring tests, and lint/typecheck or fe-type-check/fe-lint for what is touched.

## Stop Conditions

Stop and report if the Word file itself repeats the lines, or if the fix needs a document format change.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                             |
| --- | --------------------------------------------------------------------------------------------------------------------------------- |
| R1  | Light route (user rule 2026-10-21): one junior unit with a focused fail-first test, admitted on that proof with no review rounds. |

## Progress

- Diagnosed on staging doc b8ea2e5b: stored retry_source chunks repeat body:0006/0007 and question_text doubles the a)/b) lines; the Import pane renders the stored text verbatim. Root cause is grouping's subpart_anchors repeats entering question_retry_source without dedupe. Added fail-first test test_repeated_subpart_anchors_keep_each_source_line_once; fixed question_retry_source to keep each own anchor once. Focused 39 passed, domain exam_workspace 2686 passed, handlers docx/retry/import 1500 passed, lint/typecheck/docs-validate clean.
