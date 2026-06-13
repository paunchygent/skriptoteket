---
type: pr
id: PR-0343
title: "ST-21-07 Durable transcript JSON save boundary"
status: done
owners: "agents"
created: 2026-06-10
updated: 2026-06-13
stories:
  - "ST-21-07"
tags:
  - backend
  - frontend
  - conversion-hub
  - transcript
  - user-files
  - provenance
dependencies:
  - "PR-0342"
  - "Sir Convert Task 356"
acceptance_criteria:
  - "Given a valid `transcript_json` artifact is available through Gateway, when the teacher saves it, then Skriptoteket persists an owner-scoped transcript record or user file with schema, source/job/artifact provenance, language evidence, diarization mode, speaker controls, generation timestamp, and correlation metadata."
  - "Given Sir Convert's operational artifact retention expires, when a saved transcript is opened later, then Skriptoteket serves the durable saved JSON record rather than relying on the upstream job artifact."
  - "Given an unsaved transcript job exists, when the UI describes availability, then it does not imply durable storage after Sir Convert TTL."
  - "Given transcript content may contain sensitive user content, when the backend logs, lists, or reports saves, then it excludes transcript text, utterances, source filenames as labels, media hashes as labels, and provider/model details."
  - "Given TXT, Markdown, VTT, or SRT output is requested, when this PR closes, then this PR still does not expose formatter/export actions; follow-up formatter work must use saved canonical JSON and accepted Sir Convert formatter or replay artifacts."
---

# PR-0343: ST-21-07 Durable Transcript JSON Save Boundary

## Problem

Sir Convert keeps recordings, normalized audio, and transcript artifacts under
short operational retention. Skriptoteket needs a durable, owner-scoped product
save boundary for canonical transcript JSON after teachers choose to save a
result.

## Goal

Persist validated `transcript_json` from `PR-0342` as Skriptoteket-owned
teacher content with provenance, access control, retention, and deletion
behavior that does not depend on Sir Convert's short artifact TTL.

## Non-goals

- No durable source-audio archive.
- No local STT, diarization, alignment, transcript repair, or re-transcription.
- No TXT, Markdown, VTT, or SRT formatter implementation in this PR.
- No public/no-login durable transcript storage.

## Implementation Summary

Done on 2026-06-12. The durable storage shape is a typed
`conversion_hub_saved_transcripts` aggregate backed by the existing
owner-scoped Conversion Hub job ledger, not an ordinary Vault file and not a
formatter output.

The slice adds:

- backend save/readback contracts for validated canonical `transcript_json`,
  including owner-scoped saved-transcript readback at the repository query
  boundary;
- local transcript-job registration for Gateway jobs so saves can be tied to a
  Skriptoteket-owned `conversion_hub_jobs` row;
- PostgreSQL persistence with owner/upstream uniqueness, job/user foreign keys,
  JSONB transcript storage, provenance fields, and `output_format` widening for
  `transcript_bundle`;
- authenticated app routes under
  `/api/v1/apps/documents.conversion_hub/transcripts`;
- frontend save client/request builder that preserves raw canonical JSON when
  available;
- transcript workspace save affordance that distinguishes temporary transcript
  results from saved records.

Formatter/export work remains deliberately absent in this PR. Sir Convert
Story 54 / Task 358 is now accepted; `ST-21-08` owns the follow-up path for
speaker overlays, overlay-aware replay, downloads, and Mina filer saves.

## Planning Notes

`PR-0342` now has accepted live product proof through Skriptoteket, HuleEdu
Gateway, Sir Convert, STT/diarization, and canonical `transcript_json` for
English and Swedish fixtures. `PR-0343` should therefore use the live-proven
Gateway artifact as the upstream source authority and must not re-open a direct
Sir Convert, public/no-login, local STT, or formatter path.

## Post-0343 Scaffolding Direction

After this PR is done, scaffold follow-up work only from the persisted JSON
truth established here:

- Saved transcript management: list/open/delete/export saved transcript records
  or files, with owner scoping, retention copy, and no source-audio archive.
- Formatter/export availability: Sir Convert Story 54 / Task 358 is accepted
  for product-neutral artifacts. `ST-21-08` scaffolds overlay-aware exports
  from saved canonical JSON plus speaker overlay intent through Sir Convert
  Story 56 and HuleEdu `ST-01-09`.
- Downstream reuse: any later lesson-material, subtitle, or copy-workflow slice
  must consume saved transcript JSON as product truth instead of resubmitting
  audio or inventing a parallel transcript model.
- Search/indexing and sharing: defer until saved-record access, deletion,
  content-safety, and indexing behavior are explicitly accepted.

## Verification

- Retained review:
  `docs/backlog/reviews/review-pr-0343-durable-transcript-json-save-boundary.md`
  is approved with no blocking findings.
- Red check:
  `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_saves.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py`
  failed before implementation with missing transcript-save modules.
- Backend/API/repository:
  `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_saves.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py tests/integration/infrastructure/repositories/test_conversion_hub_saved_transcript_repository.py`
  passed, 8 tests. A later hardening pass first made owner+id readback a red
  requirement, then switched repository readback to an owner-scoped query and
  reran this same command green.
- Migration idempotency:
  `pdm run test 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[c4e8f0a2d6b9]' --override-ini addopts='' -m docker`
  passed.
- Frontend:
  `pdm run fe-test -- src/views/apps/ConversionHubTranscriptMode.spec.ts src/api/conversionHubTranscriptSaves.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts src/api/sirConvertGateway/transcriptClient.spec.ts`
  passed, 18 tests. The save-client spec also pins that raw canonical
  `transcript_json` is preserved when available.
- Static/build gates:
  `pdm run lint`, `pdm run typecheck`, `pdm run fe-type-check`,
  `pdm run fe-lint`, `pdm run fe-build`, and `pdm run fe-gen-api-types`
  passed.
- Local live UI attempt: `pdm run fe-dev` started Vite at
  `http://localhost:5173/`. The in-app browser transport closed before
  navigation, and the SPA package does not install a Playwright CLI binary, so
  this turn did not produce an authenticated browser screenshot of the save
  flow. The save UI is covered by component/host Vitest and production build.

## Rollback Plan

Hide save/readback affordances and leave `PR-0342` as transient transcript job
retrieval only. Do not preserve transcript text in logs or temporary local
fallback storage.
