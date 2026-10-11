---
type: task
id: TASK-SKRIPT-39-05-03
title: Fix the conversion defects the staging corpus walk found
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-11'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- Every item of every corpus exam meets the eight conversion principles in this contract against its gold file on two consecutive live eval runs, including the matching items
story: ST-SKRIPT-39-05
backlog_document_profile: contract-derived
---

## Implementation Contract

The AI-first DOCX conversion follows five rules stated in terms of source
structure. A rule never names an exam, a question number or a subject term,
and it names the source feature that triggers it. Today's prompt causes
several defects directly: it tells the model to put inline facit marks into
gaps "at the place the student answers", and never to compute or distribute
points.

1. **Gaps come from answer slots.** A gap exists where the student-visible
   text has a blank marker (an underscore run, dotted line or empty brackets),
   or where an answer line "Label: value" holds a field the question asks the
   student to produce. A field that restates student-visible context, such as
   the marked part or a clause the question gives, stays text. The facit never
   creates a slot of its own.
2. **Segmentation decides free text.** When answering requires the student to
   decide where the units start and end (a rewritten sentence with inline
   labels, or a word split with `+`), the question is free text with no gaps.
   When the source fixes the units and gives one label per unit, each unit is
   one gap.
3. **Accepted values.** A gap accepts the facit's own form, each part of a
   facit form that joins alternatives with a slash, and the form the
   question's instructions tell students to use when they define an
   abbreviation and its term ("Använd … Adv = adverbial"). Code never removes
   a value the model adds beside these.
4. **Points.** The model reports printed points only. When a section prints a
   total and its member questions print none, code splits the total equally
   when it divides evenly, and otherwise leaves the items for teacher review.
5. **Title and facit by role.** The document title is the exam's heading text
   copied verbatim. A chunk is facit by its position (under a facit heading,
   or as an answer line), never because its wording mentions an answer key.

Invariants for rules 1, 2, 5 and 7 are checked against the source chunks and
sent back as `validation_errors` retry rounds; they never consult gold.

6. **Matching.** A question that asks the student to pair entries of two
   lists becomes a native matching item with its directed pairs from the
   facit. The answer list may hold more entries than the prompt list
   (distractors). The native document model, the conversion schema, the
   editor, the QTI export, the PDF export and answer-key completion carry the
   matching kind (ST-SKRIPT-39-05 A6).
7. **Platform labels in code.** Code rejects a converted item whose text still
   carries a question number, a printed point label or a printed blank marker,
   and sends it back as a `validation_errors` retry round.

### Conversion principles

A conversion is correct when a student on Exam.net meets the same questions,
answers them the same way and is scored the same as on paper, and the
conversion adds nothing Exam.net owns and nothing that reveals an answer.
The gold file is one correct conversion; the eval judges these principles
against it, not textual identity:

1. **Segmentation.** One source question is one item with all its subparts,
   in source order; no source text is lost, duplicated or attached to the
   wrong item.
2. **Response kind.** The item has the gold item's kind.
3. **Response slots.** Gaps are equal in number and order; matching items
   have the same two lists.
4. **Scoring.** The correct-choice set equals gold. Each gap accepts every
   gold answer; an extra answer fails only when it is another gap's gold
   answer or falls outside the spelling policy and the forms rule 3 admits.
   Matching pairs equal gold.
5. **Points.** Points equal gold.
6. **No answer leakage.** No facit answer appears in student-visible text
   unless the gold item shows it there.
7. **No platform labels.** Choices carry no option letters or numbers, and
   items carry no question numbers, point labels or printed blank markers.
8. **Content present.** All gold student-visible wording is present in the
   item's title, section or prompt. Punctuation, whitespace, case, quote
   style, line breaks, the order of accepted variants and whether a heading
   sits in the title or the prompt do not count.

Out of scope: any change to gold files.

## Contract Inputs

- Staging walk 2026-10-11 on `dcf9e2af`. Symptoms:
  - `svenska_2_kursavslutande_prov`: items 1-15 have no points under a
    15-point section total.
  - `svenska_2_grammatik_omprov` variants 1 and 2: items 1 and 5 become
    gaps holding a whole analysis.
  - Variant 2: item 4 lacks the abbreviation forms, and item 6 has gaps for
    the given clause.
  - `sa24`: the title is the filename.
  - The two omprov variants convert differently from each other.
- Source check, 2026-10-11:
  - The English corpus marks every gold gap with an underscore blank.
  - The Svenska corpus has no blank markers. It marks answers as
    "Label: value" lines, which rules 1-3 describe.
- Gold files: `tests/fixtures/exam_conversion/docx_corpus/gold/`, confirmed by
  the user in TASK-SKRIPT-39-05-02.
- Prompt: `src/skriptoteket/application/curated_apps/handlers/exam_workspace_docx_build_rounds.py`.

## Core Vertical And Performance

DOCX upload in the exam workspace, through background conversion, to the
saved document and its QTI export. Conversion stays inside the current DOCX
timeout. Retry rounds caused by invariant checks stay bounded by the existing
round limit.

## Validation

- The eval comparator judges the eight conversion principles, and its gold
  README states them.
- `pdm run exam-conversion-eval --mode live`: every item of every corpus exam
  meets the principles on two consecutive runs.
- Focused tests for the changed code. Tests are adversarial on real corpus
  chunks.
- Lint and typecheck on the changed files.
- A staging walk uploads the three Svenska 2 exams, `sa24` and
  `bf26_english`, checks them against the principles, edits one matching
  item in the editor and exports QTI.

## Stop Conditions

- A rule needs an item kind other than matching, an exam-specific condition, or a gold change.
- Consistency needs a model or provider change.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | The conversion follows the source-structure rules above, including the matching kind end to end (user decision 2026-10-11, replacing an earlier term that excluded matching). |
| D2  | No rule names an exam, a question number or a subject term. Invariants check the source, never gold. No retry-until-gold loop (user instruction 2026-10-11: no reward hacking). |
| D3  | Gold files are read-only authority for comparison (TASK-SKRIPT-39-05-02). |
| D4  | The Claude parent session owns this exam work; repairs elsewhere go to Codex (user decision 2026-10-11). |
| D5  | The eval judges the eight conversion principles against gold, not textual identity; the comparator rewrite belongs to this task (user decisions 2026-10-11). |
| D6  | Each part of a slash-joined facit form is accepted; code does not remove model-added values (user decisions 2026-10-11). |
| D7  | Matching items may hold distractors: the answer list may be longer than the prompt list (user decision 2026-10-11). |
| D8  | PDF export prints matching items, and answer-key completion proposes matching pairs where the facit lacks them (user decision 2026-10-11). |
| D9  | Code rejects items that keep question numbers, printed point labels or blank markers and retries them, as for the other source invariants (user decision 2026-10-11). |
| D10 | A section instruction is copied into each item under it until the next heading, matching today's gold; section instructions become parents with child questions in ST-SKRIPT-39-06 (P5, P10) (user decision 2026-10-11). |
| D11 | A gap also accepts the other apostrophe spelling and a full-sentence answer with or without its final full stop (user decision 2026-10-11). |
| D12 | The title is the exam heading; a heading plus its printed subtitle is also correct, but the heading alone is preferred (user decision 2026-10-11). |
| D13 | When instructions define an abbreviation and its term, a gap accepts both halves (user decision 2026-10-11). |
| D14 | Admission has no source-word presence check; faithful wording stays with the model per story A14 (user decision 2026-10-11). |
