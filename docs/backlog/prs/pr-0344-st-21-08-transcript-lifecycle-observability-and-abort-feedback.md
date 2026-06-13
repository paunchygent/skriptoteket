---
type: pr
id: PR-0344
title: "ST-21-08 Transcript lifecycle observability and abort feedback"
status: done
owners: "agents"
created: 2026-06-13
updated: 2026-06-13
stories:
  - "ST-21-08"
tags:
  - frontend
  - conversion-hub
  - transcript
  - observability
  - gateway
dependencies:
  - "PR-0342"
  - "PR-0343"
  - "Sir Convert Task 357"
  - "HuleEdu TASK-0570"
acceptance_criteria:
  - "Given Gateway job status includes Sir Convert progress fields, when Skriptoteket parses the response, then it preserves a strict typed progress snapshot with status, stage, heartbeat, current phase start, processed seconds, total seconds, percent, chunk index/count, and phase timings."
  - "Given a transcript job is running, when the UI renders progress, then it shows truthful running progress and last-update state instead of a spinner-only empty panel."
  - "Given cancel is requested, when Gateway/Sir Convert accepts, rejects, or times out the cancel, then the UI shows a clear abort outcome and disables only the actions that are no longer valid."
  - "Given progress data is missing or malformed, when parsing fails, then Skriptoteket fails closed with teacher-facing copy and no loose string or catch-all progress typing."
  - "Given observability data is logged or measured, when transcript jobs run, then transcript text, utterances, source content, speaker names, media hashes as labels, and provider/model details are excluded."
---

# PR-0344: ST-21-08 Transcript Lifecycle Observability And Abort Feedback

## Problem

The current transcript workspace can appear stalled because it does not consume
the full Sir Convert progress contract that is already live-proven by Task 357.
Abort feedback is similarly under-specified for teachers.

## Goal

Make transcript progress and cancel outcomes truthful, typed, and visible
through the existing HuleEdu Gateway lifecycle client.

## Non-goals

- No speaker naming.
- No formatter/export actions.
- No durable source-audio storage.
- No new Gateway route or direct Sir Convert browser traffic.

## Implementation Plan

- Regenerate or align Sir Convert/Gateway response types so current progress
  fields are represented without stale DTO gaps.
- Replace the current narrow progress parser with a strict transcript progress
  value object.
- Render heartbeat, processed/total seconds, percent, chunk position, stage,
  retry/cancel state, and failure state in the transcript workspace.
- Add cancel-state transitions for requested, accepted, failed, timed out, and
  terminal states.
- Keep UI copy teacher-facing and avoid implementation jargon.

## Implementation Summary

Done on 2026-06-13. Skriptoteket now parses transcript lifecycle responses
into one strict `progress` snapshot instead of the earlier narrow audio-only
shape. The snapshot preserves job status, typed phase, heartbeat, current phase
start, processed/total media seconds, percent, chunk index/count, and typed
phase timing counters. Running/processing jobs without progress, unknown
phases, malformed timestamps, invalid percentages, negative counters, or
out-of-bounds chunk counters fail closed at the Gateway client boundary.

The transcript runtime now carries an explicit abort state:
`idle`, `pending`, `accepted`, `failed`, `rejected`, or `timed_out`. A cancel
request only stops polling after Gateway returns a canceled/cancelled job. A
failed, rejected, or timed-out cancel leaves the job polling alive and renders
teacher-facing feedback that transcription continues.

The workspace now renders a compact Swedish progress surface with phase copy,
percent, processed/total duration, chunk position, heartbeat timestamp, and
abort feedback when present. It does not render raw upstream/internal stage
strings. Formatter replay, TXT/MD/VTT/SRT exports, speaker overlays, and
artifact persistence remain out of scope for later `ST-21-08` slices.

## Test Plan

- Red-first parser tests for full Task 357 progress payloads and malformed
  payload rejection.
- Red-first workspace tests proving running progress and cancel feedback render.
- Focused frontend typecheck, lint, and build.
- Docs validation and handoff validation.

## Verification

- Red-first:
  `pdm run fe-test -- --run src/api/sirConvertGateway/transcriptClient.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts src/views/apps/conversion-hub-transcript/useTranscriptGatewayRuntime.spec.ts`
  failed before implementation with missing `progress`, malformed progress
  accepted, `audioProgress` access in the workspace, and missing runtime
  `abortState`.
- Focused green:
  same command passed with 3 files and 20 tests.
- Broader transcript frontend:
  `pdm run fe-test -- --run src/views/apps/ConversionHubTranscriptMode.spec.ts src/api/conversionHubTranscriptSaves.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts src/views/apps/conversion-hub-transcript/useTranscriptGatewayRuntime.spec.ts src/api/sirConvertGateway/transcriptClient.spec.ts`
  passed with 5 files and 23 tests.
- Static/build gates:
  `pdm run fe-type-check`, `pdm run fe-lint`, and `pdm run fe-build` passed.
  `fe-build` emitted the existing Vite large-chunk warnings.
- Live browser check:
  `pdm run fe-dev` started Vite at `http://localhost:5173/`. In-app Browser
  opened `/apps/documents.conversion_hub` and landed on
  `http://localhost:5173/auth/login?next=/apps/documents.conversion_hub` with
  no console errors. No authenticated transcript workspace proof was claimed
  because this turn did not run the HuleEdu browser-session ceremony.
- Overseer close-out:
  retained review
  `docs/backlog/reviews/review-pr-0344-transcript-lifecycle-observability-and-abort-feedback.md`
  is approved after re-review. Main-session verification on 2026-06-13 passed
  `pdm run fe-test -- --run src/api/sirConvertGateway/transcriptClient.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts src/views/apps/conversion-hub-transcript/useTranscriptGatewayRuntime.spec.ts src/views/apps/ConversionHubTranscriptMode.spec.ts`
  with 4 files / 23 tests, plus `pdm run fe-type-check`,
  `pdm run fe-lint`, `pdm run fe-build`, `pdm run docs-validate`,
  `pdm run handoff-validate`, and `git diff --check`. `fe-build` emitted the
  existing Vite chunk-size warnings.

## Rollback Plan

Hide the enriched progress/cancel panel and return to terminal-only status
rendering. Do not change job submission or artifact retrieval semantics.
