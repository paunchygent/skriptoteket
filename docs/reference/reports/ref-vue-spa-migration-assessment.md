---
type: reference
id: REF-vue-spa-migration-assessment
title: "Vue/Vite SPA Frontend Migration Assessment"
status: active
owners: "agents"
created: 2025-12-15
topic: "architecture"
---

## Executive Summary

This assessment evaluates the effort required to migrate Skriptoteket from its current server-rendered Jinja2/HTMX frontend to a separate Vue/Vite SPA. The migration is **feasible and low-risk** due to the existing protocol-based architecture: all handlers can be reused unchanged, requiring only a thin API layer (~23h backend) plus the Vue frontend (~39h). Total estimated effort is ~103 hours (5-7 weeks).

**Key finding**: The current DDD/Clean Architecture with Dishka DI was designed for exactly this kind of extensibility. Adding an API layer is additive, not disruptive.

---

## Current Architecture

### HTTP Surface (28 Endpoints)

| Auth Level | Count | Examples |
|------------|-------|----------|
| Public | 3 | `/health`, `/login` |
| `require_user` | 5 | `/`, `/logout`, `/browse/*` |
| `require_contributor` | 12 | `/suggestions/new`, `/admin/tools/{id}`, `/admin/tool-versions/{id}/*` |
| `require_admin` | 8 | `/admin/tools`, `/admin/suggestions/*`, version publish/request-changes |

### Frontend Stack

- **Templates**: Jinja2 in `src/skriptoteket/web/templates/`
- **Interactivity**: HTMX (admin script editor only: version list refresh, sandbox execution)
- **Code Editor**: CodeMirror 5 (vendor bundle)
- **Language**: Swedish UI

### Backend Plumbing

| Layer | Location |
|-------|----------|
| Protocols | `src/skriptoteket/protocols/*.py` |
| Handlers | `src/skriptoteket/application/*/handlers/*.py` |
| DI Container | `src/skriptoteket/di.py` |
| Repositories | `src/skriptoteket/infrastructure/repositories/*.py` |

All handlers are protocol-based, injected via Dishka, and return Pydantic models. This means they can be called from both web routes (returning HTML) and API routes (returning JSON) without modification.

---

## Migration Scope

### New API Layer

Create `src/skriptoteket/web/api/v1/` with the following structure:

```text
src/skriptoteket/web/api/
  v1/
    __init__.py
    router.py           # Aggregates all v1 routes
    auth.py             # POST /login, /logout, GET /me
    browse.py           # GET /professions, /categories, /tools
    suggestions.py      # POST /suggestions, admin review endpoints
    admin/
      __init__.py
      tools.py          # Tool list, publish/depublish
      scripting.py      # Versions, save, submit-review, publish, request-changes
      runs.py           # Sandbox execution, run results, artifact download
    schemas/
      __init__.py
      common.py         # ErrorResponse, pagination
      auth.py           # LoginRequest, LoginResponse, UserResponse
      browse.py         # ProfessionResponse, CategoryResponse, ToolResponse
      suggestions.py    # SuggestionRequest, SuggestionResponse
      scripting.py      # VersionResponse, RunResultResponse
```

### Endpoint Mapping

| Current Web Route | New API Endpoint |
|-------------------|------------------|
| `POST /login` | `POST /api/v1/auth/login` |
| `POST /logout` | `POST /api/v1/auth/logout` |
| `GET /` (user info) | `GET /api/v1/auth/me` |
| `GET /browse/` | `GET /api/v1/professions` |
| `GET /browse/{slug}` | `GET /api/v1/professions/{slug}/categories` |
| `GET /browse/{p}/{c}` | `GET /api/v1/professions/{p}/categories/{c}/tools` |
| `POST /suggestions/new` | `POST /api/v1/suggestions` |
| `GET /admin/suggestions` | `GET /api/v1/admin/suggestions` |
| `POST /admin/suggestions/{id}/decision` | `POST /api/v1/admin/suggestions/{id}/decision` |
| `GET /admin/tools` | `GET /api/v1/admin/tools` |
| `POST /admin/tools/{id}/publish` | `POST /api/v1/admin/tools/{id}/publish` |
| `POST /admin/tools/{id}/depublish` | `POST /api/v1/admin/tools/{id}/depublish` |
| `GET /admin/tools/{id}/versions` | `GET /api/v1/admin/tools/{id}/versions` |
| `POST /admin/tools/{id}/versions` | `POST /api/v1/admin/tools/{id}/versions` |
| `POST /admin/tool-versions/{id}/save` | `POST /api/v1/admin/versions/{id}/save` |
| `POST /admin/tool-versions/{id}/submit-review` | `POST /api/v1/admin/versions/{id}/submit-review` |
| `POST /admin/tool-versions/{id}/publish` | `POST /api/v1/admin/versions/{id}/publish` |
| `POST /admin/tool-versions/{id}/request-changes` | `POST /api/v1/admin/versions/{id}/request-changes` |
| `POST /admin/tool-versions/{id}/run-sandbox` | `POST /api/v1/admin/versions/{id}/run-sandbox` |
| `GET /admin/tool-runs/{id}` | `GET /api/v1/admin/runs/{id}` |
| `GET /admin/tool-runs/{id}/artifacts/{a}` | `GET /api/v1/admin/runs/{id}/artifacts/{a}` |

---

## Authentication Strategy

### Recommendation: Keep Cookie-Based Sessions with CORS

**Rationale**:

1. **Security**: HTTP-only cookies prevent XSS token theft; immediate revocation via PostgreSQL
2. **Existing infrastructure**: Session model already implemented with expiry and CSRF tokens
3. **Simplicity**: No JWT refresh logic, blacklisting, or token storage concerns
4. **SPA compatibility**: Modern browsers handle `credentials: include` correctly with CORS

**Against JWT for this codebase**:

- Sessions already in PostgreSQL with proper expiry
- No distributed microservice needs requiring stateless tokens
- JWT adds complexity (refresh tokens, blacklisting for revocation) without benefit

### Required Changes

| File | Change |
|------|--------|
| `src/skriptoteket/config.py` | Add `CORS_ORIGINS: list[str]`, `CORS_ALLOW_CREDENTIALS: bool` |
| `src/skriptoteket/web/app.py` | Add `CORSMiddleware` with credentials support |
| `src/skriptoteket/web/auth/dependencies.py` | Add `verify_csrf_for_api()` checking `X-CSRF-Token` header |
| `src/skriptoteket/web/api/v1/auth.py` | Return `csrf_token` in login response for SPA storage |

### CSRF Flow for SPA

1. SPA calls `POST /api/v1/auth/login` with credentials
2. Backend sets HTTP-only session cookie, returns `{ user, csrf_token }`
3. SPA stores `csrf_token` in memory (Pinia store)
4. For all mutating requests, SPA includes `X-CSRF-Token` header
5. Backend validates header against session's stored token

---

## Vue/Vite Frontend Structure

```text
frontend/
  package.json
  vite.config.ts
  tsconfig.json
  index.html
  src/
    main.ts
    App.vue
    router/
      index.ts                    # Vue Router with guards
    stores/                       # Pinia stores
      auth.ts                     # User, CSRF token, login/logout
      browse.ts                   # Professions, categories cache
      admin/
        tools.ts                  # Admin tool list
        scripting.ts              # Script editor state
    api/
      client.ts                   # Axios with CSRF interceptor
      auth.ts, browse.ts, suggestions.ts, admin.ts
    views/
      LoginView.vue
      HomeView.vue
      BrowseView.vue
      CategoryView.vue
      ToolsView.vue
      SuggestionNewView.vue
      admin/
        AdminToolsView.vue
        AdminSuggestionsView.vue
        AdminSuggestionDetailView.vue
        AdminScriptEditorView.vue
    components/
      common/
        NavBar.vue
        ErrorAlert.vue
        LoadingSpinner.vue
      admin/
        ScriptEditor.vue          # CodeMirror 6 integration
        VersionList.vue
        RunResult.vue
    types/
      api.ts                      # TypeScript interfaces matching backend schemas
```

### Key Technical Decisions

| Decision | Recommendation | Rationale |
|----------|----------------|-----------|
| State management | Pinia | Vue 3 standard, simple API, TypeScript support |
| HTTP client | Axios | Interceptors for CSRF, better error handling than fetch |
| Code editor | CodeMirror 6 | Modern, tree-shakeable, better TypeScript support than v5 |
| Routing | Vue Router 4 | Standard, navigation guards for auth |
| Build tool | Vite | Fast HMR, optimal production builds |

---

## Migration Phases

### Phase 1: Foundation (10h)

**Backend (4h)**:

- Add CORS middleware to `app.py`
- Create `/api/v1/auth/*` endpoints
- Add `X-CSRF-Token` header verification
- Add settings for CORS configuration

**Frontend (6h)**:

- Initialize Vue/Vite project
- Set up Pinia auth store
- Create API client with CSRF interceptor
- Build login view and auth flow

### Phase 2: Browse (6h)

**Backend (2h)**:

- Create `/api/v1/professions`, `/api/v1/professions/{slug}/categories`, `/api/v1/.../tools` endpoints
- Add response schemas

**Frontend (4h)**:

- Build profession, category, tool list views
- Implement browse navigation

### Phase 3: Suggestions (10h)

**Backend (3h)**:

- Create `/api/v1/suggestions` POST endpoint
- Create `/api/v1/admin/suggestions` GET/POST endpoints
- Add suggestion schemas

**Frontend (7h)**:

- Build suggestion form view
- Build admin review queue and detail views
- Implement decision workflow

### Phase 4: Admin Tools (4h)

**Backend (2h)**:

- Create `/api/v1/admin/tools` endpoints
- Add publish/depublish endpoints

**Frontend (2h)**:

- Build admin tools list view
- Implement publish/depublish actions

### Phase 5: Script Editor (16h)

**Backend (6h)**:

- Create versioning endpoints (create, save, submit-review, publish, request-changes)
- Create sandbox execution endpoint
- Create run result and artifact endpoints
- Handle multipart file upload

**Frontend (10h)**:

- Integrate CodeMirror 6
- Build version list component
- Implement sandbox execution flow
- Build run result display
- Handle artifact downloads

### Phase 6: Cleanup (8h)

**Backend (6h)**:

- Remove Jinja2 templates (or keep for fallback)
- Update static file serving for production SPA
- Update Docker configuration
- Update documentation

**Frontend (2h)**:

- Production build configuration
- Asset optimization

---

## Effort Estimation

### Backend

| Task | Hours |
|------|-------|
| CORS middleware + settings | 1 |
| Auth API endpoints | 2 |
| CSRF verification | 1 |
| Browse API endpoints | 2 |
| Suggestions API endpoints | 3 |
| Admin tools API endpoints | 2 |
| Scripting API endpoints | 6 |
| Response schemas | 4 |
| Integration testing | 2 |
| **Subtotal** | **23** |

### Frontend

| Task | Hours |
|------|-------|
| Project setup | 2 |
| API client + types | 3 |
| Auth flow + views | 4 |
| Browse views | 4 |
| Suggestion views | 7 |
| Admin tools view | 2 |
| Script editor + CodeMirror | 10 |
| Common components | 3 |
| Swedish translations | 2 |
| Build optimization | 2 |
| **Subtotal** | **39** |

### Infrastructure

| Task | Hours |
|------|-------|
| CORS testing | 2 |
| Docker/compose updates | 2 |
| API integration tests | 8 |
| E2E tests (Playwright/Cypress) | 8 |
| Documentation | 4 |
| **Subtotal** | **24** |

### Total

| Category | Hours |
|----------|-------|
| Backend | 23 |
| Frontend | 39 |
| Infrastructure | 24 |
| Buffer (20%) | 17 |
| **Total** | **103** |

**Calendar estimate**: 5-7 weeks (depending on parallelization)

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| CORS misconfiguration in production | Medium | High | Explicit allowed origins, no wildcards, integration tests |
| Session cookie issues across domains | Low | Medium | Use `SameSite=Lax`, test in staging with real domain |
| CodeMirror 6 learning curve | Low | Low | Well-documented, similar API to v5 |
| API/frontend contract drift | Medium | Medium | Generate TypeScript types from Pydantic schemas |
| Performance regression (SPA bundle size) | Low | Low | Vite tree-shaking, lazy route loading |

---

## Coexistence Strategy

Web and API routes can coexist during migration:

```python
# src/skriptoteket/web/router.py
from skriptoteket.web.api.v1.router import router as api_v1_router

router = APIRouter()

# New API routes
router.include_router(api_v1_router)

# Existing web routes (keep during migration)
router.include_router(auth_pages.router)
protected.include_router(home_pages.router)
# ...
```

This enables:

- Incremental migration (one feature domain at a time)
- Rollback capability (web routes remain functional)
- A/B testing between old and new frontends

---

## Key Advantages

1. **Handler reuse**: Existing protocol-based handlers work unchanged
2. **Type safety**: TypeScript DTOs mirror Pydantic schemas
3. **Incremental**: Each domain (browse, suggestions, admin) migrates independently
4. **Reversible**: Web routes preserved during transition

---

## Dependencies

### Required Before Starting

- Stable EPIC-04 implementation (scripting endpoints)
- Decision on session vs JWT (recommendation: keep sessions)

### Can Proceed in Parallel

- Vue frontend development (once API contracts defined)
- API endpoint implementation (domain by domain)

---

## ADR Recommendations

If proceeding with this migration, consider formalizing:

1. **ADR: API Layer Architecture**

   Define API versioning strategy, response envelope format, error response structure, and pagination conventions.

2. **ADR: SPA Authentication Model**

   Formalize cookie + CSRF approach for SPA, session lifetime, and refresh behavior.

---

## Decision Required

This assessment is provided for planning purposes. Before proceeding:

1. **Priority**: Is SPA migration higher priority than completing EPIC-04 governance or starting EPIC-05?
2. **Resources**: Is ~100h of effort justified given current roadmap?
3. **Alternatives**: Consider whether HTMX expansion could achieve similar UX goals with less effort

Recommendation: Defer SPA migration until after EPIC-05 (identity federation) unless there is a specific driver (mobile support, offline capability, third-party integrations) that requires a decoupled frontend.

---

## Related Documents

- **`ref-htmx-ux-enhancement-plan.md`** - HTMX alternative implementation guide (15-25h vs 103h for Vue SPA)
