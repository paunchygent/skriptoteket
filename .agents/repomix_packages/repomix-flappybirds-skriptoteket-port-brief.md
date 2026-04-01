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

## Upstream Snapshot

- Source repo: `https://github.com/trilogy-group/flappybirds`
- Local snapshot path: `.artifacts/upstream/flappybirds/`
- Snapshot commit: `e9634866ac0b276af37f17d128e271d289c27844`

## Questions This Package Should Answer

1. Should `Flappy Birds` become a new curated app such as
   `games.flappy_birds`, or should it be treated as a runtime/library exercise
   within the competitive-games family first?
2. Which upstream parts are worth preserving as-is:
   entity model, difficulty tuning, power-up semantics, asset layout, input
   scheme, local score loop?
3. Which parts should be rewritten onto Skriptoteket-native seams:
   route shell, auth-gated bootstrap, profile-aware identity, leaderboard UX,
   replay/score submission, and app-specific API contracts?
4. Should the port keep upstream raw Canvas/Web Audio patterns behind adapters,
   or should it move directly onto the current Skriptoteket game stack
   (`Pixi`, `Rapier`, `Howler`) even if those libraries need extension?
5. What shared `competitive_play` abstractions should be introduced so both
   `Flunk-Out Frenzy` and a future `Flappy Birds` app can submit scores and
   query global leaderboards without one-off persistence logic?

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
- The likely porting center of gravity is not a literal transplant; it is an
  adapter or rewrite that preserves game semantics while moving shell, identity,
  persistence, and competition mechanics onto Skriptoteket-native boundaries.
- Library reuse is allowed to evolve. The package includes the current SPA/game
  dependencies specifically so the architect can judge whether to:
  keep upstream rendering/input patterns,
  port onto the existing `Flunk-Out Frenzy` runtime substrate,
  or define a slightly broader reusable browser-game substrate for multiple
  curated games.
