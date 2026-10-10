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

from fastapi import APIRouter, Depends, File, Response, UploadFile

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceConversionStatus,
    ExamWorkspaceDocumentListResponse,
    ExamWorkspaceDocumentResponse,
    ExamWorkspaceExportTarget,
    SaveExamWorkspaceDocumentRequest,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import (
    ExportExamWorkspaceDocumentHandlerProtocol,
    GetExamWorkspaceConversionStatusHandlerProtocol,
    GetExamWorkspaceDocumentHandlerProtocol,
    ImportExamWorkspaceDocumentHandlerProtocol,
    ListExamWorkspaceDocumentsHandlerProtocol,
    SaveExamWorkspaceDocumentHandlerProtocol,
)
from skriptoteket.web.api.v1.apps_conversion_hub_access import (
    APP_ID,
    require_conversion_hub_access,
)
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(prefix=f"/api/v1/apps/{APP_ID}", tags=["apps"])


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
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceConversionStatus:
    require_conversion_hub_access(registry=registry, user=user)
    content = await file.read()
    return await handler.handle(actor=user, filename=file.filename or "prov.docx", content=content)


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
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ExportExamWorkspaceDocumentHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> Response:
    require_conversion_hub_access(registry=registry, user=user)
    result = await handler.handle(actor=user, lineage_id=lineage_id, target=target)
    safe_filename = result.filename.replace('"', "")
    return Response(
        content=result.content,
        media_type=result.media_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
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
