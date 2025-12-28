"""User-specific API endpoints (ST-16-04)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from skriptoteket.application.catalog.queries import CatalogItemKind, ListRecentToolsQuery
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.catalog import ListRecentToolsHandlerProtocol
from skriptoteket.web.auth.api_dependencies import require_user_api

router = APIRouter(prefix="/api/v1/me", tags=["me"])


class RecentToolItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["tool"]
    id: UUID
    slug: str
    title: str
    summary: str | None
    is_favorite: bool
    last_used_at: datetime


class RecentCuratedAppItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["curated_app"]
    id: UUID
    app_id: str
    title: str
    summary: str | None
    is_favorite: bool
    last_used_at: datetime


class ListRecentToolsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[RecentToolItem | RecentCuratedAppItem]


@router.get("/recent-tools", response_model=ListRecentToolsResponse)
@inject
async def list_recent_tools(
    handler: FromDishka[ListRecentToolsHandlerProtocol],
    user: User = Depends(require_user_api),
    limit: int = Query(10, ge=1, le=50),
) -> ListRecentToolsResponse:
    result = await handler.handle(actor=user, query=ListRecentToolsQuery(limit=limit))
    items: list[RecentToolItem | RecentCuratedAppItem] = []
    for item in result.items:
        if item.kind is CatalogItemKind.TOOL:
            items.append(
                RecentToolItem(
                    kind="tool",
                    id=item.id,
                    slug=item.slug or "",
                    title=item.title,
                    summary=item.summary,
                    is_favorite=item.is_favorite,
                    last_used_at=item.last_used_at,
                )
            )
        else:
            items.append(
                RecentCuratedAppItem(
                    kind="curated_app",
                    id=item.id,
                    app_id=item.app_id or "",
                    title=item.title,
                    summary=item.summary,
                    is_favorite=item.is_favorite,
                    last_used_at=item.last_used_at,
                )
            )
    return ListRecentToolsResponse(items=items)
