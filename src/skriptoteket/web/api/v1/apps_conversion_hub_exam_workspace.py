"""Exam workspace API routes (ST-SKRIPT-39-04 walking skeleton).

Purpose:
  Expose DOCX import, document listing, reopen, and versioned save for the native editable
  exam workspace under the Conversion Hub curated app.

Relationships:
  - Shares Conversion Hub app access with `apps_conversion_hub`.
  - Delegates behavior to the exam workspace application handlers; the
    native document persists as versioned Mina filer containers.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamCourseCatalogResponse,
    ExamWorkspaceConversionStatus,
    ExamWorkspaceDocumentListResponse,
    ExamWorkspaceDocumentResponse,
    ExamWorkspaceExportChecklistResponse,
    ExamWorkspaceExportTarget,
    ExamWorkspaceItemRetryResponse,
    RetryExamWorkspaceItemRequest,
    SaveExamWorkspaceDocumentRequest,
)
from skriptoteket.application.curated_apps.exam_workspace_misspellings import (
    ExamWorkspaceMisspellingsRequest,
    ExamWorkspaceMisspellingsResponse,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import (
    ExportExamWorkspaceDocumentHandlerProtocol,
    GenerateExamWorkspaceMisspellingsHandlerProtocol,
    GetExamCourseCatalogHandlerProtocol,
    GetExamWorkspaceConversionStatusHandlerProtocol,
    GetExamWorkspaceDocumentHandlerProtocol,
    ImportExamWorkspaceDocumentHandlerProtocol,
    ListExamWorkspaceDocumentsHandlerProtocol,
    RetryExamWorkspaceItemHandlerProtocol,
    SaveExamWorkspaceDocumentHandlerProtocol,
)
from skriptoteket.web.api.v1.apps_conversion_hub_access import (
    APP_ID,
    require_conversion_hub_access,
)
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(prefix=f"/api/v1/apps/{APP_ID}", tags=["apps"])


@router.post(
    "/exam-workspace/answer-misspellings",
    response_model=ExamWorkspaceMisspellingsResponse,
)
def generate_exam_workspace_misspellings(
    request: ExamWorkspaceMisspellingsRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[GenerateExamWorkspaceMisspellingsHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceMisspellingsResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return handler.handle(request=request)


@router.get(
    "/exam-workspace/documents",
    response_model=ExamWorkspaceDocumentListResponse,
)
async def list_exam_workspace_documents(
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ListExamWorkspaceDocumentsHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceDocumentListResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(actor=user)


@router.post(
    "/exam-workspace/documents",
    response_model=ExamWorkspaceConversionStatus,
    status_code=202,
)
async def import_exam_workspace_document(
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ImportExamWorkspaceDocumentHandlerProtocol],
    file: UploadFile = File(...),
    course_key: str | None = Form(None, max_length=64),
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceConversionStatus:
    require_conversion_hub_access(registry=registry, user=user)
    content = await file.read()
    return await handler.handle(
        actor=user,
        filename=file.filename or "prov.docx",
        content=content,
        course_key=course_key or None,
    )


@router.get(
    "/exam-workspace/courses",
    response_model=ExamCourseCatalogResponse,
)
def get_exam_course_catalog(
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[GetExamCourseCatalogHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamCourseCatalogResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return handler.handle()


@router.get(
    "/exam-workspace/conversion-jobs/{job_id}",
    response_model=ExamWorkspaceConversionStatus,
)
async def get_exam_workspace_conversion_status(
    job_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[GetExamWorkspaceConversionStatusHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceConversionStatus:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(actor=user, job_id=job_id)


@router.get(
    "/exam-workspace/documents/{lineage_id}",
    response_model=ExamWorkspaceDocumentResponse,
)
async def get_exam_workspace_document(
    lineage_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[GetExamWorkspaceDocumentHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceDocumentResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(actor=user, lineage_id=lineage_id)


@router.get("/exam-workspace/documents/{lineage_id}/exports/{target}")
async def export_exam_workspace_document(
    lineage_id: UUID,
    target: ExamWorkspaceExportTarget,
    expected_revision: int,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ExportExamWorkspaceDocumentHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> Response:
    require_conversion_hub_access(registry=registry, user=user)
    result = await handler.handle(
        actor=user, lineage_id=lineage_id, target=target, expected_revision=expected_revision
    )
    safe_filename = result.filename.replace('"', "")
    return Response(
        content=result.content,
        media_type=result.media_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )


@router.get(
    "/exam-workspace/documents/{lineage_id}/export-checklist",
    response_model=ExamWorkspaceExportChecklistResponse,
)
async def export_exam_workspace_document_checklist(
    lineage_id: UUID,
    expected_revision: int,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ExportExamWorkspaceDocumentHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceExportChecklistResponse:
    """List what an Exam.net import of this document's QTI package loses (Q15)."""

    require_conversion_hub_access(registry=registry, user=user)
    return await handler.checklist(
        actor=user, lineage_id=lineage_id, expected_revision=expected_revision
    )


@router.put(
    "/exam-workspace/documents/{lineage_id}",
    response_model=ExamWorkspaceDocumentResponse,
)
async def save_exam_workspace_document(
    lineage_id: UUID,
    request: SaveExamWorkspaceDocumentRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[SaveExamWorkspaceDocumentHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceDocumentResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(actor=user, lineage_id=lineage_id, request=request)


@router.post(
    "/exam-workspace/documents/{lineage_id}/items/retry",
    response_model=ExamWorkspaceItemRetryResponse,
)
async def retry_exam_workspace_item(
    lineage_id: UUID,
    request: RetryExamWorkspaceItemRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[RetryExamWorkspaceItemHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceItemRetryResponse:
    """Reconvert one question from its saved source with the chosen type."""

    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(actor=user, lineage_id=lineage_id, request=request)
