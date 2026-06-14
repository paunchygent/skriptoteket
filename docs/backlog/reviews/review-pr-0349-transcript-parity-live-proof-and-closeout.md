---
type: review
id: REV-PR-0349
title: "Review: PR-0349 Transcript Parity Live Proof And Closeout"
status: changes_requested
owners: "agents"
created: 2026-06-13
updated: 2026-06-14
reviewer: "ruthless-code-reviewer"
prs:
  - PR-0349
links:
  - ST-21-08
  - EPIC-21
  - PR-0347
  - PR-0348
---

## TL;DR

2026-06-14 update: final PR-0349 closeout is not approved. A production manual
export exposed an architecture blocker: replay/export is implemented as a
browser-owned saga instead of the DXE/converter product-owned workflow pattern.
The retained approval below remains historical for narrower upload,
truthfulness, parser, and receipt-remediation slices only; it must not be read
as final parity approval.

Required follow-up: Sir Convert `task-363` and Skriptoteket `PR-0350` must
remove the heavy-queue replay latency hazard and browser-owned
prepare/submit/poll/download/base64/complete path before PR-0349 can close.

The upload/admission remediation is now reviewable and correct within its
scoped approval boundary. The frontend surfaces pre-job multipart upload state,
the RCA no longer confuses first-response latency with conversion processing,
and the proof script now classifies `upload_abort` versus
`sir_convert_job_cancel` from observed sanitized network evidence instead of a
timeout heuristic.

## Problem Statement

PR-0349 is the live parity proof and closeout gate for ST-21-08. Because the
lane is still blocked outside Skriptoteket production behavior, this fresh
review is not about approving full transcript parity. It is about whether the
new upload/admission remediation, corrected RCA, cancel semantics, and updated
proof-script truthfulness are strong enough to approve this narrower slice
without overstating what the retained evidence proves.

## Proposed Solution

The reviewed change set now adds:

- a targeted Playwright proof entrypoint for the authenticated transcript parity
  lane;
- shared sanitized evidence helpers for bounded network/console/summary output;
- auth-helper hardening so the proof follows the HuleEdu browser-session
  ceremony and handoff link instead of product-local shortcuts;
- a typed multipart upload transport plus runtime/UI upload-state rendering so
  the transcript lane is no longer silent before Sir Convert returns a job id;
- pre-job local upload abort semantics before a Gateway/Sir Convert job id
  exists;
- docs/handoff/epic/story updates that keep PR-0349 and ST-21-08 blocked and
  explicitly separate implemented slices from unproven live closeout.

That overall shape is correct for this slice. The earlier cancel-path
truthfulness blocker has now been fixed without broadening the approval scope
beyond upload/admission remediation and proof-script truthfulness.

## Scope

Primary review target:

- `docs/backlog/prs/pr-0349-st-21-08-transcript-parity-live-proof-and-closeout.md`

Authority and adjacent governed items reviewed:

- `docs/backlog/prs/pr-0347-st-21-08-overlay-aware-formatter-replay-client.md`
- `docs/backlog/prs/pr-0348-st-21-08-overlay-aware-download-and-mina-filer-save.md`
- `docs/backlog/reviews/review-pr-0347-overlay-aware-formatter-replay-client.md`
- `docs/backlog/reviews/review-pr-0348-overlay-aware-download-and-mina-filer-save.md`
- `docs/backlog/stories/story-21-08-transcript-speaker-overlays-and-replay-formatter-exports.md`
- `docs/backlog/epics/epic-21-curated-app-conversion-hub.md`
- `.codex/handoff.md`
- `.codex/rules/075-browser-automation.md`
- `docs/index.md`
- `docs/reference/ref-review-workflow.md`

Implementation and proof files reviewed:

- `frontend/apps/skriptoteket/src/api/sirConvertGateway/uploadProgress.ts`
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/multipartUploadTransport.ts`
- `scripts/_transcript_parity_cancel.py`
- `scripts/playwright_pr_0349_transcript_parity_live.py`
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/client.ts`
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptTypes.ts`
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/parsers.ts`
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/index.ts`
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptClient.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/useTranscriptGatewayRuntime.ts`
- `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/transcriptProgressDisplay.ts`
- `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.vue`
- `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/useTranscriptGatewayRuntime.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/ConversionHubTranscriptMode.spec.ts`
- `docs/backlog/prs/pr-0349-st-21-08-transcript-parity-live-proof-and-closeout.md`

Out of scope for approval here:

- approving full ST-21-08 parity acceptance;
- fixing the HuleEdu/Sir Convert signer trust mismatch itself;
- re-reviewing the already-approved PR-0347 or PR-0348 production logic beyond
  their use as parity prerequisites.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0349-st-21-08-transcript-parity-live-proof-and-closeout.md` | Blocked closeout claims and acceptance-state honesty | 15 min |
| `docs/backlog/stories/story-21-08-transcript-speaker-overlays-and-replay-formatter-exports.md` | Story status and parity gate wording | 10 min |
| `scripts/playwright_pr_0349_transcript_parity_live.py` | Auth path, proof sequencing, retained summary truth | 30 min |
| `scripts/_transcript_parity_evidence.py` | Sanitization, blocker extraction, captured-artifact manifest | 15 min |
| `scripts/_playwright_auth.py` | HuleEdu browser-session ceremony compliance | 15 min |
| `tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py` | Blocked-run summary truthfulness coverage | 10 min |
| `.artifacts/playwright-pr-0349-transcript-parity-live/20260613T153843Z/*` | Retained evidence strength and honesty | 20 min |
| `tests/unit/scripts/test_playwright_script_surface.py` | Script-surface allowlist enforcement | 5 min |
| `tests/unit/scripts/test_conversion_hub_transcript_docs_guard.py` | Transcript docs guard coverage | 5 min |

**Total estimated time:** ~2 hours

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep approval scoped to the upload/admission remediation and proof-script truthfulness only | The full parity acceptance criteria remain unproven by design. | [x] |
| Require HuleEdu browser-session ceremony and repo helpers for proof | Matches AGENTS.md, browser-automation rules, and the PR non-goals. | [x] |
| Treat heuristic cancel-path classification as an approval blocker until fixed | This PR slice now claims truthful distinction between upload abort and Sir Convert job cancel, so the retained proof cannot guess the path from a timeout. The remediation now satisfies that requirement. | [x] |

## Review Checklist

- [x] Scope is bounded to PR-0349 proof harness and blocked closeout truthfulness.
- [x] Docs-as-code authority exists for ST-21-08 and PR-0349.
- [x] The reviewed script uses the HuleEdu browser-session ceremony and repo helpers.
- [x] No direct product-backend credential shortcut or direct Sir Convert browser proof was found.
- [x] No `Any`, `cast(...)`, or `# type: ignore` appears in the newly touched frontend/runtime/spec files or in the updated proof script.
- [x] The corrected RCA no longer overclaims 34-second conversion processing; it scopes the observed latency to first-response upload/admission.
- [x] The new frontend/runtime tests prove visible pre-job upload state and local pre-id cancel behavior.
- [x] The proof script truthfully distinguishes pre-job upload abort from Sir Convert job cancel from observed network evidence without relying on an arbitrary timeout.

## Verification

Commands run:

```bash
git status --short
git diff --check
pdm run test tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py
pdm run test tests/unit/scripts/test_playwright_script_surface.py tests/unit/scripts/test_conversion_hub_transcript_docs_guard.py tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py
pdm run fe-test -- --run frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptClient.spec.ts frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/useTranscriptGatewayRuntime.spec.ts frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts frontend/apps/skriptoteket/src/views/apps/ConversionHubTranscriptMode.spec.ts
pdm run fe-type-check
pdm run python -m py_compile scripts/playwright_pr_0349_transcript_parity_live.py scripts/_transcript_parity_cancel.py
```

Results:

- The working tree includes broader ST-21-08 implementation and docs changes,
  so this review stayed intentionally bounded to the PR-0349 proof/closeout
  slice and its governed dependencies.
- `git diff --check` passed.
- `pdm run test tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py`
  passed: 4 tests.
- `pdm run test tests/unit/scripts/test_playwright_script_surface.py tests/unit/scripts/test_conversion_hub_transcript_docs_guard.py tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py`
  passed: 10 tests.
- `pdm run fe-test -- --run ...` passed: 4 files, 30 tests.
- `pdm run fe-type-check` passed.
- `pdm run python -m py_compile scripts/playwright_pr_0349_transcript_parity_live.py scripts/_transcript_parity_cancel.py`
  passed.
- The focused Vitest suite proves:
  - the Gateway client surfaces typed upload progress through the multipart
    transport;
  - `useTranscriptGatewayRuntime` exposes pre-job upload state and resolves a
    local pre-id cancel without sending `cancelTranscriptJob`;
  - `TranscriptWorkspaceShell` renders upload-phase percent/byte feedback; and
  - `ConversionHubTranscriptMode` passes `AbortSignal` and upload-progress
    callback into transcript submission.
- The focused script tests now prove both cancel classifications:
  - no observed `/cancel` response remains `upload_abort`; and
  - a delayed-but-observed `POST .../cancel` response is classified as
    `sir_convert_job_cancel`.
- I did not rerun the live PR-0349 browser proof, so this review does not
  upgrade PR-0349 from blocked to parity-complete.

## Review Feedback

**Reviewer:** ruthless-code-reviewer
**Date:** 2026-06-13
**Verdict:** approved

### Findings

#### P0 - Browser-Owned Replay Saga Violates The Required Product Boundary

The replay/export implementation currently lets browser code coordinate a
producer workflow: prepare in Skriptoteket, submit to Sir Convert through
HuleEdu Gateway, wait/poll until terminal, download producer artifacts, collect
Gateway receipts, base64 artifact bytes, and post them back to Skriptoteket for
completion.

That is not the DXE/converter pattern requested for this lane. It makes a
simple text export button depend on foreground browser orchestration and allows
Sir Convert admission/queue latency to appear as a disabled or silent export
UI. Production manual evidence showed about 119 seconds between
`formatter-replay/prepare` and `formatter-replay/complete` for transcript
`aaf12956-67c3-4cd6-8094-b2e264ad2b59`.

Required remediation:

- Sir Convert `task-363`: replay must be a fast producer lane outside the
  generic heavy conversion queue.
- Skriptoteket `PR-0350`: remove the browser-owned replay saga, delete or
  rewrite tests that assert it, and replace it with product-owned export
  workflow state.
- PR-0349 live proof must be rerun only after those slices pass and are
  reviewed.

Historical scoped finding state: the earlier cancel-path truthfulness issue is resolved by
`scripts/_transcript_parity_cancel.py`, the updated
`scripts/playwright_pr_0349_transcript_parity_live.py` flow, and the new
focused cases in `tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py`.

### Positive Checks

- The docs/handoff state does not falsely claim parity acceptance. `PR-0349`
  and `ST-21-08` remain blocked in the PR doc, story doc, epic summary, and
  `.codex/handoff.md`.
- The corrected RCA in
  `docs/backlog/prs/pr-0349-st-21-08-transcript-parity-live-proof-and-closeout.md`
  no longer attributes the observed ~34-35 second latency to conversion
  processing and now scopes it to first-response upload/admission latency.
- The frontend/runtime path is well-typed and focused. I found no `Any`,
  `cast(...)`, or `# type: ignore` in the newly touched frontend or proof
  files.
- The new frontend tests are behavior-first rather than implementation-detail
  assertions and they prove the intended user-visible upload-state and pre-id
  cancel outcomes.
- The proof script now clicks cancel once, waits for the canceled UI surface,
  and classifies the cancel path from observed sanitized network evidence
  rather than from a timeout branch.
- The proof harness still uses `login_via_auth_entry(...)` and stays on the
  sanctioned browser-session/Gateway path; I found no direct product-backend
  credential shortcut, no local session-cookie shortcut, and no direct Sir
  Convert browser lane.

### Suggestions (Optional)

- None.

### Decision Approvals

- [x] Approval scope stays limited to the upload/admission remediation slice
- [x] Authenticated proof uses the HuleEdu browser-session ceremony
- [x] Proof-script cancel-path truth is strong enough for upload/admission remediation approval

## Implementation Response

**Date:** 2026-06-13
**Responder:** Skriptoteket implementation specialist
**Decision authority:** reviewer-owned; this response does not approve
`REV-PR-0349`.

The two requested evidence-truthfulness changes were implemented:

- `scripts/_transcript_parity_evidence.py` now finalizes retained summaries
  after bounded network/console files are written, computes the artifact
  manifest from files that exist on disk, and promotes a detected Sir Convert
  `auth_invalid_internal_identity` /
  `invalid_internal_identity_signature` submit response to the primary
  `failure` object. The PR-0349 Playwright entrypoint imports that helper.
- `tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py` covers
  the blocked-run summary shape and proves that phantom happy-path screenshots
  are not listed.

Red-first evidence:

- `pdm run test tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py`
  failed before implementation with an import error for the missing summary
  finalizer functions.

Green evidence:

- `pdm run test tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py`
  passed with `2 passed`.
- `pdm run test tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py tests/unit/scripts/test_playwright_script_surface.py tests/unit/scripts/test_conversion_hub_transcript_docs_guard.py`
  passed with `8 passed`.
- `pdm run python -m py_compile scripts/playwright_pr_0349_transcript_parity_live.py scripts/_transcript_parity_evidence.py scripts/_playwright_auth.py`
  passed.

Cross-repo smoke after approved upstream slices:

- HuleEdu `TASK-0676` profile publisher passed for `local-auth-integration` and
  `hemma-production`, both emitting canonical DER SPKI fingerprint
  `46aefc0edc2f71267e2df783ca27f4df2b0da269cc7e84b43cbe2de6ac7c1992`.
- Sir Convert `task-361` approved focused suite passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_huleedu_internal_identity_trust_profile_v1.py tests/sir_convert_a_lot/test_structured_llm_settings_route_v2.py tests/sir_convert_a_lot/test_digiexam_migration_access_control_api_v2.py tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_local_compose_contract.py -q`
  with `39 passed`.

Fresh PR-0349 live proof rerun:

- `pdm run python -m scripts.playwright_pr_0349_transcript_parity_live --base-url http://127.0.0.1:5173 --dotenv .env --timeout-seconds 1200`
  still failed before a cancellable transcript job was created.
- Retained artifact:
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260613T153843Z/proof-summary.json`.
- The top-level `failure` is now
  `type=kind=sir_convert_internal_identity_rejected` with HTTP `401`,
  `error_code=auth_invalid_internal_identity`,
  `reason=invalid_internal_identity_signature`, and path
  `/sir-convert/v2/convert/jobs?wait_seconds=0`.
- The artifact manifest lists only captured evidence:
  `network.bounded.json`, `browser-console.bounded.json`, and `failure.png`.

Remaining blocker:

- The code-level HuleEdu/Sir Convert trust-profile contract now smokes green,
  but the live Sir Convert runtime reached by the sanctioned local browser
  proof still rejects the Gateway-signed identity context. Full PR-0349 parity
  remains blocked until that deployed/runtime trust lane is reconciled.

## Residual Risks

- `PR-0349` still remains product-blocked until the HuleEdu/Sir Convert signer
  trust lane is reconciled or a sanctioned Hemma/prod browser proof lane is
  provided.
- Even after this frontend remediation, full PR-0349 live parity must not be
  approved until the live proof itself passes.
- This approval is limited to the upload/admission remediation and proof-script
  truthfulness slice. It does not approve full live parity.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0349` | Re-reviewed the remediated upload/admission slice, updated the retained review record, and marked it `approved` within the scoped boundary. |
| 2 | Implementation | No production code changes were made by this reviewer. |
| 3 | `REV-PR-0349` | Re-reviewed the replay/export disabled client-state remediation, recorded the retained artifact RCA check, and kept the follow-up decision `approved` while leaving full live parity blocked pending a fresh Hemma rerun. |

## Follow-Up Client-State Review

**Date:** 2026-06-13
**Reviewer:** ruthless-code-reviewer
**Scope:** follow-up review of the replay/export disabled client-state
remediation inside `ConversionHubTranscriptHost.vue`,
`TranscriptFormatterReplayPanel.vue`,
`ConversionHubTranscriptHost.spec.ts`, the related transcript shell/mode
frontend proof, and the refreshed PR/story/epic/handoff records.

### Findings

No findings.

### Decision

approved

### Verification

- Retained artifact check:
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260613T181847Z/`
  confirms the RCA baseline for this slice: upload/STT/durable save succeeded,
  `GET` then `PUT /speaker-overlays` both persisted `overlay_count=0`, no
  formatter-replay request was sent, and the failure screenshot shows the false
  `Talarnamn sparade.` / `Exportfiler kan skapas.` state while the replay
  button remained disabled. This evidence rules out SHA/fingerprint drift,
  internal-identity rejection, or a Sir Convert replay-backend failure as the
  current blocker for this slice.
- Red:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.spec.ts frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts`
  failed with 2 assertions before the patch.
- Green:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.spec.ts frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts frontend/apps/skriptoteket/src/views/apps/ConversionHubTranscriptMode.spec.ts`
  passed with `13 passed`.
- `pdm run fe-type-check` passed.
- `pdm run fe-lint` passed.
- `pdm run docs-validate` passed.
- `pdm run handoff-validate` passed.
- `git diff --check` passed.

### Residual Risks

- The earlier `401 auth_invalid_internal_identity` artifact is historical only,
  but full `PR-0349` parity is still unproven until the authenticated Hemma
  live proof is rerun successfully.
- This follow-up approval covers the client-state remediation and its governed
  docs updates, not the end-to-end live closeout itself.

## Independent GPT-5.5 Remediation Review

**Date:** 2026-06-13
**Reviewer:** independent GPT-5.5 reviewer
**Scope:** replay/export disabled remediation only, covering
`ConversionHubTranscriptHost.vue`, `TranscriptFormatterReplayPanel.vue`,
`ConversionHubTranscriptHost.spec.ts`, the retained
`.artifacts/playwright-pr-0349-transcript-parity-live/20260613T181847Z/`
evidence, and the refreshed PR/story/epic/handoff docs.

### Decision

approved

### Findings

No findings.

### Review Notes

- The code addresses the product root cause instead of masking the Playwright
  proof: editable overlay inputs are gated behind completed initial readback,
  empty persisted overlay responses stay `idle`, and replay copy now follows
  the same `canRequest` truth as the disabled button.
- The initial empty `GET /speaker-overlays` response can no longer clobber
  teacher-entered overlay names through the observed UI path because the inputs
  do not render until `loadSpeakerOverlays()` resolves and `saveStatus` becomes
  `saved`.
- Empty overlay saves remain truthful: an empty `PUT /speaker-overlays`
  response does not mark names saved, does not enable replay, and does not
  describe exports as ready.
- Non-empty persisted overlays enable replay only after the returned overlay
  list is stored and `speakerOverlayStatus` is `saved`.
- The new host spec is behavioral: it observes DOM state, save/replay copy, and
  the enabled/disabled replay control, and it would fail for the prior
  readback race and false empty-save success.
- The docs/RCA explicitly separate this blocker from the earlier
  SHA/fingerprint/internal-identity failure and from Sir Convert replay backend
  behavior. The retained `20260613T181847Z` network evidence shows
  `overlay_count=0` for both overlay calls and no formatter-replay request.
- No `Any`, `cast(...)`, `type ignore`, `@ts-ignore`, or `@ts-expect-error`
  appears in the touched frontend/spec files. Existing UI catch boundaries
  surface typed user-facing states and were not loosened by this remediation.
- `.codex/handoff.md` is exactly 200 lines, which is compliant with the
  repo's `<=200` rule.

### Verification

- `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.spec.ts frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts frontend/apps/skriptoteket/src/views/apps/ConversionHubTranscriptMode.spec.ts`
  passed with `13 passed`.
- `pdm run fe-type-check` passed.
- `pdm run docs-validate` passed.
- `pdm run handoff-validate` passed.
- `git diff --check` passed.
- `wc -l .codex/handoff.md` reported `200`.

### Residual Risk

Full PR-0349 remains blocked until fresh authenticated Hemma live proof passes
through speaker rename, replay export, download, and Mina filer save.

## Formatter Replay Prepare RCA And Implementation Response

**Date:** 2026-06-13
**Responder:** GPT-5.5 implementation specialist
**Scope:** backend replay-prepare contract remediation after retained artifact
`.artifacts/playwright-pr-0349-transcript-parity-live/20260613T194529Z/`.

### RCA

The prior replay/export disabled client-state fix succeeded. The next live
blocker is backend validation divergence: transcript save accepted a canonical
payload with non-empty top-level `segments`, but formatter replay prepare used
its own stricter speaker-label extractor and only inspected
`transcript.segments`. The retained network evidence shows durable save and
speaker overlay persistence both returned HTTP `200` with `overlay_count=2`;
`/formatter-replay/prepare` then returned HTTP `422` with
`Transcript JSON must contain at least one segment.`

This rules out identity/fingerprint drift, overlay persistence, and Sir Convert
replay backend behavior for this blocker.

### Implementation Response

- Added a shared application-handler transcript JSON contract helper for
  strict non-empty segment extraction and canonical speaker-label extraction.
- Updated transcript save, speaker overlay validation, and formatter replay
  prepare to use the same extractor.
- Preserved fail-closed behavior for empty/missing segments, invalid segment
  objects, missing speaker labels, missing segment text, invalid timestamps,
  and overlay labels not present in the saved transcript.

### Verification

- Red:
  `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_saved_shapes.py`
  failed before the patch with `Transcript JSON must contain at least one
  segment.`
- Green:
  the same command passed with `1 passed`.
- `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_saved_shapes.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_saves.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py`
  passed with `22 passed`.
- `pdm run typecheck` passed.

### Residual Risk

This implementation response does not approve full PR-0349 closeout. Fresh
authenticated Hemma live proof still must pass through formatter replay,
download, and Mina filer save.

## Independent Backend Remediation Review

**Date:** 2026-06-13
**Reviewer:** independent GPT-5.5 high reviewer
**Scope:** backend replay-prepare segment-extraction remediation only, covering
`conversion_hub_transcript_json_contract.py`,
`conversion_hub_transcript_saves.py`,
`conversion_hub_transcript_formatter_replay.py`,
`test_conversion_hub_transcript_formatter_replay_saved_shapes.py`, the retained
`.artifacts/playwright-pr-0349-transcript-parity-live/20260613T194529Z/`
evidence, and refreshed PR/handoff docs.

### Decision

approved

### Findings

No findings.

### Review Notes

- The root cause is correctly fixed for this backend slice: save validation,
  speaker-overlay validation, and replay-prepare overlay inventory validation
  now share the same strict saved-transcript segment and speaker-label
  extraction helper. A transcript JSON shape accepted at save can no longer fail
  replay prepare solely because replay only looked at `transcript.segments`
  while save accepted top-level `segments`.
- Validation remains fail-closed. The shared helper rejects missing or empty
  segment lists and non-object segment entries; save validation still rejects
  missing segment text, missing speaker labels, non-numeric timestamps, and
  end-before-start timestamps; overlay/replay validation still rejects labels
  not present in the saved transcript.
- The helper is correctly layered in application handler code, has a
  domain-purpose module docstring, uses concrete JSON object typing, and adds no
  `Any`, `cast(...)`, `type: ignore`, or broad exception handling.
- The new regression test is behavioral: it saves a top-level `segments`
  transcript, persists two overlays, and prepares formatter replay from the
  saved record. It would fail for the observed live 422 from
  `20260613T194529Z`.
- Existing replay, save, and web API tests still protect the public contract:
  owner scope, overlay validity, missing-overlay replay rejection, replay job
  spec shape, replay completion provenance, and route delegation all remain
  green.
- The refreshed RCA separates this blocker from prior identity/fingerprint
  trust, overlay persistence/client state, and Sir Convert replay backend
  blockers. Full PR-0349 closeout is still correctly held for fresh live proof.
- `.codex/handoff.md` remains under the repo limit at 192 lines.

### Verification

- `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_saved_shapes.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_saves.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py`
  passed with `22 passed`.
- `pdm run typecheck` passed.
- `pdm run lint` passed.
- `pdm run docs-validate` passed.
- `pdm run handoff-validate` passed.
- `git diff --check` passed.
- `wc -l .codex/handoff.md` reported `192`.

### Residual Risk

This approval covers only the backend remediation for parser divergence between
save/overlay validation and replay prepare. Full PR-0349 still requires fresh
authenticated Hemma live proof through progress, cancel feedback, durable save,
speaker rename, formatter replay, download, and Mina filer save.

## Formatter Replay Complete RCA And Implementation Response

**Date:** 2026-06-13
**Responder:** GPT-5.5 implementation specialist
**Scope:** backend replay-complete parser remediation after retained artifact
`.artifacts/playwright-pr-0349-transcript-parity-live/20260613T201049Z/`.

### RCA

The replay prepare and Sir Convert replay execution stages succeeded. The
retained live proof shows persisted `overlay_count=2`,
`/formatter-replay/prepare` returning HTTP `200`, Sir Convert replay submit
returning HTTP `200` with status `succeeded`, and Sir Convert replay artifacts
listing exactly `transcript_txt`, `transcript_md`, `transcript_vtt`, and
`transcript_srt`.

The failure was isolated to Skriptoteket completion parsing:
`/formatter-replay/complete` returned HTTP `503` with
`Sir Convert replay result is malformed.` Sir Convert `/result` returns the
normal Service API v2 envelope (`api_version`, `job_id`, `status`, and
`result.warnings`) around the strict replay result body, while Skriptoteket
expected only a bare `{result: ...}` object with extra fields forbidden.

This rules out identity/fingerprint trust, overlay persistence, replay prepare,
and Sir Convert replay execution for this blocker.

### Implementation Response

- Updated `parse_replay_result` to accept the real Service API v2 replay
  result envelope while preserving strict validation of replay artifact and
  conversion metadata.
- Added `job_id` provenance validation against the completion request
  `sir_convert_job_id` before local replay job/artifact refs are persisted.
- Kept artifact manifest parsing fail-closed for malformed, duplicate, unknown,
  unavailable, wrong-content-type, or missing requested artifacts.
- Added a red-first regression that completes a successful replay result plus a
  four-artifact producer manifest and proves local replay job/artifact refs are
  persisted and returned.

### Verification

- Red:
  `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_result_envelope.py`
  failed before the patch because `api_version`, `job_id`, `status`, and
  `result.warnings` were rejected as extra fields.
- Green:
  `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_result_envelope.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py`
  passed with `7 passed`.

### Residual Risk

This implementation response does not approve full PR-0349 closeout. Fresh
authenticated Hemma live proof still must pass through formatter replay
completion, artifact download, and Mina filer save.

## Independent Replay-Complete Remediation Review

**Date:** 2026-06-13
**Reviewer:** independent GPT-5.5 high reviewer
**Scope:** backend replay-complete result-envelope remediation only, covering
`conversion_hub_transcript_formatter_replay.py`,
`conversion_hub_transcript_formatter_replay_parsing.py`,
`test_conversion_hub_transcript_formatter_replay.py`,
`test_conversion_hub_transcript_formatter_replay_result_envelope.py`, the
retained `.artifacts/playwright-pr-0349-transcript-parity-live/20260613T201049Z/`
evidence, and refreshed PR/handoff docs.

### Decision

changes_requested

### Findings

1. `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_replay_parsing.py:92`
   accepts a result body with missing `warnings` by defaulting to `[]`, while
   the PR RCA says the Service API v2 result envelope includes
   `result.warnings` and that this slice requires `warnings` as a list of
   strings. That weakens the producer-envelope validation this remediation is
   supposed to tighten. Remove the default so missing `warnings` is rejected,
   keep the list-of-strings type validation, and add focused rejection tests for
   missing and non-list/non-string `warnings`.
2. `tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_result_envelope.py:178`
   only covers the happy Service API v2 envelope and mismatched result
   `job_id`. The review brief requires tests that protect malformed producer
   data and wrong status as part of this replay-complete slice. Add focused
   negative cases for result `status != "succeeded"`, invalid
   `conversion_metadata.pipeline_used`, invalid result artifact metadata, and
   missing/invalid `warnings`. Keep the existing artifact-manifest cases for
   mismatched job ids, unknown keys, unavailable refs, and missing requested
   artifacts green.

### Review Notes

- The live failure is correctly reproduced by the new happy-path Service API v2
  envelope test: the old bare-result parser would reject `api_version`,
  `job_id`, `status`, and `result.warnings`, while the new parser accepts the
  observed envelope shape.
- The completion handler now validates result-envelope `job_id` against
  `sir_convert_job_id` before opening the UoW and before local replay job or
  artifact refs are persisted.
- Artifact refs are still derived from the Sir Convert artifact manifest, not
  inferred from requested keys alone. Missing requested artifacts, unknown
  artifact keys, duplicate keys, wrong manifest job ids, unavailable requested
  refs, wrong content types, and incomplete producer refs still fail closed.
- I found no `Any`, `cast(...)`, `type: ignore`, or broad exception handling in
  the reviewed production/test files.
- The PR and handoff RCA correctly separate this blocker from the earlier
  identity/fingerprint trust failure, overlay persistence/client-state failure,
  replay-prepare segment extraction failure, and Sir Convert replay execution.
- `.codex/handoff.md` remains within the repo limit at 195 lines.

### Verification

- `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_result_envelope.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py`
  passed with `16 passed`.
- `pdm run typecheck` passed.
- `pdm run lint` passed.
- `pdm run docs-validate` passed.
- `pdm run handoff-validate` passed.
- `git diff --check` passed.
- `wc -l .codex/handoff.md` reported `195`.

### Residual Risk

Full PR-0349 remains blocked until fresh authenticated Hemma live proof passes
through formatter replay completion, artifact download, and Mina filer save.

## Replay-Complete Changes-Requested Remediation Response

**Date:** 2026-06-13
**Responder:** GPT-5.5 implementation specialist
**Scope:** same backend replay-complete parser slice.

### Response To Findings

1. Removed the parser fallback for missing `result.warnings`. The Service API
   v2 `/result` envelope must now include `result.warnings` as a list of
   strings; missing or non-list warnings fail closed as malformed producer data.
2. Added malformed completion coverage for wrong result status, malformed result
   artifact metadata, malformed conversion metadata, and missing/non-list
   warnings. The existing happy Service API v2 envelope, mismatched result
   `job_id`, and artifact-manifest failure tests remain in place.

### Verification

- Red:
  `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_result_envelope.py`
  failed before this follow-up patch because missing `result.warnings` did not
  raise `DomainError`.
- Green:
  `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_result_envelope.py`
  passed with `6 passed`.

### Residual Risk

This response needs re-review before the retained review status can move out of
`changes_requested`. Full PR-0349 still requires fresh authenticated Hemma live
proof through replay completion, download, and Mina filer save.

## Independent Replay-Complete Re-Review

**Date:** 2026-06-13
**Reviewer:** independent GPT-5.5 high reviewer
**Scope:** re-review of the changes-requested remediation for the backend
replay-complete parser slice.

### Decision

approved

### Findings

No findings. The two prior `changes_requested` findings are resolved.

### Review Notes

- `result.warnings` is now required as `list[str]`; missing or non-list
  warnings fail closed through the same `DomainError(SERVICE_UNAVAILABLE)`
  malformed-producer path as the rest of the result envelope.
- The result parser still accepts the live-shaped Service API v2 envelope and
  still validates `api_version=v2`, `status=succeeded`, result artifact
  metadata, strict replay conversion metadata, and result `job_id` provenance
  before any local replay job or artifact refs are persisted.
- The added malformed coverage exercises the handler boundary and verifies no
  artifact records are persisted when malformed producer result data is
  rejected. It now covers missing/non-list warnings, wrong result status,
  malformed result artifact metadata, and malformed conversion metadata.
- Artifact refs remain producer-manifest-derived rather than inferred from
  requested keys. Existing manifest tests continue to protect missing requested
  artifacts and unknown keys, while the parser still protects duplicate keys,
  wrong manifest job ids, unavailable refs, wrong content types, and incomplete
  refs.
- I found no `Any`, `cast(...)`, `type: ignore`, or broad exception handling in
  the reviewed production/test files.
- The PR/handoff RCA still correctly separates this replay-complete parser
  issue from identity/fingerprint trust, overlay persistence/client state,
  replay prepare, and Sir Convert replay execution.
- `.codex/handoff.md` remains within the repo limit at 195 lines.

### Verification

- `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_result_envelope.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py`
  passed with `20 passed`.
- `pdm run typecheck` passed.
- `pdm run lint` passed.
- `pdm run docs-validate` passed.
- `pdm run handoff-validate` passed.
- `git diff --check` passed.
- `wc -l .codex/handoff.md` reported `195`.

### Residual Risk

This approval covers only the replay-complete backend parser remediation slice.
Full PR-0349 still requires fresh authenticated Hemma live proof through
formatter replay completion, artifact download, and Mina filer save.

## Formatter Artifact Download RCA Implementation Response

**Date:** 2026-06-13
**Responder:** GPT-5 implementation specialist
**Scope:** backend/frontend artifact-download contract after successful replay
completion.

### Decision

implementation_ready_for_review

### RCA

The retained proof artifact
`.artifacts/playwright-pr-0349-transcript-parity-live/20260613T203933Z/`
shows upload/STT/save, overlay persistence, replay prepare, Sir Convert replay,
Sir Convert artifact listing, and Skriptoteket replay completion succeeded.
The first failed request was Skriptoteket artifact download, which returned HTTP
`503` with `Failed to download named v2 artifact.`

The persisted artifact ref was produced by Sir Convert artifact listing through
the HuleEdu Gateway browser-session owner context. Skriptoteket then tried to
download the named artifact directly from the backend using only server-side
transport identity. Sir Convert named artifact reads are owner-scoped; API-key
transport is not owner provenance. The contract mismatch was producer/listing
context versus consumer/download context, not a Playwright timeout.

### Remediation

- Replay completion now requires owner-session Gateway-downloaded artifact
  payloads for the requested formatter artifacts.
- The backend validates exact artifact keys, content type, byte size, and
  SHA-256 against the producer manifest before persisting bytes with the refs.
- Download and Mina-save actions read validated persisted bytes only; ref-only
  rows fail closed.
- No API-key identity fallback, self-signed identity, stringly artifact shim,
  or broad exception path was added.

### Verification

- Red: the focused artifact-payload test initially reproduced the retained live
  failure as `DomainError: Failed to download named v2 artifact.` while the
  action still used direct backend producer download.
- Green:
  `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_payloads.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_completion.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_result_envelope.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py`
  passed with `25 passed`.
- Green:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/api/conversionHubTranscriptFormatterReplay.spec.ts frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptReplayClient.spec.ts`
  passed with `6 passed`.
- Green: `pdm run typecheck`, `pdm run lint`,
  `pdm run test tests/integration/test_migration_revision_coverage_idempotent.py -k e9a4b6c8d2f0 --override-ini addopts=''`,
  `pdm run fe-type-check`, and `pdm run db-upgrade` passed.

### Residual Risk

This response still needs review and a fresh authenticated Hemma live proof
through replay completion, artifact download, and Mina filer save before
PR-0349 can close.

## Independent Review: Formatter Artifact Download RCA Remediation

**Date:** 2026-06-13
**Reviewer:** GPT-5 independent review agent
**Scope:** PR-0349 artifact-download remediation after retained live proof
`.artifacts/playwright-pr-0349-transcript-parity-live/20260613T203933Z/`.

### Decision

changes_requested

### Findings

1. **blocker - replay completion can persist forged formatter artifacts without
   Gateway-signed producer authority.**
   `src/skriptoteket/web/api/v1/apps_conversion_hub_transcript_saves.py:158`
   accepts the browser-supplied replay completion request; the handler then
   derives refs from `request.artifact_manifest` and validates
   `request.artifact_payloads` against those refs in
   `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_replay.py:164`
   through
   `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_replay.py:199`.
   The byte validation at
   `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_replay.py:280`
   through
   `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_replay.py:320`
   proves only self-consistency between two browser-supplied structures. An
   authenticated user can call `/formatter-replay/complete` directly with a
   fabricated `sir_convert_job_id`, manifest, digest, and base64 body for their
   saved transcript; Skriptoteket will create a successful local replay job and
   download/save the fabricated bytes as producer-owned artifacts. That is a
   deceptive-degradation/false-authority path for the export truth boundary.
   Fix by binding persisted bytes to a Gateway/Sir Convert authority the
   backend can verify, for example a Gateway-signed owner/job/artifact receipt
   over artifact key, content type, size, digest, owner subject, and job id, or
   a server-mediated owner-delegated Gateway fetch. Add a behavioral test that
   manually posts a self-consistent but unsigned completion payload and proves
   no job/artifact bytes are persisted.

2. **high - artifact payload persistence has no explicit byte budget before
   base64 decode and database storage.**
   `src/skriptoteket/application/curated_apps/conversion_hub_transcript_replay.py:154`
   through
   `src/skriptoteket/application/curated_apps/conversion_hub_transcript_replay.py:166`
   bounds the list length but not `content_base64`; the parsed manifest
   `size_bytes` is only `ge=0` in
   `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_replay_parsing.py:111`.
   The frontend downloads all requested artifacts and base64-encodes them before
   completion at
   `frontend/apps/skriptoteket/src/api/conversionHubTranscriptFormatterReplay.ts:161`
   through
   `frontend/apps/skriptoteket/src/api/conversionHubTranscriptFormatterReplay.ts:178`,
   and the backend decodes/persists the resulting bytes at
   `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_replay.py:306`.
   This leaves the new request body, application memory, and
   `LargeBinary` column unprotected by the repo's existing `VAULT_MAX_FILE_BYTES`
   / `UPLOAD_MAX_FILE_BYTES` limits. Fix by adding an explicit per-artifact and
   total replay artifact byte limit at the completion boundary before decode
   and before persistence, with matching frontend fail-closed handling. Add
   tests for over-limit manifest sizes and over-limit decoded payloads.

3. **medium - the new trust-boundary validators lack fail-closed negative
   tests.**
   The new end-to-end payload test at
   `tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_payloads.py:57`
   covers the happy path from replay completion to download and Mina save, and
   existing action tests cover missing artifact records. They do not cover bad
   base64, duplicate payload keys, missing payload keys, wrong content type,
   size mismatch, checksum mismatch, or a ref-only row whose `content` is
   `None`. Those are the exact conditions guarded by
   `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_replay.py:280`
   through
   `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_replay.py:320`
   and
   `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_artifact_actions.py:305`
   through
   `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_artifact_actions.py:316`.
   Add focused behavioral tests proving each malformed payload fails closed
   without persisting records, and that legacy/ref-only rows cannot be downloaded
   or saved.

### Confirmed

- The retained artifact supports the stated immediate RCA: `network.bounded.json`
  in `20260613T203933Z` shows `/formatter-replay/complete` succeeded and the
  subsequent formatter artifact download returned HTTP `503` with `Failed to
  download named v2 artifact.`
- The direct backend Sir Convert named-artifact client was removed from
  download/save handlers; download and Mina-save now read persisted bytes only.
- Migration/model/repository wiring for the nullable `content` column is
  coherent, and the new revision is covered by the focused migration idempotency
  lane.
- No new `Any`, `cast(...)`, or `type: ignore` appeared in the reviewed diff.

### Verification

- `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_payloads.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_completion.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_result_envelope.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py`
  passed with `25 passed`.
- `pdm run fe-test -- --run frontend/apps/skriptoteket/src/api/conversionHubTranscriptFormatterReplay.spec.ts frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptReplayClient.spec.ts`
  passed with `6 passed`.
- `pdm run typecheck` passed.
- `pdm run lint` passed.
- `pdm run fe-type-check` passed.
- `pdm run test tests/integration/test_migration_revision_coverage_idempotent.py -k e9a4b6c8d2f0 --override-ini addopts=''`
  passed with `1 passed, 52 deselected`.
- `pdm run fe-lint` passed.
- `pdm run docs-validate` passed before this review update.
- `pdm run handoff-validate` passed.
- `git diff --check` passed.

### Required Remediation Proof

- Add backend authority proof for artifact payloads that cannot be forged by a
  browser caller, plus tests proving forged self-consistent completions fail.
- Add explicit replay artifact payload size limits and over-limit tests.
- Add malformed payload/ref-only negative tests.
- Rerun focused backend/frontend tests, migration idempotency, typecheck, lint,
  `fe-type-check`, `fe-lint`, `docs-validate`, `handoff-validate`, and
  `git diff --check`.

## Artifact Receipt Remediation Response

**Date:** 2026-06-13
**Responder:** GPT-5 implementation specialist
**Scope:** same artifact-download remediation slice after
`changes_requested`.

### Response To Findings

1. Replaced browser self-consistency with backend-verifiable authority.
   `/formatter-replay/complete` no longer accepts `artifact_manifest`; artifact
   refs are derived only from HuleEdu detached-RS256 artifact receipts verified
   against the configured HuleEdu trust key set. Browser-forwarded bytes are
   accepted only after the receipt job/key/content-type/size/SHA-256 binding
   matches the payload.
2. Added replay artifact byte budgets: 4 MiB per artifact and 8 MiB total.
   `content_base64` is bounded at the Pydantic boundary before decode, and the
   handler rejects decoded aggregate over-budget payloads before persistence.
3. Added fail-closed tests for forged self-consistent payloads, bad base64,
   duplicate and missing keys, content-type mismatch, size mismatch, checksum
   mismatch, total byte-budget breach, overlong base64 input, and ref-only
   `content=None` rows.

### Verification

- Red:
  `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_payloads.py -k browser_self_consistent`
  failed before the receipt patch because the forged self-consistent browser
  payload persisted.
- Green:
  `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_payloads.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_completion.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_result_envelope.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py`
  passed with `32 passed`.
- Green:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/api/conversionHubTranscriptFormatterReplay.spec.ts frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptReplayClient.spec.ts`
  passed with `6 passed`.
- Green: `pdm run fe-gen-api-types`, `pdm run typecheck`,
  `pdm run fe-type-check`, and `pdm run lint` passed.

### Residual Risk

The code now fails closed without HuleEdu-signed artifact receipts. Fresh live
proof remains blocked until HuleEdu Gateway emits the receipt headers on named
artifact downloads, or an accepted HuleEdu-owned delegated artifact-fetch
contract is implemented instead.

## Independent Re-Review: Artifact Receipt Remediation

**Date:** 2026-06-13
**Reviewer:** GPT-5 independent reviewer
**Decision:** changes_requested

### Findings

1. **high - signed artifact receipts are not bound to the authenticated
   HuleEdu subject before persistence.**
   The new receipt payload includes an owner-scoped `sub` claim at
   `src/skriptoteket/application/curated_apps/conversion_hub_transcript_replay.py:218`,
   but `/formatter-replay/complete` still receives only a local `User` via
   `require_app_user_api` at
   `src/skriptoteket/web/api/v1/apps_conversion_hub_transcript_saves.py:168`.
   That dependency has already discarded the HuleEdu projection context, and
   local `User` explicitly does not carry realm subjects
   (`src/skriptoteket/domain/identity/models.py:74`). The completion handler
   verifies receipt signature, artifact key, and Sir Convert job id at
   `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_replay.py:350`
   through
   `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_replay.py:355`,
   then persists the bytes under `actor.id` at
   `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_replay.py:212`.
   A valid HuleEdu-signed receipt for subject A can therefore be replayed by
   subject B against B's local transcript/job as long as the job id/key/payload
   checks match. This keeps the fix from proving owner-scoped authority. Bind
   each verified receipt to the current signed HuleEdu projection subject before
   deriving artifact refs or persisting bytes, and add a fail-closed test where
   the authenticated actor/projection subject differs from `receipt.sub`.

### Confirmed

- The self-attested browser manifest was removed from the completion contract;
  artifact refs are derived from signed receipts.
- Detached RS256 verification uses the configured HuleEdu trust-key set and
  rejects unknown key ids, malformed signatures, and bad payloads.
- Browser-forwarded bytes are validated against the verified receipt's key,
  content type, size, and SHA-256 before persistence.
- Replay artifact budgets are present: 4 MiB per artifact and 8 MiB total.
- Download and Mina-save handlers use persisted bytes only and fail closed for
  ref-only `content=None` rows.
- Migration/model/repository compatibility for nullable persisted artifact
  content is coherent.

### Verification

- `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_payloads.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_completion.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_result_envelope.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py`
  passed with `32 passed`.
- `pdm run fe-test -- --run frontend/apps/skriptoteket/src/api/conversionHubTranscriptFormatterReplay.spec.ts frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptReplayClient.spec.ts`
  passed with `6 passed`.
- `pdm run test --override-ini addopts='' -m docker 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[e9a4b6c8d2f0]'`
  passed with `1 passed`.
- `pdm run lint`, `pdm run typecheck`, `pdm run fe-type-check`,
  `pdm run fe-lint`, `pdm run docs-validate`, `pdm run handoff-validate`, and
  `git diff --check` passed.

## Receipt Subject Binding Remediation Response

**Date:** 2026-06-13
**Responder:** GPT-5 implementation specialist
**Scope:** same artifact receipt remediation slice after the second
`changes_requested`.

### Response To Finding

- Bound artifact receipts to the authenticated HuleEdu projection subject.
  `HuleEduAppUserProjection` now carries the resolved `realm_subject_id`, and
  `/formatter-replay/complete` receives the full projection through
  `require_app_user_projection_api` instead of only the local `User`.
- The route still performs app access against the local `User`, then forwards
  `projection.realm_subject_id` to the completion handler.
- The completion handler verifies each receipt signature and then rejects any
  receipt whose `sub` differs from the current projection subject before
  deriving artifact refs or writing replay job/artifact bytes.
- Added direct fail-closed coverage for a valid RS256 receipt belonging to a
  different HuleEdu subject, asserting no persisted job/artifact side effects.

### Verification

- `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_payloads.py -k different_huleedu_subject`
  passed with `1 passed, 7 deselected`.
- `pdm run test tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py -k complete_formatter_replay`
  passed with `1 passed, 8 deselected`.
- `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_payloads.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_completion.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_result_envelope.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py`
  passed with `33 passed`.
- `pdm run test tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_profile_app_continuation_dependencies_api.py tests/unit/web/test_profile_app_continuation_context_api.py`
  passed with `38 passed`.
- `pdm run fe-test -- --run frontend/apps/skriptoteket/src/api/conversionHubTranscriptFormatterReplay.spec.ts frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptReplayClient.spec.ts`
  passed with `6 passed`.
- `pdm run typecheck`, `pdm run lint`, `pdm run fe-type-check`,
  `pdm run fe-lint`, `pdm run docs-validate`, `pdm run handoff-validate`, and
  `git diff --check` passed.

## Independent Re-Review: Receipt Subject Binding

**Date:** 2026-06-13
**Reviewer:** GPT-5 independent reviewer
**Decision:** approved

### Findings

No findings. The previous high-severity subject-binding finding is resolved.

### Confirmed

- `/formatter-replay/complete` now depends on
  `require_app_user_projection_api`, keeps app access checks on
  `projection.user`, and passes the verified `projection.realm_subject_id` into
  replay completion.
- `HuleEduAppUserProjection` carries `realm_subject_id` from the verified
  projection key on both existing-projection and provisioning paths.
- Replay completion verifies each detached RS256 receipt, rejects `receipt.sub`
  mismatch before deriving artifact refs or opening the Unit of Work, and only
  then validates/persists artifact bytes.
- The prior confirmed areas still hold: no browser self-attested manifest in
  the completion path, real HuleEdu trust-key RS256 verification, explicit 4 MiB
  per-artifact and 8 MiB total budgets, persisted bytes only for download and
  Mina-save, and ref-only `content=None` rows fail closed.

### Verification

- `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_payloads.py -k different_huleedu_subject`
  passed with `1 passed, 7 deselected`.
- `pdm run test tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py -k complete_formatter_replay_delegates_to_handler`
  passed with `1 passed, 8 deselected`.
- `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_payloads.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_completion.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_result_envelope.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py`
  passed with `33 passed`.
- `pdm run test tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_profile_app_continuation_dependencies_api.py tests/unit/web/test_profile_app_continuation_context_api.py tests/unit/web/test_huleedu_identity_context_probe_api.py tests/unit/application/identity/test_bootstrap_projection_role_matrix.py tests/unit/application/identity/test_bootstrap_subject_export_schema.py`
  passed with `63 passed`.
- `pdm run fe-test -- --run frontend/apps/skriptoteket/src/api/conversionHubTranscriptFormatterReplay.spec.ts frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptReplayClient.spec.ts`
  passed with `6 passed`.
- `pdm run test --override-ini addopts='' -m docker 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[e9a4b6c8d2f0]'`
  passed with `1 passed`.
- `pdm run lint`, `pdm run typecheck`, `pdm run fe-type-check`,
  `pdm run fe-lint`, and `git diff --check` passed.
