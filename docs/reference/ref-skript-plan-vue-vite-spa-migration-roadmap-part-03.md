---
type: reference
id: REF-SKRIPT-PLAN-vue-vite-spa-migration-roadmap-PART-03
title: Vue/Vite SPA Migration Roadmap — part 03
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: REF-SKRIPT-PLAN-vue-vite-spa-migration-roadmap
part: 3
---

| Vue Route | Current HTML Route | Auth |
|-----------|-------------------|------|
| `/` | `/` | require_user |
| `/browse` | `/browse` | require_user |
| `/browse/:profession` | `/browse/{profession}` | require_user |
| `/browse/:profession/:category` | `/browse/{profession}/{category}` | require_user |
| `/apps/:appId` | `/apps/{app_id}` | require_user |
| `/tools/:slug/run` | `/tools/{slug}/run` | require_user |
| `/my-runs` | (new) | require_user |
| `/my-runs/:id` | `/my-runs/{run_id}` | require_user |
| `/my-tools` | `/my-tools` | require_contributor |
| `/suggestions/new` | `/suggestions/new` | require_contributor |
| `/admin/tools` | `/admin/tools` | require_admin |
| `/admin/tools/:toolId` | `/admin/tools/{tool_id}` | require_contributor |
| `/admin/tool-versions/:versionId` | `/admin/tool-versions/{version_id}` | require_contributor |
| `/admin/suggestions` | `/admin/suggestions` | require_admin |
| `/admin/suggestions/:id` | `/admin/suggestions/{suggestion_id}` | require_admin |

### Phase 4: Backend API Layer

**Goal:** Add JSON endpoints for SPA consumption

**Files to create:**

- `src/skriptoteket/web/api/__init__.py`
- `src/skriptoteket/web/api/v1/__init__.py`
- `src/skriptoteket/web/api/v1/router.py`
- `src/skriptoteket/web/api/v1/auth.py`
- `src/skriptoteket/web/api/v1/catalog.py`
- `src/skriptoteket/web/api/v1/tools.py`
- `src/skriptoteket/web/api/v1/my_runs.py`
- `src/skriptoteket/web/api/v1/my_tools.py`
- `src/skriptoteket/web/api/v1/suggestions.py`
- `src/skriptoteket/web/api/v1/admin.py`

**Files to modify:**

- `src/skriptoteket/web/app.py` → Mount `/api/v1/` router

### Phase 5: Core Views

**Goal:** Implement main user-facing views

**Views to implement:**

1. `HomeView.vue` → Static welcome (uses shared primitives + tokens)
2. `ProfessionsView.vue` → GET `/api/v1/catalog/professions`
3. `CategoriesView.vue` → GET `/api/v1/catalog/professions/{slug}/categories`
4. `ToolsView.vue` → GET `/api/v1/catalog/professions/{slug}/categories/{cat}/tools`
5. `CuratedAppView.vue` → GET `/api/v1/catalog/apps/{app_id}` (plus interactive endpoints)
6. `RunToolView.vue` → POST `/api/v1/tools/{slug}/run` (multipart file upload)
7. `RunResultView.vue` → GET `/api/v1/runs/{run_id}`
8. `MyRunsView.vue` → GET `/api/v1/my-runs`
9. `RunDetailView.vue` → GET `/api/v1/my-runs/{run_id}`

### Phase 6: Contributor/Admin Views

**Goal:** Implement role-restricted views

**Views to implement:**

1. `MyToolsView.vue` → GET `/api/v1/my-tools`
2. `NewSuggestionView.vue` → POST `/api/v1/suggestions`
3. `AdminToolsView.vue` → GET `/api/v1/admin/tools`
4. `ScriptEditorView.vue` → Migrate from `EditorIslandApp.vue`
5. `SuggestionsQueueView.vue` → GET `/api/v1/admin/suggestions`
6. `SuggestionDetailView.vue` → GET + POST decision

### Phase 7: Testing & Deployment

**Goal:** E2E tests, production build, cutover

**Tasks:**

1. Playwright E2E tests for critical flows
2. Configure `vite build` output to `src/skriptoteket/web/static/spa/`
3. Add FastAPI catch-all route serving `index.html`
4. Update Docker build to run `pnpm build`
5. Test on staging environment
6. Cutover: Remove old template routes, keep API

### Backlog mapping (Docs-as-Code)

This roadmap is implemented as `EPIC-SKRIPT-11` and its stories:

- ST-11-01..02: frontend workspace + tokens/Tailwind bridge
- ST-11-03: serve SPA from FastAPI (manifest + history fallback)
- ST-11-04..05: API v1 + OpenAPI TS + auth/guards
- ST-11-06..12: SPA views for browse/tools/runs/apps/suggestions/admin/editor
- ST-11-13: cutover + deletion + Playwright E2E

Downstream note: EPIC-12 work beyond ST-12-01 is **blocked until ST-11-13** so user-facing UX is implemented once in
the SPA.

---

## Planning Stop Conditions

The source does not state separate planning stop conditions.
