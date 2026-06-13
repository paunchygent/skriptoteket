---
type: pr
id: PR-0347
title: "ST-21-08 Overlay-aware formatter replay client"
status: done
owners: "agents"
created: 2026-06-13
updated: 2026-06-13
stories:
  - "ST-21-08"
tags:
  - backend
  - frontend
  - gateway
  - transcript
  - formatter
  - replay
dependencies:
  - "PR-0345"
  - "PR-0346"
  - "Sir Convert Task 359"
  - "Sir Convert Task 360"
  - "HuleEdu TASK-0675"
acceptance_criteria:
  - "Given a saved transcript and speaker overlay exist, when the teacher requests formatter replay, then Skriptoteket submits saved canonical JSON plus typed `speaker_label_overrides` through HuleEdu Gateway using Sir Convert `transcript_json -> transcript_bundle`."
  - "Given Sir Convert returns replay job status, result, and artifacts, when Skriptoteket parses them, then only named `transcript_txt`, `transcript_md`, `transcript_vtt`, and `transcript_srt` artifact references are accepted."
  - "Given replay fails or omits an overlay-aware artifact, when export was requested, then Skriptoteket reports the failure and does not fall back to local formatting or canonical-label artifacts."
  - "Given replay requests are logged, when telemetry is emitted, then saved transcript text, speaker display names, utterances, source content, and model/provider details are excluded."
---

# PR-0347: ST-21-08 Overlay-Aware Formatter Replay Client

## Problem

Skriptoteket needs to request overlay-aware exports from the producer without
becoming a formatter or reusing source audio.

## Goal

Add a strict replay client and parser for Sir Convert overlay-aware formatter
jobs through HuleEdu Gateway.

## Non-goals

- No Mina filer save action.
- No direct artifact download UI.
- No browser-local formatter fallback.
- No new direct Sir Convert browser path.

## Implementation Plan

- Added backend/application orchestration that loads owner-scoped saved
  canonical JSON and persisted speaker overlays, then prepares the strict Sir
  Convert replay JobSpec for `transcript_json -> transcript_bundle`.
- Added strict backend/frontend replay result and artifact parsing. Accepted
  refs are limited to `transcript_txt`, `transcript_md`, `transcript_vtt`, and
  `transcript_srt`; malformed responses, unknown artifact keys, missing
  requested artifacts, unknown formats, and stale `not_implemented` responses
  fail closed.
- Added frontend command orchestration that prepares through Skriptoteket,
  submits through HuleEdu Gateway, records parsed producer refs, and renders
  compact success/failure/availability state without download actions.
- Persisted replay provenance through a local `ConversionHubJob` for later
  PR-0348 authorization.

## Test Plan

- Red evidence:
  - `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py` failed on missing replay module.
  - `pdm run fe-test -- --run src/api/sirConvertGateway/transcriptReplayClient.spec.ts src/api/conversionHubTranscriptFormatterReplay.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts` failed on missing replay client/module/button.
- Green evidence:
  - `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py` passed with 11 tests.
  - `pdm run fe-test -- --run src/api/sirConvertGateway/transcriptReplayClient.spec.ts src/api/conversionHubTranscriptFormatterReplay.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts` passed with 12 tests.
  - `pdm run fe-gen-api-types`, `pdm run typecheck`, `pdm run lint`,
    `pdm run fe-type-check`, `pdm run fe-lint`, and `pdm run fe-build` passed.
- Not run by design: `PR-0349` live authenticated proof.

## Rollback Plan

Disable replay commands and preserve saved transcript speaker overlays for
later export attempts.
