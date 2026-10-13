---
type: task
id: TASK-SKRIPT-39-05-05
title: Remove answer-key wording from converted exam titles
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-11'
status: done
closeout_review:
  record: inline
  status: not_required
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: 'User closed 39-05-05 on 2026-10-14 ("finish up the story items") after review approval 83501383, merge ece1b674 and the 2026-10-11 staging walk, evidence .orchestration/context/sessions/01a12706-566c-7480-acc3-427145283942/evidence/task-skript-39-05-05/staging-walk-ece1b674/'
task_kind: story
acceptance_criteria:
- A DOCX whose opening heading carries answer-key wording converts to a title without
  that wording, the rest of the heading copied verbatim, and every gold title that
  carries that wording matches it
story: ST-SKRIPT-39-05
backlog_document_profile: contract-derived
---

## Implementation Contract

A converted exam's title is what students see on Exam.net. When the source's
opening heading carries answer-key wording, such as "— answer key" or
"med facit", the converted title keeps that wording today, because rule 5
copies the opening heading verbatim. The title must drop that wording and
keep the rest of the heading unchanged.

The model still copies the opening heading verbatim, and the rule 5 check stays
as it is. After that check, a deterministic step removes the answer-key wording
together with the separator that joins it to the heading. The separators are a
dash, a colon, a comma or enclosing parentheses. The step recognises one closed
Swedish and English phrase list, at the start or the end of the heading. The
filename fallback title goes through the same step. No rule names an exam.

Every gold title that carries answer-key wording drops it: `sa24`,
`bf26_english`, `bf26_diagnostic`, `chapter_4` and `metodprov`; nothing else
in gold changes.

## Contract Inputs

- Staging walk 2026-10-11 on `1db37835`. The sa24 title is
  "Test Unit 3 Discuss and Argue — answer key". The bf26_english title is
  "BF26 English 1 Unit Test — 45 minutes — answer key".
- `src/skriptoteket/domain/curated_apps/exam_workspace/docx_source_rules.py`
  `title_rule_violation` holds rule 5.
- `exam_workspace_docx_build_admission.py` admits the title.

## Core Vertical And Performance

DOCX upload, conversion, title admission, the saved document, and the QTI
export title. The step does no extra model call.

## Validation

- Adversarial unit tests on the real opening headings of the corpus. Headings
  with answer-key wording lose only that wording. Headings without it are
  unchanged, including a heading where "key" or "svar" is part of the title
  itself rather than a trailing label.
- `pdm run exam-conversion-eval` (recorded mode) passes the title check on all
  eight exams.
- Lint and typecheck on the changed files.
- A staging upload of `sa24` shows the stripped title in the editor and in the
  QTI export.

## Stop Conditions

- The phrase list needs an exam-specific entry.
- Removing the wording would leave an empty title.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | Converted titles drop answer-key wording, and every gold title carrying it drops it too (five corpus exams; amended 2026-10-11 when discovery found three more than the walk showed). |
| D2  | The rule 5 verbatim check is unchanged. A deterministic step after it removes the phrases on one closed Swedish and English list (answer key, key, facit, med facit, with answers, svar) at the heading's start or end, with their joining separator. The filename fallback uses the same step. No rule names an exam. |

## Implementation Evidence

2026-10-11: the deterministic title step runs after unchanged rule 5 admission
and on the filename fallback stem, preserving its extension and source filename.
The five gold changes are title-only, approved by the user through the parent.
Retained session `01a12706-566c-7480-acc3-427145283942`, directory
`evidence/task-skript-39-05-05/`:

- `gold-title-changes.md` lists the exact five title changes; `gold-title.diff`
  retains the full diff.
- `title-tests.log`: 22 focused tests pass on the real corpus headings and
  recorded rounds. Five headings lose labels; three remain unchanged. The
  corpus has no opening heading using `key` or `svar` as ordinary title wording,
  so that negative case remains uncovered.
- `lint.log` and `typecheck.log`: Ruff and Mypy pass on all four changed Python
  files.
- `recorded-title-proof.json`: all eight existing eval title checks pass;
  non-title item results are identical to the baseline on `6bf05757`.
  `recorded-eval/report.json` and `baseline-6bf05757/report.json` retain both runs.
  Both full eval commands exit 1: diagnostic, English and grammar variant 2
  retain their existing item mismatches. This establishes the task's title
  proof; it does not establish a passing full conversion eval.

Parent-owned independent review, merge and the staging editor/QTI walk remain.

2026-10-11: fresh-owner repair of admitted F1 from review `b306d05e` treats
underscores and hyphens as word separators only for filename fallback. The
shared closed phrase list removes each complete edge label and its joining
separator, preserving remaining filename characters, the extension and source
filename. Heading cleanup, verbatim admission and the five approved gold edits
remain unchanged.

Retained repair evidence: `evidence/task-skript-39-05-05/f1-repair/` in the same
session. The new adversarial tests failed before repair (40 failed, 5 passed);
after repair all 45 pass, alongside all 22 accepted title tests. Changed-file
Ruff/Mypy pass. `filename-fallback-probe.json` records exact corrected titles
for all eight real corpus filenames with unchanged source filenames.
Independent rereview and the parent-owned staging walk remain outstanding.
