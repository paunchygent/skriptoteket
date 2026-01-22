---
id: "040-fastapi-blueprint"
type: "implementation"
created: 2025-12-13
updated: 2026-01-22
scope: "backend"
---

# 040: FastAPI Service Blueprint (SPA + API v1)

This repo is **SPA-first** (ADR-0027): FastAPI serves a built Vue/Vite SPA and exposes JSON APIs under `/api/v1/*`.
There are no server-rendered page/HTMX surfaces.

## 1. Application factory

Canonical entrypoint:

- `src/skriptoteket/web/app.py`

Expected shape (simplified; mirrors the real implementation):

```python
from pathlib import Path

from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from skriptoteket.config import Settings
from skriptoteket.di import create_container
from skriptoteket.observability.logging import configure_logging
from skriptoteket.observability.tracing import init_tracing
from skriptoteket.web.middleware.correlation import CorrelationMiddleware
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from skriptoteket.web.middleware.metrics import metrics_middleware
from skriptoteket.web.middleware.tracing import tracing_middleware
from skriptoteket.web.router import router as web_router
from skriptoteket.web.routes.observability import router as observability_router

def create_app() -> FastAPI:
    settings = Settings()
    configure_logging(...)
    if settings.OTEL_TRACING_ENABLED:
        init_tracing(settings.SERVICE_NAME)

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.ENABLE_DOCS else None,
    )

    # Middleware order: correlation (ASGI) → tracing → metrics → error_handler
    app.middleware("http")(error_handler_middleware)
    app.middleware("http")(metrics_middleware)
    app.middleware("http")(tracing_middleware)
    app.add_middleware(CorrelationMiddleware)

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    container = create_container(settings)
    setup_dishka(container, app)

    app.include_router(observability_router)  # /healthz, /metrics (public)
    app.include_router(web_router)           # /api/v1 + SPA fallback
    return app
```

## 2. Router organization (REQUIRED)

### API v1 (SPA consumption)

- Routers live in: `src/skriptoteket/web/api/v1/`
- Router aggregation lives in: `src/skriptoteket/web/router.py`

### SPA history fallback (MUST be last)

- `src/skriptoteket/web/routes/spa_fallback.py`
- MUST be the last router registered in `src/skriptoteket/web/router.py` so it does not intercept `/api/*`, `/static/*`,
  or observability endpoints.

## 3. OpenAPI-safe typing (REQUIRED)

FastAPI builds OpenAPI from type hints. With postponed evaluation / ForwardRef edge cases, router annotations can break
`/docs` and `/openapi.json`.

- **FORBIDDEN**: `from __future__ import annotations` in any *router module* under:
  - `src/skriptoteket/web/api/v1/**`
  - `src/skriptoteket/web/routes/**`
- **FORBIDDEN**: Union return type hints of Starlette responses (e.g. `FileResponse | JSONResponse`).
- **REQUIRED**: If an endpoint may return multiple response types, annotate the return type as
  `fastapi.responses.Response` (or `starlette.responses.Response`) and set an explicit `response_class=...` on the
  decorator when needed.

## 4. Endpoint pattern (REQUIRED)

- Web layer stays thin: validate inputs, call a handler protocol, return a boundary model.
- Use Dishka injection via `FromDishka[...]`.
- For mutating endpoints, enforce CSRF via `require_csrf_token` and auth via `require_user_api`.

Example (pattern only):

```python
from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends

from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.catalog import ListToolsHandlerProtocol
from skriptoteket.web.auth.api_dependencies import require_user_api

router = APIRouter(prefix="/api/v1")

@router.get("/tools")
@inject
async def list_tools(
    handler: FromDishka[ListToolsHandlerProtocol],
    user: User = Depends(require_user_api),
):
    return await handler.handle(actor=user, query=...)
```

## 5. OpenAPI as the contract (frontend types)

- The SPA treats OpenAPI as source of truth.
- After changing API models/routes, run:
  - `pdm run openapi-export-v1`
  - `pdm run fe-gen-api-types` (runs OpenAPI export + TypeScript generation)
