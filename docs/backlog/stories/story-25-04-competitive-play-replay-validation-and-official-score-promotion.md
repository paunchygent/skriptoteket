---
type: story
id: ST-25-04
title: "Competitive play replay validation and official score promotion"
status: ready
owners: "agents"
created: 2026-03-22
epic: "EPIC-25"
dependencies: ["ST-25-03", "ADR-0073"]
acceptance_criteria:
  - "Given a pending Pinball Teacher score submission with valid replay data that matches the declared `app_version` and `ruleset_id`, when validation completes, then the submission can be promoted to an official score."
  - "Given replay validation fails or the submission does not match the declared ruleset, when validation completes, then the submission is marked rejected with a stored reason and it never appears on the official leaderboard."
  - "Given a future balance or scoring change introduces a new `ruleset_id` or `season_id`, when leaderboard queries run, then incompatible runs remain scoped apart rather than merged into the same official board."
data_impact: "Yes (promotion state + validation metadata)"
---

## Context

Official competition is only trustworthy if the platform can distinguish local
results from validated results. This story adds the promotion step that turns a
pending submission into an official leaderboard entry.

## Notes

- Validation may run in-process first and later move to a worker-backed flow.
- Rejected submissions should remain auditable for operations and support.
- This story is where the shared `competitive_play` subsystem becomes more than
  a storage seam and starts enforcing real competition policy.
