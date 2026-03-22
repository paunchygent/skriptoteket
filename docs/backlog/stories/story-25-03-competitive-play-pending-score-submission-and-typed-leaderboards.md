---
type: story
id: ST-25-03
title: "Competitive play pending score submission and typed leaderboards"
status: ready
owners: "agents"
created: 2026-03-22
epic: "EPIC-25"
dependencies: ["ST-25-01", "ST-25-02", "ADR-0073"]
acceptance_criteria:
  - "Given a completed Pinball Teacher run, when the user submits a score, then the backend stores a pending submission containing `app_id`, `app_version`, `ruleset_id`, owner user id, score summary, and a replay asset reference or equivalent replay metadata."
  - "Given the SPA requests the global leaderboard or the signed-in user's own leaderboard view, when the backend responds, then the response is a typed app-specific model that includes only official scores on the official board."
  - "Given the current user has a pending submission, when they reload the game shell, then the app can show that pending status separately from the official leaderboard."
  - "Given score submission fails, when the failure is returned, then the app remains usable for local play and shows an app-level error state without corrupting the completed local run summary."
ui_impact: "Yes (score summary + leaderboard views)"
data_impact: "Yes (new competitive-play persistence tables and indexes)"
---

## Context

This story introduces the first backend-owned competition contract while keeping
live play local. The platform needs a trustworthy place to store pending score
submissions before replay validation is introduced.

## Notes

- Use typed app endpoints under `/api/v1/apps/games.pinball_teacher/...`.
- Do not leak generic run ids or generic artifact panels into the primary
  competition UX.
- Postgres is the source of truth. Redis remains optional and is not required by
  this story.
