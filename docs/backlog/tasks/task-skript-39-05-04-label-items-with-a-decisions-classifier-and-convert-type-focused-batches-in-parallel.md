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
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- Grouping and labeling run on all eight corpus exams and their questions, subparts,
  shared-context scope and labels are checked against the source before any conversion
  change
- The parallelization measurement (D26) runs the production pipeline per setting and
  reports time to first batch, time to all ready, cost and quality read as in D34
  before batch size and reasoning effort are set
- Converted batches reach the exam workspace as they finish, pending questions show
  as placeholders, and the saved document passes the assembly check against the
  grouping list before save and QTI export
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
   probabilities. A question at or above 0.95 keeps its first-pass label;
   below 0.95 a second pass (B: Responses, label only) decides alone, and
   unresolved becomes free_text until the re-tag story lands. The labeler sits behind one classifier interface (label,
   score, threshold, route), so conversion reads labels the same way whatever
   produced them.
3. **Parallel conversion.** Code packs questions into batches that hold one
   type, or the two choice types together. A question and its subparts never
   split. A shared instruction or passage reaches every batch that holds a
   question it governs, as read-only context. Batches run concurrently in two
   waves: questions accepted at 0.95 convert at once, and questions sent to B
   join second-wave batches as their labels arrive. Converted batches reach
   the editor as they finish (progressive delivery), pending questions show
   as placeholders with their source text, and the document is assembled in
   source order. Before save and QTI export, assembly checks the result
   against the grouping list: every question once, each child under its
   named parent, each instruction once, source order. Free_text questions
   carry a marking guide (rättningsmall / poängmall) in the converter schema.
4. **Recovery.** A converter that finds a question outside its batch's types
   reports a typed conflict; that question is relabeled and resent once. If it
   still conflicts, it keeps the converted item with the check-type review mark.

Step 1 has two candidates, both run in the feasibility step: the Responses
grouping pass above, and Decisions-only grouping, where a `choice` question
per source chunk labels its role (question start, subpart, shared
instruction or passage, answer key, title) and code builds the groups from
those labels. The feasibility step also tries three further Decisions inputs:
a `predicate` per answer line ("a field the student fills in, or given
text"), a `score` for item ambiguity that routes ambiguous items to more
context or a higher-effort pass, and rendered page images as labeler input.

The feasibility step also evaluates where else in the workflow a Decisions
call gives the most quality per cost and time, each measured against the same
work done today by the converter or by code:

- before conversion: chunk roles, item types, answer slots, ambiguity;
- facit attachment: which answer-key line belongs to which question;
- points: whether a printed section total governs its questions;
- after conversion: predicate checks of each converted item against its
  source (answer leakage, platform labels, missing instructions), feeding
  retries instead of a second generative pass;
- retry routing: whether a failed item needs relabeling or only
  reconversion.

The parent recommends the placements from that evidence.

Steps 1 and 2 are built and measured (feasibility result below and D23).
Before step 3 changes production, a parallelization measurement (D26)
compares batch shapes, reasoning efforts, a heading-split comparison and a
Sol 6.1 escalation for questions below 0.95. Step 3 is built now in
parallel with the measurement (D29); the measured values (batch size,
converter reasoning effort, Sol escalation, heading split) are set after
the user's decision on its result.

## Contract Inputs

- Architect proposal (GPT-6 Astra, 2026-10-11):
  `.orchestration/context/sessions/01a12706-566c-7480-acc3-427145283942/drafts/parallel-docx-conversion-and-conditional-labeler.md`,
  holding the label rules, starting thresholds, packing policy, cost estimate
  and the four-phase measurement plan.
- Official Decisions guide, read 2026-10-11
  (developers.openai.com/api/docs/guides/decisions): `predicate`
  (probability), `choice` (one supplied value, per-value probabilities,
  confidence) and `score` (ordered levels, per-level probabilities) questions;
  independent questions batch in one request; text or base64 image input;
  `gpt-6-luna` only; no structured objects or spans, which belong to
  Responses. Request limits are not yet verified (the reference page
  returned 404).
- Conversion principles and source-structure rules:
  TASK-SKRIPT-39-05-03. Gold files: `tests/fixtures/exam_conversion/docx_corpus/gold/`.

## Core Vertical And Performance

DOCX upload through grouping, labeling, parallel conversion and assembly to
the saved document and its QTI export. Speed criterion for the parent's
recommendation to the user: at least 30% lower median upload-to-ready time on
the 53-, 73- and 104-item corpus exams than the single call, with small exams
at most 10% slower. Eval criteria are evidence for that recommendation, never
automatic decision gates; the labeler's probability thresholds are runtime
routing only.

## Validation

- Feasibility step: grouping and labeling run once on each corpus exam;
  question and subpart boundaries, shared-context scope, ownership and labels
  are checked against the source. No conversion runs in this step.
- Gold is joined only by the evaluator after provider output; it is never an
  input to grouping, labeling, conversion or repair.
- Per-call tokens, cost and duration are recorded.

Feasibility result (2026-10-11, commit a63ec3cf, report
`.orchestration/context/sessions/01a12706-566c-7480-acc3-427145283942/evidence/task-skript-39-05-04/final-report.md`):
Responses grouping exact on 269–284 of 314 questions in 12–25 s per exam;
Decisions grouping with quoted chunks (B2) 266 in 2–4 s but misses most
shared-instruction scope; the item-type labeler is 96–97% correct and every
error has probability below 0.95; images, the ambiguity score, answer slots,
facit attachment, points, post-conversion checks and retry routing gave no
gain worth their cost; 7 of 356 Decisions calls failed with 503/504 and
succeeded on retry.

## Stop Conditions

- A conversion experiment (step 3 or later) starts before TASK-SKRIPT-39-05-03
  is merged; the labeling-only feasibility step may run before it.
- The grouping pass needs to write question text or answers.
- A rule needs to name an exam, a question number or a subject term.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | Conversion runs in parallel batches; the single whole-exam call is ruled out as too slow (user decision 2026-10-11). |
| D2  | A question and its subparts never split; items under a shared instruction or passage go to their type batches and receive the shared text as read-only context, with one owner per source chunk (user decisions 2026-10-11). |
| D3  | Each batch holds one item type; only single choice and multiple response may share a batch until measurement justifies another pair (user decisions 2026-10-11). |
| D4  | Item types come from a Decisions-API labeler with probability thresholds, not code-side cue typing (user decision 2026-10-11). |
| D7  | The feasibility step compares Responses grouping with Decisions-only chunk-role grouping, and tries an answer-slot predicate, an ambiguity score and page-image input; the parent recommends from that evidence (user decisions 2026-10-11). |
| D8  | The feasibility step evaluates every Decisions placement in the workflow (before conversion, facit attachment, points, post-conversion checks, retry routing) for quality per cost and time (user direction 2026-10-11). |
| D9  | The labeling-only feasibility step starts now, in parallel with TASK-SKRIPT-39-05-03; conversion experiments wait for its merge (user decision 2026-10-11). |
| D5  | The feasibility step runs before conversion changes; the larger measurement phases need a user decision on its result (user decision 2026-10-11). |
| D6  | Speed criterion: at least 30% lower median upload-to-ready on the 53-, 73- and 104-item exams, small exams at most 10% slower. Eval criteria are evidence for the parent's recommendation to the user, not automatic gates (user decisions 2026-10-11). |
| D10 | Decisions is used only for the item-type labeler: text input, 0.95 probability threshold, retries on 503 and 504; the other placements are dropped (user decision 2026-10-11). |
| D11 | The conversion experiment measures both groupings end to end: Responses grouping (A), and Decisions grouping with quoted chunks (B2) using A's instruction-scope rules; total time decides only when quality holds (user decision 2026-10-11). |
| D12 | The conversion experiment starts after TASK-SKRIPT-39-05-03 merges and builds batching on its parent model, so a parent and its children share a batch (user decision 2026-10-11). |
| D13 | The conversion experiment also targets two consecutive live eval runs where every corpus item meets the eight conversion principles, and measures higher reasoning effort as one variable (user decision 2026-10-11, moved from TASK-SKRIPT-39-05-03 D19). |
| D14 | The labeler receives each question's own source content as faithfully as possible: its own chunks in source order as markdown, keeping indentation, numbering and emphasis; inline answers, key labels, accepted alternatives and points stay where they stand; code adds nothing (no answer-slot markers, no reconstructed answer-key block) and removes nothing. Governing instructions and the section heading appear as their source text where they stand. Content that markdown cannot represent faithfully goes in as an image of that part. This replaces the earlier student-view term (user decision 2026-10-11). |
| D15 | Label descriptions are defined by how the answer is scored: gap means each response slot (blank, blank line or labelled field) is keyed by one or more accepted strings of any length; free text means the key is a sample answer, analysis or grading guidance. This replaces the rule that answer keys do not change the response action (user decision 2026-10-11). |
| D16 | Escalated questions get a second pass: each is re-asked alone with expanded context, and its effect is measured (user decision 2026-10-11). |
| D17 | Fresh test documents for the shapes behind the escalations (a whole sentence on one blank line, labelled answer fields with inline keys) are synthetic DOCX files written by an independent model that never sees the corpus or its gold, as clear teacher-style Word documents; the labeler changes are measured on the corpus and these documents (user decision 2026-10-11). |
| D18 | The labeler run also measures per-question shape counts (blanks, labelled fields, accepted strings per slot) sent as evidence alone, never as a typing rule in code; splitting the label set into two requests is measured only if escalations remain after D14-D16 (user decision 2026-10-11). |
| D19 | Shape counts (D18) are dropped from the labeler: measured on 2026-10-11 they left the corpus at 306/314 and lowered the held-out synthetic result from 73/76 to 70/76 (user decision 2026-10-11). |
| D20 | The second prompt round (probes P1-P4 and full runs with a hold-out set) ran after the D14 input repair was measured; its result is D23 (user decisions 2026-10-11). |
| D21 | Teachers can edit anything in the workspace, but problems that better model context or output handling can solve are solved there; every admission or prompt option is reported with the teacher work it leaves (user decision 2026-10-11). |
| D22 | Independent code review is paused while the pipeline is iterated and runs once on the settled pipeline before integration into main (user decision 2026-10-11). |
| D23 | Labeler prompt P1d in both passes: a type name the teacher writes settles a label, a key marking more than one option correct settles multiple_response, Swedish type names with English counterparts, no evidence wording. Admission: first pass at >= 0.95, otherwise B decides alone; no C, no tie-breaker; unresolved becomes free_text for now (user decisions 2026-10-11). |
| D24 | The teacher re-tag and rebuild flow for unsettled or wrong types is its own later story, contracted after the parallelization measurement (user decision 2026-10-11). |
| D25 | Two conversion waves (accepted questions at once, B questions after their labels arrive), progressive delivery to the editor, and a free_text marking-guide field in the converter schema are part of this task (user decisions 2026-10-11). |
| D26 | The parallelization measurement runs the production pipeline per setting, starting with one small exam: batch size (whole exam, about 16 or 6 question families, one family per request) and gpt-6-luna reasoning low or medium; reasoning none is dropped. Settings that are clearly bad are stopped early instead of run on every exam. It records timing, cost and 429s per request; quality is read as in D34. The frozen-input harness is discarded (user decisions 2026-10-11). |
| D27 | When questions under one instruction get different labels, consecutive questions of one type form one parent each, following the gold rule; each carries the instruction, and a moved question carries the check-the-type mark (user decision 2026-10-11). |
| D28 | The gold files are corrected before the measurement: samhallskunskap q14 and kursavslutande Fråga 20 become free_text, each with a note citing the user decision (user decision 2026-10-11). |
| D29 | The decided parts of steps 1-4 are built now, in parallel with the D26 measurement, by several agents in the task worktree with disjoint file scopes; batch size, converter reasoning effort, Sol escalation and heading split stay single named settings set after the measurement, which runs from a frozen snapshot (user decision 2026-10-11). |
| D30 | While batches still convert, the teacher can edit converted items: the document is saved when the first batch is ready, with placeholders (source text, converting) for the rest; each later batch fills only its own placeholders, and a placeholder the teacher changed keeps the teacher's version while the late result is dropped (user decision 2026-10-11). |
| D31 | The free_text marking guide is shown and editable in the item editor and printed in the DOCX and PDF answer-key exports; it enters the QTI export as a scorer rubric only after a staging import shows Exam.net accepts and displays it (user decision 2026-10-11). |
| D32 | The strict response schema is the only gate on converter output. A schema-valid response is never rejected or retried for unclaimed chunks, unknown or conflicting anchors, source-rule, item-rule or label-rule checks, or family splits: batch anchors are a per-request schema enum, the first item claiming an anchor keeps it, an unclaimed chunk becomes a review item holding its source text, and an item that breaks a document invariant becomes a review item with the reason. The only resend is one typed type_conflict resend per question (step 4) (user decisions 2026-10-11). |
| D33 | Following A7, gold is one correct conversion, not the only one. exam-conversion-eval judges a question only on type, answer key, points, answer leakage, and that no gold word is lost wherever it sits in the question or its parent; segmentation, slot placement, platform label and word-order checks are removed. Each converted question is paired with the gold question its wording overlaps most, not by position (user decisions 2026-10-11). |
| D34 | Conversion quality is judged, not computed: the D33 script is a loose gate that catches most failures, and the parent and the user then read the results together, adding reviewer agents (Claude, Sol 6.1) where they help. No fixed procedure is set in advance. Conversion is a best-effort first draft that a teacher reviews and can resend: a setting is chosen when its quality is reasonable for its wait, and extra time that buys only small gains on most questions is not worth it (user decision 2026-10-11). |
| D35 | The labeler sees every question with the full text of each shared heading, instruction or word box that governs it, repeated per question; conversion keeps its ownership, and a converted question never lacks the shared text that governs it (user decision 2026-10-11). |
