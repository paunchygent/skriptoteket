import json
from typing import Annotated
from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import JsonValue, ValidationError

from skriptoteket.application.scripting.commands import (
    RunSandboxCommand,
    SandboxSnapshotPayload,
    SessionFilesMode,
)
from skriptoteket.application.scripting.session_files import (
    ListSandboxSessionFilesQuery,
    ListSandboxSessionFilesResult,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.scripting import (
    ListSandboxSessionFilesHandlerProtocol,
    RunSandboxHandlerProtocol,
    StartSandboxActionHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.web.auth.api_dependencies import (
    require_contributor_api,
    require_csrf_token,
)
from skriptoteket.web.uploads import read_upload_files

from .models import (
    SandboxRunResponse,
    SandboxSessionResponse,
    StartSandboxActionRequest,
    StartSandboxActionResponse,
)

router = APIRouter()


def _sandbox_context(context_id: UUID) -> str:
    """Build sandbox session context per ADR-0044."""
    return f"sandbox:{context_id}"


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


@router.post("/tool-versions/{version_id}/run-sandbox", response_model=SandboxRunResponse)
@inject
async def run_sandbox(
    version_id: UUID,
    handler: FromDishka[RunSandboxHandlerProtocol],
    versions_repo: FromDishka[ToolVersionRepositoryProtocol],
    settings: FromDishka[Settings],
    user: User = Depends(require_contributor_api),
    _: None = Depends(require_csrf_token),
    files: Annotated[list[UploadFile] | None, File()] = None,
    inputs: Annotated[str | None, Form()] = None,
    session_files_mode: Annotated[str | None, Form()] = None,
    session_context: Annotated[str | None, Form()] = None,
    snapshot: str = Form(...),
) -> SandboxRunResponse:
    version = await versions_repo.get_by_id(version_id=version_id)
    if version is None:
        raise not_found("ToolVersion", str(version_id))

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

    try:
        snapshot_payload = SandboxSnapshotPayload.model_validate_json(snapshot)
    except ValidationError as exc:
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="snapshot must be valid JSON",
            details={"errors": exc.errors()},
        ) from exc

    result = await handler.handle(
        actor=user,
        command=RunSandboxCommand(
            tool_id=version.tool_id,
            version_id=version_id,
            snapshot_payload=snapshot_payload,
            input_files=input_files,
            input_values=input_values,
            session_context=session_context.strip() if session_context else None,
            session_files_mode=_parse_session_files_mode(session_files_mode),
        ),
    )
    run = result.run
    if run.started_at is None:
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Sandbox run missing started_at",
            details={"run_id": str(run.id)},
        )
    return SandboxRunResponse(
        run_id=run.id,
        status=run.status,
        started_at=run.started_at,
        state_rev=result.state_rev,
        snapshot_id=result.snapshot_id,
    )


@router.get("/tool-versions/{version_id}/session", response_model=SandboxSessionResponse)
@inject
async def get_sandbox_session(
    version_id: UUID,
    versions_repo: FromDishka[ToolVersionRepositoryProtocol],
    sessions: FromDishka[ToolSessionRepositoryProtocol],
    user: User = Depends(require_contributor_api),
    snapshot_id: UUID | None = Query(None),
) -> SandboxSessionResponse:
    """Get sandbox session state for a tool version (ADR-0038)."""
    version = await versions_repo.get_by_id(version_id=version_id)
    if version is None:
        raise not_found("ToolVersion", str(version_id))

    context = _sandbox_context(snapshot_id or version_id)
    session = await sessions.get(
        tool_id=version.tool_id,
        user_id=user.id,
        context=context,
    )
    if session is None:
        raise not_found("SandboxSession", str(version_id))

    return SandboxSessionResponse(
        state_rev=session.state_rev,
        state=session.state,
    )


@router.get(
    "/tool-versions/{version_id}/session-files",
    response_model=ListSandboxSessionFilesResult,
)
@inject
async def list_sandbox_session_files(
    version_id: UUID,
    handler: FromDishka[ListSandboxSessionFilesHandlerProtocol],
    user: User = Depends(require_contributor_api),
    snapshot_id: UUID = Query(...),
) -> ListSandboxSessionFilesResult:
    return await handler.handle(
        actor=user,
        query=ListSandboxSessionFilesQuery(
            version_id=version_id,
            snapshot_id=snapshot_id,
        ),
    )


@router.post(
    "/tool-versions/{version_id}/start-action",
    response_model=StartSandboxActionResponse,
)
@inject
async def start_sandbox_action(
    version_id: UUID,
    payload: StartSandboxActionRequest,
    versions_repo: FromDishka[ToolVersionRepositoryProtocol],
    handler: FromDishka[StartSandboxActionHandlerProtocol],
    user: User = Depends(require_contributor_api),
    _: None = Depends(require_csrf_token),
) -> StartSandboxActionResponse:
    """Start a sandbox action for a tool version (ADR-0038)."""
    version = await versions_repo.get_by_id(version_id=version_id)
    if version is None:
        raise not_found("ToolVersion", str(version_id))

    from skriptoteket.application.scripting.interactive_sandbox import (
        StartSandboxActionCommand,
    )

    result = await handler.handle(
        actor=user,
        command=StartSandboxActionCommand(
            tool_id=version.tool_id,
            version_id=version_id,
            snapshot_id=payload.snapshot_id,
            action_id=payload.action_id,
            input=payload.input,
            expected_state_rev=payload.expected_state_rev,
        ),
    )
    return StartSandboxActionResponse(
        run_id=result.run_id,
        state_rev=result.state_rev,
    )
