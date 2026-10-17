---
type: task
id: TASK-SKRIPT-39-06-06
title: Store a suggested type on converted questions
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-17'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - A converted question whose labeler type (`retry_source.label_kind`) differs from its saved type carries a stored suggested type that the workspace API returns and that a type change to that suggestion consumes
story: ST-SKRIPT-39-06
backlog_document_profile: contract-derived
---

## Implementation Contract

When conversion reported that a question is of another type than the one it
was saved as, the question stores that suggested type, and "Gör om till
[type]" converts the question to it (story P15). No item stores a suggested
type today. The suggested type is the labeler's `retry_source.label_kind` when
it differs from the saved kind (P5): the labeler's first type, kept before a
type-conflict resend changed the pipeline's kind
(`native_exam_retry_records.py:123-132`). This task stores that suggested type
on the item. It is backend and API work; the "Gör om till
[type]" offer is built by ST-SKRIPT-40-04 (story P15, P18).

This task delivers:

- A stored suggested type on `NativeExamItem`: a `NativeExamItemKind`, present
  only when `retry_source.label_kind` differs from the saved kind (story P15,
  P5).
  The document format changes with it and keeps no reader for the old format
  (repository invariant: no compatibility path).
- Conversion sets it wherever it builds an item from DOCX source: the DOCX
  import pipeline and the per-question retry.
- The workspace API returns it with the item in the document.
- A change to the suggested type through the change-type command of
  TASK-SKRIPT-39-06-05 clears it.

Out of scope: the "Gör om till [type]" offer (ST-SKRIPT-40-04); asking the
model to rebuild a question as a chosen type (story P16).

## Contract Inputs

- Story ST-SKRIPT-39-06 terms P15, P16 and P18.
- `src/skriptoteket/domain/curated_apps/exam_workspace/native_exam_retry_records.py:115-132`
  (`NativeExamRetrySource.label_kind`) and `native_exam_retry_source.py`
  (where `label_kind` is filled from the pipeline's `label_kinds`).
- Labeling and conflicts: `src/skriptoteket/application/curated_apps/handlers/exam_workspace_docx_pipeline.py`
  (`label_kinds`, `kinds`, resend of conflicts),
  `exam_workspace_docx_build_admission.py` (`type_conflict`,
  `type_conflict_kept`) and `exam_workspace_docx_assembly.py`
  (`with_type_check_mark`).
- Per-question retry: `exam_workspace_docx_retry.py`.
- Item and document model: `native_exam_item.py`, `native_exam_document.py`
  (`native_exam_document_v4`).
- Change-type command: TASK-SKRIPT-39-06-05.

## Core Vertical And Performance

The agent imports a DOCX exam on Hemma staging in which conversion reported a
question as another type than the one it was saved as. The document read
through the API shows that question with its suggested type, and no
suggestion on the others. The agent changes the question to the suggested
type through the change-type command; the document now shows no suggestion
on it. The suggestion adds no request: it travels in the document.

## Validation

- Focused tests on real conversion records: a question whose
  `retry_source.label_kind` differs from its saved kind stores that kind as
  the suggestion; a question whose kinds agree stores none; a per-question retry sets it again from its conversion.
- Focused domain test: a change to the suggested type clears it.
- Exam.net proof on Hemma staging: the question changed to its suggested type,
  exported and imported through the teacher's browser as that type, with
  screenshots retained in the retained root's `evidence/`.

## Stop Conditions

- TASK-SKRIPT-39-06-05 has not landed: this task waits for its command.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                 |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P1  | When conversion reports that a question is of another type than the one it was saved as, the question stores that suggested type and "Gör om till [type]" converts the question to it; this story supplies the stored type and the conversion, ST-SKRIPT-40-04's prototype the offer (story P15, user 2026-10-17 G2). |
| P2  | Asking the model to rebuild a question as a chosen type waits until walks show it is needed (story P16).                                                                                                                                                                                                              |
| P3  | This story ships backend, data, API and export only; the current workspace screens are frozen except for bug fixes (story P18, user 2026-10-17 G2).                                                                                                                                                                   |
| P4  | Older data, schemas and payloads get no readers, defaults or fallbacks; the format changes and the old path is deleted (repository invariant, `CLAUDE.md`).                                                                                                                                                           |
| P5  | The suggested type is the labeler's `retry_source.label_kind` when it differs from the saved kind (lead 2026-10-17, L1).                                                                                                                                                                                              |
