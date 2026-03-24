"""Conversion Hub curated app API routes (Skriptoteket).

Purpose:
  Expose a bespoke conversion UI surface under `/api/v1/apps/<app_id>/...` which
  orchestrates multi-format conversions by delegating execution to Sir Convert-a-Lot v2.

Relationships:
  - App registry entry: `src/skriptoteket/infrastructure/curated_apps/registry.py`
  - V2 conversion engine (external): Sir Convert-a-Lot `/v2/convert/jobs/*`
"""

from uuid import uuid4

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
    ConversionHubSubmittedJob,
)
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertALotClientV2Protocol,
    SirConvertSubmitRequestV2,
)
from skriptoteket.web.auth.api_dependencies import require_csrf_token, require_user_api
from skriptoteket.web.dishka_compat import FromDishka, inject
from skriptoteket.web.request_metadata import get_correlation_id

APP_ID = "documents.conversion_hub"

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
@inject
async def list_routes(
    registry: FromDishka[CuratedAppRegistryProtocol],
    user: User = Depends(require_user_api),
) -> ConversionHubListRoutesResult:
    _require_app_access(registry=registry, user=user)
    return ConversionHubListRoutesResult(routes=_list_supported_routes())


@router.post("/jobs", response_model=ConversionHubSubmitResult)
@inject
async def submit_jobs(
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    client: FromDishka[SirConvertALotClientV2Protocol],
    job_spec_json: str = Form(..., min_length=2),
    files: list[UploadFile] = File(...),
    wait_seconds: int = Form(0),
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> ConversionHubSubmitResult:
    _require_app_access(registry=registry, user=user)

    if wait_seconds < 0 or wait_seconds > 30:
        raise validation_error("wait_seconds must be between 0 and 30.")

    try:
        spec = ConversionHubJobSpecV2.model_validate_json(job_spec_json)
    except Exception as exc:
        raise validation_error("Invalid job_spec JSON.") from exc

    _validate_route_supported(spec)

    if not files:
        raise validation_error("At least one file must be provided.")

    correlation_id_uuid = get_correlation_id(request)
    correlation_id = str(correlation_id_uuid) if correlation_id_uuid is not None else None

    jobs: list[ConversionHubSubmittedJob] = []
    for upload in files:
        if upload.filename is None or not upload.filename:
            raise validation_error("Uploaded file is missing a filename.")

        await upload.seek(0)
        content_type = upload.content_type or "application/octet-stream"
        v2_spec = _build_v2_job_spec(spec=spec, filename=upload.filename)
        submitted = await client.submit_job(
            request=SirConvertSubmitRequestV2(
                filename=upload.filename,
                content_type=content_type,
                file_bytes=await upload.read(),
                job_spec=v2_spec,
                idempotency_key=str(uuid4()),
                wait_seconds=wait_seconds,
                correlation_id=correlation_id,
            )
        )
        jobs.append(
            ConversionHubSubmittedJob(
                input_filename=upload.filename,
                job_id=submitted.job_id,
                status=submitted.status,
                idempotent_replay=submitted.idempotent_replay,
            )
        )

    return ConversionHubSubmitResult(jobs=jobs)


@router.get("/jobs/{job_id}", response_model=ConversionHubJobStatusResult)
@inject
async def get_job_status(
    job_id: str,
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    client: FromDishka[SirConvertALotClientV2Protocol],
    user: User = Depends(require_user_api),
) -> ConversionHubJobStatusResult:
    _require_app_access(registry=registry, user=user)
    if not job_id:
        raise validation_error("job_id is required.")

    # We intentionally do not proxy the full upstream job record here.
    # The SPA polls status via this surface.
    correlation_id_uuid = get_correlation_id(request)
    correlation_id = str(correlation_id_uuid) if correlation_id_uuid is not None else None
    current = await client.get_job(job_id, correlation_id=correlation_id)
    return ConversionHubJobStatusResult(job_id=current.job_id, status=current.status)


@router.get("/jobs/{job_id}/artifact")
@inject
async def download_artifact(
    job_id: str,
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    client: FromDishka[SirConvertALotClientV2Protocol],
    user: User = Depends(require_user_api),
) -> Response:
    _require_app_access(registry=registry, user=user)
    if not job_id:
        raise validation_error("job_id is required.")

    correlation_id_uuid = get_correlation_id(request)
    correlation_id = str(correlation_id_uuid) if correlation_id_uuid is not None else None
    outcome = await client.download_artifact(job_id, correlation_id=correlation_id)
    return Response(
        content=outcome.artifact.content,
        media_type=outcome.artifact.content_type,
        headers={"Content-Disposition": f'attachment; filename="{outcome.artifact.filename}"'},
    )
