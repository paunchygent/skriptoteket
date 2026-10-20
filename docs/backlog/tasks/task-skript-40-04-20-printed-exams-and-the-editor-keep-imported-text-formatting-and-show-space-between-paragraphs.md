---
type: task
id: TASK-SKRIPT-40-04-20
title: Printed exams and the editor keep imported text formatting and show space between paragraphs
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-20'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - A native exam text with bold, italic, underline, superscript or subscript words prints those words with the same marks in the print PDF, the Förhandsgranska preview and the DOCX student copy
  - A line break inside a paragraph prints as a line break in the print PDF and the preview
  - Consecutive paragraphs show visible space between them in the full exam editor and in every print surface
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Resume here

Status 2026-10-20: U1-U4 integrated and committed on
`codex/task-skript-print-formatting-remote`. Focused proof: 145 print/DOCX tests and 541
neighbouring export tests pass; lint, typecheck, fe-type-check, fe-lint, fe-build pass;
rendered proof page `evidence/print-proof/print-page-1.png` (synthetic sample, real
WeasyPrint renderer). Next: the domain suite on the orchestrator's go, Pi ruthless review,
Mac staging walk of the editor gap and the print. Evidence: retained root
`01a15992-0dae-73a8-8965-6dd9ef7ad693`, user screenshot `user-staging-screenshot.webp`.

## Implementation Contract

The user reported on staging (2026-10-20) after importing a colleague's Word exam
through the AI conversion: the editor keeps an instruction's bold words and its
paragraphs, but (1) the print PDF and the Förhandsgranska preview print the bold
words as plain text, and (2) consecutive paragraphs sit directly under each other,
in the editor and in print, with no space that marks them as separate paragraphs.
The user wants imported formatting kept through conversion, editor and print.

Root cause (lead, with evidence):

- `exam_print_document.py` builds every printed text run as `PrintText(segment.text)`
  (`_instruction_runs`, `_text_paragraph_runs`, `_gap_line_runs`), and `PrintText`
  carries only `text`. Both print renderers read only this model: `exam_print_html.py`
  (WeasyPrint print PDF and the Förhandsgranska preview) and
  `exam_workspace_docx_writer.py` (DOCX student copy). The native body
  (`native_exam_body.py`) stores five marks (bold, italic, underline, superscript,
  subscript), a heading level per paragraph and hard breaks as `"\n"`.
- Choice, ordering-step and matching-grid text print through `body_plain_text`,
  which drops the marks.
- The print HTML escapes `"\n"` into the paragraph text with no `white-space` rule,
  so a hard break collapses to a space in the PDF and the preview. python-docx
  already turns `"\n"` into `w:br` in the DOCX.
- Paragraph space: the editor sets `.xw-richtext__surface p { margin: 0 }`; print body
  paragraphs get 2 mm after (`PARAGRAPH_SPACING`) at 12 pt and line-height 1.5. The
  Word chunker keeps only paragraphs with text or a drawing
  (`exam_workspace_docx_chunker.py`) and never reads Word paragraph spacing, so the
  paragraph boundary survives the import and the blank line does not.

## Contract Inputs

- The AI conversion already copies marks from the source Word runs by code
  (`source_formatting.py`); the editor shows them. No conversion change.
- The QTI export already maps the five marks to `strong`, `em`, `u`, `sup`, `sub`
  (`examnet_qti_rich_text.MARK_ELEMENT_NAMES`); the print HTML reuses that table.
- A parallel lead (TASK-SKRIPT-41-02-06) owns the exam workspace drawer, open path
  and guest host; this task touches none of them and keeps its editor CSS in
  `ExamWorkspaceRichTextEditor.vue`.

## Core Vertical And Performance

One native exam whose instruction holds bold words and two paragraphs renders to a
print PDF with the bold words bold and visible space between the paragraphs, and to a
DOCX with bold runs. No performance concern: rendering stays linear in the runs.

## Validation

- Fail-first backend tests: the print document keeps marks; the print HTML wraps
  marked runs in their elements, renders a hard break as `br` and gives body
  paragraphs the body spacing; the DOCX writer writes bold, italic, underline,
  superscript and subscript runs and the body spacing.
- Fail-first frontend test for the editor paragraph spacing rule (thin by nature:
  CSS; the visual proof is the staging walk).
- `pdm run lint`, `pdm run typecheck`, the focused backend test files,
  `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run fe-build`.
- One rendered print PDF page from a sample with bold words and two paragraphs,
  saved as an image in the retained root's `evidence/`.
- One domain suite run after the orchestrator's go; the Mac walks it on staging.

## Stop Conditions

- The fix needs a change to the AI conversion or the Word import.
- The fix needs a file owned by TASK-SKRIPT-41-02-06.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                          |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Print carries all five stored marks in the print PDF, the preview and the DOCX. `PrintText` gets a required `marks` field with no default; every construction site states its marks. Generated text (points, bracketed inline-choice options, header detail lines) carries no marks.           |
| D2  | A hard break inside a printed text run renders as `br` in the print HTML. The DOCX keeps python-docx's `w:br`.                                                                                                                                                                                 |
| D3  | Paragraph space lives in layout, not content: the import keeps dropping empty Word paragraphs, and no conversion change is made.                                                                                                                                                               |
| D4  | The full exam editor gives consecutive paragraphs and headings a 1rem top margin (about the print's 4 mm; user 2026-10-20 via orchestrator: a matching gap in the full editor); the compact editor (choice and entry fields) stays tight. The rule lives in `ExamWorkspaceRichTextEditor.vue`. |
| D5  | Print body and gap-line paragraphs get their own body paragraph spacing in the house template; header detail lines and answer-key lines keep `PARAGRAPH_SPACING`. The new `BODY_PARAGRAPH_SPACING` is 0 mm before and 4 mm after (user 2026-10-20 via orchestrator).                           |
| D6  | Option, ordering-step and matching-grid text carry their marks too (user 2026-10-20 via orchestrator): `PrintOption` and `PrintGrid` cells hold text runs instead of plain strings; a multi-paragraph entry joins its paragraphs with a hard break. Facit lines stay plain text.               |
| D7  | Body heading paragraphs (heading level 1-3 inside a question, instruction or entry) print bold at body size (user 2026-10-20 via orchestrator): the print document builder adds `bold` to their text runs' marks; renderers need no heading branch.                                            |
| D8  | Edge-case rule (user, 2026-10-20): no guards beyond the likely cases; no handling for marks the native model cannot store.                                                                                                                                                                     |
