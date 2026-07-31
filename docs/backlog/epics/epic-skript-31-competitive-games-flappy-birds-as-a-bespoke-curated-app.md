---
type: epic
id: EPIC-SKRIPT-31
title: 'Competitive games: Flappy Birds as a bespoke curated app'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: proposed
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
outcome: Signed-in users can open `games.flappy_birds` as a bespoke curated app inside
  the existing Skriptoteket SPA, play a polished browser-owned Flappy Birds session
  with authored difficulty, bird selection, and app-specific shell UX, and post scores
  to lightweight backend-owned personal/global leaderboards scoped by `app_version`
  and `ruleset_id`.
retired_ids:
- EPIC-31
---

## Scope

- Register `games.flappy_birds` in the curated app registry with `ui_mode=bespoke_required`
  and ship it as a real first-class curated app from day one.
- Add a dedicated bespoke SPA route/view and app-specific bootstrap contract following the
  established competitive-games pattern from `games.flunk_out_frenzy`.
- Port Flappy Birds gameplay semantics from the donor project into Skriptoteket-native
  shell/runtime boundaries instead of transplanting the donor DOM shell wholesale.
- Preserve the browser-owned live simulation rule: input, spawning, scoring, collision,
  rendering, audio, pause/restart, and local run lifecycle stay client-side.
- Build the runtime around the current competitive-game shell pattern:
  lazy runtime loading, imperative host lifecycle, and read-only HUD projections back to Vue.
- Prefer `Pixi` for rendering and `Howler` for audio unless an implementation story finds a
  better repo-local fit; do not force `Rapier` into the first Flappy Birds slice unless the
  app actually needs it.
- Keep the donor gameplay language where it is valuable:
  bird-color selection, authored difficulty curve, power-up meanings, and clear local score
  loop semantics.
- Add lightweight backend-owned score submission and leaderboard endpoints for
  `games.flappy_birds`, scoped by `app_id`, `app_version`, and `ruleset_id`.
- Treat high scores as a light leisure feature for teachers with simple, server-owned
  leaderboard state.

## Epic Contract

### Scope

- Register `games.flappy_birds` in the curated app registry with `ui_mode=bespoke_required`
  and ship it as a real first-class curated app from day one.
- Add a dedicated bespoke SPA route/view and app-specific bootstrap contract following the
  established competitive-games pattern from `games.flunk_out_frenzy`.
- Port Flappy Birds gameplay semantics from the donor project into Skriptoteket-native
  shell/runtime boundaries instead of transplanting the donor DOM shell wholesale.
- Preserve the browser-owned live simulation rule: input, spawning, scoring, collision,
  rendering, audio, pause/restart, and local run lifecycle stay client-side.
- Build the runtime around the current competitive-game shell pattern:
  lazy runtime loading, imperative host lifecycle, and read-only HUD projections back to Vue.
- Prefer `Pixi` for rendering and `Howler` for audio unless an implementation story finds a
  better repo-local fit; do not force `Rapier` into the first Flappy Birds slice unless the
  app actually needs it.
- Keep the donor gameplay language where it is valuable:
  bird-color selection, authored difficulty curve, power-up meanings, and clear local score
  loop semantics.
- Add lightweight backend-owned score submission and leaderboard endpoints for
  `games.flappy_birds`, scoped by `app_id`, `app_version`, and `ruleset_id`.
- Treat high scores as a light leisure feature for teachers with simple, server-owned
  leaderboard state.

### Out of Scope

- Treating Flappy Birds as a detached runtime experiment or standalone product outside the
  curated-app system.
- Reusing generic tool/run UI as the primary user experience.
- Submission-review pipelines, extra evidence artifacts, or any other heavyweight
  competition flow for this epic.
- Heavy moderation, anti-cheat operations, or dispute-resolution workflows.
- Requiring `Rapier` or pinball-specific runtime seams where a simpler deterministic arcade
  engine is sufficient.
- Real-time multiplayer, tournaments, or social mechanics.

### Risks

- If the donor shell is copied too literally, the app will fight the bespoke SPA route and typed
  bootstrap model already accepted for competitive curated apps.
- If `ruleset_id` and `app_version` discipline is skipped early, later balance changes may
  corrupt one shared leaderboard.
- If the leaderboard path inherits heavier validation assumptions from earlier
  competitive-games planning, a fun side feature could become overengineered.
- If current upstream assets/sounds are reused blindly, shipping could be blocked by asset-rights
  concerns late in the cycle.
- If Flunk-Out Frenzy runtime internals are treated as mandatory rather than as a precedent, the
  second game could inherit unnecessary complexity.

### Planned Implementation Lanes

- `Flappy Birds substrate`:
  curated-app registration, bespoke route resolution, and typed bootstrap contract.
- `Local playable app`:
  game-first shell, authored runtime, bird selection, difficulty curve, pause/restart/mute,
  and clean route disposal.
- `Lightweight competition plumbing`:
  app-specific score submission plus global/my leaderboard reads with ruleset/app-version
  scoping and simple server-owned acceptance.
- `Polish and release hardening`:
  asset replacement/finalization, balance tuning, browser proof, and docs/runbook closure.

### Notes

- `EPIC-31` is the implementation lane for Flappy Birds itself, not a replacement for the
  cross-cutting competitive-games family work already established in `EPIC-25`.
- This epic assumes the product decision that Flappy Birds ships as `games.flappy_birds`
  from day one and is not framed as a runtime-only experiment.
- Story docs for this epic should be scaffolded after review approval so the decomposition
  reflects the accepted lightweight leaderboard direction instead of older heavyweight
  competition assumptions.
- This epic requires review approval before implementation begins per the repo review workflow.

## ADR Coverage

No separate material is recorded in the source snapshot.

## Contract Inputs

No separate material is recorded in the source snapshot.

## Stories

No separate material is recorded in the source snapshot.

## Epic Verification Plan

No separate material is recorded in the source snapshot.

## Exceptions And Follow-Ups

- Treating Flappy Birds as a detached runtime experiment or standalone product outside the
  curated-app system.
- Reusing generic tool/run UI as the primary user experience.
- Submission-review pipelines, extra evidence artifacts, or any other heavyweight
  competition flow for this epic.
- Heavy moderation, anti-cheat operations, or dispute-resolution workflows.
- Requiring `Rapier` or pinball-specific runtime seams where a simpler deterministic arcade
  engine is sufficient.
- Real-time multiplayer, tournaments, or social mechanics.

## Risks

- If the donor shell is copied too literally, the app will fight the bespoke SPA route and typed
  bootstrap model already accepted for competitive curated apps.
- If `ruleset_id` and `app_version` discipline is skipped early, later balance changes may
  corrupt one shared leaderboard.
- If the leaderboard path inherits heavier validation assumptions from earlier
  competitive-games planning, a fun side feature could become overengineered.
- If current upstream assets/sounds are reused blindly, shipping could be blocked by asset-rights
  concerns late in the cycle.
- If Flunk-Out Frenzy runtime internals are treated as mandatory rather than as a precedent, the
  second game could inherit unnecessary complexity.

## Notes

### Scope

- Register `games.flappy_birds` in the curated app registry with `ui_mode=bespoke_required`
  and ship it as a real first-class curated app from day one.
- Add a dedicated bespoke SPA route/view and app-specific bootstrap contract following the
  established competitive-games pattern from `games.flunk_out_frenzy`.
- Port Flappy Birds gameplay semantics from the donor project into Skriptoteket-native
  shell/runtime boundaries instead of transplanting the donor DOM shell wholesale.
- Preserve the browser-owned live simulation rule: input, spawning, scoring, collision,
  rendering, audio, pause/restart, and local run lifecycle stay client-side.
- Build the runtime around the current competitive-game shell pattern:
  lazy runtime loading, imperative host lifecycle, and read-only HUD projections back to Vue.
- Prefer `Pixi` for rendering and `Howler` for audio unless an implementation story finds a
  better repo-local fit; do not force `Rapier` into the first Flappy Birds slice unless the
  app actually needs it.
- Keep the donor gameplay language where it is valuable:
  bird-color selection, authored difficulty curve, power-up meanings, and clear local score
  loop semantics.
- Add lightweight backend-owned score submission and leaderboard endpoints for
  `games.flappy_birds`, scoped by `app_id`, `app_version`, and `ruleset_id`.
- Treat high scores as a light leisure feature for teachers with simple, server-owned
  leaderboard state.

### Out of Scope

- Treating Flappy Birds as a detached runtime experiment or standalone product outside the
  curated-app system.
- Reusing generic tool/run UI as the primary user experience.
- Submission-review pipelines, extra evidence artifacts, or any other heavyweight
  competition flow for this epic.
- Heavy moderation, anti-cheat operations, or dispute-resolution workflows.
- Requiring `Rapier` or pinball-specific runtime seams where a simpler deterministic arcade
  engine is sufficient.
- Real-time multiplayer, tournaments, or social mechanics.

### Risks

- If the donor shell is copied too literally, the app will fight the bespoke SPA route and typed
  bootstrap model already accepted for competitive curated apps.
- If `ruleset_id` and `app_version` discipline is skipped early, later balance changes may
  corrupt one shared leaderboard.
- If the leaderboard path inherits heavier validation assumptions from earlier
  competitive-games planning, a fun side feature could become overengineered.
- If current upstream assets/sounds are reused blindly, shipping could be blocked by asset-rights
  concerns late in the cycle.
- If Flunk-Out Frenzy runtime internals are treated as mandatory rather than as a precedent, the
  second game could inherit unnecessary complexity.

### Planned Implementation Lanes

- `Flappy Birds substrate`:
  curated-app registration, bespoke route resolution, and typed bootstrap contract.
- `Local playable app`:
  game-first shell, authored runtime, bird selection, difficulty curve, pause/restart/mute,
  and clean route disposal.
- `Lightweight competition plumbing`:
  app-specific score submission plus global/my leaderboard reads with ruleset/app-version
  scoping and simple server-owned acceptance.
- `Polish and release hardening`:
  asset replacement/finalization, balance tuning, browser proof, and docs/runbook closure.

### Notes

- `EPIC-31` is the implementation lane for Flappy Birds itself, not a replacement for the
  cross-cutting competitive-games family work already established in `EPIC-25`.
- This epic assumes the product decision that Flappy Birds ships as `games.flappy_birds`
  from day one and is not framed as a runtime-only experiment.
- Story docs for this epic should be scaffolded after review approval so the decomposition
  reflects the accepted lightweight leaderboard direction instead of older heavyweight
  competition assumptions.
- This epic requires review approval before implementation begins per the repo review workflow.

## Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

## Plan Document Review

No separate material is recorded in the source snapshot.

## Epic Closeout Review

No separate material is recorded in the source snapshot.
