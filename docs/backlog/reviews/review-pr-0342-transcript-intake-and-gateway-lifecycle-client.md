---
type: review
id: REV-PR-0342
title: "Review: PR-0342 transcript intake and Gateway lifecycle client"
status: approved
owners: "agents"
created: 2026-06-10
updated: 2026-06-10
reviewer: "Codex"
prs:
  - PR-0342
links:
  - EPIC-21
  - ST-21-05
  - ST-21-06
---

# Review: PR-0342 Transcript Intake And Gateway Lifecycle Client

## TL;DR

Verdict: `approved`.

Re-review approved after remediation. Transcript submit/read/result/list/download/cancel stays on the HuleEdu `/sir-convert/v2/convert/...` edge, uses browser credentials, uses CSRF for unsafe methods, sends `Idempotency-Key` and correlation headers on submit, and does not send a browser `X-API-Key`. The previous blockers are resolved: upstream job stages are mapped to safe Swedish progress copy before rendering, and the false-success `transcript_json` parser matrix now covers the PR acceptance cases.

## Problem Statement

`PR-0342` is the first authenticated Conversion Hub transcript lane for `ST-21-05` and `ST-21-06`. The review checks whether Skriptoteket adds a bespoke transcript UI and HuleEdu Gateway lifecycle client without adding public/no-login/direct Sir Convert access, local STT/diarization fallback, provider/model leakage, or fail-open transcript JSON handling.

## Proposed Solution

The implementation adds transcript request values, lifecycle parsers, transcript JSON parsing, transport methods, and a Conversion Hub transcript mode under the existing authenticated host. Durable transcript save remains out of scope for `PR-0342` and belongs to `PR-0343` / `ST-21-07`.

## Artifacts to Review

| File | Focus | Result |
|------|-------|--------|
| `docs/backlog/prs/pr-0342-st-21-05-transcript-intake-and-gateway-lifecycle-client.md` | Governing scope, acceptance criteria, evidence | Approved |
| `docs/backlog/stories/story-21-05-conversion-hub-transcript-intake-and-diarization-controls.md` | Transcript intake and copy boundary | Approved |
| `docs/backlog/stories/story-21-06-transcript-job-lifecycle-through-huleedu-gateway.md` | Gateway lifecycle and false-success boundary | Approved |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptOptions.ts` | Speaker controls and JobSpec mapping | Approved |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptRequestContext.ts` | Idempotency and correlation construction | Approved |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/client.ts` | Gateway transport methods | Approved |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptParsers.ts` | Lifecycle and transcript JSON parsing | Approved |
| `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/` | Bespoke transcript UI and runtime | Approved |
| `frontend/apps/skriptoteket/src/views/apps/ConversionHubTranscriptMode.spec.ts` | UI behavior proof | Approved |
| `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts` | Stage-sanitization DOM proof | Approved |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptClient.spec.ts` | Gateway and parser proof | Approved |

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Use authenticated HuleEdu Gateway only for transcript jobs | Matches `ST-21-05`/`ST-21-06`; no public/no-login/direct Sir Convert path was added | [x] |
| Map auto/exact/range speaker controls to `auto`, `known_speaker_count`, and `speaker_range` | `transcriptOptions.ts` rejects invalid exact/range values before submit | [x] |
| Add status/result/manifest/download/cancel methods on the existing Gateway client family | Methods and URLs match the accepted lifecycle shape | [x] |
| Treat `transcript_json` as the only success authority | Parser code is fail-closed and the false-success matrix is covered by focused tests | [x] |
| Keep model/provider/internal-service terms out of teacher UI | Upstream stage values are mapped to bounded teacher-facing copy with DOM proof for unsafe input | [x] |
| Treat missing live Hule/Sir proof as follow-up until TASK-0570 is available in target deployment | The PR records the absence truthfully; not a blocker for local client approval by itself | [x] |

## Review Checklist

- [x] Governing PR and related stories were reviewed.
- [x] Out-of-scope dirty `AGENTS.md` was ignored.
- [x] No public/no-login transcript route or direct Sir Convert service host was added in the reviewed transcript implementation.
- [x] No browser `X-API-Key` is sent by the focused transcript client tests.
- [x] Submission uses `credentials: include`, CSRF, `Idempotency-Key`, and correlation headers.
- [x] Status/result/artifact/download/cancel route methods were checked.
- [x] File and test names are purpose-based, not PR/story/task-numbered.
- [x] Focused Vitest, frontend typecheck, and frontend lint reproduced green locally.
- [x] Teacher-facing progress copy is sanitized from upstream internals.
- [x] Full false-success transcript JSON rejection matrix is covered by behavioral tests.

## Review Feedback

**Reviewer:** Codex
**Date:** 2026-06-10
**Verdict:** approved

### Required Changes

None active after re-review.

### Resolved Findings

1. **Resolved high:** `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.vue` no longer renders `currentJob.stage` directly. `transcriptProgressLabel(...)` maps known stages to bounded Swedish copy and sends unknown/internal stages to `Bearbetar inspelningen.`. `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts` proves that `pyannote_sidecar_model_warmup`, `sidecar`, `model`, and `pyannote` do not reach rendered DOM text.

2. **Resolved medium:** `frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptClient.spec.ts` now includes a parameterized false-success matrix for missing JSON payload, empty segments, missing transcript text, empty transcript text, missing speaker labels, diarization unavailable, diarization failed, `diarization_unavailable`, and alignment failed. Each case asserts `SIR_CONVERT_CONTRACT_DRIFT` from the client boundary.

### Non-Blocking Follow-Up

Live authenticated Hule/Sir end-to-end proof was not run and is not claimed. Because `PR-0342` already makes that conditional on HuleEdu `TASK-0570` availability, this is a follow-up rather than a blocker for the local client/UI slice. The follow-up proof must use the HuleEdu browser-session ceremony and verify Gateway-owned submit, cancel, manifest, and named `transcript_json` download through `/sir-convert/v2/convert/...`.

## Verification

- `pdm run fe-test -- src/api/sirConvertGateway/transcriptOptions.spec.ts src/api/sirConvertGateway/transcriptClient.spec.ts src/views/apps/ConversionHubTranscriptMode.spec.ts` passed locally with 3 files and 8 tests.
- Re-review: `pdm run fe-test -- src/api/sirConvertGateway/transcriptOptions.spec.ts src/api/sirConvertGateway/transcriptClient.spec.ts src/views/apps/ConversionHubTranscriptMode.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts` passed locally with 4 files and 17 tests.
- `pdm run fe-type-check` passed locally.
- `pdm run fe-lint` passed locally.
- Context7 was checked for current Vue Test Utils, Vitest, and Zod guidance. The applicable review standard remains: test public DOM/output behavior, reset mocks cleanly, and fail closed on runtime schema/contract mismatches.
- Live authenticated Hule/Sir proof was not run.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0342` | Created retained ruthless review record with `changes_requested` verdict, findings, verification, and live-proof follow-up. |
| 2 | `REV-PR-0342` | Re-reviewed remediation and approved after verifying safe stage-label rendering and complete false-success parser proof. |
