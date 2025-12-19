"""Observability endpoints: /healthz and /metrics.

Public endpoints (no authentication required) for monitoring infrastructure.

NOTE: Do NOT use `from __future__ import annotations` in router modules.
See .agent/rules/040-fastapi-blueprint.md (OpenAPI-safe typing).
"""

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.ext.asyncio import AsyncEngine

from skriptoteket.config import Settings
from skriptoteket.observability.health import build_health_response, check_database

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

    payload, status_code = build_health_response(
        service_name=settings.SERVICE_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        db_status=db_status,
        db_error=db_error,
    )

    return JSONResponse(content=payload, status_code=status_code)


@router.get("/metrics", response_class=Response)
async def metrics() -> Response:
    """Prometheus metrics endpoint for scraping."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
