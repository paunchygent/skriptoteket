---
id: "040-fastapi-blueprint"
type: "implementation"
created: 2025-12-13
scope: "backend"
---

# 040: FastAPI Service Blueprint

## 1. Application Factory

```python
# app.py
from fastapi import FastAPI
from dishka.integrations.fastapi import setup_dishka

from src.config import Settings
from src.di import create_container
from src.web import router as web_router
from src.api.v1 import router as v1_router
from src.api.middleware.correlation import CorrelationMiddleware
from src.api.middleware.error_handler import error_handler_middleware

def create_app() -> FastAPI:
    settings = Settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.ENABLE_DOCS else None,
    )

    # Middleware (order matters: first added = outermost)
    app.middleware("http")(error_handler_middleware)
    app.add_middleware(CorrelationMiddleware)

    # DI container
    container = create_container(settings)
    setup_dishka(container, app)

    # Routers
    app.include_router(web_router)  # Server-rendered UI (default)
    app.include_router(v1_router, prefix="/api/v1")

    # Health endpoint
    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app

app = create_app()
```

## 2. Web Layer (server-rendered UI)

### OpenAPI-safe typing (REQUIRED)

FastAPI uses type hints to build OpenAPI. With our current stack (FastAPI + Pydantic v2), postponed evaluation of
annotations can surface as unresolved `ForwardRef`s and break `/docs` and `/openapi.json`.

- **FORBIDDEN**: `from __future__ import annotations` in any router module (e.g. `src/skriptoteket/web/pages/**`,
  `src/skriptoteket/web/partials/**`, `src/skriptoteket/api/**`).
- **FORBIDDEN**: Union return type hints of Starlette responses (e.g. `RedirectResponse | HTMLResponse`).
- **REQUIRED**: If an endpoint may return multiple response types (e.g. render a template on validation error and
  redirect on success), annotate the return type as `fastapi.responses.Response` and set an explicit
  `response_class=...` on the route decorator.

### Router organization

```python
# web/__init__.py
from fastapi import APIRouter
from src.web.pages.tools import router as tools_pages_router
from src.web.partials.tools import router as tools_partials_router

router = APIRouter()
router.include_router(tools_pages_router)
router.include_router(tools_partials_router)
```

### HTMX endpoint pattern (partials)

```python
# web/partials/tools.py
from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from dishka.integrations.fastapi import FromDishka, inject

from src.protocols import RunToolCommandHandlerProtocol
from src.application.tools.commands import RunToolCommand

router = APIRouter()
templates = Jinja2Templates(directory="src/web/templates")

@router.post("/tools/{tool_id}/run", response_class=HTMLResponse)
@inject
async def run_tool(
    request: Request,
    tool_id: str,
    file: UploadFile = File(...),
    handler: FromDishka[RunToolCommandHandlerProtocol],
) -> HTMLResponse:
    result = await handler.handle(RunToolCommand(tool_id=tool_id, file=file))
    return templates.TemplateResponse(
        "tools/_result.html",
        {"request": request, "result": result},
    )
```

## 3. API Router Organization (optional)

```python
# api/v1/__init__.py
from fastapi import APIRouter
from src.api.v1.users import router as users_router
from src.api.v1.orders import router as orders_router

router = APIRouter()
router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(orders_router, prefix="/orders", tags=["orders"])
```

## 4. API Endpoint Pattern (optional)

```python
# api/v1/users.py
from fastapi import APIRouter, status
from dishka.integrations.fastapi import FromDishka, inject
from pydantic import BaseModel
from uuid import UUID

from src.protocols import UserServiceProtocol
from src.domain.errors import DomainError, ErrorCode
from src.domain.users.models import User

router = APIRouter()

# Request/Response DTOs
class CreateUserRequest(BaseModel):
    email: str
    name: str

class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str

    @classmethod
    def from_domain(cls, user: User) -> "UserResponse":
        return cls(id=user.id, email=user.email, name=user.name)

# Endpoints
@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_user(
    request: CreateUserRequest,
    service: FromDishka[UserServiceProtocol],
) -> UserResponse:
    user = await service.create(request)
    return UserResponse.from_domain(user)

@router.get("/{user_id}", response_model=UserResponse)
@inject
async def get_user(
    user_id: UUID,
    service: FromDishka[UserServiceProtocol],
) -> UserResponse:
    user = await service.get_by_id(user_id)
    if not user:
        raise DomainError(
            code=ErrorCode.USER_NOT_FOUND,
            message="User not found",
            details={"user_id": str(user_id)},
        )
    return UserResponse.from_domain(user)
```

## 5. Correlation Middleware

```python
# api/middleware/correlation.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from uuid import uuid4, UUID

class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID")
        if correlation_id:
            try:
                request.state.correlation_id = UUID(correlation_id)
            except ValueError:
                request.state.correlation_id = uuid4()
        else:
            request.state.correlation_id = uuid4()

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = str(request.state.correlation_id)
        return response
```

## 6. Error Handler Middleware

```python
# api/middleware/error_handler.py
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
import structlog

from src.domain.errors import DomainError, ErrorCode
from src.api.error_mapping import error_to_status

logger = structlog.get_logger()
templates = Jinja2Templates(directory="src/web/templates")

async def error_handler_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except DomainError as e:
        logger.warning(
            "Application error",
            error_code=e.code.value,
            message=e.message,
            correlation_id=str(getattr(request.state, "correlation_id", None)),
        )

        status_code = error_to_status(e.code)
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=status_code,
                content={
                    "error": {
                        "code": e.code.value,
                        "message": e.message,
                        "details": e.details,
                    }
                },
            )

        # Web UI: return an HTML page (or fragment for HTMX).
        return templates.TemplateResponse(
            request=request,
            name="shared/error.html",
            context={"error": e},
            status_code=status_code,
        )
    except Exception as e:
        logger.exception(
            "Unhandled exception",
            correlation_id=str(getattr(request.state, "correlation_id", None)),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "Internal server error",
                }
            },
        )
```

## 7. Configuration

```python
# config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # App
    APP_NAME: str = "myapp"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    ENABLE_DOCS: bool = True

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CONSUMER_GROUP: str = "myapp-consumer"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

## 8. Router/Page Size Limits

| Metric | Limit |
|--------|-------|
| LoC per API router | <150 |
| LoC per web module | <200 |
| Endpoints per module | <10 |
| Nesting depth | max 2 (`/api/v1/users`) |

Split large routers into submodules:

```text
api/v1/users/
├── __init__.py      # Router aggregation
├── crud.py          # CRUD endpoints
├── auth.py          # Auth-related endpoints
└── admin.py         # Admin endpoints
```

## 9. Validation Patterns

```python
# Request validation via Pydantic
class CreateOrderRequest(BaseModel):
    user_id: UUID
    items: list[OrderItemRequest]

    @field_validator("items")
    @classmethod
    def validate_items(cls, v):
        if not v:
            raise ValueError("Order must have at least one item")
        return v

# Path parameter validation
@router.get("/{order_id}")
async def get_order(
    order_id: UUID,  # Automatic UUID validation
    service: FromDishka[OrderServiceProtocol],
): ...

# Query parameter validation
@router.get("")
async def list_orders(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
): ...
```
