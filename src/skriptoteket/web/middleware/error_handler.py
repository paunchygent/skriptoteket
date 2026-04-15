"""Domain error handling for HTTP requests.

Purpose:
    Convert framework-agnostic domain errors into JSON HTTP responses while
    preserving correlation metadata and recording sanitized local RBAC denials.

Relationships:
    - Used by the FastAPI app as the central error boundary.
    - Observes role-guard `DomainError` payloads without coupling domain code
      to FastAPI, Prometheus, or Structlog.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable
from uuid import UUID

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse, Response

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.auth_outcomes import AuthOutcomeRecorderProtocol
from skriptoteket.web.error_mapping import error_to_status

logger = structlog.get_logger(__name__)


@runtime_checkable
class AuthOutcomeContainerProtocol(Protocol):
    """Request-scoped DI container shape needed by the auth outcome boundary."""

    async def get(self, dependency_type: object) -> AuthOutcomeRecorderProtocol: ...


async def error_handler_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Map domain and unexpected errors to safe JSON responses."""
    try:
        return await call_next(request)
    except DomainError as exc:
        correlation_id = _request_correlation_id(request)
        status_code = error_to_status(exc.code)

        if exc.code is ErrorCode.FORBIDDEN:
            await _record_rbac_denial_if_needed(
                request=request,
                error=exc,
                correlation_id=correlation_id,
            )

        logger.warning(
            "Application error",
            error_code=exc.code.value,
            http_status=status_code,
            method=request.method,
            path=request.url.path,
            correlation_id=str(correlation_id) if correlation_id else None,
        )

        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": exc.code.value,
                    "message": exc.message,
                    "details": exc.details,
                },
                "correlation_id": str(correlation_id) if correlation_id else None,
            },
        )
    except Exception:
        correlation_id = _request_correlation_id(request)
        logger.exception(
            "Unhandled exception",
            method=request.method,
            path=request.url.path,
            correlation_id=str(correlation_id) if correlation_id else None,
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


async def _record_rbac_denial_if_needed(
    *,
    request: Request,
    error: DomainError,
    correlation_id: UUID | None,
) -> None:
    denial = _rbac_denial_from_details(error.details)
    if denial is None:
        return

    recorder = await _resolve_auth_outcome_recorder(request)
    if recorder is None:
        return

    required_role, actual_role = denial
    recorder.record_rbac_decision(
        decision="denied",
        required_role=required_role,
        actual_role=actual_role,
        route_family=_route_family(request),
        correlation_id=correlation_id,
    )


async def _resolve_auth_outcome_recorder(
    request: Request,
) -> AuthOutcomeRecorderProtocol | None:
    container = getattr(request.state, "dishka_container", None)
    if not isinstance(container, AuthOutcomeContainerProtocol):
        return None
    return await container.get(AuthOutcomeRecorderProtocol)


def _rbac_denial_from_details(details: dict[str, object]) -> tuple[str, str] | None:
    actual_role = _string_detail(details.get("actual_role")) or _string_detail(
        details.get("actor_role")
    )
    if actual_role is None:
        return None

    required_role = _string_detail(details.get("required_role"))
    if required_role is None:
        required_role = _required_role_from_roles(details.get("required_roles"))
    if required_role is None:
        return None

    return required_role, actual_role


def _required_role_from_roles(value: object) -> str | None:
    if not isinstance(value, list):
        return None
    roles = frozenset(role for item in value if (role := _string_detail(item)) is not None)
    if not roles:
        return None
    if roles == {"admin", "superuser"}:
        return "admin_or_superuser"
    if len(roles) == 1:
        return next(iter(roles))
    return "unknown"


def _string_detail(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return value


def _route_family(request: Request) -> str:
    path = request.url.path
    if path.startswith("/api/v1/admin"):
        return "admin"
    if path.startswith("/api/v1/catalog") or path.startswith("/api/v1/tools"):
        return "catalog"
    if path.startswith("/api/v1/apps"):
        return "curated_app"
    if path.startswith("/api/v1/editor"):
        return "editor"
    if path.startswith("/api/v1/profile") or path.startswith("/api/v1/me"):
        return "profile"
    if path.startswith("/api/v1/suggestions"):
        return "suggestions"
    if path.startswith("/tools") or path.startswith("/runs"):
        return "interactive_tool"
    return "api"


def _request_correlation_id(request: Request) -> UUID | None:
    correlation_id = getattr(request.state, "correlation_id", None)
    if isinstance(correlation_id, UUID):
        return correlation_id
    return None
