---
type: pr
id: PR-0348
title: "ST-21-08 Overlay-aware download and Mina filer save"
status: done
owners: "agents"
created: 2026-06-13
updated: 2026-06-13
stories:
  - "ST-21-08"
tags:
  - frontend
  - backend
  - user-files
  - transcript
  - formatter
  - replay
dependencies:
  - "PR-0347"
acceptance_criteria:
  - "Given replay returned an overlay-aware formatter artifact reference, when the teacher chooses download, then Skriptoteket downloads through the authorized Gateway/artifact action boundary."
  - "Given replay returned an overlay-aware formatter artifact reference, when the teacher chooses save to Mina filer, then Skriptoteket saves the producer artifact with product-owned filename and metadata without reformatting content."
  - "Given no valid replay artifact reference exists, when download or save is requested, then the action is unavailable or fails closed without falling back to canonical-label artifacts."
  - "Given saved files are listed or logged, when metadata is emitted, then transcript text, utterances, speaker names, source content, media hashes as labels, and provider/model details are excluded."
---

# PR-0348: ST-21-08 Overlay-Aware Download And Mina Filer Save

## Problem

Saved transcript exports are not useful until teachers can download them or
save them to Mina filer from producer-authoritative artifacts.

## Goal

Wire overlay-aware formatter artifact references into download and Mina filer
save actions.

## Non-goals

- No replay request construction changes beyond consuming `PR-0347` output.
- No local formatting.
- No source-audio archive.
- No public/no-login save path.

## Implementation Plan

- Added persisted replay artifact provenance for `transcript_txt`,
  `transcript_md`, `transcript_vtt`, and `transcript_srt`, populated by the
  PR-0347 replay completion handler and scoped to owner plus saved transcript.
- Added backend download and Mina filer save handlers/routes that authorize
  against persisted replay provenance, validate the local replay job, fetch the
  named producer artifact through the Gateway client boundary, and fail closed
  when refs/provenance are missing or mismatched.
- Added product-owned filenames (`transkript-{savedTranscript}.txt/md/vtt/srt`)
  and Vault `APP_EXPORT` save metadata without transcript text, utterances,
  speaker display names, source content, media hashes as labels, or provider
  details.
- Invalidated persisted formatter artifact refs when speaker overlays change so
  downloads/saves require a fresh replay after overlay edits.
- Added compact frontend artifact action controls with availability,
  running/success/failure states, protected API clients, and no direct browser
  Sir Convert artifact path.

## Test Plan

- Red evidence:
  - `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py` failed on missing artifact-action modules/routes.
  - `pdm run fe-test -- --run src/api/conversionHubTranscriptFormatterArtifactActions.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts` failed on the missing protected API helper and missing action controls/states.
- Green evidence:
  - `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_saves.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py` passed with 25 tests.
  - `pdm run fe-test -- --run src/api/conversionHubTranscriptFormatterArtifactActions.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts` passed with 10 tests.
  - `pdm run test 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[e1f2a3b4c5d6]' --override-ini addopts='' -m docker` passed.
  - `pdm run fe-gen-api-types`, `pdm run lint`, `pdm run typecheck`,
    `pdm run fe-type-check`, `pdm run fe-lint`, and `pdm run fe-build` passed.
- Not run by design: `PR-0349` live authenticated proof.

## Rollback Plan

Hide export action buttons and keep replay results internal until the action
boundary is repaired.
