---
type: task
id: TASK-SKRIPT-39-07-01
title: Import a DigiExam export into the exam workspace as a native exam document
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
  - A teacher's .dxe DigiExam export imports through the workspace API into a saved native exam document with a DigiExam origin, its supported questions, assets and points; questions of unsupported types are not imported and the import notes name each one by number and opening words (EPIC-SKRIPT-39 E12)
story: ST-SKRIPT-39-07
backlog_document_profile: contract-derived
---

## Implementation Contract

A DigiExam `.dxe` export reaches the exam workspace only through the old
converter today. The workspace import route accepts `.docx` only
(`ImportExamWorkspaceDocumentHandler` rejects other files with `Välj en .docx-fil.`), and `NativeExamDocumentOrigin.kind` allows `docx_import` and
`created` only. This task imports a `.dxe` export into a saved native exam
document that the workspace opens, edits and exports like a DOCX import.

This task delivers:

- A mapper from `DigiExamIntermediateExam` to `NativeExamDocument`. The mapper
  lives on the workspace side and imports the DigiExam IR, the direction the
  dependencies already run (workspace modules import `digiexam_*` modules
  today, never the reverse). Per `DigiExamIrItem`:
  - Item kind, following the mapping the current DigiExam QTI adapter already
    uses (`digiexam_examnet_qti_adapter.py`, `_qti_item`): `open_ended` to
    `free_text`; `single_choice` and `multiple_choice` to `single_choice`;
    `multiple_response` to `multiple_response`; `gap_fill` to `gap_fill`.
  - Question text: `prompt_html` becomes native paragraphs with the text
    formatting the native body already holds; embedded images
    (`embedded_assets` with their references) become exam assets of the
    document, placed where the source references them.
  - Choice alternatives, gaps and `max_score` become the item's choices, gaps
    and points.
  - Answer keys and their provenance: a key present in the `.dxe`
    (`dxe_populated_key`) becomes the item's key with origin
    `source_provided`; `absent` stays `absent`; `not_applicable` stays
    `not_applicable`. The import parses the bare `.dxe` without an overlay or a
    result PDF, so the overlay and result-PDF provenances do not occur here.
  - Manual follow-ups (`manual_marking_required`,
    `manual_answer_key_required`, `parser_warning_blocks_rendering`) become
    `review_required` on the item, with the follow-up message as the review
    reason.
  - An item of type `unknown` (follow-up `unsupported_item_type`) is not
    imported: the mapper builds no native item for it, and the import notes
    name each such item by its question number and opening words (T8). This
    matches EPIC-SKRIPT-39 E12.
- A DigiExam document origin: a new `NativeExamDocumentOrigin` kind for
  DigiExam imports that, like `docx_import`, requires the source filename and
  the source SHA-256.
- The workspace import route and job for `.dxe`: an upload route under
  `/api/v1/apps/documents.conversion_hub/exam-workspace/` that accepts a
  `.dxe` file with the same optional `course_key` as the DOCX import, queues
  one import job on the same job ledger as the DOCX import
  (`ExamAnswerKeyEnrichmentJob`, a DigiExam import source kind beside
  `docx_import`), and reports progress through the existing
  `GET /exam-workspace/conversion-jobs/{job_id}` status route. The job parses
  the file with the existing DigiExam parser (`parse_source_exam`), maps it
  and saves revision 1 as a workspace document in Mina filer. The OpenAPI
  types are regenerated so TASK-SKRIPT-40-04-03 can build the `Öppna` drawer
  entry against the route.
- Original wording for the import box (G19): each imported question keeps its
  DigiExam wording (`prompt_html`, `prompt_lines`) and the import records its
  steps in the shape TASK-SKRIPT-39-04-06 defines for DOCX imports. This task
  does not build a second projection.

Out of scope: any workspace UI (G2; TASK-SKRIPT-40-04-03), AI answer-key
suggestions (TASK-SKRIPT-39-07-02), removal of the old converter
(TASK-SKRIPT-39-07-03), and any handling of unsupported DigiExam types beyond
E12.

## Contract Inputs

- Story ST-SKRIPT-39-07 terms S1-S7.
- DigiExam IR and parser:
  `src/skriptoteket/domain/curated_apps/exam_conversion/digiexam_ir_contracts.py`,
  `src/skriptoteket/domain/curated_apps/exam_conversion/digiexam_contracts.py`
  (`DigiExamItemType`, `DigiExamAnswerKeyProvenance`, `DigiExamGap`),
  `parse_source_exam` in
  `src/skriptoteket/application/curated_apps/exam_conversion_producers.py`.
- Kind mapping precedent:
  `src/skriptoteket/domain/curated_apps/exam_conversion/digiexam_examnet_qti_adapter.py`.
- Native model:
  `src/skriptoteket/domain/curated_apps/exam_workspace/native_exam_document.py`,
  `native_exam_body.py`, `native_exam_values.py` (`NativeItemReview`) and
  `native_exam_vocabulary.py` (`NativeExamItemKind`, `NativeAnswerKeyOrigin`,
  `NativeItemReviewState`).
- Import and job pattern:
  `src/skriptoteket/application/curated_apps/handlers/exam_workspace_documents.py`
  (`ImportExamWorkspaceDocumentHandler`, `conversion_status`),
  `src/skriptoteket/application/curated_apps/handlers/exam_workspace_docx_jobs.py`,
  `src/skriptoteket/application/curated_apps/exam_answer_key_enrichment.py`
  (`ExamAnswerKeySourceKind`),
  `src/skriptoteket/web/api/v1/apps_conversion_hub_exam_workspace.py`.
- Fixtures: `tests/fixtures/exam_conversion/1772718003-test-samma-prov-i-digiexam.dxe`,
  `tests/fixtures/exam_conversion/sanitized-embedded-image.dxe` and
  `tests/fixtures/exam_conversion/real_inputs/1776888013-ak7-lag-och-ratt.dxe`.
- TASK-SKRIPT-39-04-06 for the wording-and-steps shape.

## Core Vertical And Performance

A teacher's `.dxe` export is uploaded to the import route with a course. The
job parses and maps it and saves a native exam document with a DigiExam origin,
its supported questions, keys, points and pictures. The existing document,
export and checklist routes open it and export QTI, PDF and DOCX without any
DigiExam-specific code. The import runs once per upload in the background job;
no editor request parses the `.dxe` again.

## Validation

- Focused mapper tests on the three fixtures: each supported DigiExam type
  maps to its native kind; points, alternatives and gaps carry over; a
  `dxe_populated_key` key arrives as `source_provided`, a keyless item as
  `absent`; a manual follow-up arrives as `review_required` with its message;
  the embedded image arrives as an exam asset; an `unknown` item yields no
  native item and the import notes name it by its question number and opening
  words.
- Focused origin test: the DigiExam origin requires filename and SHA-256.
- Focused route and job tests: a `.dxe` upload queues one job and returns the
  conversion status; an empty file, a non-`.dxe` file and an unknown
  `course_key` are rejected; the job saves revision 1 with the DigiExam origin.
- API proof against the running app: upload the real fixture through the
  import route, poll the status route to completion, read the document, and
  fetch its QTI, PDF and DOCX exports; the responses are retained in the
  task's evidence. No browser walk: the workspace UI for this route comes from
  TASK-SKRIPT-40-04-03 (G2).

## Stop Conditions

- TASK-SKRIPT-39-04-06 has not fixed the wording-and-steps shape when this
  task needs it: coordinate with that task's owner instead of defining a
  DigiExam-only shape.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                              |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| T1  | DigiExam conversion is a secondary input mode of the exam workspace and uses the same editor (EPIC-SKRIPT-39 E16, user 2026-10-12).                                |
| T2  | No unsupported DigiExam types and no new importer research are authorized (EPIC-SKRIPT-39 E12).                                                                    |
| T3  | DigiExam exams export in the same QTI 3.0 package shape as other workspace exams (EPIC-SKRIPT-39 E13).                                                             |
| T4  | This task ships backend, data and API only; the Öppna-drawer DigiExam entry is built by ST-SKRIPT-40-04 (G2, user 2026-10-17).                                     |
| T5  | DigiExam imports use the workspace's per-question review; unsupported types keep E12 (G21, user 2026-10-17).                                                       |
| T6  | The task starts now as a backend lane (G22, user 2026-10-17).                                                                                                      |
| T7  | The import box shows original wording and a few readable steps for DigiExam imports too; TASK-SKRIPT-39-04-06 builds that projection (G19, user 2026-10-17).       |
| T8  | DigiExam questions of unsupported types are not imported; the import notes name each one by its number and opening words; this matches E12 (user 2026-10-17, G26). |
