from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime, timezone
from typing import Generic, TypeVar
from uuid import UUID, uuid4

import httpx
import pytest
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.application.identity.commands import LoginResult
from skriptoteket.application.scripting.commands import (
    CreateDraftVersionResult,
    SaveDraftVersionResult,
)
from skriptoteket.application.scripting.draft_locks import (
    AcquireDraftLockResult,
    ReleaseDraftLockResult,
)
from skriptoteket.application.scripting.interactive_tools import StartActionResult
from skriptoteket.config import Settings
from skriptoteket.domain.errors import ErrorCode
from skriptoteket.domain.identity.models import Role, Session, User, UserProfile
from skriptoteket.domain.scripting.models import (
    ToolVersion,
    VersionState,
    compute_content_hash,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.draft_locks import (
    AcquireDraftLockHandlerProtocol,
    ReleaseDraftLockHandlerProtocol,
)
from skriptoteket.protocols.identity import (
    CurrentUserProviderProtocol,
    LoginHandlerProtocol,
    LogoutHandlerProtocol,
    ProfileRepositoryProtocol,
    SessionRepositoryProtocol,
)
from skriptoteket.protocols.interactive_tools import StartActionHandlerProtocol
from skriptoteket.protocols.scripting import (
    CreateDraftVersionHandlerProtocol,
    SaveDraftVersionHandlerProtocol,
)
from skriptoteket.web.api.v1 import auth as api_v1_auth
from skriptoteket.web.api.v1 import editor as editor_routes
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from skriptoteket.web.routes import interactive_tools as interactive_tools_routes
from tests.fixtures.identity_fixtures import make_session, make_user

_Call = tuple[tuple[object, ...], dict[str, object]]
ResultT = TypeVar("ResultT")


class AsyncVoidStub:
    def __init__(self) -> None:
        self.calls: list[_Call] = []

    def _record(self, *args: object, **kwargs: object) -> None:
        self.calls.append((args, kwargs))

    def assert_not_called(self) -> None:
        assert not self.calls

    def assert_called_once(self) -> None:
        assert len(self.calls) == 1


class AsyncResultStub(Generic[ResultT]):
    def __init__(self) -> None:
        self.calls: list[_Call] = []
        self.result: ResultT | None = None

    def _record(self, *args: object, **kwargs: object) -> None:
        self.calls.append((args, kwargs))

    def _get_result(self, *, error: str) -> ResultT:
        assert self.result is not None, error
        return self.result

    def assert_not_called(self) -> None:
        assert not self.calls

    def assert_called_once(self) -> None:
        assert len(self.calls) == 1


class LoginHandlerStub(AsyncResultStub[LoginResult], LoginHandlerProtocol):
    async def handle(self, command: object) -> LoginResult:
        self._record(command)
        return self._get_result(error="Login result not set")


class LogoutHandlerStub(AsyncVoidStub, LogoutHandlerProtocol):
    async def handle(self, command: object) -> None:
        self._record(command)


class CurrentUserProviderStub(CurrentUserProviderProtocol):
    def __init__(self) -> None:
        self.calls: list[UUID | None] = []
        self.result: User | None = None
        self.resolver: Callable[..., Awaitable[User | None]] | None = None

    async def get_current_user(self, *, session_id: UUID | None) -> User | None:
        self.calls.append(session_id)
        if self.resolver:
            return await self.resolver(session_id=session_id)
        return self.result


class SessionRepositoryStub(SessionRepositoryProtocol):
    def __init__(self) -> None:
        self.get_by_id_result: Session | None = None
        self.get_by_id_calls: list[UUID] = []
        self.revoke_calls: list[UUID] = []
        self.create_calls: list[Session] = []
        self.count_active_result = 0
        self.sync_calls: list[dict[str, object]] = []

    async def create(self, *, session: Session) -> None:
        self.create_calls.append(session)

    async def get_by_id(self, session_id: UUID) -> Session | None:
        self.get_by_id_calls.append(session_id)
        return self.get_by_id_result

    async def revoke(self, *, session_id: UUID) -> None:
        self.revoke_calls.append(session_id)

    async def revoke_all_for_user(self, *, user_id: UUID, revoked_at: datetime) -> int:
        matching_session_ids = [
            session.id
            for session in self.create_calls
            if session.user_id == user_id
            and session.revoked_at is None
            and session.expires_at > revoked_at
        ]
        self.revoke_calls.extend(matching_session_ids)
        return len(matching_session_ids)

    async def count_active(self, *, now: datetime) -> int:
        return self.count_active_result

    async def sync_ai_settings_for_user(
        self,
        *,
        user_id: UUID,
        allow_remote_fallback: bool | None,
        inline_completion_provider: str | None,
        now: datetime,
    ) -> None:
        self.sync_calls.append(
            {
                "user_id": user_id,
                "allow_remote_fallback": allow_remote_fallback,
                "inline_completion_provider": inline_completion_provider,
                "now": now,
            }
        )


class ProfileRepositoryStub(ProfileRepositoryProtocol):
    def __init__(self) -> None:
        self.get_by_user_id_result: UserProfile | None = None
        self.get_by_user_id_calls: list[UUID] = []
        self.create_calls: list[UserProfile] = []
        self.update_calls: list[UserProfile] = []

    async def get_by_user_id(self, *, user_id: UUID) -> UserProfile | None:
        self.get_by_user_id_calls.append(user_id)
        return self.get_by_user_id_result

    async def create(self, *, profile: UserProfile) -> UserProfile:
        self.create_calls.append(profile)
        return profile

    async def update(self, *, profile: UserProfile) -> UserProfile:
        self.update_calls.append(profile)
        return profile


class StartActionHandlerStub(AsyncResultStub[StartActionResult], StartActionHandlerProtocol):
    async def handle(self, *, actor: User, command: object) -> StartActionResult:
        self._record(actor, command=command)
        return self._get_result(error="Start action result not set")


class CreateDraftHandlerStub(
    AsyncResultStub[CreateDraftVersionResult], CreateDraftVersionHandlerProtocol
):
    async def handle(self, *, actor: User, command: object) -> CreateDraftVersionResult:
        self._record(actor, command=command)
        return self._get_result(error="Create draft result not set")


class SaveDraftHandlerStub(
    AsyncResultStub[SaveDraftVersionResult], SaveDraftVersionHandlerProtocol
):
    async def handle(self, *, actor: User, command: object) -> SaveDraftVersionResult:
        self._record(actor, command=command)
        return self._get_result(error="Save draft result not set")


class AcquireDraftLockHandlerStub(
    AsyncResultStub[AcquireDraftLockResult], AcquireDraftLockHandlerProtocol
):
    async def handle(self, *, actor: User, command: object) -> AcquireDraftLockResult:
        self._record(actor, command=command)
        return self._get_result(error="Acquire draft lock result not set")


class ReleaseDraftLockHandlerStub(
    AsyncResultStub[ReleaseDraftLockResult], ReleaseDraftLockHandlerProtocol
):
    async def handle(self, *, actor: User, command: object) -> ReleaseDraftLockResult:
        self._record(actor, command=command)
        return self._get_result(error="Release draft lock result not set")


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
        login_handler: LoginHandlerStub,
        logout_handler: LogoutHandlerStub,
        current_user_provider: CurrentUserProviderStub,
        sessions: SessionRepositoryStub,
        profiles: ProfileRepositoryStub,
        start_action: StartActionHandlerStub,
        create_draft: CreateDraftHandlerStub,
        save_draft: SaveDraftHandlerStub,
        acquire_draft_lock: AcquireDraftLockHandlerStub,
        release_draft_lock: ReleaseDraftLockHandlerStub,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._clock = clock
        self._login_handler = login_handler
        self._logout_handler = logout_handler
        self._current_user_provider = current_user_provider
        self._sessions = sessions
        self._profiles = profiles
        self._start_action = start_action
        self._create_draft = create_draft
        self._save_draft = save_draft
        self._acquire_draft_lock = acquire_draft_lock
        self._release_draft_lock = release_draft_lock

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return self._settings

    @provide(scope=Scope.APP)
    def clock(self) -> ClockProtocol:
        return self._clock

    @provide(scope=Scope.REQUEST)
    def login_handler(self) -> LoginHandlerProtocol:
        return self._login_handler

    @provide(scope=Scope.REQUEST)
    def logout_handler(self) -> LogoutHandlerProtocol:
        return self._logout_handler

    @provide(scope=Scope.REQUEST)
    def current_user_provider(self) -> CurrentUserProviderProtocol:
        return self._current_user_provider

    @provide(scope=Scope.REQUEST)
    def sessions(self) -> SessionRepositoryProtocol:
        return self._sessions

    @provide(scope=Scope.REQUEST)
    def profiles(self) -> ProfileRepositoryProtocol:
        return self._profiles

    @provide(scope=Scope.REQUEST)
    def start_action_handler(self) -> StartActionHandlerProtocol:
        return self._start_action

    @provide(scope=Scope.REQUEST)
    def create_draft_handler(self) -> CreateDraftVersionHandlerProtocol:
        return self._create_draft

    @provide(scope=Scope.REQUEST)
    def save_draft_handler(self) -> SaveDraftVersionHandlerProtocol:
        return self._save_draft

    @provide(scope=Scope.REQUEST)
    def acquire_draft_lock_handler(self) -> AcquireDraftLockHandlerProtocol:
        return self._acquire_draft_lock

    @provide(scope=Scope.REQUEST)
    def release_draft_lock_handler(self) -> ReleaseDraftLockHandlerProtocol:
        return self._release_draft_lock


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def clock(now: datetime) -> ClockProtocol:
    return FixedClock(now=now)


@pytest.fixture
def login_handler() -> LoginHandlerStub:
    return LoginHandlerStub()


@pytest.fixture
def logout_handler() -> LogoutHandlerStub:
    return LogoutHandlerStub()


@pytest.fixture
def current_user_provider() -> CurrentUserProviderStub:
    return CurrentUserProviderStub()


@pytest.fixture
def sessions() -> SessionRepositoryStub:
    return SessionRepositoryStub()


@pytest.fixture
def profiles() -> ProfileRepositoryStub:
    return ProfileRepositoryStub()


@pytest.fixture
def start_action_handler() -> StartActionHandlerStub:
    return StartActionHandlerStub()


@pytest.fixture
def create_draft_handler() -> CreateDraftHandlerStub:
    return CreateDraftHandlerStub()


@pytest.fixture
def save_draft_handler() -> SaveDraftHandlerStub:
    return SaveDraftHandlerStub()


@pytest.fixture
def acquire_draft_lock_handler() -> AcquireDraftLockHandlerStub:
    return AcquireDraftLockHandlerStub()


@pytest.fixture
def release_draft_lock_handler() -> ReleaseDraftLockHandlerStub:
    return ReleaseDraftLockHandlerStub()


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockProtocol,
    login_handler: LoginHandlerStub,
    logout_handler: LogoutHandlerStub,
    current_user_provider: CurrentUserProviderStub,
    sessions: SessionRepositoryStub,
    profiles: ProfileRepositoryStub,
    start_action_handler: StartActionHandlerStub,
    create_draft_handler: CreateDraftHandlerStub,
    save_draft_handler: SaveDraftHandlerStub,
    acquire_draft_lock_handler: AcquireDraftLockHandlerStub,
    release_draft_lock_handler: ReleaseDraftLockHandlerStub,
) -> FastAPI:
    provider = ApiProvider(
        settings=settings,
        clock=clock,
        login_handler=login_handler,
        logout_handler=logout_handler,
        current_user_provider=current_user_provider,
        sessions=sessions,
        profiles=profiles,
        start_action=start_action_handler,
        create_draft=create_draft_handler,
        save_draft=save_draft_handler,
        acquire_draft_lock=acquire_draft_lock_handler,
        release_draft_lock=release_draft_lock_handler,
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
    sessions: SessionRepositoryStub,
    current_user_provider: CurrentUserProviderStub,
) -> None:
    session = make_session(
        session_id=session_id,
        user_id=user.id,
        now=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    session = session.model_copy(update={"csrf_token": csrf_token})

    sessions.get_by_id_result = session

    async def _get_current_user(*, session_id: UUID | None) -> User | None:
        if session_id == session.id:
            return user
        return None

    current_user_provider.resolver = _get_current_user


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_v1_auth_login_sets_cookie_and_returns_user_and_csrf(
    client: httpx.AsyncClient,
    settings: Settings,
    login_handler: LoginHandlerStub,
) -> None:
    settings.AI_REMOTE_PROVIDERS_ENABLED = True
    settings.LLM_COMPLETION_BASE_URL = "https://api.openai.com"
    settings.LLM_COMPLETION_MODEL = "gpt-5-nano"
    settings.LLM_COMPLETION_FALLBACK_BASE_URL = "http://localhost:8082"
    settings.LLM_COMPLETION_FALLBACK_MODEL = "Devstral-Small-2-24B"

    user = make_user(role=Role.USER)
    session_id = uuid4()
    login_handler.result = LoginResult(
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
    assert payload["ai_policy"] == {
        "remote_providers_enabled": True,
        "completion_external_available": True,
        "completion_local_available": True,
    }

    set_cookie = response.headers.get("set-cookie", "")
    assert f"{settings.SESSION_COOKIE_NAME}=" in set_cookie


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_v1_auth_me_requires_session(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 200
    payload = response.json()
    assert payload["authenticated"] is False
    assert payload["user"] is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_v1_auth_me_returns_user_when_authenticated(
    client: httpx.AsyncClient,
    settings: Settings,
    sessions: SessionRepositoryStub,
    current_user_provider: CurrentUserProviderStub,
) -> None:
    settings.AI_REMOTE_PROVIDERS_ENABLED = True
    settings.LLM_COMPLETION_BASE_URL = "https://api.openai.com"
    settings.LLM_COMPLETION_MODEL = "gpt-5-nano"
    settings.LLM_COMPLETION_FALLBACK_BASE_URL = "http://localhost:8082"
    settings.LLM_COMPLETION_FALLBACK_MODEL = "Devstral-Small-2-24B"

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
    payload = response.json()
    assert payload["authenticated"] is True
    assert payload["user"]["id"] == str(user.id)
    assert payload["ai_policy"] == {
        "remote_providers_enabled": True,
        "completion_external_available": True,
        "completion_local_available": True,
    }


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
    sessions: SessionRepositoryStub,
    current_user_provider: CurrentUserProviderStub,
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
    sessions: SessionRepositoryStub,
    current_user_provider: CurrentUserProviderStub,
    logout_handler: LogoutHandlerStub,
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

    logout_handler.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_v1_auth_logout_succeeds_with_valid_csrf_header(
    client: httpx.AsyncClient,
    settings: Settings,
    sessions: SessionRepositoryStub,
    current_user_provider: CurrentUserProviderStub,
    logout_handler: LogoutHandlerStub,
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
    logout_handler.assert_called_once()

    set_cookie = response.headers.get("set-cookie", "")
    assert f"{settings.SESSION_COOKIE_NAME}=" in set_cookie


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_v1_post_requires_csrf_token_for_start_action(
    client: httpx.AsyncClient,
    settings: Settings,
    sessions: SessionRepositoryStub,
    current_user_provider: CurrentUserProviderStub,
    start_action_handler: StartActionHandlerStub,
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

    start_action_handler.result = StartActionResult(run_id=uuid4(), state_rev=2)

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
    start_action_handler.assert_not_called()

    ok = await client.post(
        "/api/v1/start_action",
        headers={"X-CSRF-Token": csrf_token},
        json=payload,
    )
    assert ok.status_code == 200
    start_action_handler.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_v1_post_requires_csrf_token_for_editor_create_draft_version(
    client: httpx.AsyncClient,
    settings: Settings,
    sessions: SessionRepositoryStub,
    current_user_provider: CurrentUserProviderStub,
    create_draft_handler: CreateDraftHandlerStub,
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
    create_draft_handler.result = CreateDraftVersionResult(version=version)

    payload = {"entrypoint": "run_tool", "source_code": "print('hi')"}

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session_id))
    missing_csrf = await client.post(
        f"/api/v1/editor/tools/{tool_id}/draft",
        json=payload,
    )
    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["error"]["code"] == ErrorCode.FORBIDDEN.value
    create_draft_handler.assert_not_called()

    ok = await client.post(
        f"/api/v1/editor/tools/{tool_id}/draft",
        headers={"X-CSRF-Token": csrf_token},
        json=payload,
    )
    assert ok.status_code == 200
    create_draft_handler.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_v1_post_requires_csrf_token_for_editor_draft_lock_acquire(
    client: httpx.AsyncClient,
    settings: Settings,
    sessions: SessionRepositoryStub,
    current_user_provider: CurrentUserProviderStub,
    acquire_draft_lock_handler: AcquireDraftLockHandlerStub,
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
    draft_head_id = uuid4()
    acquire_draft_lock_handler.result = AcquireDraftLockResult(
        tool_id=tool_id,
        draft_head_id=draft_head_id,
        locked_by_user_id=contributor.id,
        expires_at=datetime(2025, 1, 1, 12, 10, tzinfo=timezone.utc),
        is_owner=True,
    )

    payload = {"draft_head_id": str(draft_head_id), "force": False}

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session_id))
    missing_csrf = await client.post(
        f"/api/v1/editor/tools/{tool_id}/draft-lock",
        json=payload,
    )
    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["error"]["code"] == ErrorCode.FORBIDDEN.value
    acquire_draft_lock_handler.assert_not_called()

    ok = await client.post(
        f"/api/v1/editor/tools/{tool_id}/draft-lock",
        headers={"X-CSRF-Token": csrf_token},
        json=payload,
    )
    assert ok.status_code == 200
    acquire_draft_lock_handler.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_v1_delete_requires_csrf_token_for_editor_draft_lock_release(
    client: httpx.AsyncClient,
    settings: Settings,
    sessions: SessionRepositoryStub,
    current_user_provider: CurrentUserProviderStub,
    release_draft_lock_handler: ReleaseDraftLockHandlerStub,
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
    release_draft_lock_handler.result = ReleaseDraftLockResult(tool_id=tool_id)

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session_id))
    missing_csrf = await client.delete(f"/api/v1/editor/tools/{tool_id}/draft-lock")
    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["error"]["code"] == ErrorCode.FORBIDDEN.value
    release_draft_lock_handler.assert_not_called()

    ok = await client.delete(
        f"/api/v1/editor/tools/{tool_id}/draft-lock",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert ok.status_code == 200
    release_draft_lock_handler.assert_called_once()
