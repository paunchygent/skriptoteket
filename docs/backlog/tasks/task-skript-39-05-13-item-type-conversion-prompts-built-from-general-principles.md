---
type: task
id: TASK-SKRIPT-39-05-13
title: Item-type conversion prompts built from general principles
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-16'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- The DOCX build prompt is a shared core plus one section per item kind, sent only
  for the kinds in the batch, stated as general principles with positive phrasing
  and short constructed examples; a live run of every corpus exam resolves the six
  ST-SKRIPT-39-05 model-quality findings without new regressions, and a staging walk
  imports one converted exam into Exam.net.
story: ST-SKRIPT-39-05
backlog_document_profile: contract-derived
---

## Implementation Contract

The DOCX build call sends the model one 190-line prompt for every batch,
whatever item kinds the batch holds. It states rules abstractly, gives no
example, and warns against things the model has no means to do. Live v14
replies show six model-quality faults that all happen inside a batch that
holds every chunk involved (replay check 2026-10-16):

- Poetry Q8 (body:0028) repeats Q7's question text.
- SA24 Q42 (body:0096) drops "Also accepted: ballanced" from the accepted
  values and the facit text; other "Also accepted" forms are missing likewise.
- Diagnostic grammar items at body:0154, body:0166 and body:0220 drop the
  bracketed source-language cue after the gap.
- Svenska grammar variant 1 Fråga 1 (body:0008) puts all its gaps at the end of
  the line instead of after the word parts they answer.
- English body:0115 needs a type_conflict follow-up whose live result is
  unverified.

The prompt becomes a shared core plus one section per item kind:

- The core states the output envelope, chunk ownership, facit position,
  points, headings, pictures, review and one recognition line per kind with
  the type_conflict rule, so a batch can still name a kind it was not given.
- Each kind section (gap_fill, choice, matching, free_text) is sent only when
  that kind is in the batch's item_kinds. It states that kind's general
  principles: what the student answers, where each answer place goes, what
  stays text, and what goes into the key and facit_text.
- Gap placement follows one principle: a gap goes where the student's answer
  belongs in reading order, directly after the smallest piece of text the
  answer is about (on a printed blank; after a word or part; after the
  sentence; on its own line below the question). One gap per facit answer;
  every word and cue the student reads stays text in its printed order.
- Rules are stated positively. A prohibition stays only where a recorded
  reply shows the model making that error. Pattern-specific rules (one
  exercise type, one language) are replaced by the general principle that
  covers them.
- Each principle carries one or two short constructed examples whose subject
  varies, never a copy of a corpus question.

## Contract Inputs

- `src/skriptoteket/application/curated_apps/handlers/exam_workspace_docx_build_rounds.py`
  (`_PROMPT`, `build_batch_request`).
- `src/skriptoteket/domain/curated_apps/exam_workspace/item_kind_boundary.py`
  (`converter_kind_rule`).
- v14 recordings `tests/fixtures/exam_conversion/docx_key_provenance_v14/` and
  the replay harness `tests/unit/application/curated_apps/handlers/docx_pipeline_replay.py`.
- Live eval `pdm run exam-conversion-eval`, run on Hemma staging as in
  TASK-SKRIPT-39-05-10.

## Core Vertical And Performance

The batch request carries the prompt assembled for its kinds; its token
estimate uses the assembled text. Every caller that builds a docx_exam build
request, including the per-question retry and the type_conflict follow-up,
gets the same assembly. A batch with fewer kinds sends a shorter prompt.

## Validation

- Focused tests: the prompt-content tests
  (`test_item_kind_boundary_and_schema.py`,
  `test_exam_workspace_docx_field_label_prompt.py`) and the recorded-corpus
  replay tests, which do not key on prompt text.
- Live eval on Hemma of every corpus exam with the task branch packet. Pass
  means each of the six findings is fixed, item by item, against the v14 replay
  output, with no new review items or lost source words elsewhere. The eval's
  gold-match line is not a criterion (user decision 2026-10-16).
- Staging walk with one affected exam and its Exam.net import.

## Stop Conditions

- A finding persists after the rewrite and its cause lies outside the prompt:
  report the evidence to the user before changing code outside the prompt.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | Shared core plus one section per item kind, sent only for the batch's item_kinds, with worked examples (user 2026-10-16). |
| D2  | Proof is a live run of the affected exams and the full corpus plus one staging walk with an Exam.net import (user 2026-10-16). |
| D3  | Rules are stated positively; prohibitions about inputs or tools the model never has are removed (user 2026-10-16). |
| D4  | General principles replace pattern-specific rules; gap placement follows the "directly after the smallest text the answer is about" principle (user 2026-10-16). |
| D5  | No gold-corpus eval metric is a criterion (user 2026-10-16). |
