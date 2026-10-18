---
type: task
id: TASK-SKRIPT-39-04-15
title: Left-out check covers the own chunks an item lists, by source alignment, never
  by wording
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-18'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- Every own chunk a converted item lists is checked like an unlisted one; Part 3 Question
  4 and q8 of the v14 chapter_4 replay are marked; every other replay difference is
  classified
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

TASK-SKRIPT-39-04-14 D4 marks a converted item's left-out own chunk under the check
mark (D41) when no body paragraph, choice or matching entry is aligned to it. Admission
(`_with_left_out` in `exam_workspace_docx_build_admission`) applies it only to own chunks
no item lists (`state.pending`). A chunk the item lists is never checked.

This task extends the check (`docx_own_instructions.left_out_chunks`) to every own chunk
the item lists. A listed chunk is held unmarked when it is an answer or facit line, a
points line, the question's grouped key, a chunk the grouping marks as governing, or an
instruction that section placement places. Decisions read the source alignment and the
source classification only, never the reply's wording.

## Contract Inputs

- Finding: TASK-SKRIPT-39-04-14 Validation, "Drop audit" (2026-10-18), defect 2:
  chapter 4 Part 3 Question 4 loses its word bank, "Use the best word or phrase." and
  "Two words are extra." (`v14`, live runs 1-3); q8 (`v14`) carries q7's stem with q8's
  choices and key. Mac parent contract, user request 2026-10-18.
- Probe at `6e3453b2e` (retained root `01a14f3e-12df-7020-8c18-18ad39a131cf`,
  `evidence/probes/`): both items are aligned to the chunk they shorten. Question 4
  lists `body:0129`-`body:0131`; its body is aligned to `body:0129` and `body:0130`.
  The word bank, the instruction and the gap sentence are one source paragraph,
  `body:0130`. q8 lists `body:0028`-`body:0029`; its body paragraph is aligned to
  `body:0028` and its choices to `body:0029`. The body alignment covers 35% of
  `body:0130`'s visible source characters and 30% of `body:0028`'s.

## Core Vertical And Performance

Admission reads the alignment each built item already carries; no new data is produced.

## Validation

- Adversarial unit tests: a listed word-bank chunk no paragraph shows is marked; a listed
  chunk a paragraph shows is not marked; a listed facit line is not marked.
- The ten recorded replays (eight `docx_key_provenance_v14` exams and the two
  `docx_user_exams`): the v14 chapter_4 replay marks Part 3 Question 4 and q8; every
  other difference is classified.
- On Hemma: `PYTHONHASHSEED=0 pdm run test-parallel tests/unit/application/curated_apps tests/unit/domain/curated_apps tests/unit/web -q -p no:randomly`,
  `pdm run lint`, `pdm run typecheck`, `pdm run docs-validate`.

## Stop Conditions

- OPEN (escalated to the parent 2026-10-18): the chunk-level rule cannot mark Question 4
  or q8, because a body paragraph is aligned to each chunk they shorten (Contract
  Inputs). Marking them requires reading how much of an aligned chunk the alignment
  covers, which reverses TASK-SKRIPT-39-04-14 D7 (user-accepted: a sentence dropped
  inside an aligned paragraph is not flagged). Implementation waits for the decision.
- A replay difference that is not a proven fix goes to the parent before merge.
- Task 1 (gap paragraphs built from the source paragraph) merges first; this branch
  merges `origin/main` when the parent says it has landed, and the replays run again.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | The left-out check runs on every own chunk of the question a converted item lists, as well as on the unlisted ones it already checks. |
| D2  | A listed chunk is never marked when it is a source answer or facit line (`answer_line`), a points line (`is_points_line`), a grouped key (`state.grouped_keys`), a chunk the grouping marks as governing, or an instruction that section placement places. |
| D3  | Marking rule for a listed chunk: open, escalated to the parent 2026-10-18 (Stop Conditions). |
| D4  | Decisions read the source alignment and the source classification only; no reply wording is compared, and no fallback reads wording. |
| D5  | Owning story is ST-SKRIPT-39-04; the task builds on TASK-SKRIPT-39-04-14 at `6e3453b2e` and merges after Task 1. |
