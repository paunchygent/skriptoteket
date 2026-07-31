"""Public Exam Converter runtime routes.

Purpose:
  Expose the approved anonymous Exam Converter capability under the public
  Conversion Hub namespace while keeping grants, upstream authority, and
  artifacts server-side.

Relationships:
  - Reads active capability metadata from the curated-app registry.
  - Calls `PublicExamConverterRuntimeHandler` for submit/poll/result/manifest.
  - Shares public helper throttle and redacted request metadata conventions.
"""

import asyncio
import json
from collections.abc import Awaitable
from typing import TypeVar
from uuid import uuid4

import structlog
from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import Response

from skriptoteket.application.curated_apps.handlers.public_exam_converter_jobs import (
    APP_ID,
    CAPABILITY,
    PublicExamConverterRuntimeHandler,
)
from skriptoteket.application.curated_apps.public_exam_converter import (
    PublicExamConverterArtifactManifestResponse,
    PublicExamConverterJobResultResponse,
    PublicExamConverterJobStatusResponse,
    PublicExamConverterSubmitResponse,
    PublicExamConverterTarget,
    PublicExamConverterUpload,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.models import CuratedAppPublicRuntimeStatus
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.public_helpers import PublicHelperThrottleProtocol
from skriptoteket.web.api.v1.public_apps import EXAM_CONVERTER_PUBLIC_API_NAMESPACE
from skriptoteket.web.api.v1.public_apps_support import require_public_curated_app_capability
from skriptoteket.web.dishka_dependencies import FromDishka
from skriptoteket.web.request_metadata import get_client_ip, get_correlation_id, get_user_agent

logger = structlog.get_logger(__name__)

_T = TypeVar("_T")

SUBMIT_HELPER_NAME = "exam_converter_submit"
STATUS_HELPER_NAME = "exam_converter_status"
RESULT_HELPER_NAME = "exam_converter_result"
ARTIFACT_MANIFEST_HELPER_NAME = "exam_converter_artifact_manifest"
ARTIFACT_DOWNLOAD_HELPER_NAME = "exam_converter_artifact_download"
_DXE_SUFFIX = ".dxe"
_PDF_SUFFIX = ".pdf"
_GENERIC_CONTENT_TYPES = frozenset({"", "application/octet-stream"})
_DXE_CONTENT_TYPES = frozenset({"application/octet-stream"})
_PDF_CONTENT_TYPES = frozenset({"application/pdf"})

router = APIRouter(
    prefix=EXAM_CONVERTER_PUBLIC_API_NAMESPACE,
    tags=["public-apps", "exam-converter"],
)


def _require_active_exam_converter(
    *,
    registry: CuratedAppRegistryProtocol,
) -> None:
    _app, capability = require_public_curated_app_capability(
        app_id=APP_ID,
        scope=CAPABILITY,
        registry=registry,
    )
    if capability.runtime_status is not CuratedAppPublicRuntimeStatus.ACTIVE:
        raise DomainError(
            code=ErrorCode.NOT_FOUND,
            message="Public Exam Converter runtime is not active.",
            details={
                "app_id": APP_ID,
                "capability": CAPABILITY,
                "reason_code": "public_exam_converter_runtime_inactive",
            },
        )


def _parse_targets(*, targets_json: str | None) -> tuple[PublicExamConverterTarget, ...]:
    if targets_json is None or targets_json.strip() == "":
        return (
            PublicExamConverterTarget.EXAMNET_PDF,
            PublicExamConverterTarget.QTI_PACKAGE,
        )
    try:
        payload = json.loads(targets_json)
    except json.JSONDecodeError as exc:
        raise validation_error(
            "Invalid Exam Converter target payload.",
            details={
                "app_id": APP_ID,
                "capability": CAPABILITY,
                "reason_code": "public_exam_converter_invalid_target",
            },
        ) from exc
    if not isinstance(payload, list) or not payload:
        raise validation_error(
            "At least one Exam Converter target is required.",
            details={
                "app_id": APP_ID,
                "capability": CAPABILITY,
                "reason_code": "public_exam_converter_invalid_target",
            },
        )
    targets: list[PublicExamConverterTarget] = []
    for raw_target in payload:
        if not isinstance(raw_target, str):
            raise _invalid_target()
        try:
            target = PublicExamConverterTarget(raw_target)
        except ValueError as exc:
            raise _invalid_target() from exc
        if target not in targets:
            targets.append(target)
    return tuple(targets)


def _invalid_target() -> DomainError:
    return validation_error(
        "Unsupported Exam Converter target.",
        details={
            "app_id": APP_ID,
            "capability": CAPABILITY,
            "reason_code": "public_exam_converter_invalid_target",
            "allowed_targets": [target.value for target in PublicExamConverterTarget],
        },
    )


async def _read_upload(
    *,
    upload: UploadFile,
    field_name: str,
    required_suffix: str,
    allowed_content_types: frozenset[str],
    max_bytes: int,
) -> PublicExamConverterUpload:
    filename = (upload.filename or "").strip()
    if not filename:
        raise validation_error(
            "Uploaded file is missing a filename.",
            details={
                "app_id": APP_ID,
                "capability": CAPABILITY,
                "reason_code": "public_exam_converter_missing_filename",
                "field": field_name,
            },
        )
    if not filename.lower().endswith(required_suffix):
        raise DomainError(
            code=ErrorCode.UNSUPPORTED_MEDIA_TYPE,
            message="Unsupported file type for public Exam Converter.",
            details={
                "app_id": APP_ID,
                "capability": CAPABILITY,
                "reason_code": "public_exam_converter_unsupported_file_type",
                "field": field_name,
            },
        )
    content_type = (upload.content_type or "application/octet-stream").strip().lower()
    if content_type not in allowed_content_types and content_type not in _GENERIC_CONTENT_TYPES:
        raise DomainError(
            code=ErrorCode.UNSUPPORTED_MEDIA_TYPE,
            message="Unsupported content type for public Exam Converter.",
            details={
                "app_id": APP_ID,
                "capability": CAPABILITY,
                "reason_code": "public_exam_converter_unsupported_content_type",
                "field": field_name,
            },
        )
    content = await upload.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise DomainError(
            code=ErrorCode.PAYLOAD_TOO_LARGE,
            message="Public Exam Converter payload exceeds the allowed size.",
            details={
                "app_id": APP_ID,
                "capability": CAPABILITY,
                "reason_code": "public_exam_converter_payload_too_large",
                "field": field_name,
                "max_bytes": max_bytes,
            },
        )
    if len(content) == 0:
        raise validation_error(
            "Uploaded file is empty.",
            details={
                "app_id": APP_ID,
                "capability": CAPABILITY,
                "reason_code": "public_exam_converter_empty_payload",
                "field": field_name,
            },
        )
    return PublicExamConverterUpload(
        filename=filename,
        content_type=content_type or "application/octet-stream",
        file_bytes=content,
    )


def _enforce_anonymous_rate_limit(
    *,
    request: Request,
    registry: CuratedAppRegistryProtocol,
    settings: Settings,
    clock: ClockProtocol,
    throttle: PublicHelperThrottleProtocol,
    helper_name: str,
) -> tuple[str | None, str]:
    _require_active_exam_converter(registry=registry)
    client_ip = get_client_ip(request, settings=settings)
    user_agent = get_user_agent(request)
    correlation_id_uuid = get_correlation_id(request)
    correlation_id = str(correlation_id_uuid) if correlation_id_uuid is not None else str(uuid4())
    now = clock.now()
    decision = throttle.evaluate_request(
        app_id=APP_ID,
        helper_name=helper_name,
        client_ip=client_ip,
        user_agent=user_agent,
        max_requests=settings.PUBLIC_EXAM_CONVERTER_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.PUBLIC_EXAM_CONVERTER_RATE_LIMIT_WINDOW_SECONDS,
        now=now,
    )
    if decision.is_rate_limited:
        logger.warning(
            "public_exam_converter_request_denied",
            app_id=APP_ID,
            reason_code="public_exam_converter_rate_limited",
            retry_after_seconds=decision.retry_after_seconds,
            correlation_id=correlation_id,
            client_ip=client_ip,
        )
        raise DomainError(
            code=ErrorCode.TOO_MANY_REQUESTS,
            message="Public Exam Converter rate limit exceeded.",
            details={
                "app_id": APP_ID,
                "capability": CAPABILITY,
                "reason_code": "public_exam_converter_rate_limited",
                "retry_after_seconds": decision.retry_after_seconds,
            },
        )
    throttle.record_request(
        app_id=APP_ID,
        helper_name=helper_name,
        client_ip=client_ip,
        user_agent=user_agent,
        max_requests=settings.PUBLIC_EXAM_CONVERTER_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.PUBLIC_EXAM_CONVERTER_RATE_LIMIT_WINDOW_SECONDS,
        now=now,
    )
    return client_ip, correlation_id


async def _with_request_time_budget(
    *,
    settings: Settings,
    work: Awaitable[_T],
) -> _T:
    try:
        async with asyncio.timeout(settings.PUBLIC_EXAM_CONVERTER_REQUEST_TIME_BUDGET_SECONDS):
            return await work
    except TimeoutError as exc:
        raise DomainError(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message="Public Exam Converter time budget exceeded.",
            details={
                "app_id": APP_ID,
                "capability": CAPABILITY,
                "reason_code": "public_exam_converter_time_budget_exceeded",
            },
        ) from exc


@router.post("/jobs", response_model=PublicExamConverterSubmitResponse)
async def submit_public_exam_converter_job(
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    clock: FromDishka[ClockProtocol],
    throttle: FromDishka[PublicHelperThrottleProtocol],
    handler: FromDishka[PublicExamConverterRuntimeHandler],
    source_dxe: UploadFile = File(...),
    graded_result_pdf: UploadFile | None = File(None),
    targets_json: str | None = Form(None),
) -> PublicExamConverterSubmitResponse:
    client_ip, correlation_id = _enforce_anonymous_rate_limit(
        request=request,
        registry=registry,
        settings=settings,
        clock=clock,
        throttle=throttle,
        helper_name=SUBMIT_HELPER_NAME,
    )
    active_jobs = await handler.count_active_jobs()
    if active_jobs >= settings.PUBLIC_EXAM_CONVERTER_CONCURRENCY_LIMIT:
        raise DomainError(
            code=ErrorCode.TOO_MANY_REQUESTS,
            message="Public Exam Converter concurrency limit exceeded.",
            details={
                "app_id": APP_ID,
                "capability": CAPABILITY,
                "reason_code": "public_exam_converter_concurrency_limited",
            },
        )
    targets = _parse_targets(targets_json=targets_json)
    source = await _read_upload(
        upload=source_dxe,
        field_name="source_dxe",
        required_suffix=_DXE_SUFFIX,
        allowed_content_types=_DXE_CONTENT_TYPES,
        max_bytes=settings.PUBLIC_EXAM_CONVERTER_SOURCE_DXE_MAX_BYTES,
    )
    graded = None
    if graded_result_pdf is not None:
        graded = await _read_upload(
            upload=graded_result_pdf,
            field_name="graded_result_pdf",
            required_suffix=_PDF_SUFFIX,
            allowed_content_types=_PDF_CONTENT_TYPES,
            max_bytes=settings.PUBLIC_EXAM_CONVERTER_GRADED_RESULT_PDF_MAX_BYTES,
        )
    aggregate_bytes = len(source.file_bytes) + len(graded.file_bytes if graded is not None else b"")
    if aggregate_bytes > settings.PUBLIC_EXAM_CONVERTER_AGGREGATE_MAX_BYTES:
        raise DomainError(
            code=ErrorCode.PAYLOAD_TOO_LARGE,
            message="Public Exam Converter aggregate payload exceeds the allowed size.",
            details={
                "app_id": APP_ID,
                "capability": CAPABILITY,
                "reason_code": "public_exam_converter_payload_too_large",
                "field": "aggregate",
                "max_bytes": settings.PUBLIC_EXAM_CONVERTER_AGGREGATE_MAX_BYTES,
            },
        )
    logger.info(
        "public_exam_converter_request_started",
        app_id=APP_ID,
        target_count=len(targets),
        payload_bytes=aggregate_bytes,
        correlation_id=correlation_id,
        client_ip=client_ip,
    )
    return await _with_request_time_budget(
        settings=settings,
        work=handler.submit(
            source_dxe=source,
            graded_result_pdf=graded,
            targets=targets,
            correlation_id=correlation_id,
            artifact_ttl_seconds=settings.PUBLIC_EXAM_CONVERTER_ARTIFACT_TTL_SECONDS,
            api_namespace=EXAM_CONVERTER_PUBLIC_API_NAMESPACE,
        ),
    )


@router.get("/jobs/{public_job_id}", response_model=PublicExamConverterJobStatusResponse)
async def get_public_exam_converter_job_status(
    public_job_id: str,
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    clock: FromDishka[ClockProtocol],
    throttle: FromDishka[PublicHelperThrottleProtocol],
    handler: FromDishka[PublicExamConverterRuntimeHandler],
) -> PublicExamConverterJobStatusResponse:
    _client_ip, correlation_id = _enforce_anonymous_rate_limit(
        request=request,
        registry=registry,
        settings=settings,
        clock=clock,
        throttle=throttle,
        helper_name=STATUS_HELPER_NAME,
    )
    return await _with_request_time_budget(
        settings=settings,
        work=handler.get_status(public_job_id=public_job_id, correlation_id=correlation_id),
    )


@router.get("/jobs/{public_job_id}/result", response_model=PublicExamConverterJobResultResponse)
async def get_public_exam_converter_job_result(
    public_job_id: str,
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    clock: FromDishka[ClockProtocol],
    throttle: FromDishka[PublicHelperThrottleProtocol],
    handler: FromDishka[PublicExamConverterRuntimeHandler],
) -> PublicExamConverterJobResultResponse:
    _client_ip, correlation_id = _enforce_anonymous_rate_limit(
        request=request,
        registry=registry,
        settings=settings,
        clock=clock,
        throttle=throttle,
        helper_name=RESULT_HELPER_NAME,
    )
    return await _with_request_time_budget(
        settings=settings,
        work=handler.get_result(
            public_job_id=public_job_id,
            correlation_id=correlation_id,
            api_namespace=EXAM_CONVERTER_PUBLIC_API_NAMESPACE,
        ),
    )


@router.get(
    "/jobs/{public_job_id}/artifacts",
    response_model=PublicExamConverterArtifactManifestResponse,
)
async def get_public_exam_converter_artifacts(
    public_job_id: str,
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    clock: FromDishka[ClockProtocol],
    throttle: FromDishka[PublicHelperThrottleProtocol],
    handler: FromDishka[PublicExamConverterRuntimeHandler],
) -> PublicExamConverterArtifactManifestResponse:
    _client_ip, correlation_id = _enforce_anonymous_rate_limit(
        request=request,
        registry=registry,
        settings=settings,
        clock=clock,
        throttle=throttle,
        helper_name=ARTIFACT_MANIFEST_HELPER_NAME,
    )
    return await _with_request_time_budget(
        settings=settings,
        work=handler.get_artifact_manifest(
            public_job_id=public_job_id,
            correlation_id=correlation_id,
            api_namespace=EXAM_CONVERTER_PUBLIC_API_NAMESPACE,
        ),
    )


@router.get("/jobs/{public_job_id}/artifacts/{artifact_key}/download")
async def download_public_exam_converter_artifact(
    public_job_id: str,
    artifact_key: str,
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    clock: FromDishka[ClockProtocol],
    throttle: FromDishka[PublicHelperThrottleProtocol],
    handler: FromDishka[PublicExamConverterRuntimeHandler],
) -> Response:
    _client_ip, correlation_id = _enforce_anonymous_rate_limit(
        request=request,
        registry=registry,
        settings=settings,
        clock=clock,
        throttle=throttle,
        helper_name=ARTIFACT_DOWNLOAD_HELPER_NAME,
    )
    artifact = await _with_request_time_budget(
        settings=settings,
        work=handler.download_artifact(
            public_job_id=public_job_id,
            artifact_key=artifact_key,
            correlation_id=correlation_id,
        ),
    )
    return Response(
        content=artifact.content,
        media_type=artifact.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{artifact.filename}"',
            "Cache-Control": "no-store",
        },
    )
