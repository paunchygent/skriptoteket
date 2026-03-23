---
type: pr
id: PR-0096
title: "Flunk-Out Frenzy: minimal bootstrap contract"
status: done
owners: "agents"
created: 2026-03-22
updated: 2026-03-23
stories:
  - "ST-25-01"
tags: ["curated-apps", "backend", "frontend", "api"]
dependencies:
  - "PR-0094"
  - "PR-0095"
acceptance_criteria:
  - "`GET /api/v1/apps/games.flunk_out_frenzy/bootstrap` returns a typed app-specific bootstrap payload."
  - "The bootstrap payload remains minimal and contains only app metadata, feature flags, and a manual semantic `ruleset_id`."
  - "The initial `ruleset_id` is an explicit semantic constant rather than a hash-derived value."
  - "The bespoke shell view loads the bootstrap payload and renders its top-level states without introducing generic `start_action` or `tool_sessions` orchestration."
---

## Problem

`ST-25-01` requires more than registration and route wiring. The app also needs
an app-specific bootstrap contract so the SPA can load a stable, minimal game
entry payload without leaning on the generic tool-run/session flow.

## Goal

Introduce the first Flunk-Out Frenzy app-specific API contract:

- one minimal typed bootstrap endpoint
- one app-specific backend use case/handler
- one frontend shell integration that consumes the bootstrap and renders
  loading/error/ready states

## Non-goals

- No gameplay runtime yet.
- No runtime asset manifest or physics config in the bootstrap payload.
- No score submission or leaderboard APIs yet.
- No replay persistence yet.

## Implementation plan

- Add an app-specific bootstrap handler/use case under
  `src/skriptoteket/application/curated_apps/flunk_out_frenzy/`.
- Add an app-specific router:
  - `src/skriptoteket/web/api/v1/apps_flunk_out_frenzy.py`
- Expose:
  - `GET /api/v1/apps/games.flunk_out_frenzy/bootstrap`
- Keep the payload intentionally minimal. Recommended fields:
  - `app_id`
  - `title`
  - `summary`
  - `app_version`
  - `ruleset_id`
  - `feature_flags`
    - `audio_enabled`
    - `replay_capture_enabled`
    - `score_submission_enabled`
- Set the initial `ruleset_id` as a manual semantic constant such as
  `flunk_out_frenzy.prototype_alpha.v1`.
- Update `FlunkOutFrenzyView.vue` to fetch and render bootstrap state.
- Keep all bootstrap logic app-specific; do not introduce a new generic
  bootstrap framework in this PR.

## Test plan

Automated:

- backend API tests for the bootstrap endpoint
- backend handler tests for payload shape and access gating
- frontend tests for bootstrap loading/error/ready rendering

Manual/live:

- run local backend + SPA
- open `/apps/games.flunk_out_frenzy`
- verify shell loads bootstrap and reaches ready state

Suggested commands:

```bash
pdm run pytest tests/unit/web -q
pdm run ruff check src/skriptoteket/application/curated_apps/flunk_out_frenzy src/skriptoteket/web/api/v1/apps_flunk_out_frenzy.py tests/unit
pdm run mypy src/skriptoteket/application/curated_apps/flunk_out_frenzy src/skriptoteket/web/api/v1/apps_flunk_out_frenzy.py

pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/FlunkOutFrenzyView.spec.ts
pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/FlunkOutFrenzyView.vue src/views/apps/FlunkOutFrenzyView.spec.ts
pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit
pnpm -C frontend --filter @skriptoteket/spa build

pdm run docs-validate
```

## Rollback plan

- Remove the app-specific bootstrap handler and router.
- Remove bootstrap loading from `FlunkOutFrenzyView.vue`.
- Keep the curated app registration and bespoke route shell in place if desired.
