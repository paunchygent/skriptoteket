---
type: task
id: TASK-SKRIPT-39-10-01
title: A PDF exam with text opens in the exam workspace through the Word import path
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-21'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - A Word corpus exam saved as PDF, dropped or chosen in the exam workspace import box, opens in the editor with its text questions, through the same chunk sequence and conversion path as the Word import
  - PDF import adds no new AI call site and follows Word import access; guests get the sign-in prompt naming PDF with DigiExam and Word
  - A staging walk shows the PDF exam opening, text only
story: ST-SKRIPT-39-10
backlog_document_profile: contract-derived
---

## Implementation Contract

The walking skeleton of ST-SKRIPT-39-10. A teacher drops or chooses a PDF in the exam workspace import box, the same box that takes Word, DigiExam and QTI files. The PDF is read locally into the chunk sequence the Word import produces (paragraphs, headings, tables), and the existing Word path runs it unchanged: AI grouping, labeling, conversion, review, the points warning and export. The exam opens in the editor as a Word import does.

This task carries text only:

- Repeated page headers, footers and page numbers are dropped.
- Two-column pages read column by column.
- Drawn answer lines are dropped, as in the Word import.

Pictures and drawn figures (TASK-SKRIPT-39-10-02) and the no-text stop message and skipped-pages note (TASK-SKRIPT-39-10-03) are later tasks.

Non-goals: scanned PDFs (OCR), pictures and figures, the no-text rules, publisher-layout parity, and any new AI call site.

## Contract Inputs

- ST-SKRIPT-39-10 P1, P4, P5 and P9. The Mac plan and explorer evidence are in Mac retained root `01a1602d-173d-72ed-b3ac-83c6a24e9070`, `evidence/planning/ST-SKRIPT-39-10/plan.md`.
- `infrastructure/documents/pdf_text_extraction.py` (pdfplumber; pypdf and pypdfium2 are also declared), `infrastructure/curated_apps/apps/conversion_hub/exam_workspace_docx_chunker.py`, `application/curated_apps/handlers/exam_workspace_docx_pipeline.py`, the import box in `views/apps/exam-workspace/ExamWorkspaceOpenDrawer.vue` and `useExamWorkspaceSourceFile.ts`.
- ST-SKRIPT-41-02 P1 (guests use no AI) and ST-SKRIPT-41-01 (the LLM provider door, which carries PDF import with the Word import).

## Core Vertical And Performance

One Word corpus exam saved as PDF goes through the import box, is read into the Word chunk sequence, runs the Word conversion path and opens in the editor with the same text questions, types and points as its Word import. The PDF reading runs locally and adds no external call. It must not slow the Word path.

## Validation

- Focused tests:
  - PDF bytes produce the Word chunk sequence for paragraphs, headings, tables, repeated headers and footers, page numbers, two columns and answer lines;
  - the PDF source enters the existing pipeline;
  - the import box accepts PDF;
  - access follows the Word import, so a guest gets the sign-in prompt naming PDF with DigiExam and Word;
  - a guard shows no new AI call site.
- Lint and typecheck for the backend; Vitest, fe-type-check and fe-lint for the frontend.
- A staging walk by the Mac with the proof admin: one corpus exam saved as PDF opens, text only. It is judged as if AI is on for teachers (P4).

## Stop Conditions

- Stop and report if the PDF cannot be mapped onto the Word chunk sequence without changing the Word conversion path.
- Stop and report any new product decision. It goes to the Mac orchestrator.

## Decided Contract Terms

| ID  | Decided contract term                                                                      |
| --- | ------------------------------------------------------------------------------------------ |
| T1  | ST-SKRIPT-39-10 P1, P4, P5 and P9 apply as written.                                        |
| T2  | This task is text only; pictures, figures and the no-text rules belong to tasks 02 and 03. |
| T3  | The REP-0044 admin-only AI gate stays; the walk uses the proof admin.                      |

## Progress

### 2026-10-21 (Hemma orchestrator)

- Scaffolded from the ST-SKRIPT-39-10 story terms. The story is `ready` by the user's grilling of 2026-10-21, relayed by the Mac orchestrator, and this task is `ready` with it. A lead session is assigned.

### 2026-10-21 (implementation lead, branch `codex/task-skript-39-10-01`)

- Mechanism: the PDF uses the Word import lane unchanged. The import handler admits a `.pdf` whose bytes start with `%PDF-` into an `ExamAnswerKeySourceKind.DOCX_IMPORT` job; the bytes travel in the existing `source_docx` field. The job's chunker and the pipeline's labeler source are format dispatchers (`exam_workspace_import_source`) that send PDF bytes to the new pdfplumber reader and Word bytes to the Word readers. The pipeline, job handler and validator are unchanged, and pdfplumber loads only when a PDF is read.
- The reader (`exam_workspace_pdf_layout`, `exam_workspace_pdf_blocks`, `exam_workspace_pdf_chunker`) rebuilds the Word chunks: paragraphs from line pitch and wrap, soft line breaks, headings from font size, italic as the `<i>` facit cue, ruled and borderless tables, two-column pages, and underscore answer lines as their own chunks. It drops repeated headers, footers and page numbers. Drawn lines carry no text.
- Real-producer proof: the Word-saved PDF of `bf26_english_1_unit_test_kap_1_2_med_facit` reads as the Word file's 136 chunks. Every table, heading level and italic span is equal. The only difference is six Word paragraphs that contain a blank soft-broken line; each reads as two chunks.
- The import box accepts `.pdf`; the guest prompt reads "Logga in för att importera från DigiExam, Word eller PDF.". Access is the Word import's route gate. An import scan shows that the PDF modules import no AI client.
- Review F1 and F2 (page furniture), repaired under the user's page-match rule (2026-10-22) with the orchestrator's choice (c): a repeated line's changing number is a page counter only when it equals the page number, and such a line counts as a header or footer only in a font smaller than the body text or set off from the body by more than one body line step. Known limit: a body-size line whose only changing number equals its page number, with more than a line step of white space below it (above it, for a footer), is dropped.
- Owed: the staging walk (Validation), then closeout.
