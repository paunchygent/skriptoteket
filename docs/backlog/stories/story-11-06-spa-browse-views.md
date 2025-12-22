---
type: story
id: ST-11-06
title: "Catalog browse views (professions/categories/tools)"
status: done
owners: "agents"
created: 2025-12-21
epic: "EPIC-11"
acceptance_criteria:
  - "Given an authenticated user, when visiting /browse, then the SPA lists professions from /api/v1/catalog/professions"
  - "Given a user selects a profession and category, when visiting /browse/:profession/:category, then the SPA lists tools with the same results as the legacy templates"
ui_impact: "Migrates the core browse/catalog experience to the SPA."
dependencies: ["ST-11-04", "ST-11-05"]
---

## Context

Browse flows are the main entry point for users. These must reach parity early to validate the migration approach.

## Implementation (2025-12-22)

### Phase 1: Catalog API (completed earlier)

Created three RESTful catalog endpoints:

- `GET /api/v1/catalog/professions` - Lists all professions
- `GET /api/v1/catalog/professions/{slug}/categories` - Lists categories for a profession
- `GET /api/v1/catalog/professions/{slug}/categories/{slug}/tools` - Lists tools and curated apps

Files: `src/skriptoteket/web/api/v1/catalog.py`, TypeScript types regenerated in `frontend/apps/skriptoteket/src/api/openapi.d.ts`.

### Phase 2: Frontend Views (completed)

Updated Vue router and created three browse views:

**Routes** (`frontend/apps/skriptoteket/src/router/routes.ts`):

- `/browse` -> `BrowseProfessionsView.vue`
- `/browse/:profession` -> `BrowseCategoriesView.vue`
- `/browse/:profession/:category` -> `BrowseToolsView.vue`

All routes have `meta: { requiresAuth: true }`.

**Views created**:

- `BrowseProfessionsView.vue` - Lists professions with navigation links
- `BrowseCategoriesView.vue` - Lists categories for selected profession with breadcrumb navigation
- `BrowseToolsView.vue` - Lists tools and curated apps with action buttons ("Koer" for tools, "Oeppna" for apps)

**Styling**: Pure CSS with HuleEdu design tokens (ADR-0029, now superseded by ADR-0032 Tailwind 4), scoped styles, responsive mobile layout. Note: These views use the pre-Tailwind pattern; future views should use Tailwind utilities.

**Decisions made**:

1. API structure: Three RESTful endpoints (Option A)
2. Vue routes: Child routes under `/browse` (Option A)
3. State management: Local component state, no Pinia store (Option A, YAGNI)

### Verification

- `pdm run lint` - All checks passed
- `pdm run typecheck` - 299 files, no issues
- `pdm run docs-validate` - Passed
- `pnpm -C frontend --filter @skriptoteket/spa typecheck` - Passed

### Live Functional Check (2025-12-22)

Verified via Playwright automation:

1. `/browse` (unauthenticated) -> Redirects to `/login?next=/browse`
2. Login with `superuser@local.dev` -> Redirects to `/browse`
3. `/browse` -> Lists 5 professions (Larare, Specialpedagog, Skoladministrator, Rektor, Gemensamt)
4. Click "Larare" -> `/browse/larare` -> Lists 4 categories with breadcrumb
5. Click "Lektionsplanering" -> `/browse/larare/lektionsplanering` -> Lists tools
6. `/browse/gemensamt/ovrigt` -> Shows "Kurerade appar" section with demo.counter app

Screenshots saved: `.artifacts/st-11-06-professions.png`, `st-11-06-categories.png`, `st-11-06-curated.png`

**Note**: Fixed router base path (`createWebHistory(import.meta.env.BASE_URL)`) and Vite proxy config to exclude `/static/spa` from backend proxy during dev.
