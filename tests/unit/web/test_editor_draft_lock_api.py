from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.draft_locks import (
    AcquireDraftLockResult,
    ReleaseDraftLockResult,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.draft_locks import DraftLock
from skriptoteket.domain.scripting.models import VersionState
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.draft_locks import (
    AcquireDraftLockHandlerProtocol,
    DraftLockRepositoryProtocol,
    ReleaseDraftLockHandlerProtocol,
)
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol
from skriptoteket.web.api.v1 import editor
from tests.unit.web.admin_scripting_test_support import _tool, _user, _version


def _unwrap_dishka(fn):
    """Extract original function from Dishka-wrapped handlers."""
    return getattr(fn, "__dishka_orig_func__", fn)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_acquire_draft_lock_endpoint_returns_lock_response() -> None:
    handler = AsyncMock(spec=AcquireDraftLockHandlerProtocol)
    tool = _tool()
    user = _user(role=Role.CONTRIBUTOR)
    draft_head_id = uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    handler.handle.return_value = AcquireDraftLockResult(
        tool_id=tool.id,
        draft_head_id=draft_head_id,
        locked_by_user_id=user.id,
        expires_at=expires_at,
        is_owner=True,
    )

    result = await _unwrap_dishka(editor.acquire_draft_lock)(
        tool_id=tool.id,
        payload=editor.DraftLockRequest(draft_head_id=draft_head_id, force=False),
        handler=handler,
        user=user,
        _=None,
    )

    assert isinstance(result, editor.DraftLockResponse)
    assert result.tool_id == tool.id
    assert result.draft_head_id == draft_head_id
    assert result.locked_by_user_id == user.id
    assert result.expires_at == expires_at
    assert result.is_owner is True

    command = handler.handle.call_args.kwargs["command"]
    assert command.tool_id == tool.id
    assert command.draft_head_id == draft_head_id
    assert command.force is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_release_draft_lock_endpoint_returns_release_response() -> None:
    handler = AsyncMock(spec=ReleaseDraftLockHandlerProtocol)
    tool = _tool()
    user = _user(role=Role.ADMIN)
    handler.handle.return_value = ReleaseDraftLockResult(tool_id=tool.id)

    result = await _unwrap_dishka(editor.release_draft_lock)(
        tool_id=tool.id,
        handler=handler,
        user=user,
        _=None,
    )

    assert isinstance(result, editor.DraftLockReleaseResponse)
    assert result.tool_id == tool.id
    handler.handle.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_editor_boot_includes_draft_lock_metadata() -> None:
    tools = AsyncMock()
    maintainers = AsyncMock()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    locks = AsyncMock(spec=DraftLockRepositoryProtocol)
    clock = Mock(spec=ClockProtocol)

    tool = _tool()
    user = _user(role=Role.ADMIN)
    draft = _version(
        tool_id=tool.id,
        created_by_user_id=user.id,
        state=VersionState.DRAFT,
        version_number=2,
    )
    versions.list_for_tool.return_value = [draft]
    tools.get_by_id.return_value = tool
    clock.now.return_value = datetime.now(timezone.utc)
    locks.get_for_tool.return_value = DraftLock(
        tool_id=tool.id,
        draft_head_id=draft.id,
        locked_by_user_id=user.id,
        locked_at=clock.now.return_value,
        expires_at=clock.now.return_value + timedelta(minutes=10),
        forced_by_user_id=None,
    )

    result = await _unwrap_dishka(editor.get_editor_for_tool)(
        tool_id=tool.id,
        tools=tools,
        maintainers=maintainers,
        versions_repo=versions,
        locks=locks,
        clock=clock,
        user=user,
    )

    assert isinstance(result, editor.EditorBootResponse)
    assert result.draft_head_id == draft.id
    assert result.save_mode == "snapshot"
    assert result.parent_version_id is None
    assert result.create_draft_from_version_id is None
    assert result.selected_version is not None
    assert result.selected_version.reviewed_at is None
    assert result.selected_version.published_at is None
    assert result.versions[0].reviewed_at is None
    assert result.versions[0].published_at is None
    assert result.draft_lock is not None
    assert result.draft_lock.tool_id == tool.id
    assert result.draft_lock.is_owner is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_editor_boot_includes_parent_and_create_draft_ids_for_non_draft() -> None:
    tools = AsyncMock()
    maintainers = AsyncMock()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    locks = AsyncMock(spec=DraftLockRepositoryProtocol)
    clock = Mock(spec=ClockProtocol)

    user = _user(role=Role.ADMIN)
    now = datetime.now(timezone.utc)

    tool = _tool().model_copy(update={"is_published": True})
    previous = _version(
        tool_id=tool.id,
        created_by_user_id=user.id,
        state=VersionState.ARCHIVED,
        version_number=1,
    ).model_copy(update={"reviewed_at": now})
    active = _version(
        tool_id=tool.id,
        created_by_user_id=user.id,
        state=VersionState.ACTIVE,
        version_number=2,
    ).model_copy(update={"derived_from_version_id": previous.id, "published_at": now})
    tool = tool.model_copy(update={"active_version_id": active.id})

    versions.list_for_tool.return_value = [active, previous]
    tools.get_by_id.return_value = tool
    clock.now.return_value = now
    locks.get_for_tool.return_value = None

    result = await _unwrap_dishka(editor.get_editor_for_tool)(
        tool_id=tool.id,
        tools=tools,
        maintainers=maintainers,
        versions_repo=versions,
        locks=locks,
        clock=clock,
        user=user,
    )

    assert isinstance(result, editor.EditorBootResponse)
    assert result.save_mode == "create_draft"
    assert result.parent_version_id == previous.id
    assert result.create_draft_from_version_id == active.id
    assert result.selected_version is not None
    assert result.selected_version.published_at == now
    assert result.selected_version.reviewed_at is None
    assert result.versions[0].id == active.id
    assert result.versions[0].published_at == now
    assert result.versions[1].id == previous.id
    assert result.versions[1].reviewed_at == now
