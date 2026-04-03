---
type: review
id: REV-EPIC-25
title: "Review: Competitive games foundations and Flunk-Out Frenzy"
status: approved
owners: "agents"
updated: 2026-04-03
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
family inside Skriptoteket, with Flunk-Out Frenzy as the first app. The key
architectural move is to keep live gameplay browser-owned while moving score
submission and lightweight leaderboard support into a shared backend subsystem.

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
`competitive_play` backend subsystem, and build Flunk-Out Frenzy as the first
consumer. The first implementation slice covers app registration, typed
bootstrap, and a local runtime vertical slice. The follow-on stories add pending
score submission, typed leaderboards, and lightweight leaderboard hardening with
ruleset scoping.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0073-competitive-games-and-official-high-scores.md` | Browser/runtime vs backend/competition boundary | 10 min |
| `docs/backlog/epics/epic-25-competitive-games-and-flunk-out-frenzy.md` | Scope and slice boundaries | 5 min |
| `docs/reference/ref-competitive-games-cross-cutting-programme.md` | Cross-cutting workstream and backlog framing | 5 min |
| `docs/backlog/stories/story-25-01-competitive-games-substrate-and-flunk-out-frenzy-bootstrap-contract.md` | Curated-app entry seam | 5 min |
| `docs/backlog/stories/story-25-02-flunk-out-frenzy-local-runtime-vertical-slice.md` | Local runtime boundary | 5 min |
| `docs/backlog/stories/story-25-03-competitive-play-pending-score-submission-and-typed-leaderboards.md` | Submission + leaderboard contract | 5 min |
| `docs/backlog/stories/story-25-04-competitive-play-leaderboard-hardening-and-ruleset-scoping.md` | Lightweight leaderboard hardening policy | 5 min |

**Total estimated time:** ~40 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Browser-owned live simulation | Protect game feel and keep network latency out of active play | [x] |
| Shared `competitive_play` backend | Avoid one-off Flunk-Out Frenzy persistence logic and prepare for future games | [x] |
| Lightweight server-owned leaderboard lifecycle | Keep global leaderboards fun, consistent, and proportionate to the product | [x] |
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

### Decision Approvals

- [x] Browser-owned live simulation
- [x] Shared `competitive_play` backend
- [x] Lightweight server-owned leaderboard lifecycle
- [x] `ruleset_id` from the start

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | ADR-0073 | Initial proposal created |
| 2 | EPIC-25 / ST-25-01..04 | Initial scope and stories created |

## Supplemental Review Record: PR-0204 Launcher Input/Overlay Gate

**Reviewer:** `skriptoteket_reviewer` (independent; not the plan author)
**Date:** 2026-04-03
**Verdict:** `changes_requested`

### Scope Reviewed

- `docs/backlog/prs/pr-0204-flunk-out-frenzy-ruthless-review-gate-for-launcher-input-and-overlay-seam.md`

### Required Changes (blocking for gate approval)

1. Make the authoritative live plunger defect explicit approval blocker; do not
   allow `approved` while unresolved.
2. Make overlay/input interaction checks explicit (keyboard + pointer, focus
   states, overlay closed/reopened).
3. Replace route/bootstrap-only evidence with launcher behavior proof
   requirements.
4. Operationalize reviewer independence (no self-approval, no delegated
   approval for this gate).
5. Require explicit scope listing and retained verdict artifact discipline.

### Evidence Notes

- This supplemental record is retained to keep the launcher review gate verdict
  in canonical docs workflow, not session-only notes.
- Enforcing surfaces for the terminal-route-only `handoffVelocity` invariant:
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/tableDefinitionTypes.ts`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.ts`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts`
