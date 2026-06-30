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

## Follow-Up Implementation Evidence: Final Summary Write Masking Fix

**Implementer:** implementation_agent
**Date:** 2026-06-30
**Status:** implemented; not final Story 58 closeout

### Scope

- `scripts/playwright_pr_0337_correction_session_live.py`
- `tests/unit/scripts/test_story58_private_request_capture.py`

### Prior Finding Resolution

The PR-0337 Playwright proof harness now tracks the active exception from the
main live-run body and passes it into the outer `finally` summary write. The
final manifest write remains strict on successful runs, but when an original
login/conversion exception is already propagating, a secondary
`_write_summary` failure is recorded in `failure_artifact_errors` as
`final_summary` and cannot replace the original exception observed by the
caller.

This fixes the rereview finding without changing Story 58 closeout status or
claiming the broader Dev/Prod stale replay matrix is complete.

### Verification Evidence

| Command or evidence | Result |
|---|---|
| Red-first `pdm run test tests/unit/scripts/test_story58_private_request_capture.py -k final_summary_write_failure_does_not_mask_active_exception` | Failed before implementation with `AttributeError: module 'scripts.playwright_pr_0337_correction_session_live' has no attribute '_write_final_summary'`. |
| Green `pdm run test tests/unit/scripts/test_story58_private_request_capture.py -k final_summary_write_failure_does_not_mask_active_exception` | Passed: 1 selected test. |

## Follow-Up Implementation Evidence: PR-0337 Failure Artifact Preservation

**Implementer:** implementation_agent
**Date:** 2026-06-30
**Status:** implemented; not final Story 58 closeout

### Scope

- `scripts/playwright_pr_0337_correction_session_live.py`
- `tests/unit/scripts/test_story58_private_request_capture.py`

### Evidence Note

The PR-0337 Playwright proof harness now records the original failure
exception type and message in the retained summary before attempting failure
diagnostics. Failure screenshot and failure page-text capture are best-effort:
if either secondary artifact capture fails, the harness records that secondary
error in `failure_artifact_errors` and still re-raises the original exception.

### Verification Evidence

| Command or evidence | Result |
|---|---|
| Red-first `pdm run test tests/unit/scripts/test_story58_private_request_capture.py -k failure_artifacts_do_not_mask_original_exception_metadata` | Failed before implementation with `AttributeError: module 'scripts.playwright_pr_0337_correction_session_live' has no attribute '_record_failure_artifacts'`. |
| Green `pdm run test tests/unit/scripts/test_story58_private_request_capture.py -k failure_artifacts_do_not_mask_original_exception_metadata` | Passed: 1 test selected. |
| Green `pdm run test tests/unit/scripts/test_story58_private_request_capture.py` | Passed: 10 tests. |

## Independent Follow-Up Review: PR-0337 Failure Artifact Preservation

**Reviewer:** ruthless_review_agent
**Date:** 2026-06-30
**Verdict:** changes_requested

### Scope

- `scripts/playwright_pr_0337_correction_session_live.py`
- `tests/unit/scripts/test_story58_private_request_capture.py`
- `docs/backlog/reviews/review-pr-0410-exam-converter-correction-replay-artifact-set-consumer.md`

This review covers only the failure-artifact preservation follow-up. It does
not approve final Sir Convert Story 58 closeout, deployment, stale-replay
proof, or producer behavior.

### Findings

#### High: final manifest write can still mask the original live-run exception

`scripts/playwright_pr_0337_correction_session_live.py:1380` catches a
diagnostic `_write_summary` failure and records it as a secondary
`failure_artifact_errors` entry, but
`scripts/playwright_pr_0337_correction_session_live.py:1759` then calls
`_write_summary(summary, artifact_dir)` unguarded from `finally`. If manifest
writing is the failing secondary artifact operation, that final write raises
after the `except` block has re-raised the original login or conversion
exception, so Python replaces the original exception with the cleanup/write
exception. That means the follow-up still does not satisfy the required
behavior for summary-write failures.

Fix: make the final failure-path summary write best-effort as well, or gate the
`finally` manifest write so that once an original exception is being propagated
no later diagnostic write can replace it. Preserve the original exception
metadata in the in-memory summary before any diagnostic capture, record
secondary write errors when possible, and re-raise the original exception.

Proof required:
`pdm run test tests/unit/scripts/test_story58_private_request_capture.py -k failure_artifacts_do_not_mask_original_exception_metadata`

Add coverage that simulates `_write_summary` raising during failure cleanup and
asserts the caller still observes the original exception, not the manifest
writer exception. The existing focused test only covers screenshot/title-text
capture failures.

### Review Notes

- Screenshot capture and failure text capture are now best-effort and no longer
  mask the original exception in the helper itself.
- Retained exception metadata is acceptable for this proof harness as bounded
  diagnostics: the reviewed code stores exception type and message, while the
  existing raise sites mostly use operator-facing assertion messages and
  sanitized paths/statuses. Do not add response bodies, credentials, private
  request paths, raw source text, provider prompts, or identity/grant material
  to exception messages.
- The focused regression is meaningful for screenshot/text failures, but it is
  not sufficient for the stated summary-write masking requirement.
- The documentation correctly says this is implemented evidence only and does
  not claim final Story 58 closeout.

### Verification Evidence

| Command or evidence | Result |
|---|---|
| Reviewer code review of `scripts/playwright_pr_0337_correction_session_live.py` | The helper catches screenshot/text/first summary failures, but the outer `finally` still performs an unguarded summary write. |
| Reviewer-run `pdm run test tests/unit/scripts/test_story58_private_request_capture.py -k failure_artifacts_do_not_mask_original_exception_metadata` | Passed: 1 selected test; coverage is too narrow for summary-write masking. |
| Context7 Playwright Python docs lookup for sync screenshot/title/locator APIs | Confirmed the reviewed diagnostic calls are current Playwright Python API surfaces. |

### Decision

changes_requested

## Independent Rereview: Final Summary Write Masking Fix

**Reviewer:** ruthless_review_agent
**Date:** 2026-06-30
**Verdict:** approved

### Scope

- `scripts/playwright_pr_0337_correction_session_live.py`
- `tests/unit/scripts/test_story58_private_request_capture.py`
- `docs/backlog/reviews/review-pr-0410-exam-converter-correction-replay-artifact-set-consumer.md`

This rereview covers only the PR-0337 failure-preservation fix for final
summary writes. It does not approve final Sir Convert Story 58 closeout,
deployment, stale-replay proof, producer behavior, or the full Dev/Prod
duplicate/distinct/stale replay matrix.

### Findings

No blocking findings.

### Review Notes

- The prior finding is resolved. The final `finally` path now calls
  `_write_final_summary(...)` with the tracked `active_exception`; if an
  original login/conversion/live-run exception is already propagating, a
  secondary `_write_summary` failure is recorded as `final_summary` and is not
  allowed to replace the original exception observed by the caller.
- The success path remains strict enough: `_write_final_summary(...)` re-raises
  manifest writer failures when `active_exception is None`, so a successful run
  cannot silently skip its retained summary.
- The regression is meaningful for the prior bug class. It simulates the final
  manifest writer failing while an original exception is active and asserts the
  exact original exception object is still raised, with the secondary writer
  failure retained in `failure_artifact_errors`.
- The retained review wording correctly keeps this as proof-harness follow-up
  evidence only and avoids claiming final Story 58 closeout.

### Verification Evidence

| Command or evidence | Result |
|---|---|
| Reviewer code review of `scripts/playwright_pr_0337_correction_session_live.py` | `_write_final_summary(...)` is strict on success and non-masking only when an active exception is present. |
| Reviewer-run `pdm run test tests/unit/scripts/test_story58_private_request_capture.py -k final_summary_write_failure_does_not_mask_active_exception` | Passed: 1 selected test. |
| Reviewer-run `pdm run test tests/unit/scripts/test_story58_artifact_set_invariants.py tests/unit/scripts/test_story58_private_request_capture.py tests/unit/scripts/test_story58_artifact_route_probe.py` | Passed: 24 tests. |
| Parent-run `pdm run lint` | Passed. |
| Parent-run `pdm run typecheck` | Passed with the existing `docx.*` note. |
| Parent-run `pdm run docs-validate` | Passed before this retained-rereview update. |
| Parent-run `git diff --check` | Passed before this retained-rereview update. |

### Decision

approved

## Follow-Up Implementation Evidence: Story 58 Comparable Product-Route Snapshots

**Implementer:** implementation_agent
**Date:** 2026-06-30
**Status:** implemented; not final Story 58 closeout

### Scope

- `scripts/_story58_artifact_route_probe.py`
- `scripts/_story58_artifact_observations.py`
- `scripts/_story58_artifact_set_invariants.py`
- `scripts/_story58_mismatched_artifact_probe.py`
- `scripts/playwright_pr_0337_correction_session_live.py`
- `tests/unit/scripts/test_story58_artifact_set_invariants.py`
- `tests/unit/scripts/test_story58_artifact_route_probe.py`
- `tests/unit/scripts/test_story58_private_request_capture.py`

### Evidence Note

The canonical PR-0337 Playwright proof harness now supports comparable Story 58
artifact-set observations before the final download/save assertions. It first
attempts safe apply-response reference probes through the authenticated
`page.request` context and nested correction replay route, failing on any
attempted non-2xx route response. Because the current retained production
manifest shape may omit `correction_replay_artifact_references` from apply
responses, the harness also records product-route PDF artifact-set snapshots
from the canonical browser flow after an exportable answer-key baseline and
again after a later distinct point/prompt correction while file actions remain
exportable. The existing reload/final file-action proof then provides the
duplicate replay observation.

Snapshots retain only approved artifact/request digest metadata:
`artifact_set_id`, `artifact_key`, `content_sha256`, nested route path/status,
`observed_via`, UI artifact key, request id/occurrence, request digest, and
already-redacted source/correction digest fields. They do not retain raw
response bytes, raw correction bodies, private paths, source text,
identity/grants, idempotency keys, or provider material.

### Verification Evidence

| Command or evidence | Result |
|---|---|
| Red-first `pdm run test tests/unit/scripts/test_story58_artifact_set_invariants.py tests/unit/scripts/test_story58_private_request_capture.py` | Failed before implementation with `ModuleNotFoundError: No module named 'scripts._story58_artifact_route_probe'`. |
| Green `pdm run test tests/unit/scripts/test_story58_artifact_set_invariants.py tests/unit/scripts/test_story58_artifact_route_probe.py tests/unit/scripts/test_story58_private_request_capture.py` | Passed: 22 tests. |
| `pdm run lint` | Passed. |
| `pdm run typecheck` | Passed: no issues in 1166 source files; existing unused `pyproject.toml` section note. |
| `pdm run docs-validate` | Passed. |
| `git diff --check` | Passed. |

### Residual Live-Proof Gap

This implementation extends the proof surface only. It does not claim final
Sir Convert Story 58 closeout. Stale replay still requires the operator/private
inputs and governed live setup needed to produce the final Dev/Prod
duplicate/distinct/stale replay matrix.

## Independent Review: Story 58 Comparable Product-Route Snapshots

**Reviewer:** ruthless_review_agent
**Date:** 2026-06-30
**Verdict:** approved

### Scope

- `scripts/_story58_artifact_observations.py`
- `scripts/_story58_artifact_route_probe.py`
- `scripts/_story58_artifact_set_invariants.py`
- `scripts/_story58_mismatched_artifact_probe.py`
- `scripts/playwright_pr_0337_correction_session_live.py`
- `tests/unit/scripts/test_story58_artifact_set_invariants.py`
- `tests/unit/scripts/test_story58_artifact_route_probe.py`
- `tests/unit/scripts/test_story58_private_request_capture.py`
- `docs/backlog/reviews/review-pr-0410-exam-converter-correction-replay-artifact-set-consumer.md`

This review covers only the bounded proof-harness extension for comparable
Story 58 product-route artifact-set observations. It does not approve final
Sir Convert Story 58 closeout, deployment, stale-replay proof, or producer
behavior.

### Findings

No blocking findings.

### Review Notes

- The change extends the canonical PR-0337 Playwright proof harness instead of
  adding a parallel proof script or using API-key-only proof.
- Product-route observations use the authenticated Playwright request/browser
  context and the nested Sir Convert correction replay artifact route.
- The harness now records an exportable baseline PDF route snapshot, a
  post-distinct-correction PDF route snapshot, and final replay download/save
  route snapshots so duplicate and distinct rows are not inferred from a final
  download alone.
- Apply-response reference probing is fail-closed for attempted non-2xx nested
  artifact routes, while missing apply-response references remain explicit
  skipped/unproven evidence rather than fabricated proof.
- Public retained Story 58 metadata remains bounded to approved request/artifact
  identifiers, digests, route path/status, source/correction digests already
  allowed by the proof lane, and occurrence context. The reviewed paths do not
  retain raw response bytes, correction bodies, private paths, source text,
  identity/grant envelopes, idempotency keys, provider prompts, or uploaded
  bytes in the new Story 58 observation summaries.
- Tests are behavioral enough for this harness slice: final-only evidence stays
  `unproven`, comparable product-route snapshots can prove duplicate/distinct
  rows, non-2xx route probes fail, and redaction boundaries are asserted.
- The helper split improves SRP around route probing, observation assembly, and
  invariant classification. Existing large proof-harness size remains a
  pre-existing retained-script concern, not a new blocker for this narrow
  extension.

### Verification Evidence

| Command or evidence | Result |
|---|---|
| Reviewer-run `pdm run test tests/unit/scripts/test_story58_artifact_set_invariants.py tests/unit/scripts/test_story58_artifact_route_probe.py tests/unit/scripts/test_story58_private_request_capture.py` | Passed: 22 tests. |
| Reviewer-run `pdm run lint` | Passed. |
| Reviewer-run `pdm run typecheck` | Passed: no issues in 1166 source files; existing unused `pyproject.toml` docx section note. |
| Reviewer-run `git diff --check` | Passed before this retained-review update. |
| Reviewer-run `pdm run docs-validate` | Passed after this retained-review update. |
| Reviewer-run `git diff --check` | Passed after this retained-review update. |

### Residual Risks

- This approval is for proof-harness capability only. Final Story 58 closeout
  still requires governed live Dev/Prod evidence for the full
  duplicate/distinct/stale replay matrix with the required private/operator
  inputs.
- The PR-0337 proof entrypoint remains intentionally large and should be split
  only under a separate governed refactor slice so the canonical retained proof
  behavior is not changed opportunistically.

### Decision

approved

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0410` | Added this retained independent review artifact with decision `approved`. |
| 2 | `REV-PR-0410` | Added follow-up retained review for the Story 58 proof-harness extension with decision `approved`. |
| 3 | `REV-PR-0410` | Added follow-up retained review for the Story 58 artifact-set invariant extension with decision `changes_requested`. |
| 4 | `REV-PR-0410` | Added rereview for the Story 58 artifact-set invariant extension with decision `approved`. |
| 5 | `REV-PR-0410` | Added independent follow-up review for comparable Story 58 product-route snapshots with decision `approved`. |
| 6 | `REV-PR-0410` | Added independent follow-up review for PR-0337 failure artifact preservation with decision `changes_requested`. |
| 7 | `REV-PR-0410` | Added implementation evidence for the final summary write masking fix; Story 58 closeout remains open. |
| 8 | `REV-PR-0410` | Added independent rereview for the final summary write masking fix with decision `approved`; Story 58 closeout remains open. |
| 9 | `REV-PR-0410` | Added independent review for Story 58 selected-detail proof-harness stabilization with decision `changes_requested`. |
| 10 | `REV-PR-0410` | Added independent rereview for Story 58 selected-detail proof-harness stabilization with decision `approved`; Story 58 closeout remains open. |

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
- The Story 58 artifact-set invariant extension adds public manifest fields
  `story58_artifact_set_snapshots` and `story58_artifact_set_invariants`.
  Snapshots retain only request/artifact digest metadata from real product-route
  replay downloads or saves, and invariant rows must report `pass`, `fail`, or
  `unproven` instead of inferring duplicate/distinct replay proof from final
  downloads alone.
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

## Follow-Up Review: Story 58 Artifact-Set Invariant Extension

**Reviewer:** ruthless_review_agent
**Date:** 2026-06-30
**Verdict:** changes_requested

### Scope

- `scripts/_story58_artifact_set_invariants.py`
- `tests/unit/scripts/test_story58_artifact_set_invariants.py`
- `scripts/playwright_pr_0337_correction_session_live.py`
- `docs/backlog/reviews/review-pr-0410-exam-converter-correction-replay-artifact-set-consumer.md`

### Findings

#### High: Canonical manifest still retains correction-row metadata outside the approved digest-only evidence contract

`scripts/playwright_pr_0337_correction_session_live.py:192` builds the public
`correction_apply_requests` manifest summary, and lines `197-207` still retain a
`corrections` array with per-correction fields copied from the request body.
That summary is appended to the retained proof manifest at
`scripts/playwright_pr_0337_correction_session_live.py:1294-1295`. For this
Story 58 proof-harness extension, retained public evidence is limited to
request/body/correction digests, request id, job/source digests when already
retained, artifact-set id/key/content hash, and path/status metadata. Keeping
request-derived correction rows in the canonical public manifest violates that
boundary even though the new private-capture helper is stricter.

Fix: remove the `corrections` row list from `_summarize_apply_request`; retain
`correction_count`, `body_sha256`, `corrections_sha256`, safe request id, and
approved job/source digest metadata only. Add/adjust a boundary test for
`_handle_request` or `_summarize_apply_request` using correction rows that
contain `source_text`, identity/grant/idempotency/provider fields, and private
paths, then assert the rendered `correction_apply_requests` summary contains no
raw or structured correction body material.

Proof required:
`pdm run test tests/unit/scripts/test_story58_artifact_set_invariants.py tests/unit/scripts/test_story58_private_request_capture.py`

### Live-Proof Gap

The invariant helper correctly supports `pass`, `fail`, and `unproven`, and the
current Playwright wiring records real product-route artifact snapshots only
after final replay download/save actions. That means the next live manifest may
truthfully remain `unproven` for the missing Story 58 production
duplicate/distinct artifact-set rows unless the live run captures comparable
product-route snapshots for each relevant correction-apply response, not only
the final artifact set.

### Verification Evidence

| Command or evidence | Result |
|---|---|
| Reviewer-run `pdm run test tests/unit/scripts/test_story58_artifact_set_invariants.py tests/unit/scripts/test_story58_private_request_capture.py` | Passed: 17 tests. |
| Reviewer-run `pdm run lint` | Passed. |
| Reviewer-run `pdm run typecheck` | Passed: no issues in 1166 source files; existing unused `pyproject.toml` section note. |
| Reviewer-run `pdm run docs-validate` | Passed. |
| Reviewer-run `git diff --check` | Passed. |

### Decision

changes_requested

## Rereview: Story 58 Artifact-Set Invariant Extension Redaction Fix

**Reviewer:** ruthless_review_agent
**Date:** 2026-06-30
**Verdict:** approved

### Scope

- `scripts/_story58_artifact_set_invariants.py`
- `tests/unit/scripts/test_story58_artifact_set_invariants.py`
- `scripts/playwright_pr_0337_correction_session_live.py`
- `tests/unit/scripts/test_story58_private_request_capture.py`
- `docs/backlog/reviews/review-pr-0410-exam-converter-correction-replay-artifact-set-consumer.md`

### Prior Finding Resolution

Approved. `_summarize_apply_request` now removes the public
`correction_apply_requests[*].corrections` row list and retains only summary
metadata needed by the proof harness: count, request/body/correction digests,
request id, selected job/source digest metadata, method/path, schema version,
and target metadata. The code no longer copies per-correction `entry_id`,
`item_id`, `kind`, `sequence`, source text, teacher answer text, identity/grant,
idempotency, provider prompt, private path, or raw body material into the public
apply-request summary.

The regression test now exercises the canonical PR-0337 request-handler path
with correction rows containing `entry_id`, `item_id`, `kind`, `sequence`,
`source_text`, and answer text, then asserts those values do not appear in the
rendered public summary. The private-capture tests continue to prove raw bodies
stay in the operator-provided private directory while the public summary remains
digest/count based.

### Findings

No blocking findings.

### Live-Proof Gap

The extension is approved as a proof-harness evidence/redaction slice. It still
does not itself close the broader Sir Convert Story 58 production
duplicate/distinct artifact-set matrix. The current Playwright script records
product-route artifact snapshots after final replay download/save actions, so a
future live run may still truthfully report `unproven` unless it captures
comparable product-route snapshots for each relevant correction-apply response.

### Verification Evidence

| Command or evidence | Result |
|---|---|
| Reviewer code review of `scripts/playwright_pr_0337_correction_session_live.py` | `_summarize_apply_request` no longer retains structured correction rows in public `correction_apply_requests`. |
| Reviewer code review of `tests/unit/scripts/test_story58_private_request_capture.py` | Canonical request-handler boundary test now fails if correction row ids/types/sequence/source text/answer text leak into the public apply-request summary. |
| Reviewer code review of `scripts/_story58_artifact_set_invariants.py` and `tests/unit/scripts/test_story58_artifact_set_invariants.py` | Invariant helper still redacts non-approved observation keys and preserves `unproven` for insufficient product-route evidence. |
| Reviewer-run `pdm run test tests/unit/scripts/test_story58_artifact_set_invariants.py tests/unit/scripts/test_story58_private_request_capture.py` | Passed: 17 tests. |
| Reviewer-run `pdm run lint` | Passed. |
| Reviewer-run `pdm run typecheck` | Passed: no issues in 1166 source files; existing unused `pyproject.toml` section note. |
| Reviewer-run `pdm run docs-validate` | Passed before and after this retained-review update. |
| Reviewer-run `git diff --check` | Passed before and after this retained-review update. |

### Decision

approved

## Independent Review: Story 58 Selected-Detail Proof-Harness Stabilization

**Reviewer:** Codex retained reviewer
**Date:** 2026-06-30
**Verdict:** changes_requested

### Scope

- `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/ExamConverterQuestionReviewShell.vue`
- `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts`
- `scripts/playwright_pr_0337_correction_session_live.py`

This review covers only the current uncommitted selected-detail proof-harness
stabilization patch. It does not approve final Sir Convert Story 58 closeout,
deployment, stale-replay proof, producer behavior, or raw private request
capture contents.

### Findings

#### Low: current proof script formatting fails the repo lint gate

`scripts/playwright_pr_0337_correction_session_live.py:91` and
`scripts/playwright_pr_0337_correction_session_live.py:1780` are formatted
differently from the repo formatter's expected output, so `pdm run lint` fails
on the current uncommitted diff. The selected-detail behavior itself looks
sound, but this patch cannot be approved while a required closeout gate fails
for a touched proof script.

Fix: run the repo formatter or apply the formatter's exact changes for the
changed proof script only; do not alter the proof flow, selectors, or
`_click_and_wait_for_apply` behavior.

Proof required:
`pdm run lint`

### Review Notes

- The added `data-selected-item-id` on
  `exam-converter-selected-question-detail` is a real route-visible DOM signal,
  not a facade around the Playwright script.
- `_click_and_wait_for_apply` remains semantically intact: it still waits for
  the correction-session write, then the Sir Convert apply/source-state
  response, and it still retries source-state rate limiting.
- The answer-key proof selectors are now scoped through the detail container
  whose `data-selected-item-id` matches the selected row, which addresses the
  stale `Granska` row/detail mismatch without broadening selectors.
- `LocatorRoot = Page | Locator` and the changed helper return types pass the
  repo Python typecheck.

### Verification Evidence

| Command or evidence | Result |
|---|---|
| Reviewer code review of scoped diff | No behavior blocker found in selected-detail scoping or apply-wait semantics. |
| Reviewer-run `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts` | Passed: 13 tests. |
| Reviewer-run `pdm run test tests/unit/scripts/test_story58_private_request_capture.py tests/unit/scripts/test_story58_artifact_set_invariants.py tests/unit/scripts/test_story58_artifact_route_probe.py` | Passed: 24 tests. |
| Reviewer-run `pdm run fe-type-check` | Passed. |
| Reviewer-run `pdm run typecheck` | Passed: no issues in 1166 source files; existing unused `pyproject.toml` docx section note. |
| Reviewer-run `git diff --check -- frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/ExamConverterQuestionReviewShell.vue frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts scripts/playwright_pr_0337_correction_session_live.py` | Passed. |
| Reviewer-run `pdm run lint` | Failed: `scripts/playwright_pr_0337_correction_session_live.py` would be reformatted. |

### Decision

changes_requested

## Rereview: Story 58 Selected-Detail Proof-Harness Stabilization

**Reviewer:** Codex retained reviewer
**Date:** 2026-06-30
**Verdict:** approved

### Scope

- `.codex/handoff.md`
- `docs/backlog/reviews/review-pr-0410-exam-converter-correction-replay-artifact-set-consumer.md`
- `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/ExamConverterQuestionReviewShell.vue`
- `scripts/playwright_pr_0337_correction_session_live.py`
- `tests/unit/scripts/test_story58_private_request_capture.py`

This rereview approves only the bounded Skriptoteket follow-up diff for
proof-harness stabilization and the selected-detail `data-selected-item-id`
hook. It does not approve final Sir Convert Story 58 closeout, production
rerun/deploy status, stale-replay private-input proof, producer behavior, or
raw private request bodies.

### Findings

No blocking findings remain.

### Review Notes

- The selected-detail hook is a real DOM state signal on the existing question
  detail surface, with a focused component assertion. It is not a compatibility
  facade, local replay shim, or product fallback.
- The proof harness now scopes answer-key actions through the selected detail
  whose `data-selected-item-id` matches the selected row. This addresses the
  auto-next/stale-detail race without loosening selectors or hiding failed
  correction-session/apply responses.
- The harness still waits for the correction-session write and Sir Convert
  apply/source-state response before advancing. Download/save proof continues
  to require the nested correction-replay route with `artifact_set_id`,
  `artifact_key`, and `content_sha256`, and mismatched replay artifacts fail
  closed.
- The current Dev manifest
  `.artifacts/playwright-pr-0337-correction-session-live/20260630T201858Z/manifest.redacted.json`
  records `proof_complete`, replay PDF/QTI download `200`, Save to My Files
  `200`, distinct artifact-set invariants `pass`, manual review-required
  cleanup with `Granska: 0`, and mismatched replay artifact `409`.
- Public retained evidence remains bounded to redacted manifest facts. The
  manifest marks private request capture as private-dir only with no raw bodies
  or private paths retained; reviewer redaction scan found no raw request body,
  source-state signature, identity/grant envelope, provider prompt, or source
  text terms in the retained public summary.
- The proof script remains a large targeted Playwright entrypoint, but the
  current follow-up keeps the added logic inside the existing disposable
  proof-harness lane and does not introduce a reusable shim/facade surface.

### Verification Evidence

| Command or evidence | Result |
|---|---|
| Reviewer code review of scoped diff | No behavior, boundary, redaction, or selected-detail blocker found. |
| Reviewer-run `pdm run lint` | Passed. |
| Reviewer-run `pdm run test tests/unit/scripts/test_story58_private_request_capture.py tests/unit/scripts/test_playwright_script_surface.py` | Passed: 19 tests. |
| Reviewer-run `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts` | Passed: 13 tests. |
| Reviewer-run `pdm run python -m py_compile scripts/playwright_pr_0337_correction_session_live.py` | Passed. |
| Reviewer-run `git diff --check` | Passed before this retained-review artifact update. |
| Reviewer manifest spot-check of `.artifacts/playwright-pr-0337-correction-session-live/20260630T201858Z/manifest.redacted.json` | Confirmed proof completion, replay-scoped download/save, manual review-required cleanup, artifact-set invariants, mismatched-artifact 409, and redacted private request capture summary. |

### Decision

approved
