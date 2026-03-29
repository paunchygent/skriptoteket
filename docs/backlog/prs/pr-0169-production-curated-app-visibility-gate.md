---
type: pr
id: PR-0169
title: "Production curated app visibility gate"
status: done
owners: "agents"
created: 2026-03-30
updated: 2026-03-30
stories:
  - "ST-09-06"
tags: ["backend", "curated-apps", "security", "ops"]
acceptance_criteria:
  - "The backend registry reads a production-only curated app allowlist from config and excludes non-approved curated apps when `ENVIRONMENT=production`."
  - "Production-hidden curated apps are absent from catalog/discoverability, generic app detail lookup, and app-specific bootstrap/access paths because they no longer resolve from the registry."
  - "Legacy favorites/recent-run surfaces tolerate missing registry entries and do not leak production-hidden curated apps."
  - "Focused automated tests cover production filtering and non-production retention for the affected curated apps."
---

## Problem

Curated app registration is currently environment-agnostic. That is convenient
for local development, but it is too permissive for deployed production: any
app registered for local/demo work is also visible to production discovery and
deep-link routes unless another surface remembers to hide it.

For the current release posture, production must not expose:

- `Interaktiv räknare (demo)` (`demo.counter`)
- `Flunk-Out Frenzy` (`games.flunk_out_frenzy`)

## Goal

Add a production-only curated app visibility gate in backend registry config so
production exposes only explicitly approved curated apps, while development and
test environments keep the full registry for verification.

## Non-goals

- Removing demo or in-development curated app code from the repo.
- Changing bespoke app implementations or frontend route components.
- Adding a new database-backed curated app registry.
- Reworking tool/script-bank seeding in this slice.

## Implementation plan

1. Add a config-backed production curated app allowlist to
   `src/skriptoteket/config.py`, with production-safe defaults.
2. Filter curated app registration in
   `src/skriptoteket/infrastructure/curated_apps/registry.py` when
   `ENVIRONMENT=production`.
3. Keep all registry consumers unchanged where possible so production gating
   automatically flows through:
   - catalog listing
   - `/api/v1/apps/{app_id}`
   - app-specific routes such as Flunk-Out Frenzy bootstrap
   - favorites and recent items
4. Add focused tests for:
   - production vs non-production registry contents
   - hidden-app omission on favorites/recent surfaces when legacy references
     remain
5. Update docs/handoff with the production-hardening intent and verification.

## Test plan

- `pdm run pytest tests/unit/infrastructure/curated_apps/test_registry.py tests/unit/application/favorites/handlers/test_list_favorites.py tests/unit/application/catalog/handlers/test_list_recent_tools.py tests/unit/web/test_apps_api_routes.py tests/unit/web/apps/flunk_out_frenzy/test_api.py -q`
- `pdm run docs-validate`
- Live functional check against the local app surface proving approved curated
  apps still resolve while the hidden production-only ids fail closed when the
  backend runs with `ENVIRONMENT=production`.

## Rollback plan

- Revert the registry/config changes and the focused tests.
- If production urgently needs one of the hidden curated apps, temporarily add
  its `app_id` back to the production allowlist rather than bypassing the gate
  in route code.
