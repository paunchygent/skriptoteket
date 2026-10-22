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

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T1  | ST-SKRIPT-39-10 P3, P5, P6 and P8 apply as written.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| T2  | Pictures and cut figures enter through the Word import's picture chunk and the exam's existing picture node and limits.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| T3  | A cut figure includes its labels and a margin; its label text is not also read as question text.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| T4  | Real task: one independent review, at most one rereview per finding; staging walk by the Mac. User decision after the second review (user via orchestrator, 2026-10-22, verbatim "stop fucking reviewing it over and over again. Now it's enough."): no further independent review; the second review's S1-S5 close on focused fail-first proof admitted by the orchestrator. |
| T5  | User decision (user via Mac AskUserQuestion 2026-10-22; agent-planning:user-closure-gate), replaces the earlier T5 "Labels outside become text": a picture or drawn figure keeps the text that sits on it, as it looks in the file (labels on a map, a triangle's A, B and C, a chart's axis numbers), and that text is not also read as question text (T3 as written). Accepted residuals, by the user's reason that real exams do not write the key on a figure or a map: an answer written next to a figure, inside its bounding box or in its label ring, is read as a label (review F1), and an indented answer paragraph over a placed picture belongs to the picture (rereview F3). No rule makes a placed picture own no text. |
| T6  | Follows from T5, T7 and T8 (user via Mac AskUserQuestion 2026-10-22; agent-planning:user-closure-gate): a word that belongs to no picture or figure is painted white wherever it falls inside a cut picture. Cost: such text lying over a picture leaves white areas in it.                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| T7  | User decision (user via Mac AskUserQuestion 2026-10-22; agent-planning:user-closure-gate), "Accept, teacher deletes": a drawing made only of its outline (a box or rectangle) is a picture; words inside it stay text and are painted white. A border that paragraphs run inside from the left text margin is decoration and makes no picture. Cost: a bordered text box also yields an empty-box picture, which the teacher deletes.                                                                                                                                                                                                                                                                                                  |
| T8  | User decision (user via Mac AskUserQuestion 2026-10-22; agent-planning:user-closure-gate), "Accept one picture per page": a placed picture of any size is a picture; text from a paragraph running over it stays text. Cost: a scanned or full-background page becomes one picture per page, with its text areas painted white.                                                                                                                                                                                                                                                                                                                                                                                                        |
| T9  | User decision (user via Mac AskUserQuestion 2026-10-22; agent-planning:user-closure-gate), rereview F2: the even-odd band rule is removed; a fill-only box (no outline) behind text is shading: its text stays text and it makes no picture (paragraph shading, highlights, shaded table cells, a shape with its outline removed). Second review S3, user decision (user via orchestrator AskUserQuestion 2026-10-22, "Accept narrow rule"; agent-planning:user-closure-gate): the inference across separate paint operations stays removed; a fill whose two nested rectangles are painted by one even-odd operation, read from the content stream with pypdf, is its painted bands (a CSS border reads as an answer line). |

## Progress

### 2026-10-22 (Hemma orchestrator)

- Full contract written from the ST-SKRIPT-39-10 story terms, and status set to `ready` by the user's decision of 2026-10-22 (Mac AskUserQuestion, "39-10-02 + REP-0049"). A fresh lead session is assigned.

### 2026-10-22 (implementation lead)

- Built on `codex/task-skript-39-10-02`. `exam_workspace_pdf_graphics` decides each page's
  pictures and drawn figures from the PDF's own drawing primitives (box geometry, no text
  cues, no AI): placed pictures; figures with their labels; answer lines, rules, frames,
  text shading, page-sized backgrounds and strokes in text tables are not figures; a ruled
  grid without text is a drawing. `exam_workspace_pdf_pictures` cuts each region out of
  the PDFium-rendered page (180 dpi PNG, only pages with pictures) and the blocks emit it
  as the Word import's `drawing` chunk; the labeler gets the same PNG. A failed render is
  a named missing picture. Header and footer pictures that recur are dropped. A PDF with
  pictures and no text still stops with the no-text error.
- A ring label beside or under a figure is taken only when it does not start at the left
  text margin, so a paragraph right after a figure stays text; a picture behind a
  paragraph claims none of its words.
- Proof: fail-first (7 of 9 new reader tests fail on 41691447), classifier geometry tests,
  a pipeline test that runs a PDF picture through grouping, labeling, conversion and the
  native document, lint and typecheck. Logs in retained root
  `01a160cd-e56d-72dd-a347-6c49957db10c` `evidence/proof/`.
- Corpus parity: no corpus fixture held a picture or drawn figure, so the Mac made
  `metodprov_med_bilder.docx` in Microsoft Word (a chart picture in question 7, figures
  drawn with shapes and text-box labels in questions 5 and 6) and Word's own PDF export;
  both are in `tests/fixtures/exam_conversion/pdf_corpus/`. The PDF import gives the same
  101 chunks and text as the Word import, the picture in the same place with its shape,
  and both drawn figures as pictures in their places (the Word import has no picture for
  Word shapes). No answer line, rule or table became a figure on it, so the stop
  condition did not trigger. Reading the PDF takes about 1.8 s, as before this task.
- Residual (39-10-01, not this task): a non-breaking space Word kept on one line reads as
  a line break inside the paragraph ("100\\nelever").
- Review `changes_requested` (F1-F7, retained root `evidence/reviews/review-39-10-02.md`):
  repairs follow T5-T9.
- Repairs: a figure owns only words inside its outline and its cut stops short of the
  rest (F1, F4); words that stay text are painted white in every cut (T6); a box drawing
  is a picture, a paragraph or page border is not, and even-odd filled rect pairs read as
  their painted bands (F2); pictures and strokes have no size limit (F3); regions map
  through the CropBox PDFium renders, and a rotated page or a bitmap of the wrong size
  gives a named missing picture (F5); the pdfplumber adapter narrows its records without
  `Any` (F7); the layout and blocks modules are split by responsibility into items, page
  adapter, furniture, layout, paragraphs, block tables and blocks, each under 500 lines
  (F6). The reviewer's probes are reader tests that fail on ce01ebcd9 and pass now.
  Proof in retained root `evidence/proof/repair/`, with before and after examples of each
  cost in `examples/`.
- Rereview `changes_requested` (F1-F3, `evidence/reviews/review-39-10-02-rereview.md`);
  second repair round by the user's decisions T5 and T9, replacing two first-round rules
  above: the even-odd band rule is removed, so two nested fills are one filled figure
  (T9); a figure again keeps its ring labels, so a triangle's A, B and C and an axis tick
  are in the picture and not in the text (T5, T3 as written). A box drawing takes ring
  labels but no words inside it (T7). F1 and F3 are accepted residuals (T5). Measured
  limit: a line more than half a body size above or below a figure (an axis title one
  line further down, "8 cm" 8 pt under a rectangle) stays text. Proof in
  `evidence/proof/repair/r5b/`.
