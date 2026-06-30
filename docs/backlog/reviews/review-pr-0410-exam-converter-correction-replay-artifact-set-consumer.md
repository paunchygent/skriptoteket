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
| Production proof `.artifacts/playwright-pr-0337-correction-session-live/20260630T014512Z/manifest.redacted.json` | Exact `ak7_lag_och_ratt_with_image.dxe` filename proof passed after HuleEdu `TASK-0831`; PDF/QTI replay downloads and Save to My Files returned `200`. |
| Production proof `.artifacts/playwright-pr-0337-correction-session-live/20260630T015236Z/manifest.redacted.json` | Same DXE bytes with run-scoped filename passed and retained `service-monitoring.json` plus `service-logs/*.log` from Skriptoteket, HuleEdu Gateway/File Service, and Sir Convert containers. |
| Dev proof `.artifacts/playwright-pr-0337-correction-session-live/20260630T020711Z/manifest.redacted.json` | Same DXE bytes passed through local shared-auth, local HuleEdu Gateway, local Sir Convert, and Skriptoteket Docker; PDF/QTI replay downloads and Save to My Files returned `200` with retained local Docker service logs. |
| Current production proof `.artifacts/playwright-pr-0337-correction-session-live/20260630T110339Z/manifest.json` | Real `ak7_lag_och_ratt_with_image.dxe` run-scoped copy passed through production shared auth and Gateway; Sir Convert returned fresh admission followed by in-run strict replay, nested replay PDF/ZIP downloads returned `200`, Save to My Files returned `200`, PDF inspection passed with 6 pages, QTI inspection passed with 9 XML files and 37 correct responses, and retained Hemma Gateway/File/Sir Convert/Skriptoteket service logs show the handled requests. |
| Current Dev proof `.artifacts/playwright-pr-0337-correction-session-live/20260630T111643Z/manifest.json` | Same real DXE bytes with a run-scoped filename passed through local shared-auth, local HuleEdu Gateway, local Sir Convert, and Skriptoteket Docker; fresh admission followed by in-run strict replay, nested replay PDF/ZIP downloads returned `200`, Save to My Files returned `200`, PDF/QTI inspection passed, and retained local Docker service logs show the handled requests. |

### Non-Blocking Risks

- The 2026-06-30 production failure was a HuleEdu Gateway route gap, not a
  Skriptoteket consumer regression. The Dev/Prod proofs above satisfy the
  PR-0410 consumer-route incident proof only; they do not close Sir Convert
  Story 58's broader stale-replay and correction-replay live proof gate.
- Preserve-source reruns against an already processed DXE can replay an existing
  ready job and hit a persisted correction-session version conflict before file
  actions, as captured at
  `.artifacts/playwright-pr-0337-correction-session-live/20260630T110042Z/manifest.json`;
  that is not the original download/save failure.
- The first local Dev rerun after service startup hit a Gateway connect timeout
  to local Sir Convert before file actions, as captured at
  `.artifacts/playwright-pr-0337-correction-session-live/20260630T111335Z/manifest.json`;
  Gateway-to-Sir-Convert readiness then returned `200` and the subsequent Dev
  proof passed.
- Local proof setup needs both Skriptoteket shared-auth Vite on `:5173` and the
  HuleEdu auth frontend on `:5174`; a missing auth frontend produced
  `chrome-error://chromewebdata/` before upload in
  `.artifacts/playwright-pr-0337-correction-session-live/20260630T083201Z/failure-page-state.json`.
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
| 2 | `REV-PR-0410` | Added follow-up retained review for the Story 58 proof-harness extension with decision `approved`. |

## Follow-Up Review: Story 58 Proof Harness Evidence Extension

**Reviewer:** Codex retained reviewer
**Date:** 2026-06-30
**Verdict:** approved

### Scope

- `scripts/_story58_private_request_capture.py`
- `scripts/_story58_mismatched_artifact_probe.py`
- `scripts/playwright_pr_0337_correction_session_live.py`
- `tests/unit/scripts/test_story58_private_request_capture.py`

This follow-up review covers only the opt-in proof-harness extension for Sir
Convert Story 58 closeout. It does not approve product behavior changes,
producer behavior, deployment, or the final live Story 58 proof result.

### Findings

No blocking findings.

### Review Notes

- The new `--story58-private-request-capture-dir` flag is opt-in and preserves
  the existing PR-0337 request summary path when absent.
- Raw POST bodies for the source-state issue and correction apply routes are
  written only to the operator-provided private directory.
- The public manifest summary retains route/method, counts, safe identifiers,
  and SHA-256 digests, but does not retain raw request bodies, private paths,
  source-state signatures, identity/grant envelopes, idempotency keys, uploaded
  bytes, source text, provider prompts, or fixture secret markers covered by
  the focused tests.
- The helper rejects a private capture directory nested inside the retained
  artifact directory, preventing accidental promotion of raw bodies into the
  public proof bundle.
- Existing `correction_apply_requests` summary behavior remains wired before
  the private capture hook.
- The mismatched artifact probe reuses the real nested replay artifact download
  evidence, corrupts only the `content_sha256` query value, and requires a
  fail-closed `404` or `409 correction_replay_artifact_reference_mismatch`
  result.
- The canonical PR-0337 proof script remains the active proof entrypoint; the
  new behavior is helper-backed and opt-in/inline rather than a parallel proof
  script or browser-local fallback.

### Verification Evidence

| Command or evidence | Result |
|---|---|
| Code review of `Story58PrivateRequestCapture` | Private raw-body writes and public summary boundaries match the Story 58 evidence contract. |
| Code review of `scripts/_story58_mismatched_artifact_probe.py` | Mismatch proof mutates only `content_sha256`, summarizes only approved request/error metadata, and asserts fail-closed `404`/`409` outcomes. |
| Code review of `scripts/playwright_pr_0337_correction_session_live.py` | Existing PR-0337 proof behavior is preserved unless the opt-in private directory flag is supplied. |
| Reviewer-run `pdm run test tests/unit/scripts/test_story58_private_request_capture.py` | Passed: 9 tests. |
| Parent-reported `pdm run lint` | Passed. |
| Parent-reported `pdm run typecheck` | Passed. |
| Reviewer-run `git diff --check -- scripts/playwright_pr_0337_correction_session_live.py scripts/_story58_private_request_capture.py scripts/_story58_mismatched_artifact_probe.py tests/unit/scripts/test_story58_private_request_capture.py docs/backlog/reviews/review-pr-0410-exam-converter-correction-replay-artifact-set-consumer.md` | Passed before this retained-review artifact update. |
| Production proof `.artifacts/playwright-pr-0337-correction-session-live/20260630T143803Z/manifest.redacted.json` | Real `ak7_lag_och_ratt_with_image.dxe` proof retained nested PDF/QTI replay downloads `200`, Save to My Files `200`, mismatch probe `409 correction_replay_artifact_reference_mismatch`, service logs, and public private-capture summary counts `30` total requests: `8` correction apply and `22` source-state issue. |
| Reviewer redaction scan of `.artifacts/playwright-pr-0337-correction-session-live/20260630T143803Z/manifest.redacted.json` | No raw request bodies, private capture paths, source-state signatures, identity/grant envelope, provider prompt, or source text terms were present in the Story 58 private-capture public summary. |

### Residual Risks

- The live run still needs operator-supplied private storage with appropriate
  local permissions and retention handling; this review only verifies the
  harness does not copy raw request bodies into retained public artifacts.
- The public manifest intentionally includes request/job identifiers and
  digest metadata as proof metadata. Treat the manifest as retained proof
  evidence, not as a broadly publishable public report.
- Final Story 58 closeout still depends on the broader Sir Convert Story 58
  closeout packet; this review approves only the downstream/product
  proof-harness tranche and its production evidence.
