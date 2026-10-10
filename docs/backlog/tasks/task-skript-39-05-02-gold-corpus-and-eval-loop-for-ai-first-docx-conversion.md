---
type: task
id: TASK-SKRIPT-39-05-02
title: Gold corpus and eval loop for AI-first DOCX conversion
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-10'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- Each of the eight corpus exams has a gold file the user has confirmed, and one eval
  command converts every corpus exam and reports every item that differs from its
  gold
story: ST-SKRIPT-39-05
backlog_document_profile: contract-derived
---

## Implementation Contract

Give ST-SKRIPT-39-05 its pass bar (story term A7): one hand-checked gold
file per corpus exam, and one eval command that converts every corpus exam
and reports each item that differs from its gold.

- **Gold files are read from the source, never from the converter.** Each
  gold file is drafted by reading the DOCX and its facit directly. It is
  never produced by running the AI converter. The user confirms each file
  once, and a file is marked confirmed only after that.
- **One gold file per exam.** Each file sits next to the DOCX in
  `tests/fixtures/exam_conversion/docx_corpus/gold/` and lists the expected
  items in order. Each item states:
  - its kind;
  - its points;
  - its student-visible prompt text;
  - for choice items, the options and which are correct;
  - for gap items, each gap's accepted facit answers;
  - for matching items, the pairs.
- **Expected shapes per story term A6.** Matching tables are gold matching
  items even before task 4 adds the kind. A word bank is gap text where each
  gap accepts its own facit word. A shape that fits no kind is a gold review
  item.
- **The comparison checks substance, not formatting.**
  - Prompt text is compared after whitespace normalisation.
  - Accepted answers and correct options are compared as sets.
  - The converter may add an accepted answer that is not in gold only when
    it is a close misspelling of a gold answer within the edit distance of
    story term A10. Any other extra or missing answer is a mismatch.
- **The eval command reports, it never fixes.** It converts every corpus
  exam through the real import pipeline. It has two modes: recorded provider
  responses for repeatable runs, and the live provider for eval-loop rounds.
  It prints a per-exam and per-item mismatch report, stores the full report
  as evidence, and exits non-zero when any item differs. A live run records
  its input and output tokens per exam.
- **Order of work.** Draft the gold files, the gold schema and the
  comparator now. Wire the eval command to the converter after
  TASK-SKRIPT-39-05-01 is merged to `main`; the parent merges `main` into
  this branch for that step.

## Contract Inputs

- ST-SKRIPT-39-05 terms A3, A6, A7 and A10.
- Corpus `tests/fixtures/exam_conversion/docx_corpus/`: eight DOCX exams
  with `.sha256` files (`144d6333`).
- Native item contract `domain/curated_apps/exam_workspace/native_exam_document.py`.
- TASK-SKRIPT-39-05-01 converter and import job (branch
  `codex/task-skript-39-05-01`, under review).
- Current-importer probe:
  `.orchestration/context/sessions/01a1263d-5783-74c7-823d-9b4475c85915/evidence/docx-corpus-current-importer-2026-10-10.txt`.

## Core Vertical And Performance

`corpus DOCX -> gold file (drafted from source, user-confirmed) -> eval
command converts each exam through the import pipeline -> comparator ->
per-item mismatch report and non-zero exit on any difference`.

- A recorded-mode run of all eight exams is fast enough for a focused test
  suite. Live mode is a manual eval-loop step and is not part of CI.

## Validation

- Unit tests for the comparator:
  - whitespace-only prompt differences pass;
  - answer order does not matter;
  - an allowed misspelling passes;
  - an extra or missing answer, a wrong kind, wrong points and a wrong
    correct option each fail.
- A schema test that every gold file parses and covers its exam's items.
- The eval command runs in recorded mode over the corpus and reports
  mismatches. It is not expected to pass until task 3.
- Backend gates per `AGENTS.md`: lint and focused tests.

## Stop Conditions

- Stop if a gold file would have to be derived from converter output.
- Stop if the facit of an exam is ambiguous enough that gold needs a
  teacher decision. Name the item and the question for the parent.
- Stop before wiring the eval command if TASK-SKRIPT-39-05-01 is not yet
  merged.
- Production acceptance remains user-owned.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| G1 | Gold files are drafted from the DOCX and facit, never from converter output, and are confirmed once by the user (ST-SKRIPT-39-05 A7, user decision 2026-10-10). |
| G2 | Comparison checks kind, points, normalised prompt text, and answer sets; extra answers pass only as close misspellings within the A10 bound (ST-SKRIPT-39-05 A7 and A10, user decisions 2026-10-10). |
| G3 | Gold expresses matching, word banks and unfit shapes per A6, so the eval reports them until later tasks pass them (ST-SKRIPT-39-05 A6, user decision 2026-10-10). |
| G4 | The eval command runs recorded and live modes, reports every mismatch, exits non-zero on any difference, and records live token use (ST-SKRIPT-39-05 A2 and A3, user direction 2026-10-10). |
