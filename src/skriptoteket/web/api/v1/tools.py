import json
from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, ConfigDict, JsonValue

from skriptoteket.application.scripting.commands import RunActiveToolCommand
from skriptoteket.application.scripting.tool_settings import (
    GetToolSettingsQuery,
    UpdateToolSettingsCommand,
)
from skriptoteket.config import Settings
from skriptoteket.domain.catalog.models import Tool
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.models import ToolVersion, VersionState
from skriptoteket.domain.scripting.tool_inputs import ToolInputField
from skriptoteket.domain.scripting.tool_usage_instructions import (
    USAGE_INSTRUCTIONS_SEEN_HASH_KEY,
    USAGE_INSTRUCTIONS_SESSION_CONTEXT,
    compute_usage_instructions_hash_or_none,
)
from skriptoteket.domain.scripting.ui.contract_v2 import UiActionField
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import (
    RunActiveToolHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.tool_settings import (
    GetToolSettingsHandlerProtocol,
    UpdateToolSettingsHandlerProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol
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
    usage_instructions_seen: bool
    upload_constraints: UploadConstraints
    input_schema: list[ToolInputField] | None = None


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


class MarkUsageInstructionsSeenResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    usage_instructions_seen: bool
    state_rev: int


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


async def _load_runnable_tool_by_id(
    *,
    tools: ToolRepositoryProtocol,
    versions: ToolVersionRepositoryProtocol,
    tool_id: UUID,
) -> tuple[Tool, ToolVersion]:
    tool = await tools.get_by_id(tool_id=tool_id)
    if tool is None:
        raise not_found("Tool", str(tool_id))
    if not tool.is_published:
        raise not_found("Tool", str(tool_id))
    if tool.active_version_id is None:
        raise not_found("Tool", str(tool_id))

    version = await versions.get_by_id(version_id=tool.active_version_id)
    if version is None:
        raise not_found("ToolVersion", str(tool.active_version_id))
    if version.state is not VersionState.ACTIVE:
        raise not_found("ToolVersion", str(tool.active_version_id))

    return tool, version


@router.get("/{slug}", response_model=ToolMetadataResponse)
@inject
async def get_tool_by_slug(
    slug: str,
    uow: FromDishka[UnitOfWorkProtocol],
    tools: FromDishka[ToolRepositoryProtocol],
    versions: FromDishka[ToolVersionRepositoryProtocol],
    sessions: FromDishka[ToolSessionRepositoryProtocol],
    id_generator: FromDishka[IdGeneratorProtocol],
    settings: FromDishka[Settings],
    user: User = Depends(require_user_api),
) -> ToolMetadataResponse:
    async with uow:
        tool, version = await _load_runnable_tool(tools=tools, versions=versions, slug=slug)

        usage_instructions_hash = compute_usage_instructions_hash_or_none(
            usage_instructions=version.usage_instructions,
        )
        if usage_instructions_hash is None:
            usage_instructions_seen = True
        else:
            session = await sessions.get_or_create(
                session_id=id_generator.new_uuid(),
                tool_id=tool.id,
                user_id=user.id,
                context=USAGE_INSTRUCTIONS_SESSION_CONTEXT,
            )
            stored_hash = session.state.get(USAGE_INSTRUCTIONS_SEEN_HASH_KEY)
            usage_instructions_seen = (
                isinstance(stored_hash, str) and stored_hash == usage_instructions_hash
            )

    return ToolMetadataResponse(
        id=tool.id,
        slug=tool.slug,
        title=tool.title,
        summary=tool.summary,
        usage_instructions=version.usage_instructions,
        usage_instructions_seen=usage_instructions_seen,
        upload_constraints=UploadConstraints(
            max_files=settings.UPLOAD_MAX_FILES,
            max_file_bytes=settings.UPLOAD_MAX_FILE_BYTES,
            max_total_bytes=settings.UPLOAD_MAX_TOTAL_BYTES,
        ),
        input_schema=version.input_schema,
    )


@router.post("/{slug}/run", response_model=StartToolRunResponse)
@inject
async def start_tool_run(
    slug: str,
    handler: FromDishka[RunActiveToolHandlerProtocol],
    settings: FromDishka[Settings],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
    files: list[UploadFile] | None = File(None),
    inputs: str | None = Form(None),
) -> StartToolRunResponse:
    input_files: list[tuple[str, bytes]] = []
    if files:
        input_files = await read_upload_files(
            files=files,
            max_files=settings.UPLOAD_MAX_FILES,
            max_file_bytes=settings.UPLOAD_MAX_FILE_BYTES,
            max_total_bytes=settings.UPLOAD_MAX_TOTAL_BYTES,
        )

    input_values: dict[str, JsonValue] = {}
    if inputs is not None and inputs.strip():
        try:
            parsed = json.loads(inputs)
        except json.JSONDecodeError as exc:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="inputs must be valid JSON",
            ) from exc
        if not isinstance(parsed, dict):
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="inputs must be a JSON object",
            )
        input_values = parsed

    result = await handler.handle(
        actor=user,
        command=RunActiveToolCommand(
            tool_slug=slug,
            input_files=input_files,
            input_values=input_values,
        ),
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


@router.post(
    "/{tool_id}/usage-instructions/seen",
    response_model=MarkUsageInstructionsSeenResponse,
)
@inject
async def mark_usage_instructions_seen(
    tool_id: UUID,
    uow: FromDishka[UnitOfWorkProtocol],
    tools: FromDishka[ToolRepositoryProtocol],
    versions: FromDishka[ToolVersionRepositoryProtocol],
    sessions: FromDishka[ToolSessionRepositoryProtocol],
    id_generator: FromDishka[IdGeneratorProtocol],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> MarkUsageInstructionsSeenResponse:
    async with uow:
        tool, version = await _load_runnable_tool_by_id(
            tools=tools, versions=versions, tool_id=tool_id
        )

        usage_instructions_hash = compute_usage_instructions_hash_or_none(
            usage_instructions=version.usage_instructions,
        )

        session = await sessions.get_or_create(
            session_id=id_generator.new_uuid(),
            tool_id=tool.id,
            user_id=user.id,
            context=USAGE_INSTRUCTIONS_SESSION_CONTEXT,
        )

        if usage_instructions_hash is None:
            return MarkUsageInstructionsSeenResponse(
                tool_id=tool.id,
                usage_instructions_seen=True,
                state_rev=session.state_rev,
            )

        for _attempt in range(2):
            stored_hash = session.state.get(USAGE_INSTRUCTIONS_SEEN_HASH_KEY)
            if isinstance(stored_hash, str) and stored_hash == usage_instructions_hash:
                return MarkUsageInstructionsSeenResponse(
                    tool_id=tool.id,
                    usage_instructions_seen=True,
                    state_rev=session.state_rev,
                )

            next_state = dict(session.state)
            next_state[USAGE_INSTRUCTIONS_SEEN_HASH_KEY] = usage_instructions_hash

            try:
                session = await sessions.update_state(
                    tool_id=tool.id,
                    user_id=user.id,
                    context=USAGE_INSTRUCTIONS_SESSION_CONTEXT,
                    expected_state_rev=session.state_rev,
                    state=next_state,
                )
                return MarkUsageInstructionsSeenResponse(
                    tool_id=tool.id,
                    usage_instructions_seen=True,
                    state_rev=session.state_rev,
                )
            except DomainError as exc:
                if exc.code is ErrorCode.CONFLICT:
                    session = await sessions.get_or_create(
                        session_id=id_generator.new_uuid(),
                        tool_id=tool.id,
                        user_id=user.id,
                        context=USAGE_INSTRUCTIONS_SESSION_CONTEXT,
                    )
                    continue
                raise

        return MarkUsageInstructionsSeenResponse(
            tool_id=tool.id,
            usage_instructions_seen=True,
            state_rev=session.state_rev,
        )
