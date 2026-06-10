---
type: pr
id: PR-0342
title: "ST-21-05 Transcript intake and Gateway lifecycle client"
status: done
owners: "agents"
created: 2026-06-10
updated: 2026-06-10
stories:
  - "ST-21-05"
  - "ST-21-06"
tags:
  - frontend
  - conversion-hub
  - transcript
  - sir-convert
  - huleedu-gateway
  - diarization
dependencies:
  - "HuleEdu TASK-0570"
  - "Sir Convert Task 356"
acceptance_criteria:
  - "Given a signed-in teacher opens Conversion Hub, when transcript mode is selected, then the UI offers authenticated audio/video upload and speaker controls without public/no-login/direct Sir Convert access."
  - "Given speaker controls are submitted, when the user chooses auto, exact count, or min/max range, then the client maps them to Sir Convert `auto`, `known_speaker_count`, or `speaker_range` and rejects invalid combinations before submit."
  - "Given a valid transcript submission, when the client calls HuleEdu Gateway, then it posts `audio -> transcript_bundle` with `audio_transcription_options`, CSRF, idempotency, and correlation headers through the existing `sirConvertGateway` adapter family."
  - "Given a transcript job runs, succeeds, fails, or is canceled, when the UI polls Gateway, then status, result, artifact manifest, named `transcript_json` download, and cancel handling are reflected without exposing model/provider/internal-service details."
  - "Given `transcript_json` is returned, when the client parses it, then missing JSON, empty transcript, missing speaker labels, diarization unavailable, or failed alignment are treated as failure rather than success."
---

# PR-0342: ST-21-05 Transcript Intake And Gateway Lifecycle Client

## Problem

Skriptoteket has approved planning stories for authenticated transcript intake
and job lifecycle, but no implemented Conversion Hub transcript lane. Sir
Convert now has accepted canonical JSON runtime behavior, and HuleEdu
`TASK-0570` is the remaining Gateway edge task needed for the full lifecycle
including cancel.

## Goal

Add the first authenticated transcript lane in Conversion Hub by extending the
existing `sirConvertGateway` client family and bespoke app UI to submit,
poll, cancel, and retrieve canonical `transcript_json` artifacts through
HuleEdu Gateway.

## Non-goals

- No public/no-login transcript workflow.
- No direct Sir Convert browser credentials or direct `convert.hule.education`
  calls.
- No local STT, diarization, alignment, or transcript repair fallback.
- No durable transcript save in this PR; that is `PR-0343`.
- No TXT, Markdown, VTT, or SRT formatter output.

## Implementation Plan

1. Add purpose-named transcript request/value modules under
   `frontend/apps/skriptoteket/src/api/sirConvertGateway/` for
   `audio -> transcript_bundle`, `audio_transcription_options`,
   speaker-setting validation, lifecycle progress, cancel, and
   `transcript_json` parsing.
2. Extend the authenticated Conversion Hub UI with a transcript mode that uses
   file upload controls and explicit speaker controls:
   automatic, known speaker count, and min/max speaker range.
3. Reuse the existing Gateway base URL, CSRF, idempotency, correlation, and
   error-normalization patterns from the Exam Converter authenticated lane.
4. Render progress and failures in teacher-facing language without model,
   provider, sidecar, media-hash-label, or transcript-text leakage.
5. Treat malformed or false-success `transcript_json` shapes as failures until
   `PR-0343` persists a valid JSON artifact.
6. Keep code and test files named by domain purpose, not story or task number.

## Test Plan

- Red-first Vitest for speaker option mapping and invalid combinations.
- Red-first Vitest for transcript job submission body, CSRF,
  `Idempotency-Key`, and correlation behavior through `sirConvertGateway`.
- Red-first Vitest for status/result/artifact/cancel lifecycle handling and
  false-success `transcript_json` rejection.
- Focused Conversion Hub component tests for transcript mode upload controls,
  progress, cancel, and teacher-facing error copy.
- `pdm run fe-test -- --run <focused transcript and sirConvertGateway specs>`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- Live authenticated browser proof through HuleEdu Gateway after HuleEdu
  `TASK-0570` lands, ending in a complete and parsable `transcript_json`
  response.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Implementation Evidence

Local implementation added the first authenticated transcript lane in the
existing Conversion Hub host. The slice extends
`frontend/apps/skriptoteket/src/api/sirConvertGateway/` with transcript
request values, deterministic Gateway request context, lifecycle parsers, named
`transcript_json` parsing, and cancel-capable client methods. The UI adds a
bespoke transcript mode with audio/video intake, automatic/exact/range speaker
controls, progress/failure/cancel state, and parsed JSON preview. It does not
add public/no-login/direct Sir Convert access, local STT/diarization, durable
transcript save, or formatter output.

Red-first evidence:

- `pdm run fe-test -- src/api/sirConvertGateway/transcriptOptions.spec.ts src/api/sirConvertGateway/transcriptClient.spec.ts`
  failed before implementation with missing `./transcriptOptions` and missing
  `submitTranscriptJob`, `getTranscriptJob`, and `downloadTranscriptJson`
  methods.
- `pdm run fe-test -- src/views/apps/ConversionHubTranscriptMode.spec.ts`
  failed before UI implementation because
  `[data-test="conversion-hub-mode-transcript"]` did not exist.

Green evidence:

- `pdm run fe-test -- src/api/sirConvertGateway/transcriptOptions.spec.ts src/api/sirConvertGateway/transcriptClient.spec.ts src/views/apps/ConversionHubTranscriptMode.spec.ts`
  passed with 8 tests.
- `pdm run fe-type-check` passed.
- `pdm run fe-lint` passed.
- `pdm run docs-validate` passed.
- `git diff --check` passed.

Live authenticated Hule/Sir end-to-end proof was not run in this slice. The
accepted HuleEdu TASK-0570 cancel edge is documented as reviewed, but public
deployment proof must still be run against the target shared-auth/Gateway
environment before claiming live product evidence.

### Remediation Evidence

Ruthless review `REV-PR-0342` requested two fixes: sanitize producer-owned
transcript progress stages before rendering them to teachers, and complete the
false-success `transcript_json` rejection proof matrix. Red-first focused
evidence:

- `pdm run fe-test -- src/api/sirConvertGateway/transcriptClient.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts`
  failed because `TranscriptWorkspaceShell` rendered
  `pyannote_sidecar_model_warmup` instead of safe Swedish progress copy. The
  added false-success matrix already passed against the fail-closed parser.

Green remediation evidence:

- `pdm run fe-test -- src/api/sirConvertGateway/transcriptClient.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts`
  passed with 12 tests.
- `pdm run fe-test -- src/api/sirConvertGateway/transcriptOptions.spec.ts src/api/sirConvertGateway/transcriptClient.spec.ts src/views/apps/ConversionHubTranscriptMode.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts`
  passed with 17 tests.
- `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run docs-validate`,
  `pdm run handoff-validate`, and `git diff --check` passed.

Retained review `REV-PR-0342` is approved. Live authenticated Hule/Sir
end-to-end proof remains a truthful follow-up and is not claimed as completed
by this local client/UI slice.

## Rollback Plan

Disable the transcript mode affordance while keeping the existing Exam
Converter `sirConvertGateway` lane intact. Do not add a direct Sir Convert
fallback or public transcript path.
