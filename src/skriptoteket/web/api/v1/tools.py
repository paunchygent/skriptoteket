from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, ConfigDict, JsonValue

from skriptoteket.application.scripting.commands import RunActiveToolCommand
from skriptoteket.application.scripting.tool_settings import (
    GetToolSettingsQuery,
    UpdateToolSettingsCommand,
)
from skriptoteket.config import Settings
from skriptoteket.domain.catalog.models import Tool
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.models import ToolVersion, VersionState
from skriptoteket.domain.scripting.ui.contract_v2 import UiActionField
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.scripting import (
    RunActiveToolHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.tool_settings import (
    GetToolSettingsHandlerProtocol,
    UpdateToolSettingsHandlerProtocol,
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
    usage_instructions: str | None
    upload_constraints: UploadConstraints


class StartToolRunResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: UUID


class ToolSettingsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    schema_version: str | None
    settings_schema: list[UiActionField] | None
    values: dict[str, JsonValue]
    state_rev: int


class UpdateToolSettingsRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    expected_state_rev: int
    values: dict[str, JsonValue]


async def _load_runnable_tool(
    *,
    tools: ToolRepositoryProtocol,
    versions: ToolVersionRepositoryProtocol,
    slug: str,
) -> tuple[Tool, ToolVersion]:
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

    return tool, version


@router.get("/{slug}", response_model=ToolMetadataResponse)
@inject
async def get_tool_by_slug(
    slug: str,
    tools: FromDishka[ToolRepositoryProtocol],
    versions: FromDishka[ToolVersionRepositoryProtocol],
    settings: FromDishka[Settings],
    _user: User = Depends(require_user_api),
) -> ToolMetadataResponse:
    tool, version = await _load_runnable_tool(tools=tools, versions=versions, slug=slug)
    return ToolMetadataResponse(
        id=tool.id,
        slug=tool.slug,
        title=tool.title,
        summary=tool.summary,
        usage_instructions=version.usage_instructions,
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


@router.get("/{tool_id}/settings", response_model=ToolSettingsResponse)
@inject
async def get_tool_settings(
    tool_id: UUID,
    handler: FromDishka[GetToolSettingsHandlerProtocol],
    user: User = Depends(require_user_api),
) -> ToolSettingsResponse:
    result = await handler.handle(actor=user, query=GetToolSettingsQuery(tool_id=tool_id))
    settings_state = result.settings
    return ToolSettingsResponse(
        tool_id=settings_state.tool_id,
        schema_version=settings_state.schema_version,
        settings_schema=settings_state.settings_schema,
        values=settings_state.values,
        state_rev=settings_state.state_rev,
    )


@router.put("/{tool_id}/settings", response_model=ToolSettingsResponse)
@inject
async def update_tool_settings(
    tool_id: UUID,
    payload: UpdateToolSettingsRequest,
    handler: FromDishka[UpdateToolSettingsHandlerProtocol],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> ToolSettingsResponse:
    result = await handler.handle(
        actor=user,
        command=UpdateToolSettingsCommand(
            tool_id=tool_id,
            expected_state_rev=payload.expected_state_rev,
            values=payload.values,
        ),
    )
    settings_state = result.settings
    return ToolSettingsResponse(
        tool_id=settings_state.tool_id,
        schema_version=settings_state.schema_version,
        settings_schema=settings_state.settings_schema,
        values=settings_state.values,
        state_rev=settings_state.state_rev,
    )
