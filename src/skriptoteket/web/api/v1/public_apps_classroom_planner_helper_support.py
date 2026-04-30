"""Shared public Klassrumskartan helper route support.

Purpose:
  Keep anonymous helper request body caps, public app authorization, throttle
  checks, and redacted request metadata in one route-adjacent module used by
  direct-download exports and public guest share creation.

Relationships:
  - Used by `public_apps_classroom_planner_exports.py`.
  - Used by `public_apps_classroom_planner_shares.py`.
  - Depends only on web request metadata, settings, and public helper protocols.
"""

import structlog
from fastapi import Request

from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.public_helpers import PublicHelperThrottleProtocol
from skriptoteket.web.api.v1.public_apps_support import require_public_curated_app
from skriptoteket.web.request_metadata import get_client_ip, get_correlation_id, get_user_agent

logger = structlog.get_logger(__name__)

APP_ID = "classroom.group-seating-studio"


async def read_capped_json_body(*, request: Request, max_bytes: int, helper_name: str) -> bytes:
    """Read a required JSON request body without accepting oversized payloads."""

    body = bytearray()
    async for chunk in request.stream():
        if len(chunk) == 0:
            continue
        body.extend(chunk)
        if len(body) > max_bytes:
            raise DomainError(
                code=ErrorCode.PAYLOAD_TOO_LARGE,
                message="Public helper payload exceeds the allowed size.",
                details={
                    "app_id": APP_ID,
                    "helper_name": helper_name,
                    "reason_code": "public_helper_payload_too_large",
                    "max_bytes": max_bytes,
                },
            )
    if len(body) == 0:
        raise validation_error(
            "Request body is required.",
            details={
                "app_id": APP_ID,
                "helper_name": helper_name,
                "reason_code": "public_helper_empty_payload",
            },
        )
    return bytes(body)


def enforce_public_helper_rate_limit(
    *,
    request: Request,
    helper_name: str,
    max_requests: int,
    window_seconds: int,
    registry: CuratedAppRegistryProtocol,
    settings: Settings,
    clock: ClockProtocol,
    throttle: PublicHelperThrottleProtocol,
) -> tuple[str | None, str | None, str | None]:
    """Apply the shared anonymous helper throttle and return redacted metadata."""

    app = require_public_curated_app(app_id=APP_ID, registry=registry)
    client_ip = get_client_ip(request, settings=settings)
    user_agent = get_user_agent(request)
    correlation_id_uuid = get_correlation_id(request)
    correlation_id = str(correlation_id_uuid) if correlation_id_uuid is not None else None

    throttle_decision = throttle.evaluate_request(
        app_id=APP_ID,
        helper_name=helper_name,
        client_ip=client_ip,
        user_agent=user_agent,
        max_requests=max_requests,
        window_seconds=window_seconds,
        now=clock.now(),
    )
    if throttle_decision.is_rate_limited:
        logger.warning(
            "public_helper_request_denied",
            app_id=APP_ID,
            helper_name=helper_name,
            reason_code="public_helper_rate_limited",
            retry_after_seconds=throttle_decision.retry_after_seconds,
            correlation_id=correlation_id,
            client_ip=client_ip,
        )
        raise DomainError(
            code=ErrorCode.TOO_MANY_REQUESTS,
            message="Public helper rate limit exceeded.",
            details={
                "app_id": APP_ID,
                "helper_name": helper_name,
                "reason_code": "public_helper_rate_limited",
                "retry_after_seconds": throttle_decision.retry_after_seconds,
                "window_seconds": window_seconds,
                "max_requests": max_requests,
                "public_access_profile": app.public_access_profile,
            },
        )

    throttle.record_request(
        app_id=APP_ID,
        helper_name=helper_name,
        client_ip=client_ip,
        user_agent=user_agent,
        max_requests=max_requests,
        window_seconds=window_seconds,
        now=clock.now(),
    )
    return client_ip, user_agent, correlation_id
