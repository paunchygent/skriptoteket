---
type: epic
id: EPIC-25
title: "Curated app family: competitive games foundations and Pinball Teacher"
status: accepted
owners: "agents"
created: 2026-03-22
outcome: "Signed-in users can open Pinball Teacher as a bespoke curated app, play a polished local browser-based vertical slice inside the existing Skriptoteket SPA, and the platform has the backend seams required to add replay-backed official high scores without rewriting the app contract."
dependencies: ["ADR-0023", "ADR-0027", "ADR-0073"]
---

## Scope

- **Family architecture**: establish the competitive-games curated-app shape so
  future games can reuse the same competition backend seams.
- **Pinball Teacher app**: introduce the first game as a bespoke curated app
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

- [ ] [ST-25-01: Competitive games substrate and Pinball Teacher bootstrap contract](../stories/story-25-01-competitive-games-substrate-and-pinball-teacher-bootstrap-contract.md)
- [ ] [ST-25-02: Pinball Teacher local runtime vertical slice](../stories/story-25-02-pinball-teacher-local-runtime-vertical-slice.md)
- [ ] [ST-25-03: Competitive play pending score submission and typed leaderboards](../stories/story-25-03-competitive-play-pending-score-submission-and-typed-leaderboards.md)
- [ ] [ST-25-04: Competitive play replay validation and official score promotion](../stories/story-25-04-competitive-play-replay-validation-and-official-score-promotion.md)

## Notes

- **First implementation slice**: ST-25-01 and ST-25-02.
- **Planned from the start**: ST-25-03 and ST-25-04 define the competition path
  that the local slice must remain compatible with.
- Cross-cutting sequencing beyond this epic is tracked in
  `docs/reference/ref-competitive-games-cross-cutting-programme.md`.
