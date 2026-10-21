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

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P1  | Only right after an import: when a conversion finishes and its questions open in the workspace, and one or more questions' points differ from the points the source printed for that question (`source_points`), the question-list panel shows one line: "{N} frågor avviker från provtexten" (singular "1 fråga avviker från provtexten"). A question whose source printed two different values counts as differing, because no single printed value matches. The line shows even when the exam and part totals add up, and when the source prints no total. |
| P2  | The differing questions' points show amber in the question-list row meta, for example "Fritext · 5 p". Inside a differing question, "Provtexten: {n} p" sits next to the Poäng field. A "Visa frågorna" glyph (shared `continue`) after the line steps through the differing questions one at a time, so the teacher can compare each with its original text in the existing Import view (user approval of the mock, 2026-10-21: "Approve, shorter text").                                                                                                    |
| P3  | An "Avfärda" glyph after "Visa frågorna", a close (✕) glyph from the shared catalogue, hides the line and every amber mark in one click.                                                                                                                                                                                                                                                                                                                                                                                                                      |
| P4  | Nothing is saved: no stored dismissal and no stored "seen" flag. The warning exists only in the open workspace for that import. Opening another exam, reloading or reopening the exam later never shows it again.                                                                                                                                                                                                                                                                                                                                             |
| P5  | The existing exam and part total lines from TASK-SKRIPT-40-04-10 ("Provtexten säger N p, frågorna ger M p.", Godta, Visa frågorna) are unchanged.                                                                                                                                                                                                                                                                                                                                                                                                             |
| P6  | This supersedes 40-04-10 T5's "no per-question rows" and T7's "no dismiss" for this import-time line only.                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| P7  | The planner decides, without a user gate, how the line sits with the existing floating note lines under 40-04-10 T11, and which shared close glyph is "Avfärda" if the catalogue has more than one; any copy beyond P1 and P2 goes through `huleedu-ui-design`.                                                                                                                                                                                                                                                                                               |

## Progress

### 2026-10-21 (Hemma orchestrator)

- The user approved the mock (Mac `.artifacts/mock-points-mismatch-warning/`) with shorter copy ("Approve, shorter text", relayed by the Mac orchestrator): P1 copy, P2 amber row meta and the "Provtexten: {n} p" hint, P3 close glyph. The task is ready and a lead is assigned; the staging walk goes to the Mac orchestrator after merge.

### 2026-10-21 (implementation lead, branch `codex/task-skript-40-04-23`)

- Started from main 99b86291; status in_progress. Retained root `01a15ff0-a322-73b4-83e9-d7209f112e84`, evidence under `evidence/lead-40-04-23/`.
- Stop condition 1 reached: a DOCX question whose own lines print two different values gets `PrintedQuestion(prints=True, points=None)` and never passes `with_question_points`, so its `source_points` stays the model's reading (a single number or null), the same as a one-value print or no print; no review reason or build event marks it (probe `evidence/lead-40-04-23/probe_two_value_source_points.log`). Reported to the parent; the two-value case is blocked, the one-value cases proceed.
- P7 decisions (lead): the import line is the first line of the existing floating stack (T11), so the printed-total lines keep their place right above Totalt and neither the list nor its end room changes; "Avfärda" uses the catalogue's one close glyph `close` (lucide X), as `ExamWorkspaceInlineNotice` does.
- Built for single-value prints: `examWorkspaceSourcePointsDiffer` (shared with the 40-04-10 rule, which is unchanged), `examWorkspaceImportPoints` (ids in list order, wrap-around stepping, copy), `useExamWorkspaceImportPoints` (in-memory state: an import started here shows once its exam is open and no import or conversion runs; any open, Avfärda or a reload ends it), the list line and amber row points (unit A), the "Provtexten: {n} p" hint by injection (unit B). The count follows the open copy, so a corrected question leaves the count.
- Proof: fail-first and passing logs per unit under `evidence/lead-40-04-23/`; view slice `ExamWorkspaceImportPointsSlice.spec.ts` fails 9/9 without the view wiring and catches a removed open-clear; exam-workspace domain 335 files, 2527 tests passed; fe-type-check and fe-lint clean.
