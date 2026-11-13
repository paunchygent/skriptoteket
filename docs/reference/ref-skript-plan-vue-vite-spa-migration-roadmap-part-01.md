---
type: reference
id: REF-SKRIPT-PLAN-vue-vite-spa-migration-roadmap-PART-01
title: Vue/Vite SPA Migration Roadmap — part 01
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: REF-SKRIPT-PLAN-vue-vite-spa-migration-roadmap
part: 1
---

## Outcome And Purpose

### Source: Executive Summary

This roadmap details the migration from Jinja2/HTMX server-rendered frontend to a Vue 3/Vite SPA with a custom component library.

| Decision | Choice |
|----------|--------|
| **Strategy** | Full SPA replacement (clean break cutover) |
| **Design System** | Tailwind CSS v4 (`@theme`) + HuleEdu design tokens (`--huleedu-*`) (ADR-SKRIPT-0032; supersedes ADR-0029) |
| **API** | `/api/v1/*` + OpenAPI as source of truth + generated TypeScript (`openapi-typescript`) |
| **Build** | pnpm monorepo with Vite 6 |

This plan follows ADR-SKRIPT-0027 and supersedes the prior SSR/HTMX and “SPA islands” paradigm decisions (ADR-0001, ADR-0025).

---

## Planning Boundary

### Source: Current State (post-cutover)

**Status (2025-12-23): cutover complete.** Skriptoteket now serves a full Vue/Vite SPA for all non-API routes via
history fallback (`src/skriptoteket/web/routes/spa_fallback.py`). Legacy Jinja/HTMX page routes are removed.
Legacy `frontend/islands/` has been deleted.

No separate component-library package is maintained; SPA UI primitives live in
`frontend/apps/skriptoteket/src/assets/main.css`.

| Component | Location | Technology |
|-----------|----------|------------|
| SPA source | `frontend/apps/skriptoteket/` | Vue 3.5 + Vite 6 + Tailwind v4 (`@theme`) |
| Built SPA assets | `src/skriptoteket/web/static/spa/` | Vite build output served by FastAPI |
| SPA fallback | `src/skriptoteket/web/routes/spa_fallback.py` | FastAPI history fallback (`index.html`) |
| Design tokens | `src/skriptoteket/web/static/css/huleedu-design-tokens.css` | Canonical `--huleedu-*` tokens |
| Tailwind bridge | `frontend/apps/skriptoteket/src/styles/tailwind-theme.css` | `@theme inline` token mapping |
| JSON API | `src/skriptoteket/web/api/v1/` | `/api/v1/*` (OpenAPI source of truth) |

---

### Source: Target State

### Directory Structure

```text
frontend/
├── package.json                          # pnpm workspace root
├── pnpm-workspace.yaml
├── pnpm-lock.yaml
├── eslint-rules/                         # optional
└── apps/
    └── skriptoteket/                     # Main SPA
        ├── package.json                  # @skriptoteket/spa
        ├── vite.config.ts
        ├── index.html
        └── src/
            ├── main.ts
            ├── App.vue
            ├── router/
            ├── stores/
            ├── api/
            ├── assets/
            ├── components/
            └── views/
```

### Island Migration Map

| Current File | New Location |
|--------------|--------------|
| `editor/CodeMirrorEditor.vue` | `components/editor/CodeMirrorEditor.vue` |
| `editor/EditorIslandApp.vue` | `views/admin/ScriptEditorView.vue` |
| `runtime/UiOutputs.vue` | `components/tools/UiOutputs.vue` |
| `runtime/RuntimeIslandApp.vue` | `views/tools/RunResultView.vue` (integrated) |

**Deleted after migration:** `frontend/islands/` directory

---

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

## Evidence Basis

### Source: Pre-cutover Inventory (historical)

### Frontend Stack

| Component | Location | Technology |
|-----------|----------|------------|
| Templates | `src/skriptoteket/web/templates/` | Jinja2 + HTMX |
| Static CSS | `src/skriptoteket/web/static/css/` | HuleEdu design system (custom) |
| Static JS | `src/skriptoteket/web/static/js/app.js` | Vanilla JS (HTMX helpers) |
| Vue Islands | `frontend/islands/` | Vue 3.5 + Vite 6 (+ Tailwind v4 tokens via `@theme`; ADR-SKRIPT-0032) |

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
- `tailwindcss@^4.1.0` (Tailwind v4 with tokens via `@theme`; ADR-SKRIPT-0032)
- `vite@^6.0.0`

**Missing today:** No Pinia, no Vue Router, no centralized state management.

### Design Tokens

From `src/skriptoteket/web/static/css/huleedu-design-tokens.css`:

```css
/* Core Colors */
--huleedu-canvas: #F9F8F2;
--huleedu-navy: #1C2E4A;
--huleedu-burgundy: #4D1521;
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

**Note:** The token CSS file should remain the source of truth and (if we later extract a shared UI package) be
packaged rather than rewritten by hand.

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

### Source: API Additions

### New Backend Module

Create `src/skriptoteket/web/api/v1/`:
