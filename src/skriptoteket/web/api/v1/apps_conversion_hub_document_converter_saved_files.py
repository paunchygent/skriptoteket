"""Document Converter saved-file API routes.

Purpose:
    Expose owner-scoped Mina filer source listing and saved-file submission
    under the Document Converter namespace without making the browser upload
    saved bytes back to the backend.

Relationships:
    Uses the shared Conversion Hub app access policy and application handlers
    for compatible source listing plus server-side job submission.
"""

from fastapi import APIRouter, Depends, Request

from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterSubmitResult,
    ListDocumentConverterSavedFilesResult,
    SubmitDocumentConverterSavedFileRequest,
    validate_document_converter_route,
)
from skriptoteket.application.curated_apps.handlers.document_converter_saved_sources import (
    ListDocumentConverterSavedFilesHandler,
    SubmitDocumentConverterSavedFileHandler,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.web.api.v1.apps_conversion_hub import _build_v2_job_spec
from skriptoteket.web.api.v1.apps_conversion_hub_access import (
    APP_ID,
    require_conversion_hub_access,
)
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.dishka_dependencies import FromDishka
from skriptoteket.web.request_metadata import get_correlation_id

router = APIRouter(
    prefix=f"/api/v1/apps/{APP_ID}/document-converter",
    tags=["apps"],
)


def _require_app_access(*, registry: CuratedAppRegistryProtocol, user: User) -> None:
    require_conversion_hub_access(registry=registry, user=user)


@router.get("/saved-files", response_model=ListDocumentConverterSavedFilesResult)
async def list_document_converter_saved_files(
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ListDocumentConverterSavedFilesHandler],
    user: User = Depends(require_app_user_api),
) -> ListDocumentConverterSavedFilesResult:
    """Return compatible owner-scoped Mina filer sources."""
    _require_app_access(registry=registry, user=user)
    return await handler.handle(actor=user)


@router.post("/saved-files/jobs", response_model=DocumentConverterSubmitResult)
async def submit_document_converter_saved_file_job(
    request: Request,
    submit_request: SubmitDocumentConverterSavedFileRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[SubmitDocumentConverterSavedFileHandler],
    user: User = Depends(require_app_user_api),
) -> DocumentConverterSubmitResult:
    """Start one Document Converter job from an owner-scoped saved file ref."""
    _require_app_access(registry=registry, user=user)
    validate_document_converter_route(submit_request.job_spec)
    correlation_id_uuid = get_correlation_id(request)
    correlation_id = str(correlation_id_uuid) if correlation_id_uuid is not None else None
    return await handler.handle(
        actor=user,
        spec=submit_request.job_spec,
        source_ref=submit_request.source_ref,
        wait_seconds=submit_request.wait_seconds,
        correlation_id=correlation_id,
        build_job_spec=_build_v2_job_spec,
    )
