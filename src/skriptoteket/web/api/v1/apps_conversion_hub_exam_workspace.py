"""Exam workspace API routes (ST-SKRIPT-39-04 walking skeleton).

Purpose:
  Expose DOCX import, reopen, and versioned save for the native editable
  exam workspace under the Conversion Hub curated app.

Relationships:
  - Shares Conversion Hub app access with `apps_conversion_hub`.
  - Delegates behavior to the exam workspace application handlers; the
    native document persists as versioned Mina filer containers.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceDocumentResponse,
    SaveExamWorkspaceDocumentRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    GetExamWorkspaceDocumentHandler,
    ImportExamWorkspaceDocumentHandler,
    SaveExamWorkspaceDocumentHandler,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.web.api.v1.apps_conversion_hub_access import (
    APP_ID,
    require_conversion_hub_access,
)
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(prefix=f"/api/v1/apps/{APP_ID}", tags=["apps"])


@router.post(
    "/exam-workspace/documents",
    response_model=ExamWorkspaceDocumentResponse,
)
async def import_exam_workspace_document(
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ImportExamWorkspaceDocumentHandler],
    file: UploadFile = File(...),
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceDocumentResponse:
    require_conversion_hub_access(registry=registry, user=user)
    content = await file.read()
    return await handler.handle(actor=user, filename=file.filename or "prov.docx", content=content)


@router.get(
    "/exam-workspace/documents/{lineage_id}",
    response_model=ExamWorkspaceDocumentResponse,
)
async def get_exam_workspace_document(
    lineage_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[GetExamWorkspaceDocumentHandler],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceDocumentResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(actor=user, lineage_id=lineage_id)


@router.put(
    "/exam-workspace/documents/{lineage_id}",
    response_model=ExamWorkspaceDocumentResponse,
)
async def save_exam_workspace_document(
    lineage_id: UUID,
    request: SaveExamWorkspaceDocumentRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[SaveExamWorkspaceDocumentHandler],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceDocumentResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(actor=user, lineage_id=lineage_id, request=request)
