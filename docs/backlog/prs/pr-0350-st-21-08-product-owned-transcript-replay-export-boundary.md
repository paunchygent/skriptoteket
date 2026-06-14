---
type: pr
id: PR-0350
title: "ST-21-08 Product-owned transcript replay export boundary"
status: in_progress
owners: "agents"
created: 2026-06-14
updated: 2026-06-14
stories:
  - "ST-21-08"
tags:
  - backend
  - frontend
  - transcript
  - formatter
  - replay
  - architecture
dependencies:
  - "PR-0348"
  - "Sir Convert task-363 completed at 4b09baa989d38f582573a810f045e50c676139a9"
acceptance_criteria:
  - "Given a teacher requests transcript exports, when the browser clicks the export action, then Skriptoteket records product intent and returns product-owned export state without the browser submitting, polling, downloading, base64-encoding, or completing Sir Convert replay."
  - "Given Sir Convert replay is available through the accepted fast producer lane, when Skriptoteket creates exports, then the backend-owned workflow obtains and verifies producer artifact authority before persisting TXT, Markdown, VTT, and SRT bytes/provenance."
  - "Given replay exceeds the bounded fast-lane budget, when the UI observes the export, then it shows explicit product-owned pending/failure/progress state instead of a disabled button with silent foreground waiting."
  - "Given cleanup is complete, when the reviewer inspects the implementation, then no browser-owned prepare-submit-poll-download-base64-complete replay path, fallback, or saga-specific test remains."
  - "Given the old saga was removed, when focused tests run, then they prove the product-owned export behavior rather than direct browser Sir Convert replay submission, browser artifact receipt collection, or browser byte courier behavior."
---

# PR-0350: ST-21-08 Product-Owned Transcript Replay Export Boundary

## Problem

`PR-0347` implemented overlay-aware replay with the browser as the workflow
coordinator: prepare in Skriptoteket, submit through HuleEdu Gateway, wait on
Sir Convert, poll status, download named artifacts, collect Gateway receipts,
base64 artifact bytes, and call Skriptoteket `complete`.

That preserved artifact authority but violated the Conversion Hub / DXE
converter pattern. The browser must express teacher intent and observe product
state; it must not run producer workflows or carry artifact bytes back to the
backend.

The production symptom exposed the architecture defect: a manual export for
transcript `aaf12956-67c3-4cd6-8094-b2e264ad2b59` took about 119 seconds from
`formatter-replay/prepare` 200 to `formatter-replay/complete` 200 because the
foreground UI was waiting across Sir Convert submit, poll, artifact fetch, and
complete. The later proof path was fast, but the architecture still permits a
simple export button to become a silent distributed workflow.

## Goal

Replace the browser-owned replay saga with the same product-owned boundary used
by the converter lanes:

- browser records export intent and observes state;
- Skriptoteket owns local product export job/provenance and teacher-facing
  actions;
- HuleEdu/Sir Convert provide producer authority through a typed server-owned
  contract;
- Sir Convert owns deterministic formatter artifacts through the fast replay
  lane from `task-363`.

## Non-goals

- No API-key identity fallback.
- No direct browser Sir Convert replay path.
- No browser byte courier path.
- No local TXT/Markdown/VTT/SRT formatter fallback.
- No parallel legacy/new export flow.
- No retention of tests whose purpose is to assert the removed browser saga.
- No anti-pattern or meta tests that encode the old design as a permanent
  system surface.

## Implementation Plan

- Add a Skriptoteket-owned export request/status boundary for saved transcript
  formatter exports.
- Consume Sir Convert `task-363` fast replay through the accepted Service API
  v2 producer contract from the backend, preserving artifact authority without
  moving orchestration into the browser.
- Persist export artifacts and provenance through the existing
  `conversion_hub_transcript_formatter_artifacts` authority after server-side
  producer verification.
- Replace the frontend replay command with a product API call plus visible
  product-owned state.
- Delete browser replay orchestration code, including direct replay submit,
  polling, artifact download, receipt-header collection, base64 encoding, and
  completion courier behavior.
- Rewrite tests so they prove the product-owned workflow and no longer assert
  the removed implementation.
- Update `PR-0349` proof to depend on this slice before final live closeout.

## Accepted Producer Contract

Sir Convert task-363 is completed, pushed, and deployed on Hemma at
`4b09baa989d38f582573a810f045e50c676139a9`. The deploy report passed with
remote/service revision parity, v2 live smoke, metrics safety, public HTTPS/TLS,
nginx host registration, and default-host placeholder checks.

Skriptoteket must consume the existing Service API v2 job lifecycle from the
backend:

- `POST /v2/convert/jobs?wait_seconds=0`
- multipart `file=@saved-transcript.json;type=application/json`
- headers: `X-API-Key`, `Idempotency-Key`, optional `X-Correlation-ID`
- `job_spec.api_version = "v2"`
- `source = {"kind": "upload", "filename": "saved-transcript.json", "format": "transcript_json"}`
- `conversion = {"output_format": "transcript_bundle"}`
- `transcript_formatter_options.schema_version = "transcript_formatter_replay_v1"`
- `transcript_formatter_options.requested_artifacts = ["txt", "md", "vtt", "srt"]`
- `transcript_formatter_options.speaker_label_overrides` maps exact canonical
  speaker labels to teacher display names.
- `retention = {"pin": false}`

Accepted `wait_seconds=0` behavior:

- valid admitted replay returns HTTP `200` with terminal
  `job.status = "succeeded"`;
- fail-closed execution errors return HTTP `200` with terminal
  `job.status = "failed"`;
- request-shape validation errors still use the normal v2 error envelope before
  job creation.

Artifact authority:

- `/result` points to `transcript_replay_bundle_manifest.json`;
- `/artifacts` and `/artifacts/{artifact_key}` are authoritative for named
  outputs;
- named outputs are `transcript_txt`, `transcript_md`, `transcript_vtt`, and
  `transcript_srt`;
- replay does not emit `transcript_json`.

Downstream smoke command retained upstream:

`pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_replay_fast_lane_v2.py::test_downstream_replay_fast_lane_smoke_fetches_overlay_artifact -q`

## Required Cleanup

The implementation is not accepted until the old path is gone, not merely
unused:

- Remove browser replay workflow ownership from
  `requestConversionHubTranscriptFormatterReplay`.
- Remove browser replay `waitSeconds: 20`.
- Remove browser replay polling for Sir Convert terminal status.
- Remove browser artifact download and `arrayBufferToBase64` courier behavior.
- Remove browser-facing replay completion as the normal artifact-byte proof
  path.
- Delete or rewrite tests that expect the browser to submit to
  `/sir-convert/v2/convert/jobs`, fetch `/artifacts/{key}`, collect Gateway
  receipt headers, or send `artifact_payloads` back to Skriptoteket as export
  completion.

Receipt verification code may remain only if the new server/delegated contract
uses it as the product-owned authority check. It must not justify keeping the
browser byte courier.

## Test Plan

- Focused backend tests proving product-owned export creation persists verified
  TXT/Markdown/VTT/SRT artifacts and provenance.
- Focused frontend tests proving the browser calls Skriptoteket product export
  endpoints and renders product-owned pending/succeeded/failed states.
- Focused failure tests proving producer drift, missing artifacts, and bad
  authority fail closed through the product-owned boundary.
- Live browser proof after Sir Convert `task-363` passes and the product-owned
  path is deployed.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Implementation Evidence

Implemented in this branch as a product-owned boundary:

- `POST /api/v1/apps/documents.conversion_hub/transcripts/{transcript_id}/formatter-exports`
  records export intent, builds the accepted task-363 producer request
  server-side, verifies `/result`, `/artifacts`, and named artifact bytes, then
  persists product export state.
- `GET /api/v1/apps/documents.conversion_hub/transcripts/{transcript_id}/formatter-exports`
  returns latest product export state or `not_requested`.
- Response shape is product-safe only: `transcript_id`,
  `conversion_hub_job_id`, `status`, `requested_artifacts`, `artifacts`,
  `error_message`, `created_at`, and `updated_at`.
- Browser-owned prepare/submit/poll/download/base64/complete replay saga files,
  direct replay Gateway client, and saga tests were removed or rewritten.
- No migration was added; existing local Conversion Hub job rows and formatter
  artifact rows represent pending, failed, and succeeded export state.

Red evidence:

- `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_exports.py`
  initially failed with `ModuleNotFoundError` for the missing product export
  module.
- `pdm run fe-test -- --run src/api/conversionHubTranscriptFormatterExports.spec.ts`
  initially failed because the new product export API client did not exist.

Green evidence:

- `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_exports.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py`
  passed with 24 tests.
- `pdm run fe-test -- --run src/api/conversionHubTranscriptFormatterExports.spec.ts src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts src/api/conversionHubTranscriptFormatterArtifactActions.spec.ts src/api/sirConvertGateway/client.spec.ts src/api/sirConvertGateway/transcriptClient.spec.ts`
  passed with 50 tests.
- `pdm run fe-gen-api-types`, `pdm run lint`, `pdm run typecheck`,
  `pdm run fe-type-check`, `pdm run fe-lint`, and `pdm run fe-build` passed.
  `fe-build` retained the existing Vite dynamic/static import and large chunk
  warnings.

## Rollback Plan

Hide the export action and keep saved transcripts plus speaker overlays
available. Do not restore the browser-owned replay saga as rollback.
