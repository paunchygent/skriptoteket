---
type: review
id: REV-PR-0349
title: "Review: PR-0349 Transcript Parity Live Proof And Closeout"
status: approved
owners: "agents"
created: 2026-06-13
updated: 2026-06-13
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

No findings. The earlier cancel-path truthfulness issue is resolved by
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
