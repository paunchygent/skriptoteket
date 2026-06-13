---
type: review
id: REV-PR-0344
title: "Review: PR-0344 Transcript Lifecycle Observability and Abort Feedback"
status: approved
owners: "agents"
created: 2026-06-13
updated: 2026-06-13
reviewer: "ruthless-code-reviewer"
prs:
  - PR-0344
links:
  - ST-21-08
  - EPIC-21
  - PR-0342
  - PR-0343
---

## TL;DR

Approved on re-review. The fix resolves both prior blockers: pre-id cancel now
stays pending until a real Gateway cancel can be issued, and present malformed
terminal `progress` payloads now fail closed instead of being normalized.

## Problem Statement

PR-0344 is supposed to make transcript lifecycle progress and abort outcomes
truthful, strict, and teacher-facing. This re-review checks that the two prior
blocking findings are actually closed and that the fix did not regress the
runtime/parser boundary.

## Proposed Solution

The fix keeps the existing typed progress/abort design, but tightens two
critical behaviors:

- pre-id cancel is queued as a pending intent and only becomes accepted after a
  real Gateway cancel response returns `canceled` / `cancelled`;
- a present non-object `progress` field now throws contract drift for terminal
  transcript jobs instead of being treated as missing progress.

## Scope

Primary review target:

- `docs/backlog/prs/pr-0344-st-21-08-transcript-lifecycle-observability-and-abort-feedback.md`

Authority and parent scope reviewed:

- `docs/backlog/stories/story-21-08-transcript-speaker-overlays-and-replay-formatter-exports.md`
- `docs/index.md`
- `.codex/handoff.md`

Implementation files reviewed:

- `frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptTypes.ts`
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptParsers.ts`
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptClient.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/useTranscriptGatewayRuntime.ts`
- `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/useTranscriptGatewayRuntime.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.vue`
- `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkflowRailShell.vue`
- `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.vue`
- `frontend/apps/skriptoteket/src/views/apps/ConversionHubTranscriptMode.spec.ts`

Out-of-scope implementation intentionally not reviewed for approval here:

- Formatter authority sync, replay/export actions, speaker naming overlays, and
  Mina filer persistence beyond the already-governed PR-0343 save boundary.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0344-st-21-08-transcript-lifecycle-observability-and-abort-feedback.md` | PR scope, acceptance, verification | 10 min |
| `docs/backlog/stories/story-21-08-transcript-speaker-overlays-and-replay-formatter-exports.md` | Parent story contract and non-goals | 10 min |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptTypes.ts` | Strict progress types and phase enums | 8 min |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptParsers.ts` | Fail-closed parsing and contract drift handling | 15 min |
| `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/useTranscriptGatewayRuntime.ts` | Polling, cancel state transitions, race safety | 15 min |
| `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.vue` | Teacher-facing progress and abort copy | 10 min |
| Transcript Vitest specs listed in Scope | Behavioral proof quality | 15 min |

**Total estimated time:** ~1.5 hours

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Replace `audioProgress` consumption with one typed `progress` snapshot | Matches the governed PR scope and removes loose progress access from the UI. | [x] |
| Keep raw upstream phase names out of teacher-facing UI copy | Prevents internal stage leakage and matches the copy rules. | [x] |
| Accept cancel only after Gateway returns a canceled job | This is the core abort truthfulness contract for PR-0344. | [x] |
| Fail closed on malformed Gateway progress | The PR explicitly claims a strict progress contract with no loose typing. | [x] |

## Review Checklist

- [x] Scope is bounded to PR-0344 progress and abort feedback.
- [x] No formatter/export/speaker-overlay implementation is approved here.
- [x] UI copy stays Swedish and avoids raw upstream/internal stage names.
- [x] Focused parser, runtime, and workspace tests exist.
- [x] Cancel behavior is truthful when cancel is pressed before job ids exist.
- [x] Parser fails closed for malformed terminal `progress` payloads.

## Verification

Commands run:

```bash
git status --short
git diff --name-only
git diff --stat
pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/useTranscriptGatewayRuntime.spec.ts frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptClient.spec.ts
git diff --check
pdm run docs-validate
pdm run handoff-validate
```

Results:

- Working tree review scope had broader unrelated transcript/save changes, so
  this review stayed bounded to the implementer-declared PR-0344 files and
  governing docs.
- Focused frontend Vitest passed: 2 files, 17 tests.
- `git diff --check` passed.
- `pdm run docs-validate` passed.
- `pdm run handoff-validate` passed.
- No reviewer production-code edits were made.

## Review Feedback

**Reviewer:** ruthless-code-reviewer
**Date:** 2026-06-13
**Verdict:** approved

### Required Changes

None.

### Findings

No blocking findings in the re-review scope.

Resolved prior findings:

- Pre-id cancel no longer marks the runtime canceled/accepted without a real
  Gateway cancel response. `cancelTranscript()` now leaves the runtime in a
  pending state until submitted ids exist, and `submitAndPoll()` immediately
  issues the queued cancel once submission resolves.
- Present malformed terminal `progress` no longer falls through to
  `emptyProgress(...)`. `progressRecord()` now throws when `progress` exists but
  is not an object, and the client spec proves terminal malformed progress is
  rejected as contract drift.

### Suggestions (Optional)

- After the blocking fixes land, add one end-to-end transcript mode spec that
  covers visible pending cancel copy plus post-cancel terminal copy through the
  host/view boundary, not only the composable and workspace in isolation.

### Decision Approvals

- [x] Typed transcript progress snapshot
- [x] Teacher-facing Swedish progress copy
- [x] Abort acceptance only after real Gateway cancel
- [x] Fail-closed malformed terminal progress

## Residual Risks

- I did not rerun authenticated browser-session proof. This re-review is scoped
  to the runtime/parser fixes and their focused Vitest evidence, not a new live
  shared-auth transcript session.
- The queued pre-id cancel failure path is not covered by a dedicated new spec,
  but it reuses the same `requestGatewayCancel()` helper exercised by the
  existing cancel-failure polling test, and the production control flow now
  falls back into normal polling when cancel is rejected or fails.
- The request named a non-existent story path. I reviewed the canonical
  `ST-21-08` story file that exists in the repo.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0344` | Updated the retained review record after fix verification and marked the PR approved on re-review. |
| 2 | Implementation | No production code changes were made by this reviewer. |
