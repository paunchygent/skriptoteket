---
type: review
id: REV-PR-0406
title: "Review: PR-0406 Exam Converter compact answer-key review state"
status: approved
owners: "agents"
created: 2026-06-29
updated: 2026-06-29
reviewer: "ruthless-code-review"
prs:
  - PR-0406
links:
  - ST-21-11
  - ST-21-04
  - ADR-0086
  - ADR-0087
---

## TL;DR

Approved on pass 2. The strict consumer adapter, first-pass
`answer_key_review_state_report` authority, correction replay
`answer_key_review_state` authority, replay-scoped file-action boundaries, and
the remediated pending advisory detail interaction now satisfy PR-0406. The
pass-1 blocker is retained below for history; remediation added an explicit
`Acceptera` unchanged path, an `Ändra` transition into the normal `Spara facit`
editor, producer-projection/replay-backed state transitions, and retained live
proof for both advisory paths.

## Problem Statement

PR-0406 must consume Sir Convert's
`digiexam_answer_key_review_state_v1` projection through one strict adapter while
keeping Skriptoteket responsible only for authenticated teacher interaction,
local saved intents, and replay/file action presentation. The final production
proof must show the approved compact labels, teacher interactions, correction
replay, and replay-scoped PDF/QTI artifact actions.

## Proposed Solution

The implementation introduces a narrow compact answer-key review-state adapter,
loads the first-pass compact report as the source projection authority, applies
top-level replay review state after correction-session apply, keeps local saved
intents out of file-readiness decisions, and updates the authenticated Exam
Converter list/detail/report/files surfaces to render the compact states.

## Artifacts to Review

| File | Focus | Reviewed |
|------|-------|----------|
| `docs/backlog/stories/story-21-11-cross-repo-compact-answer-key-review-state-production-proof.md` | ST-21-11 authority and final live gate | yes |
| `docs/backlog/prs/pr-0406-st-21-04-exam-converter-consume-compact-answer-key-review-state.md` | PR-0406 acceptance criteria, decisions, and test plan | yes |
| `.codex/handoff.md` | Current implementation and proof claims | yes |
| `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/reviews/review-58-ruthless-review-of-task-373-compact-answer-key-review-state.md` | Producer approval dependency | yes |
| `docs/mockups/pr-0406-answer-key-review-small-screen/README.md` | Approved small-screen copy/state authority | yes |
| `docs/mockups/pr-0406-answer-key-review-desktop/README.md` | Desktop copy/state alignment authority | yes |
| `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/answerKeyReviewStateAdapter.ts` | Strict producer projection adapter | yes |
| `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/answerKeyReviewStateAdapter.spec.ts` | Adapter fail-closed and label coverage | yes |
| `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/digiexamIrReviewParser.ts` | First-pass compact report consumption | yes |
| `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/correctionSessionProjection.ts` | Replay compact state and file action projection | yes |
| `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/useExamConverterReviewArtifacts.ts` | First-pass artifact loading | yes |
| `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/useExamConverterUnifiedCorrections.ts` | Local saved state versus replay projection | yes |
| `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/ExamConverterManualAnswerKeyEditor.vue` | Advisory/edit persistence UI | yes |
| `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedAiPrefillDurableSlice.spec.ts` | Advisory detail behavior tests | yes |
| `.artifacts/playwright-pr-0337-correction-session-live/20260629T121300Z/manifest.redacted.json` | Pre-remediation red proof | yes |
| `.artifacts/playwright-pr-0337-correction-session-live/20260629T122200Z/manifest.redacted.json` | Post-remediation green live proof | yes |

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Consume Sir Convert compact review state through one strict adapter. | The adapter validates the schema version, supported states/origins/reasons, rejects legacy `history` and `review_decision`, and fails closed on missing projection rows. | yes |
| Use first-pass `answer_key_review_state_report` as item review-state authority. | The parser now requires the compact report and applies it to projected questions instead of deriving current list truth from IR/report/readiness joins. | yes |
| Use replay top-level `answer_key_review_state` for correction-session projection. | Replay projection applies returned compact state and keeps locally saved readback separate from fresh Sir Convert truth. | yes |
| Keep file readiness separate from list state. | File actions require target readiness plus artifact references; draft/local state does not unlock save or download buttons. | yes |
| Render the pending advisory acceptance/edit contract. | Pass 2 adds the required pending advisory panel, unchanged acceptance, edit transition, and replay-backed proof. | yes |

## Review Checklist

- [x] Scope is bounded to PR-0406 and ST-21-11.
- [x] Sir Convert Task 373 producer approval artifact was reviewed.
- [x] Current worktree diff was inspected after confirming no implementation
  agent is active in this thread.
- [x] Strict adapter and schema/version/fallback behavior were reviewed.
- [x] First-pass and replay authority boundaries were reviewed.
- [x] File-readiness and artifact-action boundaries were reviewed.
- [x] Green live proof artifact was inspected.
- [x] Focused adapter/replay/file-action tests were run.
- [x] Blocking UI contract mismatch is documented with remediation proof
  requirements.
- [x] Pass-2 remediation diff, focused tests, script surface, and live proof
  artifact were reviewed.

## Review Feedback

**Reviewer:** ruthless-code-review
**Date:** 2026-06-29
**Verdict:** changes_requested

### Required Changes

1. **blocking - pending advisory review skips the required `Acceptera` / `Ändra` interaction**

   Authority requires a distinct pending advisory detail path: `Acceptera` is
   reserved for accepting an AI suggestion unchanged, while `Ändra` opens the
   normal selected-question answer-key editor with `Spara facit` and bounded
   `Tidigare förslag` detail
   (`docs/backlog/prs/pr-0406-st-21-04-exam-converter-consume-compact-answer-key-review-state.md:236`,
   `docs/backlog/prs/pr-0406-st-21-04-exam-converter-consume-compact-answer-key-review-state.md:283`,
   `docs/backlog/stories/story-21-11-cross-repo-compact-answer-key-review-state-production-proof.md:131`,
   `docs/backlog/stories/story-21-11-cross-repo-compact-answer-key-review-state-production-proof.md:138`,
   `docs/mockups/pr-0406-answer-key-review-small-screen/README.md:62`,
   `docs/mockups/pr-0406-answer-key-review-desktop/README.md:77`).

   The implementation instead renders the manual editor directly and exposes
   only `Spara facit` for the selected answer-key action
   (`frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/ExamConverterManualAnswerKeyEditor.vue:286`).
   The focused durable-slice test codifies this as intended behavior by asserting
   that an AI-seeded row has no selected-question AI suggestion panel and does
   have the manual editor immediately
   (`frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedAiPrefillDurableSlice.spec.ts:501`).
   A production-code search found no `Acceptera` label in the Exam Converter
   review/detail components; the only matching strings are docs, mockups, and
   report summary copy.

   This is not a copy-only issue. The retained green proof records
   `first_review_required_preparation: "unchanged"` and
   `first_saved_review_required_status: "Klart"`, but it cannot prove the
   approved unchanged-advisory acceptance path because that UI control does not
   exist. The current path also weakens the teacher-intent distinction the PR
   explicitly protects: unchanged AI acceptance must not be silently converted
   into a teacher-authored edit by another save click.

   Remediation required:

   - Add the pending advisory detail surface for producer-backed
     `review_required` advisory rows.
   - Render `Acceptera` for unchanged advisory acceptance.
   - Render `Ändra` as the transition into the existing normal answer-key editor.
   - Keep the editor's persistence action as `Spara facit` for manual selection,
     manual editing, and validation repair.
   - Show bounded `Tidigare förslag` provenance detail only in the detail/editor
     context; do not use it as list truth, completion truth, or file-readiness
     truth.
   - Update the focused component tests so they prove `Acceptera` unchanged and
     `Ändra` edit flows, and remove the assertion that no separate acceptance
     panel exists.
   - Rerun the live proof with retained evidence that the unchanged advisory path
     clicked `Acceptera` and that an advisory edit path clicked `Ändra` before
     `Spara facit`.

## Verification Evidence

| Command or artifact | Result |
|---------------------|--------|
| `pdm run fe-test -- --run src/views/apps/exam-converter-authenticated/answerKeyReviewStateAdapter.spec.ts src/views/apps/ExamConverterAuthenticatedCompactReviewState.spec.ts src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts src/views/apps/ExamConverterCorrectionSessionReplay.spec.ts` | Passed, 4 files / 22 tests. |
| `.artifacts/playwright-pr-0337-correction-session-live/20260629T121300Z/manifest.redacted.json` | Red pre-remediation proof stopped after conversion and draft negative proof. |
| `.artifacts/playwright-pr-0337-correction-session-live/20260629T122200Z/manifest.redacted.json` | Green for conversion, compact labels, disabled draft file actions, replay-scoped PDF/QTI download/save, reload persistence, and clean PDF/QTI inspection. Blocking gap: no evidence of `Acceptera` / `Ändra` because the UI path is absent. |
| `rg -n "Acceptera\|Ändra\|Tidigare förslag" frontend/apps/skriptoteket/src/views/apps docs/backlog/prs/pr-0406-st-21-04-exam-converter-consume-compact-answer-key-review-state.md docs/mockups/pr-0406-answer-key-review-small-screen/README.md docs/mockups/pr-0406-answer-key-review-desktop/README.md` | `Acceptera` appears in docs/mockups and report summary copy, not in the Exam Converter pending advisory detail UI. |

## Required Proof Before Approval

Run the focused component/harness proof:

```bash
pdm run fe-test -- --run src/views/apps/exam-converter-authenticated/answerKeyReviewStateAdapter.spec.ts src/views/apps/ExamConverterAuthenticatedCompactReviewState.spec.ts src/views/apps/ExamConverterAuthenticatedAiPrefillDurableSlice.spec.ts src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts src/views/apps/ExamConverterCorrectionSessionReplay.spec.ts
```

Then rerun the governed live proof against the deployed/remediated stack and
retain the new manifest:

```bash
pdm run python -m scripts.playwright_pr_0337_correction_session_live --base-url http://127.0.0.1:5173 --source-dxe /Users/olofs_mba/Documents/Repos/sir-convert-a-lot/inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe/1776888013-ak7-lag-och-ratt.dxe --timeout-seconds 60
```

The new proof must show `Acceptera` for unchanged advisory acceptance, `Ändra`
before the normal `Spara facit` editor for advisory edits, fresh Sir Convert
replay projection/readback before auto-advance, and replay-scoped PDF/QTI
actions remaining gated by target readiness plus artifact references.

## Review Pass 2

Pass 2 inspected the remediation for the pass-1 pending advisory finding. The
new `ExamConverterAdvisoryAnswerKeyPanel` renders only for producer-backed
`review_required` advisory rows, exposes `Acceptera` for unchanged advisory
acceptance, and exposes `Ändra` as the transition into the normal answer-key
editor. The new `useExamConverterAdvisoryAnswerKeyMode` state is local display
state only: it tracks whether the selected pending advisory row has entered edit
mode and prunes itself when the producer projection changes. It does not drive
list labels, completion, report state, target readiness, or file actions.

The persistence path stays on the existing correction intent and Sir Convert
replay boundary. Component tests now prove unchanged acceptance sends
`accepted_advisory_candidate`, edited advisory answers send
`teacher_edited_advisory_candidate`, accepted/edited rows render without a
current-key AI marker, and files remain blocked until replay returns target
readiness plus replay artifact references. The governed live proof at
`.artifacts/playwright-pr-0337-correction-session-live/20260629T125825Z/manifest.redacted.json`
records `Acceptera -> Klart`, CSRF-protected cleanup between probe flows,
`Ändra -> Ändrat`, disabled draft file actions, validation-row saves,
replay-scoped PDF/QTI download and save actions, reload persistence, and clean
PDF/QTI inspection.

No new blocking findings were found in pass 2.

## Review Pass 2 Decision

approved

## Review Pass 2 Verification

| Command or artifact | Result |
|---------------------|--------|
| `/opt/homebrew/bin/pdm run fe-test -- --run src/views/apps/exam-converter-authenticated/answerKeyReviewStateAdapter.spec.ts src/views/apps/ExamConverterAuthenticatedCompactReviewState.spec.ts src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts src/views/apps/ExamConverterAuthenticatedAiPrefillDurableSlice.spec.ts src/views/apps/ExamConverterAuthenticatedCorrectionSlice.spec.ts src/views/apps/exam-converter-authenticated/useExamConverterFileActions.spec.ts src/views/apps/ExamConverterCorrectionSessionReplay.spec.ts` | Passed, 8 files / 53 tests. |
| `/opt/homebrew/bin/pdm run pytest tests/unit/scripts/test_playwright_script_surface.py` | Passed, 7 tests. |
| `.artifacts/playwright-pr-0337-correction-session-live/20260629T125825Z/manifest.redacted.json` | Passed proof manifest: no `failed_at`, `Acceptera -> Klart`, `Ändra -> Ändrat`, draft downloads/saves disabled, replay artifact downloads/saves used `correction_replay_*` references, PDF/QTI inspection clean. |
| Code review/search of remediation files | No local review-state rederivation, legacy `history`/`review_decision` compatibility layer, browser-local export authority, direct browser-to-Sir-Convert bypass, or AI marker as current state truth found in the PR-0406 remediation. |

## Changes Made

- Added this retained review artifact with decision `changes_requested`.
- Updated this retained review artifact with pass-2 decision `approved`.
- No production or test code was modified by this review.
