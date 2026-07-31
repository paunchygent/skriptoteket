---
type: reference
id: REF-SKRIPT-PLAN-vue-vite-spa-migration-roadmap-PART-02
title: Vue/Vite SPA Migration Roadmap — part 02
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: REF-SKRIPT-PLAN-vue-vite-spa-migration-roadmap
part: 2
---

```text
src/skriptoteket/web/api/
├── __init__.py
└── v1/
    ├── __init__.py
    ├── router.py
    ├── auth.py
    ├── catalog.py
    ├── tools.py
    ├── my_runs.py
    ├── my_tools.py
    ├── suggestions.py
    └── admin.py
```

### Endpoint Mapping

#### Auth API

This report predates the HuleEdu browser-session cutover. Earlier local
browser-auth endpoint notes are superseded by the HuleEdu ceremony plus shared
session/CSRF surfaces; do not use this historical report as an auth
implementation guide.

#### Catalog API (`/api/v1/catalog/`)

| Endpoint | Method | Handler |
|----------|--------|---------|
| `/api/v1/catalog/professions` | GET | `ListProfessionsHandler` |
| `/api/v1/catalog/professions/{slug}/categories` | GET | `ListCategoriesForProfessionHandler` |
| `/api/v1/catalog/professions/{slug}/categories/{cat}/tools` | GET | `ListToolsByTagsHandler` |
| `/api/v1/catalog/apps/{app_id}` | GET | New: curated app detail (registry) |

#### Tools API (`/api/v1/tools/`)

| Endpoint | Method | Handler |
|----------|--------|---------|
| `/api/v1/tools/{slug}` | GET | New: returns tool details |
| `/api/v1/tools/{slug}/run` | POST | `RunActiveToolHandler` |

#### My Runs API (`/api/v1/my-runs/`)

| Endpoint | Method | Handler |
|----------|--------|---------|
| `/api/v1/my-runs` | GET | New: list user's runs |
| `/api/v1/my-runs/{run_id}` | GET | New: run detail for user |

#### Contributor API (`/api/v1/my-tools/`)

| Endpoint | Method | Handler |
|----------|--------|---------|
| `/api/v1/my-tools` | GET | `ListToolsForContributorHandler` |

#### Suggestions API (`/api/v1/suggestions/`)

| Endpoint | Method | Handler |
|----------|--------|---------|
| `/api/v1/suggestions` | POST | `SubmitSuggestionHandler` |

#### Admin API (`/api/v1/admin/`)

| Endpoint | Method | Handler |
|----------|--------|---------|
| `/api/v1/admin/tools` | GET | `ListToolsForAdminHandler` |
| `/api/v1/admin/tools/{id}` | GET | Composite (tool + versions) |
| `/api/v1/admin/tools/{id}/publish` | POST | `PublishToolHandler` |
| `/api/v1/admin/tools/{id}/depublish` | POST | `DepublishToolHandler` |
| `/api/v1/admin/suggestions` | GET | `ListSuggestionsForReviewHandler` |
| `/api/v1/admin/suggestions/{id}` | GET | New: suggestion detail for review |
| `/api/v1/admin/suggestions/{id}/decision` | POST | `DecideSuggestionHandler` |

**Keep existing (already migrated to v1):** `/api/v1/editor/*`, `/api/v1/start_action`, `/api/v1/runs/*`, `/api/v1/tools/{id}/sessions/*`

---

### Source: Critical Review Points

### Session Handling

SPA uses same httponly cookies. CSRF token flow:

1. Browser starts the HuleEdu-owned auth ceremony.
2. HuleEdu establishes the shared browser session and redirects back to
   Skriptoteket continuation.
3. Skriptoteket resolves the signed app context to a local projection.
4. The SPA fetches shared CSRF through the HuleEdu session contract when
   needed for mutating requests.

**Verify:** Requests use `credentials: 'include'`. Same-origin hosting (ADR-SKRIPT-0028) avoids CORS complexity.

### File Uploads

`RunToolView.vue` must support `multipart/form-data`:

```typescript
const formData = new FormData()
for (const file of files) formData.append('files', file) // multi-file contract (ST-12-01 / ADR-SKRIPT-0031)
await api.post(`/api/v1/tools/${slug}/run`, formData)
```

**Verify:** Backend expects `files: list[UploadFile]` and enforces per-file + total upload caps.

### Role Guards

Vue Router guards must match FastAPI dependencies:

| FastAPI | Vue Guard |
|---------|-----------|
| `require_user` | `isAuthenticated` |
| `require_contributor` | `hasRole(['contributor', 'admin', 'superuser'])` |
| `require_admin` | `hasRole(['admin', 'superuser'])` |
| `require_superuser` | `hasRole(['superuser'])` |

### Toast System

Current: Cookies + middleware (`set_toast_cookie`, `request.state.toast_message`)

New: Pinia store with `useToast()` composable (ADR-SKRIPT-0037, REF-SKRIPT-GENERAL-reference-toasts-and-system-messages-spa):

```typescript
const toast = useToast()
toast.success('Tool executed successfully')
toast.error('Execution failed')
```

### CodeMirror Migration

Existing `CodeMirrorEditor.vue` uses CM6. Ensure same version in component library.

### Tailwind Decision

Decision: adopt **Tailwind CSS v4** as a utility layer backed by **HuleEdu design tokens** via `@theme inline`
(ADR-SKRIPT-0032; supersedes ADR-0029).

---

### Source: Finalized Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Tailwind vs CSS | **Tailwind v4 + design tokens (`@theme`)** | Utility productivity without losing token authority (no Tailwind defaults leak through) |
| OpenAPI generation | **Yes**, `openapi-typescript` | Single source of truth; prevents frontend/backend drift |
| Single vs separate admin | **Single SPA** with route guards | Shared auth context, shared components, simpler deployment |
| Cutover strategy | **Clean break** (no redirects) | SPA replaces all routes; old templates deleted |

---

### Source: Checklist

### Pre-Implementation

- [ ] Team reviews this document
- [ ] Ensure ADR-SKRIPT-0027..0030 are accepted and linked from the implementation epic and governing backlog items
- [ ] Verify all current routes documented correctly
- [ ] Confirm design token values are accurate

### Implementation

- [ ] Phase 1: Monorepo foundation
- [ ] Phase 2: Component library (not pursued)
- [ ] Phase 3: SPA scaffolding
- [ ] Phase 4: Backend API layer
- [ ] Phase 5: Core views
- [ ] Phase 6: Contributor/Admin views
- [ ] Phase 7: Testing & deployment

### Post-Implementation

- [x] Remove `frontend/islands/` after migration
- [ ] Remove old Jinja2 templates (clean break)
- [ ] Update CLAUDE.md with new frontend commands
- [ ] Update deployment scripts

---

### Source: Related Documents

- `REF-SKRIPT-PRD-frontend-prd-v0-1-full-vue-vite-spa-migration` - product goals and scope for the SPA migration
- `ADR-SKRIPT-0027` - full SPA decision (supersedes ADR-0001 and ADR-0025)
- `ADR-SKRIPT-0028` - SPA hosting + history fallback
- `ADR-0029` - pure CSS + design tokens (superseded by ADR-SKRIPT-0032)
- `ADR-SKRIPT-0032` - Tailwind CSS 4 with `@theme` design tokens (supersedes ADR-0029)
- `ADR-SKRIPT-0030` - OpenAPI → TypeScript generation (`openapi-typescript`)
- `EPIC-SKRIPT-11` - backlog breakdown for the migration
- `REF-vue-spa-migration-assessment` - initial assessment (deprecated)
- `ADR-SKRIPT-0017` - HuleEdu design system adoption (tokens)

## Confirmed Contract

### Source: Phase Breakdown

### Phase 1: Monorepo Foundation

**Goal:** Restructure `frontend/` for new architecture

**Files to create:**

- `frontend/pnpm-workspace.yaml`
- `frontend/apps/skriptoteket/package.json`
- `frontend/apps/skriptoteket/vite.config.ts`
- `frontend/apps/skriptoteket/index.html`

**Files to modify:**

- `frontend/package.json` → Add workspace scripts

### Phase 2: Component library (not pursued)

**Goal (historical):** Extract a shared HuleEdu UI component library.

**Outcome:** Not pursued. SPA UI primitives live directly in `frontend/apps/skriptoteket/src/assets/main.css`
(Tailwind v4 + design tokens via `@theme`; ADR-SKRIPT-0032).

### Phase 3: SPA Scaffolding

**Goal:** Set up Vue Router, Pinia stores, API client

**Files to create:**

- `frontend/apps/skriptoteket/src/main.ts`
- `frontend/apps/skriptoteket/src/App.vue`
- `frontend/apps/skriptoteket/src/router/index.ts`
- `frontend/apps/skriptoteket/src/router/guards.ts`
- `frontend/apps/skriptoteket/src/stores/auth.ts`
- `frontend/apps/skriptoteket/src/stores/toast.ts`
- `frontend/apps/skriptoteket/src/api/client.ts`
- `frontend/apps/skriptoteket/src/api/types.ts`

**Route mapping:**

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

## Backlog Derivation

### Source: Phase Breakdown

### Phase 1: Monorepo Foundation

**Goal:** Restructure `frontend/` for new architecture

**Files to create:**

- `frontend/pnpm-workspace.yaml`
- `frontend/apps/skriptoteket/package.json`
- `frontend/apps/skriptoteket/vite.config.ts`
- `frontend/apps/skriptoteket/index.html`

**Files to modify:**

- `frontend/package.json` → Add workspace scripts

### Phase 2: Component library (not pursued)

**Goal (historical):** Extract a shared HuleEdu UI component library.

**Outcome:** Not pursued. SPA UI primitives live directly in `frontend/apps/skriptoteket/src/assets/main.css`
(Tailwind v4 + design tokens via `@theme`; ADR-SKRIPT-0032).

### Phase 3: SPA Scaffolding

**Goal:** Set up Vue Router, Pinia stores, API client

**Files to create:**

- `frontend/apps/skriptoteket/src/main.ts`
- `frontend/apps/skriptoteket/src/App.vue`
- `frontend/apps/skriptoteket/src/router/index.ts`
- `frontend/apps/skriptoteket/src/router/guards.ts`
- `frontend/apps/skriptoteket/src/stores/auth.ts`
- `frontend/apps/skriptoteket/src/stores/toast.ts`
- `frontend/apps/skriptoteket/src/api/client.ts`
- `frontend/apps/skriptoteket/src/api/types.ts`

**Route mapping:**
