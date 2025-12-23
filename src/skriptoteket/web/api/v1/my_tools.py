"""My tools API endpoints for contributor dashboard (ST-11-15)."""

from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from skriptoteket.application.catalog.queries import ListToolsForContributorQuery
from skriptoteket.domain.catalog.models import Tool
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.catalog import ListToolsForContributorHandlerProtocol
from skriptoteket.web.auth.api_dependencies import require_contributor_api

router = APIRouter(prefix="/api/v1/my-tools", tags=["my-tools"])


class MyToolItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    title: str
    summary: str | None
    is_published: bool


class ListMyToolsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    tools: list[MyToolItem]


def to_my_tool_item(tool: Tool) -> MyToolItem:
    return MyToolItem(
        id=tool.id,
        title=tool.title,
        summary=tool.summary,
        is_published=tool.is_published,
    )


@router.get("", response_model=ListMyToolsResponse)
@inject
async def list_my_tools(
    handler: FromDishka[ListToolsForContributorHandlerProtocol],
    user: User = Depends(require_contributor_api),
) -> ListMyToolsResponse:
    result = await handler.handle(actor=user, query=ListToolsForContributorQuery())
    return ListMyToolsResponse(tools=[to_my_tool_item(tool) for tool in result.tools])
