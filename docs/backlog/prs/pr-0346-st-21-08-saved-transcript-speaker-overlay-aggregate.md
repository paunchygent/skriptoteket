---
type: pr
id: PR-0346
title: "ST-21-08 Saved transcript speaker overlay aggregate"
status: done
owners: "agents"
created: 2026-06-13
updated: 2026-06-13
stories:
  - "ST-21-08"
tags:
  - backend
  - frontend
  - conversion-hub
  - transcript
  - speaker-overlay
dependencies:
  - "PR-0343"
acceptance_criteria:
  - "Given a saved transcript has canonical speaker labels, when a teacher names speakers, then Skriptoteket persists owner-scoped overlay rows keyed by saved transcript id and canonical speaker label."
  - "Given the canonical transcript JSON is read back, when speaker names are edited, then the JSON payload remains byte-for-byte product truth and speaker names live only in overlay state."
  - "Given invalid overlay input is submitted, when labels are unknown, names are empty, duplicate, too long, or contain control characters, then the API rejects the request with teacher-safe errors."
  - "Given a saved transcript is opened later, when overlays exist, then the UI renders editable display names mapped to canonical labels without creating export artifacts."
---

# PR-0346: ST-21-08 Saved Transcript Speaker Overlay Aggregate

## Problem

Teachers need to replace labels such as `speaker_00` with real names, but that
product intent must not rewrite the canonical producer transcript.

## Goal

Persist speaker display-name overlays as typed Skriptoteket-owned state over a
saved transcript.

## Non-goals

- No formatter replay request.
- No download or Mina filer save action.
- No mutation, repair, or migration of canonical `transcript_json`.

## Implementation Plan

Implemented on 2026-06-13.

- Added a saved-transcript speaker overlay aggregate and PostgreSQL table keyed
  by owner, saved transcript id, and canonical speaker label.
- Added authenticated read/replace API routes under the existing Conversion Hub
  transcript ownership boundary.
- Added frontend overlay state and speaker-name edit affordances after a
  transcript has been durably saved.
- Validated overlay labels against the saved canonical transcript speaker
  inventory and rejected unknown labels, duplicate labels, empty names,
  duplicate names, overlong names, and control characters.
- Preserved canonical `transcript_json` as the product truth; overlays are
  separate rows and do not create formatter artifacts.

## Test Plan

- `pdm run pytest tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_saves.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py tests/integration/infrastructure/repositories/test_conversion_hub_saved_transcript_repository.py`
- `pdm run pytest 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[d7c9a1e4b6f2]' --override-ini addopts='' -s -v --durations=10 --log-cli-level=INFO --import-mode=importlib`
- `pdm run fe-test -- src/api/conversionHubTranscriptSaves.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts src/views/apps/ConversionHubTranscriptMode.spec.ts`

## Rollback Plan

Hide speaker-name editing and keep saved transcripts with canonical labels
only. Preserve the saved transcript aggregate.
