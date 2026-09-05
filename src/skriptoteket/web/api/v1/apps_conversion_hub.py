"""Conversion Hub curated app API routes (Skriptoteket).
Purpose:
  Expose a bespoke Conversion Hub API surface under `/api/v1/apps/<app_id>/...`
  while keeping Skriptoteket as the owner of job identity, authorization, and
  artifact downloads.
Relationships:
  - App registry entry: `src/skriptoteket/infrastructure/curated_apps/registry.py`
  - Application handlers: `application.curated_apps.handlers.conversion_hub_jobs`
  - Upstream conversion engine: Sir Convert-a-Lot v2
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import JsonValue

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJobSpecV2,
    ConversionHubJobStatusResult,
    ConversionHubListRoutesResult,
    ConversionHubOutputFormatV2,
    ConversionHubRouteV2,
    ConversionHubSourceFormatV2,
    ConversionHubSubmitResult,
    build_conversion_hub_v2_job_spec,
)
from skriptoteket.application.curated_apps.conversion_hub_saved_artifacts import (
    SaveConversionHubArtifactResult,
)
from skriptoteket.application.curated_apps.document_converter import (
    DOCUMENT_CONVERTER_MAX_BATCH_ITEMS,
    DocumentConverterJobStatusResult,
    DocumentConverterSubmitResult,
    SaveDocumentConverterArtifactResult,
    validate_document_converter_batch_count,
    validate_document_converter_route,
    validate_document_converter_upload,
)
from skriptoteket.application.curated_apps.document_converter import (
    list_document_converter_routes as build_document_converter_routes,
)
from skriptoteket.application.curated_apps.exam_conversion import (
    ExamConverterConversionSubmitResult,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_document_converter import (
    DownloadDocumentConverterArtifactHandler,
    GetDocumentConverterJobHandler,
    SaveDocumentConverterArtifactHandler,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import (
    ConversionHubUpload,
    CreateConversionHubJobsHandler,
    DownloadConversionHubArtifactHandler,
    GetConversionHubJobHandler,
)
from skriptoteket.application.curated_apps.handlers.document_converter_jobs import (
    CreateDocumentConverterJobsHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_converter_conversions import (
    CreateExamConverterConversionJobsHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_converter_product import (
    ExamConverterProductHandler,
    ExamConverterProductResult,
    SaveExamConverterLocalArtifactHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.web.api.v1.apps_conversion_hub_access import (
    APP_ID,
    require_conversion_hub_access,
)
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.content_disposition import attachment_content_disposition
from skriptoteket.web.dishka_dependencies import FromDishka
from skriptoteket.web.request_metadata import get_correlation_id
from skriptoteket.web.uploads import read_upload_files

_MAX_WAIT_SECONDS = 20
router = APIRouter(prefix=f"/api/v1/apps/{APP_ID}", tags=["apps"])


def _require_app_access(*, registry: CuratedAppRegistryProtocol, user: User) -> None:
    require_conversion_hub_access(registry=registry, user=user)


def _list_supported_routes() -> list[ConversionHubRouteV2]:
    # Mirror the Sir Convert-a-Lot v2 allowed route set (domain/specs_v2.py).
    return [
        ConversionHubRouteV2(
            source_format=ConversionHubSourceFormatV2.PDF,
            output_format=ConversionHubOutputFormatV2.MD,
            title="PDF -> Markdown",
        ),
        ConversionHubRouteV2(
            source_format=ConversionHubSourceFormatV2.PDF,
            output_format=ConversionHubOutputFormatV2.DOCX,
            title="PDF -> DOCX",
        ),
        ConversionHubRouteV2(
            source_format=ConversionHubSourceFormatV2.DOCX,
            output_format=ConversionHubOutputFormatV2.MD,
            title="DOCX -> Markdown",
        ),
        ConversionHubRouteV2(
            source_format=ConversionHubSourceFormatV2.DOCX,
            output_format=ConversionHubOutputFormatV2.PDF,
            title="DOCX -> PDF",
        ),
        ConversionHubRouteV2(
            source_format=ConversionHubSourceFormatV2.MD,
            output_format=ConversionHubOutputFormatV2.PDF,
            title="Markdown -> PDF",
        ),
        ConversionHubRouteV2(
            source_format=ConversionHubSourceFormatV2.MD,
            output_format=ConversionHubOutputFormatV2.DOCX,
            title="Markdown -> DOCX",
        ),
        ConversionHubRouteV2(
            source_format=ConversionHubSourceFormatV2.HTML,
            output_format=ConversionHubOutputFormatV2.MD,
            title="HTML -> Markdown",
        ),
        ConversionHubRouteV2(
            source_format=ConversionHubSourceFormatV2.HTML,
            output_format=ConversionHubOutputFormatV2.PDF,
            title="HTML -> PDF",
        ),
        ConversionHubRouteV2(
            source_format=ConversionHubSourceFormatV2.HTML,
            output_format=ConversionHubOutputFormatV2.DOCX,
            title="HTML -> DOCX",
        ),
    ]


def _validate_route_supported(spec: ConversionHubJobSpecV2) -> None:
    allowed = {(r.source_format, r.output_format) for r in _list_supported_routes()}
    route = (spec.source_format, spec.output_format)
    if route not in allowed:
        route_str = f"{spec.source_format.value} -> {spec.output_format.value}"
        raise validation_error(f"Unsupported v2 conversion route: {route_str}")


@router.get("/routes", response_model=ConversionHubListRoutesResult)
async def list_routes(
    registry: FromDishka[CuratedAppRegistryProtocol],
    user: User = Depends(require_app_user_api),
) -> ConversionHubListRoutesResult:
    _require_app_access(registry=registry, user=user)
    return ConversionHubListRoutesResult(routes=_list_supported_routes())


@router.get("/document-converter/routes", response_model=ConversionHubListRoutesResult)
async def list_document_converter_routes(
    registry: FromDishka[CuratedAppRegistryProtocol],
    user: User = Depends(require_app_user_api),
) -> ConversionHubListRoutesResult:
    _require_app_access(registry=registry, user=user)
    return build_document_converter_routes()


@router.post("/jobs", response_model=ConversionHubSubmitResult)
async def submit_jobs(
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[CreateConversionHubJobsHandler],
    job_spec_json: str = Form(..., min_length=2),
    files: list[UploadFile] = File(...),
    wait_seconds: int = Form(0),
    user: User = Depends(require_app_user_api),
) -> ConversionHubSubmitResult:
    _require_app_access(registry=registry, user=user)
    if wait_seconds < 0 or wait_seconds > _MAX_WAIT_SECONDS:
        raise validation_error(f"wait_seconds must be between 0 and {_MAX_WAIT_SECONDS}.")
    try:
        spec = ConversionHubJobSpecV2.model_validate_json(job_spec_json)
    except Exception as exc:
        raise validation_error("Invalid job_spec JSON.") from exc
    _validate_route_supported(spec)
    if not files:
        raise validation_error("At least one file must be provided.")
    correlation_id_uuid = get_correlation_id(request)
    correlation_id = str(correlation_id_uuid) if correlation_id_uuid is not None else None
    uploads: list[ConversionHubUpload] = []
    for upload in files:
        if upload.filename is None or not upload.filename:
            raise validation_error("Uploaded file is missing a filename.")
        build_conversion_hub_v2_job_spec(spec=spec, filename=upload.filename)
        await upload.seek(0)
        uploads.append(
            ConversionHubUpload(
                filename=upload.filename,
                content_type=upload.content_type or "application/octet-stream",
                file_bytes=await upload.read(),
            )
        )
    return await handler.handle(
        actor=user,
        spec=spec,
        uploads=uploads,
        wait_seconds=wait_seconds,
        correlation_id=correlation_id,
        build_job_spec=build_conversion_hub_v2_job_spec,
    )


@router.post("/document-converter/jobs", response_model=DocumentConverterSubmitResult)
async def submit_document_converter_job(
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[CreateDocumentConverterJobsHandler],
    settings: FromDishka[Settings],
    job_spec_json: str = Form(..., min_length=2),
    files: list[UploadFile] = File(...),
    wait_seconds: int = Form(0),
    user: User = Depends(require_app_user_api),
) -> DocumentConverterSubmitResult:
    _require_app_access(registry=registry, user=user)
    if wait_seconds < 0 or wait_seconds > _MAX_WAIT_SECONDS:
        raise validation_error(f"wait_seconds must be between 0 and {_MAX_WAIT_SECONDS}.")
    try:
        spec = ConversionHubJobSpecV2.model_validate_json(job_spec_json)
    except Exception as exc:
        raise validation_error("Invalid job_spec JSON.") from exc
    validate_document_converter_route(spec)
    validate_document_converter_batch_count(files_count=len(files))

    validated_uploads: list[tuple[str, str]] = []
    for upload in files:
        filename, content_type = validate_document_converter_upload(
            spec=spec,
            filename=upload.filename,
            content_type=upload.content_type,
        )
        build_conversion_hub_v2_job_spec(spec=spec, filename=filename)
        validated_uploads.append((filename, content_type))

    input_files = await read_upload_files(
        files=files,
        max_files=DOCUMENT_CONVERTER_MAX_BATCH_ITEMS,
        max_file_bytes=settings.UPLOAD_MAX_FILE_BYTES,
        max_total_bytes=settings.UPLOAD_MAX_TOTAL_BYTES,
        default_filename="document-converter-input.bin",
    )
    correlation_id_uuid = get_correlation_id(request)
    correlation_id = str(correlation_id_uuid) if correlation_id_uuid is not None else None
    return await handler.handle(
        actor=user,
        spec=spec,
        uploads=[
            ConversionHubUpload(
                filename=validated_uploads[index][0],
                content_type=validated_uploads[index][1],
                file_bytes=input_file[1],
            )
            for index, input_file in enumerate(input_files)
        ],
        wait_seconds=wait_seconds,
        correlation_id=correlation_id,
        build_job_spec=build_conversion_hub_v2_job_spec,
    )


@router.post(
    "/exam-converter/jobs/{job_id}/artifacts/{artifact_key}/save",
    response_model=SaveConversionHubArtifactResult,
)
async def save_local_exam_converter_artifact(
    job_id: UUID,
    artifact_key: str,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[SaveExamConverterLocalArtifactHandler],
    user: User = Depends(require_app_user_api),
) -> SaveConversionHubArtifactResult:
    _require_app_access(registry=registry, user=user)
    return await handler.handle(actor=user, job_id=job_id, artifact_key=artifact_key)


@router.post(
    "/exam-converter/conversions",
    response_model=ExamConverterConversionSubmitResult,
)
async def submit_exam_converter_conversion(
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[CreateExamConverterConversionJobsHandler],
    settings: FromDishka[Settings],
    idempotency_key: Annotated[str, Form(min_length=1, max_length=128)],
    file: UploadFile = File(...),
    ingestion_overlay: UploadFile | None = File(None),
    advisory_retry_attempt: Annotated[int | None, Form(ge=1)] = None,
    user: User = Depends(require_app_user_api),
) -> ExamConverterConversionSubmitResult:
    _require_app_access(registry=registry, user=user)
    if file.filename is None or not file.filename:
        raise validation_error("Uploaded file is missing a filename.")
    if not file.filename.lower().endswith(".dxe"):
        raise validation_error("Endast DigiExam-exporter (.dxe) stöds.")
    correlation_id_uuid = get_correlation_id(request)
    correlation_id = str(correlation_id_uuid) if correlation_id_uuid is not None else None
    input_files = await read_upload_files(
        files=[file],
        max_files=1,
        max_file_bytes=settings.UPLOAD_MAX_FILE_BYTES,
        max_total_bytes=settings.UPLOAD_MAX_TOTAL_BYTES,
        default_filename="exam-converter-input.dxe",
    )
    overlay_bytes: bytes | None = None
    if ingestion_overlay is not None:
        overlay_files = await read_upload_files(
            files=[ingestion_overlay],
            max_files=1,
            max_file_bytes=settings.UPLOAD_MAX_FILE_BYTES,
            max_total_bytes=settings.UPLOAD_MAX_TOTAL_BYTES,
            default_filename="ingestion-overlay.json",
        )
        overlay_bytes = overlay_files[0][1]
    return await handler.handle(
        actor=user,
        upload=ConversionHubUpload(
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            file_bytes=input_files[0][1],
        ),
        overlay_bytes=overlay_bytes,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        advisory_retry_attempt=advisory_retry_attempt,
    )


@router.get(
    "/exam-converter/jobs/{job_id}/result",
    response_model=ExamConverterProductResult,
)
async def get_exam_converter_result(
    job_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ExamConverterProductHandler],
    user: User = Depends(require_app_user_api),
) -> ExamConverterProductResult:
    _require_app_access(registry=registry, user=user)
    return await handler.result(actor=user, job_id=job_id)


@router.get("/exam-converter/jobs/{job_id}/artifacts")
async def get_exam_converter_artifacts(
    job_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ExamConverterProductHandler],
    user: User = Depends(require_app_user_api),
) -> dict[str, JsonValue]:
    _require_app_access(registry=registry, user=user)
    return await handler.manifest(actor=user, job_id=job_id)


@router.get("/exam-converter/jobs/{job_id}/artifacts/{artifact_key}")
async def download_exam_converter_named_artifact(
    job_id: UUID,
    artifact_key: str,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ExamConverterProductHandler],
    user: User = Depends(require_app_user_api),
) -> Response:
    _require_app_access(registry=registry, user=user)
    artifact = await handler.named_artifact(
        actor=user,
        job_id=job_id,
        artifact_key=artifact_key,
    )
    return Response(
        content=artifact.content,
        media_type=artifact.content_type,
        headers={
            "Content-Disposition": attachment_content_disposition(filename=artifact.filename),
            "Cache-Control": "no-store",
        },
    )


@router.get("/exam-converter/jobs/{job_id}/source-state")
async def get_exam_converter_source_state(
    job_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ExamConverterProductHandler],
    user: User = Depends(require_app_user_api),
) -> dict[str, JsonValue]:
    _require_app_access(registry=registry, user=user)
    return await handler.source_state(actor=user, job_id=job_id)


@router.post("/exam-converter/jobs/{job_id}/replay")
async def replay_exam_converter_corrections(
    job_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ExamConverterProductHandler],
    user: User = Depends(require_app_user_api),
) -> dict[str, JsonValue]:
    _require_app_access(registry=registry, user=user)
    return await handler.replay(actor=user, job_id=job_id)


@router.get(
    "/document-converter/jobs/{job_id}",
    response_model=DocumentConverterJobStatusResult,
)
async def get_document_converter_job_status(
    job_id: UUID,
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[GetDocumentConverterJobHandler],
    user: User = Depends(require_app_user_api),
) -> DocumentConverterJobStatusResult:
    _require_app_access(registry=registry, user=user)
    correlation_id_uuid = get_correlation_id(request)
    correlation_id = str(correlation_id_uuid) if correlation_id_uuid is not None else None
    return await handler.handle(actor=user, job_id=job_id, correlation_id=correlation_id)


@router.get("/document-converter/jobs/{job_id}/artifact")
async def download_document_converter_artifact(
    job_id: UUID,
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[DownloadDocumentConverterArtifactHandler],
    filename_stem: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    user: User = Depends(require_app_user_api),
) -> Response:
    _require_app_access(registry=registry, user=user)
    correlation_id_uuid = get_correlation_id(request)
    correlation_id = str(correlation_id_uuid) if correlation_id_uuid is not None else None
    filename, content_type, content = await handler.handle(
        actor=user,
        job_id=job_id,
        correlation_id=correlation_id,
        filename_stem=filename_stem,
    )
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.post(
    "/document-converter/jobs/{job_id}/artifact/save",
    response_model=SaveDocumentConverterArtifactResult,
)
async def save_document_converter_artifact(
    job_id: UUID,
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[SaveDocumentConverterArtifactHandler],
    filename_stem: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    user: User = Depends(require_app_user_api),
) -> SaveDocumentConverterArtifactResult:
    _require_app_access(registry=registry, user=user)
    correlation_id_uuid = get_correlation_id(request)
    correlation_id = str(correlation_id_uuid) if correlation_id_uuid is not None else None
    return await handler.handle(
        actor=user,
        job_id=job_id,
        correlation_id=correlation_id,
        filename_stem=filename_stem,
    )


@router.get("/jobs/{job_id}", response_model=ConversionHubJobStatusResult)
async def get_job_status(
    job_id: UUID,
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[GetConversionHubJobHandler],
    user: User = Depends(require_app_user_api),
) -> ConversionHubJobStatusResult:
    _require_app_access(registry=registry, user=user)
    correlation_id_uuid = get_correlation_id(request)
    correlation_id = str(correlation_id_uuid) if correlation_id_uuid is not None else None
    return await handler.handle(actor=user, job_id=job_id, correlation_id=correlation_id)


@router.get("/jobs/{job_id}/artifact")
async def download_artifact(
    job_id: UUID,
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[DownloadConversionHubArtifactHandler],
    user: User = Depends(require_app_user_api),
) -> Response:
    _require_app_access(registry=registry, user=user)
    correlation_id_uuid = get_correlation_id(request)
    correlation_id = str(correlation_id_uuid) if correlation_id_uuid is not None else None
    filename, content_type, content = await handler.handle(
        actor=user,
        job_id=job_id,
        correlation_id=correlation_id,
    )
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
