from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.models import VersionState
from skriptoteket.domain.scripting.tool_sessions import ToolSession
from skriptoteket.domain.scripting.tool_usage_instructions import (
    USAGE_INSTRUCTIONS_SEEN_HASH_KEY,
    USAGE_INSTRUCTIONS_SESSION_CONTEXT,
    compute_usage_instructions_hash_or_none,
)
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.web.api.v1 import tools as tools_api
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.identity_fixtures import make_user
from tests.unit.web.admin_scripting_test_support import _tool, _version


def _unwrap_dishka(fn):
    """Extract original function from Dishka-wrapped handlers."""
    return getattr(fn, "__dishka_orig_func__", fn)


def _make_tool_session(
    *,
    now: datetime,
    session_id: UUID,
    tool_id: UUID,
    user_id: UUID,
    context: str,
    state: dict[str, object] | None = None,
    state_rev: int = 0,
) -> ToolSession:
    return ToolSession(
        id=session_id,
        tool_id=tool_id,
        user_id=user_id,
        context=context,
        state={} if state is None else state,
        state_rev=state_rev,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tool_by_slug_returns_usage_instructions_seen_false_when_unseen(
    now: datetime,
) -> None:
    user = make_user(role=Role.USER, user_id=uuid4())
    uow = FakeUow()

    tool = _tool(title="Tool").model_copy(
        update={"slug": "my-tool", "is_published": True},
    )
    version = _version(
        tool_id=tool.id,
        created_by_user_id=user.id,
        state=VersionState.ACTIVE,
    ).model_copy(update={"usage_instructions": "# Instruktion"})
    tool = tool.model_copy(update={"active_version_id": version.id})

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_slug.return_value = tool

    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = version

    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    sessions.get_or_create.return_value = _make_tool_session(
        now=now,
        session_id=uuid4(),
        tool_id=tool.id,
        user_id=user.id,
        context=USAGE_INSTRUCTIONS_SESSION_CONTEXT,
        state={},
        state_rev=0,
    )

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = uuid4()

    result = await _unwrap_dishka(tools_api.get_tool_by_slug)(
        slug="my-tool",
        uow=uow,
        tools=tools,
        versions=versions,
        sessions=sessions,
        id_generator=id_generator,
        settings=Settings(),
        user=user,
    )

    assert result.usage_instructions == "# Instruktion"
    assert result.usage_instructions_seen is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tool_by_slug_returns_usage_instructions_seen_true_when_hash_matches(
    now: datetime,
) -> None:
    user = make_user(role=Role.USER, user_id=uuid4())
    uow = FakeUow()

    tool = _tool(title="Tool").model_copy(
        update={"slug": "my-tool", "is_published": True},
    )
    version = _version(
        tool_id=tool.id,
        created_by_user_id=user.id,
        state=VersionState.ACTIVE,
    ).model_copy(update={"usage_instructions": "Hej"})
    tool = tool.model_copy(update={"active_version_id": version.id})

    usage_hash = compute_usage_instructions_hash_or_none(
        usage_instructions=version.usage_instructions,
    )
    assert usage_hash is not None

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_slug.return_value = tool

    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = version

    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    sessions.get_or_create.return_value = _make_tool_session(
        now=now,
        session_id=uuid4(),
        tool_id=tool.id,
        user_id=user.id,
        context=USAGE_INSTRUCTIONS_SESSION_CONTEXT,
        state={USAGE_INSTRUCTIONS_SEEN_HASH_KEY: usage_hash},
        state_rev=1,
    )

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = uuid4()

    result = await _unwrap_dishka(tools_api.get_tool_by_slug)(
        slug="my-tool",
        uow=uow,
        tools=tools,
        versions=versions,
        sessions=sessions,
        id_generator=id_generator,
        settings=Settings(),
        user=user,
    )

    assert result.usage_instructions_seen is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mark_usage_instructions_seen_persists_hash_and_returns_state_rev(
    now: datetime,
) -> None:
    user = make_user(role=Role.USER, user_id=uuid4())
    uow = FakeUow()

    tool = _tool(title="Tool").model_copy(update={"is_published": True})
    version = _version(
        tool_id=tool.id,
        created_by_user_id=user.id,
        state=VersionState.ACTIVE,
    ).model_copy(update={"usage_instructions": "Hej"})
    tool = tool.model_copy(update={"active_version_id": version.id})

    usage_hash = compute_usage_instructions_hash_or_none(
        usage_instructions=version.usage_instructions,
    )
    assert usage_hash is not None

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool

    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = version

    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    sessions.get_or_create.return_value = _make_tool_session(
        now=now,
        session_id=uuid4(),
        tool_id=tool.id,
        user_id=user.id,
        context=USAGE_INSTRUCTIONS_SESSION_CONTEXT,
        state={},
        state_rev=0,
    )
    sessions.update_state.return_value = _make_tool_session(
        now=now,
        session_id=uuid4(),
        tool_id=tool.id,
        user_id=user.id,
        context=USAGE_INSTRUCTIONS_SESSION_CONTEXT,
        state={USAGE_INSTRUCTIONS_SEEN_HASH_KEY: usage_hash},
        state_rev=1,
    )

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = uuid4()

    result = await _unwrap_dishka(tools_api.mark_usage_instructions_seen)(
        tool_id=tool.id,
        uow=uow,
        tools=tools,
        versions=versions,
        sessions=sessions,
        id_generator=id_generator,
        user=user,
    )

    assert result.tool_id == tool.id
    assert result.usage_instructions_seen is True
    assert result.state_rev == 1

    sessions.update_state.assert_awaited_once()
    update_kwargs = sessions.update_state.call_args.kwargs
    assert update_kwargs["tool_id"] == tool.id
    assert update_kwargs["user_id"] == user.id
    assert update_kwargs["context"] == USAGE_INSTRUCTIONS_SESSION_CONTEXT
    assert update_kwargs["expected_state_rev"] == 0
    assert update_kwargs["state"][USAGE_INSTRUCTIONS_SEEN_HASH_KEY] == usage_hash
