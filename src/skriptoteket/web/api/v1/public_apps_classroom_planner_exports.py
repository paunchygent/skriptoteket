"""Public Klassrumskartan direct-download export routes for guest snapshots.

Purpose:
  Expose cookie-agnostic grouping and seating export helpers under the public
  Klassrumskartan namespace without weakening the authenticated export-job
  boundary.

Relationships:
  - Reuses the browser-owned guest snapshot request contracts from the
    application layer.
  - Reuses the public helper throttle and time-budget pattern already used by
    the public Smart helper routes.
  - Returns direct-download attachment responses only; it never creates jobs
    or Vault artifacts.
"""

import asyncio

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import Response
from pydantic import ValidationError

from skriptoteket.application.curated_apps.classroom_planner import (
    RunPublicGroupingExportHandler,
    RunPublicSeatingExportHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.public_export_contracts import (
    PublicGroupingExportRequest,
    PublicSeatingExportRequest,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.public_helpers import PublicHelperThrottleProtocol
from skriptoteket.web.api.v1.public_apps_support import require_public_curated_app
from skriptoteket.web.dishka_dependencies import FromDishka
from skriptoteket.web.request_metadata import get_client_ip, get_correlation_id, get_user_agent

logger = structlog.get_logger(__name__)

APP_ID = "classroom.group-seating-studio"
GROUPING_HELPER_NAME = "grouping_export"
SEATING_HELPER_NAME = "seating_export"

router = APIRouter(
    prefix=f"/api/v1/public/apps/{APP_ID}",
    tags=["public-apps", "classroom-planner"],
)


async def _read_capped_json_body(*, request: Request, max_bytes: int) -> bytes:
    body = bytearray()
    async for chunk in request.stream():
        if len(chunk) == 0:
            continue
        body.extend(chunk)
        if len(body) > max_bytes:
            raise DomainError(
                code=ErrorCode.PAYLOAD_TOO_LARGE,
                message="Public export helper payload exceeds the allowed size.",
                details={
                    "app_id": APP_ID,
                    "reason_code": "public_helper_payload_too_large",
                    "max_bytes": max_bytes,
                },
            )
    if len(body) == 0:
        raise validation_error(
            "Request body is required.",
            details={
                "app_id": APP_ID,
                "reason_code": "public_helper_empty_payload",
            },
        )
    return bytes(body)


def _enforce_rate_limit(
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


def _parse_grouping_export_request(*, body: bytes) -> PublicGroupingExportRequest:
    try:
        return PublicGroupingExportRequest.model_validate_json(body)
    except ValidationError as exc:
        raise validation_error(
            "Invalid public grouping export payload.",
            details={
                "app_id": APP_ID,
                "helper_name": GROUPING_HELPER_NAME,
                "reason_code": "public_helper_invalid_payload",
                "validation_error_count": len(exc.errors()),
            },
        ) from exc


def _parse_seating_export_request(*, body: bytes) -> PublicSeatingExportRequest:
    try:
        return PublicSeatingExportRequest.model_validate_json(body)
    except ValidationError as exc:
        raise validation_error(
            "Invalid public seating export payload.",
            details={
                "app_id": APP_ID,
                "helper_name": SEATING_HELPER_NAME,
                "reason_code": "public_helper_invalid_payload",
                "validation_error_count": len(exc.errors()),
            },
        ) from exc


@router.post("/grouping/export")
async def export_public_grouping(
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    clock: FromDishka[ClockProtocol],
    throttle: FromDishka[PublicHelperThrottleProtocol],
    handler: FromDishka[RunPublicGroupingExportHandler],
) -> Response:
    client_ip, _user_agent, correlation_id = _enforce_rate_limit(
        request=request,
        helper_name=GROUPING_HELPER_NAME,
        max_requests=settings.PUBLIC_HELPER_SMART_RUN_MAX_REQUESTS,
        window_seconds=settings.PUBLIC_HELPER_SMART_RUN_WINDOW_SECONDS,
        registry=registry,
        settings=settings,
        clock=clock,
        throttle=throttle,
    )
    body = await _read_capped_json_body(
        request=request,
        max_bytes=settings.PUBLIC_HELPER_SMART_RUN_MAX_REQUEST_BYTES,
    )
    payload = _parse_grouping_export_request(body=body)

    logger.info(
        "public_helper_request_started",
        app_id=APP_ID,
        helper_name=GROUPING_HELPER_NAME,
        payload_bytes=len(body),
        correlation_id=correlation_id,
        client_ip=client_ip,
    )
    try:
        async with asyncio.timeout(settings.PUBLIC_HELPER_SMART_RUN_TIMEOUT_SECONDS):
            result = await handler.handle(
                snapshot=payload.snapshot,
                expected_revision=payload.expected_revision,
                export_kind=payload.export_kind,
                paper_size=payload.paper_size,
            )
    except TimeoutError as exc:
        logger.warning(
            "public_helper_request_timed_out",
            app_id=APP_ID,
            helper_name=GROUPING_HELPER_NAME,
            reason_code="public_helper_time_budget_exceeded",
            time_budget_seconds=settings.PUBLIC_HELPER_SMART_RUN_TIMEOUT_SECONDS,
            correlation_id=correlation_id,
            client_ip=client_ip,
        )
        raise DomainError(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message="Public helper time budget exceeded.",
            details={
                "app_id": APP_ID,
                "helper_name": GROUPING_HELPER_NAME,
                "reason_code": "public_helper_time_budget_exceeded",
                "time_budget_seconds": settings.PUBLIC_HELPER_SMART_RUN_TIMEOUT_SECONDS,
            },
        ) from exc

    logger.info(
        "public_helper_request_completed",
        app_id=APP_ID,
        helper_name=GROUPING_HELPER_NAME,
        payload_bytes=len(body),
        correlation_id=correlation_id,
        client_ip=client_ip,
    )
    return Response(
        content=result.content,
        media_type=result.media_type,
        headers={"Content-Disposition": f'attachment; filename="{result.filename}"'},
    )


@router.post("/seating/export")
async def export_public_seating(
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    clock: FromDishka[ClockProtocol],
    throttle: FromDishka[PublicHelperThrottleProtocol],
    handler: FromDishka[RunPublicSeatingExportHandler],
) -> Response:
    client_ip, _user_agent, correlation_id = _enforce_rate_limit(
        request=request,
        helper_name=SEATING_HELPER_NAME,
        max_requests=settings.PUBLIC_HELPER_SMART_RUN_MAX_REQUESTS,
        window_seconds=settings.PUBLIC_HELPER_SMART_RUN_WINDOW_SECONDS,
        registry=registry,
        settings=settings,
        clock=clock,
        throttle=throttle,
    )
    body = await _read_capped_json_body(
        request=request,
        max_bytes=settings.PUBLIC_HELPER_SMART_RUN_MAX_REQUEST_BYTES,
    )
    payload = _parse_seating_export_request(body=body)

    logger.info(
        "public_helper_request_started",
        app_id=APP_ID,
        helper_name=SEATING_HELPER_NAME,
        payload_bytes=len(body),
        correlation_id=correlation_id,
        client_ip=client_ip,
    )
    try:
        async with asyncio.timeout(settings.PUBLIC_HELPER_SMART_RUN_TIMEOUT_SECONDS):
            result = await handler.handle(
                snapshot=payload.snapshot,
                expected_revision=payload.expected_revision,
                export_kind=payload.export_kind,
                layout_id=payload.layout_id,
                paper_size=payload.paper_size,
            )
    except TimeoutError as exc:
        logger.warning(
            "public_helper_request_timed_out",
            app_id=APP_ID,
            helper_name=SEATING_HELPER_NAME,
            reason_code="public_helper_time_budget_exceeded",
            time_budget_seconds=settings.PUBLIC_HELPER_SMART_RUN_TIMEOUT_SECONDS,
            correlation_id=correlation_id,
            client_ip=client_ip,
        )
        raise DomainError(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message="Public helper time budget exceeded.",
            details={
                "app_id": APP_ID,
                "helper_name": SEATING_HELPER_NAME,
                "reason_code": "public_helper_time_budget_exceeded",
                "time_budget_seconds": settings.PUBLIC_HELPER_SMART_RUN_TIMEOUT_SECONDS,
            },
        ) from exc

    logger.info(
        "public_helper_request_completed",
        app_id=APP_ID,
        helper_name=SEATING_HELPER_NAME,
        payload_bytes=len(body),
        correlation_id=correlation_id,
        client_ip=client_ip,
    )
    return Response(
        content=result.content,
        media_type=result.media_type,
        headers={"Content-Disposition": f'attachment; filename="{result.filename}"'},
    )
