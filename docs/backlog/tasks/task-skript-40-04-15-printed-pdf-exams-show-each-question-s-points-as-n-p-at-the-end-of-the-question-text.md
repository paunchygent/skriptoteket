---
type: task
id: TASK-SKRIPT-40-04-15
title: Printed PDF exams show each question's points as (N p) at the end of the question text
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-19'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-19'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Independent ruthless-reviewer 9aa64d69 (Pi) approved dbbb5f8d with one low finding, fixed in R3 fae44edb and admitted on focused proof (retained 01a1542c evidence/results/9aa64d69-fc20-41eb-8993-eded036ef865.json). Merged to main as df87d633; the Mac staging walk at df87d633 passed (Mac .artifacts/staging-walk-40-04-15/walk-record.md).'
task_kind: story
acceptance_criteria:
  - 'In the print preview, the student PDF, the PDF med facit and the DOCX, each question''s points print as "(N p)" at the end of its last question-text paragraph, and no separate "Poäng: N poäng" line prints'
  - 'The "PDF för Exam.net" export keeps its current import-oriented points line'
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The user ruled on 2026-10-19 (a voice transcript relayed by the Mac, then AskUserQuestion in the Hemma orchestrator session; D1-D2 and P1-P2 are the user's answers, and the orchestrator accepted the remaining terms as decided; agent-planning:user-closure-gate) that the printed exam shows a question's worth inline as "(N p)" right after the question text, instead of a separate bold "Poäng: N poäng" line. The separate line is a leftover of the Exam.net import format. Their example: student PDF Fråga 11 (screenshot `skriptoteket-mockups/pdf-points-line-2026-10-19.png`) prints the stem, "Poäng: 1 poäng", then the alternatives; it should print "… Vilket problem prövas? (1 p)" and then the alternatives (D1). The Exam.net import PDF keeps its format (D2).

Root cause, from the code at `26f84883`: `exam_print_document._question_blocks` (lines 289-349) appends one `PrintParagraph(style=POINTS)` holding `ExamExportLabels.points_line` ("Poäng: N poäng", or "Poäng: saknas" when points are missing; `exam_language_labels.py:67-70`) as the last block of the question text group. `exam_print_html.py` prints it as `p.print-points`, which the house template's `POINTS_BOLD` makes bold (`exam_print_html.py:80,105`). The DOCX writer renders the same paragraph and makes it bold (`exam_workspace_docx_writer.py:106,213`). The preview, the student PDF and the PDF med facit all render `render_print_html(build_print_document(...))` (`exam_workspace_print_preview.py:86`, `exam_workspace_export_renderer.py:169`). The Exam.net PDF is built separately by `examnet_pdf_export.native_exam_to_pdf_document` (`exam_workspace_export_renderer.py:128-148`) and never reads the print document.

The change: `_question_blocks` stops emitting the points paragraph and appends the text " (N p)" as a final `PrintText` run to the question's last text paragraph (P3-P6). `PrintParagraphStyle.POINTS`, `ExamExportLabels.points_line` and the label fields only it reads, the house template's `POINTS_BOLD`, the `p.print-points` CSS rule and the DOCX writer's points-bold branch are deleted, with no fallback (P8).

Non-goals: the Exam.net import PDF (D2); the facit criterion lines, which already print "(N p)"; import-side handling of "Poäng:" source paragraphs (TASK-SKRIPT-39-04-20).

## Contract Inputs

- User request 2026-10-19 (voice transcript relayed by the Mac) and decisions D1-D2 the same day (AskUserQuestion in the Hemma orchestrator session `944b5a5a`).
- Retained session `01a1542c-ba56-70ef-8ea6-2c5860b404dc`, Explorer records under `discovery/explorer/` (Q1 DOCX writer reads the print model; Q2 Exam.net PDF route; Q3 preview route; Q4 points type and paragraph fields; Q5 no sub-part points).
- TASK-SKRIPT-40-04-12 (on main): the question text group and its keep-together CSS (K8, K9, K13); its page-break tests stay green.
- TASK-SKRIPT-39-04-20 (branch `codex/task-skript-39-04-score-field-remote`): changes only `docx_source_rules.py` and `source_native_carriers.py` on the import side, so it does not conflict with this task and the merge order does not matter for code.
- Code: `src/skriptoteket/domain/curated_apps/exam_workspace/exam_print_document.py`, `exam_print_html.py`, `exam_language_labels.py`; `src/skriptoteket/domain/curated_apps/exam_conversion/exam_print_house_template.py`; `src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/exam_workspace_docx_writer.py`.
- `NativeExamItem.points` is `int | float | None`, nonnegative and finite (`native_exam_item.py:69,96-114`); `NativeParagraph` has `segments` and `heading_level` only, with no list field (`native_exam_body.py:93-98`); items have no sub-parts with their own points.

## Core Vertical And Performance

The core vertical is one question's text group in the print document model, rendered by the HTML renderer for the preview and both PDFs, and by the DOCX writer (P1). No performance concern: the change replaces one paragraph with one run.

Units, one fresh junior each, in order:

1. Fail-first tests. Add `tests/unit/domain/curated_apps/exam_workspace/test_exam_print_inline_points.py`: build native items, run `build_print_document` and `render_print_html` for STUDENT and FACIT, and assert the Validation cases on the rendered HTML. Add the DOCX case (P1) and the Exam.net unchanged case. The inline cases fail on `26f84883`.
2. Implementation. Change `_question_blocks`, delete the items listed under P8, and update the existing tests that assert "Poäng: N poäng" or `PrintParagraphStyle.POINTS` in the print document, the print HTML, the page-break tests and the DOCX writer tests. Done when unit 1's tests and the updated focused files pass.

## Validation

Focused tests only:

- `tests/unit/domain/curated_apps/exam_workspace/test_exam_print_inline_points.py` (new, fail-first), STUDENT and FACIT, on the rendered print HTML:
  - a single-paragraph stem: the last `p.print-body` ends with " (1 p)";
  - a multi-paragraph stem: only the last text paragraph carries "(N p)", the earlier ones do not;
  - a choice question: "(1 p)" ends the stem paragraph inside `div.print-question-text`, before `div.print-options`;
  - a free-text question: "(N p)" ends the stem, before `div.writing-area`;
  - a gap-line last paragraph: "(N p)" follows its last blank;
  - a question with no text paragraph: the heading reads "Fråga N (M p)" (P5);
  - 0 points prints "(0 p)"; 1.5 points prints "(1,5 p)";
  - missing points: no points text anywhere in the question, heading unchanged (P2);
  - no "Poäng:" and no `print-points` anywhere in the student, facit or preview HTML;
  - the Exam.net PDF document for the same exam still carries its points line, unchanged.
- The DOCX writer prints the same "(N p)" at the end of the last text paragraph and no "Poäng:" paragraph (P1).
- Updated: `test_exam_print_document.py`, `test_exam_print_html.py`, `test_exam_print_document_answer_forms.py`, `tests/unit/infrastructure/curated_apps/test_exam_print_page_breaks.py` (green, with the omprov Fråga 3 fixture asserting "(4 p)" in place of "Poäng: 4 poäng"), and the DOCX writer test files that assert the points line.
- `pdm run lint` and `pdm run typecheck`.
- One domain suite for the exam workspace at the end, after the orchestrator's go.
- Staging walk with the exam converter output: the Förhandsgranska preview, the student PDF and the PDF med facit show "(N p)" at the end of each question's text and no "Poäng:" line.

## Stop Conditions

- Removing the points paragraph changes the page-break behaviour the 40-04-12 tests guard: stop and return the rendered evidence.
- The Exam.net PDF output changes: stop.
- A printed question carries points in a place this contract does not name: stop and return the case.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                            |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| D1  | A question's points print as "(N p)" right after the question text, such as "… Vilket problem prövas? (1 p)" (user 2026-10-19).                                                                                                                  |
| D2  | The "PDF för Exam.net" export keeps its import-oriented points line; only the student PDF, the PDF med facit and the print preview change (user 2026-10-19).                                                                                     |
| P1  | The DOCX shows the same inline "(N p)" from the shared print model; there is no DOCX-only points path (user 2026-10-19, AskUserQuestion: "Yes, inline").                                                                                         |
| P2  | A question with missing points prints no points text in the preview, the student PDF, the facit or the DOCX, and its heading is unchanged (user 2026-10-19, AskUserQuestion: "Nothing").                                                         |
| P3  | The text is one space and "(N p)", plain (not bold), appended as the last run of the question's last text paragraph (body or gap line), after any blank or picture (orchestrator-accepted default 2026-10-19).                                   |
| P4  | When the body ends in an answer-line paragraph (ruled line), "(N p)" goes on the last text paragraph before it.                                                                                                                                  |
| P5  | When the question has no text paragraph, "(N p)" goes at the end of the question heading, such as "Fråga 3 (2 p)".                                                                                                                               |
| P6  | Whole points print without decimals, 0 prints "(0 p)", and fractional points print with a decimal comma, such as "(1,5 p)".                                                                                                                      |
| P7  | The facit prints the points in the same place as the student copy; the facit criterion lines keep their own "(N p)".                                                                                                                             |
| P8  | Deleted with no fallback or alias: `PrintParagraphStyle.POINTS`, `ExamExportLabels.points_line` and the label fields only it reads, `POINTS_BOLD` in the house template, the `p.print-points` CSS rule and the DOCX writer's points-bold branch. |
| P9  | The 40-04-12 keep-together rules are unchanged; the points now sit inside the last text paragraph, which the text group already keeps together.                                                                                                  |
| P10 | TASK-SKRIPT-39-04-20 touches only import-side files and has no merge-order dependency on this task.                                                                                                                                              |

## Resume here

2026-10-19: done. Lead `600fa5a8` built it (units `5c0edd33`, `1f7558d3`, R1 `b3fa0683`, R2 `bba2cf09`, R3 `fae44edb`); review 9aa64d69 approved; merged to main as `df87d633`.

Staging walk at `df87d633` (the Mac, `.artifacts/staging-walk-40-04-15/walk-record.md`): PASS.
- Student PDF, PDF med facit and DOCX: no "Poäng:" lines and 24 inline markers, one per question; "(1,5 p)" uses a decimal comma and "(0 p)" prints; the total reads "Totalt: 35,5 poäng".
- Förhandsgranska shows the same inline markers (visual check, the preview is page images).
- PDF för Exam.net is unchanged: 24 "Poäng" lines, no inline markers.
- TASK-SKRIPT-40-04-12 keep-together still holds; page counts 8 and 9 match the revision-1 export.

Walk observations outside this task:
- A question with blank points cannot be exported (422 `missing_points`), so the no-points case was walked with 0 p.
- One first save showed "Sparat" but did not persist after a reload; not reproduced, and later saves at revisions 2-4 persisted.
- Page 8 of the student PDF holds only the last two writing lines of Fråga 24; the export did this before, and 40-04-12 does not cover writing lines.
- Source points wording left in imported stems ("(1 point) (1 p)") is TASK-SKRIPT-39-04-21's scope.
