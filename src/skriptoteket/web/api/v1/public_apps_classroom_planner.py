"""Public Klassrumskartan helper routes with cookie-agnostic abuse controls.

Purpose:
  Expose the first public helper namespace for Klassrumskartan under
  `/api/v1/public/apps/classroom.group-seating-studio/...` without weakening
  the authenticated owner-scoped planner API.

Relationships:
  - Reads the canonical public-access profile from the curated-app registry.
  - Reuses `CreateClassListImportPreviewHandler` for stateless server-side
    roster parsing.
  - Enforces anonymous abuse controls, payload caps, MIME validation, and a
    request time budget before work reaches the import pipeline.
"""

import asyncio

import structlog
from fastapi import APIRouter, Request, UploadFile

from skriptoteket.application.curated_apps.classroom_planner.handlers.imports import (
    CreateClassListImportPreviewHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.import_contracts import (
    ClassListImportPreview,
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
HELPER_NAME = "roster_import_preview"
_GENERIC_CONTENT_TYPES = frozenset({"", "application/octet-stream"})
_ALLOWED_FILE_SUFFIXES = frozenset({".csv", ".pdf", ".tsv", ".txt", ".xls", ".xlsx"})
_ALLOWED_CONTENT_TYPES = frozenset(
    {
        "application/csv",
        "application/pdf",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/csv",
        "text/plain",
        "text/tab-separated-values",
    }
)

router = APIRouter(
    prefix=f"/api/v1/public/apps/{APP_ID}",
    tags=["public-apps", "classroom-planner"],
)


def _validated_filename(*, raw_filename: str | None) -> str:
    normalized = (raw_filename or "").strip()
    if not normalized:
        raise validation_error(
            "Filename is required.",
            details={
                "app_id": APP_ID,
                "helper_name": HELPER_NAME,
                "reason_code": "public_helper_missing_filename",
            },
        )

    lower_name = normalized.lower()
    if not any(lower_name.endswith(suffix) for suffix in _ALLOWED_FILE_SUFFIXES):
        raise DomainError(
            code=ErrorCode.UNSUPPORTED_MEDIA_TYPE,
            message="Unsupported file type for public roster import preview.",
            details={
                "app_id": APP_ID,
                "helper_name": HELPER_NAME,
                "reason_code": "public_helper_unsupported_file_type",
                "allowed_file_suffixes": sorted(_ALLOWED_FILE_SUFFIXES),
            },
        )
    return normalized


def _validated_content_type(*, raw_content_type: str | None) -> str:
    normalized = (raw_content_type or "application/octet-stream").strip().lower()
    if normalized in _GENERIC_CONTENT_TYPES or normalized in _ALLOWED_CONTENT_TYPES:
        return normalized or "application/octet-stream"

    raise DomainError(
        code=ErrorCode.UNSUPPORTED_MEDIA_TYPE,
        message="Unsupported content type for public roster import preview.",
        details={
            "app_id": APP_ID,
            "helper_name": HELPER_NAME,
            "reason_code": "public_helper_unsupported_content_type",
            "allowed_content_types": sorted(_ALLOWED_CONTENT_TYPES),
        },
    )


async def _read_capped_upload(*, file: UploadFile, max_bytes: int) -> bytes:
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise DomainError(
            code=ErrorCode.PAYLOAD_TOO_LARGE,
            message="Public roster import preview payload exceeds the allowed size.",
            details={
                "app_id": APP_ID,
                "helper_name": HELPER_NAME,
                "reason_code": "public_helper_payload_too_large",
                "max_bytes": max_bytes,
            },
        )
    if len(content) == 0:
        raise validation_error(
            "Uploaded file is empty.",
            details={
                "app_id": APP_ID,
                "helper_name": HELPER_NAME,
                "reason_code": "public_helper_empty_payload",
            },
        )
    return content


@router.post("/rosters/import-preview", response_model=ClassListImportPreview)
async def create_public_import_preview(
    request: Request,
    file: UploadFile,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    clock: FromDishka[ClockProtocol],
    throttle: FromDishka[PublicHelperThrottleProtocol],
    handler: FromDishka[CreateClassListImportPreviewHandler],
) -> ClassListImportPreview:
    app = require_public_curated_app(app_id=APP_ID, registry=registry)
    client_ip = get_client_ip(request, settings=settings)
    user_agent = get_user_agent(request)
    now = clock.now()
    correlation_id_uuid = get_correlation_id(request)
    correlation_id = str(correlation_id_uuid) if correlation_id_uuid is not None else None

    throttle_decision = throttle.evaluate_request(
        app_id=APP_ID,
        helper_name=HELPER_NAME,
        client_ip=client_ip,
        user_agent=user_agent,
        max_requests=settings.PUBLIC_HELPER_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.PUBLIC_HELPER_RATE_LIMIT_WINDOW_SECONDS,
        now=now,
    )
    if throttle_decision.is_rate_limited:
        logger.warning(
            "public_helper_request_denied",
            app_id=APP_ID,
            helper_name=HELPER_NAME,
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
                "helper_name": HELPER_NAME,
                "reason_code": "public_helper_rate_limited",
                "retry_after_seconds": throttle_decision.retry_after_seconds,
                "window_seconds": settings.PUBLIC_HELPER_RATE_LIMIT_WINDOW_SECONDS,
                "max_requests": settings.PUBLIC_HELPER_RATE_LIMIT_MAX_REQUESTS,
            },
        )

    throttle.record_request(
        app_id=APP_ID,
        helper_name=HELPER_NAME,
        client_ip=client_ip,
        user_agent=user_agent,
        max_requests=settings.PUBLIC_HELPER_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.PUBLIC_HELPER_RATE_LIMIT_WINDOW_SECONDS,
        now=now,
    )
    file_name = _validated_filename(raw_filename=file.filename)
    content_type = _validated_content_type(raw_content_type=file.content_type)
    content = await _read_capped_upload(
        file=file,
        max_bytes=settings.PUBLIC_HELPER_IMPORT_PREVIEW_MAX_FILE_BYTES,
    )

    logger.info(
        "public_helper_request_started",
        app_id=APP_ID,
        helper_name=HELPER_NAME,
        public_access_profile=app.public_access_profile,
        content_type=content_type,
        payload_bytes=len(content),
        correlation_id=correlation_id,
        client_ip=client_ip,
    )

    try:
        async with asyncio.timeout(settings.PUBLIC_HELPER_IMPORT_PREVIEW_TIMEOUT_SECONDS):
            preview = await handler.handle(
                file_content=content,
                file_name=file_name,
                content_type=content_type,
                correlation_id=correlation_id,
            )
    except TimeoutError as exc:
        logger.warning(
            "public_helper_request_timed_out",
            app_id=APP_ID,
            helper_name=HELPER_NAME,
            reason_code="public_helper_time_budget_exceeded",
            time_budget_seconds=settings.PUBLIC_HELPER_IMPORT_PREVIEW_TIMEOUT_SECONDS,
            correlation_id=correlation_id,
            client_ip=client_ip,
        )
        raise DomainError(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message="Public helper time budget exceeded.",
            details={
                "app_id": APP_ID,
                "helper_name": HELPER_NAME,
                "reason_code": "public_helper_time_budget_exceeded",
                "time_budget_seconds": settings.PUBLIC_HELPER_IMPORT_PREVIEW_TIMEOUT_SECONDS,
            },
        ) from exc

    logger.info(
        "public_helper_request_completed",
        app_id=APP_ID,
        helper_name=HELPER_NAME,
        parsed_students=len(preview.parsed_students),
        ambiguous_rows=len(preview.ambiguous_rows),
        correlation_id=correlation_id,
        client_ip=client_ip,
    )
    return preview
