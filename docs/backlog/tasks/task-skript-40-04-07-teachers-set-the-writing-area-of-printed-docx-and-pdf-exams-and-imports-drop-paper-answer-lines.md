---
type: task
id: TASK-SKRIPT-40-04-07
title: Teachers set the writing area of printed DOCX and PDF exams and imports drop paper answer lines
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
  - The student PDF and DOCX print each free-text question with its ruled writing area, short-answer gaps as one handwriting line, inline gaps as writable blanks and choice options with tick boxes, and no answers
  - PDF med facit prints the same pages with answer keys and criteria, and the Exam.net import PDF stays a separate fallback export labelled not for printing
  - A teacher sets writing lines per question with a stepper, copies a value to every free-text question in one click, and sees the result in the Förhandsgranska panel
  - QTI free-text boxes follow the question's writing lines
  - An imported DOCX underscore-only paragraph never reaches a question body
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

No printed export creates answer space today. The PDF is the Exam.net import plan with answer keys inline (`examnet_pdf_export.py`, `examnet_pdf_item_strategies.py`), the DOCX prints heading, body and points only (`exam_workspace_docx_writer.py:107-123`), Word's underscore answer lines survive as literal text, and QTI gives every free-text box a fixed 8 lines (`examnet_qti_xml.py:371-379`). The document model has no answer-space field.

This task gives each question a teacher-set writing area and makes the printed exam answerable on paper. The student PDF and DOCX print ruled writing areas in one handwriting-first house template; the print PDFs (student and med facit) render the DOCX layout, and the Exam.net import PDF stays a separate fallback export (W1-W3, W9, W11). Teachers size writing areas with a stepper and an apply-to-all action and watch a live preview (W4, W5). Short-answer gaps, inline gaps and choice options get paper answer forms (W6-W8). QTI follows the same lines (W2), and the converter stops importing underscore answer lines (W10).

Non-goals: editable templates; writing areas on kinds other than free text; changing the Exam.net QTI route for gaps or choices; changing the Exam.net import PDF.

## Contract Inputs

- User grilling 2026-10-18; TASK-SKRIPT-40-04-06 D8.
- Current code: `native_exam_item.py:57-88`, `native_exam_document.py:77-114`; `examnet_pdf_export.py:113,119,332-364`, `exam_conversion/examnet_pdf_item_strategies.py`, `digiexam_examnet_pdf_html.py:41-124`; `exam_workspace_docx_writer.py:55,107-184`; `examnet_qti_xml.py:371-379`; `exam_workspace_docx_build_prompt.py:79-80`; Kort svar as a one-gap gap_fill in its own paragraph (`examWorkspaceItemEdits.ts:406-441`, TASK-SKRIPT-39-09-05).
- `docs/reference/ref-skript-research-exam-net-qti-import-routes-per-question-type-*.md` (Enkelt svar imports as a one-gap Lucktext).

## Core Vertical And Performance

The core vertical is a writing-line count stored on free-text items, read by one print layout owner. That owner renders the student and facit variants for PDF and DOCX from the house template and drives the preview, and the QTI writer reads the same count. The structural short-answer rule (W6) and the gap blank sizing (W7) live in that print layout owner.

Units:

1. Model field, default and editor commands: the stepper and apply-to-all.
2. House template and student/facit PDF.
3. DOCX student copy.
4. QTI expected-lines.
5. The Förhandsgranska panel.
6. Converter drop of underscore-only paragraphs.

Performance is material for the preview. It renders the student PDF server-side after a debounce from the saved state, shows the last good render while a new one runs, and never blocks editing.

## Validation

- Focused backend tests:
  - writing-line default and validation;
  - the student and facit PDF HTML (ruled lines, short-answer line, blank widths, tick boxes, no answers in the student copy);
  - DOCX output;
  - QTI expected-lines;
  - the converter dropping underscore-only paragraphs while keeping dash and dot paragraphs and inline gap blanks.
- Vitest for the stepper, the apply-to-all action and the preview panel states.
- Frontend typecheck and build. Lint and typecheck for the touched backend domains.
- A staging walk that exports and prints-to-screen the omprov student PDF, the facit PDF and the DOCX, and checks the preview.

## Stop Conditions

Stop and report to the parent in either case:

- the house template cannot render ruled lines that print at handwriting spacing in both PDF and DOCX;
- the preview cannot stay responsive with a server render.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                            |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| W1  | The PDF export is the print rendering of the DOCX student exam in the house template, with writing areas and no answers; a separate PDF med facit prints the same pages with each question's answer key and criteria after it. Neither print PDF is offered for Exam.net import. |
| W2  | The DOCX export is the student copy with writing areas; the QTI free-text box expected-lines follows the question's writing-area lines instead of the fixed 8.                                                                                                                   |
| W3  | One fixed house template designed for handwriting (readable font, generous line spacing, writing lines spaced for a hand) governs the student PDF, facit PDF, DOCX and the preview; there are no template settings.                                                              |
| W4  | Free-text questions start at 8 writing lines; a Skrivyta: N rader stepper changes one question and Använd för alla fritextfrågor copies a value to every free-text question in one click.                                                                                        |
| W5  | A Förhandsgranska panel shows the rendered student PDF page by page, updates after edits, scrolls to the selected question and keeps the steppers usable while open.                                                                                                             |
| W6  | Any gap_fill question whose gap stands alone in its own paragraph, including teacher-made Kort svar and imported printed blank lines, prints as one full-width handwriting answer line.                                                                                          |
| W7  | Gaps inside sentences print as handwriting blanks long enough to write the longest accepted answer by hand, with a minimum width, and gap-fill lines get writing-height spacing so the blanks are writable on DOCX and PDF.                                                      |
| W8  | Single and multiple choice options get tick boxes in the student copy; matching and ordering keep their boxes.                                                                                                                                                                   |
| W9  | Writing areas print as ruled lines.                                                                                                                                                                                                                                              |
| W10 | The DOCX converter drops a paragraph consisting only of underscores and whitespace on import; dashes and dots are kept.                                                                                                                                                          |
| W11 | The Exam.net import PDF keeps its current content and stays a separate fallback export, last in the export menu, labelled as a fallback for Exam.net import when QTI fails and not for printing; QTI is the main route into Exam.net.                                            |

## Resume here (2026-10-18 clean break)

- Branch `codex/task-skript-40-04-07-remote`, worktree
  `/home/paunchygent/apps/skriptoteket-task-skript-40-04-07-remote`. The head is
  the commit that adds this note; its parent is merge `12c1c42f`.
- Done: the repair of review 09d50acc (changes requested at `b027d93e`). R1
  house template on A4 (`65ad81a0`, `3d5b667a`); R2 answer-line drop survives
  source reconstruction (`0383413e`); R3 preview follows the history cursor
  (`b4176e78`, `c4630370`); R4 PDFium lock (`f24adedd`); R5 preview disposal
  (`8ff9f1c3`); R6 file splits (`0ff1b18b`, `5c58b9ff`, `240b2448`, `5fe9bf48`,
  `19fa3e12`, `2602cd15`); L1 `f132b336`; L2 `9181d010`. After those, origin/main
  `188a2139` was merged with its conflicts resolved explicitly (`12c1c42f`).
- Next unit, the v8 seam: port `exam_print_document._print_walk` to
  `native_exam_outline.document_outline`. A part prints its instruction only
  when `is_empty_body(part.instruction)` is false, then prints its children in
  order. Bump `native_exam_document_v7` to `v8` everywhere: the domain,
  fixtures, frontend spec supports and `openapi.d.ts`. Keep no v7 reader. Keep
  REP-0044's admin-only AI gate.
- Open after the merge: mypy reports `printed_parent_of` missing (fixed by the
  seam). It also reports Optional `Length` errors in
  `test_exam_workspace_docx_house_geometry.py` and `Page.width/height` in
  `test_exam_print_html.py`. Frontend typecheck passes.
- Not yet run after the merge: the focused tests, lint, frontend
  ESLint/build and the one exam-workspace domain suite. R1–R4 then return to
  reviewer 09d50acc. Under the user's 2026-10-18 instruction, no review
  launches until the work resumes.
- Retained root:
  `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a14e6d-3ab6-7b8f-a363-3295c0f7fda6`
  (work orders in `evidence/lead-715cef23/orders/`).
- 2026-10-19, lead e12a2a36 (orders in `evidence/lead-e12a2a36/orders/`): the
  v8 seam and v8 bump landed (`1551b238`); mypy is at zero (`5b6d6625`, weasyprint
  stub `Page.width/height`, guard for `Length | None`); the DOCX ordering test now
  reads the drawn number box that R1 part 2 introduced (U3). Lint, typecheck,
  frontend type-check, ESLint and build pass. Exam-workspace domain suite
  (2026-10-19, `evidence/lead-e12a2a36/suite/`): vitest 942/942; pytest 17
  failed, 4308 passed, all from the merge. Main's free-text fixtures lacked
  `writing_lines` (fixed `7de1486b`), and one test called a fixture directly
  (fixed `b035ea13`). Those three files rerun green (25).
- 2026-10-19, rereview at `b3ab4b85`: changes requested on R1–R3 (R4 cleared,
  v8 seam clean; `evidence/reviews/09d50acc-…-rereview.md`). Repairs: R1
  `f44b5631` (body reset, proven on the WeasyPrint box tree); R2 `e112c3e3`
  (heading restoration skips W10 answer space, proven through the real
  chunker); R3 `6f457750` + `c1511017` (the preview sends the history owner's
  position as `step_id` and the server renders that retained step). Round-2
  domain suite: pytest 4333 passed, vitest 949 passed.
- 2026-10-19, rereview2 at `b6bb2fbb`: R1 and R3 clear; R2 reopened. A
  Heading 1-styled answer line came back through final section assembly. Fixed
  in `b2aaac08`: `with_heading_runs` and `_unshown` apply the W10 owner, proven
  through the real chunker, `assemble_build_result` and `admit_batch`. Round-3
  domain suite passed at `b2aaac08`.
- 2026-10-19, rereview3: R2 reopened again. A table cell shown as an
  instruction restores the answer line through `_in_source_form`. Explorers
  listed nine rebuild paths (P1-P9); all reach the final document only through
  `docx_ai_build.assemble_build_result`. R4.1 (`adbefd72`): one W10 gate at
  the end of `assemble_build_result` drops printed answer lines from item
  bodies, part instructions and document instructions; the round-3 `_unshown`
  filter is removed; `source_anchor` and review status are unchanged. R4.2
  (the commit after `adbefd72`): `docx_answer_line_gate.gated_item` sends an
  item to review with `ANSWER_LINE_ONLY_REASON` when its body ends empty and
  either the gate removed a line or its source chunk is only an answer line.
  Focused proof: 132 tests pass, ruff and full typecheck clean. Round-4
  domain suite at `a34a8de9` (2026-10-19, `evidence/lead-e12a2a36/suite4/`):
  pytest 4350 passed.
- 2026-10-19, rereview4 at `a34a8de9`: R2 reopened for single-question retry,
  which never reaches `assemble_build_result`. Explorer `54cfc2d4` found retry
  to be the only consumer of accepted items that bypasses assembly. R5.1:
  `RetryExamWorkspaceItemHandler.handle` returns every item, including the
  source review items, through `gated_item` at one exit, against the saved
  source chunks (`f14ba5f0`). Tests go through the real handler. Round-5
  domain suite at `f14ba5f0` (2026-10-19, `evidence/lead-e12a2a36/suite5/`):
  pytest 4357 passed. Next: R2 goes back to 09d50acc. User gates: none open.
