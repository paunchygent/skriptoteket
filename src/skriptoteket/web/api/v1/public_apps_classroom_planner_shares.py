"""Public Klassrumskartan share-link helper routes.

Purpose:
  Expose the ADR-0084 guest `Dela länk` helper boundary for grouping and
  seating snapshots without using authenticated APIs, SPA fallback, or
  account-owned rows.

Relationships:
  - Reuses public helper throttle/body-cap support.
  - Calls public guest share handlers from the classroom-planner application.
  - Returns copyable public share URLs through `PUBLIC_APP_BASE_URL`.
"""

import asyncio

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, ValidationError

from skriptoteket.application.curated_apps.classroom_planner import (
    CreatePublicGuestGroupingShareHandler,
    CreatePublicGuestSeatingShareHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.public_share_contracts import (
    PublicGuestShareRequest,
    PublicGuestShareResult,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.public_helpers import PublicHelperThrottleProtocol
from skriptoteket.web.api.v1.apps_classroom_planner_share_contracts import (
    ClassroomPlannerShareArtifactDto,
    serialize_share_artifact,
)
from skriptoteket.web.api.v1.public_apps_classroom_planner_helper_support import (
    APP_ID,
    enforce_public_helper_rate_limit,
    logger,
    read_capped_json_body,
)
from skriptoteket.web.dishka_dependencies import FromDishka
from skriptoteket.web.spa_metadata import absolute_public_url

GROUPING_SHARE_HELPER_NAME = "grouping_share"
SEATING_SHARE_HELPER_NAME = "seating_share"

router = APIRouter(
    prefix=f"/api/v1/public/apps/{APP_ID}",
    tags=["public-apps", "classroom-planner"],
)


class CreatedPublicGuestShareDto(BaseModel):
    """Serialize a newly created public guest share link."""

    model_config = ConfigDict(frozen=True)

    artifact: ClassroomPlannerShareArtifactDto
    public_path: str
    public_url: str
    public_revoke_secret: str
    superseded_previous: bool
    reused_client_operation: bool


def _parse_public_share_request(*, body: bytes, helper_name: str) -> PublicGuestShareRequest:
    try:
        return PublicGuestShareRequest.model_validate_json(body)
    except ValidationError as exc:
        raise validation_error(
            "Invalid public share payload.",
            details={
                "app_id": APP_ID,
                "helper_name": helper_name,
                "reason_code": "public_helper_invalid_payload",
                "validation_error_count": len(exc.errors()),
            },
        ) from exc


def _serialize_public_share_result(
    result: PublicGuestShareResult,
    *,
    public_app_base_url: str,
) -> CreatedPublicGuestShareDto:
    public_url = absolute_public_url(
        public_base_url=public_app_base_url,
        path=result.public_path,
    )
    return CreatedPublicGuestShareDto(
        artifact=serialize_share_artifact(
            result.artifact,
            public_app_base_url=public_app_base_url,
        ),
        public_path=result.public_path,
        public_url=public_url,
        public_revoke_secret=result.public_revoke_secret,
        superseded_previous=result.superseded_previous,
        reused_client_operation=result.reused_client_operation,
    )


async def _create_public_share(
    *,
    request: Request,
    helper_name: str,
    registry: CuratedAppRegistryProtocol,
    settings: Settings,
    clock: ClockProtocol,
    throttle: PublicHelperThrottleProtocol,
    handler: CreatePublicGuestGroupingShareHandler | CreatePublicGuestSeatingShareHandler,
) -> CreatedPublicGuestShareDto:
    client_ip, _user_agent, correlation_id = enforce_public_helper_rate_limit(
        request=request,
        helper_name=helper_name,
        max_requests=settings.PUBLIC_HELPER_SHARE_MAX_REQUESTS,
        window_seconds=settings.PUBLIC_HELPER_SHARE_WINDOW_SECONDS,
        registry=registry,
        settings=settings,
        clock=clock,
        throttle=throttle,
    )
    body = await read_capped_json_body(
        request=request,
        max_bytes=settings.PUBLIC_HELPER_SHARE_MAX_REQUEST_BYTES,
        helper_name=helper_name,
    )
    payload = _parse_public_share_request(body=body, helper_name=helper_name)

    logger.info(
        "public_helper_request_started",
        app_id=APP_ID,
        helper_name=helper_name,
        payload_bytes=len(body),
        correlation_id=correlation_id,
        client_ip=client_ip,
    )
    try:
        async with asyncio.timeout(settings.PUBLIC_HELPER_SHARE_TIMEOUT_SECONDS):
            result = await handler.handle(request=payload)
    except TimeoutError as exc:
        logger.warning(
            "public_helper_request_timed_out",
            app_id=APP_ID,
            helper_name=helper_name,
            reason_code="public_helper_time_budget_exceeded",
            time_budget_seconds=settings.PUBLIC_HELPER_SHARE_TIMEOUT_SECONDS,
            correlation_id=correlation_id,
            client_ip=client_ip,
        )
        raise DomainError(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message="Public helper time budget exceeded.",
            details={
                "app_id": APP_ID,
                "helper_name": helper_name,
                "reason_code": "public_helper_time_budget_exceeded",
                "time_budget_seconds": settings.PUBLIC_HELPER_SHARE_TIMEOUT_SECONDS,
            },
        ) from exc

    logger.info(
        "public_helper_request_completed",
        app_id=APP_ID,
        helper_name=helper_name,
        payload_bytes=len(body),
        correlation_id=correlation_id,
        client_ip=client_ip,
        superseded_previous=result.superseded_previous,
        reused_client_operation=result.reused_client_operation,
    )
    return _serialize_public_share_result(
        result,
        public_app_base_url=settings.PUBLIC_APP_BASE_URL,
    )


@router.post("/grouping/share", response_model=CreatedPublicGuestShareDto)
async def create_public_guest_grouping_share(
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    clock: FromDishka[ClockProtocol],
    throttle: FromDishka[PublicHelperThrottleProtocol],
    handler: FromDishka[CreatePublicGuestGroupingShareHandler],
) -> CreatedPublicGuestShareDto:
    return await _create_public_share(
        request=request,
        helper_name=GROUPING_SHARE_HELPER_NAME,
        registry=registry,
        settings=settings,
        clock=clock,
        throttle=throttle,
        handler=handler,
    )


@router.post("/seating/share", response_model=CreatedPublicGuestShareDto)
async def create_public_guest_seating_share(
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    clock: FromDishka[ClockProtocol],
    throttle: FromDishka[PublicHelperThrottleProtocol],
    handler: FromDishka[CreatePublicGuestSeatingShareHandler],
) -> CreatedPublicGuestShareDto:
    return await _create_public_share(
        request=request,
        helper_name=SEATING_SHARE_HELPER_NAME,
        registry=registry,
        settings=settings,
        clock=clock,
        throttle=throttle,
        handler=handler,
    )
