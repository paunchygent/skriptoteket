---
type: task
id: TASK-SKRIPT-39-09-06
title: 'Structured misspellings: a deterministic producer gives every keyed gap its
  automatic misspellings'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-15'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- A teacher keys an accepted answer in any gap and gets up to 3 realistic automatic
  misspellings from the structured producer; DOCX conversion uses the same producer;
  Exam.net imports them as accepted gap values
story: ST-SKRIPT-39-09
backlog_document_profile: contract-derived
---

## Implementation Contract

Delivers ST-SKRIPT-39-09 task 6 (story term Q18): one deterministic,
structured producer gives every keyed gap its automatic misspellings, for
teacher-created and converted gaps alike.

- **Producer.** For each accepted value, candidates come in tier order:
  attested learner errors (Swedish pairs aligned from DaLAJ; English from the
  Birkbeck `missp.dat` and the Wikipedia common-misspellings list), then
  hunspell REP-rule reversal (`sv_SE.aff`, `en_US.aff`; one application,
  anchored, whitespace and dot rules excluded), then keyboard-adjacency typos
  with a vendored Swedish and English QWERTY neighbour map. Each candidate
  passes the existing A10 filter (`answer_spelling.py`); the first 3 survivors
  per accepted value are kept. The same input always yields the same output.
- **Data.** The attested maps are built once by a committed build script,
  pre-filtered to the A10 distance bound, and committed as static data with
  their source attribution; the REP tables and keyboard maps are committed
  too. No model, JVM or network access runs at request time.
- **Teacher keying.** Adding an accepted value through the gap popover adds
  that value's misspellings to the gap's automatic values. A variant the
  teacher removed stays removed; editing other values does not regenerate it.
- **Conversion.** The DOCX conversion route uses the same producer; the model
  no longer proposes spelling candidates, and its schema, contracts and
  recordings drop them (no backward compatibility).
- **Export.** Automatic values export as accepted gap values through the task
  2 Lucktext route, unchanged.
- **Out of scope.** Any LanguageTool server; languages other than Swedish and
  English.

## Contract Inputs

- ST-SKRIPT-39-09 term Q18; task 5 review finding F2
  (`evidence/reviews/TASK-SKRIPT-39-09-05/review-b58778a8.md` in retained
  session 01a13c92).
- Research: `evidence/research/misspelling-sources.md` in retained session
  01a13c92 (sources, REP-reversal probes, ranking).
- Backend: `answer_spelling.py` (A10 filter), `docx_ai_build.py`,
  `docx_ai_contracts.py`, `docx_ai_schema.py`,
  `exam_workspace_docx_build_rounds.py`, `native_exam_document.py`
  (`NativeGap`), `examnet_qti_export.py`.
- Frontend: `ExamWorkspaceGapPopover.vue`, `examWorkspaceItemEdits.ts`
  (`withGapValues`), `useExamWorkspaceDocument.ts` (`updateItemGapValues`).

## Core Vertical And Performance

A teacher adds Kort svar, keys "Stockholm" and sees up to 3 automatic
misspellings; saves and exports; Exam.net imports the Lucktext with the
accepted and automatic values keyed. The producer loads its static data once
per process; a lookup for one value stays within a few milliseconds.

## Validation

- Focused pytest for the producer tiers, ranking, the A10 bound, determinism
  and both languages, and for the DOCX route using the producer.
- Focused Vitest for adding misspellings on keying and keeping removed ones
  removed.
- Staging walk: a keyed Kort svar gets its misspellings, exports and imports
  into Exam.net with them keyed.

## Stop Conditions

- DaLAJ alignment yields too few Swedish pairs to rank above REP reversal;
  report the yield before shipping Swedish attested data.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| T1  | The producer ranks attested learner errors, then hunspell REP reversal, then keyboard typos; candidates pass the A10 filter and the first 3 per accepted value are kept (R15). |
| T2  | The producer replaces the model's spelling candidates in DOCX conversion; one producer serves teacher-created and converted gaps (R16). |
| T3  | Adding an accepted value through the gap popover adds its misspellings; a teacher-removed variant stays removed (R15, Q14). |
