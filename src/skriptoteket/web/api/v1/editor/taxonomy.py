from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends

from skriptoteket.application.catalog.commands import UpdateToolTaxonomyCommand
from skriptoteket.application.catalog.queries import ListToolTaxonomyQuery
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.catalog import (
    ListToolTaxonomyHandlerProtocol,
    UpdateToolTaxonomyHandlerProtocol,
)
from skriptoteket.web.auth.api_dependencies import (
    require_admin_api,
    require_csrf_token,
)

from .models import ToolTaxonomyRequest, ToolTaxonomyResponse

router = APIRouter()


@router.get("/tools/{tool_id}/taxonomy", response_model=ToolTaxonomyResponse)
@inject
async def get_tool_taxonomy(
    tool_id: UUID,
    handler: FromDishka[ListToolTaxonomyHandlerProtocol],
    user: User = Depends(require_admin_api),
) -> ToolTaxonomyResponse:
    result = await handler.handle(
        actor=user,
        query=ListToolTaxonomyQuery(tool_id=tool_id),
    )
    return ToolTaxonomyResponse(
        tool_id=result.tool_id,
        profession_ids=result.profession_ids,
        category_ids=result.category_ids,
    )


@router.patch("/tools/{tool_id}/taxonomy", response_model=ToolTaxonomyResponse)
@inject
async def update_tool_taxonomy(
    tool_id: UUID,
    payload: ToolTaxonomyRequest,
    handler: FromDishka[UpdateToolTaxonomyHandlerProtocol],
    user: User = Depends(require_admin_api),
    _: None = Depends(require_csrf_token),
) -> ToolTaxonomyResponse:
    result = await handler.handle(
        actor=user,
        command=UpdateToolTaxonomyCommand(
            tool_id=tool_id,
            profession_ids=payload.profession_ids,
            category_ids=payload.category_ids,
        ),
    )
    return ToolTaxonomyResponse(
        tool_id=result.tool_id,
        profession_ids=result.profession_ids,
        category_ids=result.category_ids,
    )
