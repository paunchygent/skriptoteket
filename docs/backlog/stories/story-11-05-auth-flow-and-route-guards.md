---
type: story
id: ST-11-05
title: "Auth flow + route guards"
status: done
owners: "agents"
created: 2025-12-21
epic: "EPIC-11"
acceptance_criteria:
  - "Given an unauthenticated user visits a protected route, when the SPA loads, then it navigates to /login and preserves the intended destination"
  - "Given a user logs in and receives a session cookie, when navigating to protected routes, then the SPA renders the correct view and role-gated navigation items"
ui_impact: "Replaces server-rendered login/logout pages with SPA equivalents while preserving roles."
dependencies: ["ADR-0009", "ADR-0030"]
---

## Context

The SPA must implement the session + CSRF flow and enforce role guards consistent with backend dependencies.

## Implemented (2025-12-21)

- Pinia auth store (session bootstrap + CSRF): `frontend/apps/skriptoteket/src/stores/auth.ts`
- SPA API client wrapper (credentials + CSRF injection + error envelope + clears auth on 401): `frontend/apps/skriptoteket/src/api/client.ts`
- Router guards + protected routes: `frontend/apps/skriptoteket/src/router/index.ts`, `frontend/apps/skriptoteket/src/router/routes.ts`
  - Role too low redirects to `/forbidden` with context in query params.
- UI wiring:
  - Login form: `frontend/apps/skriptoteket/src/views/LoginView.vue`
  - Role-gated nav + logout + auto-redirect to `/login?next=...` if auth is cleared while on a protected route: `frontend/apps/skriptoteket/src/App.vue`
  - Placeholder guarded routes: `/my-tools` (contributor+), `/admin/tools` (admin+)

## Verify

- `pdm run lint`
- `pdm run typecheck`
- `pdm run docs-validate`
- `pnpm -C frontend --filter @skriptoteket/spa typecheck`
- `pdm run fe-type-check-islands`
- `pdm run pytest tests/unit/web/test_api_v1_auth_and_csrf_routes.py`
- Live check (SPA auth): ran Vite dev server and validated redirects + login/logout + role-gated nav with Playwright.

## Verified (2025-12-22)

- All static checks passed (lint, typecheck, docs-validate, SPA typecheck, islands typecheck)
- Unit tests: 9 passed (`test_api_v1_auth_and_csrf_routes.py`)
- Backend auth API: login/me/csrf/logout+CSRF verified via curl
- SPA manual tests: unauthenticated→/login?next=, post-login lands on next, logout→/, 401-clear-to-login
- Role-gating with `user` account (`test-user@local.dev`): nav links hidden, /admin/tools→/forbidden?required=admin, /my-tools→/forbidden?required=contributor
