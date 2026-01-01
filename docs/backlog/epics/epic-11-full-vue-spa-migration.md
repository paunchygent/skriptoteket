---
type: epic
id: EPIC-11
title: "Full Vue/Vite SPA migration"
status: done
owners: "agents"
created: 2025-12-21
outcome: "Skriptoteket runs as a single Vue/Vite SPA for all routes (user + admin), backed by /api/v1 with generated TypeScript types, with legacy Jinja2/HTMX removed."
---

## Scope

- Replace the server-rendered Jinja2/HTMX UI with a single Vue 3 / Vite SPA (ADR-0027).
- Frontend workspace:
  - `frontend/apps/skriptoteket` (SPA)
  - `frontend/packages/huleedu-ui` (component library + design tokens; Tailwind 4 with @theme; ADR-0032)
- Backend API:
  - `/api/v1/*` endpoints for SPA consumption
  - OpenAPI schema as source of truth + generated TS types (`openapi-typescript`; ADR-0030)
- Hosting:
  - SPA built assets served by FastAPI with history fallback routing (ADR-0028)
- Route parity for all roles: user, contributor, admin, superuser.

## Out of scope

- Long-term coexistence of SSR and SPA (cutover is a clean replacement).
- Allowing tool-provided UI JavaScript (typed UI contract remains the boundary).

## Stories

### Phase 1: Foundation (done)
- [ST-11-01: Frontend workspace + SPA scaffold](../stories/story-11-01-frontend-workspace-and-spa-scaffold.md)
- [ST-11-02: UI library + design tokens (pure CSS)](../stories/story-11-02-ui-library-and-design-tokens.md)
- [ST-11-03: Serve SPA from FastAPI (manifest + history fallback)](../stories/story-11-03-spa-hosting-fastapi-integration.md)
- [ST-11-04: API v1 conventions + OpenAPI → TypeScript generation](../stories/story-11-04-api-v1-and-openapi-typescript.md)
- [ST-11-05: Auth flow + route guards](../stories/story-11-05-auth-flow-and-route-guards.md)

### Phase 2: User-facing views (done)
- [ST-11-06: Catalog browse views (professions/categories/tools)](../stories/story-11-06-spa-browse-views.md)
- [ST-11-07: Tool run + results (uploads, artifacts, typed outputs)](../stories/story-11-07-tool-run-and-results.md)
- [ST-11-08: My runs list + detail](../stories/story-11-08-my-runs-views.md)
- [ST-11-09: Curated apps views (`/apps/:app_id`)](../stories/story-11-09-curated-apps-views.md)

### Phase 3: Contributor/admin views (done)
- [ST-11-10: Suggestions flows (contributor + admin review)](../stories/story-11-10-suggestions-flows.md)
- [ST-11-11: Admin tools list + publish/depublish](../stories/story-11-11-admin-tools-management.md)
- [ST-11-12: Script editor migration (CodeMirror 6)](../stories/story-11-12-script-editor-migration.md)

### Phase 4: Remaining features (done)
- [ST-11-15: My Tools view (contributor dashboard)](../stories/story-11-15-my-tools-view.md)
- [ST-11-16: Editor workflow actions (review, publish, reject)](../stories/story-11-16-editor-workflow-actions.md)
- [ST-11-17: Tool metadata editor (title, summary, tags)](../stories/story-11-17-tool-metadata-editor.md)
- [ST-11-18: Maintainer management (add/remove contributors)](../stories/story-11-18-maintainer-management.md)
- [ST-11-19: Help framework (contextual help panel)](../stories/story-11-19-help-framework.md)

### Phase 5: Cutover (done)
- [ST-11-13: Cutover + deletion + E2E](../stories/story-11-13-cutover-and-e2e.md) (done)

### Post-cutover follow-ups
- [ST-11-20: Tool taxonomy editor (professions + categories)](../stories/story-11-20-tool-taxonomy-editor.md) (done)
- [ST-11-21: Unified landing page (auth-adaptive home view)](../stories/story-11-21-unified-landing-page.md) (done)
- [ST-11-22: Remove /login route (modal-only login)](../stories/story-11-22-remove-login-route.md) (done)
- [ST-11-23: Tool owner + maintainer permission hardening](../stories/story-11-23-tool-owner-and-maintainer-permissions.md) (done)

## Implementation Summary (as of 2026-01-01)

- Full SPA cutover complete; legacy SSR/HTMX routes removed and FastAPI serves built SPA with history fallback.
- API v1 + OpenAPI-to-TypeScript types are the source of truth for SPA integration.
- Route parity delivered across user, contributor, admin, and superuser flows (browse, run, my-runs, my-tools, editor).

## Risks

- Cutover risk (mitigate with route parity + Playwright E2E before deletion).
- Auth/session edge cases (mitigate with clear 401/403 handling + CSRF contract; ADR-0030).
- Bundle/perf regressions (mitigate with route-based code splitting and size budgets).
- API/frontend drift (mitigate with OpenAPI → generated types; ADR-0030).

## Dependencies

- PRD-spa-frontend-v0.1
- ADR-0027 (full SPA)
- ADR-0028 (hosting + routing)
- ADR-0032 (Tailwind 4 with @theme design tokens; supersedes ADR-0029)
- ADR-0030 (OpenAPI + generated TS)
