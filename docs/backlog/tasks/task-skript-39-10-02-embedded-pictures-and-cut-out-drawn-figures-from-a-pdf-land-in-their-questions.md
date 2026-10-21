---
type: task
id: TASK-SKRIPT-39-10-02
title: Embedded pictures and cut-out drawn figures from a PDF land in their questions
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
  - Pictures placed in the PDF come along with their question
  - Figures drawn with lines are cut out of the page generously, with the whole drawing, its labels and a margin, and placed in their question as a picture
story: ST-SKRIPT-39-10
backlog_document_profile: contract-derived
---

## Implementation Contract

A PDF import brings its pictures and its drawn figures into the questions they belong to, as a Word import does with its pictures.

- A picture placed in the PDF (an embedded image) becomes a picture chunk at its place in the reading order, so the existing grouping puts it in its question.
- A figure drawn with lines (a chart, geometry, shapes) is cut out of the page as one picture. The cut is generous: the whole drawing, every label that belongs to it and a margin. It becomes a picture chunk at the figure's place in the reading order.
- The text of a figure's labels stays inside the cut picture and is not also read as question text.
- Drawn answer lines are still dropped as in the Word import; they are not figures.
- From the picture chunk onwards, the existing Word import path runs unchanged: grouping, labeling, conversion, review, the exam picture node, its asset rules and limits, and export. PDF import adds no new AI call site (P5).

Non-goals: scanned PDFs (OCR), re-cutting a figure from the original page, picture resizing, publisher-layout parity, and the "Lägg till bild" control (TASK-SKRIPT-39-10-04).

## Contract Inputs

- ST-SKRIPT-39-10 P3, P5, P6 and P8 (figures are cut generously). The Mac plan is in Mac retained root `01a1602d-173d-72ed-b3ac-83c6a24e9070`, `evidence/planning/ST-SKRIPT-39-10/plan.md`.
- TASK-SKRIPT-39-10-01 (done): the PDF reader `exam_workspace_pdf_chunker.py`, `exam_workspace_pdf_layout.py` and `exam_workspace_pdf_blocks.py`. The chunker returns `LabelerSource` with `images={}`; this task fills it.
- The Word picture path: `exam_workspace_docx_picture.py`, `exam_workspace_labeler_block_image.py`, `exam_image_readability.py`, and the picture node in `examWorkspaceRichTextSchema.ts`.
- Declared PDF libraries: pdfplumber, pypdf and pypdfium2 (page rendering).
- The Word corpus fixtures in `tests/fixtures/exam_conversion/docx_corpus/` that hold pictures or drawn figures, saved as PDF from Microsoft Word.

## Core Vertical And Performance

A teacher drops a Word corpus exam with a picture and a drawn figure, saved as PDF, into the import box. The exam opens with the picture in its question and the figure, cut whole with its labels and a margin, as a picture in its question. The labels' text does not appear a second time as question text. Import time stays in the range of a Word import of the same exam.

## Validation

- Focused fail-first tests: an embedded picture lands as a picture chunk in its reading-order place; a drawn figure is cut as one picture that holds the whole drawing, its labels and a margin; a figure's label text is not also emitted as text; drawn answer lines are still dropped; a page with two figures gives two pictures in order.
- Corpus parity: for each fixture with pictures, the PDF import gives the same pictures in the same questions as the Word import of the same exam.
- `pdm run lint`, `pdm run typecheck` and docs-validate; fe-type-check and fe-lint if the frontend is touched.
- One independent review.
- A staging walk by the Mac with the proof admin, AI on (P4): one corpus exam with a picture and a drawn figure, saved as PDF, opens with both in their questions, and the PDF med facit export shows them.

## Stop Conditions

- Stop and report if pictures cannot reach the document through the existing picture chunk, picture node and asset rules without changing the exam document format.
- Stop and report if cutting figures needs a dependency beyond the declared PDF libraries.
- Stop and report if a figure cannot be told apart from drawn answer lines or table rules on the corpus without a new AI call.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                   |
| --- | ----------------------------------------------------------------------------------------------------------------------- |
| T1  | ST-SKRIPT-39-10 P3, P5, P6 and P8 apply as written.                                                                     |
| T2  | Pictures and cut figures enter through the Word import's picture chunk and the exam's existing picture node and limits. |
| T3  | A cut figure includes its labels and a margin; its label text is not also read as question text.                        |
| T4  | Real task: one independent review, at most one rereview per finding; staging walk by the Mac.                           |

## Progress

### 2026-10-22 (Hemma orchestrator)

- Full contract written from the ST-SKRIPT-39-10 story terms, and status set to `ready` by the user's decision of 2026-10-22 (Mac AskUserQuestion, "39-10-02 + REP-0049"). A fresh lead session is assigned.
