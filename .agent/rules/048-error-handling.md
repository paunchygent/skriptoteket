---
id: "048-error-handling"
type: "implementation"
created: 2025-12-13
scope: "backend"
---

# 048: Structured Error Handling

## 1. Error Code Enum

```python
# errors.py
from enum import Enum

class ErrorCode(str, Enum):
    # Validation (400)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"

    # Authentication (401)
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_TOKEN = "INVALID_TOKEN"

    # Authorization (403)
    FORBIDDEN = "FORBIDDEN"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"

    # Not Found (404)
    NOT_FOUND = "NOT_FOUND"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"

    # Conflict (409)
    CONFLICT = "CONFLICT"
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"

    # Business Logic (422)
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"

    # Server Errors (500)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"

    # External Service (502/503)
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
```

## 2. Base Error Class

```python
# domain/errors.py (domain/application layer)
from typing import Any

class DomainError(Exception):
    """Framework-agnostic error used across layers.

    NOTE: Do not store HTTP concerns here. HTTP mapping happens in the web/api layer.
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

# Convenience constructors
def validation_error(message: str, details: dict[str, Any] | None = None) -> DomainError:
    return DomainError(code=ErrorCode.VALIDATION_ERROR, message=message, details=details)

def not_found_error(resource: str, resource_id: str) -> DomainError:
    return DomainError(
        code=ErrorCode.NOT_FOUND,
        message=f"{resource} not found: {resource_id}",
        details={"resource": resource, "id": resource_id},
    )

def business_error(message: str, details: dict[str, Any] | None = None) -> DomainError:
    return DomainError(code=ErrorCode.BUSINESS_RULE_VIOLATION, message=message, details=details)
```

## 3. Error Response Schema

```python
# api/schemas/errors.py
from pydantic import BaseModel
from typing import Any

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}

class ErrorResponse(BaseModel):
    error: ErrorDetail
    correlation_id: str | None = None
```

## 4. HTTP Mapping (web/api layer only)

Map `ErrorCode` → HTTP status in the interface layer (never in domain):

```python
# api/error_mapping.py (or web/error_mapping.py)
from src.domain.errors import ErrorCode

ERROR_CODE_TO_STATUS: dict[ErrorCode, int] = {
    ErrorCode.VALIDATION_ERROR: 400,
    ErrorCode.INVALID_INPUT: 400,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.DUPLICATE_ENTRY: 409,
    ErrorCode.BUSINESS_RULE_VIOLATION: 422,
    ErrorCode.TIMEOUT: 504,
}

def error_to_status(code: ErrorCode) -> int:
    return ERROR_CODE_TO_STATUS.get(code, 500)
```

## 5. Error Handler Middleware (API / JSON)

```python
# api/middleware/error_handler.py
from fastapi import Request
from fastapi.responses import JSONResponse
import structlog

from src.domain.errors import DomainError, ErrorCode
from src.api.error_mapping import error_to_status

logger = structlog.get_logger()

async def error_handler_middleware(request: Request, call_next):
    correlation_id = getattr(request.state, "correlation_id", None)

    try:
        return await call_next(request)

    except DomainError as e:
        logger.warning(
            "Application error",
            error_code=e.code.value,
            message=e.message,
            details=e.details,
            correlation_id=str(correlation_id),
        )
        return JSONResponse(
            status_code=error_to_status(e.code),
            content={
                "error": {
                    "code": e.code.value,
                    "message": e.message,
                    "details": e.details,
                },
                "correlation_id": str(correlation_id) if correlation_id else None,
            },
        )

    except Exception as e:
        logger.exception(
            "Unhandled exception",
            error_type=type(e).__name__,
            correlation_id=str(correlation_id),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "Internal server error",
                    "details": {},
                },
                "correlation_id": str(correlation_id) if correlation_id else None,
            },
        )
```

## 6. Error Handling (Web / HTML)

For server-rendered pages and HTMX partials, map `DomainError` to an HTML response (page or fragment). Keep the mapping and templates in the `web/` layer.

## 7. Domain Layer Error Handling

Raise `DomainError` for business rule violations (no HTTP concerns):

```python
# domain/orders/services.py
async def complete_order(self, order_id: UUID) -> Order:
    order = await self._repo.get_by_id(order_id)
    if not order:
        raise not_found_error("Order", str(order_id))

    if order.status == OrderStatus.CANCELLED:
        raise business_error(
            "Cannot complete cancelled order",
            {"order_id": str(order_id), "current_status": order.status.value},
        )

    order.status = OrderStatus.COMPLETED
    return await self._repo.update(order)
```

## 8. Infrastructure Layer Error Handling

Wrap external errors into `DomainError` and let the interface layer map to HTTP:

```python
# infrastructure/clients/payment_client.py
async def charge(self, amount: float, user_id: UUID) -> PaymentResult:
    try:
        response = await self._http_client.post(
            f"{self._base_url}/charge",
            json={"amount": amount, "user_id": str(user_id)},
        )
        response.raise_for_status()
        return PaymentResult.model_validate(response.json())

    except httpx.TimeoutException as e:
        raise DomainError(code=ErrorCode.TIMEOUT, message="Payment service timeout")

    except httpx.HTTPStatusError as e:
        raise DomainError(
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message="Payment service error",
            details={"service": "payment", "status": e.response.status_code},
        )
```

## 9. Correlation ID Propagation

Correlation ID is attached at the boundary (middleware), not stored in domain errors:

```python
# Usage in middleware/logging
async def handler(request: Request):
    try:
        ...
    except IntegrityError:
        raise DomainError(code=ErrorCode.DUPLICATE_ENTRY, message="Duplicate entry")
```

## 10. Logging Standards

```python
# Always log with correlation_id and error_code
logger.error(
    "Failed to process order",
    error_code=e.code.value,
    order_id=str(order_id),
    correlation_id=str(correlation_id),
    exc_info=True,  # Include traceback for unexpected errors
)
```

## 11. Forbidden Patterns

| Pattern | Why Forbidden |
|---------|---------------|
| `try/except pass` | Silently swallows errors |
| Logging without correlation_id | Breaks traceability |
| Raw exception messages to client | Leaks implementation details |
| Catching `Exception` without re-raising | Hides bugs |
| Catching `Exception` without logging | Silently swallows errors; use `logger.exception()` |
| HTTP status from domain layer | Domain shouldn't know HTTP |
| Repository code mapping to HTTP | Mapping belongs in web/api layer |

## 12. Middleware Exception Logging

Always log unhandled exceptions in error handler middleware with full traceback:

```python
except Exception as exc:
    logger.exception(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
    )
```

Using `logger.exception()` automatically includes the traceback. Never use bare `print()` statements for error logging in production code.
