---
type: reference
id: REF-curated-app-flunk-out-frenzy-architecture-and-foundational-code
title: "Reference: Competitive games curated apps and Flunk-Out Frenzy"
status: active
owners: "agents"
created: 2026-03-22
updated: 2026-03-22
topic: "curated-apps"
links:
  - ADR-0023
  - ADR-0027
  - ADR-0073
  - EPIC-25
  - REF-competitive-games-cross-cutting-programme
  - REV-EPIC-25
---

## Purpose

This reference describes how **competitive browser games** should fit into
Skriptoteket as a curated-app family, with **Flunk-Out Frenzy** as the first
candidate app.

It is intentionally architectural. It defines the platform seams, the runtime
boundary between browser and backend, and the code layout that keeps a game app
compatible with Skriptoteket's curated-app rules.

This document is not a greenfield scaffold, and it is not a standalone game-repo
plan.

## Search terms

Use these canonical terms when searching the codebase or linking future docs:

- `competitive games`
- `Flunk-Out Frenzy`
- `curated app`
- `bespoke_required`
- `official high score`
- `pending score submission`
- `replay validation`
- `leaderboard`

## Product position

- Skriptoteket may ship a small family of playful curated apps that signed-in
  users can open directly in the SPA.
- These apps are still first-class Skriptoteket modules, not external products
  or tool-editor scripts.
- Users should be able to enjoy a short game session locally in the browser
  without network roundtrips during play.
- Competitive features such as global high scores must remain trustworthy,
  reviewable, and compatible with the platform's identity and persistence model.

## Architectural position

Competitive games should use the **bespoke curated-app path**:

- The SPA renders a dedicated app-specific view under `/apps/:appId`.
- The backend exposes app-specific endpoints under `/api/v1/apps/{app_id}/...`.
- Shared platform concerns such as auth, role checks, persistence, observability,
  and auditability remain inside Skriptoteket.
- Shared competitive-play concerns should live in a reusable backend subsystem,
  not inside one game's frontend runtime.

## Core boundary

The most important boundary is:

- The **browser runtime owns live simulation**.
- The **backend owns durable competition state**.

That means:

- Live physics, frame stepping, collision handling, rendering, and local audio
  belong in the frontend runtime.
- Identity, app boot metadata, pending score submissions, official score
  promotion, replay persistence, and leaderboard queries belong in the backend.

### Do not use as the primary runtime model

These platform primitives remain useful, but they must not become the game's
main simulation contract:

- `tool_sessions`
- `ui_payload`
- generic `start_action`
- generic run/status polling UI

For games, those are at most support primitives for small shell state or
internal implementation details. They are not the primary contract for live
play.

## Recommended family model

Use two layers:

### 1. Shared competitive-play backend

This layer should be reusable across future game apps.

Recommended responsibilities:

- `ruleset_id` / `season_id` scoping
- pending score submission records
- replay asset references and metadata
- replay validation and promotion to official scores
- official leaderboard queries
- personal-history queries for the signed-in user

### 2. App-specific game implementation

This layer is where Flunk-Out Frenzy remains bespoke.

Recommended responsibilities:

- runtime bootstrap payload
- table content and game rules
- app-specific HUD and UX
- app-specific score summary and submission UX
- app-specific rendering, controls, and audiovisual feel

## Recommended code map

```text
src/skriptoteket/
  domain/
    competitive_play/
      models.py
      policies.py
      errors.py
    curated_apps/
      flunk_out_frenzy/
        models.py
        bootstrap.py
        scoring.py
  application/
    competitive_play/
      get_leaderboard.py
      submit_score.py
      validate_submission.py
    curated_apps/
      flunk_out_frenzy/
        get_bootstrap.py
  infrastructure/
    competitive_play/
      repositories.py
      replay_storage.py
    curated_apps/
      apps/
        flunk_out_frenzy/
          registry_entry.py
  web/
    api/v1/
      apps_flunk_out_frenzy.py
frontend/apps/skriptoteket/src/
  views/apps/
    FlunkOutFrenzyView.vue
  components/apps/flunk-out-frenzy/
    GameHost.vue
    gameBridge.ts
    game/
```

## Flunk-Out Frenzy frontend boundary

Flunk-Out Frenzy should keep a hard split between the SPA shell and the game
machine:

### Shell responsibilities

`frontend/apps/skriptoteket/src/views/apps/FlunkOutFrenzyView.vue` should own:

- route-level loading and error states
- app boot metadata
- route-level immersive mode activation
- HUD projection from the runtime
- pause / restart / mute buttons
- score summary and submit-score UX
- leaderboard and profile-adjacent views

### Shell presentation rule

Once the user enters Flunk-Out Frenzy, the main surface should read as a game,
not as a generic Skriptoteket teacher tool.

That means:

- keep only the shared top bar as obvious Skriptoteket chrome
- hide the normal sidebar / generic content framing while the game route is
  active
- make the first viewport read as one staged game composition rather than a
  dashboard of unrelated columns
- use strong container styling only where it carries interaction or critical
  game information; do not wrap empty or decorative regions in cards/panels
- use real playfield, cabinet, or game-world imagery as the main visual anchor;
  abstract gradients can support the scene but should not define it
- avoid academic/brutalist card stacks and visible debug/bootstrap panels in
  the main play surface
- treat settings, diagnostics, and future score-submission affordances as
  secondary overlays or in-game menus, not permanent side panels

### Machine responsibilities

`frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/` should
own:

- fixed-step runtime loop
- input-to-command translation
- physics
- rendering
- audio
- deterministic rule evaluation
- replay capture for validation

### Non-negotiable rule

Vue must not own live simulation state.

Weak:

- ball position in a Vue store
- flipper angle in a composable
- collision handling through watchers

Strong:

- `GameRuntime` owns the machine
- Vue receives a read-only HUD projection such as score, balls left,
  multiplier, mute state, and paused state

## Flunk-Out Frenzy stack recommendation

Within the existing Skriptoteket SPA and backend:

- Frontend runtime: Vue 3 + TypeScript + PixiJS v8 + Rapier 2D + Howler.js
- Testing: Vitest + Playwright
- Backend: existing FastAPI monolith, not a separate service
- Persistence: PostgreSQL first; Redis only if later profiling proves a cache or
  live fan-out is necessary

This stack choice is app-specific. Future competitive games do not need to use
the same rendering or simulation libraries.

## Suggested backend API shape

Flunk-Out Frenzy should prefer typed app endpoints such as:

- `GET /api/v1/apps/games.flunk_out_frenzy/bootstrap`
- `POST /api/v1/apps/games.flunk_out_frenzy/score-submissions`
- `GET /api/v1/apps/games.flunk_out_frenzy/leaderboards/global`
- `GET /api/v1/apps/games.flunk_out_frenzy/leaderboards/me`

If the app uses internal run/execution machinery for exports or background
validation, those details must stay server-side behind the app-specific API.

## High-score support planned from day one

Even if global competition lands after the first local slice, the architecture
should reserve these concepts immediately:

- `app_id`
- `app_version`
- `ruleset_id`
- optional `season_id`
- `pending` versus `official` score lifecycle
- replay asset reference plus summary metadata

This prevents balance changes or scoring tweaks from corrupting one shared
leaderboard.

## Identity and display rules

- Use the existing Skriptoteket user and session model.
- Do not expose email addresses on leaderboards.
- Use `UserProfile.display_name` as the initial public display string unless a
  future story introduces a dedicated public alias.
- Keep authorization local to Skriptoteket roles, consistent with the current
  identity model.

## Storage guidance

### PostgreSQL

Required from the first competition-capable slice:

- score submissions
- official scores
- replay metadata
- leaderboard query indexes
- app/ruleset/season scoping

### Redis

Optional later optimization only:

- cached leaderboard pages
- rate limiting
- live scoreboard fan-out if the product genuinely needs it

Redis is not required for the first local vertical slice, and it is not required
for the first trustworthy leaderboard slice.

## Suggested rollout

### Slice 1: local playable app

- bespoke route and bootstrap contract
- Flunk-Out Frenzy runtime inside the existing SPA
- local 3-ball play
- pause / restart / mute

### Slice 2: competitive-play plumbing

- pending score submissions
- replay storage
- typed leaderboard endpoints
- personal best and global board views

### Slice 3: officialization

- replay validation worker
- official score promotion
- rejection reasons and moderation-safe failure states

## Testing shape

- Unit tests for pure rules and scoring logic
- Frontend tests around runtime-to-HUD bridging and route lifecycle cleanup
- Backend tests for score submission, promotion policy, and leaderboard scoping
- Live functional UI checks whenever the app route or view changes

## Explicit non-goals for this reference

- A fresh Vite/FastAPI scaffold
- Replacing the repo's existing SPA host or curated app registry
- Driving the game primarily through generic `AppDetailView`
- Storing live machine state in `tool_sessions`
- Treating Redis or WebSockets as mandatory on day one

## Notes

- Flunk-Out Frenzy is the first candidate app, not a special exception to the
  platform.
- If additional games are added later, extend the shared `competitive_play`
  subsystem instead of cloning Pinball-specific persistence logic.
