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
from skriptoteket.web.api.v1.public_apps_classroom_planner_helper_support import (
    APP_ID,
    enforce_public_helper_rate_limit,
    logger,
    read_capped_json_body,
)
from skriptoteket.web.dishka_dependencies import FromDishka

GROUPING_HELPER_NAME = "grouping_export"
SEATING_HELPER_NAME = "seating_export"

router = APIRouter(
    prefix=f"/api/v1/public/apps/{APP_ID}",
    tags=["public-apps", "classroom-planner"],
)


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
    client_ip, _user_agent, correlation_id = enforce_public_helper_rate_limit(
        request=request,
        helper_name=GROUPING_HELPER_NAME,
        max_requests=settings.PUBLIC_HELPER_SMART_RUN_MAX_REQUESTS,
        window_seconds=settings.PUBLIC_HELPER_SMART_RUN_WINDOW_SECONDS,
        registry=registry,
        settings=settings,
        clock=clock,
        throttle=throttle,
    )
    body = await read_capped_json_body(
        request=request,
        max_bytes=settings.PUBLIC_HELPER_SMART_RUN_MAX_REQUEST_BYTES,
        helper_name=GROUPING_HELPER_NAME,
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
    client_ip, _user_agent, correlation_id = enforce_public_helper_rate_limit(
        request=request,
        helper_name=SEATING_HELPER_NAME,
        max_requests=settings.PUBLIC_HELPER_SMART_RUN_MAX_REQUESTS,
        window_seconds=settings.PUBLIC_HELPER_SMART_RUN_WINDOW_SECONDS,
        registry=registry,
        settings=settings,
        clock=clock,
        throttle=throttle,
    )
    body = await read_capped_json_body(
        request=request,
        max_bytes=settings.PUBLIC_HELPER_SMART_RUN_MAX_REQUEST_BYTES,
        helper_name=SEATING_HELPER_NAME,
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
