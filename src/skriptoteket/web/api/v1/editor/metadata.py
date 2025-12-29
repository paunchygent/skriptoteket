from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends

from skriptoteket.application.catalog.commands import (
    UpdateToolMetadataCommand,
    UpdateToolSlugCommand,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.catalog import (
    ToolRepositoryProtocol,
    UpdateToolMetadataHandlerProtocol,
    UpdateToolSlugHandlerProtocol,
)
from skriptoteket.web.auth.api_dependencies import (
    require_admin_api,
    require_csrf_token,
)

from .models import (
    EditorToolMetadataRequest,
    EditorToolMetadataResponse,
    EditorToolSlugRequest,
)

router = APIRouter()


@router.patch("/tools/{tool_id}/metadata", response_model=EditorToolMetadataResponse)
@inject
async def update_tool_metadata(
    tool_id: UUID,
    payload: EditorToolMetadataRequest,
    tools: FromDishka[ToolRepositoryProtocol],
    handler: FromDishka[UpdateToolMetadataHandlerProtocol],
    user: User = Depends(require_admin_api),
    _: None = Depends(require_csrf_token),
) -> EditorToolMetadataResponse:
    summary = payload.summary
    if "summary" not in payload.model_fields_set:
        tool = await tools.get_by_id(tool_id=tool_id)
        if tool is None:
            raise not_found("Tool", str(tool_id))
        summary = tool.summary

    result = await handler.handle(
        actor=user,
        command=UpdateToolMetadataCommand(
            tool_id=tool_id,
            title=payload.title,
            summary=summary,
        ),
    )
    tool = result.tool
    return EditorToolMetadataResponse(
        id=tool.id,
        slug=tool.slug,
        title=tool.title,
        summary=tool.summary,
    )


@router.patch("/tools/{tool_id}/slug", response_model=EditorToolMetadataResponse)
@inject
async def update_tool_slug(
    tool_id: UUID,
    payload: EditorToolSlugRequest,
    handler: FromDishka[UpdateToolSlugHandlerProtocol],
    user: User = Depends(require_admin_api),
    _: None = Depends(require_csrf_token),
) -> EditorToolMetadataResponse:
    result = await handler.handle(
        actor=user,
        command=UpdateToolSlugCommand(
            tool_id=tool_id,
            slug=payload.slug,
        ),
    )
    tool = result.tool
    return EditorToolMetadataResponse(
        id=tool.id,
        slug=tool.slug,
        title=tool.title,
        summary=tool.summary,
    )
