---
type: review
id: REV-PR-0410
title: "Review: PR-0410 Exam Converter correction replay artifact-set consumer"
status: approved
owners: "agents"
created: 2026-06-30
updated: 2026-06-30
reviewer: "ruthless_review_agent"
prs:
  - PR-0410
links:
  - ST-21-11
  - PR-0406
  - PR-0408
  - /Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md
  - /Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-378-bind-correction-replay-artifacts-to-request-scoped-identity.md
---

## TL;DR

Approved for the bounded Skriptoteket PR-0410 consumer slice. The current diff
consumes full `correction_replay_artifact_reference_v1` references, rejects
stale or incomplete replay references, routes corrected replay download/save
byte fetches through the nested Sir Convert correction-replay artifact route,
and keeps first-pass/original job artifact actions on the existing named
artifact route. This review does not approve Sir Convert Story 58 closeout,
deployment, or live dev/prod proof.

## Problem Statement

PR-0410 must update the authenticated Exam Converter consumer after Sir Convert
Task 378 changes correction replay artifact authority from static
`correction_replay_*` named artifacts to request-scoped artifact-set
references. Missing or incomplete replay authority must fail closed and must
not fall back to original job artifacts, static correction-replay aliases, or
latest bytes.

## Proposed Solution

The implementation adds a nested Sir Convert Gateway download method, extends
the compact review-state adapter to require full replay-reference fields, carries
the replay job id, artifact set id, artifact key, and content digest through the
Exam Converter file-action projection, and switches replay-result file actions
to the nested route while preserving original-job actions for first-pass files.

## Artifacts to Review

| File | Focus | Reviewed |
|------|-------|----------|
| `docs/backlog/prs/pr-0410-st-21-11-correction-replay-artifact-set-consumer.md` | PR scope, non-goals, acceptance criteria, and deferred Story 58 closeout proof | yes |
| `docs/backlog/prs/pr-0406-st-21-04-exam-converter-consume-compact-answer-key-review-state.md` | Existing compact projection and file-readiness authority | yes |
| `docs/backlog/prs/pr-0408-st-21-04-exam-converter-frontend-design-implementation-alignment.md` | Adjacent replay/UI design boundaries | yes |
| `docs/backlog/reviews/review-pr-0406-exam-converter-compact-answer-key-review-state.md` | Prior retained review and replay-scoped action boundary | yes |
| `docs/backlog/reviews/review-pr-0408-exam-converter-frontend-design-implementation-alignment.md` | Prior retained review and Story 58 boundary context | yes |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/client.ts` and `client.spec.ts` | Nested correction replay artifact route and query encoding | yes |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/schemaVersions.ts`, `types.ts`, `sirConvertOpenapi.d.ts` | Contract shape for replay artifact references and route | yes |
| `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/answerKeyReviewStateAdapter.ts` and spec | Strict replay-reference parsing and fail-closed stale-shape rejection | yes |
| `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/digiexamIrReviewParser.ts` | First-pass original-job versus replay-reference action authority | yes |
| `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/correctionSessionProjection.ts` | Corrected replay file projection and missing-reference disablement | yes |
| `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/useExamConverterFileActions.ts` and spec | Download/save byte fetch routing for replay and original actions | yes |
| Impacted Exam Converter fixtures/specs | Behavioral proof for missing refs, nested route params, and file action gating | yes |
| `scripts/playwright_pr_0337_correction_session_live.py` | Retained proof script assertion of nested replay route and content digest | yes |

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Corrected replay artifact references must use `correction_replay_artifact_reference_v1`. | The parser now rejects stale `{artifact_key, target}`-only references, unknown fields, missing digest, unknown schema versions, and mismatched artifact-key/target pairs. | yes |
| Corrected replay file actions must use the nested Sir Convert route. | `useExamConverterFileActions` dispatches `replay_result` references to `downloadDigiExamMigrationCorrectionReplayArtifact` with `job_id`, `artifact_set_id`, `artifact_key`, and `content_sha256`. | yes |
| First-pass/original files must remain on the named artifact route. | `original_job` action references still call `downloadDigiExamMigrationArtifact`; this preserves the existing first-pass contract without using it as a replay fallback. | yes |
| Missing replay authority must fail closed. | Corrected replay projections return `artifactActionReference: null` when target readiness/availability exists but the replay reference is missing, so UI actions remain disabled instead of falling back. | yes |
| Browser proof updates are script-level readiness for later closeout, not Story 58 approval. | The Playwright script now records `artifact_set_id` and `content_sha256` from nested route responses, but live dev/prod proof remains a later story-closeout gate. | yes |

## Review Checklist

- [x] Read `AGENTS.md`, `.codex/handoff.md`, `docs/index.md`, `.codex/rules/000-rule-index.md`, rules `070`, `075`, and `096`, and the retained review workflow reference.
- [x] Used the review, testing, frontend, Playwright, and docs-governance skills/references required for this surface.
- [x] Inspected the current worktree diff for all PR-0410 files named in the review request.
- [x] Checked public contracts: Sir Convert Gateway route, replay reference schema, file-action projection type, and save/download behavior.
- [x] Checked data/runtime boundaries: no direct browser-to-Sir-Convert bypass, no product-local latest-byte lookup, no original-job fallback for corrected replay actions.
- [x] Checked typing and parser strictness for stale, missing, unknown, and mismatched replay references.
- [x] Audited tests for behavioral proof rather than helper-only assertions.
- [x] Kept final closeout scoped to PR-0410; Story 58 live dev/prod proof is not claimed here.

## Review Feedback

**Reviewer:** ruthless_review_agent
**Date:** 2026-06-30
**Verdict:** approved

### Findings

No blocking findings.

### Required Changes

None.

### Verification Evidence

| Command or evidence | Result |
|---|---|
| Code review of `answerKeyReviewStateAdapter.ts` and spec | Strict parser requires full replay-reference shape and rejects stale/incomplete references. |
| Code review of `digiexamIrReviewParser.ts`, `correctionSessionProjection.ts`, and `useExamConverterFileActions.ts` | Corrected replay actions require replay reference authority and use nested route params; original first-pass actions remain named-route only. |
| Code review of `scripts/playwright_pr_0337_correction_session_live.py` | Proof script now waits for nested correction replay artifact responses with `content_sha256` and records artifact-set evidence. |
| Parent-reported `pdm run fe-test -- --run src/api/sirConvertGateway/client.spec.ts src/views/apps/exam-converter-authenticated/answerKeyReviewStateAdapter.spec.ts src/views/apps/exam-converter-authenticated/useExamConverterFileActions.spec.ts` | Passed: 32 tests. |
| Parent-reported `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts` | Passed: 6 tests. |
| Parent-reported `pdm run fe-type-check` | Passed. |
| Parent-reported `pdm run fe-lint` | Passed. |
| Parent-reported `pdm run fe-build` | Passed with existing Vite chunk/dynamic-import warnings. |
| Parent-reported `pdm run docs-validate` | Passed. |
| Parent-reported `git diff --check` | Passed. |

### Non-Blocking Risks

- Live dev/prod browser proof for the nested replay route is still a Story 58
  closeout gate and is not approved by this PR-0410 retained review.
- Several touched legacy modules remain above the repo's preferred 400-500 line
  size guideline. This review does not block PR-0410 on that pre-existing
  shape because the bounded slice is contract-hardening and the changed behavior
  is covered, but later cleanup should split these surfaces when a governed
  refactor slice owns it.

### Decision

approved

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0410` | Added this retained independent review artifact with decision `approved`. |
