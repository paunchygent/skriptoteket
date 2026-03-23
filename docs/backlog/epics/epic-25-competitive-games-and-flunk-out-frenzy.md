---
type: epic
id: EPIC-25
title: "Curated app family: competitive games foundations and Flunk-Out Frenzy"
status: active
owners: "agents"
created: 2026-03-22
updated: 2026-03-23
outcome: "Signed-in users can open Flunk-Out Frenzy as a bespoke curated app, play a polished local browser-based vertical slice inside the existing Skriptoteket SPA, and the platform has the backend seams required to add official high scores without rewriting the app contract."
dependencies: ["ADR-0023", "ADR-0027", "ADR-0073"]
---

## Scope

- **Family architecture**: establish the competitive-games curated-app shape so
  future games can reuse the same competition backend seams.
- **Flunk-Out Frenzy app**: introduce the first game as a bespoke curated app
  under the existing app host.
- **Frontend runtime**: keep live simulation browser-owned and isolated from the
  generic tool-run/session UI model.
- **Backend substrate**: reserve the models and API contracts needed for pending
  score submission, official score promotion, replay metadata, and leaderboard
  queries.

## Out of scope

- Multiple game apps shipping in the same slice
- Tournament administration
- Social graph or chat
- Mobile-first controls
- Real-time multiplayer
- Redis/WebSocket infrastructure as a hard requirement

## Risks

- The first game could accidentally couple itself to one-off persistence paths.
- A weak replay/score contract could make later official score support expensive
  to add safely.
- The frontend could drift into Vue-owned simulation state if the shell/runtime
  boundary is not enforced.

## Stories

- [x] [ST-25-01: Competitive games substrate and Flunk-Out Frenzy bootstrap contract](../stories/story-25-01-competitive-games-substrate-and-flunk-out-frenzy-bootstrap-contract.md)
- [x] [ST-25-02: Flunk-Out Frenzy local runtime vertical slice](../stories/story-25-02-flunk-out-frenzy-local-runtime-vertical-slice.md)
- [ ] [ST-25-03: Competitive play pending score submission and typed leaderboards](../stories/story-25-03-competitive-play-pending-score-submission-and-typed-leaderboards.md)
- [ ] [ST-25-04: Competitive play replay validation and official score promotion](../stories/story-25-04-competitive-play-replay-validation-and-official-score-promotion.md)

## Notes

- **First implementation slice**: ST-25-01 and ST-25-02.
- **Planned from the start**: ST-25-03 and ST-25-04 define the competition path
  that the local slice must remain compatible with.
- Cross-cutting sequencing beyond this epic is tracked in
  `docs/reference/ref-competitive-games-cross-cutting-programme.md`.

## Implementation Summary (as of 2026-03-23)

- `ST-25-01` shipped the Flunk-Out Frenzy curated-app registration,
  discoverability, bespoke route resolution, and minimal typed bootstrap
  contract.
- `ST-25-02` shipped the immersive game-first shell, runtime/core boundary,
  Rapier-backed prototype-alpha physics/rules, and the first playable local
  Pixi/Howler 3-ball slice with verified pause/restart/mute and route disposal.
