---
type: review
id: REV-PR-0343
title: "Review: PR-0343 Durable Transcript JSON Save Boundary"
status: approved
owners: "agents"
created: 2026-06-12
updated: 2026-06-13
reviewer: "ruthless-code-reviewer"
prs:
  - PR-0343
links:
  - ST-21-07
  - EPIC-21
---

## TL;DR

Approved. The current worktree implements PR-0343 as an authenticated,
owner-scoped durable `transcript_json` save/readback boundary with PostgreSQL
JSONB storage, local Conversion Hub job provenance, repository-level owner
readback, frontend raw JSON preservation, and no formatter implementation.

## Problem Statement

Sir Convert transcript artifacts are operational and short-lived. PR-0343 must
let a teacher explicitly save canonical transcript JSON inside Skriptoteket so
future transcript management and formatter/export work can use durable product
truth without relying on Sir Convert artifact TTLs, local re-transcription, or
unaccepted formatter authority.

## Proposed Solution

The implementation adds a typed `conversion_hub_saved_transcripts` aggregate,
authenticated transcript job registration/save/readback routes, Dishka-wired
application handlers, a PostgreSQL repository and migration, generated OpenAPI
types, and a frontend save path that preserves canonical raw `transcript_json`
when the Gateway parser supplies it.

Formatter outputs remain absent. The docs keep TXT, Markdown, VTT, and SRT work
outside PR-0343. Post-review status note, 2026-06-13: Sir Convert Story 54 /
Task 358 is now accepted for product-neutral formatter artifacts. Overlay-aware
speaker-name exports are governed by `ST-21-08`, Sir Convert Story 56, and
HuleEdu `ST-01-09`.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0343-st-21-07-durable-transcript-json-save-boundary.md` | PR scope, acceptance, verification | 10 min |
| `docs/backlog/stories/story-21-07-durable-transcript-saves-and-json-first-downstream-formatting.md` | Parent story scope and formatter block | 8 min |
| `docs/backlog/epics/epic-21-curated-app-conversion-hub.md` | Epic status and transcript lane constraints | 5 min |
| `src/skriptoteket/application/curated_apps/conversion_hub_transcript_saves.py` | Typed save/readback contracts | 8 min |
| `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_saves.py` | Owner checks, provenance validation, UoW boundary | 15 min |
| `src/skriptoteket/infrastructure/repositories/conversion_hub_saved_transcripts.py` | Owner-scoped repository queries, no commits | 10 min |
| `src/skriptoteket/infrastructure/db/models/conversion_hub_saved_transcript.py` | DB model shape and indexes | 8 min |
| `migrations/versions/c4e8f0a2d6b9_add_conversion_hub_saved_transcripts.py` | Migration shape and rollback | 10 min |
| `src/skriptoteket/web/api/v1/apps_conversion_hub_transcript_saves.py` | Router thinness, auth, no postponed annotations | 8 min |
| `src/skriptoteket/di/curated_apps.py` | Dishka provider registration | 5 min |
| `frontend/apps/skriptoteket/src/api/conversionHubTranscriptSaves.ts` | Save request builder and raw JSON preservation | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/*` | Unsaved/saved copy and save affordance | 10 min |
| PR-0343 tests under `tests/unit`, `tests/integration`, and frontend specs | Behavioral proof quality | 20 min |

**Total estimated time:** ~2 hours

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Use a typed saved-transcript aggregate instead of Vault/file fallback | The saved JSON is first-class product transcript truth, not a formatter artifact or generic file workaround. | [x] |
| Persist owner, local job, upstream job, artifact key, schema, language, diarization, speaker, generated, and correlation provenance | Meets ST-21-07 and PR-0343 durability and traceability requirements without preserving source audio. | [x] |
| Read saved transcripts through `get_by_owner_and_id` at the repository query boundary | Prevents load-by-id then app-layer filtering for transcript JSON readback. | [x] |
| Keep TXT, Markdown, VTT, and SRT formatters out of PR-0343 | PR-0343 intentionally shipped no formatter/export behavior. The then-current Story 54 blocker is now superseded by accepted Sir Convert Task 358; ST-21-08 owns the follow-up. | [x] |
| Preserve raw frontend canonical JSON when available | Prevents lossy client re-normalization before durable save. | [x] |

## Review Checklist

- [x] Scope is bounded to durable transcript JSON save/readback.
- [x] Saved transcript storage is typed, owner-scoped, and provenance-rich.
- [x] Readback uses an owner+transcript-id repository query.
- [x] UI copy distinguishes unsaved temporary transcripts from saved records.
- [x] No TXT/Markdown/VTT/SRT formatter implementation was added.
- [x] Save/readback path adds no transcript-text or provider/model logging.
- [x] Migration has repository roundtrip and docker idempotency coverage.
- [x] Frontend save path preserves raw canonical transcript JSON when present.
- [x] Router module has no `from __future__ import annotations`.
- [x] Repositories do not commit or rollback; application handlers use UoW.
- [x] Dishka registrations are present.
- [x] New production modules have domain-purpose docstrings.
- [x] Docs-as-code status is coherent for PR, story, epic, and handoff.

## Review Feedback

**Reviewer:** ruthless-code-reviewer
**Date:** 2026-06-12
**Verdict:** approved

### Required Changes

None.

### Findings

No blocking findings.

Evidence inspected:

- `PostgreSQLConversionHubSavedTranscriptRepository.get_by_owner_and_id` filters by both
  `id` and `owner_user_id` in the SQL query before returning transcript JSON.
- `SaveConversionHubTranscriptHandler` validates artifact key, schema version,
  transcript text, segments, speaker labels, timestamps, owner-owned local job,
  upstream job id, audio source format, transcript bundle output, and succeeded
  job status before creating a durable record.
- The migration creates `conversion_hub_saved_transcripts` with owner/job FKs,
  JSONB transcript storage, owner/upstream uniqueness, owner-created and job
  indexes, and widens `conversion_hub_jobs.output_format` for
  `transcript_bundle`.
- `apps_conversion_hub_transcript_saves.py` is a thin authenticated app router,
  delegates to handlers, uses `FromDishka`, and has no postponed annotations.
- `ConversionHubTranscriptHost.vue` registers the local job after Gateway
  success and saves through the new endpoint; `TranscriptWorkspaceShell.vue`
  renders unsaved as temporary/not saved and saved as saved.
- `parseTranscriptJson` now carries `rawJson`, and
  `buildSaveTranscriptRequest` uses that raw object when available.
- Targeted searches found formatter terms only in docs/docstrings describing
  the then-current block, not active formatter code. Targeted searches found no logging
  calls in the new save/readback path.

Commands run:

```bash
git status --short
git diff --name-status
git diff --stat
git diff --check
pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_saves.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py tests/integration/infrastructure/repositories/test_conversion_hub_saved_transcript_repository.py
pdm run test 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[c4e8f0a2d6b9]' --override-ini addopts='' -m docker
pdm run fe-test -- src/views/apps/ConversionHubTranscriptMode.spec.ts src/api/conversionHubTranscriptSaves.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts src/api/sirConvertGateway/transcriptClient.spec.ts
pdm run lint
pdm run typecheck
pdm run fe-type-check
pdm run fe-lint
pdm run fe-build
```

Results:

- `git diff --check` passed.
- Backend/API/repository focused tests passed: 8 passed.
- Migration docker idempotency test for `c4e8f0a2d6b9` passed: 1 passed.
- Focused frontend Vitest passed: 18 passed.
- `pdm run lint` passed.
- `pdm run typecheck` passed.
- `pdm run fe-type-check` passed.
- `pdm run fe-lint` passed.
- `pdm run fe-build` passed with existing Vite chunk-size/dynamic-import
  warnings only.

### Suggestions (Optional)

- Keep the next saved-transcript management slice on the same repository-owned
  owner-scoping pattern for list/open/delete/export. Do not introduce list
  labels that contain transcript text, source filenames, media hashes, or
  provider/model details.
- Consider replacing test-local `Any`/`cast` JSON assertions with small typed
  helpers in a later cleanup if this test surface grows. This is not blocking
  because the production boundary uses explicit Pydantic/JSON types and the
  repository/API behavior is covered.
- This review did not rerun authenticated browser proof. The PR already records
  that the prior local browser attempt was blocked by in-app browser transport,
  and the saved UI path is covered by focused component/API tests plus build.

### Decision Approvals

- [x] Durable saved transcript aggregate
- [x] Owner-scoped repository readback
- [x] Raw canonical frontend JSON preservation
- [x] Formatter work remains blocked
- [x] Logs/docs avoid operational transcript/provider leakage

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0343` | Created this retained independent review record with approved verdict and reviewer-side verification evidence. |
| 2 | Implementation | No production code changes were made by this reviewer. |
