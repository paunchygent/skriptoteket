from datetime import datetime
from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends

from skriptoteket.domain.catalog.models import Tool
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.draft_locks import DraftLock
from skriptoteket.domain.scripting.models import ToolVersion, VersionState
from skriptoteket.domain.scripting.tool_inputs import ToolInputField
from skriptoteket.domain.scripting.ui.contract_v2 import UiActionField
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol, ToolRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.draft_locks import DraftLockRepositoryProtocol
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol
from skriptoteket.web.auth.api_dependencies import require_contributor_api
from skriptoteket.web.editor_support import (
    DEFAULT_ENTRYPOINT,
    STARTER_TEMPLATE,
    require_tool_access,
    select_default_version,
    visible_versions_for_actor,
)

from .models import (
    DraftLockResponse,
    EditorBootResponse,
    EditorSaveMode,
    EditorToolSummary,
    EditorVersionSummary,
)

router = APIRouter()


def _to_tool_summary(tool: Tool) -> EditorToolSummary:
    return EditorToolSummary(
        id=tool.id,
        slug=tool.slug,
        title=tool.title,
        summary=tool.summary,
        is_published=tool.is_published,
        active_version_id=tool.active_version_id,
    )


def _to_version_summary(version: ToolVersion) -> EditorVersionSummary:
    return EditorVersionSummary(
        id=version.id,
        version_number=version.version_number,
        state=version.state,
        created_at=version.created_at,
        reviewed_at=version.reviewed_at,
        published_at=version.published_at,
    )


def _resolve_draft_head(versions: list[ToolVersion]) -> ToolVersion | None:
    for version in versions:
        if version.state is VersionState.DRAFT:
            return version
    return None


def _to_draft_lock_response(
    *,
    lock: DraftLock | None,
    draft_head_id: UUID | None,
    actor: User,
    now: datetime,
) -> DraftLockResponse | None:
    if lock is None or draft_head_id is None:
        return None
    if lock.expires_at <= now:
        return None
    if lock.draft_head_id != draft_head_id:
        return None
    return DraftLockResponse(
        tool_id=lock.tool_id,
        draft_head_id=lock.draft_head_id,
        locked_by_user_id=lock.locked_by_user_id,
        expires_at=lock.expires_at,
        is_owner=lock.locked_by_user_id == actor.id,
    )


def _resolve_editor_state(
    selected_version: ToolVersion | None,
) -> tuple[
    str,
    str,
    list[UiActionField] | None,
    list[ToolInputField],
    str | None,
    EditorSaveMode,
    UUID | None,
    UUID | None,
]:
    if selected_version is None:
        return DEFAULT_ENTRYPOINT, STARTER_TEMPLATE, None, [], None, "create_draft", None, None

    is_draft = selected_version.state is VersionState.DRAFT
    save_mode: EditorSaveMode = "snapshot" if is_draft else "create_draft"
    parent_version_id = selected_version.derived_from_version_id
    create_draft_from_version_id = None if is_draft else selected_version.id
    return (
        selected_version.entrypoint,
        selected_version.source_code,
        selected_version.settings_schema,
        selected_version.input_schema,
        selected_version.usage_instructions,
        save_mode,
        parent_version_id,
        create_draft_from_version_id,
    )


def _build_editor_response(
    *,
    tool: Tool,
    visible_versions: list[ToolVersion],
    selected_version: ToolVersion | None,
    draft_head_id: UUID | None,
    draft_lock: DraftLockResponse | None,
) -> EditorBootResponse:
    (
        entrypoint,
        source_code,
        settings_schema,
        input_schema,
        usage_instructions,
        save_mode,
        parent_version_id,
        create_draft_from_version_id,
    ) = _resolve_editor_state(selected_version)

    return EditorBootResponse(
        tool=_to_tool_summary(tool),
        versions=[_to_version_summary(v) for v in visible_versions],
        selected_version=_to_version_summary(selected_version) if selected_version else None,
        draft_head_id=draft_head_id,
        draft_lock=draft_lock,
        save_mode=save_mode,
        parent_version_id=parent_version_id,
        create_draft_from_version_id=create_draft_from_version_id,
        entrypoint=entrypoint,
        source_code=source_code,
        settings_schema=settings_schema,
        input_schema=input_schema,
        usage_instructions=usage_instructions,
    )


@router.get("/tools/{tool_id}", response_model=EditorBootResponse)
@inject
async def get_editor_for_tool(
    tool_id: UUID,
    tools: FromDishka[ToolRepositoryProtocol],
    maintainers: FromDishka[ToolMaintainerRepositoryProtocol],
    versions_repo: FromDishka[ToolVersionRepositoryProtocol],
    locks: FromDishka[DraftLockRepositoryProtocol],
    clock: FromDishka[ClockProtocol],
    user: User = Depends(require_contributor_api),
) -> EditorBootResponse:
    tool = await tools.get_by_id(tool_id=tool_id)
    if tool is None:
        raise not_found("Tool", str(tool_id))

    is_tool_maintainer = await require_tool_access(
        actor=user,
        tool_id=tool.id,
        maintainers=maintainers,
    )
    versions = await versions_repo.list_for_tool(tool_id=tool.id, limit=50)
    visible_versions = visible_versions_for_actor(
        actor=user,
        versions=versions,
        is_tool_maintainer=is_tool_maintainer,
    )
    selected_version = select_default_version(
        actor=user,
        tool=tool,
        versions=versions,
        is_tool_maintainer=is_tool_maintainer,
    )
    draft_head = _resolve_draft_head(versions)
    draft_head_id = draft_head.id if draft_head else None
    draft_lock = _to_draft_lock_response(
        lock=await locks.get_for_tool(tool_id=tool.id),
        draft_head_id=draft_head_id,
        actor=user,
        now=clock.now(),
    )
    return _build_editor_response(
        tool=tool,
        visible_versions=visible_versions,
        selected_version=selected_version,
        draft_head_id=draft_head_id,
        draft_lock=draft_lock,
    )


@router.get("/tool-versions/{version_id}", response_model=EditorBootResponse)
@inject
async def get_editor_for_version(
    version_id: UUID,
    tools: FromDishka[ToolRepositoryProtocol],
    maintainers: FromDishka[ToolMaintainerRepositoryProtocol],
    versions_repo: FromDishka[ToolVersionRepositoryProtocol],
    locks: FromDishka[DraftLockRepositoryProtocol],
    clock: FromDishka[ClockProtocol],
    user: User = Depends(require_contributor_api),
) -> EditorBootResponse:
    version = await versions_repo.get_by_id(version_id=version_id)
    if version is None:
        raise not_found("ToolVersion", str(version_id))

    tool = await tools.get_by_id(tool_id=version.tool_id)
    if tool is None:
        raise not_found("Tool", str(version.tool_id))

    is_tool_maintainer = await require_tool_access(
        actor=user,
        tool_id=tool.id,
        maintainers=maintainers,
    )
    versions = await versions_repo.list_for_tool(tool_id=tool.id, limit=50)
    visible_versions = visible_versions_for_actor(
        actor=user,
        versions=versions,
        is_tool_maintainer=is_tool_maintainer,
    )
    if not any(v.id == version.id for v in visible_versions):
        raise DomainError(
            code=ErrorCode.FORBIDDEN,
            message="Insufficient permissions",
            details={"tool_id": str(tool.id), "version_id": str(version.id)},
        )

    draft_head = _resolve_draft_head(versions)
    draft_head_id = draft_head.id if draft_head else None
    draft_lock = _to_draft_lock_response(
        lock=await locks.get_for_tool(tool_id=tool.id),
        draft_head_id=draft_head_id,
        actor=user,
        now=clock.now(),
    )
    return _build_editor_response(
        tool=tool,
        visible_versions=visible_versions,
        selected_version=version,
        draft_head_id=draft_head_id,
        draft_lock=draft_lock,
    )
