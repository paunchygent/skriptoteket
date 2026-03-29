import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import BaseModel, ConfigDict, Field, JsonValue

from skriptoteket.application.scripting.commands import (
    RunActiveToolCommand,
    SessionFilesMode,
)
from skriptoteket.application.scripting.file_refs import (
    ListToolFileRefsQuery,
    ListToolFileRefsResult,
)
from skriptoteket.application.scripting.tool_settings import (
    GetToolSettingsQuery,
    UpdateToolSettingsCommand,
)
from skriptoteket.config import Settings
from skriptoteket.domain.catalog.models import Tool
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.file_refs import FileRefSource
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
    ListToolFileRefsHandlerProtocol,
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
from skriptoteket.web.dishka_dependencies import FromDishka
from skriptoteket.web.uploads import read_upload_files

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


def _parse_session_files_mode(value: str | None) -> SessionFilesMode:
    if value is None:
        return SessionFilesMode.NONE
    normalized = value.strip()
    if not normalized:
        return SessionFilesMode.NONE
    try:
        return SessionFilesMode(normalized)
    except ValueError as exc:
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="session_files_mode must be one of: none, reuse, clear",
            details={"session_files_mode": normalized},
        ) from exc


def _parse_file_refs_by_field(raw: str | None) -> dict[str, list[str]]:
    if raw is None or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="file_refs_by_field must be valid JSON",
        ) from exc
    if not isinstance(parsed, dict):
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="file_refs_by_field must be a JSON object",
        )
    normalized: dict[str, list[str]] = {}
    for key, value in parsed.items():
        if not isinstance(key, str) or not key.strip():
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="file_refs_by_field keys must be non-empty strings",
            )
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="file_refs_by_field values must be lists of strings",
            )
        normalized[key] = [item.strip() for item in value if item.strip()]
    return normalized


def _parse_file_ref_sources(raw: list[str] | None) -> list[FileRefSource]:
    if raw is None or not raw:
        return [FileRefSource.SESSION, FileRefSource.VAULT]
    tokens: list[str] = []
    for item in raw:
        for part in item.split(","):
            normalized = part.strip().lower()
            if normalized:
                tokens.append(normalized)
    if not tokens:
        return [FileRefSource.SESSION, FileRefSource.VAULT]
    sources: list[FileRefSource] = []
    seen: set[FileRefSource] = set()
    for token in tokens:
        try:
            source = FileRefSource(token)
        except ValueError as exc:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="sources must be a subset of: session, vault",
                details={"sources": tokens},
            ) from exc
        if source in seen:
            continue
        seen.add(source)
        sources.append(source)
    return sources


def _parse_file_fields(raw: str | None, *, expected_len: int) -> list[str]:
    if expected_len == 0:
        return []
    if raw is None or not raw.strip():
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="file_fields is required when uploading files",
            details={"files": expected_len},
        )
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="file_fields must be valid JSON",
        ) from exc
    if not isinstance(parsed, list) or any(not isinstance(item, str) for item in parsed):
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="file_fields must be a JSON array of strings",
        )
    if len(parsed) != expected_len:
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="file_fields length must match files",
            details={"file_fields": len(parsed), "files": expected_len},
        )
    normalized: list[str] = []
    for item in parsed:
        normalized_item = item.strip()
        if not normalized_item:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="file_fields entries must be non-empty strings",
            )
        normalized.append(normalized_item)
    return normalized


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
    input_schema: list[ToolInputField] = Field(default_factory=list)


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
async def start_tool_run(
    slug: str,
    handler: FromDishka[RunActiveToolHandlerProtocol],
    settings: FromDishka[Settings],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
    files: Annotated[list[UploadFile] | None, File()] = None,
    inputs: Annotated[str | None, Form()] = None,
    file_fields: Annotated[str | None, Form()] = None,
    file_refs_by_field: Annotated[str | None, Form()] = None,
    session_files_mode: Annotated[str | None, Form()] = None,
    session_context: Annotated[str | None, Form()] = None,
) -> StartToolRunResponse:
    input_files: list[tuple[str, bytes]] = []
    if files:
        input_files = await read_upload_files(
            files=files,
            max_files=settings.UPLOAD_MAX_FILES,
            max_file_bytes=settings.UPLOAD_MAX_FILE_BYTES,
            max_total_bytes=settings.UPLOAD_MAX_TOTAL_BYTES,
        )
    input_files_by_field: dict[str, list[tuple[str, bytes]]] = {}
    if input_files:
        parsed_fields = _parse_file_fields(file_fields, expected_len=len(input_files))
        for entry, field in zip(input_files, parsed_fields, strict=True):
            input_files_by_field.setdefault(field, []).append(entry)
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
    parsed_file_refs_by_field = _parse_file_refs_by_field(file_refs_by_field)
    context = session_context.strip() if session_context is not None else ""
    result = await handler.handle(
        actor=user,
        command=RunActiveToolCommand(
            tool_slug=slug,
            input_files_by_field=input_files_by_field,
            input_values=input_values,
            file_refs_by_field=parsed_file_refs_by_field,
            session_context=context or "default",
            session_files_mode=_parse_session_files_mode(session_files_mode),
        ),
    )
    return StartToolRunResponse(run_id=result.run.id)


@router.get("/{tool_id}/file-refs", response_model=ListToolFileRefsResult)
async def list_tool_file_refs(
    tool_id: UUID,
    handler: FromDishka[ListToolFileRefsHandlerProtocol],
    user: User = Depends(require_user_api),
    context: str = Query("default"),
    sources: list[str] | None = Query(None),
) -> ListToolFileRefsResult:
    parsed_sources = _parse_file_ref_sources(sources)
    return await handler.handle(
        actor=user,
        query=ListToolFileRefsQuery(
            tool_id=tool_id,
            context=context,
            sources=parsed_sources,
        ),
    )


@router.get("/{tool_id}/settings", response_model=ToolSettingsResponse)
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
