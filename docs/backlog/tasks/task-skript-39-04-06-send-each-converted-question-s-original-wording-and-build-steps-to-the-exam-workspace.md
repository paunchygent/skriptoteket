---
type: task
id: TASK-SKRIPT-39-04-06
title: Send each converted question's original wording and build steps to the exam workspace
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-13'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - Each imported question in a saved exam carries its original wording from the exam file and a few readable steps (the chosen type, where the answer key came from, any retry), the workspace API returns them for DOCX and DigiExam imports alike, they survive save and reopen, and raw build events stay out of the document and the API
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

After a DOCX import, each question already keeps data about how it was built,
but the teacher cannot see it per question:

- `retry_source` on the item holds the question's own chunks (`text`,
  `marked_text`), its answer-key chunks, the read-only shared context and
  `label_kind`, the labeler's first type before a type-conflict resend.
- `facit_text` on the item holds the teacher's original facit wording.
- `answer_key.origin` records where the key came from; the DOCX build maps
  the model's `key_source` to it (`copied` to `source_provided`,
  `interpreted` to `ai_interpreted`, `invented` to `machine_proposed`, no key
  to `absent`, free text to `not_applicable`). A later teacher edit changes
  the origin, so the current origin no longer tells how the question was
  imported.
- `DocxBuildEvent` records are saved per conversion job as job diagnostics,
  free of exam wording, not per question.

This task delivers, as backend and API only:

- An import record on each imported question, stored in the saved exam
  document so it survives save and reopen. The record is the same for DOCX
  and DigiExam imports. It holds:
  - the original wording: the question as written in the exam file and its
    answer-key wording;
  - a few ordered steps: the type chosen for the question; where the answer
    key came from at import; each retry the question went through.
- DOCX fill at import: the wording is the plain text of the retry source's
  own chunks plus `facit_text`; the chosen type is the item's `kind`; the
  key source is the import-time origin from the `key_source` mapping above.
  Whether the DOCX wording is stored in the record or read from
  `retry_source` when the response is built is an implementation choice; the
  API shape is the same.
- Retries, as the code records them per question today: the import's single
  type-conflict resend (admission codes `type_conflict` and
  `type_conflict_kept`), whose step names the first labeled type
  (`retry_source.label_kind`) and the type the resend used, and each
  `Konvertera igen` through the `items/retry` route. The retry handler's replacement item keeps the
  question's wording and adds a retry step naming the chosen type and whether
  the reply converted or came back as a review item. Grouping retries belong
  to the whole job, not to a question, and are not steps.
- The workspace document responses (`GET` and `PUT`
  `documents/{lineage_id}`, and the `items/retry` response) return the record
  per item as structured data. Questions created from scratch carry no
  record.
- `DocxBuildEvent` records are not copied into the document and not returned
  by the API; they stay in the job diagnostics and logs as today.
- The record is a change of the native exam document format: the document
  schema version moves on from `native_exam_document_v4`, with no reader or
  backfill for documents saved before it (repository invariant). This task
  lands after TASK-SKRIPT-39-04-08, which also changes the stored format.

DigiExam: TASK-SKRIPT-39-07-01 imports DigiExam exports into the workspace,
owns the DigiExam origin kind on the document (`NativeExamDocumentOrigin`
holds only `docx_import` and `created` today) and fills the same record
from `DigiExamIrItem` (`prompt_lines` or `prompt_html`, `item_type`,
`answer_key`). This task defines the record and
fills it for DOCX; it does not build the DigiExam import.

Out of scope: the import box and the Swedish wording of the steps in the
workspace (ST-SKRIPT-40-04), DigiExam import (TASK-SKRIPT-39-07-01), and the
save model (TASK-SKRIPT-39-04-08).

## Contract Inputs

- Item and source model:
  `src/skriptoteket/domain/curated_apps/exam_workspace/native_exam_item.py`
  (`facit_text`, `answer_key`, `retry_source`),
  `native_exam_retry_records.py` (`NativeExamRetrySource`),
  `native_exam_retry_source.py`, `native_exam_vocabulary.py`
  (`NativeAnswerKeyOrigin`), `native_exam_document.py` (schema version,
  `NativeExamDocumentOrigin`).
- DOCX build: `docx_ai_contracts.py` (`key_source`, `facit_text`,
  `DocxBuildEvent`), `docx_ai_build.py` (key-source-to-origin mapping),
  `application/curated_apps/handlers/exam_workspace_docx_build_admission.py`
  (type-conflict resend), `exam_workspace_docx_pipeline.py` (`label_kinds`),
  `exam_workspace_docx_jobs.py` (job diagnostics),
  `exam_workspace_docx_retry.py` (`Konvertera igen`).
- API: `src/skriptoteket/web/api/v1/apps_conversion_hub_exam_workspace.py`.
- DigiExam source: `domain/curated_apps/exam_conversion/digiexam_ir_contracts.py`
  (`DigiExamIrItem`), through TASK-SKRIPT-39-07-01.
- Landing order: after TASK-SKRIPT-39-04-08.
- User decisions G2 and G19 and lead decision L4 (2026-10-17), retained in
  session `01a1495e-8398-75be-b2da-f0b08ba11afa`,
  `evidence/planning/decisions-2026-10-17.md`.

## Core Vertical And Performance

A teacher imports a DOCX whose question 4 the labeler first read as single
choice and the resend built as multiple choice from an interpreted facit.
The saved exam's question 4 carries its original wording and the steps:
chosen type multiple choice, answer key interpreted from the facit, and one
retry from single choice to multiple choice. The teacher runs `Konvertera igen` as Lucktext,
saves and reopens; the `GET` response shows the same wording and one more
retry step. The record is built from data the conversion already has; it adds
no provider call.

## Validation

- Focused backend tests: the DOCX build fills the record with the chosen
  type, a resend retry step only when the resend changed the type, and the
  key source for each `key_source` value and for free text; a teacher key edit
  leaves the record's key source unchanged; `Konvertera igen` keeps the
  wording and adds one retry step for a converted reply and for a review
  reply; the record round-trips through save and reopen; a created question
  has no record; no `DocxBuildEvent` field appears in the document or the
  API response.
- Hemma staging, through the workspace API: import one genuine DOCX, save,
  reopen and read one question's record in the `GET` response.

## Stop Conditions

- TASK-SKRIPT-39-07-01 reaches implementation before this record shape is
  reviewed: coordinate the shape with that task before either writes it.
- A step G19 names cannot be derived from data the conversion or the retry
  handler already has: report to the user before adding a new capture.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| I1  | Each imported question shows its original wording plus a few readable steps: the chosen type, where the answer key came from, and retries; for DOCX and DigiExam imports alike (G19).                                                                                |
| I2  | The record survives save and reopen; raw build events stay in logs and job diagnostics, not in the document or the API (G19; job diagnostics: `exam_workspace_docx_jobs.py`).                                                                                        |
| I3  | This task ships the backend and API projection only; the import box and its wording are built by the redesign, ST-SKRIPT-40-04 (G1, G2).                                                                                                                             |
| I4  | DOCX wording comes from `retry_source` and `facit_text`, the resend retry step's first type from `retry_source.label_kind`, and the key source from the import-time `key_source` origin (`native_exam_retry_records.py`, `native_exam_item.py`, `docx_ai_build.py`). |
| I5  | DigiExam imports fill the same record in TASK-SKRIPT-39-07-01; this task owns the record and the DOCX fill (G19, G22).                                                                                                                                               |
| I6  | The document format changes without a reader for older saved documents (CLAUDE.md repository invariant).                                                                                                                                                             |
| I7  | This task lands after TASK-SKRIPT-39-04-08; both change the stored exam document format (lead 2026-10-17, L4).                                                                                                                                                       |
