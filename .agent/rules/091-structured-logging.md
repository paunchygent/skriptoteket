---
id: "091-structured-logging"
type: "implementation"
created: 2025-12-20
scope: "backend"
---

# 091: Structured Logging

HuleEdu-compatible structured logging with correlation ID propagation.

## 1. JSON Log Shape (Required Fields)

Production logs MUST be JSON with these fields:

```json
{
  "timestamp": "2025-12-20T10:30:00.123456Z",
  "level": "info",
  "event": "User logged in",
  "service.name": "skriptoteket",
  "deployment.environment": "production",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO 8601 | RFC 3339 timestamp with microseconds |
| `level` | string | `debug`, `info`, `warning`, `error`, `critical` |
| `event` | string | Human-readable log message |
| `service.name` | string | Service identifier |
| `deployment.environment` | string | `development`, `staging`, `production` |

### Optional Fields (when available)

| Field | Type | Description |
|-------|------|-------------|
| `correlation_id` | UUID | Request correlation ID |
| `trace_id` | hex string | OpenTelemetry trace ID (32 chars) |
| `span_id` | hex string | OpenTelemetry span ID (16 chars) |

## 2. Correlation ID Middleware

```python
# web/middleware/correlation.py
from contextvars import ContextVar
from uuid import UUID, uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

correlation_id_var: ContextVar[UUID | None] = ContextVar("correlation_id", default=None)

class CorrelationMiddleware(BaseHTTPMiddleware):
    header_name = "X-Correlation-ID"

    async def dispatch(self, request: Request, call_next):
        # Extract or generate correlation ID
        header_value = request.headers.get(self.header_name)
        try:
            correlation_id = UUID(header_value) if header_value else uuid4()
        except ValueError:
            correlation_id = uuid4()

        # Bind to context var
        token = correlation_id_var.set(correlation_id)
        try:
            response = await call_next(request)
            response.headers[self.header_name] = str(correlation_id)
            return response
        finally:
            correlation_id_var.reset(token)
```

## 3. Structlog Configuration

```python
# observability/logging.py
import structlog
from skriptoteket.config import Settings

def configure_logging(settings: Settings) -> None:
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.LOG_FORMAT == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(settings.LOG_LEVEL),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

## 4. Binding Correlation ID to Logs

```python
# In request handlers or services
import structlog
from skriptoteket.web.middleware.correlation import correlation_id_var

logger = structlog.get_logger()

async def handle_request():
    correlation_id = correlation_id_var.get()
    structlog.contextvars.bind_contextvars(correlation_id=str(correlation_id))

    logger.info("Processing request", user_id=str(user.id))
```

## 5. Sensitive Data Redaction

The logging configuration MUST include automatic redaction for sensitive keys:

```python
REDACTED_KEYS = frozenset({
    "password", "token", "secret",
    "api_key", "api-key", "x-api-key",
    "authorization", "credential", "bearer",
    "cookie", "session",
})

def redact_sensitive(_, __, event_dict: dict) -> dict:
    for key in event_dict:
        if key.lower() in REDACTED_KEYS:
            event_dict[key] = "[REDACTED]"
    return event_dict
```

## 6. What MUST NOT Be Logged

| Category | Examples | Reason |
|----------|----------|--------|
| Credentials | passwords, tokens, API keys | Security |
| PII | emails, names, student data | GDPR/privacy |
| File contents | uploaded documents | Data leakage |
| Request bodies | form data with user input | May contain PII |

## 7. Log Level Guidelines

| Level | Use Case |
|-------|----------|
| `debug` | Detailed diagnostic information |
| `info` | Normal operation events (request handled, job completed) |
| `warning` | Recoverable issues (rate limit approaching, retry) |
| `error` | Errors that need attention (failed request, exception) |
| `critical` | System-level failures (database down, config missing) |

## 8. Forbidden Patterns

| Pattern | Why Forbidden |
|---------|---------------|
| `print()` statements | Not structured, not captured |
| Logging without correlation_id | Breaks request traceability |
| Logging PII (emails, names) | GDPR violation |
| Bare `except: pass` | Swallows errors silently |

## References

- ADR-0018: Structured logging and correlation
- Runbook: `docs/runbooks/runbook-observability-logging.md`
