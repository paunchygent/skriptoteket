---
type: review
id: REV-PR-0347
title: "Review: PR-0347 Overlay-Aware Formatter Replay Client"
status: approved
owners: "agents"
created: 2026-06-13
updated: 2026-06-13
reviewer: "ruthless-code-reviewer"
prs:
  - PR-0347
links:
  - ST-21-08
  - EPIC-21
  - PR-0345
  - PR-0346
---

## TL;DR

Approved on pass 2. The remediation closes the prior replay-provenance blocker:
existing replay-job reuse now validates the current saved transcript's gateway
filename before returning the local job, and the new regression proves a
same-owner replay job id cannot be rebound to a different saved transcript.

## Problem Statement

PR-0347 is supposed to turn one saved canonical transcript plus persisted
speaker overlays into producer-owned TXT/MD/VTT/SRT artifact references without
local formatting fallback, loose parsing, or invented provenance. This review
checks the replay request/response boundary, owner scope, future authorization
readiness, and the truthfulness of the focused tests.

## Proposed Solution

The implementation adds:

- backend replay prepare/complete handlers over saved transcripts and speaker
  overlays;
- transcript-saves API routes for replay prepare/complete;
- frontend Gateway replay client/parsers plus workspace replay state;
- generated API types and docs updates for the new replay contract.

That overall shape is consistent with ST-21-08, and the pass-2 remediation now
makes replay-job reuse transcript-specific enough for the governed PR-0348
authorization follow-up.

## Scope

Primary review target:

- `docs/backlog/prs/pr-0347-st-21-08-overlay-aware-formatter-replay-client.md`

Authority and parent scope reviewed:

- `docs/backlog/stories/story-21-08-transcript-speaker-overlays-and-replay-formatter-exports.md`
- `docs/backlog/prs/pr-0345-st-21-08-formatter-authority-sync-and-artifact-selection.md`
- `docs/backlog/prs/pr-0346-st-21-08-saved-transcript-speaker-overlay-aggregate.md`
- `docs/index.md`
- `.codex/handoff.md`

Implementation files reviewed:

- `src/skriptoteket/application/curated_apps/conversion_hub_transcript_replay.py`
- `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_replay.py`
- `src/skriptoteket/web/api/v1/apps_conversion_hub_transcript_saves.py`
- `src/skriptoteket/protocols/conversion_hub.py`
- `src/skriptoteket/di/curated_apps.py`
- `frontend/apps/skriptoteket/src/api/conversionHubTranscriptFormatterReplay.ts`
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptReplayClient.ts`
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptReplayParsers.ts`
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptTypes.ts`
- `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.vue`
- `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.vue`
- `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptFormatterReplayPanel.vue`
- `frontend/apps/skriptoteket/src/api/conversionHubTranscriptFormatterReplay.spec.ts`
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptReplayClient.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts`
- `tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py`
- `tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py`
- `tests/unit/scripts/test_conversion_hub_transcript_docs_guard.py`

Out of scope by governed design:

- PR-0348 download and Mina filer actions.
- PR-0349 authenticated live proof.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0347-st-21-08-overlay-aware-formatter-replay-client.md` | PR scope, acceptance, verification | 10 min |
| `docs/backlog/stories/story-21-08-transcript-speaker-overlays-and-replay-formatter-exports.md` | Parent story contract and non-goals | 10 min |
| `docs/backlog/prs/pr-0345-st-21-08-formatter-authority-sync-and-artifact-selection.md` | Formatter authority dependency | 8 min |
| `docs/backlog/prs/pr-0346-st-21-08-saved-transcript-speaker-overlay-aggregate.md` | Overlay persistence dependency | 8 min |
| Backend/frontend/test files listed in Scope | Replay provenance, parser strictness, UI truthfulness | 45 min |

**Total estimated time:** ~1.5 hours

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep replay authority producer-owned and fail closed on malformed/non-requested artifacts | Matches ST-21-08 and avoids local formatter fallbacks. | [x] |
| Keep PR-0348 download/Mina filer actions out of this slice | Matches the governed PR split. | [x] |
| Persist replay provenance in the local `ConversionHubJob` ledger | Acceptable because replay-job reuse now validates the current transcript-derived gateway filename before reusing local provenance. | [x] |

## Review Checklist

- [x] Scope is bounded to PR-0347 replay request/parsing/provenance behavior.
- [x] Docs-as-code authority exists for ST-21-08 and PR-0347.
- [x] No browser-local formatter fallback or canonical-label fallback was found
  in the reviewed replay path.
- [x] Focused backend/frontend/docs proof exists and was rerun.
- [x] PR-0348 and PR-0349 work stayed out of scope.
- [x] Replay provenance is safe for later authorization use.

## Verification

Commands run:

```bash
pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py
pdm run docs-validate
git diff --check
```

Results:

- Backend focused tests passed on pass 2: 12 tests, including
  `test_complete_replay_rejects_existing_replay_job_for_different_transcript`.
- `pdm run docs-validate` passed after updating this retained review artifact.
- `git diff --check` passed after updating this retained review artifact.
- I did not rerun the frontend replay lane in pass 2 because the remediation is
  backend-only and the original focused frontend proof remains sufficient for
  the unchanged browser surface.
- No production code changes were made by this reviewer.

## Review Feedback

**Reviewer:** ruthless-code-reviewer
**Date:** 2026-06-13
**Verdict:** approved

### Required Changes

None.

### Findings

No blocking findings remain in the pass-2 scope.

Resolved prior finding:

- `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_replay.py:294`
  now passes the current transcript-derived gateway filename into
  `_validate_existing_replay_job(...)`, and
  [conversion_hub_transcript_formatter_replay.py](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_replay.py:321)
  rejects reuse when `job.input_filename` does not match the current saved
  transcript.
- [test_conversion_hub_transcript_formatter_replay.py](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py:335)
  now proves the original failure mode directly: the same owner and
  `sir_convert_job_id` cannot reuse replay provenance across two different
  saved transcripts and now fail closed with `VALIDATION_ERROR`.

### Suggestions (Optional)

- A future hardening pass could add one focused idempotent-reuse test for the
  same transcript/job pair, to pin the intended happy-path reuse contract
  alongside the cross-transcript rejection case.

### Decision Approvals

- [x] Producer-owned replay artifact authority
- [x] No PR-0348/PR-0349 scope bleed
- [x] Transcript-safe replay provenance reuse

## Residual Risks

- The reviewed slice still trusts the browser to relay Gateway replay result and
  artifact manifest payloads, but the local replay ledger now rejects the
  cross-transcript provenance reuse hole that previously made that trust unsafe
  for the next slice.
- I did not independently rerun lint/typecheck in pass 2; the backend-focused
  regression lane plus the unchanged surface elsewhere were sufficient for this
  review pass, and the implementer reported those broader gates green.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0347` | Updated the retained review record for pass 2 and marked the PR approved. |
| 2 | Implementation | No production code changes were made by this reviewer. |
