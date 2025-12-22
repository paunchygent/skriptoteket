---
type: story
id: ST-11-04
title: "API v1 conventions + OpenAPI → TypeScript generation"
status: done
owners: "agents"
created: 2025-12-21
epic: "EPIC-11"
acceptance_criteria:
  - "Given /api/v1 endpoints are implemented, when inspecting the OpenAPI schema, then request/response models are documented and stable under /api/v1"
  - "Given a developer runs the type generation command, when the SPA is built, then it imports the generated types without hand-written API DTO drift"
ui_impact: "Stabilizes SPA/backend contracts and prevents schema drift."
dependencies: ["ADR-0030"]
---

## Context

We want the backend OpenAPI schema to be the source of truth for all SPA DTOs, validated in CI.

## Implemented (2025-12-21)

- Migrated legacy JSON routes from `/api/*` → `/api/v1/*` and enforced CSRF on `POST`s:
  - `src/skriptoteket/web/routes/interactive_tools.py` (`/api/v1/start_action`, `/api/v1/runs/*`, `/api/v1/tools/*/sessions/*`)
  - `src/skriptoteket/web/routes/editor.py` (`/api/v1/editor/*`)
  - `src/skriptoteket/web/auth/api_dependencies.py` (API auth + CSRF deps)
  - `frontend/islands/src/runtime/RuntimeIslandApp.vue`, `frontend/islands/src/editor/EditorIslandApp.vue` (updated paths + `X-CSRF-Token`)
- Added API v1 auth endpoints:
  - `src/skriptoteket/web/api/v1/auth.py` (`/api/v1/auth/login|logout|me|csrf`)
  - `src/skriptoteket/web/router.py` mounts API v1 routers outside the redirecting protected router.
- OpenAPI export + TypeScript generation:
  - `scripts/export_openapi_v1.py` writes a filtered schema (only `/api/v1/*`) to `frontend/apps/skriptoteket/openapi.json` (gitignored).
  - `frontend/apps/skriptoteket/package.json` adds `gen:api-types` and `openapi-typescript`.
  - Generated types are committed at `frontend/apps/skriptoteket/src/api/openapi.d.ts` and imported via `frontend/apps/skriptoteket/src/api/types.ts`.
  - Convenience command: `pdm run fe-gen-api-types`.

## Verify

- `pdm run fe-gen-api-types`
- `pnpm -C frontend --filter @skriptoteket/spa typecheck`
- `pdm run pytest tests/unit/web/test_api_v1_auth_and_csrf_routes.py`

## Verified (2025-12-22)

- All static checks passed (lint, typecheck, docs-validate, SPA typecheck)
- Unit tests: 9 passed (`test_api_v1_auth_and_csrf_routes.py`)
- API v1 auth endpoints verified via curl (login/me/csrf/logout with CSRF)
