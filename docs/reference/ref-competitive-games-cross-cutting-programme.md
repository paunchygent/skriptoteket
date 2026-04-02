---
type: reference
id: REF-competitive-games-cross-cutting-programme
title: "Reference: Competitive games cross-cutting delivery programme"
status: active
owners: "agents"
created: 2026-03-22
topic: "curated-apps"
links:
  - ADR-0073
  - EPIC-25
  - REF-curated-app-flunk-out-frenzy-architecture-and-foundational-code
---

## Purpose

This reference defines the **cross-cutting delivery programme** for the
competitive-games family in Skriptoteket.

It is not a user-facing product concept. It exists to help us plan epics,
stories, and implementation tasks that cut across:

- curated-app family seams
- frontend runtime foundations
- shared competition infrastructure
- lightweight global high-score support
- testing and operational hardening

## How to use this document

Use this reference when:

- decomposing competitive-games work into epics and stories
- deciding whether a task belongs in shared infrastructure or one game app
- sequencing delivery so local gameplay can ship before lightweight leaderboard support
- checking that cross-cutting work is not being hidden inside a single app story

Do not use this document as a replacement for the app architecture reference or
for the ADR.

## Programme goals

- Keep live play browser-owned and responsive.
- Keep leaderboard state backend-owned and proportionate to a fun teacher-competition feature.
- Reuse shared competition infrastructure across future games.
- Preserve Skriptoteket's curated-app model instead of inventing a parallel
  product architecture.
- Let the first game ship without blocking on heavyweight leaderboard machinery.

## Workstreams

### 1. Curated-app family substrate

Focus:

- curated app registry entries
- bespoke SPA view routing
- typed bootstrap contracts
- app-specific API surfaces
- app identity fields such as `app_id`, `app_version`, and `ruleset_id`

Typical output:

- app registration stories
- bootstrap contract stories
- frontend host wiring

### 2. Local game runtime foundations

Focus:

- shell/runtime boundary
- fixed-step simulation
- input, physics, render, and audio seams
- runtime lifecycle and cleanup

Typical output:

- vertical-slice runtime stories
- runtime test stories
- feel-and-polish follow-up stories

### 3. Shared competition infrastructure

Focus:

- pending score submissions
- leaderboard read models
- persistence tables and indexes
- personal history views
- backend contracts that are reusable across games

Typical output:

- shared `competitive_play` domain/application/infrastructure stories
- typed leaderboard and submission API stories

### 4. Leaderboard acceptance and lightweight competition hardening

Focus:

- lightweight score-acceptance checks
- duplicate/spam protection when needed
- clean failure handling
- ruleset and season scoping

Typical output:

- leaderboard hardening stories
- ruleset/season scoping stories
- release-safe failure-state stories

### 5. Quality, observability, and operability

Focus:

- deterministic tests for scoring and rules
- browser smoke coverage for app routes and runtime cleanup
- leaderboard correctness checks
- monitoring and support diagnostics
- production-safe failure states

Typical output:

- Playwright/Vitest/Pytest coverage stories
- runbooks and operational hardening tasks

## Planning rules

- Put shared competition behavior in shared workstreams, not inside one game's
  app-specific story unless it is truly app-specific.
- Put live runtime concerns in frontend runtime stories, not in backend
  competition stories.
- Keep the browser-runtime versus backend-competition boundary intact in every
  epic and story.
- Reserve future competition identifiers early, even when a story only ships
  local play.

## Current mapping

### Current epic

- `EPIC-25` currently covers the first competitive-games family slice with
  Flunk-Out Frenzy as the first app.

### Current stories

- `ST-25-01`: curated-app substrate + bootstrap seam
- `ST-25-02`: local runtime vertical slice
- `ST-25-03`: lightweight score submissions + typed leaderboards
- `ST-25-04`: lightweight leaderboard hardening + ruleset scoping

## Recommended next backlog evolution

If the competitive-games family grows beyond the first game, consider splitting
future backlog into additional epics by workstream rather than stretching one
epic indefinitely.

Good split candidates:

- an epic for shared competition infrastructure
- an epic for lightweight leaderboard hardening across multiple games
- an epic for runtime hardening and second-game readiness

## Notes

- This programme is cross-cutting delivery structure, not a user-facing hub.
- Flunk-Out Frenzy remains the first app-specific implementation reference.
