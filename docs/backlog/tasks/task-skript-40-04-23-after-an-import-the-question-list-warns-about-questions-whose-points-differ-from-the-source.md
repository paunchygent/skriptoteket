---
type: task
id: TASK-SKRIPT-40-04-23
title: After an import the question list warns about questions whose points differ from the source
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
  - 'Right after an import, when one or more questions'' points differ from the points the source printed for them, the question-list panel shows one line: "{N} frågor avviker från provtexten" (singular "1 fråga avviker från provtexten")'
  - 'Those questions'' points show amber in the list row meta and "Provtexten: {n} p" shows next to their Poäng field; Visa frågorna steps through them one at a time, and Avfärda hides the line and every mark in one click'
  - 'Nothing is saved: opening another exam, reloading or reopening the exam never shows the warning again, and the 40-04-10 exam and part total lines are unchanged'
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

User decision 2026-10-21, relayed by the Mac orchestrator (the user answered "yes" to terms P1-P6 below). Right after an import, the teacher is told when questions carry points that differ from the points the source printed for them, so they can compare those questions with the source while the import is fresh. The warning is informational and is never saved. In the user's words: "informational rather than something critical to save … You want to know it when you import it and when it's fresh. Then is the time to be warned about mismatches. After that, it's no longer an issue."

The task builds on TASK-SKRIPT-40-04-10: the per-question `source_points`, the question-list panel's floating note lines and their layout rules (T11), and the existing amber mark in the question list. It also answers the conflicting-question-totals question raised by the TASK-SKRIPT-39-04-11 tail review; 39-04-11's code does not change.

Non-goals: storing a dismissal or a "seen" flag; showing the warning after the import's workspace session; changing the 40-04-10 exam and part total lines.

## Contract Inputs

- TASK-SKRIPT-40-04-10 and its decided terms T5, T7 and T11 (`docs/backlog/tasks/task-skript-40-04-10-teachers-see-which-questions-and-parts-cause-a-printed-total-difference-and-can-dismiss-it.md`).
- TASK-SKRIPT-39-04-11 tail review, non-authorizing question on conflicting question totals (Hemma retained root `01a15f48-0f71-77ba-b7df-f48c8e838efb`, `evidence/reviews/task-skript-39-04-11-tail-review.md`).
- The Mac orchestrator will show the user a mock before a lead is assigned.

## Core Vertical And Performance

A conversion finishes and its questions open in the workspace. The workspace compares each question's points with its `source_points`. If one or more differ, the question-list panel shows the line, the differing questions carry the amber mark, "Visa frågorna" steps through them, and "Avfärda" clears the line and the marks. The comparison runs once per import over the exam's questions in the browser; no request and no stored state is added.

## Validation

- Focused Vitest: the line and its count appear right after an import with one or more differing questions, including a question whose source printed two different values, an exam whose totals add up, and an exam with no printed total; the line does not appear with no differing question; the amber marks; "Visa frågorna" stepping one question at a time; "Avfärda" clearing the line and every mark in one click; no line after opening another exam, reloading or reopening the exam; the 40-04-10 exam and part total lines unchanged.
- Behaviour: a staging walk by the Mac orchestrator with an exam whose questions differ from the printed points.

## Stop Conditions

- Stop and report if `source_points` cannot tell a question whose source printed two different values from one whose source printed one value.
- Stop and report if the line cannot sit with the existing note lines under 40-04-10 T11 without the list moving.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| P1  | Only right after an import: when a conversion finishes and its questions open in the workspace, and one or more questions' points differ from the points the source printed for that question (`source_points`), the question-list panel shows one line: "{N} frågor avviker från provtexten" (singular "1 fråga avviker från provtexten"). A question whose source printed two different values counts as differing, because no single printed value matches. The line shows even when the exam and part totals add up, and when the source prints no total.                                                                                                                                                                                                            |
| P2  | The differing questions' points show amber in the question-list row meta, for example "Fritext · 5 p". Inside a differing question, "Provtexten: {n} p" sits next to the Poäng field. A "Visa frågorna" glyph (shared `continue`) after the line steps through the differing questions one at a time, so the teacher can compare each with its original text in the existing Import view (user approval of the mock, 2026-10-21: "Approve, shorter text").                                                                                                                                                                                                                                                                                                               |
| P3  | An "Avfärda" glyph after "Visa frågorna", a close (✕) glyph from the shared catalogue, hides the line and every amber mark in one click.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| P4  | Nothing is saved: no stored dismissal and no stored "seen" flag. The warning exists only in the open workspace for that import. Opening another exam, reloading or reopening the exam later never shows it again.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| P5  | The existing exam and part total lines from TASK-SKRIPT-40-04-10 ("Provtexten säger N p, frågorna ger M p.", Godta, Visa frågorna) are unchanged.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| P6  | This supersedes 40-04-10 T5's "no per-question rows" and T7's "no dismiss" for this import-time line only.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| P7  | The planner decides, without a user gate, how the line sits with the existing floating note lines under 40-04-10 T11, and which shared close glyph is "Avfärda" if the catalogue has more than one; any copy beyond P1 and P2 goes through `huleedu-ui-design`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| P8  | Two printed values count (user choice "Count it", 2026-10-21, relayed by the Mac orchestrator): when a DOCX question's own lines print two or more different values, the import keeps those values on the native exam document as `conflicting_source_points` (in print order; `source_points` is then null) in document version `native_exam_document_v11`, with no reader or upgrade step for v10 (ADR-SKRIPT-0093 before release; no data migration). The import line counts that question, its row meta shows amber, Visa frågorna steps to it, and its hint names every printed value: "Provtexten: 4 p och 5 p" (three values: "Provtexten: 4 p, 2,5 p och 3 p"). The 40-04-10 rule is unchanged (P5). DigiExam and QTI carry one max_score each and never set it. |
| P9  | Problem rows (user choice "Leave as is", 2026-10-21, relayed by the Mac orchestrator): a row that shows a problem text instead of points, for example "facit ej granskat", gets no amber points; the line's count, Visa frågorna and the Poäng hint cover it. No change.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |

## Progress

### 2026-10-21 (Hemma orchestrator)

- The user approved the mock (Mac `.artifacts/mock-points-mismatch-warning/`) with shorter copy ("Approve, shorter text", relayed by the Mac orchestrator): P1 copy, P2 amber row meta and the "Provtexten: {n} p" hint, P3 close glyph. The task is ready and a lead is assigned; the staging walk goes to the Mac orchestrator after merge.

### 2026-10-21 (implementation lead, branch `codex/task-skript-40-04-23`)

- Started from main 99b86291; status in_progress. Retained root `01a15ff0-a322-73b4-83e9-d7209f112e84`, evidence under `evidence/lead-40-04-23/`.
- Stop condition 1 reached: a DOCX question whose own lines print two different values gets `PrintedQuestion(prints=True, points=None)` and never passes `with_question_points`, so its `source_points` stays the model's reading (a single number or null), the same as a one-value print or no print; no review reason or build event marks it (probe `evidence/lead-40-04-23/probe_two_value_source_points.log`). Reported to the parent; the two-value case is blocked, the one-value cases proceed.
- P7 decisions (lead): the import line is the first line of the existing floating stack (T11), so the printed-total lines keep their place right above Totalt and neither the list nor its end room changes; "Avfärda" uses the catalogue's one close glyph `close` (lucide X), as `ExamWorkspaceInlineNotice` does.
- Built for single-value prints: `examWorkspaceSourcePointsDiffer` (shared with the 40-04-10 rule, which is unchanged), `examWorkspaceImportPoints` (ids in list order, wrap-around stepping, copy), `useExamWorkspaceImportPoints` (in-memory state: an import started here shows once its exam is open and no import or conversion runs; any open, Avfärda or a reload ends it), the list line and amber row points (unit A), the "Provtexten: {n} p" hint by injection (unit B). The count follows the open copy, so a corrected question leaves the count.
- Proof: fail-first and passing logs per unit under `evidence/lead-40-04-23/`; view slice `ExamWorkspaceImportPointsSlice.spec.ts` fails 9/9 without the view wiring and catches a removed open-clear; exam-workspace domain 335 files, 2527 tests passed; fe-type-check and fe-lint clean.

### 2026-10-21 (implementation lead, two-value follow-up)

- The user chose "Count it" (P8) and "Leave as is" (P9) with full context, relayed by the Mac orchestrator; stop condition 1 is resolved by P8. Evidence under `evidence/two-value/` in retained root `01a15ff0-a322-73b4-83e9-d7209f112e84`.
- Built: `PrintedQuestion.values` and `apply_printed_points` put a two-value question's printed values on its item as `conflicting_source_points` with `source_points` null; `NativeExamItem` validates that shape; `native_exam_document_v11` with the oldest readable version raised to 11 and the v11 sample replacing the v10 one (the 74adf10e2441 migration test keeps its own v10 copy). Frontend: `examWorkspaceSourcePointsConflict` joins the import-line rule only (40-04-10 unchanged) and `examWorkspaceSourcePointsHintText` gives "Provtexten: 4 p och 5 p".
- Proof (fail-first and passing logs under `evidence/two-value/`): backend 2714 passed, exam-index and 74adf10e2441 integration 10 passed, lint and typecheck clean; frontend exam-workspace domain 355 files, 2797 tests passed, fe-type-check and fe-lint clean.

### 2026-10-21 (implementation lead, review repair)

- Repaired review F1 and F2 (`evidence/reviews/review-40-04-23.md`); evidence under `evidence/review-repair/` in retained root `01a15ff0-a322-73b4-83e9-d7209f112e84`. F1: `replacement_item` and `source_review_item` now take what a retried question keeps from one helper, `_kept_from_original`, which also keeps a saved `conflicting_source_points` with `source_points` null, so reconverting a question and its source-review fallback both keep the printed conflict. F2: the enrichment status line moved to `ExamWorkspaceEnrichmentNotice.vue` and the conflict reload to `useExamWorkspaceDocumentReload.ts`; `ExamWorkspaceView.vue` is 494 lines and `useExamWorkspaceDocument.ts` 470, behaviour unchanged.

### 2026-10-21 (Hemma orchestrator, review admission)

- Independent review of the whole task (Pi ruthless-reviewer `dd95a00e`, record `evidence/reviews/review-40-04-23.md` in retained root `01a15ff0-a322-73b4-83e9-d7209f112e84`): changes_requested with two medium findings, F1 (a retried question dropped its printed conflict) and F2 (two files above 500 lines). The rest of the task passed review. The lead's residuals were judged not blocking: no end-to-end two-value DOCX test, staging exams unreadable after the v11 bump, a possible false amber row, and the acceptance wording behind P8.
- F1 and F2 were repaired in `5e4649b3a` and admitted by the Hemma orchestrator on the lead's focused proof (F1 fail-first logs; backend 4527 passed; frontend exam-workspace domain 2797 passed; lint, typecheck, fe-type-check, fe-lint and docs-validate clean). Medium repairs need no rereview. Next: merge to main, the staging walk by the Mac from a fresh DOCX import, then user closure.

### 2026-10-21 (Hemma orchestrator, staging walk)

- The Mac staging walk at `87ab4573`, repeated at `25c4ac01` with the proof admin and a fresh DOCX (Mac `.artifacts/staging-walk-40-04-23/walk-record.md`), passed these checks:
  - the line "1 fråga avviker från provtexten";
  - amber points on the differing row only;
  - the hint "Provtexten: 2,5 p och 3 p";
  - Visa frågorna stepping and wrapping;
  - Avfärda clearing everything in one click;
  - a reload ending the warning;
  - later edits adding no line.
- Open walk findings for a repair unit:
  - W1, against P8: a question printing "(4 p)" in its heading and "(3 poäng)" in its text imported as "Ej konverterad" with 3 p. It had `source_points` 3 and `conflicting_source_points` [], kept the heading line in its body, and was neither counted nor hinted. A two-value question that fails conversion escapes the warning.
  - W2, for the lead to judge against P8: a question printing heading "(4 p)" plus parts "(2,5 p)" and "(3 p)" has 4 p and `conflicting_source_points` [2.5, 3]. The heading value is missing from the conflict list and the hint.
- Not exercised: the single-value hint, the three-value form, and a differing row that shows a problem text.

### 2026-10-21 (implementation lead, walk repair W1 and W2)

- One mechanism caused both findings. A Word heading such as "Fråga 1 (4 p)" carries no part, exam or question label, so `printed_points_plan` makes it a part over its one question. Its value was the part total and never reached the question's printed values: the walk's Fråga 1 had values (3) and Fråga 2 had (2,5, 3). W1's failed conversion did not cause the miss; a converted Fråga 1 missed the warning the same way.
- W2 judgement: P8 settles it. P8's three-value example "Provtexten: 4 p, 2,5 p och 3 p" is the walk's Fråga 2, so the heading value belongs in the list. The other reading, that the heading is a total over the parts, was rejected.
- Fix: `printed_points_plan` puts the own printed total of a heading that heads only one question first in that question's `values`. `prints`, `points`, `lines`, the part totals and the scoring stay as they were. The walk's questions now get `conflicting_source_points` (4, 3) and (4, 2,5, 3). A heading-only question keeps no conflict. No frontend change.
- Proof (evidence under `evidence/walk-repair/` in retained root `01a1605f-1f41-723a-93c5-34da7477c9b1`): the staging document's items and a plan probe before and after; four walk-shape tests in `test_docx_section_points.py` fail before the fix and pass after (40 passed); exam-workspace domain 933 passed; DOCX handlers 1468 passed; lint and typecheck clean.
- Residuals: a heading whose value equals the sum of its parts (5,5 over 2,5 and 3) still counts as three values, as P8 already did for parts; a question printing only its heading total keeps `source_points` null, as before; staging's Fråga 2 import record repeats its a) and b) lines, and its converted body drops the "a)" label.
