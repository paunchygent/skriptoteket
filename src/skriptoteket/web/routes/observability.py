"""Observability endpoints: /healthz and /metrics.

Public endpoints (no authentication required) for monitoring infrastructure.

NOTE: Do NOT use `from __future__ import annotations` in router modules.
See .agent/rules/040-fastapi-blueprint.md (OpenAPI-safe typing).
"""

import asyncio

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.ext.asyncio import AsyncEngine

from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.infrastructure.session_files.usage import get_session_file_usage
from skriptoteket.observability.health import build_health_response, check_database, check_smtp
from skriptoteket.observability.metrics import get_metrics
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import SessionRepositoryProtocol, UserRepositoryProtocol

router = APIRouter(tags=["observability"])


@router.get("/healthz", response_class=JSONResponse)
@inject
async def healthz(
    engine: FromDishka[AsyncEngine],
    settings: FromDishka[Settings],
) -> JSONResponse:
    """HuleEdu standard health check endpoint.

    Returns:
        200 with JSON payload if healthy
        503 with JSON payload if degraded/unhealthy
    """
    db_status, db_error = await check_database(engine)
    smtp_status = None
    smtp_error = None

    if settings.HEALTHZ_SMTP_CHECK_ENABLED and settings.EMAIL_PROVIDER == "smtp":
        smtp_status, smtp_error = await check_smtp(settings)

    payload, status_code = build_health_response(
        service_name=settings.SERVICE_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        db_status=db_status,
        db_error=db_error,
        smtp_status=smtp_status,
        smtp_error=smtp_error,
    )

    return JSONResponse(content=payload, status_code=status_code)


@router.get("/metrics", response_class=Response)
@inject
async def metrics(
    settings: FromDishka[Settings],
    sessions: FromDishka[SessionRepositoryProtocol],
    users: FromDishka[UserRepositoryProtocol],
    clock: FromDishka[ClockProtocol],
) -> Response:
    """Prometheus metrics endpoint for scraping."""
    metrics = get_metrics()
    usage = await asyncio.to_thread(get_session_file_usage, artifacts_root=settings.ARTIFACTS_ROOT)
    now = clock.now()
    active_sessions = await sessions.count_active(now=now)
    users_by_role = await users.count_active_by_role()

    metrics["session_files_bytes_total"].set(usage.bytes_total)
    metrics["session_files_count"].set(usage.files)
    metrics["active_sessions"].set(active_sessions)
    for role in Role:
        metrics["users_by_role"].labels(role=role.value).set(users_by_role.get(role, 0))

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
