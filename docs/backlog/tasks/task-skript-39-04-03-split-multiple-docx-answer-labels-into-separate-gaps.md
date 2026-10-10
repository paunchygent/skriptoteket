---
type: task
id: TASK-SKRIPT-39-04-03
title: Split multiple DOCX answer labels into separate gaps
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-10'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- A DOCX facit line with several answer labels imports as one gap per label, so each
  accepted value holds only its own answer and Exam.net scores a correct student answer
  as correct
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The DOCX importer turns each facit sub-line into a gap-fill gap. When a line
carries more than one answer label, for example
`a) Jag vet att det regnar. Bisats: att det regnar Typ: att-sats`, the
importer today keeps everything after the first label as one accepted value
(`att det regnar Typ: att-sats`) and flags the item with
`multiple_answer_labels_detected`. Exam.net then marks the correct student
answer `att det regnar` as wrong. The 2026-10-10 staging walk of
TASK-SKRIPT-39-04-02 found the same defect in the real fixture
(`vid skolan Satsdel: adverbial`).

- Each answer label on a sub-line becomes its own gap. The visible question
  text keeps every label in order, followed by its gap:
  `a) Jag vet att det regnar. Bisats: [gap] Typ: [gap]`.
- Each gap's accepted value is the text between its label and the next label
  or the end of the line, trimmed.
- An item whose labels all split cleanly no longer carries
  `multiple_answer_labels_detected`.
- A label with no answer text after it still becomes a gap, with no
  accepted value. The question stays a gap-fill item (it no longer falls
  back to free text), is review_required, and shows the missing answer at
  the gap. The existing partial-key save rule then refuses a teacher save
  in Swedish until the teacher types the answer. The import itself must
  still create and open the document.
- Points, confidence and the other review reasons keep their current rules.

## Contract Inputs

- `src/skriptoteket/domain/curated_apps/exam_workspace/docx_extraction.py`:
  `_split_answer_label` (line 99), `_build_item` (line 134), and the
  `multiple_answer_labels_detected` reason (line 167).
- `tests/unit/domain/curated_apps/exam_workspace/test_docx_extraction.py`:
  line 113 asserts today's merged value and changes with this task.
- Fixture `tests/fixtures/exam_conversion/real_inputs/grammatik_omprov_examnet_import_med_facit.docx`.
- TASK-SKRIPT-39-04-01 (DOCX walking skeleton) and TASK-SKRIPT-39-04-02
  (walk finding W9).

## Core Vertical And Performance

`DOCX facit line with several labels -> one gap per label -> teacher sees
each gap as its own chip -> QTI export holds one keyed text entry per gap`.

- Extraction stays deterministic and in-process; no new LLM step.
- No new backend state or endpoints.

## Validation

- Unit tests: two labels, three labels, a trailing label without an
  answer (gap-fill with one empty gap, review_required), and the
  single-label case unchanged. The line 113 assertion becomes two gaps
  `("att det regnar",)` and `("att-sats",)`.
- Fixture test on the real DOCX: no gap's accepted value contains a second
  answer label.
- QTI export of the fixture passes the existing fail-closed validators, with
  one `textEntryInteraction` and one `correctResponse` per gap.
- Backend gates per `AGENTS.md`: lint, typecheck, focused tests.
- Agent-driven browser walk on Hemma staging: import the fixture, check that
  the former merged items show separate chips, export QTI and inspect it.

## Stop Conditions

- Stop if splitting would change items without multiple labels.
- Stop if a label pattern in the fixture cannot be split without guessing;
  keep it review_required and report it.
- Stop if the import path refuses to persist a document with an empty gap;
  report it instead of weakening the save rule.
- Production acceptance remains user-owned.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| F1 | Fix the merged facit value as its own task under ST-SKRIPT-39-04 (user decision 2026-10-10). |
| F2 | Each answer label on a facit line becomes its own gap with only its own answer as accepted value (user decision 2026-10-10). |
| F3 | A label without answer text becomes an empty gap; the item stays gap-fill and review_required, and the teacher must type the answer before saving; no guessed answers and no free-text fallback (user decision 2026-10-10). |
