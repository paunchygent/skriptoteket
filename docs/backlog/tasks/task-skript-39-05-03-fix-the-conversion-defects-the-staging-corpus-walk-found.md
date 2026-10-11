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
- The conversion follows the five source-structure rules in this contract, so the eval reports no difference on the items they govern, two consecutive runs agree, and no exam that matches gold today regresses
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
3. **Accepted values.** A gap accepts the facit's own form, plus the form the
   question's instructions tell students to use when they define an
   abbreviation and its term ("Använd … Adv = adverbial").
4. **Points.** The model reports printed points only. When a section prints a
   total and its member questions print none, code splits the total equally
   when it divides evenly, and otherwise leaves the items for teacher review.
5. **Title and facit by role.** The document title is the exam's heading text
   copied verbatim. A chunk is facit by its position (under a facit heading,
   or as an answer line), never because its wording mentions an answer key.

Invariants for rules 1, 2 and 5 are checked against the source chunks and
sent back as `validation_errors` retry rounds; they never consult gold.

Out of scope: the matching kind (ST-SKRIPT-39-05 A6), and any change to
gold files.

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

- `pdm run exam-conversion-eval`: no difference on the items the five rules
  govern, and no regression on `metodprov`, `bf26_diagnostic`, `sa24`
  answers or the `bf26_english` choices.
- Two consecutive eval runs produce the same item shapes.
- Focused tests for the changed code. Tests are adversarial on real corpus
  chunks.
- Lint and typecheck on the changed files.
- A staging walk uploads the three Svenska 2 exams and `sa24`, and checks
  them against gold.

## Stop Conditions

- A rule needs a new item kind, an exam-specific condition, or a gold change.
- Consistency needs a model or provider change.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | The conversion follows the five source-structure rules above. Matching stays with its own story item (user decision 2026-10-11). |
| D2  | No rule names an exam, a question number or a subject term. Invariants check the source, never gold. No retry-until-gold loop (user instruction 2026-10-11: no reward hacking). |
| D3  | Gold files are read-only authority for comparison (TASK-SKRIPT-39-05-02). |
| D4  | The Claude parent session owns this exam work; repairs elsewhere go to Codex (user decision 2026-10-11). |
