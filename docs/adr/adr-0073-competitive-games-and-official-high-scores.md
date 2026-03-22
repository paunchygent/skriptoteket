---
type: adr
id: ADR-0073
title: "Competitive browser games as bespoke curated apps with official high-score validation"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2026-03-22
links: ["ADR-0023", "ADR-0027", "EPIC-25", "REF-curated-app-pinball-teacher-architecture-and-foundational-code"]
---

## Context

Skriptoteket already supports curated apps as first-class application modules
with bespoke SPA views and app-specific API surfaces.

We now want to introduce a small family of **competitive browser games** that:

- run as signed-in curated apps inside the existing SPA
- remain fun and responsive during live play
- support trusted global high scores over time
- do not force the browser runtime through the generic tool-run/session UI model

The existing curated-app platform contracts are a strong base, but browser games
introduce a new tension:

- live simulation wants a local browser-owned loop
- competition features want durable backend-owned validation and persistence

We need an explicit architecture that keeps those concerns separate from the
start so the first game can ship locally without later rewriting the app family
to add official score support.

## Decision

### 1. Competitive games are bespoke curated apps

Competitive games SHALL be implemented as curated apps with
`ui_mode=bespoke_required`.

They SHALL:

- register in the curated app registry
- render through the SPA app host under `/apps/:appId`
- expose app-specific typed endpoints under `/api/v1/apps/{app_id}/...`

They SHALL NOT use the generic `AppDetailView` or generic tool action renderer
as the primary UX for live play.

### 2. The browser runtime owns live simulation

For game apps, the frontend runtime SHALL own:

- fixed-step simulation
- input processing
- rendering
- audio
- deterministic gameplay rules during a live run

The backend SHALL NOT be the source of truth for frame-by-frame machine state.

`tool_sessions`, `ui_payload`, and generic run-state orchestration MAY still be
used as internal support primitives, but they SHALL NOT be the primary contract
for the live gameplay loop.

### 3. The backend owns durable competition state

The backend SHALL own:

- app bootstrap metadata
- identity and authorization checks
- pending score submissions
- replay metadata and storage references
- official score promotion
- leaderboard queries

This logic SHALL live in a shared backend subsystem for competitive play rather
than being embedded ad hoc inside one game's web router.

### 4. Introduce a shared `competitive_play` bounded context

Skriptoteket SHALL add a reusable backend subsystem responsible for:

- score submission lifecycle (`pending`, `official`, `rejected`)
- replay-backed validation workflows
- leaderboard scoping
- player-facing leaderboard read models

This subsystem SHALL be reusable across future curated game apps.

### 5. Scope official scores by app and ruleset

Score records SHALL include at minimum:

- `app_id`
- `app_version`
- `ruleset_id`
- owner user id
- score value
- replay asset reference or equivalent replay metadata

The design MAY also include `season_id` when needed.

Official leaderboard queries SHALL scope by app and ruleset, and SHALL NOT
merge incompatible runs across rule changes.

### 6. Use a pending-to-official promotion pipeline

The competition flow SHALL be:

1. the browser completes a local run
2. the client submits a score summary plus replay payload/reference
3. the backend stores a **pending** submission
4. replay validation promotes valid submissions to **official**
5. official leaderboards show only promoted scores

Rejected submissions SHALL retain a reason for auditability and user-facing
error handling.

### 7. Storage choice

PostgreSQL SHALL be the source of truth for:

- score submissions
- official scores
- replay metadata
- leaderboard indexes and queries

Redis SHALL be optional and used only as an optimization for:

- cached leaderboard pages
- rate limiting
- live fan-out, if later required

Redis is not a prerequisite for the first local slice or the first trustworthy
leaderboard slice.

### 8. Identity and public display

Competitive games SHALL use the existing Skriptoteket user/session model.

Leaderboards SHALL NOT expose user email addresses.

Initial public display SHOULD use `UserProfile.display_name`; a dedicated public
alias remains a future enhancement if needed.

## Consequences

### Benefits

- Keeps game feel strong by avoiding server-owned live simulation.
- Preserves curated-app architecture instead of inventing a parallel product.
- Makes official high scores trustworthy without forcing high-latency gameplay.
- Creates a reusable competitive-play backend for future game apps.

### Tradeoffs

- Introduces a new shared bounded context that needs clear ownership.
- Requires explicit replay-format and validation-policy decisions.
- Adds product complexity around ruleset/version scope and score lifecycle.

### Risks

- If we let the first game persist too little metadata, later officialization
  may require migration or invalidating early runs.
- If we overfit the shared subsystem to Pinball Teacher, future games may not
  fit cleanly.
- If we prematurely require Redis/WebSockets, the first slice may become heavier
  than necessary.

### Mitigations

- Reserve `ruleset_id` from the first score-capable slice.
- Keep replay validation and leaderboard logic app-agnostic.
- Ship local play first, then layer pending submission and promotion on top.
