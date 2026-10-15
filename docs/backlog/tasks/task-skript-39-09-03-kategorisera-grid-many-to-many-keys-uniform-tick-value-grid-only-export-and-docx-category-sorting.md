---
type: task
id: TASK-SKRIPT-39-09-03
title: 'Kategorisera grid: many-to-many keys, uniform tick value, grid-only export
  and DOCX category sorting'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-15'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-15'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Pi ruthless-reviewer (gpt-6.1-sol) requested changes on c6e0e28c and 0fa48e19, approved 07bede41 (merged 2ebed4cb). Live eval found valid type_conflict replies rejected by the key validator; repair 7c8c6bd7 approved and merged. Walk at 7c8c6bd7: kategorisera exam converted to two Kategorisera grids with vila keyed to two columns; tick 0.5 gave 2 points; export imported into Exam.net as 5339116, categorizingItems 2p with four 0.5 rules and answers [1,2]. Records in Skriptoteket session 01a13c92-d70e-765f-ae36-b6583539e201 evidence/reviews/TASK-SKRIPT-39-09-03/ and evidence/walk/TASK-SKRIPT-39-09-03/walk-7c8c6bd7.md.'
task_kind: story
acceptance_criteria:
- A teacher keys a many-to-many Kategorisera grid with one tick value, exports it,
  and Exam.net imports it as categorizingItems with every tick keyed at that value;
  DOCX conversion produces such grids and the gold eval covers them
story: ST-SKRIPT-39-09
backlog_document_profile: contract-derived
---

## Implementation Contract

Delivers ST-SKRIPT-39-09 task 3 (story terms Q7–Q11; plan rows R10–R13): a
matching item is a Kategorisera grid with a many-to-many key and one tick
value, exported to Exam.net only as the grid, printed in the PDF as a tick
table, and produced by DOCX conversion from category-sorting questions.

- **Model.** A keyed matching item has at least one pair for every left entry
  (row); a right entry (column) may appear in several pairs or none; a pair
  appears at most once. The one-to-one checks in `NativeExamItem` and in the
  AI answer-key suggestion invariants are deleted. A matching item carries
  `tick_points` (positive, at most 2 decimals, default 1 for a new item); its
  `points` equal `tick_points` × the number of pairs, and validation rejects
  any other value. Other kinds carry no `tick_points`. No reader or default is
  kept for documents saved under the one-to-one rule.
- **QTI export, both lanes.** A grid is one `qti-match-interaction`: rows are
  the first `qti-simple-match-set` with `match-max` equal to the number of
  columns, columns the second with `match-max` equal to the number of rows,
  and `max-associations` rows × columns (probe V51). The response mapping
  gives every pair `tick_points`; MAXSCORE equals the points. No lane writes a
  matching item as `qti-associate-interaction` or `qti-order-interaction`.
  The DigiExam converter's matching items take the same shape with its own
  per-pair value under the task 2 rules.
- **PDF export.** A grid prints as a table with one row per left entry, one
  column per right entry and an empty box in each cell; the answer-key
  version marks each correct cell.
- **DOCX conversion.** The produced-item schema and the build prompt describe
  category sorting: rows are the entries sorted, columns the categories, and
  `match_pairs` holds every tick the answer key gives, several per row when
  the key says so. The build sets `tick_points` to the answer-key points
  divided by the ticks, rounded down to 2 decimals, sets `points` to
  `tick_points` × ticks, and marks the points estimated when the division is
  inexact or the key states no points.
- **Gold corpus.** One agent-authored teacher-style Swedish exam DOCX with at
  least two category-sorting tables (at least one row with two correct
  categories and one unused category) and an answer key is added to
  `tests/fixtures/exam_conversion/docx_corpus/` with its `.sha256` sidecar and
  its gold JSON, and is labelled as authored in the corpus README. The gold
  schema and comparator accept several pairs per row and compare pairs as sets.
- **Out of scope.** The teacher-facing name "Kategorisera", the checkbox grid
  editor, the tick-value field and the read-only points display are the
  parent's UI unit, done last. Fritext criteria, Kort svar and the export
  checklist are tasks 4–6.

## Contract Inputs

- ST-SKRIPT-39-09 terms Q7–Q11; retained plan rows R10–R13
  (`.orchestration/context/sessions/01a13c92-d70e-765f-ae36-b6583539e201/evidence/planning/ST-SKRIPT-39-09/plan.md`).
- REF-SKRIPT-RESEARCH-exam-net-qti-import-routes-per-question-type
  (Kategorisera section); probe round 13 V51, session
  `01a13be3-772e-73bb-9d8a-8cf2dd1d5df3` `evidence/probe-r13/`.
- Model: `domain/curated_apps/exam_workspace/native_exam_document.py`
  (`NativeMatchPair`, `NativeAnswerKey`, `_match_pairs_valid`,
  `_suggestion_invariants`), `answer_key_view.py` (`_validated_matching_proposal`).
- Export: `exam_workspace/examnet_qti_export.py` (`_matching_item`),
  `exam_conversion/examnet_qti_xml.py` (`_append_match_interaction`,
  `_append_associable_choice`, mapping), `exam_workspace/examnet_pdf_export.py`
  and its template.
- Conversion: `exam_workspace/docx_ai_contracts.py` (`ProducedItem`,
  `ProducedMatchPair`), `docx_ai_build.py`,
  `application/curated_apps/handlers/exam_workspace_docx_build_rounds.py`.
- Gold: `tests/fixtures/exam_conversion/docx_corpus/gold/`,
  `scripts/exam_conversion_eval/gold.py`, `compare.py`.

## Core Vertical And Performance

A teacher's workspace grid with a row keyed to two columns, an unused column
and tick value 0.5 exports as QTI; Exam.net imports it as categorizingItems
with every tick keyed at 0.5 and points 0.5 × ticks. The authored DOCX
converts to the same kind of grid and the gold eval scores it. No performance
concern: grid sizes are small.

## Validation

- Focused unit tests for the model rules (many-to-many accepted, row without a
  tick rejected, duplicate pair rejected, points ≠ tick × ticks rejected), the
  QTI grid shape and mapping, the PDF tick table, the DOCX build rounding and
  estimate flag, and the gold schema with several pairs per row, under
  `tests/unit/domain/curated_apps/exam_workspace/`,
  `tests/unit/domain/curated_apps/exam_conversion/` and
  `tests/unit/scripts/`.
- The gold-corpus eval runs over the authored exam.
- Staging walk: a grid is keyed and exported from the workspace, imported into
  Exam.net in the agent's own tab and read back through
  `/api/exams/automarked/<id>/questions` for type, ticks and points.

## Stop Conditions

- Exam.net imports a many-to-many grid with any tick unkeyed or at a value
  other than `tick_points`.
- A lane needs a matching shape other than `qti-match-interaction`.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| T1  | A matching key is many-to-many: every row has at least one correct column, a column may serve several rows or none (Q9). |
| T2  | One `tick_points` per grid, default 1; points are `tick_points` × ticks and shown read-only (Q10, R11). |
| T3  | Matching exports only as the `qti-match-interaction` grid with one mapped value per tick (Q7, V51). |
| T4  | The PDF prints a grid as a tick table; the answer-key version marks the correct cells (R13). |
| T5  | DOCX conversion produces many-to-many grids; the tick value is points ÷ ticks rounded down to 2 decimals, estimated when inexact (Q11, R12). |
| T6  | The gold corpus gains one agent-authored, labelled category-sorting exam (R10). |
| T7  | The teacher-facing name is Kategorisera; the editor UI is the parent's last unit (Q8). |
