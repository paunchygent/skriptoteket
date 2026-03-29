from __future__ import annotations

from typing import cast

import pytest

from skriptoteket.config import Settings
from skriptoteket.observability.health import HealthPayload, build_health_response, check_smtp


def test_build_health_response_degraded_when_smtp_degraded() -> None:
    payload, status_code = build_health_response(
        service_name="skriptoteket",
        version=Settings().APP_VERSION,
        environment="test",
        db_status="healthy",
        db_error=None,
        smtp_status="degraded",
        smtp_error="SMTP unreachable",
    )
    detailed_payload = cast(HealthPayload, payload)

    assert status_code == 503
    assert detailed_payload["status"] == "degraded"
    assert detailed_payload["dependencies"]["smtp"]["status"] == "degraded"
    assert detailed_payload["checks"]["dependencies_available"] is False


def test_build_health_response_unhealthy_when_database_unhealthy() -> None:
    payload, status_code = build_health_response(
        service_name="skriptoteket",
        version=Settings().APP_VERSION,
        environment="test",
        db_status="unhealthy",
        db_error="DB down",
        smtp_status="healthy",
        smtp_error=None,
    )
    detailed_payload = cast(HealthPayload, payload)

    assert status_code == 503
    assert detailed_payload["status"] == "unhealthy"
    assert detailed_payload["dependencies"]["database"]["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_check_smtp_skips_when_email_provider_is_mock() -> None:
    settings = Settings().model_copy(update={"EMAIL_PROVIDER": "mock"})

    status, error = await check_smtp(settings)

    assert status == "healthy"
    assert error is None
