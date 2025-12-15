from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    # Authentication (401)
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"

    # Authorization (403)
    FORBIDDEN = "FORBIDDEN"

    # Not Found (404)
    NOT_FOUND = "NOT_FOUND"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"

    # Conflict (409)
    CONFLICT = "CONFLICT"
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"

    # Service errors (503)
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

    # Validation (400)
    VALIDATION_ERROR = "VALIDATION_ERROR"

    # Server Errors (500)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"


class DomainError(Exception):
    """Framework-agnostic error used across layers.

    Do not store HTTP concerns here. Mapping happens in the web layer.
    """

    def __init__(
        self,
        *,
        code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def not_found(resource: str, resource_id: str) -> DomainError:
    return DomainError(
        code=ErrorCode.NOT_FOUND,
        message=f"{resource} not found: {resource_id}",
        details={"resource": resource, "id": resource_id},
    )


def validation_error(message: str, details: dict[str, Any] | None = None) -> DomainError:
    return DomainError(code=ErrorCode.VALIDATION_ERROR, message=message, details=details)
