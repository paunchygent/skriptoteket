"""Admin tools API endpoints for SPA admin management (ST-11-11, ADR-0033)."""

from datetime import datetime
from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from skriptoteket.application.catalog.commands import (
    DepublishToolCommand,
    PublishToolCommand,
)
from skriptoteket.application.catalog.queries import ListToolsForAdminQuery
from skriptoteket.domain.catalog.models import Tool, ToolVersionStats
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.catalog import (
    DepublishToolHandlerProtocol,
    ListToolsForAdminHandlerProtocol,
    PublishToolHandlerProtocol,
)
from skriptoteket.web.auth.api_dependencies import require_admin_api, require_csrf_token

router = APIRouter(prefix="/api/v1", tags=["admin-tools"])


# --- DTOs ---


class AdminToolItem(BaseModel):
    """Tool representation for admin list/actions (ADR-0033)."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    slug: str
    title: str
    summary: str | None
    is_published: bool
    active_version_id: UUID | None
    created_at: datetime
    updated_at: datetime

    # Version statistics for status enrichment (ADR-0033)
    version_count: int
    latest_version_state: str | None
    has_pending_review: bool


class ListAdminToolsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    tools: list[AdminToolItem]


class PublishToolResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool: AdminToolItem


class DepublishToolResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool: AdminToolItem


def to_admin_tool_item(tool: Tool, stats: ToolVersionStats) -> AdminToolItem:
    return AdminToolItem(
        id=tool.id,
        slug=tool.slug,
        title=tool.title,
        summary=tool.summary,
        is_published=tool.is_published,
        active_version_id=tool.active_version_id,
        created_at=tool.created_at,
        updated_at=tool.updated_at,
        version_count=stats.version_count,
        latest_version_state=stats.latest_version_state,
        has_pending_review=stats.has_pending_review,
    )


# Default stats for tools without version information
_DEFAULT_STATS = ToolVersionStats(
    version_count=0,
    latest_version_state=None,
    has_pending_review=False,
)

# Stats for publishable tools (have at least one active version)
_PUBLISHABLE_STATS = ToolVersionStats(
    version_count=1,  # At minimum, the active version exists
    latest_version_state="active",
    has_pending_review=False,
)


# --- Endpoints ---


@router.get(
    "/admin/tools",
    response_model=ListAdminToolsResponse,
)
@inject
async def list_admin_tools(
    handler: FromDishka[ListToolsForAdminHandlerProtocol],
    user: User = Depends(require_admin_api),
) -> ListAdminToolsResponse:
    result = await handler.handle(actor=user, query=ListToolsForAdminQuery())
    return ListAdminToolsResponse(
        tools=[
            to_admin_tool_item(t, result.version_stats.get(t.id, _DEFAULT_STATS))
            for t in result.tools
        ]
    )


@router.post(
    "/admin/tools/{tool_id}/publish",
    response_model=PublishToolResponse,
)
@inject
async def publish_tool(
    tool_id: UUID,
    handler: FromDishka[PublishToolHandlerProtocol],
    user: User = Depends(require_admin_api),
    _: None = Depends(require_csrf_token),
) -> PublishToolResponse:
    result = await handler.handle(
        actor=user,
        command=PublishToolCommand(tool_id=tool_id),
    )
    # Tool must have active version to be publishable
    return PublishToolResponse(tool=to_admin_tool_item(result.tool, _PUBLISHABLE_STATS))


@router.post(
    "/admin/tools/{tool_id}/depublish",
    response_model=DepublishToolResponse,
)
@inject
async def depublish_tool(
    tool_id: UUID,
    handler: FromDishka[DepublishToolHandlerProtocol],
    user: User = Depends(require_admin_api),
    _: None = Depends(require_csrf_token),
) -> DepublishToolResponse:
    result = await handler.handle(
        actor=user,
        command=DepublishToolCommand(tool_id=tool_id),
    )
    # Tool still has active version after depublish
    return DepublishToolResponse(tool=to_admin_tool_item(result.tool, _PUBLISHABLE_STATS))
