---
type: task
id: TASK-SKRIPT-39-05-05
title: Remove answer-key wording from converted exam titles
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
