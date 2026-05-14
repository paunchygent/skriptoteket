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

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import Response

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJobSpecV2,
    ConversionHubJobStatusResult,
    ConversionHubListRoutesResult,
    ConversionHubOutputFormatV2,
    ConversionHubRouteV2,
    ConversionHubSourceFormatV2,
    ConversionHubSubmitResult,
)
from skriptoteket.application.curated_apps.conversion_hub_saved_artifacts import (
    ConversionHubSirConvertArtifactSaveMetadata,
    SaveConversionHubSirConvertArtifactCommand,
    SaveConversionHubSirConvertArtifactResult,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_artifact_saves import (
    SaveConversionHubSirConvertArtifactHandler,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import (
    ConversionHubUpload,
    CreateConversionHubJobsHandler,
    DownloadConversionHubArtifactHandler,
    GetConversionHubJobHandler,
)
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.dishka_dependencies import FromDishka
from skriptoteket.web.request_metadata import get_correlation_id

APP_ID = "documents.conversion_hub"
_MAX_WAIT_SECONDS = 20
router = APIRouter(prefix=f"/api/v1/apps/{APP_ID}", tags=["apps"])


def _require_app_access(*, registry: CuratedAppRegistryProtocol, user: User) -> None:
    app = registry.get_by_app_id(app_id=APP_ID)
    if app is None:
        raise not_found("CuratedApp", APP_ID)
    require_at_least_role(user=user, role=app.min_role)


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


def _build_v2_job_spec(*, spec: ConversionHubJobSpecV2, filename: str) -> dict[str, object]:
    if spec.output_format.value != "pdf" and spec.pdf_layout is not None:
        raise validation_error("pdf_layout is only supported for PDF outputs.")
    job_spec: dict[str, object] = {
        "api_version": "v2",
        "source": {
            "kind": "upload",
            "filename": filename,
            "format": spec.source_format.value,
        },
        "conversion": {
            "output_format": spec.output_format.value,
            "css_filenames": [],
            "pdf_layout": spec.pdf_layout.model_dump(mode="json")
            if spec.pdf_layout is not None
            else None,
            "template": None,
            "reference_docx_filename": None,
        },
        "pdf_options": None,
        "execution": None,
        "retention": {"pin": False},
    }
    if spec.source_format.value == "pdf":
        # Provide safe defaults required by Sir Convert-a-Lot v2 for PDF sources.
        job_spec["pdf_options"] = {
            "backend_strategy": "auto",
            "ocr_mode": "auto",
            "table_mode": "accurate",
            "normalize": "standard",
        }
        job_spec["execution"] = {
            "acceleration_policy": "gpu_required",
            "priority": "normal",
            "document_timeout_seconds": 1800,
        }
    return job_spec


@router.get("/routes", response_model=ConversionHubListRoutesResult)
async def list_routes(
    registry: FromDishka[CuratedAppRegistryProtocol],
    user: User = Depends(require_app_user_api),
) -> ConversionHubListRoutesResult:
    _require_app_access(registry=registry, user=user)
    return ConversionHubListRoutesResult(routes=_list_supported_routes())


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
        _build_v2_job_spec(spec=spec, filename=upload.filename)
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
        build_job_spec=_build_v2_job_spec,
    )


@router.post(
    "/exam-converter/artifacts/save",
    response_model=SaveConversionHubSirConvertArtifactResult,
)
async def save_exam_converter_artifact(
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[SaveConversionHubSirConvertArtifactHandler],
    metadata_json: str = Form(..., min_length=2),
    artifact: UploadFile = File(...),
    user: User = Depends(require_app_user_api),
) -> SaveConversionHubSirConvertArtifactResult:
    _require_app_access(registry=registry, user=user)
    try:
        metadata = ConversionHubSirConvertArtifactSaveMetadata.model_validate_json(metadata_json)
    except Exception as exc:
        raise validation_error("Invalid artifact metadata JSON.") from exc
    filename = artifact.filename or metadata.saved_display_filename
    content = await artifact.read()
    return await handler.handle(
        actor=user,
        command=SaveConversionHubSirConvertArtifactCommand(
            metadata=metadata,
            filename=filename,
            content_type=artifact.content_type or metadata.content_type,
            content=content,
        ),
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
