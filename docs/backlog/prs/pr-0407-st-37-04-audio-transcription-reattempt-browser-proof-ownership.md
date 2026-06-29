---
type: pr
id: PR-0407
title: "ST-37-04 Audio Transcription retryable reattempt browser proof ownership"
status: done
owners: "agents"
created: 2026-06-29
updated: 2026-06-29
stories:
  - "ST-37-04"
tags:
  - playwright
  - audio-transcription
  - sir-convert
  - proof
  - shared-auth
dependencies:
  - "Sir Convert task-368"
  - "Sir Convert task-369"
  - "Sir Convert task-371"
links:
  - "/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-368-centralize-retryable-failed-idempotency-reattempts-in-service-api-v2.md"
  - "/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-369-remove-cli-auto-rerun-wrappers-after-service-api-v2-owns-retryable-reattempts.md"
  - "/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-371-prove-audio-transcription-public-browser-retryable-reattempt.md"
acceptance_criteria:
  - "Given the retained Sir Convert Task 371 proof used a one-off script, when this slice closes, then Skriptoteket owns the reusable public browser proof entrypoint and helper surface under domain names, not task-numbered names."
  - "Given historical proof evidence remains valid, when the reusable Skriptoteket proof surface is added, then the ignored Sir Convert `build/verification/task-371-public-browser-audio-cli-proof/` bundle remains untouched as retained historical evidence."
  - "Given retryable-failed preconditions require Sir Convert runtime state, when the Skriptoteket proof runs, then Sir Convert sidecar/runtime preparation remains an explicit external operator step rather than hidden inside Skriptoteket browser helpers."
  - "Given shared-auth proof sometimes lands on a HuleEdu callback or dashboard after a successful login, when an app route requested a specific `next` path, then the canonical auth helper can recover by navigating to that target route and waiting for the route-owned ready selector."
  - "Given Service API v2 owns retryable-failed reattempts, when the Audio Transcription browser proof submits the replay through the public Skriptoteket route, then retained Gateway evidence shows exactly one create-job POST, `service_reattempt` idempotency metadata, the expected failed-attempt lineage, successful job completion, and result/artifact fetches."
---

# PR-0407: ST-37-04 Audio Transcription Retryable Reattempt Browser Proof Ownership

## Problem

Sir Convert Task 371 produced the right live evidence for the Task 368/369
idempotency remediation, but its proof script lived under Sir Convert's ignored
`build/verification/` tree and carried task-oriented naming. That was useful
for the one-off closeout, but the repeatable browser/Gateway proof belongs to
Skriptoteket because the public path is the authenticated
`/apps/audio-transcription` route talking through the HuleEdu Gateway.

The proof also exposed a reusable shared-auth gap: the HuleEdu login ceremony
can succeed while the browser lands on a callback or dashboard instead of the
requested app route. The current helper treats that as proof failure even
though the session may be valid.

## Accepted Decisions

1. The follow-up implementation lives in Skriptoteket as a governed
   PR/backlog slice. Sir Convert docs may link to it, but the browser proof
   script is not owned by Sir Convert.
2. The existing ignored Sir Convert Task 371 proof artifact remains untouched
   as historical retained evidence. Do not delete, rewrite, quarantine, or
   rename it as part of this slice.
3. Skriptoteket owns the browser, Gateway, auth, and retained proof-helper
   flow. Sir Convert sidecar/runtime setup for producing a retryable failed
   audio/STT precondition remains an explicit external operator step.
4. Durable script and helper names use domain language:
   `audio_transcription_retryable_reattempt_public_proof.py`,
   `_audio_transcription_browser.py`, and
   `_sir_convert_gateway_evidence.py`.
5. The canonical shared-auth helper must handle the recoverable
   "auth succeeded but landed away from the app" case by navigating to the
   requested app route and waiting for a route-owned ready selector.

## Goal

Promote the Task 371 browser-proof mechanics into Skriptoteket's canonical
Playwright proof surface while preserving the Service API v2 ownership boundary:
the browser performs one public route submission, the Gateway returns
service-owned retryable reattempt metadata, and no CLI/client-side compatibility
rerun is introduced.

## Non-goals

- No Sir Convert, Gateway, or HuleEdu runtime implementation changes.
- No hidden sidecar stop/start or production dependency perturbation inside
  Skriptoteket proof scripts.
- No deletion or mutation of the Sir Convert retained Task 371 proof bundle.
- No CLI-side retry, salted idempotency key, second-submit remediation, or
  caller-owned retry wrapper.
- No new `scripts/playwright_pr_*.py` entrypoint.

## Implementation Plan

1. Extend `scripts._playwright_auth.login_via_auth_entry` with opt-in target
   recovery that uses the existing `/auth/login?next=...` contract, then waits
   for either the heading pattern or a route-owned ready selector.
2. Add `scripts._audio_transcription_browser` for opening the authenticated
   Audio Transcription route and driving route-owned upload/start/reset/terminal
   surfaces.
3. Add `scripts._sir_convert_gateway_evidence` for redacted create-job request,
   response, idempotency, lineage, result, artifact, and transcript JSON
   evidence assertions.
4. Add `scripts.audio_transcription_retryable_reattempt_public_proof` as the
   reusable public browser proof. It assumes the retryable failed precondition
   has been prepared externally and validates the replay through the browser
   route.
5. Keep active proof-script surface tests enforcing domain-named reusable
   scripts and update current operator docs/index/handoff references.

## Test Plan

- Red first:
  - auth-helper recovery test fails before the shared helper accepts a target
    ready selector and recovery option;
  - reusable proof-surface test fails before the new domain-named script and
    Gateway evidence helper exist.
- Green:
  - `pdm run test tests/unit/scripts/test_playwright_auth_recovery.py tests/unit/scripts/test_audio_transcription_retryable_reattempt_public_proof.py tests/unit/scripts/test_playwright_script_surface.py`
  - `pdm run test tests/unit/scripts/test_audio_transcription_parity_progress_snapshot.py tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py`
- Close-out:
  - `pdm run format`
  - `pdm run lint`
  - `pdm run typecheck`
  - `pdm run docs-validate`
  - `pdm run handoff-validate`
  - `git diff --check`

## Rollback Plan

Remove the new Skriptoteket proof script and helpers, revert the shared-auth
helper recovery option, and keep the historical Sir Convert Task 371 proof
bundle untouched.

## Implementation Summary

- Added opt-in target-route recovery to
  `scripts._playwright_auth.login_via_auth_entry` with a route-owned ready
  selector, preserving strict failure behavior for callers that do not opt in.
- Added `scripts._audio_transcription_browser` as the route-owned helper for
  opening `/apps/audio-transcription`, selecting audio, starting a transcript,
  resetting state, and waiting for terminal UI surfaces.
- Added `scripts._sir_convert_gateway_evidence` to capture redacted Gateway
  create-job requests/responses, assert exactly one replay submit, assert
  `service_reattempt` idempotency lineage, and require result/artifact/
  `transcript_json` fetches.
- Added `scripts.audio_transcription_retryable_reattempt_public_proof` and the
  `pdm run audio-transcription-reattempt-proof` command. The script assumes the
  retryable failed precondition was prepared externally and does not stop/start
  Sir Convert sidecars.
- Updated active script-surface tests, docs index, ST-37-04 story, and handoff
  so the reusable proof surface is domain-named and discoverable.
- Resolved retained review finding by making auth recovery wait for the success
  heading or route-owned ready selector after navigating to `next_path`.

## Validation

- Red first:
  `pdm run test tests/unit/scripts/test_playwright_auth_recovery.py tests/unit/scripts/test_audio_transcription_retryable_reattempt_public_proof.py tests/unit/scripts/test_playwright_script_surface.py`
  failed before implementation because
  `scripts._sir_convert_gateway_evidence` did not exist.
- Focused green:
  `pdm run test tests/unit/scripts/test_playwright_auth_recovery.py tests/unit/scripts/test_audio_transcription_retryable_reattempt_public_proof.py tests/unit/scripts/test_playwright_script_surface.py`
  passed with 13 tests after the retained-review fix.
- Transcript proof regression:
  `pdm run test tests/unit/scripts/test_audio_transcription_parity_progress_snapshot.py tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py`
  passed with 32 tests.
- Command surface:
  `pdm run audio-transcription-reattempt-proof --help` passed.
- Gates:
  `pdm run format`, `pdm run lint`, `pdm run typecheck`,
  `pdm run docs-validate`, `pdm run handoff-validate`, and
  `git diff --check` passed.
- Retained review:
  `docs/backlog/reviews/review-pr-0407-audio-transcription-reattempt-browser-proof-ownership.md`
  is approved as `REV-PR-0407`.

## Live Proof Note

This slice does not rerun the production retryable-failed precondition. The
canonical live proof remains the Sir Convert Task 371 retained evidence, while
this PR moves the reusable browser/Gateway proof surface to Skriptoteket for
future runs with an explicitly prepared external Sir Convert precondition.
