"""Exam workspace picture routes (TASK-SKRIPT-39-05-09 D2).

Purpose:
  Serve one declared picture of a saved exam workspace document as a binary response
  with its own media type, so the editor shows the teacher's own pictures. The saved
  head revision is the authority and the response requires app access; no picture is
  ever served anonymously, and the client never supplies the bytes.

Relationships:
  - Shares Conversion Hub app access with `apps_conversion_hub_exam_workspace`.
  - Delegates behavior to the exam workspace asset handler over the versioned container.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Response

from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import GetExamWorkspaceAssetHandlerProtocol
from skriptoteket.web.api.v1.apps_conversion_hub_access import (
    APP_ID,
    require_conversion_hub_access,
)
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(prefix=f"/api/v1/apps/{APP_ID}", tags=["apps"])


@router.get("/exam-workspace/documents/{lineage_id}/assets/{asset_id}")
async def get_exam_workspace_asset(
    lineage_id: UUID,
    asset_id: str,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[GetExamWorkspaceAssetHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> Response:
    require_conversion_hub_access(registry=registry, user=user)
    asset = await handler.handle(actor=user, lineage_id=lineage_id, asset_id=asset_id)
    return Response(content=asset.content, media_type=asset.media_type)
