"""One workspace question-type command, without changing the frozen editor UI."""

from uuid import UUID

from fastapi import APIRouter, Depends

from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace_change_type import (
    ChangeExamWorkspaceItemTypeHandlerProtocol,
    ChangeExamWorkspaceItemTypeRequest,
    ChangeExamWorkspaceItemTypeResponse,
)
from skriptoteket.web.api.v1.apps_conversion_hub_access import APP_ID, require_conversion_hub_access
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(
    prefix=f"/api/v1/apps/{APP_ID}/exam-workspace/documents/{{lineage_id}}",
    tags=["apps"],
)


@router.post("/change-type", response_model=ChangeExamWorkspaceItemTypeResponse)
async def change_exam_item_type(
    lineage_id: UUID,
    request: ChangeExamWorkspaceItemTypeRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ChangeExamWorkspaceItemTypeHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ChangeExamWorkspaceItemTypeResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(actor=user, lineage_id=lineage_id, request=request)
