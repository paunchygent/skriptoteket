from __future__ import annotations

import pytest

from skriptoteket.config import Settings
from skriptoteket.observability.health import build_health_response, check_smtp


def test_build_health_response_degraded_when_smtp_degraded() -> None:
    payload, status_code = build_health_response(
        service_name="skriptoteket",
        version="0.1.0",
        environment="test",
        db_status="healthy",
        db_error=None,
        smtp_status="degraded",
        smtp_error="SMTP unreachable",
    )

    assert status_code == 503
    assert payload["status"] == "degraded"
    assert payload["dependencies"]["smtp"]["status"] == "degraded"
    assert payload["checks"]["dependencies_available"] is False


def test_build_health_response_unhealthy_when_database_unhealthy() -> None:
    payload, status_code = build_health_response(
        service_name="skriptoteket",
        version="0.1.0",
        environment="test",
        db_status="unhealthy",
        db_error="DB down",
        smtp_status="healthy",
        smtp_error=None,
    )

    assert status_code == 503
    assert payload["status"] == "unhealthy"
    assert payload["dependencies"]["database"]["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_check_smtp_skips_when_email_provider_is_mock() -> None:
    settings = Settings().model_copy(update={"EMAIL_PROVIDER": "mock"})

    status, error = await check_smtp(settings)

    assert status == "healthy"
    assert error is None
