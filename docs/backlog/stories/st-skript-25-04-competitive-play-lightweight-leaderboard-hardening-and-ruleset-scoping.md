---
type: story
id: ST-SKRIPT-25-04
title: Competitive play lightweight leaderboard hardening and ruleset scoping
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-25
acceptance_criteria:
- Given a Flunk-Out Frenzy score submission matches the declared `app_version` and
  `ruleset_id`, when lightweight server-side acceptance checks run, then eligible
  scores can appear on the leaderboard without a detached validation pipeline.
- Given a submission is malformed, duplicate, or out of policy, when it is handled,
  then leaderboard state remains unchanged and the app receives a clear failure response.
- Given a future balance or scoring change introduces a new `ruleset_id` or `season_id`,
  when leaderboard queries run, then incompatible runs remain scoped apart rather
  than merged into the same official board.
retired_ids:
- ST-25-04
dependencies:
- ST-SKRIPT-25-03
- ADR-SKRIPT-0073
---

## Context
Lightweight competition still needs a server-owned acceptance and scoping layer
so the leaderboard stays coherent across ruleset changes and malformed
submissions, but this story no longer assumes detached playback pipelines or
moderation-heavy competition mechanics.

## Epic Contract Slice
The source record did not define a separate section for this package heading.

## ADR Coverage
The source record did not define a separate section for this package heading.

## Contract Inputs
The source record did not define a separate section for this package heading.

## Live Verification Plan
The source record did not define a separate section for this package heading.

## Non-Goals
The source record did not define a separate section for this package heading.

## Notes
- Keep acceptance checks proportionate to a fun teacher leaderboard.
- Inline application-layer handling is preferred; a worker-backed flow is not
  required for this story.
- Do not introduce playback storage, manual review tooling, or moderation-heavy
  workflows here.

## Decision And Assumption Ledger
The source record did not define a separate section for this package heading.

## Plan Document Review
The source record did not define a separate section for this package heading.

## Story Closeout Review
The source record did not define a separate section for this package heading.
