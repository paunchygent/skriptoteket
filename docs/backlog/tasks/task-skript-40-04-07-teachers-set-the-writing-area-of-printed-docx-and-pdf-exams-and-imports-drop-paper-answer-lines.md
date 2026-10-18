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
  - PDF med facit prints the same pages with answer keys and criteria, and the export menu states the PDF can be imported into Exam.net
  - A teacher sets writing lines per question with a stepper, copies a value to every free-text question in one click, and sees the result in the Förhandsgranska panel
  - QTI free-text boxes follow the question's writing lines
  - An imported DOCX underscore-only paragraph never reaches a question body
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

No printed export creates answer space today. The PDF is the Exam.net import plan with answer keys inline (`examnet_pdf_export.py`, `examnet_pdf_item_strategies.py`), the DOCX prints heading, body and points only (`exam_workspace_docx_writer.py:107-123`), Word's underscore answer lines survive as literal text, and QTI gives every free-text box a fixed 8 lines (`examnet_qti_xml.py:371-379`). The document model has no answer-space field.

This task gives each question a teacher-set writing area and makes the printed exam answerable on paper. The student PDF and DOCX print ruled writing areas in one handwriting-first house template; a facit PDF carries the answer keys (W1-W3, W9). Teachers size writing areas with a stepper and an apply-to-all action and watch a live preview (W4, W5). Short-answer gaps, inline gaps and choice options get paper answer forms (W6-W8). QTI follows the same lines (W2), and the converter stops importing underscore answer lines (W10).

Non-goals: editable templates; writing areas on kinds other than free text; changing the Exam.net QTI route for gaps or choices.

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

| ID  | Decided contract term                                                                                                                                                                                                                                                                                 |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| W1  | The PDF export is a printable student exam with writing areas and no answers, and the export menu states it can also be imported into Exam.net as a PDF; a separate PDF med facit prints the same pages with each question's answer key and criteria after it and serves as the Exam.net import plan. |
| W2  | The DOCX export is the student copy with writing areas; the QTI free-text box expected-lines follows the question's writing-area lines instead of the fixed 8.                                                                                                                                        |
| W3  | One fixed house template designed for handwriting (readable font, generous line spacing, writing lines spaced for a hand) governs the student PDF, facit PDF, DOCX and the preview; there are no template settings.                                                                                   |
| W4  | Free-text questions start at 8 writing lines; a Skrivyta: N rader stepper changes one question and Använd för alla fritextfrågor copies a value to every free-text question in one click.                                                                                                             |
| W5  | A Förhandsgranska panel shows the rendered student PDF page by page, updates after edits, scrolls to the selected question and keeps the steppers usable while open.                                                                                                                                  |
| W6  | Any gap_fill question whose gap stands alone in its own paragraph, including teacher-made Kort svar and imported printed blank lines, prints as one full-width handwriting answer line.                                                                                                               |
| W7  | Gaps inside sentences print as handwriting blanks long enough to write the longest accepted answer by hand, with a minimum width, and gap-fill lines get writing-height spacing so the blanks are writable on DOCX and PDF.                                                                           |
| W8  | Single and multiple choice options get tick boxes in the student copy; matching and ordering keep their boxes.                                                                                                                                                                                        |
| W9  | Writing areas print as ruled lines.                                                                                                                                                                                                                                                                   |
| W10 | The DOCX converter drops a paragraph consisting only of underscores and whitespace on import; dashes and dots are kept.                                                                                                                                                                               |
