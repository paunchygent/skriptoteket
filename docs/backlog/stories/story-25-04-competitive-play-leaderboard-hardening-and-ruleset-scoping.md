---
type: story
id: ST-25-04
title: "Competitive play lightweight leaderboard hardening and ruleset scoping"
status: ready
owners: "agents"
created: 2026-03-22
epic: "EPIC-25"
dependencies: ["ST-25-03", "ADR-0073"]
acceptance_criteria:
  - "Given a Flunk-Out Frenzy score submission matches the declared `app_version` and `ruleset_id`, when lightweight server-side acceptance checks run, then eligible scores can appear on the leaderboard without a detached validation pipeline."
  - "Given a submission is malformed, duplicate, or out of policy, when it is handled, then leaderboard state remains unchanged and the app receives a clear failure response."
  - "Given a future balance or scoring change introduces a new `ruleset_id` or `season_id`, when leaderboard queries run, then incompatible runs remain scoped apart rather than merged into the same official board."
ui_impact: "Yes (leaderboard states and user-facing failure handling)"
data_impact: "Yes (leaderboard acceptance policy + scoped leaderboard state)"
---

## Context

Lightweight competition still needs a server-owned acceptance and scoping layer
so the leaderboard stays coherent across ruleset changes and malformed
submissions, but this story no longer assumes detached playback pipelines or
moderation-heavy competition mechanics.

## Notes

- Keep acceptance checks proportionate to a fun teacher leaderboard.
- Inline application-layer handling is preferred; a worker-backed flow is not
  required for this story.
- Do not introduce playback storage, manual review tooling, or moderation-heavy
  workflows here.
