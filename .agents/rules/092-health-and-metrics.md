---
id: "092-health-and-metrics"
type: "implementation"
created: 2025-12-20
scope: "backend"
---

# 092: Health Checks and Prometheus Metrics

HuleEdu-standard health check and metrics endpoints.

## 1. Health Check Endpoint

`GET /healthz` MUST return:

```json
{
  "service": "skriptoteket",
  "status": "healthy",
  "message": "Service is healthy",
  "version": "0.1.0",
  "environment": "production",
  "checks": {
    "service_responsive": true,
    "dependencies_available": true
  },
  "dependencies": {
    "database": {"status": "healthy"}
  }
}
```

### Status Values

| Status | HTTP Code | Meaning |
|--------|-----------|---------|
| `healthy` | 200 | All systems operational |
| `degraded` | 503 | Partial functionality |
| `unhealthy` | 503 | Service unable to process requests |

### Implementation

```python
# web/routes/observability.py
from fastapi import APIRouter
from skriptoteket.observability.health import HealthChecker

router = APIRouter()

@router.get("/healthz")
async def healthz(checker: FromDishka[HealthChecker]):
    result = await checker.check()
    status_code = 200 if result.status == "healthy" else 503
    return JSONResponse(content=result.model_dump(), status_code=status_code)
```

### Health Checker Pattern

```python
# observability/health.py
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

class HealthChecker:
    def __init__(self, session: AsyncSession, settings: Settings):
        self._session = session
        self._settings = settings

    async def check(self) -> HealthResult:
        db_status = await self._check_database()
        overall = "healthy" if db_status.status == "healthy" else "unhealthy"

        return HealthResult(
            service=self._settings.SERVICE_NAME,
            status=overall,
            version=self._settings.APP_VERSION,
            environment=self._settings.ENVIRONMENT,
            dependencies={"database": db_status},
        )

    async def _check_database(self) -> DependencyStatus:
        try:
            await asyncio.wait_for(
                self._session.execute(text("SELECT 1")),
                timeout=2.0,
            )
            return DependencyStatus(status="healthy")
        except Exception:
            return DependencyStatus(status="unhealthy")
```

## 2. Metrics Endpoint

`GET /metrics` MUST return Prometheus-compatible metrics.

### Required Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `skriptoteket_http_requests_total` | Counter | method, endpoint, status_code | Total HTTP requests |
| `skriptoteket_http_request_duration_seconds` | Histogram | method, endpoint | Request latency |

### Implementation

```python
# observability/metrics.py
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

http_requests_total = Counter(
    "skriptoteket_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration = Histogram(
    "skriptoteket_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)
```

### Metrics Middleware

```python
# web/middleware/metrics.py
import time
from starlette.requests import Request

EXCLUDED_PATHS = frozenset({"/healthz", "/metrics", "/static"})

async def metrics_middleware(request: Request, call_next):
    path = request.url.path

    # Skip metrics for observability endpoints
    if any(path.startswith(excluded) for excluded in EXCLUDED_PATHS):
        return await call_next(request)

    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start

    # Use route pattern, not raw path (avoid high cardinality)
    endpoint = _get_route_pattern(request)

    http_requests_total.labels(
        method=request.method,
        endpoint=endpoint,
        status_code=response.status_code,
    ).inc()

    http_request_duration.labels(
        method=request.method,
        endpoint=endpoint,
    ).observe(duration)

    return response
```

## 3. Label Cardinality Rules

FORBIDDEN: Using raw paths as labels (causes metric explosion)

```python
# BAD - high cardinality
labels(endpoint=f"/tools/{tool_id}")  # Each UUID creates new series!

# GOOD - use route pattern
labels(endpoint="/tools/{id}")  # Single series for all tool IDs
```

## 4. Excluded Paths

These paths MUST be excluded from metrics collection:
- `/healthz` - Health checks (high frequency, no business value)
- `/metrics` - Metrics endpoint itself
- `/static` - Static file serving

## 5. Prometheus Naming Conventions

| Component | Convention | Example |
|-----------|------------|---------|
| Namespace | Service name | `skriptoteket_` |
| Suffix (Counter) | `_total` | `skriptoteket_http_requests_total` |
| Suffix (Histogram) | `_seconds`, `_bytes` | `skriptoteket_http_request_duration_seconds` |
| Labels | snake_case | `status_code`, `method` |

## References

- ADR-0019: Health, metrics, and tracing endpoints
- Runbook: `docs/runbooks/runbook-observability-logging.md`
