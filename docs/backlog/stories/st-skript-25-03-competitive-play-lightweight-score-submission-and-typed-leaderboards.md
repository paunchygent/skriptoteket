---
type: story
id: ST-SKRIPT-25-03
title: Competitive play lightweight score submission and typed leaderboards
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
- Given a completed Flunk-Out Frenzy run, when the user submits a score, then the
  backend stores a lightweight score submission containing `app_id`, `app_version`,
  `ruleset_id`, owner user id, score value, and compact score summary metadata.
- Given the SPA requests the global leaderboard or the signed-in user's own leaderboard
  view, when the backend responds, then the response is a typed app-specific model
  scoped to the current `ruleset_id`.
- Given the current user has recently submitted a score, when they reload the game
  shell, then the app can show personal-best or latest-score state without leaking
  generic run mechanics into the competition UX.
- Given score submission fails, when the failure is returned, then the app remains
  usable for local play and shows an app-level error state without corrupting the
  completed local run summary.
retired_ids:
- ST-25-03
---

## Context


This story introduces the first backend-owned competition contract while keeping
live play local. The platform needs a lightweight place to store submitted
scores and serve typed leaderboards without forcing heavyweight competition
machinery into a fun teacher-facing feature.

## Epic Contract Slice

No separate epic contract slice is stated in the source.

## ADR Coverage

No separate adr coverage is stated in the source.

## Contract Inputs

No separate contract inputs is stated in the source.

## Live Verification Plan

No separate live verification plan is stated in the source.

## Non-Goals

No separate non-goals is stated in the source.

## Notes


- Use typed app endpoints under `/api/v1/apps/games.flunk_out_frenzy/...`.
- Do not leak generic run ids or generic artifact panels into the primary
  competition UX.
- Postgres is the source of truth. Redis remains optional and is not required by
  this story.

## Decision And Assumption Ledger

| source | semantic | carried_forward | Source material is retained in the sections above. | source |

## Plan Document Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.

## Story Closeout Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.
