---
type: review
id: REV-PR-0348
title: "Review: PR-0348 Overlay-Aware Download And Mina Filer Save"
status: approved
owners: "agents"
created: 2026-06-13
updated: 2026-06-13
reviewer: "ruthless-code-reviewer"
prs:
  - PR-0348
links:
  - ST-21-08
  - EPIC-21
  - PR-0347
---

## TL;DR

Approved. The reviewed slice keeps download and Mina filer save bound to
owner-scoped saved transcripts plus persisted replay provenance, fetches bytes
only from named producer artifacts, invalidates stale refs on overlay changes,
and fails closed when provenance or artifact integrity does not match.

## Problem Statement

PR-0348 is supposed to let teachers download or save overlay-aware transcript
exports from replay-returned artifact references without trusting browser-sent
job/artifact paths, reformatting transcript content locally, or reprocessing
source audio.

## Proposed Solution

The implementation adds:

- persisted replay-artifact provenance for saved transcripts;
- backend-authorized download and Mina filer save handlers/routes;
- artifact-integrity checks against producer metadata before delivery/save;
- product-owned filenames and Vault app-export saves;
- frontend action controls that call only Skriptoteket-owned protected routes.

That design matches the governed PR and keeps the producer-authority boundary
intact.

## Scope

Primary review target:

- `docs/backlog/prs/pr-0348-st-21-08-overlay-aware-download-and-mina-filer-save.md`

Authority and adjacent governed items reviewed:

- `docs/backlog/prs/pr-0347-st-21-08-overlay-aware-formatter-replay-client.md`
- `docs/backlog/reviews/review-pr-0347-overlay-aware-formatter-replay-client.md`
- `docs/backlog/stories/story-21-08-transcript-speaker-overlays-and-replay-formatter-exports.md`
- `docs/index.md`
- `.codex/handoff.md`

Implementation files reviewed:

- `src/skriptoteket/application/curated_apps/conversion_hub_transcript_artifact_actions.py`
- `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_artifact_actions.py`
- `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_replay.py`
- `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_saves.py`
- `src/skriptoteket/protocols/conversion_hub.py`
- `src/skriptoteket/protocols/sir_convert_a_lot_v2.py`
- `src/skriptoteket/infrastructure/repositories/conversion_hub_transcript_formatter_artifacts.py`
- `src/skriptoteket/infrastructure/db/models/conversion_hub_transcript_formatter_artifact.py`
- `migrations/versions/e1f2a3b4c5d6_add_conversion_hub_transcript_formatter_artifacts.py`
- `src/skriptoteket/web/api/v1/apps_conversion_hub_transcript_saves.py`
- `frontend/apps/skriptoteket/src/api/conversionHubTranscriptFormatterArtifactActions.ts`
- `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.vue`
- `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptFormatterReplayPanel.vue`
- `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.vue`
- `tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py`
- `tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py`
- `tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py`
- `frontend/apps/skriptoteket/src/api/conversionHubTranscriptFormatterArtifactActions.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts`

Out of scope by governed design:

- PR-0349 authenticated live proof.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0348-st-21-08-overlay-aware-download-and-mina-filer-save.md` | Scope, acceptance, proof obligations | 10 min |
| `docs/backlog/stories/story-21-08-transcript-speaker-overlays-and-replay-formatter-exports.md` | Parent story contract and non-goals | 10 min |
| Backend/frontend/test files listed in Scope | Authorization, provenance, stale-ref invalidation, Mina filer semantics, truthful proof | 60 min |

**Total estimated time:** ~1.5 hours

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep artifact actions transcript-owned and provenance-checked before every download/save | Prevents browser-supplied job ids, artifact paths, or stale overlay exports from becoming trusted. | [x] |
| Keep save/download bytes producer-owned with no local formatting or source-audio replay | Matches ST-21-08 non-goals and preserves Sir Convert as formatter authority. | [x] |
| Keep Mina filer metadata product-owned and content-safe | Avoids leaking transcript text, speaker names, media-hash labels, or provider details into saved-file labels/metadata. | [x] |

## Review Checklist

- [x] Scope is bounded to PR-0348 download/save behavior.
- [x] Docs-as-code authority exists for ST-21-08 and PR-0348.
- [x] Download/save actions fail closed when persisted replay refs or replay job provenance do not match.
- [x] No browser-local formatter fallback, canonical-label fallback, or source-audio replay was found in the reviewed slice.
- [x] Focused backend, frontend, and migration proof was rerun.
- [x] PR-0349 live proof remained out of scope.

## Verification

Commands run:

```bash
pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py
pdm run fe-test -- --run frontend/apps/skriptoteket/src/api/conversionHubTranscriptFormatterArtifactActions.spec.ts frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts
pdm run test 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[e1f2a3b4c5d6]' --override-ini addopts='' -m docker
```

Results:

- Focused backend proof passed: 18 tests covering replay provenance reuse,
  fail-closed download/save authorization, and route delegation.
- Focused frontend proof passed: 2 files / 10 tests covering protected API
  usage and user-visible action states.
- Docker migration idempotency for `e1f2a3b4c5d6` passed.
- No production code changes were made by this reviewer.

## Review Feedback

**Reviewer:** ruthless-code-reviewer
**Date:** 2026-06-13
**Verdict:** approved

### Required Changes

None.

### Findings

No findings in the reviewed PR-0348 scope.

### Suggestions (Optional)

- Add a future integration-repository test for
  `PostgreSQLConversionHubTranscriptFormatterArtifactRepository` if later slices
  need broader persistence regression coverage beyond the current handler and
  migration proof.

### Decision Approvals

- [x] Owner-scoped replay artifact authorization
- [x] Producer-only bytes for download/save
- [x] Content-safe Mina filer metadata

## Residual Risks

- PR-0349 authenticated live proof was not rerun here by design, so this review
  does not add end-to-end browser proof for the final protected path.
- The reviewed slice still depends on the PR-0347 replay-complete boundary for
  initial artifact-ref persistence; this pass confirmed PR-0348 uses only that
  persisted provenance and does not widen browser trust during download/save.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0348` | Created the retained review record and marked PR-0348 approved. |
| 2 | Implementation | No production code changes were made by this reviewer. |
