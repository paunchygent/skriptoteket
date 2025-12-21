---
type: reference
id: REF-vue-spa-migration-roadmap
title: "Vue/Vite SPA Migration Roadmap"
status: active
owners: "agents"
created: 2025-12-21
topic: "frontend-migration"
links:
  - PRD-spa-frontend-v0.1
  - EPIC-11
  - ADR-0027
  - ADR-0028
  - ADR-0029
  - ADR-0030
  - REF-vue-spa-migration-assessment
  - ADR-0017
---

## Executive Summary

This roadmap details the migration from Jinja2/HTMX server-rendered frontend to a Vue 3/Vite SPA with a custom component library.

| Decision | Choice |
|----------|--------|
| **Strategy** | Full SPA replacement (clean break cutover) |
| **Design System** | Custom Vue component library (`@huleedu/ui`) + design tokens (**pure CSS**, no Tailwind) |
| **API** | `/api/v1/*` + OpenAPI as source of truth + generated TypeScript (`openapi-typescript`) |
| **Build** | pnpm monorepo with Vite 6 |

This plan follows ADR-0027 and supersedes the prior SSR/HTMX and “SPA islands” paradigm decisions (ADR-0001, ADR-0025).

---

## Current State Inventory

### Frontend Stack

| Component | Location | Technology |
|-----------|----------|------------|
| Templates | `src/skriptoteket/web/templates/` | Jinja2 + HTMX |
| Static CSS | `src/skriptoteket/web/static/css/` | HuleEdu design system (custom) |
| Static JS | `src/skriptoteket/web/static/js/app.js` | Vanilla JS (HTMX helpers) |
| Vue Islands | `frontend/islands/` | Vue 3.5 + Vite 6 (+ Tailwind 4.1 today; removed per ADR-0029) |

### Existing Vue Islands

```text
frontend/islands/src/
├── DemoApp.vue
├── entrypoints/
│   ├── demo.ts
│   ├── editor.ts
│   └── runtime.ts
├── editor/
│   ├── types.ts
│   ├── CodeMirrorEditor.vue
│   └── EditorIslandApp.vue
├── runtime/
│   ├── types.ts
│   ├── UiOutputs.vue
│   └── RuntimeIslandApp.vue
└── env.d.ts
```

**Dependencies** (`frontend/islands/package.json`):

- `vue@^3.5.0`
- `@codemirror/*@^6.x` (CodeMirror 6 modules)
- `tailwindcss@^4.1.0` (dev dependency today; removed per ADR-0029)
- `vite@^6.0.0`

**Missing today:** No Pinia, no Vue Router, no centralized state management.

### Design Tokens

From `src/skriptoteket/web/static/css/huleedu-design-tokens.css`:

```css
/* Core Colors */
--huleedu-canvas: #F9F8F2;
--huleedu-navy: #1C2E4A;
--huleedu-burgundy: #6B1C2E;
--huleedu-success: #059669;
--huleedu-warning: #D97706;
--huleedu-error: #DC2626;

/* Typography */
--huleedu-font-sans: "IBM Plex Sans", system-ui, sans-serif;
--huleedu-font-serif: "IBM Plex Serif", Georgia, serif;
--huleedu-font-mono: "IBM Plex Mono", ui-monospace, monospace;

/* Brutalist Shadows */
--huleedu-shadow-brutal: 6px 6px 0px 0px var(--huleedu-navy);
--huleedu-shadow-brutal-sm: 4px 4px 0px 0px var(--huleedu-navy);
```

**Note:** The token CSS file should remain the source of truth and be packaged into `@huleedu/ui` rather than rewritten
by hand.

### Current Routes

From `src/skriptoteket/web/router.py`:

**Public:**

- `auth_pages.router` → `/login`, `POST /login`, `POST /logout`

**Protected (require_user):**

- `home_pages.router` → `/`
- `browse_pages.router` → `/browse`, `/browse/{profession}`, `/browse/{profession}/{category}`
- `curated_apps_pages.router` → `/apps/{app_id}`
- `tools_pages.router` → `/tools/{slug}/run`, `POST /tools/{slug}/run`
- `my_runs_pages.router` → `/my-runs/{run_id}`
- `my_tools_pages.router` → `/my-tools`
- `suggestions_pages.router` → `/suggestions/*`
- `spa_islands_pages.router` → `/spa/demo`, etc.
- `editor_routes.router` → `/api/v1/editor/*` (JSON)
- `interactive_tools_routes.router` → `/api/v1/*` (JSON)
- `admin_tools_pages.router` → `/admin/tools`
- `admin_scripting_pages.router` → `/admin/tool-versions/*`

### Existing JSON API Endpoints

```text
POST /api/v1/editor/tools/{tool_id}/draft           → SaveResult
POST /api/v1/editor/tool-versions/{version_id}/save → SaveResult
POST /api/v1/start_action                           → StartActionResult
GET  /api/v1/tools/{tool_id}/sessions/{context}     → GetSessionStateResult
GET  /api/v1/runs/{run_id}                          → GetRunResult
GET  /api/v1/runs/{run_id}/artifacts                → ListArtifactsResult
GET  /api/v1/runs/{run_id}/artifacts/{artifact_id}  → FileResponse
```

### Template Structure

From `src/skriptoteket/web/templates/base.html`:

```html
<body class="huleedu-base" hx-boost="true">
  <div class="huleedu-frame">
    <header class="huleedu-header">
      <!-- Brand, nav (role-based), hamburger, logout form -->
    </header>
    <nav id="mobile-nav" hidden><!-- Mobile nav --></nav>
    <main>{% block content %}{% endblock %}</main>
  </div>
  <div id="toast-container"><!-- Toast notifications --></div>
  <script src="/static/js/app.js"></script>
  <script src="/static/vendor/htmx.min.js"></script>
</body>
```

### Handler Pattern

From `src/skriptoteket/web/pages/browse.py`:

```python
@router.get("/{profession_slug}/{category_slug}")
@inject
async def list_tools_by_tags(
    handler: FromDishka[ListToolsByTagsHandlerProtocol],
    user: User = Depends(require_user),
    session: Session | None = Depends(get_current_session),
) -> HTMLResponse:
    result = await handler.handle(actor=user, query=ListToolsByTagsQuery(...))
    return templates.TemplateResponse(
        name="browse_tools.html",
        context={"user": user, "profession": result.profession, "tools": result.tools, ...}
    )
```

**Key insight:** Handlers return Pydantic models. JSON endpoints only need different serialization.

---

## Target State

### Directory Structure

```text
frontend/
├── package.json                          # Monorepo root
├── pnpm-workspace.yaml
├── turbo.json                            # Optional: Turborepo
│
├── packages/
│   └── huleedu-ui/                       # Vue component library
│       ├── package.json                  # @huleedu/ui
│       ├── vite.config.ts
│       ├── src/
│       │   ├── index.ts
│       │   ├── tokens/
│       │   │   ├── colors.ts
│       │   │   ├── typography.ts
│       │   │   └── tokens.css
│       │   ├── composables/
│       │   │   ├── useToast.ts
│       │   │   └── useBreakpoint.ts
│       │   └── components/
│       │       ├── primitives/           # HButton, HInput, HSelect, HLabel
│       │       ├── layout/               # HFrame, HHeader, HCard
│       │       ├── feedback/             # HToast, HDot, HSpinner
│       │       ├── forms/                # HFormField, HFileUpload
│       │       └── navigation/           # HNav, HMobileNav, HBreadcrumb
│       ├── .storybook/
│       └── stories/
│
└── apps/
    └── skriptoteket/                     # Main SPA
        ├── package.json                  # @skriptoteket/spa
        ├── vite.config.ts
        ├── index.html
        └── src/
            ├── main.ts
            ├── App.vue
            ├── router/
            │   ├── index.ts
            │   └── guards.ts
            ├── stores/
            │   ├── auth.ts
            │   ├── user.ts
            │   └── toast.ts
            ├── api/
            │   ├── client.ts
            │   ├── types.ts
            │   ├── catalog.ts
            │   ├── tools.ts
            │   └── admin.ts
            ├── views/
            │   ├── auth/LoginView.vue
            │   ├── home/HomeView.vue
            │   ├── browse/
            │   ├── tools/
            │   ├── my-runs/
            │   ├── my-tools/
            │   ├── suggestions/
            │   └── admin/
            └── components/
                ├── layout/AppHeader.vue
                └── tools/ToolCard.vue
```

### Island Migration Map

| Current File | New Location |
|--------------|--------------|
| `editor/CodeMirrorEditor.vue` | `components/editor/CodeMirrorEditor.vue` |
| `editor/EditorIslandApp.vue` | `views/admin/ScriptEditorView.vue` |
| `runtime/UiOutputs.vue` | `components/tools/UiOutputs.vue` |
| `runtime/RuntimeIslandApp.vue` | `views/tools/RunResultView.vue` (integrated) |

**Delete after migration:** `frontend/islands/` directory

---

## API Additions

### New Backend Module

Create `src/skriptoteket/web/api/v1/`:

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

#### Auth API (`/api/v1/auth/`)

| Endpoint | Method | Handler |
|----------|--------|---------|
| `/api/v1/auth/login` | POST | `LoginHandler` (exists) |
| `/api/v1/auth/logout` | POST | `LogoutHandler` (exists) |
| `/api/v1/auth/me` | GET | Returns `user` from session |
| `/api/v1/auth/csrf` | GET | Returns CSRF token |

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

## Phase Breakdown

### Phase 1: Monorepo Foundation

**Goal:** Restructure `frontend/` for new architecture

**Files to create:**

- `frontend/pnpm-workspace.yaml`
- `frontend/packages/huleedu-ui/package.json`
- `frontend/packages/huleedu-ui/vite.config.ts`
- `frontend/packages/huleedu-ui/src/index.ts`
- `frontend/packages/huleedu-ui/src/tokens/colors.ts`
- `frontend/packages/huleedu-ui/src/tokens/typography.ts`
- `frontend/packages/huleedu-ui/src/tokens/tokens.css`
- `frontend/packages/huleedu-ui/.storybook/main.ts`
- `frontend/packages/huleedu-ui/.storybook/preview.ts`
- `frontend/apps/skriptoteket/package.json`
- `frontend/apps/skriptoteket/vite.config.ts`
- `frontend/apps/skriptoteket/index.html`

**Files to modify:**

- `frontend/package.json` → Add workspace scripts

### Phase 2: Component Library

**Goal:** Build all HuleEdu UI components with Storybook

**Components to build:**

| Component | CSS Class | Priority |
|-----------|-----------|----------|
| `HButton` | `.huleedu-btn`, `.huleedu-btn-secondary`, `.huleedu-btn-sm` | High |
| `HInput` | `.huleedu-input` | High |
| `HSelect` | `.huleedu-select` | High |
| `HLabel` | `.huleedu-label` | High |
| `HCard` | `.huleedu-card`, `.huleedu-card-sm` | High |
| `HFrame` | `.huleedu-frame` | High |
| `HHeader` | `.huleedu-header` | High |
| `HLink` | `.huleedu-link` | Medium |
| `HDot` | `.huleedu-dot-active`, `.huleedu-dot-success`, etc. | Medium |
| `HToast` | Toast markup from `base.html` | Medium |
| `HNav` | `.huleedu-header-nav` | Medium |
| `HMobileNav` | `.huleedu-mobile-nav` | Medium |
| `HRow` | `.huleedu-row` | Low |
| `HFormField` | Composite (label + input + error) | Low |
| `HFileUpload` | Custom drag-drop | Low |
| `HSpinner` | Loading indicator | Low |
| `HBreadcrumb` | Navigation path | Low |

**Files to create per component:**

- `frontend/packages/huleedu-ui/src/components/{category}/{Component}.vue`
- `frontend/packages/huleedu-ui/stories/{Component}.stories.ts`

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
| `/login` | `/login` | Public |
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

1. `LoginView.vue` → POST `/api/v1/auth/login`
2. `HomeView.vue` → Static welcome (uses HuleEdu UI)
3. `ProfessionsView.vue` → GET `/api/v1/catalog/professions`
4. `CategoriesView.vue` → GET `/api/v1/catalog/professions/{slug}/categories`
5. `ToolsView.vue` → GET `/api/v1/catalog/professions/{slug}/categories/{cat}/tools`
6. `CuratedAppView.vue` → GET `/api/v1/catalog/apps/{app_id}` (plus interactive endpoints)
7. `RunToolView.vue` → POST `/api/v1/tools/{slug}/run` (multipart file upload)
8. `RunResultView.vue` → GET `/api/runs/{run_id}` (existing endpoint)
9. `MyRunsView.vue` → GET `/api/v1/my-runs`
10. `RunDetailView.vue` → GET `/api/v1/my-runs/{run_id}`

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

This roadmap is implemented as `EPIC-11` and its stories:

- ST-11-01..02: frontend workspace + UI library/tokens
- ST-11-03: serve SPA from FastAPI (manifest + history fallback)
- ST-11-04..05: API v1 + OpenAPI TS + auth/guards
- ST-11-06..12: SPA views for browse/tools/runs/apps/suggestions/admin/editor
- ST-11-13: cutover + deletion + Playwright E2E

---

## Critical Review Points

### Session Handling

SPA uses same httponly cookies. CSRF token flow:

1. SPA calls `POST /api/v1/auth/login` with credentials
2. Backend sets HTTP-only session cookie, returns `{ user, csrf_token }`
3. SPA stores `csrf_token` in Pinia store (memory)
4. For mutating requests, SPA includes `X-CSRF-Token` header
5. Backend validates header against session's stored token

**Verify:** Requests use `credentials: 'include'`. Same-origin hosting (ADR-0028) avoids CORS complexity.

### File Uploads

`RunToolView.vue` must support `multipart/form-data`:

```typescript
const formData = new FormData()
formData.append('file', file)
await api.post(`/api/v1/tools/${slug}/run`, formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
})
```

**Verify:** Endpoint accepts `UploadFile` from FastAPI.

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

New: Pinia store with `useToast()` composable:

```typescript
const toast = useToast()
toast.success('Tool executed successfully')
toast.error('Execution failed')
```

### CodeMirror Migration

Existing `CodeMirrorEditor.vue` uses CM6. Ensure same version in component library.

### Tailwind Decision

Decision: use **pure CSS** with design tokens and remove Tailwind from the toolchain (ADR-0029).

---

## Finalized Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Tailwind vs CSS | **Pure CSS** with design tokens | HuleEdu design is distinctive (brutalist); component library owns its styles |
| OpenAPI generation | **Yes**, `openapi-typescript` | Single source of truth; prevents frontend/backend drift |
| Single vs separate admin | **Single SPA** with route guards | Shared auth context, shared components, simpler deployment |
| Cutover strategy | **Clean break** (no redirects) | SPA replaces all routes; old templates deleted |

---

## Checklist

### Pre-Implementation

- [ ] Team reviews this document
- [ ] Ensure ADR-0027..0030 are accepted and linked from the implementation epic/sprint
- [ ] Verify all current routes documented correctly
- [ ] Confirm design token values are accurate

### Implementation

- [ ] Phase 1: Monorepo foundation
- [ ] Phase 2: Component library (Storybook)
- [ ] Phase 3: SPA scaffolding
- [ ] Phase 4: Backend API layer
- [ ] Phase 5: Core views
- [ ] Phase 6: Contributor/Admin views
- [ ] Phase 7: Testing & deployment

### Post-Implementation

- [ ] Remove `frontend/islands/` after migration
- [ ] Remove old Jinja2 templates (clean break)
- [ ] Update CLAUDE.md with new frontend commands
- [ ] Update deployment scripts

---

## Related Documents

- `PRD-spa-frontend-v0.1` - product goals and scope for the SPA migration
- `ADR-0027` - full SPA decision (supersedes ADR-0001 and ADR-0025)
- `ADR-0028` - SPA hosting + history fallback
- `ADR-0029` - pure CSS + design tokens (no Tailwind)
- `ADR-0030` - OpenAPI → TypeScript generation (`openapi-typescript`)
- `EPIC-11` - backlog breakdown for the migration
- `REF-vue-spa-migration-assessment` - initial assessment (deprecated)
- `ADR-0017` - HuleEdu design system adoption (tokens)
