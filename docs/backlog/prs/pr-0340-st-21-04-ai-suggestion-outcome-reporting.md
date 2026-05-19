---
type: pr
id: PR-0340
title: "ST-21-04 AI suggestion outcome reporting"
status: done
owners: "agents"
created: 2026-05-19
updated: 2026-05-19
stories:
  - "ST-21-04"
tags:
  - frontend
  - conversion-hub
  - exam-converter
  - ai-prefill
  - report
dependencies:
  - "PR-0338"
  - "PR-0339"
acceptance_criteria:
  - "Given AI answer-key suggestions exist for missing answer-key provenance or similar source diagnostics, when the teacher opens the report, then the report shows the teacher-relevant AI suggestion outcome counts instead of a standalone raw conversion-warning count."
  - "Given AI suggestions were accepted unchanged, teacher-edited before save, suppressed, or left unresolved, when the report is rendered, then each outcome is counted separately and the totals reconcile to the item rows shown in the question list or inspector."
  - "Given all AI-suggested facit are saved and replayed, when corrected files are exportable, then the report states that no AI suggestion review remains instead of implying unresolved warnings."
  - "Given original Sir Convert conversion diagnostics still exist, when they do not require teacher action, then they are hidden from the teacher-facing report summary."
  - "Given conversion diagnostics are needed for support, when a support/debug surface is created later, then it must not use internal artifact names, raw provenance enums, Sir Convert terminology, or backend-only codes as primary teacher copy."
---

# PR-0340: ST-21-04 AI Suggestion Outcome Reporting

## Problem

`PR-0339` separated remaining teacher actions from raw conversion diagnostics,
but the resulting `Konverteringsvarningar` count is still not useful enough for
teachers. A count such as `4` does not answer the teacher's real questions:
which questions had AI-suggested facit, how many suggestions were produced,
which suggestions were accepted unchanged, which were edited by the teacher,
and whether anything remains to review.

The backend `warning_count` remains useful as service diagnostics, but it is not
the right primary teacher-facing report metric.

## Goal

Replace the prominent conversion-warning count in the Exam Converter report
with AI suggestion outcome reporting that is specific to teacher work:

- total AI suggestions presented for the current conversion;
- accepted unchanged;
- edited by teacher before save;
- suppressed/rejected where that action exists;
- unresolved suggestions still needing review;
- item-level mapping back to the question rows or inspector.

Raw conversion diagnostics may still exist, but they are not part of the main
teacher-facing report. If support needs them later, that belongs in a separate
debug/support surface.

## Non-goals

- No change to Sir Convert's `warning_count` or `warnings_report` contract.
- No claim that every Sir Convert warning maps one-to-one to an AI suggestion.
- No new AI provider call or answer-key generation behavior.
- No matching answer-key enablement before the governed matching producer task.
- No exposure of raw backend diagnostic codes as primary teacher copy.

## Implementation plan

1. Extend the frontend report projection so it derives AI suggestion outcome
   counts from question projection and durable correction/replay provenance,
   not from raw `warning_count`.
2. Count accepted unchanged AI suggestions from replayed answer-key provenance
   such as `accepted_advisory_candidate`.
3. Count teacher-edited AI-seeded saves separately when durable intent
   `submission_origin` indicates an advisory candidate was edited before save.
4. Count unresolved suggestions from remaining valid `llmCandidate` rows.
5. If candidate suppression is present, count those rows separately from
   accepted or unresolved suggestions.
6. Replace the prominent `Konverteringsdiagnostik` block with an
   `AI-förslag` summary that links back to the question list/inspector.
7. Hide raw conversion diagnostics from the teacher-facing report summary when
   no teacher action remains.
8. Update Swedish copy and tests so the report cannot imply that completed
   AI-suggested facit are still unresolved warnings.

## Test plan

- Focused Vitest for report projection and rendering:
  - accepted unchanged AI suggestion;
  - teacher-edited AI-seeded suggestion;
  - unresolved suggestion;
  - suppressed/rejected suggestion where available;
  - raw conversion warning count present but demoted.
- Focused Exam Converter view test proving the report no longer shows a
  standalone `Konverteringsvarningar` count as the main teacher-action signal.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback plan

Restore the prior report rendering while keeping the `PR-0339` distinction that
remaining teacher actions and raw conversion diagnostics are separate. Do not
move raw `warning_count` back under `Det här behöver kontrolleras`.

## Implementation Summary

- `digiexamIrReviewParser.ts` now derives an AI suggestion outcome report from
  question projection state.
- `correctionSessionProjection.ts` rebuilds that report after durable readback
  and replay, counting accepted unchanged AI suggestions, teacher-edited
  AI-seeded saves, suppressed suggestions, and unresolved suggestions.
- `ExamConverterReportSummary.vue` replaces the raw conversion-warning block
  with the teacher-facing `AI-förslag` summary and item rows. Raw conversion
  diagnostics are not shown in the report summary.
- `ExamConverterEffectiveAnswerKeySummary.vue` now renders saved choice facit
  as selected alternative rows with the alternative text, not as detached
  numeric values.
- Focused Exam Converter Vitest coverage now proves accepted, edited,
  suppressed, and unresolved AI suggestion reporting while a raw
  `warningCount` remains present in the projection.

## Verification

- `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterAuthenticatedAiPrefillDurableSlice.spec.ts src/views/apps/ExamConverterCorrectionSessionReplay.spec.ts`
- `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedAiPrefillDurableSlice.spec.ts src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts`
- `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterAuthenticatedAiPrefillDurableSlice.spec.ts src/views/apps/ExamConverterCorrectionSessionReplay.spec.ts src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `pdm run python -c '...'` Playwright smoke against
  `http://127.0.0.1:5173/apps/documents.conversion_hub/exam-converter/ui-fixtures/persisted-corrections`
  with auth endpoints fulfilled in-browser; verified
  `exam-converter-effective-answer-key-choice-2` contains the selected
  alternative text.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`
