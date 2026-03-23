---
type: pr
id: PR-0094
title: "Flunk-Out Frenzy: curated app registration and discoverability"
status: done
owners: "agents"
created: 2026-03-22
updated: 2026-03-23
stories:
  - "ST-25-01"
tags: ["curated-apps", "backend", "catalog"]
acceptance_criteria:
  - "`games.flunk_out_frenzy` is present in the curated app registry with a deterministic curated-app `tool_id`."
  - "The app is registered as `ui_mode=bespoke_required` with display title `Flunk-Out Frenzy`."
  - "The app is discoverable through the existing curated-app/catalog surfaces using placements `gemensamt/ovrigt` and `larare/ovrigt`."
  - "`GET /api/v1/apps/games.flunk_out_frenzy` returns the expected app metadata and role gate."
---

## Problem

`ST-25-01` starts with the platform seam: Flunk-Out Frenzy must exist as a
real bespoke curated app before any frontend shell or runtime work can be
meaningfully attached to it.

Right now the app does not exist in the curated app registry, so it has no
stable `app_id`, no deterministic `tool_id`, and no discoverability through the
existing curated-app/catalog surfaces.

## Goal

Register Flunk-Out Frenzy as a first-class curated app in the existing
Skriptoteket registry and prove that it behaves like other bespoke curated apps
with respect to:

- app identity
- role gating
- catalog discoverability
- generic app detail lookup

## Non-goals

- No bespoke SPA view yet.
- No bootstrap endpoint yet.
- No gameplay/runtime code.
- No games-specific portal or alternative discovery surface.

## Implementation plan

- Add a curated app entry in
  `src/skriptoteket/infrastructure/curated_apps/registry.py`:
  - `app_id="games.flunk_out_frenzy"`
  - title `Flunk-Out Frenzy`
  - `ui_mode=CuratedAppUiMode.BESPOKE_REQUIRED`
  - placements:
    - `gemensamt/ovrigt`
    - `larare/ovrigt`
- Reuse the existing deterministic `curated_app_tool_id(app_id=...)` model.
- Ensure the existing curated app detail API in
  `src/skriptoteket/web/api/v1/apps.py` exposes the new app correctly without
  adding any new list endpoint.
- Add or extend tests around:
  - curated app registry identity
  - app detail lookup
  - catalog discoverability through existing curated-app surfaces

## Test plan

Automated:

- backend/unit tests for curated app registry contents
- API tests for `GET /api/v1/apps/games.flunk_out_frenzy`
- catalog/discoverability tests proving the app appears through existing
  curated-app placements

Suggested commands:

```bash
pdm run pytest tests/unit/application/catalog tests/unit/web -q
pdm run ruff check src/skriptoteket/infrastructure/curated_apps/registry.py src/skriptoteket/web/api/v1/apps.py tests/unit
pdm run mypy src/skriptoteket/infrastructure/curated_apps/registry.py src/skriptoteket/web/api/v1/apps.py
```

## Rollback plan

- Remove the curated app registry entry for `games.flunk_out_frenzy`.
- Remove any focused tests that assume the app exists.
- No schema or persisted data rollback is required in this PR.
