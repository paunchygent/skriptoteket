---
type: review
id: REV-PR-0407
title: "Review: PR-0407 Audio Transcription retryable reattempt browser proof ownership"
status: approved
owners: "agents"
created: 2026-06-29
updated: 2026-06-29
reviewer: "ruthless-code-review"
prs:
  - PR-0407
links:
  - ST-37-04
  - EPIC-37
---

## TL;DR

PR-0407 is approved on pass 2. The active script and helpers are domain-named,
the Sir Convert Task 371 proof bundle remains external historical evidence,
sidecar preparation stays an explicit operator precondition, and the Gateway
helper asserts one replay POST plus `service_reattempt` lineage and artifact
fetches. The first-pass auth recovery finding is resolved: recovery now waits
for the success heading or route-owned ready selector after navigating to the
requested `next` route.

## Problem Statement

This review checks whether Skriptoteket now owns the reusable public Audio
Transcription retryable-reattempt browser proof without reintroducing caller-side
retry behavior, task-numbered proof surfaces, hidden Sir Convert sidecar
mutation, or weakened shared-auth proof semantics.

## Proposed Solution

The implementation adds a domain-named browser proof entrypoint,
Audio Transcription route helpers, Gateway evidence assertions, and opt-in
shared-auth target-route recovery. The proof assumes a Sir Convert retryable
failed precondition has already been prepared by an operator.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0407-st-37-04-audio-transcription-reattempt-browser-proof-ownership.md` | Governing contract and validation claims | 10 min |
| `scripts/_playwright_auth.py` | Opt-in shared-auth target recovery | 20 min |
| `scripts/_audio_transcription_browser.py` | Route-owned Audio Transcription browser helpers | 10 min |
| `scripts/_sir_convert_gateway_evidence.py` | Gateway evidence assertions and redaction | 25 min |
| `scripts/audio_transcription_retryable_reattempt_public_proof.py` | Public proof entrypoint and sidecar boundary | 15 min |
| `tests/unit/scripts/test_playwright_auth_recovery.py` | Auth recovery truthfulness | 10 min |
| `tests/unit/scripts/test_audio_transcription_retryable_reattempt_public_proof.py` | Gateway proof truthfulness | 15 min |
| `tests/unit/scripts/test_playwright_script_surface.py` | Domain-named script surface | 10 min |
| `pyproject.toml`, `docs/index.md`, `.codex/handoff.md`, `ST-37-04` | Command/docs discoverability | 10 min |

**Total estimated time:** ~125 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep reusable proof ownership in Skriptoteket under domain names. | Matches the public browser route and avoids a Sir Convert-owned one-off proof script becoming the durable surface. | Yes |
| Keep Sir Convert retryable-failed setup external to the browser helper. | Prevents hidden sidecar stop/start or runtime mutation inside a Skriptoteket proof. | Yes |
| Require opt-in shared-auth route recovery without weakening strict callers. | Recovery now navigates to the requested route and waits for the route-owned ready selector or success heading. | Yes |
| Assert one replay create-job POST, `service_reattempt` lineage, and result/artifact/transcript JSON fetches. | The helper fails closed for duplicate submits and missing lineage/fetch evidence. | Yes |

## Review Checklist

- [x] Scope is bounded and appropriate.
- [x] Acceptance criteria or proof obligations are reviewable.
- [x] Risks and structural fault lines are called out explicitly.
- [x] Verification plan fully matches the claimed auth recovery contract.
- [x] No caller-side retry wrapper, salted idempotency workaround, Gateway/Sir Convert mutation shortcut, active task-named alias, or hidden sidecar fallback found in reviewed PR-0407 code.

## Review Feedback

**Reviewer:** ruthless-code-review
**Date:** 2026-06-29
**Verdict:** approved

### Required Changes

None open.

### Resolved Required Changes

1. **medium - `scripts/_playwright_auth.py:200`**

   `_try_recover_to_next_path()` navigates to the requested app route and then
   immediately calls `_success_destination_visible()` through `Locator.count()`
   / `Locator.is_visible()`. Those Playwright calls do not wait. The PR
   acceptance requires the helper to recover by navigating to the target route
   and waiting for the route-owned ready selector. In the actual SPA path, the
   route can render after `domcontentloaded`, so a valid session can still fail
   the proof before `[data-test="transcript-workflow-rail-shell"]` appears.

   Why it matters: this is the exact shared-auth recovery gap PR-0407 claims to
   close. The current unit test only models an immediately visible selector, so
   it would stay green while the browser proof remains flaky or falsely fails
   after successful auth.

   Correct shape: make recovery wait for the configured route-owned ready
   selector or success heading with an explicit timeout, using the same
   opt-in-only semantics. Default callers without `recover_to_next_path=True`
   must keep the existing strict failure behavior.

   Proof required:
   - Add/update a behavioral unit test in
     `tests/unit/scripts/test_playwright_auth_recovery.py` where recovery
     navigation succeeds only after the route-ready locator becomes visible
     after a wait, and prove strict non-recovery still fails.
   - Run:
     `pdm run test tests/unit/scripts/test_playwright_auth_recovery.py tests/unit/scripts/test_audio_transcription_retryable_reattempt_public_proof.py tests/unit/scripts/test_playwright_script_surface.py`
   - Run the usual close-out gates for this script/docs change:
     `pdm run format`, `pdm run lint`, `pdm run typecheck`,
     `pdm run docs-validate`, `pdm run handoff-validate`, and
     `git diff --check`.

   Pass 2 resolution: `scripts._playwright_auth._try_recover_to_next_path()`
   now calls `_wait_for_success_destination(...)` with `success_timeout_ms`
   after navigating to `next_path`. The new
   `test_auth_helper_waits_for_requested_route_ready_selector_after_recovery`
   delays route readiness until two target-route waits, so the old immediate
   visibility check would fail while the fixed behavior passes.

### Pass 2 Verification

| Command | Result |
|---------|--------|
| `pdm run test tests/unit/scripts/test_playwright_auth_recovery.py tests/unit/scripts/test_audio_transcription_retryable_reattempt_public_proof.py tests/unit/scripts/test_playwright_script_surface.py` | Passed, 13 tests. |
| `rg -n "caller-side\|second-submit\|salt\|sidecar\|docker\|subprocess\|requests\\.\|httpx\|playwright_pr_0407\|task-371\|Task 371\|compatibility shim\|fallback\|except Exception\|pass" scripts/_playwright_auth.py tests/unit/scripts/test_playwright_auth_recovery.py scripts/_audio_transcription_browser.py scripts/_sir_convert_gateway_evidence.py scripts/audio_transcription_retryable_reattempt_public_proof.py docs/backlog/prs/pr-0407-st-37-04-audio-transcription-reattempt-browser-proof-ownership.md` | No new forbidden retry, sidecar, task-named active script, or mutation shortcut found. |

### Suggestions (Optional)

None.

### Decision Approvals

- [x] Domain-named reusable proof surface.
- [x] Sir Convert Task 371 historical bundle remains external and untouched by this implementation.
- [x] Sidecar/runtime preparation remains an explicit external operator step.
- [x] Shared-auth recovery waits for requested route readiness.
- [x] Gateway evidence helper rejects duplicate replay submits and missing reattempt lineage/fetches.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0407` | Initial independent retained review recorded with `changes_requested`. |
| 2 | `REV-PR-0407` | Pass 2 approved after auth recovery was changed to wait for delayed route readiness and focused tests passed. |
