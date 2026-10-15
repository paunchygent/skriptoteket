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
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-15'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Pi ruthless-reviewer (gpt-6.1-sol) requested changes on 7d4ae4a5 and approved its repair; the under-four-characters rule 2647de47 was approved and merged as ebe212f1. Walk at cbe58ae1: a live gap key gained three spellings for substantivfras and none for KS or NF; Exam.net import 5339195 holds the keys and six spellings as accepted gap values. Records in Skriptoteket session 01a13c92-d70e-765f-ae36-b6583539e201 evidence/reviews/TASK-SKRIPT-39-09-06/ and evidence/walk/TASK-SKRIPT-39-09-06/walk-cbe58ae1.md.'
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
  Infer one language from the complete exam text using stopword counts and
  å/ä/ö as a Swedish signal, with Swedish winning ties; pass it explicitly
  to the producer. Never mix languages for a value. Exclude valid words of
  that language, including inflected forms, from every tier using the committed
  dictionary-and-inflection lexicons. User decision 2026-10-15: no compound
  check; a real compound absent from those lexicons is not filtered.
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

- The DaLAJ 1.0 alignment gate was reached and reported. The user resolved
  it with the Swedish-source research: DaLAJ-GED-Superlim 2.0 O-labelled
  pairs yielded 1,377 A10 pairs covering 1,007 words before inflected-word
  filtering. Use O and mixed-O as the primary Swedish attested source,
  with the researched Wikipedia lists as supplements; preserve attribution.
  Evidence: retained session `01a13c92-d70e-765f-ae36-b6583539e201`,
  `evidence/research/swedish-misspelling-sources.md`.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| T1  | The producer ranks attested learner errors, then hunspell REP reversal, then keyboard typos; candidates pass the A10 filter and the first 3 per accepted value are kept (R15). |
| T2  | The producer replaces the model's spelling candidates in DOCX conversion; one producer serves teacher-created and converted gaps (R16). |
| T3  | Adding an accepted value through the gap popover adds its misspellings; a teacher-removed variant stays removed (R15, Q14). |
