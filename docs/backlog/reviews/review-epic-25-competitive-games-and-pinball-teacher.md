---
type: review
id: REV-EPIC-25
title: "Review: Competitive games foundations and Pinball Teacher"
status: approved
owners: "agents"
updated: 2026-03-22
reviewer: "lead-developer"
epic: "EPIC-25"
created: 2026-03-22
adrs:
  - ADR-0073
stories:
  - ST-25-01
  - ST-25-02
  - ST-25-03
  - ST-25-04
---

## TL;DR

This review approves introducing competitive browser games as a new curated-app
family inside Skriptoteket, with Pinball Teacher as the first app. The key
architectural move is to keep live gameplay browser-owned while moving score
submission, replay validation, and official leaderboard promotion into a shared
backend subsystem.

## Scope of this review

This review covers:

- the architecture decision in `ADR-0073`
- the first implementation epic in `EPIC-25`
- the first four stories in that epic
- the cross-cutting planning reference that explains how later work should be
  split across shared workstreams

This review does not approve implementation details below story level.

## Problem Statement

The current curated-app platform supports bespoke apps well, but competitive
games add a new requirement mix: low-latency local play plus trustworthy global
competition. If we drive a game primarily through generic tool sessions and
typed UI outputs, the product will fight both the game runtime and the curated
app architecture.

## Proposed Solution

Adopt `ui_mode=bespoke_required` for competitive game apps, add a shared
`competitive_play` backend subsystem, and build Pinball Teacher as the first
consumer. The first implementation slice covers app registration, typed
bootstrap, and a local runtime vertical slice. The follow-on stories add pending
score submission, typed leaderboards, replay validation, and official score
promotion.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0073-competitive-games-and-official-high-scores.md` | Browser/runtime vs backend/competition boundary | 10 min |
| `docs/backlog/epics/epic-25-competitive-games-and-pinball-teacher.md` | Scope and slice boundaries | 5 min |
| `docs/reference/ref-competitive-games-cross-cutting-programme.md` | Cross-cutting workstream and backlog framing | 5 min |
| `docs/backlog/stories/story-25-01-competitive-games-substrate-and-pinball-teacher-bootstrap-contract.md` | Curated-app entry seam | 5 min |
| `docs/backlog/stories/story-25-02-pinball-teacher-local-runtime-vertical-slice.md` | Local runtime boundary | 5 min |
| `docs/backlog/stories/story-25-03-competitive-play-pending-score-submission-and-typed-leaderboards.md` | Submission + leaderboard contract | 5 min |
| `docs/backlog/stories/story-25-04-competitive-play-replay-validation-and-official-score-promotion.md` | Officialization policy | 5 min |

**Total estimated time:** ~40 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Browser-owned live simulation | Protect game feel and keep network latency out of active play | [x] |
| Shared `competitive_play` backend | Avoid one-off Pinball Teacher persistence logic and prepare for future games | [x] |
| Pending-to-official score lifecycle | Keep global leaderboards trustworthy and auditable | [x] |
| `ruleset_id` from the start | Prevent future scoring/balance changes from corrupting one shared board | [x] |

## Review Checklist

- [x] ADR defines a clear runtime and persistence boundary
- [x] EPIC scope is appropriate for a first curated game family slice
- [x] Stories have testable acceptance criteria
- [x] Backend contracts remain app-specific and bespoke
- [x] Risks are identified with reasonable mitigations

## Review Feedback

**Reviewer:** @lead-developer
**Date:** 2026-03-22
**Verdict:** approved

### Required Changes

None. The proposal is thorough and aligns with the project's architectural principles.

### Suggestions (Optional)

- Consider how `ruleset_id` will be generated/managed (e.g., content-based hash or manual sequence) as this will be critical for the first score-capable slice in `ST-25-03`.
- Ensure the replay capture seam in `ST-25-02` is isolated enough that it can be easily updated if the validation logic in `ST-25-04` requires more metadata than initially planned.

### Decision Approvals

- [x] Browser-owned live simulation
- [x] Shared `competitive_play` backend
- [x] Pending-to-official score lifecycle
- [x] `ruleset_id` from the start

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | ADR-0073 | Initial proposal created |
| 2 | EPIC-25 / ST-25-01..04 | Initial scope and stories created |
