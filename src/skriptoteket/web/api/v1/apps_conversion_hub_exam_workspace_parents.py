"""Parent authoring commands; the existing workspace UI remains unchanged."""

from uuid import UUID

from fastapi import APIRouter, Depends

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceDocumentResponse
from skriptoteket.application.curated_apps.exam_workspace_parents import (
    AddExamChildRequest,
    CreateExamParentRequest,
    ExamWorkspaceDeleteResponse,
    ParentCommandRequest,
    ReorderExamChildrenRequest,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace_parents import ExamWorkspaceParentsHandlerProtocol
from skriptoteket.web.api.v1.apps_conversion_hub_access import (
    APP_ID,
    require_conversion_hub_access,
)
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(
    prefix=f"/api/v1/apps/{APP_ID}/exam-workspace/documents/{{lineage_id}}/parents",
    tags=["apps"],
)


@router.post("", response_model=ExamWorkspaceDocumentResponse)
async def create_exam_parent(
    lineage_id: UUID,
    request: CreateExamParentRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ExamWorkspaceParentsHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceDocumentResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.create_parent(actor=user, lineage_id=lineage_id, request=request)


@router.post("/{parent_id}/children", response_model=ExamWorkspaceDocumentResponse)
async def add_exam_child(
    lineage_id: UUID,
    parent_id: str,
    request: AddExamChildRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ExamWorkspaceParentsHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceDocumentResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.add_child(
        actor=user, lineage_id=lineage_id, parent_id=parent_id, request=request
    )


@router.delete("/{parent_id}", response_model=ExamWorkspaceDeleteResponse)
async def delete_exam_parent(
    lineage_id: UUID,
    parent_id: str,
    request: ParentCommandRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ExamWorkspaceParentsHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceDeleteResponse:
    """Delete only the instruction, leaving its questions standalone."""
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.delete_parent(
        actor=user, lineage_id=lineage_id, parent_id=parent_id, request=request
    )


@router.delete("/{parent_id}/with-children", response_model=ExamWorkspaceDeleteResponse)
async def delete_exam_parent_with_children(
    lineage_id: UUID,
    parent_id: str,
    request: ParentCommandRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ExamWorkspaceParentsHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceDeleteResponse:
    """Explicitly delete the instruction and every question it contains."""
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.delete_parent_with_children(
        actor=user, lineage_id=lineage_id, parent_id=parent_id, request=request
    )


@router.delete("/{parent_id}/children/{item_id}", response_model=ExamWorkspaceDeleteResponse)
async def delete_exam_child(
    lineage_id: UUID,
    parent_id: str,
    item_id: str,
    request: ParentCommandRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ExamWorkspaceParentsHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceDeleteResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.delete_child(
        actor=user, lineage_id=lineage_id, parent_id=parent_id, item_id=item_id, request=request
    )


@router.put("/{parent_id}/children/order", response_model=ExamWorkspaceDocumentResponse)
async def reorder_exam_children(
    lineage_id: UUID,
    parent_id: str,
    request: ReorderExamChildrenRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ExamWorkspaceParentsHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceDocumentResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.reorder_children(
        actor=user, lineage_id=lineage_id, parent_id=parent_id, request=request
    )
