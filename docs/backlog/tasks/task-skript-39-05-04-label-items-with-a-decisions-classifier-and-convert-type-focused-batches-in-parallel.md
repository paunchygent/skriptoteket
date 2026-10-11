---
type: task
id: TASK-SKRIPT-39-05-04
title: Label items with a Decisions classifier and convert type-focused batches in
  parallel
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-11'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- Grouping and labeling run on all eight corpus exams and their questions, subparts,
  shared-context scope and labels are checked against the source before any conversion
  change
story: ST-SKRIPT-39-05
backlog_document_profile: contract-derived
---

## Implementation Contract

DOCX conversion moves from one whole-exam call to type-focused parallel
batches, because the single call is too slow. Before conversion, two labeling
steps decide what each question is:

1. **Grouping pass.** One low-effort `gpt-6-luna` Responses call returns only
   source references: each question with its subparts, each shared
   instruction or passage with the questions it governs and its single owner,
   and the title. It writes no question text and no answers.
2. **Labeler.** One batched Decisions call gives each question one label from
   a closed set: `single_choice`, `multiple_response`, `gap_fill`,
   `free_text`, `matching`, `unsupported`, `unresolved`, with the label
   probabilities. A probability or top-two margin below the label's threshold
   sends the question to a second labeling pass with more context, and then
   to a review item. The labeler sits behind one classifier interface (label,
   score, threshold, route), so conversion reads labels the same way whatever
   produced them.
3. **Parallel conversion.** Code packs questions into batches that hold one
   type, or the two choice types together. A question and its subparts never
   split. A shared instruction or passage reaches every batch that holds a
   question it governs, as read-only context. Batches run concurrently; the
   document is assembled in source order.
4. **Recovery.** A converter that finds a question outside its batch's types
   reports a typed conflict; that question is relabeled and resent, at most
   three attempts in total.

This task first builds steps 1 and 2 and runs them on the eight corpus exams
without converting. Building step 3 and the larger measurement phases follows
a user decision on that result.

## Contract Inputs

- Architect proposal (GPT-6 Astra, 2026-10-11):
  `.orchestration/context/sessions/01a12706-566c-7480-acc3-427145283942/drafts/parallel-docx-conversion-and-conditional-labeler.md`,
  holding the label rules, starting thresholds, packing policy, cost estimate
  and the four-phase measurement plan.
- Official Decisions guide and reference, read 2026-10-11: Decisions answers
  predicate, choice and score questions with probabilities; it does not
  extract arbitrary structure, which belongs to Responses.
- Conversion principles and source-structure rules:
  TASK-SKRIPT-39-05-03. Gold files: `tests/fixtures/exam_conversion/docx_corpus/gold/`.

## Core Vertical And Performance

DOCX upload through grouping, labeling, parallel conversion and assembly to
the saved document and its QTI export. Target: at least 30% lower median
upload-to-ready time on the 53-, 73- and 104-item corpus exams than the
single call, with small exams at most 10% slower.

## Validation

- Feasibility step: grouping and labeling run once on each corpus exam;
  question and subpart boundaries, shared-context scope, ownership and labels
  are checked against the source. No conversion runs in this step.
- Gold is joined only by the evaluator after provider output; it is never an
  input to grouping, labeling, conversion or repair.
- Per-call tokens, cost and duration are recorded.

## Stop Conditions

- TASK-SKRIPT-39-05-03 is not merged; this task measures against its frozen
  result.
- The grouping pass needs to write question text or answers.
- A rule needs to name an exam, a question number or a subject term.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | Conversion runs in parallel batches; the single whole-exam call is ruled out as too slow (user decision 2026-10-11). |
| D2  | A question and its subparts never split; items under a shared instruction or passage go to their type batches and receive the shared text as read-only context, with one owner per source chunk (user decisions 2026-10-11). |
| D3  | Each batch holds one item type; only single choice and multiple response may share a batch until measurement justifies another pair (user decisions 2026-10-11). |
| D4  | Item types come from a Decisions-API labeler with probability thresholds, not code-side cue typing; a low-effort Responses grouping pass supplies the question references it labels (user decisions 2026-10-11). |
| D5  | The feasibility step runs before conversion changes; the larger measurement phases need a user decision on its result (user decision 2026-10-11). |
| D6  | Speed target: at least 30% lower median upload-to-ready on the 53-, 73- and 104-item exams; small exams at most 10% slower (user decision 2026-10-11). |
