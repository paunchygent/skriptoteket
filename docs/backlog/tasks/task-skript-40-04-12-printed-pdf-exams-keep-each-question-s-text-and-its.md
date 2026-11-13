---
type: task
id: TASK-SKRIPT-40-04-12
title: Printed PDF exams keep each question's text and its alternatives on one page
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-19'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: user
  decided_at: '2026-10-22'
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: 'The user closed the task on 2026-10-22 after merge 8d51a6ba, the K11 staging walk (Mac .artifacts/staging-walk-40-04-12/walk-record.md) and the K7 walk at fd2d911c: neither the student PDF nor the PDF med facit holds a line with only "/" under omprov Fråga 1c (Mac .artifacts/staging-walk-owed-2026-10-22/walk-record.md).'
task_kind: story
acceptance_criteria:
  - In the print preview and the exported student and facit PDF, no page break falls inside a question's text block (heading, instruction and problem body) or inside its choice alternatives, writing lines may split, and a block taller than one page still splits
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The user ruled on 2026-10-19 (given on the Mac, relayed by the Mac parent) that the printed PDF keeps each question's text together across page breaks. Their example of a wrong split: omprov Fråga 3 "Identifiera huvudord / Stryk under huvudordet i varje nominalfras." ends one page, and its items 1-4 and "Poäng: 4 poäng" start the next. This task makes the print preview, the student PDF and the PDF med facit follow K1-K5. The user answered the open questions on 2026-10-19 (K12-K15). The user accepted the plan as built on 2026-10-19 (AskUserQuestion in the Hemma orchestrator session; agent-planning:user-closure-gate), and the task is ready.

Root cause, from the code at `61e460f6`: a question prints as one flat `<section class="print-question">` of sibling blocks (`exam_print_html.py:197-221`, built by `exam_print_document._question_blocks`, lines 272-330): an `h3`, one `p.print-body` per body paragraph (the items are paragraphs, not a list), `p.print-points`, then the answer form (`div.writing-area`, one `p.print-option` per alternative, or `table.print-grid`). The section and its paragraphs carry no fragmentation rule, so WeasyPrint may break between any two siblings; `h3 { break-after: avoid }` only binds the heading to the first paragraph (`exam_print_html.py:65-73`). The only other rules are `break-inside: avoid` on `.print-instruction`, `.writing-line` and `.print-answer-key`.

The change: the print document model gives each question two explicit groups, the question text and the answer form (K8). The HTML wraps the text group and the alternatives in their own keep-together `div` and stops the split inside single paragraphs and alternatives (K9). The DOCX writer reads the same groups in the same order and its output stays unchanged (K6).

Non-goals: DOCX page layout (K6); the Exam.net import PDF; the stray "/" line under the last item before "Poäng", which TASK-SKRIPT-39-04-20 fixes (K7); facit answer-key placement, which keeps its current `break-inside: avoid`.

## Contract Inputs

- User ruling 2026-10-19 (rules 1-5) and the DOCX correction the same day, both relayed by the Mac parent through the Hemma orchestrator.
- Retained plan: session `01a1539d-dada-765d-a9ba-f473aed5212b`, `evidence/planning/TASK-SKRIPT-40-04-12/plan.md`; discovery under `discovery/explorer/`; WeasyPrint 69.0 probes in `evidence/probes/` (`results-2026-10-19.md`).
- TASK-SKRIPT-40-04-07 (done): the print document model, house template and preview this task changes.
- TASK-SKRIPT-39-04-20: the stray "/" fix (branch `codex/task-skript-39-04-score-field-remote`, head `02092a59`).
- Code: `src/skriptoteket/domain/curated_apps/exam_workspace/exam_print_document.py`, `exam_print_html.py`; `src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/exam_workspace_docx_writer.py`; preview and export share `render_print_html(build_print_document(...))` (`exam_workspace_print_preview.py:86`, `exam_workspace_export_renderer.py:168`).
- WeasyPrint docs (Context7 `/websites/doc_courtbouillon_weasyprint_stable`): `break-before`, `break-after`, `break-inside`, `orphans` and `widows` are supported for pages.

## Core Vertical And Performance

The core vertical is the question's two groups in the print document model, wrapped by the HTML renderer and laid out by WeasyPrint for both the preview and the export. No performance concern: the change adds wrapper elements and CSS rules to an HTML string the renderer already builds once per render.

Units, one fresh junior each, after the user accepts the plan:

1. Fail-first page-break tests. Add `tests/unit/infrastructure/curated_apps/test_exam_print_page_breaks.py`: lay out the production HTML (`build_print_document` -> `render_print_html` -> `weasyprint.HTML(string=...).render()`) for STUDENT and FACIT, reusing the box-tree walk of `test_exam_print_pdf_docx_geometry.py`. Parametrise the content before the question over a range of heights and assert the invariant on every render. Cases are listed under Validation. The K1 and K4 cases fail on `61e460f6`.
2. Model groups. `exam_print_document.py`: `PrintQuestion` carries the question text group and the answer form group (K8, K13); `exam_workspace_docx_writer.py` iterates both in order. Update `test_exam_print_document.py` and `test_exam_print_document_answer_forms.py`. Done when the existing DOCX writer and `test_exam_print_pdf_docx_geometry.py` tests pass unchanged.
3. HTML and CSS, after unit 2. `exam_print_html.py`: wrap the text group and the alternatives or ordering steps in `div` groups with `break-inside: avoid`, add `break-inside: avoid` to `p.print-body`, `p.print-option` and `table.print-grid`, and give `div.print-instruction` `break-after: avoid` so a part's instruction stays with its first question's text (K9, K12, K14, K15). Update `test_exam_print_html.py`. Done when unit 1's tests pass.

## Validation

Focused tests only:

- `tests/unit/infrastructure/curated_apps/test_exam_print_page_breaks.py` (new, fail-first), STUDENT and FACIT:
  - the omprov Fråga 3 fixture (heading, "Identifiera huvudord", "Stryk under huvudordet i varje nominalfras.", items 1-4, "Poäng: 4 poäng") placed near a page end: the heading and item 4 lay out on the same page at every tested height (K1);
  - a choice question near a page end: all alternatives lay out on one page; where the text fits and the alternatives do not, the text stays on the earlier page and the alternatives start the next (K3, K4);
  - a question whose text is taller than one page: it splits, and the split falls between paragraphs, never inside one (K5, K14);
  - a part instruction followed by a question near a page end: the instruction and the question's text lay out on the same page (K12);
  - an ordering question and a matching question near a page end: all steps, and the whole grid, lay out on one page (K15);
  - a free-text question whose writing lines cross a page end: the lines continue on the next page and the text stays whole (K2).
- `tests/unit/domain/curated_apps/exam_workspace/test_exam_print_html.py`, `test_exam_print_document.py`, `test_exam_print_document_answer_forms.py`.
- DOCX unchanged: the existing DOCX writer tests and `tests/unit/infrastructure/curated_apps/test_exam_print_pdf_docx_geometry.py`.
- `pdm run lint` and `pdm run typecheck`.
- Staging walk with the omprov exam (K11): the Förhandsgranska preview, the student PDF and the PDF med facit show Fråga 3 whole on one page and every question's alternatives on one page.
- Once TASK-SKRIPT-39-04-20 is on main, the same walk confirms no "/" line prints under Fråga 3's item 4 before "Poäng: 4 poäng" (K7).

## Stop Conditions

- WeasyPrint cannot keep the text group whole while letting the alternatives move to the next page on the production HTML: stop and return the rendered evidence.
- Keeping a group together needs a change to the DOCX output (K6): stop and return the case.
- The real omprov exam on staging prints a split that the fixture tests do not reproduce: stop and add the case before repair.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                      |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| K1  | A question's text never splits across a page break: its heading, instruction text and problem body move to the next page together.                                                                                                                                                         |
| K2  | Writing lines may split across pages; a single writing line never splits.                                                                                                                                                                                                                  |
| K3  | For choice questions the question text may end one page and the alternatives start the next, to keep page gaps small.                                                                                                                                                                      |
| K4  | A question's alternatives stay together on one page; no break falls between two alternatives and no alternative splits.                                                                                                                                                                    |
| K5  | A block taller than one page still splits.                                                                                                                                                                                                                                                 |
| K6  | The rule applies only to the PDF: the print preview, the student PDF and the PDF med facit. The DOCX gets no page breaks and no keep-with-next or keep-lines settings, because the teacher sets the layout of the editable DOCX; DOCX output stays unchanged (user correction 2026-10-19). |
| K7  | The stray "/" line under the last item before "Poäng" belongs to TASK-SKRIPT-39-04-20; this task only checks it is gone once 39-04-20 is on main.                                                                                                                                          |
| K8  | `PrintQuestion` carries two explicit groups, the question text and the answer form; the DOCX writer iterates both in order and the HTML renderer wraps each; no group is inferred from paragraph styles.                                                                                   |
| K9  | The HTML wraps the question text and a question's alternatives each in a `div` with `break-inside: avoid`; single paragraphs and alternatives get `break-inside: avoid`; groups are `div` elements of `p`, not lists.                                                                      |
| K10 | Fail-first WeasyPrint tests lay out the production HTML for STUDENT and FACIT over a range of preceding heights and assert each rule on every render.                                                                                                                                      |
| K11 | A staging walk of the preview, the student PDF and the PDF med facit with the omprov exam closes the task.                                                                                                                                                                                 |
| K12 | A part's instruction stays on the same page as its first question's text (user 2026-10-19).                                                                                                                                                                                                |
| K13 | "Poäng: N poäng" belongs to the question text group (user 2026-10-19).                                                                                                                                                                                                                     |
| K14 | A block taller than one page splits only between paragraphs, items or alternatives, never inside one, unless one paragraph is itself taller than a page (user 2026-10-19).                                                                                                                 |
| K15 | Ordering steps and the matching grid stay together on one page, like the alternatives (user 2026-10-19).                                                                                                                                                                                   |

## Resume here

2026-10-19, lead `c30dba85`: the user accepted the plan as built, and the status is ready. The code, the F1 repair and the merge of origin/main `eba9d0f2` are committed, and the focused print tests pass (389). Next: the Mac parent merges and runs the staging walk (K11), then the TASK-SKRIPT-39-04-20 "/" check once that task is on main.

## Progress

### Reconciliation 2026-10-20 (Mac parent, against main 114ca971)

- Status corrected from `ready` to `in_progress`: merged to main as `8d51a6ba` (2026-10-19). The staging walk passed K11 (`.artifacts/staging-walk-40-04-12/walk-record.md`). TASK-SKRIPT-39-04-20 is on main (`f7eeada5`), so K7 can now be checked.
- Owed: the K7 "/" check on staging, then closeout.

### 2026-10-22 (Mac orchestrator, closure)

- Closed by the user on 2026-10-22 (see `closeout_review`).
