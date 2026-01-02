from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import cast
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pytest
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from skriptoteket.application.scripting.session_files import (
    ListSessionFilesResult,
    SessionFileInfo,
)
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
from skriptoteket.protocols.identity import CurrentUserProviderProtocol
from skriptoteket.protocols.interactive_tools import ListSessionFilesHandlerProtocol
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.web.api.v1 import tools as tools_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from skriptoteket.web.routes import interactive_tools as interactive_tools_routes
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


class InteractiveToolsApiProvider(Provider):
    def __init__(
        self,
        *,
        settings: Settings,
        current_user_provider: AsyncMock,
        list_session_files_handler: AsyncMock,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._current_user_provider = current_user_provider
        self._list_session_files_handler = list_session_files_handler

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return self._settings

    @provide(scope=Scope.REQUEST)
    def current_user_provider(self) -> CurrentUserProviderProtocol:
        return cast(CurrentUserProviderProtocol, self._current_user_provider)

    @provide(scope=Scope.REQUEST)
    def list_session_files_handler(self) -> ListSessionFilesHandlerProtocol:
        return cast(ListSessionFilesHandlerProtocol, self._list_session_files_handler)


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def current_user_provider() -> AsyncMock:
    provider = AsyncMock(spec=CurrentUserProviderProtocol)
    provider.get_current_user.return_value = None
    return provider


@pytest.fixture
def list_session_files_handler() -> AsyncMock:
    return AsyncMock(spec=ListSessionFilesHandlerProtocol)


@pytest.fixture
def app(
    settings: Settings,
    current_user_provider: AsyncMock,
    list_session_files_handler: AsyncMock,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(interactive_tools_routes.router)

    container = make_async_container(
        InteractiveToolsApiProvider(
            settings=settings,
            current_user_provider=current_user_provider,
            list_session_files_handler=list_session_files_handler,
        )
    )
    setup_dishka(container, app)
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_session_files_calls_handler_with_context() -> None:
    user = make_user(role=Role.USER, user_id=uuid4())
    handler = AsyncMock(spec=ListSessionFilesHandlerProtocol)
    tool_id = uuid4()

    handler.handle.return_value = ListSessionFilesResult(
        tool_id=tool_id,
        context="custom",
        files=[SessionFileInfo(name="input.txt", bytes=12)],
    )

    result = await _unwrap_dishka(interactive_tools_routes.list_session_files)(
        tool_id=tool_id,
        handler=handler,
        user=user,
        context="custom",
    )

    assert result.tool_id == tool_id
    assert result.context == "custom"
    assert result.files[0].name == "input.txt"

    handler.handle.assert_awaited_once()
    handler_kwargs = handler.handle.call_args.kwargs
    assert handler_kwargs["actor"] == user
    assert handler_kwargs["query"].tool_id == tool_id
    assert handler_kwargs["query"].context == "custom"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_session_files_defaults_context(
    client: httpx.AsyncClient,
    current_user_provider: AsyncMock,
    list_session_files_handler: AsyncMock,
) -> None:
    user = make_user(role=Role.USER)
    tool_id = uuid4()

    current_user_provider.get_current_user.return_value = user
    list_session_files_handler.handle.return_value = ListSessionFilesResult(
        tool_id=tool_id,
        context="default",
        files=[SessionFileInfo(name="input.txt", bytes=12)],
    )

    response = await client.get(f"/api/v1/tools/{tool_id}/session-files")

    assert response.status_code == 200
    assert response.json() == {
        "tool_id": str(tool_id),
        "context": "default",
        "files": [{"name": "input.txt", "bytes": 12}],
    }
    list_session_files_handler.handle.assert_awaited_once()
    query = list_session_files_handler.handle.call_args.kwargs["query"]
    assert query.tool_id == tool_id
    assert query.context == "default"
