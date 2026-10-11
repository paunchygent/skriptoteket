---
type: task
id: TASK-SKRIPT-39-05-06
title: Judge a staging-converted exam document against its gold with one command
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
- pdm run exam-conversion-judge <exam stem> <saved document json> prints the eval
  comparator verdict per principle, the title check and every mismatch for a document
  fetched from staging, and exits non-zero when any item or the title fails
story: ST-SKRIPT-39-05
backlog_document_profile: contract-derived
---

## Implementation Contract

Staging walks fetch a converted exam document from the exam-workspace API and
judge it against its gold with the eval comparator. Today that judge is a
scratch script. Add `pdm run exam-conversion-judge <exam stem> <document json>`
beside `exam-conversion-eval`. It reuses `compare_native_exam`, the corpus gold
file and the DOCX chunker (for the title check). It accepts the document API
response (`{"document": ...}`) or a bare native document, prints the failing
item count per principle, the title verdict and every mismatch, and exits 1
when any item or the title fails, 0 otherwise.

## Contract Inputs

- Scratch judge used on the staging walks of 2026-10-11.
- `scripts/exam_conversion_eval/compare.py` (`compare_native_exam`) and
  `__main__.py` (report printing).

## Core Vertical And Performance

Command entry in `pyproject.toml`, the judge module under
`scripts/exam_conversion_eval/`, shared report printing with the eval. No model
or network call.

## Validation

- Adversarial tests on real inputs: a recorded corpus document that matches
  its gold exits 0; the same document with one item's points changed exits 1
  and names that item and principle; the API envelope and the bare document
  both parse.
- Ruff and mypy on changed files.

## Stop Conditions

- The comparator or gold would need to change.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | `pdm run exam-conversion-judge <exam stem> <document json>` reuses the eval comparator, gold and chunker; accepts the API envelope or a bare document; prints per-principle failures, the title verdict and every mismatch; exits 1 on any failure. |

## Implementation Evidence

- Command: `pdm run exam-conversion-judge <exam stem> <document json>`.
  `scripts/exam_conversion_eval/judge.py` loads the saved API response or bare
  native document, the matching corpus gold and DOCX chunks. Shared comparison
  printing lives in `report.py` and is also used by `exam-conversion-eval`.
- Proof and command captures are retained in session
  `01a12706-566c-7480-acc3-427145283942`, under
  `evidence/task-skript-39-05-06/` and `operational-output/commands/`.
  `evidence/task-skript-39-05-06/summary.md` lists the commands and results.
- Five saved staging documents satisfy all item principles (166/166 items).
  Three exit 0; historical SA24 and BF26 captures exit 1 because their titles
  still contain answer-key wording. Three additional bare live-eval documents
  were checked separately; their historical mismatches remain failures.
- The unchanged Swedish grammar variant-1 capture passes as an envelope and
  as a bare document. Changing its first score from 6 to 7 prints the question
  and points mismatch and exits 1; a title-only mutation also exits 1.
- Five focused adversarial tests, changed-file Ruff, format and mypy checks,
  docs and handoff validation pass. Recorded eval retains its baseline three
  failed exams. Independent review and parent integration remain pending.
