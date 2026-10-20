"""Exam workspace export routes (TASK-SKRIPT-41-02-06 U13a).

Purpose:
    Download a saved exam workspace document in a converted target format,
    list what an Exam.net import of its QTI package loses, render the retained
    history step the editor names for the Förhandsgranska panel, and save a
    converted export back to Mina filer.

Relationships:
    - Shares Conversion Hub app access with `apps_conversion_hub_exam_workspace`.
    - Delegates behavior to the exam workspace export and print preview handlers.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Response

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceExportChecklistResponse,
    ExamWorkspaceExportTarget,
    ExamWorkspacePrintPreviewResponse,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultFile
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import (
    ExportExamWorkspaceDocumentHandlerProtocol,
    PreviewExamWorkspacePrintHandlerProtocol,
)
from skriptoteket.web.api.v1.apps_conversion_hub_access import (
    APP_ID,
    require_conversion_hub_access,
)
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.content_disposition import attachment_content_disposition
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(prefix=f"/api/v1/apps/{APP_ID}", tags=["apps"])


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
    return Response(
        content=result.content,
        media_type=result.media_type,
        headers={"Content-Disposition": attachment_content_disposition(filename=result.filename)},
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


@router.get(
    "/exam-workspace/documents/{lineage_id}/print-preview",
    response_model=ExamWorkspacePrintPreviewResponse,
)
async def preview_exam_workspace_document_print(
    lineage_id: UUID,
    expected_revision: int,
    expected_cursor: UUID,
    step_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[PreviewExamWorkspacePrintHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspacePrintPreviewResponse:
    """Render the retained history step the editor names for the Förhandsgranska panel (W5)."""

    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(
        actor=user,
        lineage_id=lineage_id,
        expected_revision=expected_revision,
        expected_cursor=expected_cursor,
        step_id=step_id,
    )


@router.post("/exam-workspace/documents/{lineage_id}/exports/{target}", response_model=VaultFile)
async def save_exam_workspace_export(
    lineage_id: UUID,
    target: ExamWorkspaceExportTarget,
    expected_revision: int,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ExportExamWorkspaceDocumentHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> VaultFile:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.save(
        actor=user, lineage_id=lineage_id, target=target, expected_revision=expected_revision
    )
