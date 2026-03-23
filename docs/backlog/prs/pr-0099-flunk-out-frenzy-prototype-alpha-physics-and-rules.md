---
type: pr
id: PR-0099
title: "Flunk-Out Frenzy: prototype-alpha physics and rules"
status: done
owners: "agents"
created: 2026-03-22
updated: 2026-03-23
stories:
  - "ST-25-02"
tags: ["frontend", "games", "physics", "rules"]
dependencies:
  - "PR-0098"
acceptance_criteria:
  - "The first playable table runs with one active ball, two flippers, launcher, drain handling, score, and multiplier."
  - "Rapier-backed physics stays behind a `PhysicsWorld` boundary and emits semantic machine events instead of raw engine details."
  - "A rule engine consumes machine events and produces score, multiplier, and ball-lifecycle outcomes without leaking rendering or audio concerns into the physics layer."
  - "The first table definition is authored as typed TypeScript modules, not externalized JSON, and remains intentionally narrow."
---

## Problem

The runtime backbone alone is not enough. `ST-25-02` only becomes meaningful
when the browser-owned runtime can run a real, deterministic local game slice
with clear physics and rules boundaries.

## Goal

Build the first narrow playable table logic for Flunk-Out Frenzy:

- one local table
- one active ball
- two flippers and a launcher
- drain handling
- score and multiplier loop
- deterministic physics-to-rules translation

## Non-goals

- No replay capture.
- No drop-target bank, scoop choreography, or ramp logic in this slice.
- No backend score submission or global leaderboard integration.
- No externalized JSON content system yet.

## Implementation plan

- Commit to the intended runtime stack now:
  - PixiJS
  - Rapier 2D
  - Howler
- Add physics/rules modules such as:
  - `PhysicsWorld.ts`
  - `RuleEngine.ts`
  - typed table definition modules for the first prototype table
- Keep the first typed content subset deliberately narrow, based on the locked
  story scope:
  - launch lane
  - three pop bumpers
  - left/right slingshots
  - `L-A-T-E` rollover bank
  - drain
- Exclude the more advanced themed features from this slice even if they are
  already sketched in content drafts:
  - jock drop targets
  - scoop/mode behavior
  - ramps
  - multiball
- Ensure physics emits stable semantic tags and rules consume those tags to
  award score and update multiplier state.

## Test plan

Automated:

- physics tests for launcher/drain/bumper/slingshot event behavior
- rule-engine tests for score and multiplier progression
- regression tests proving Vue never owns live simulation state

Manual/live:

- verify one full 3-ball local run can be played
- verify drain respawns until game over
- verify score and multiplier change for bumpers, slingshots, and rollovers

Suggested commands:

```bash
pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/components/apps/flunk-out-frenzy/game/**/*.spec.ts
pnpm -C frontend --filter @skriptoteket/spa exec eslint src/components/apps/flunk-out-frenzy/game
pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit
```

## Rollback plan

- Remove the prototype-alpha physics/rules modules and tests.
- Keep the runtime core from `PR-0098` intact if useful for later work.
- Revert the shell to a non-playable host if the table slice must be backed out.
