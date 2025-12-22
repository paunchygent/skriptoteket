---
type: story
id: ST-11-03
title: "Serve SPA from FastAPI (manifest + history fallback)"
status: done
owners: "agents"
created: 2025-12-21
epic: "EPIC-11"
acceptance_criteria:
  - "Given a production SPA build exists, when the FastAPI app runs, then deep links (e.g. /browse/foo) serve the SPA index and load hashed assets successfully"
  - "Given API routes exist under /api, when requesting /api/*, then the SPA history fallback does not intercept API responses"
ui_impact: "Enables the SPA to own all route paths without redirects."
dependencies: ["ADR-0027", "ADR-0028"]
---

## Context

The SPA must work with history routing and be served as a first-class part of the FastAPI app.

## Implementation (2025-12-22)

### Changes Made

1. **SPA Vite config** (`frontend/apps/skriptoteket/vite.config.ts`):
   - Added `base: "/static/spa/"` for correct asset URL prefixes
   - Added `outDir` pointing to `src/skriptoteket/web/static/spa`
   - Added `/static` proxy for dev server

2. **History fallback route** (`src/skriptoteket/web/routes/spa_fallback.py`):
   - New module with catch-all route `/{full_path:path}`
   - Serves `index.html` for non-API/static paths
   - Explicit exclusion list: `/api/`, `/static/`, `/healthz`, `/metrics`, `/docs`, `/redoc`, `/openapi.json`
   - No authentication on fallback (Vue Router handles auth via `/api/v1/auth/me`)

3. **Router registration** (`src/skriptoteket/web/router.py`):
   - Imported `spa_fallback` module
   - Registered fallback router LAST to avoid intercepting API routes

4. **Dockerfile**:
   - Updated Stage 1 to build `@skriptoteket/spa` instead of `@skriptoteket/islands`
   - SPA replaces islands at `/static/spa/` (clean break per ADR-0027)

5. **Tests** (`tests/unit/web/test_spa_fallback.py`):
   - Unit tests for `_should_serve_spa()` path exclusion logic

### Verification

```bash
# Build SPA (outputs to src/skriptoteket/web/static/spa/)
pdm run fe-build

# Verify index.html has correct asset paths
cat src/skriptoteket/web/static/spa/index.html
# → src="/static/spa/assets/index-*.js"

# Test deep link (returns SPA HTML)
curl http://127.0.0.1:8000/browse
# → <!doctype html>...

# Test API route (returns JSON, not intercepted)
curl http://127.0.0.1:8000/api/v1/auth/me
# → {"error":{"code":"UNAUTHORIZED",...}}

# Quality gates
pdm run lint                                    # All checks passed
pdm run typecheck                               # Success: no issues in 298 files
pnpm -C frontend --filter @skriptoteket/spa typecheck  # OK
pdm run pytest tests/unit/web/test_spa_fallback.py -v  # 10 passed
```

### Route Priority

1. `/static/*` - StaticFiles mount (first priority)
2. `/healthz`, `/metrics` - Observability routes
3. `/login`, `/logout` - Auth pages
4. `/api/v1/*` - API routes
5. SSR pages (protected) - Will be removed at cutover (ST-11-13)
6. `/{full_path:path}` - SPA fallback (LAST)
