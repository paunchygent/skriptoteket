"""My runs API endpoints for SPA views (ST-11-08)."""

from datetime import datetime
from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.models import RunContext, RunStatus
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.scripting import ToolRunRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.web.auth.api_dependencies import require_user_api

router = APIRouter(prefix="/api/v1/my-runs", tags=["my-runs"])


class MyRunItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: UUID
    tool_id: UUID
    tool_slug: str | None
    tool_title: str
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None


class ListMyRunsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    runs: list[MyRunItem]
    total_count: int


@router.get("", response_model=ListMyRunsResponse)
@inject
async def list_my_runs(
    uow: FromDishka[UnitOfWorkProtocol],
    runs: FromDishka[ToolRunRepositoryProtocol],
    tools: FromDishka[ToolRepositoryProtocol],
    curated_apps: FromDishka[CuratedAppRegistryProtocol],
    user: User = Depends(require_user_api),
) -> ListMyRunsResponse:
    async with uow:
        user_runs = await runs.list_for_user(
            user_id=user.id,
            context=RunContext.PRODUCTION,
            limit=50,
        )
        total_count = await runs.count_for_user_this_month(
            user_id=user.id,
            context=RunContext.PRODUCTION,
        )

        items: list[MyRunItem] = []
        for run in user_runs:
            app = curated_apps.get_by_tool_id(tool_id=run.tool_id)
            if app is not None:
                tool_slug = None
                tool_title = app.title
            else:
                tool = await tools.get_by_id(tool_id=run.tool_id)
                if tool is None:
                    tool_slug = None
                    tool_title = "Okänt verktyg"
                else:
                    tool_slug = tool.slug
                    tool_title = tool.title

            items.append(
                MyRunItem(
                    run_id=run.id,
                    tool_id=run.tool_id,
                    tool_slug=tool_slug,
                    tool_title=tool_title,
                    status=run.status,
                    started_at=run.started_at,
                    finished_at=run.finished_at,
                )
            )

    return ListMyRunsResponse(runs=items, total_count=total_count)
