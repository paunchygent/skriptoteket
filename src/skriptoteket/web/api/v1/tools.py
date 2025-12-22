from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, ConfigDict

from skriptoteket.application.scripting.commands import RunActiveToolCommand
from skriptoteket.config import Settings
from skriptoteket.domain.catalog.models import Tool
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.models import VersionState
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.scripting import (
    RunActiveToolHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.web.auth.api_dependencies import require_csrf_token, require_user_api
from skriptoteket.web.uploads import read_upload_files

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


class UploadConstraints(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_files: int
    max_file_bytes: int
    max_total_bytes: int


class ToolMetadataResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    slug: str
    title: str
    summary: str | None
    upload_constraints: UploadConstraints


class StartToolRunResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: UUID


async def _load_runnable_tool(
    *,
    tools: ToolRepositoryProtocol,
    versions: ToolVersionRepositoryProtocol,
    slug: str,
) -> Tool:
    tool = await tools.get_by_slug(slug=slug)
    if tool is None:
        raise not_found("Tool", slug)
    if not tool.is_published:
        raise not_found("Tool", slug)
    if tool.active_version_id is None:
        raise not_found("Tool", slug)

    version = await versions.get_by_id(version_id=tool.active_version_id)
    if version is None:
        raise not_found("Tool", slug)
    if version.state is not VersionState.ACTIVE:
        raise not_found("Tool", slug)

    return tool


@router.get("/{slug}", response_model=ToolMetadataResponse)
@inject
async def get_tool_by_slug(
    slug: str,
    tools: FromDishka[ToolRepositoryProtocol],
    versions: FromDishka[ToolVersionRepositoryProtocol],
    settings: FromDishka[Settings],
    _user: User = Depends(require_user_api),
) -> ToolMetadataResponse:
    tool = await _load_runnable_tool(tools=tools, versions=versions, slug=slug)
    return ToolMetadataResponse(
        id=tool.id,
        slug=tool.slug,
        title=tool.title,
        summary=tool.summary,
        upload_constraints=UploadConstraints(
            max_files=settings.UPLOAD_MAX_FILES,
            max_file_bytes=settings.UPLOAD_MAX_FILE_BYTES,
            max_total_bytes=settings.UPLOAD_MAX_TOTAL_BYTES,
        ),
    )


@router.post("/{slug}/run", response_model=StartToolRunResponse)
@inject
async def start_tool_run(
    slug: str,
    handler: FromDishka[RunActiveToolHandlerProtocol],
    settings: FromDishka[Settings],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
    files: list[UploadFile] = File(...),
) -> StartToolRunResponse:
    input_files = await read_upload_files(
        files=files,
        max_files=settings.UPLOAD_MAX_FILES,
        max_file_bytes=settings.UPLOAD_MAX_FILE_BYTES,
        max_total_bytes=settings.UPLOAD_MAX_TOTAL_BYTES,
    )
    result = await handler.handle(
        actor=user,
        command=RunActiveToolCommand(tool_slug=slug, input_files=input_files),
    )
    return StartToolRunResponse(run_id=result.run.id)
