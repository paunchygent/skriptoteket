from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import cast
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import httpx
import pytest
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from skriptoteket.application.identity.commands import LoginResult
from skriptoteket.application.scripting.commands import CreateDraftVersionResult
from skriptoteket.application.scripting.interactive_tools import StartActionResult
from skriptoteket.config import Settings
from skriptoteket.domain.errors import ErrorCode
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.scripting.models import (
    ToolVersion,
    VersionState,
    compute_content_hash,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    CurrentUserProviderProtocol,
    LoginHandlerProtocol,
    LogoutHandlerProtocol,
    SessionRepositoryProtocol,
)
from skriptoteket.protocols.interactive_tools import StartActionHandlerProtocol
from skriptoteket.protocols.scripting import (
    CreateDraftVersionHandlerProtocol,
    SaveDraftVersionHandlerProtocol,
)
from skriptoteket.web.api.v1 import auth as api_v1_auth
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from skriptoteket.web.routes import editor as editor_routes
from skriptoteket.web.routes import interactive_tools as interactive_tools_routes
from tests.fixtures.identity_fixtures import make_session, make_user


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


def _make_tool_version(*, tool_id: UUID, created_by_user_id: UUID) -> ToolVersion:
    entrypoint = "run_tool"
    source_code = "print('hello')\n"
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return ToolVersion(
        id=uuid4(),
        tool_id=tool_id,
        version_number=1,
        state=VersionState.DRAFT,
        source_code=source_code,
        entrypoint=entrypoint,
        content_hash=compute_content_hash(entrypoint=entrypoint, source_code=source_code),
        derived_from_version_id=None,
        created_by_user_id=created_by_user_id,
        created_at=now,
        submitted_for_review_by_user_id=None,
        submitted_for_review_at=None,
        reviewed_by_user_id=None,
        reviewed_at=None,
        published_by_user_id=None,
        published_at=None,
        change_summary=None,
        review_note=None,
    )


class ApiProvider(Provider):
    def __init__(
        self,
        *,
        settings: Settings,
        clock: ClockProtocol,
        login_handler: AsyncMock,
        logout_handler: AsyncMock,
        current_user_provider: AsyncMock,
        sessions: AsyncMock,
        start_action: AsyncMock,
        create_draft: AsyncMock,
        save_draft: AsyncMock,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._clock = clock
        self._login_handler = login_handler
        self._logout_handler = logout_handler
        self._current_user_provider = current_user_provider
        self._sessions = sessions
        self._start_action = start_action
        self._create_draft = create_draft
        self._save_draft = save_draft

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return self._settings

    @provide(scope=Scope.APP)
    def clock(self) -> ClockProtocol:
        return self._clock

    @provide(scope=Scope.REQUEST)
    def login_handler(self) -> LoginHandlerProtocol:
        return cast(LoginHandlerProtocol, self._login_handler)

    @provide(scope=Scope.REQUEST)
    def logout_handler(self) -> LogoutHandlerProtocol:
        return cast(LogoutHandlerProtocol, self._logout_handler)

    @provide(scope=Scope.REQUEST)
    def current_user_provider(self) -> CurrentUserProviderProtocol:
        return cast(CurrentUserProviderProtocol, self._current_user_provider)

    @provide(scope=Scope.REQUEST)
    def sessions(self) -> SessionRepositoryProtocol:
        return cast(SessionRepositoryProtocol, self._sessions)

    @provide(scope=Scope.REQUEST)
    def start_action_handler(self) -> StartActionHandlerProtocol:
        return cast(StartActionHandlerProtocol, self._start_action)

    @provide(scope=Scope.REQUEST)
    def create_draft_handler(self) -> CreateDraftVersionHandlerProtocol:
        return cast(CreateDraftVersionHandlerProtocol, self._create_draft)

    @provide(scope=Scope.REQUEST)
    def save_draft_handler(self) -> SaveDraftVersionHandlerProtocol:
        return cast(SaveDraftVersionHandlerProtocol, self._save_draft)


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def clock(now: datetime) -> ClockProtocol:
    return FixedClock(now=now)


@pytest.fixture
def login_handler() -> AsyncMock:
    return AsyncMock(spec=LoginHandlerProtocol)


@pytest.fixture
def logout_handler() -> AsyncMock:
    return AsyncMock(spec=LogoutHandlerProtocol)


@pytest.fixture
def current_user_provider() -> AsyncMock:
    provider = AsyncMock(spec=CurrentUserProviderProtocol)
    provider.get_current_user.return_value = None
    return provider


@pytest.fixture
def sessions() -> AsyncMock:
    repo = AsyncMock(spec=SessionRepositoryProtocol)
    repo.get_by_id.return_value = None
    return repo


@pytest.fixture
def start_action_handler() -> AsyncMock:
    return AsyncMock(spec=StartActionHandlerProtocol)


@pytest.fixture
def create_draft_handler() -> AsyncMock:
    return AsyncMock(spec=CreateDraftVersionHandlerProtocol)


@pytest.fixture
def save_draft_handler() -> AsyncMock:
    return AsyncMock(spec=SaveDraftVersionHandlerProtocol)


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockProtocol,
    login_handler: AsyncMock,
    logout_handler: AsyncMock,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    start_action_handler: AsyncMock,
    create_draft_handler: AsyncMock,
    save_draft_handler: AsyncMock,
) -> FastAPI:
    provider = ApiProvider(
        settings=settings,
        clock=clock,
        login_handler=login_handler,
        logout_handler=logout_handler,
        current_user_provider=current_user_provider,
        sessions=sessions,
        start_action=start_action_handler,
        create_draft=create_draft_handler,
        save_draft=save_draft_handler,
    )
    container = make_async_container(provider)

    app = FastAPI(title="Test App", version="0.0.0")
    app.middleware("http")(error_handler_middleware)
    setup_dishka(container, app)

    app.include_router(api_v1_auth.router)
    app.include_router(interactive_tools_routes.router)
    app.include_router(editor_routes.router)

    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


def _setup_valid_auth(
    *,
    user: User,
    session_id: UUID,
    csrf_token: str,
    sessions: AsyncMock,
    current_user_provider: AsyncMock,
) -> None:
    session = make_session(
        session_id=session_id,
        user_id=user.id,
        now=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    session = session.model_copy(update={"csrf_token": csrf_token})

    sessions.get_by_id.return_value = session

    async def _get_current_user(*, session_id: UUID | None) -> User | None:
        if session_id == session.id:
            return user
        return None

    current_user_provider.get_current_user.side_effect = _get_current_user


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_v1_auth_login_sets_cookie_and_returns_user_and_csrf(
    client: httpx.AsyncClient,
    settings: Settings,
    login_handler: AsyncMock,
) -> None:
    user = make_user(role=Role.USER)
    session_id = uuid4()
    login_handler.handle.return_value = LoginResult(
        session_id=session_id,
        csrf_token="csrf-token",
        user=user,
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "pw"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["id"] == str(user.id)
    assert payload["csrf_token"] == "csrf-token"

    set_cookie = response.headers.get("set-cookie", "")
    assert f"{settings.SESSION_COOKIE_NAME}=" in set_cookie


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_v1_auth_me_requires_session(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == ErrorCode.UNAUTHORIZED.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_v1_auth_me_returns_user_when_authenticated(
    client: httpx.AsyncClient,
    settings: Settings,
    sessions: AsyncMock,
    current_user_provider: AsyncMock,
) -> None:
    user = make_user(role=Role.ADMIN)
    session_id = uuid4()
    _setup_valid_auth(
        user=user,
        session_id=session_id,
        csrf_token="csrf-token",
        sessions=sessions,
        current_user_provider=current_user_provider,
    )

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session_id))
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["user"]["id"] == str(user.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_v1_auth_csrf_requires_session(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/auth/csrf")
    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == ErrorCode.UNAUTHORIZED.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_v1_auth_csrf_returns_token_when_authenticated(
    client: httpx.AsyncClient,
    settings: Settings,
    sessions: AsyncMock,
    current_user_provider: AsyncMock,
) -> None:
    user = make_user(role=Role.USER)
    session_id = uuid4()
    csrf_token = "csrf-token"
    _setup_valid_auth(
        user=user,
        session_id=session_id,
        csrf_token=csrf_token,
        sessions=sessions,
        current_user_provider=current_user_provider,
    )

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session_id))
    response = await client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    assert response.json()["csrf_token"] == csrf_token


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_v1_auth_logout_requires_csrf_header_when_session_exists(
    client: httpx.AsyncClient,
    settings: Settings,
    sessions: AsyncMock,
    current_user_provider: AsyncMock,
    logout_handler: AsyncMock,
) -> None:
    user = make_user(role=Role.USER)
    session_id = uuid4()
    _setup_valid_auth(
        user=user,
        session_id=session_id,
        csrf_token="csrf-token",
        sessions=sessions,
        current_user_provider=current_user_provider,
    )

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session_id))
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == ErrorCode.FORBIDDEN.value

    logout_handler.handle.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_v1_auth_logout_succeeds_with_valid_csrf_header(
    client: httpx.AsyncClient,
    settings: Settings,
    sessions: AsyncMock,
    current_user_provider: AsyncMock,
    logout_handler: AsyncMock,
) -> None:
    user = make_user(role=Role.USER)
    session_id = uuid4()
    csrf_token = "csrf-token"
    _setup_valid_auth(
        user=user,
        session_id=session_id,
        csrf_token=csrf_token,
        sessions=sessions,
        current_user_provider=current_user_provider,
    )

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session_id))
    response = await client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 204
    logout_handler.handle.assert_awaited_once()

    set_cookie = response.headers.get("set-cookie", "")
    assert f"{settings.SESSION_COOKIE_NAME}=" in set_cookie


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_v1_post_requires_csrf_token_for_start_action(
    client: httpx.AsyncClient,
    settings: Settings,
    sessions: AsyncMock,
    current_user_provider: AsyncMock,
    start_action_handler: AsyncMock,
) -> None:
    user = make_user(role=Role.USER)
    session_id = uuid4()
    csrf_token = "csrf-token"
    _setup_valid_auth(
        user=user,
        session_id=session_id,
        csrf_token=csrf_token,
        sessions=sessions,
        current_user_provider=current_user_provider,
    )

    start_action_handler.handle.return_value = StartActionResult(run_id=uuid4(), state_rev=2)

    payload = {
        "tool_id": str(uuid4()),
        "context": "default",
        "action_id": "go",
        "input": {},
        "expected_state_rev": 1,
    }

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session_id))
    missing_csrf = await client.post(
        "/api/v1/start_action",
        json=payload,
    )
    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["error"]["code"] == ErrorCode.FORBIDDEN.value
    start_action_handler.handle.assert_not_awaited()

    ok = await client.post(
        "/api/v1/start_action",
        headers={"X-CSRF-Token": csrf_token},
        json=payload,
    )
    assert ok.status_code == 200
    start_action_handler.handle.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_v1_post_requires_csrf_token_for_editor_create_draft_version(
    client: httpx.AsyncClient,
    settings: Settings,
    sessions: AsyncMock,
    current_user_provider: AsyncMock,
    create_draft_handler: AsyncMock,
) -> None:
    contributor = make_user(role=Role.CONTRIBUTOR)
    session_id = uuid4()
    csrf_token = "csrf-token"
    _setup_valid_auth(
        user=contributor,
        session_id=session_id,
        csrf_token=csrf_token,
        sessions=sessions,
        current_user_provider=current_user_provider,
    )

    tool_id = uuid4()
    version = _make_tool_version(tool_id=tool_id, created_by_user_id=contributor.id)
    create_draft_handler.handle.return_value = CreateDraftVersionResult(version=version)

    payload = {"entrypoint": "run_tool", "source_code": "print('hi')"}

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session_id))
    missing_csrf = await client.post(
        f"/api/v1/editor/tools/{tool_id}/draft",
        json=payload,
    )
    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["error"]["code"] == ErrorCode.FORBIDDEN.value
    create_draft_handler.handle.assert_not_awaited()

    ok = await client.post(
        f"/api/v1/editor/tools/{tool_id}/draft",
        headers={"X-CSRF-Token": csrf_token},
        json=payload,
    )
    assert ok.status_code == 200
    create_draft_handler.handle.assert_awaited_once()
