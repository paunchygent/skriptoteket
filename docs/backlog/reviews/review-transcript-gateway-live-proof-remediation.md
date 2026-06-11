---
type: review
id: REV-PR-0342
title: "Review: Transcript Gateway live-proof remediation"
status: approved
owners: "agents"
created: 2026-06-11
updated: 2026-06-11
reviewer: "fixed-ruthless-review-agent"
prs:
  - PR-0342
links:
  - EPIC-21
  - ST-21-05
  - ST-21-06
  - PR-0343
---

# Review: Transcript Gateway Live-Proof Remediation

## TL;DR

Approved after re-review. Commit
`31bd0ce0b5ae0bdb9568d3d260d093fd3b5cab9c` closes the previous
false-success gap by rejecting canonical
`diarization.used_mode = "diarization_unavailable"` and updating the focused
client tests to use the real producer field. The deployed proof now supports
accepting the full successful product path through Skriptoteket -> HuleEdu
Gateway `/sir-convert` -> Sir Convert -> STT/diarization ->
`transcript_json` for both English and Swedish fixtures.

## Problem Statement

`PR-0342` was previously approved as a local authenticated transcript lane, with
live HuleEdu/Sir proof left as the remaining product evidence. The first
live-proof review requested one fix: false-success rejection had to target the
canonical `diarization.used_mode` field rather than the earlier
`diarization.mode_used` shape. This re-review checks that the blocker is
closed, deployed, and backed by truthful focused evidence.

## Proposed Solution

Accept the real producer contracts observed after deployment:

- result envelopes with `result.conversion_metadata.pipeline_used`;
- runtime metadata fields `backend_used`, `acceleration_used`, and
  `options_fingerprint`;
- artifact manifests with `api_version`, `output_format`, and mixed
  `available` / `not_implemented` artifact entries;
- canonical transcript JSON with top-level `segments` using `segment_id`,
  language evidence, and `diarization.used_mode`.

The re-review accepts the remediation because the parser and spec now reject
canonical unavailable diarization mode as contract drift instead of treating it
as successful transcript JSON.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0342-st-21-05-transcript-intake-and-gateway-lifecycle-client.md` | Governing scope and live-proof follow-up | 5 min |
| `docs/backlog/reviews/review-pr-0342-transcript-intake-and-gateway-lifecycle-client.md` | Prior retained review and approved blockers | 5 min |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptParsers.ts` | Canonical diarization false-success rejection | 10 min |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptClient.spec.ts` | Canonical `used_mode` test proof | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/ConversionHubTranscriptMode.spec.ts` | UI edge regression proof | 5 min |
| `.artifacts/transcript-live-gateway-proof/20260611T003730Z/` | English live proof after `31bd0ce0` | 10 min |
| `.artifacts/transcript-live-gateway-proof/20260611T003748Z/` | Swedish live proof after `31bd0ce0` | 10 min |
| `/home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-20260611-003417.log` | Deployment revision and smoke evidence | 5 min |

**Total estimated time:** ~60 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Accept result envelope/runtime metadata remediation | Parser requires `audio_to_transcript_bundle_v2`, rejecting non-transcript pipelines instead of accepting generic successful results. | [x] |
| Accept artifact manifest remediation | Parser accepts available `transcript_json` and unavailable formatter artifacts only when unavailable entries carry `unavailable_code`. | [x] |
| Accept canonical top-level segment remediation | Parser accepts top-level `segments` and `segment_id`, matching the live artifacts. | [x] |
| Accept false-success rejection as complete for the reviewed producer shape | Parser now reads canonical `diarization.used_mode` and rejects `diarization_unavailable`; focused spec covers that shape. | [x] |
| Accept live product proof as final PR-0342 proof | Deployed revision `31bd0ce0b5ae0bdb9568d3d260d093fd3b5cab9c` produced English and Swedish successful UI + Gateway + `transcript_json` evidence. | [x] |

## Review Checklist

- [x] Scope is bounded to the remediation commit
  `31bd0ce0b5ae0bdb9568d3d260d093fd3b5cab9c` plus the previously reviewed
  PR-0342 producer-contract commits.
- [x] Review ignores unrelated dirty `AGENTS.md`.
- [x] Parser/type/test changes remain purpose-named and do not add story-numbered
  modules, wrappers, aliases, lint bypasses, `Any`, casts, or type ignores.
- [x] False-success rejection is complete for canonical `diarization.used_mode`.
- [x] Live proof exercises the deployed product path for English and Swedish
  fixtures after the fix.
- [x] Focused frontend test, typecheck, lint, docs validation, and diff checks
  pass.

## Review Feedback

**Reviewer:** fixed-ruthless-review-agent
**Date:** 2026-06-11
**Verdict:** approved

### Required Changes

None.

Resolved previous finding:

- `frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptParsers.ts:269`
  now reads `diarization.used_mode` and rejects
  `used_mode === "diarization_unavailable"`.
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptClient.spec.ts`
  now uses `used_mode` in valid fixtures and the false-success unavailable-mode
  rejection case.

### Decision

`approved`

The previous blocker is closed. The live product proof can be accepted for
`PR-0342`: the deployed Skriptoteket transcript lane reaches HuleEdu Gateway,
Sir Convert, STT/diarization, and canonical `transcript_json` for both reviewed
fixtures without weakening false-success rejection.

### Review Questions

1. Do the fixes correctly accept the real Sir Convert producer contracts without weakening false-success rejection?

   Yes. Result envelopes, runtime metadata, artifact manifests, top-level
   canonical segments, and canonical `diarization.used_mode` are accepted or
   rejected at the right boundary. The unavailable-mode false-success case is
   now covered against the real field name.

2. Are parser/type/test changes purpose-named and free of shims/aliases/wrappers/lint bypasses?

   Yes for the reviewed files. I found no wrappers, aliases, shims, lint
   bypasses, casts, `Any`, or type ignores in scope.

3. Does the live proof prove full product path through Skriptoteket -> HuleEdu Gateway `/sir-convert` -> Sir Convert -> STT/diarization transcript JSON for both fixtures?

   Yes. The post-fix proof uses the authenticated app, submits through
   `/sir-convert/v2/convert/jobs`, captures result, artifact manifest, and
   named `transcript_json` responses, saves full JSON artifacts, and verifies UI
   result rendering for English and Swedish fixtures.

4. Is any further blocking issue required before accepting the live product proof?

   No.

### Validation Evidence

- Confirmed local HEAD:
  `git rev-parse HEAD` -> `31bd0ce0b5ae0bdb9568d3d260d093fd3b5cab9c`.
- Inspected remediation diff:
  `git show -- frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptParsers.ts frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptClient.spec.ts`.
- Inspected parser/spec lines with `nl -ba`:
  `transcriptParsers.ts:269` reads `diarization.used_mode`;
  `transcriptClient.spec.ts:45`, `:209`, and `:350` use canonical
  `used_mode`.
- Inspected deploy log on Hemma:
  `/home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-20260611-003417.log`
  shows `Deploying commit 31bd0ce0b5ae0bdb9568d3d260d093fd3b5cab9c`,
  `skriptoteket-web` and `skriptoteket-worker` were recreated/started,
  migrations ran, and `Seating export deploy/readiness gate passed.`
- Inspected English live proof summary:
  `.artifacts/transcript-live-gateway-proof/20260611T003730Z/proof-summary.json`
  shows deployed app path `/apps/documents.conversion_hub`, Gateway
  POST/result/artifacts/`transcript_json` statuses all `200`, UI terminal state
  `succeeded`, rendered segment count `231`, detected language `en`,
  diarization `succeeded`, speakers `SPEAKER_00` and `SPEAKER_01`, and saved
  `transcript-json.full.json`.
- Inspected Swedish live proof summary:
  `.artifacts/transcript-live-gateway-proof/20260611T003748Z/proof-summary.json`
  shows Gateway POST/result/artifacts/`transcript_json` statuses all `200`, UI
  terminal state `succeeded`, rendered segment count `2`, detected language
  `sv`, diarization `succeeded`, speaker `SPEAKER_00`, and saved
  `transcript-json.full.json`.
- Inspected both full transcript JSON artifacts with `jq`, confirming
  `schema_version = "transcript_json_v1"`, non-empty text, top-level segments,
  speaker labels, detected language, and canonical
  `diarization.used_mode = "known_speaker_count"`.
- Inspected browser console artifacts for both live proofs. The only entry in
  each is the unrelated Permissions-Policy warning for
  `ambient-light-sensor`.
- Ran
  `pdm run fe-test -- src/api/sirConvertGateway/transcriptClient.spec.ts src/views/apps/ConversionHubTranscriptMode.spec.ts`.
  Result: passed, 2 files, 13 tests.
- Ran `pdm run fe-type-check`. Result: passed.
- Ran `pdm run fe-lint`. Result: passed.
- Ran `pdm run docs-validate`. Result: passed after this review update.
- Ran `git diff --check`. Result: passed after this review update.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `review-transcript-gateway-live-proof-remediation.md` | Updated retained review from `changes_requested` to `approved` after verifying the canonical `used_mode` fix, deployed proof, and focused gates. |
