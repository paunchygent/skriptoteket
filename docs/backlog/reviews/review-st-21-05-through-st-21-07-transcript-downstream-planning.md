---
type: review
id: REV-ST-21-05
title: "Review: Transcript downstream planning for ST-21-05 through ST-21-07"
status: approved
owners: "agents"
created: 2026-06-09
updated: 2026-06-09
reviewer: "fixed-reviewer"
stories:
  - ST-21-05
  - ST-21-06
  - ST-21-07
links:
  - EPIC-21
---

## TL;DR

This retained review asks a fixed reviewer to approve or request changes for
the downstream transcript planning lane under EPIC-21. The reviewed surface is
docs-only: authenticated transcript intake, Gateway-backed job lifecycle, and
Skriptoteket-owned durable transcript saves over canonical JSON.

## Problem Statement

Sir Convert Story 55 accepted only cross-repo planning alignment for speech-to-
text delivery. Skriptoteket needs its own retained review before the new STT
stories can be treated as committed downstream execution authority.

## Proposed Solution

Keep ST-21-05 through ST-21-07 as ready planning stories that preserve the
Gateway-only access path, diarization control vocabulary, upstream block
conditions, durable-retention ownership, and JSON-first downstream formatting
sequence. No runtime browser route, direct Sir Convert access, local STT engine,
diarization fallback, or formatter implementation is approved by this review.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/epics/epic-21-curated-app-conversion-hub.md` | Parent scope and transcript-lane summary | 8 min |
| `docs/backlog/stories/story-21-05-conversion-hub-transcript-intake-and-diarization-controls.md` | Intake, diarization controls, and access boundary | 10 min |
| `docs/backlog/stories/story-21-06-transcript-job-lifecycle-through-huleedu-gateway.md` | Gateway lifecycle and upstream blockers | 10 min |
| `docs/backlog/stories/story-21-07-durable-transcript-saves-and-json-first-downstream-formatting.md` | Durable save ownership and formatter sequencing | 10 min |
| `tests/unit/scripts/test_conversion_hub_transcript_docs_guard.py` | Docs guard coverage for retained constraints | 5 min |

**Total estimated time:** ~43 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Transcript access stays Gateway-only through `/sir-convert/v2/convert` | Preserves the HuleEdu authenticated product edge and avoids direct browser/sidecar authority | [x] |
| ST-21-05 owns intake and diarization controls only | Keeps audio/video upload and speaker controls separate from job execution and durable saves | [x] |
| ST-21-06 remains blocked on Sir Convert Story 53 and HuleEdu ST-01-08 | Runtime job lifecycle needs the accepted route and Gateway edge before implementation | [x] |
| ST-21-07 remains blocked on canonical JSON/Sir Convert Story 54 | Durable saved records and formatters must derive from canonical transcript JSON | [x] |
| Skriptoteket owns durable transcript retention after save | Matches product ownership while Sir Convert keeps short operational retention | [x] |

## Review Checklist

- [x] Scope is bounded and appropriate
- [x] Acceptance criteria or proof obligations are reviewable
- [x] Risks and structural fault lines are called out explicitly
- [x] Verification plan matches the claimed contract
- [x] Review does not authorize runtime STT, diarization, re-transcription, or direct Sir Convert access

## Review Feedback

**Reviewer:** fixed-reviewer
**Date:** 2026-06-09
**Verdict:** approved

### Required Changes

No required changes.

### Suggestions (Optional)

None.

### Evidence

- `ST-21-05` keeps transcript intake authenticated through
  `documents.conversion_hub`, names Gateway-only `/sir-convert/v2/convert`
  access, rejects public/no-login/direct Sir Convert browser or sidecar access,
  and maps speaker controls to `auto`, `known_speaker_count`, and
  `speaker_range` before submit.
- `ST-21-06` remains planning authority only until Sir Convert Story 53 and
  HuleEdu `ST-01-08` are accepted and available. Its acceptance criteria keep
  create, poll, artifact retrieval, cancel/error handling, CSRF, idempotency,
  and correlation on the HuleEdu Gateway path.
- `ST-21-07` remains blocked on canonical JSON/Sir Convert Story 54, keeps
  durable transcript retention in Skriptoteket after save, and requires
  TXT/Markdown/VTT/SRT outputs to derive from canonical saved JSON or Sir
  Convert formatter artifacts.
- The upstream authorities reviewed were Sir Convert Review 30, Sir Convert
  ADR-0013 and audio-transcription contract, Sir Convert Stories 53 and 54, and
  HuleEdu `ST-01-08`. They agree that the audio route is planned, not live
  runtime authority, and that downstream product access stays Gateway-only.
- The docs guard is meaningful for this docs-only lane: it asserts the retained
  planning constraints directly in the governed story/review records and uses a
  small deterministic `tests/unit/scripts/` pytest module without network,
  Docker, or brittle fixture coupling.

### Decision Approvals

- [x] Gateway-only access boundary
- [x] Diarization controls and validation scope
- [x] Upstream blocker sequencing
- [x] Durable retention ownership
- [x] JSON-first formatter sequencing

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `ST-21-05` | Made Gateway-only `/sir-convert/v2/convert` access, no public/no-login/direct sidecar access, and diarization option mapping explicit. |
| 2 | `ST-21-06` | Recorded the Sir Convert Story 53 and HuleEdu ST-01-08 implementation blockers. |
| 3 | `ST-21-07` | Recorded canonical JSON/Sir Convert Story 54 blocking, Skriptoteket durable-retention ownership, and JSON-first formatter sequencing. |
| 4 | `REV-ST-21-05` | Created the retained pending review gate for ST-21-05 through ST-21-07. |
| 5 | Docs guard | Added a focused unit guard for the downstream transcript planning constraints. |
| 6 | `REV-ST-21-05` | Fixed reviewer approved the downstream transcript planning lane and closed the decision checklist. |
