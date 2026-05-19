---
type: review
id: REV-PR-0333
title: "Review: Correction-session backend aggregate and persistence"
status: changes_requested
owners: "agents"
created: 2026-05-19
updated: 2026-05-19
reviewer: "Codex"
prs:
  - PR-0333
adrs:
  - ADR-0087
links:
  - EPIC-21
  - ST-21-04
  - PR-0335
  - PR-0336
  - PR-0337
---

# Review: PR-0333 Correction-Session Backend Aggregate And Persistence

## TL;DR

Verdict: `changes_requested`.

The re-review verified that two narrow defects were patched:
`candidate_suppression` and `review_decision` now reach Sir Convert replay, and
the backend aggregate now rejects the forbidden answer-key/review-decision
family. That is not enough to approve the slice. The implementation still
bundles AI suggestion review, teacher editing, and persisted effective exam
state into one UI model, so actions such as "Acceptera", "Redigera", "Ta bort",
and "Spara facit" remain ambiguous. The product must be redesigned around the
core invariant: teacher-visible applied truth comes only from durable readback
plus Sir Convert replay, not local browser state.

## Problem Statement

`PR-0333` established the Skriptoteket-owned correction-session aggregate and
persistence boundary for `ST-21-04`. The critical contract is that durable
teacher intent truth is source-bound, owner/job-scoped, conflict-safe, and later
replayable through the stateless Sir Convert apply edge without claiming that
Sir Convert owns persistence.

This review checks the post-remediation state after the UI/Sir Convert replay
path was found to persist some decisions locally without submitting them to the
producer apply route.

## Proposed Solution

Keep `PR-0333` as the backend aggregate/persistence slice, but verify the
adjacent replay and UI contract because the original implementation commit
crossed into `PR-0335`/`PR-0336` surfaces. Approval here is limited to the
`PR-0333` aggregate/persistence contract and the remediation of the replay
contract regression that made persisted decisions non-effective.

## Artifacts to Review

| File | Focus | Result |
|------|-------|--------|
| `docs/backlog/prs/pr-0333-st-21-04-correction-session-backend-aggregate-and-persistence.md` | PR authority and acceptance criteria | Approved |
| `docs/adr/adr-0087-exam-converter-durable-correction-sessions-with-stateless-apply.md` | Durable-session invariants | Approved |
| `src/skriptoteket/domain/curated_apps/exam_converter_correction_sessions.py` | Current-set conflicts and replay ordering | Approved |
| `tests/unit/domain/curated_apps/test_exam_converter_correction_sessions.py` | Aggregate proof | Approved |
| `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/correctionSessionReplay.ts` | Complete persisted set sent to Sir Convert apply | Approved |
| `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/correctionSessionIntentBuilders.ts` | Accepted-vs-edited advisory provenance | Approved |
| `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts` | UI proof that `review_decision` reaches apply | Approved |
| `frontend/apps/skriptoteket/src/views/apps/ExamConverterCorrectionSessionReplay.spec.ts` | Replay proof for `candidate_suppression` | Approved |
| `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue` | Per-question AI-seeded save wiring | Changes requested |
| `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/ExamConverterManualAnswerKeyEditor.vue` | AI-seeded editor save event | Changes requested |
| `scripts/playwright_pr_0337_correction_session_live.py` | Live proof path for saving one AI-seeded key | Changes requested |

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Skriptoteket owns durable correction-session persistence | Matches `ADR-0087`; Sir Convert remains stateless apply authority | [x] |
| `candidate_suppression` and `review_decision` are submitted during replay | Persisted decisions must affect producer-derived projection/export truth | [x] |
| Answer-key and `review_decision` intents conflict for the same item family | Prevents contradictory current-set truth before replay/export | [x] |
| Accepted unchanged advisory suggestions keep `accepted_advisory_candidate` provenance | Avoids hiding accepted-vs-edited teacher provenance | [x] |
| Per-question AI-seeded save preserves the intended AI-key workflow | Required for the actual teacher UI path and PR-0337 live proof | [ ] |
| UI separates AI review, teacher editing, and replayed effective state | Prevents copy/status controls from explaining contradictory state | [ ] |
| Browser state is draft-only until durable readback and replay prove truth | Preserves the central `ADR-0087` invariant | [ ] |

## Review Checklist

- [x] Scope is bounded and appropriate
- [x] Acceptance criteria or proof obligations are reviewable
- [x] Risks and structural fault lines are called out explicitly
- [x] Verification plan matches the claimed contract
- [x] Prior blockers were rechecked directly

## Review Feedback

**Reviewer:** Codex
**Date:** 2026-05-19
**Verdict:** changes_requested

### Required Changes

1. Separate the UI model into three explicit concepts: AI suggestion review,
   teacher draft/editing, and persisted effective exam state. The current panel
   mixes them, so "Acceptera", "Redigera", "Ta bort", and "Spara facit" can
   contradict each other. The fix should produce distinct state machines and
   visible affordances for advisory candidate decisions, teacher-authored
   drafts, durable persisted intents, and replayed effective state.

2. Treat browser/UI state as draft-only. The UI must not show accepted, saved,
   changed, ready, or file-unlocked truth until the relevant correction has
   round-tripped through Skriptoteket persistence, durable readback, Sir Convert
   replay, and projection/readiness rendering. Local transitions may show
   pending progress only.

3. `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue`
   wires `@apply-manual-answer-key` directly to `handleApplyManualAnswerKey`,
   while `useExamConverterAiFacitReview` exposes `acceptSuggestion`,
   `acceptEditedChoiceSuggestion`, and `acceptEditedGapFillSuggestion` that are
   not consumed by the view. When the editor is prefilled from an AI candidate
   and the teacher clicks "Spara facit", the UI does not commit through the AI
   review decision path that preserves candidate lineage and accepted-vs-edited
   semantics. Split the action handler so AI-seeded saves either commit
   `accepted_advisory_candidate` when unchanged or
   `teacher_edited_advisory_candidate` when changed, then persist/replay that
   complete intent set.

4. Remove UX copy and status surfaces that paper over invalid state. Messages,
   pills, disabled overlays, "missing facit", "changed", "partial conversion",
   and file-readiness states should be derived from the corrected state model.
   Do not use labels to explain a state that cannot be represented by the
   contract.

5. Replace the happy-path proof shape with the real teacher workflow: click,
   persist, read back, replay, render, export readiness, and download. The
   tests must prove both accepted AI candidates and edited AI candidates through
   the same path a teacher actually uses, plus stale/unavailable states where
   local truth must not unlock files.

6. `scripts/playwright_pr_0337_correction_session_live.py` currently exercises
   `_save_visible_answer_key()` through the manual answer-key button, but the
   retained review must not treat that as proof that "AI keys save" unless the
   resulting request/manifest proves the saved intent retained candidate
   lineage and the correct `submission_origin`. Extend the proof to retain that
   request evidence or add a focused Vitest assertion for the same per-question
   path.

The previous replay blocker is resolved: `candidate_suppression` and
`review_decision` are now included in `SUPPORTED_REPLAY_KINDS`, and the focused
review-slice test confirms accepting current-state export submits a
`review_decision` correction to the Sir Convert apply client.

The previous aggregate blocker is resolved: `REVIEW_DECISION` is now part of
the conflict family, same-batch answer-key/review-decision writes are rejected,
and a later `review_decision` supersedes the prior answer-key intent for the
same source-bound family.

The previous provenance concern is resolved for accepted advisory suggestions:
`accepted_unchanged` maps to `accepted_advisory_candidate`, while edited
suggestions map to `teacher_edited_advisory_candidate`. That proof currently
covers the accept-all decision path, not the per-question editor save path.

### Retained Findings From 2026-05-19 UI/Contract Re-review

1. The UI mixed three different concepts: AI suggestion review, teacher editing,
   and persisted effective exam state. This made "Acceptera", "Redigera",
   "Ta bort", and "Spara facit" ambiguous and sometimes contradictory.
2. Browser/UI state was treated as if it could explain truth. Local accepted,
   saved, and changed transitions were shown before durable readback plus Sir
   Convert replay had proven the effective state.
3. Replay had filtered out parts of the durable active set. The direct code
   defect is patched for `candidate_suppression` and `review_decision`, but the
   proof burden remains: all persisted supported decisions must be submitted to
   Sir Convert apply before UI/export readiness claims truth.
4. Provenance was masked. Accepted AI suggestions had been rewritten as
   teacher-edited in places. The accept-all path is fixed, but the per-question
   save path still needs proof.
5. The backend aggregate allowed incompatible state. The direct answer-key plus
   review-decision coexistence defect is patched and covered by unit tests.
6. Tests were too mocked and too happy-path. They proved function shapes, not
   the complete teacher workflow from click to durable readback, replay,
   render, export readiness, and download.
7. The UX kept papering over contract confusion. The fix must remove the broken
   state model, not add more explanatory statuses around it.

### Suggestions

`PR-0337` still owns retained browser/artifact evidence. Before approving that
proof slice, its live script or retained evidence should show candidate
suppression where available, because `PR-0337` explicitly promises proof for
points, choice keys, gap/open-cloze keys, item text, review decisions, and
candidate suppression in the complete Sir Convert apply set.

## Verification

- `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterCorrectionSessionReplay.spec.ts src/views/apps/ExamConverterAuthenticatedReviewedAiDurableSlice.spec.ts src/views/apps/ExamConverterAuthenticatedCorrectionSlice.spec.ts`
- `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts`
- `pdm run test tests/unit/domain/curated_apps/test_exam_converter_correction_sessions.py`
- `pdm run test tests/unit/scripts/test_playwright_script_surface.py`

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0333` | Retained re-review created after direct blocker verification. |
| 2 | `REV-PR-0333` | Verdict corrected to `changes_requested` after identifying that the per-question AI-seeded save path still bypasses the AI review-decision workflow. |
| 3 | `REV-PR-0333` | User's UI/contract findings retained as active blockers: mixed state concepts, browser-local truth leakage, insufficient workflow proof, and UX papering over contract confusion. |
