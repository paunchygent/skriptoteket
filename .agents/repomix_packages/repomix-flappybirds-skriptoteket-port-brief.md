# Flappy Birds -> Skriptoteket Port Planning Brief

## Purpose

This repomix package is for architecture planning, not direct implementation.

It bundles:

- the upstream `trilogy-group/flappybirds` TypeScript game snapshot
- Skriptoteket's curated-app platform seams
- the current competitive-games architecture and backlog
- the existing `Flunk-Out Frenzy` browser-runtime implementation as the closest
  in-repo analogue

The planning goal is to decide how `Flappy Birds` should be ported into
Skriptoteket as a first-class curated game app while staying compatible with:

- bespoke curated-app routing and typed app APIs
- the existing SPA stack and current game/runtime libraries
- future shared global high-score mechanics

## Governing Assumptions

Treat these as fixed product direction for this package:

- `Flappy Birds` ships as `games.flappy_birds` from day one.
- It is a bespoke curated app, not a detached runtime experiment.
- It follows the already-accepted competitive-games model:
  browser-owned live simulation plus backend-owned competition state.
- `Flunk-Out Frenzy` is the first consumer of that pattern, not a special
  exception.
- Delivery should follow the existing programme order:
  local playable app first, shared competition plumbing second, official score
  support third.
- High scores are a lightweight teacher-fun feature, not a real audit-heavy
  esports system. Do not overdesign replay review, moderation, or forensic
  validation for this port.

## Upstream Snapshot

- Source repo: `https://github.com/trilogy-group/flappybirds`
- Local snapshot path: `.artifacts/upstream/flappybirds/`
- Snapshot commit: `e9634866ac0b276af37f17d128e271d289c27844`

## Questions This Package Should Answer

1. Which upstream parts are worth preserving as authored gameplay semantics:
   entity model, difficulty tuning, power-up semantics, asset layout, input
   scheme, local score loop?
2. Which parts should be rewritten onto Skriptoteket-native seams:
   route shell, auth-gated bootstrap, profile-aware identity, leaderboard UX,
   score submission, and app-specific API contracts?
3. Should the port keep upstream raw Canvas/Web Audio patterns behind adapters,
   or should it move directly onto the current Skriptoteket game shell pattern
   with `Pixi` and `Howler`, while avoiding unnecessary `Rapier` adoption for a
   simple arcade loop?
4. What shared `competitive_play` abstractions should be introduced so both
   `Flunk-Out Frenzy` and a future `Flappy Birds` app can submit scores and
   query global leaderboards without one-off persistence logic?
5. What is the lightest credible score-submission model that preserves
   cross-game consistency without turning fun teacher leaderboards into a heavy
   audit product?

## Important Current-State Reality

- Skriptoteket already has accepted architecture for competitive curated games,
  including pending -> official score promotion, `ruleset_id`, optional
  `season_id`, and display-name-based leaderboard identity.
- Skriptoteket does **not** yet have the shared `competitive_play` bounded
  context implemented in code. That work is planned in `ST-25-03` and
  `ST-25-04`.
- `Flunk-Out Frenzy` already proves the intended browser-owned runtime plus
  backend-owned competition split and shows the current frontend game-library
  direction.
- The repo backlog still frames replay validation and promotion more strongly
  than this product needs for a casual teacher leaderboard. For this package,
  treat those heavier ideas as background context, not as a requirement to
  reproduce in full for `Flappy Birds` v1.

## Suggested Reading Order

1. Architecture rules and ADRs
2. Competitive-games reference and backlog
3. Current Skriptoteket curated-app seams
4. Existing `Flunk-Out Frenzy` shell/runtime code
5. Upstream `flappybirds` code snapshot

## What To Pay Attention To

- `Flappy Birds` currently owns local storage, DOM-managed screens, raw canvas,
  and local high score handling.
- Skriptoteket wants auth-gated curated app routes, typed bootstrap, browser
  runtime isolation, and future server-owned official leaderboard state.
- Preserve gameplay semantics, not the donor shell. The likely port is an
  adapter/rebuild around Skriptoteket-native route, bootstrap, HUD, and score
  seams rather than a direct transplant of `Game.ts`.
- Prefer the current curated-game shell pattern:
  lazy runtime loading, imperative host lifecycle, and read-only HUD snapshots
  flowing back to Vue.
- Reuse `Pixi` for rendering and `Howler` for audio unless the architect finds
  a strong reason not to. `Rapier` should be considered optional for this app,
  not mandatory.
- The likely porting center of gravity is not a literal transplant; it is an
  adapter or rewrite that preserves game semantics while moving shell, identity,
  persistence, and competition mechanics onto Skriptoteket-native boundaries.
- Keep client storage for non-authoritative preferences such as bird color if
  useful, but treat any local best score as local-only. Official/global boards
  still belong to backend-owned app-specific endpoints.
- Library reuse is allowed to evolve. The package includes the current SPA/game
  dependencies specifically so the architect can judge whether to:
  keep upstream rendering/input patterns,
  port onto the existing `Flunk-Out Frenzy` runtime substrate,
  or define a slightly broader reusable browser-game substrate for multiple
  curated games.

## Lightweight Competition Guidance

Design the leaderboard path as a fun, low-stakes feature:

- Keep `app_id`, `app_version`, and `ruleset_id` from day one so future balance
  changes do not corrupt one shared board.
- Use app-specific endpoints and backend-owned score rows, but keep the
  integrity model proportionate.
- Prefer lightweight run summaries and compact replay or input-log data that
  support debugging or future iteration if cheap, not a full audit trail.
- Avoid designing for manual review, anti-cheat operations, or real-world score
  disputes unless the product direction changes later.
