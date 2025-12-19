"""Health check utilities for Skriptoteket.

Provides HuleEdu-compliant health check logic with database connectivity checks.
"""

from __future__ import annotations

import asyncio
from typing import Literal, TypedDict

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = structlog.get_logger(__name__)

# Database health check timeout (2s to avoid blocking healthcheck)
DB_HEALTH_CHECK_TIMEOUT = 2.0

HealthStatus = Literal["healthy", "degraded", "unhealthy"]


class DependencyStatus(TypedDict):
    status: HealthStatus


class Dependency(DependencyStatus, total=False):
    error: str


class HealthPayload(TypedDict):
    service: str
    status: HealthStatus
    message: str
    version: str
    environment: str
    checks: dict[str, bool]
    dependencies: dict[str, Dependency]


async def check_database(engine: AsyncEngine) -> tuple[HealthStatus, str | None]:
    """Check database connectivity with timeout.

    Args:
        engine: SQLAlchemy async engine

    Returns:
        Tuple of (status, error_message). Error is None if healthy.
    """
    try:
        async with asyncio.timeout(DB_HEALTH_CHECK_TIMEOUT):
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
        return "healthy", None
    except asyncio.TimeoutError:
        return "unhealthy", "Database check timed out"
    except Exception as e:
        return "unhealthy", str(e)


def build_health_response(
    service_name: str,
    version: str,
    environment: str,
    db_status: HealthStatus,
    db_error: str | None,
) -> tuple[HealthPayload, int]:
    """Build HuleEdu-compliant health response.

    Args:
        service_name: Service identifier (e.g., "skriptoteket")
        version: Application version
        environment: Deployment environment
        db_status: Database health status
        db_error: Database error message (None if healthy)

    Returns:
        Tuple of (payload_dict, http_status_code)
    """
    checks: dict[str, bool] = {
        "service_responsive": True,
        "dependencies_available": db_status == "healthy",
    }

    dependencies: dict[str, Dependency] = {}
    if db_error:
        dependencies["database"] = {"status": db_status, "error": db_error}
        logger.warning("Health check: database unhealthy", error=db_error)
    else:
        dependencies["database"] = {"status": db_status}

    overall_status: HealthStatus = "healthy" if db_status == "healthy" else "unhealthy"

    payload: HealthPayload = {
        "service": service_name,
        "status": overall_status,
        "message": f"Service is {overall_status}",
        "version": version,
        "environment": environment,
        "checks": checks,
        "dependencies": dependencies,
    }

    status_code = 200 if overall_status == "healthy" else 503
    return payload, status_code
