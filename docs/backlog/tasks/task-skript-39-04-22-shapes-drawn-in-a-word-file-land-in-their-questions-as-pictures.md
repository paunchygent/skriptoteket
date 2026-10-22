---
type: task
id: TASK-SKRIPT-39-04-22
title: Shapes drawn in a Word file land in their questions as pictures
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-22'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- A shape group, a single shape or a drawing canvas made of supported shapes becomes
  a picture in its question
- A figure holding an unsupported shape keeps today's descriptor and review warning
- The Word import of metodprov_med_bilder.docx gives pictures in questions 5 and 6
- Word export writes the figure's original shapes back, editable in Word
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

A Word import brings figures drawn with Word's shapes into their questions as pictures, as the
PDF import does since TASK-SKRIPT-39-10-02.

- Today a body block that holds only drawn shapes and no embedded picture becomes a `drawing`
  chunk with no image. The model sees "[Bild utan text]", and the question goes to review with
  "Delar av källtexten saknas".
- After this task, such a block whose shapes are all supported becomes one picture at its place
  in the reading order. The picture is drawn from Word's own shape data (D1, D2).
- A figure holding any unsupported shape, fill or effect is left out whole, as today (D3).
- A drawing made only of plain lines is no figure (D4).
- From the picture chunk onwards, the Word path runs unchanged (D5).
- The import also stores the figure's original Word shape markup with the picture's
  asset. Display, Exam.net QTI, the student PDF and PDF med facit use the picture (D8).
- Word (DOCX) export writes the stored shapes back instead of the picture, so the exported
  file opens in Word with editable shapes (D9). Only self-contained markup is stored (D12).
- When the teacher replaces or removes the picture, its stored shapes go with it (D10).
- Non-goals: native Word charts (`c:chart`), SmartArt (`dgm`), custom geometry, gradient or
  picture fills, and VML-only legacy shapes.

## Contract Inputs

- Proven drop, from the orchestrator's chunker probe and the Mac staging walk of the Word
  import (document a09def63, 2026-10-22), both on
  `tests/fixtures/exam_conversion/pdf_corpus/metodprov_med_bilder.docx`:
  - Question 5 (`body:0029`): a `wpg` group of two ellipses with text-box labels.
  - Question 6 (`body:0036`): a `wpg` group of rect, rightArrow, rect, rightArrow, rect with
    text-box labels.
  - Both give a `drawing` chunk with 0 images. The placed chart in question 7 gives 1 image.
- The file's `mc:Fallback` holds VML ovals and no preview picture. LibreOffice is not on Hemma
  or in the worker image.
- Existing code to build on:
  - `exam_workspace_docx_chunker.py`: `drawn`, `_placeable_pictures`, `_rendered_picture` and
    `_block_png`.
  - `exam_workspace_labeler_block_image.py`: `DocxBlockImageRenderer`. It renders HTML through
    `render_html_to_pdf_bytes`, rasterizes with `rasterize_pdf_pages` and crops. Its `_drawing`
    raises `_Unrenderable` for a drawing without a picture.
- Word answer lines are printed underscores (`is_answer_line_chunk` in `shared_body.py`), not
  drawn lines.

## Core Vertical And Performance

The core vertical: import `metodprov_med_bilder.docx`, then check that questions 5 and 6 carry
their pictures in the workspace and in the PDF med facit export.

The shape drawing runs only for blocks that hold drawn shapes and no picture, so ordinary
imports pay nothing new. The render reuses the existing HTML-to-PDF and PDFium stack, with one
render per figure.

Units, one junior each:

1. Read a drawing's shapes into a figure model. This covers groups with their child transforms,
   single shapes and canvases, and the supported preset geometry, fills, outlines, arrowheads
   and text-box labels. Anything unsupported is reported as such.
2. Draw a figure model as SVG and turn it into a PNG through the existing render stack.
3. Wire the chunker so a drawn-only block gets its picture, and apply D3 and D4.
4. Store the self-contained shape markup with the picture's asset, and drop it when the
   picture is replaced or removed (D8, D10, D12).
5. Make the Word export write the stored shapes in place of the picture (D9).
6. Prove fixture parity with the PDF import.

## Validation

- Focused tests for each supported shape kind and container.
- One test with an unsupported shape (the figure keeps its descriptor) and one with a line-only
  drawing.
- The Word import of `metodprov_med_bilder.docx` gives pictures in questions 5 and 6 at the
  same places as its PDF import, and the labels are not question text.
- The existing Word picture tests stay green.
- A Word export of that import holds the original shape groups in questions 5 and 6, and
  no stored shapes remain after a picture is replaced or removed.
- A Mac staging walk of that Word import: the figures with their labels inside, parity
  with the PDF import, the Exam.net and PDF exports showing the pictures, and a Word
  export that opens in Word with editable shapes in questions 5 and 6 (D6, D9).

## Stop Conditions

- The drawn picture would need a new system dependency, such as LibreOffice.
- A supported shape cannot be drawn faithfully enough for the teacher to recognise the figure.
- The change would alter the picture path after the picture chunk, or add an AI call site.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | Draw the shapes from Word's DrawingML data (preset geometry, group and child transforms, solid fill, solid outline, arrowheads, text-box labels) as SVG, and turn it into a PNG through the existing HTML-to-PDF and PDFium stack. Add no LibreOffice. |
| D2  | Cover shape groups (`wpg:wgp`), single shapes (`wps:wsp`) and drawing canvases (`wpc:wpc`) built from rectangles, rounded rectangles, ellipses, triangles, right triangles, lines, straight connectors and the four block arrows, with their text-box labels. Native charts, SmartArt, custom geometry, gradient or picture fills and VML-only shapes are out. |
| D3  | A figure holding any unsupported shape, fill or effect is left out whole, as today: "[Bild utan text]" and review with "Delar av källtexten saknas". |
| D4  | A drawing made only of plain lines or connectors, with no arrowheads and no labels, is no figure and keeps today's handling, as drawn answer lines are not figures in the PDF import. |
| D5  | The drawn PNG is the drawing chunk's picture. From the picture chunk onwards, the Word path runs unchanged: grouping, labeling, exam picture node, asset rules and limits, export. The label text stays inside the picture and is not question text. No new AI call site. |
| D6  | Proof: focused tests for each supported shape kind and container, plus one for an unsupported shape and one for a line-only drawing. The Word import of `metodprov_med_bilder.docx` gives pictures in questions 5 and 6 at the same places as its PDF import. The existing Word picture tests stay green. A Mac staging walk covers that Word import and its PDF med facit export. |
| D7  | One independent review at most. Repairs are admitted on focused fail-first proof, with no rereview unless the user asks (user rule 2026-10-22). |
| D8  | The import stores the figure's original Word shape markup with its picture's asset. Display, Exam.net QTI, the student PDF and PDF med facit use the picture. |
| D9  | Word (DOCX) export writes the stored shapes back in place of the picture, so the exported file opens in Word with editable shapes. |
| D10 | When the teacher replaces or removes the picture in the workspace, its stored shapes go with it; the new picture carries none. |
| D11 | Questions 5 and 6 of `metodprov_med_bilder.docx` are no longer review items for a missing picture. |
| D12 | Only self-contained shape markup is stored. Markup that references a relationship (an embedded picture, a hyperlink or another part) stores none, and its Word export writes the picture. |

D8–D11 are the user's decision (via the Mac orchestrator's AskUserQuestion, 2026-10-22,
verbatim "Picture + keep shapes (Recommended)"; agent-planning:user-closure-gate). D1–D7
and D12 are orchestrator decisions under the user's delegation (2026-10-22, "Take care of
it."). All come from the retained plan in root `01a162d4-76fc-7f54-bc33-c0dd63e13388`.
