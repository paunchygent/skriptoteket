from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import cast
from unittest.mock import AsyncMock

import httpx
import pytest
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    CurrentUserProviderProtocol,
    SessionRepositoryProtocol,
)
from skriptoteket.protocols.llm import (
    InlineCompletionHandlerProtocol,
    InlineCompletionResult,
    PromptEvalMeta,
)
from skriptoteket.web.api.v1.editor import completions as completions_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.identity_fixtures import make_session, make_user


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class EditorCompletionApiProvider(Provider):
    def __init__(
        self,
        *,
        settings: Settings,
        clock: ClockProtocol,
        current_user_provider: AsyncMock,
        sessions: AsyncMock,
        handler: AsyncMock,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._clock = clock
        self._current_user_provider = current_user_provider
        self._sessions = sessions
        self._handler = handler

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return self._settings

    @provide(scope=Scope.APP)
    def clock(self) -> ClockProtocol:
        return self._clock

    @provide(scope=Scope.REQUEST)
    def current_user_provider(self) -> CurrentUserProviderProtocol:
        return cast(CurrentUserProviderProtocol, self._current_user_provider)

    @provide(scope=Scope.REQUEST)
    def sessions(self) -> SessionRepositoryProtocol:
        return cast(SessionRepositoryProtocol, self._sessions)

    @provide(scope=Scope.REQUEST)
    def inline_completion_handler(self) -> InlineCompletionHandlerProtocol:
        return cast(InlineCompletionHandlerProtocol, self._handler)


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def clock(now: datetime) -> ClockProtocol:
    return FixedClock(now=now)


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
def handler() -> AsyncMock:
    return AsyncMock(spec=InlineCompletionHandlerProtocol)


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockProtocol,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    handler: AsyncMock,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(completions_api.router, prefix="/api/v1/editor", tags=["editor"])

    container = make_async_container(
        EditorCompletionApiProvider(
            settings=settings,
            clock=clock,
            current_user_provider=current_user_provider,
            sessions=sessions,
            handler=handler,
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


@pytest.mark.asyncio
async def test_inline_completion_requires_auth(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/editor/completions",
        json={"prefix": "def x():\n    ", "suffix": ""},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_inline_completion_requires_csrf(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    now: datetime,
) -> None:
    user = make_user(role=Role.CONTRIBUTOR)
    session = make_session(user_id=user.id, now=now)

    current_user_provider.get_current_user.return_value = user
    sessions.get_by_id.return_value = session

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        "/api/v1/editor/completions",
        json={"prefix": "def x():\n    ", "suffix": ""},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_inline_completion_success(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    handler: AsyncMock,
    now: datetime,
) -> None:
    user = make_user(role=Role.CONTRIBUTOR)
    session = make_session(user_id=user.id, now=now)

    current_user_provider.get_current_user.return_value = user
    sessions.get_by_id.return_value = session
    handler.handle.return_value = InlineCompletionResult(completion="pass\n", enabled=True)

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        "/api/v1/editor/completions",
        headers={"X-CSRF-Token": session.csrf_token},
        json={"prefix": "def x():\n    ", "suffix": ""},
    )

    assert response.status_code == 200
    assert response.json() == {"completion": "pass\n", "enabled": True}

    handler.handle.assert_awaited_once()


@pytest.mark.asyncio
async def test_inline_completion_passes_ai_settings_to_handler(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    handler: AsyncMock,
    now: datetime,
) -> None:
    user = make_user(role=Role.CONTRIBUTOR)
    session = make_session(
        user_id=user.id,
        now=now,
        allow_remote_fallback=True,
        inline_completion_provider="external",
    )

    current_user_provider.get_current_user.return_value = user
    sessions.get_by_id.return_value = session
    handler.handle.return_value = InlineCompletionResult(completion="pass\n", enabled=True)

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        "/api/v1/editor/completions",
        headers={"X-CSRF-Token": session.csrf_token},
        json={
            "prefix": "def x():\n    ",
            "suffix": "",
        },
    )

    assert response.status_code == 200
    handler.handle.assert_awaited_once()
    called = handler.handle.call_args.kwargs["command"]
    assert called.allow_remote_fallback is True
    assert called.inline_completion_provider == "external"


@pytest.mark.asyncio
async def test_inline_completion_includes_notice_fields_when_present(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    handler: AsyncMock,
    now: datetime,
) -> None:
    user = make_user(role=Role.CONTRIBUTOR)
    session = make_session(user_id=user.id, now=now)

    current_user_provider.get_current_user.return_value = user
    sessions.get_by_id.return_value = session
    handler.handle.return_value = InlineCompletionResult(
        completion="",
        enabled=True,
        notice_code="remote_fallback_required",
        notice_variant="warning",
        notice_message="Enable external AI",
    )

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        "/api/v1/editor/completions",
        headers={"X-CSRF-Token": session.csrf_token},
        json={"prefix": "def x():\n    ", "suffix": ""},
    )

    assert response.status_code == 200
    assert response.json() == {
        "completion": "",
        "enabled": True,
        "notice_code": "remote_fallback_required",
        "notice_variant": "warning",
        "notice_message": "Enable external AI",
    }


@pytest.mark.asyncio
async def test_inline_completion_eval_headers_require_admin(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    now: datetime,
) -> None:
    user = make_user(role=Role.CONTRIBUTOR)
    session = make_session(user_id=user.id, now=now)

    current_user_provider.get_current_user.return_value = user
    sessions.get_by_id.return_value = session

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        "/api/v1/editor/completions",
        headers={
            "X-CSRF-Token": session.csrf_token,
            "X-Skriptoteket-Eval": "1",
        },
        json={"prefix": "def x():\n    ", "suffix": ""},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_inline_completion_includes_eval_headers_for_superuser(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    handler: AsyncMock,
    now: datetime,
) -> None:
    user = make_user(role=Role.SUPERUSER)
    session = make_session(user_id=user.id, now=now)

    current_user_provider.get_current_user.return_value = user
    sessions.get_by_id.return_value = session
    handler.handle.return_value = InlineCompletionResult(
        completion="pass\n",
        enabled=True,
        eval_meta=PromptEvalMeta(
            template_id="inline_completion_v1",
            outcome="ok",
            system_prompt_chars=123,
            prefix_chars=12,
            suffix_chars=0,
            raw_chars=42,
            normalized_chars=4,
            prefix_overlap_chars=12,
            suffix_overlap_chars=0,
            prepare_ms=5,
            provider_ms=321,
            normalize_ms=2,
            total_ms=330,
        ),
    )

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        "/api/v1/editor/completions",
        headers={
            "X-CSRF-Token": session.csrf_token,
            "X-Skriptoteket-Eval": "1",
        },
        json={"prefix": "def x():\n    ", "suffix": ""},
    )

    assert response.status_code == 200
    assert response.headers["X-Skriptoteket-Eval-Template-Id"] == "inline_completion_v1"
    assert response.headers["X-Skriptoteket-Eval-Outcome"] == "ok"
    assert response.headers["X-Skriptoteket-Eval-System-Prompt-Chars"] == "123"
    assert response.headers["X-Skriptoteket-Eval-Prefix-Chars"] == "12"
    assert response.headers["X-Skriptoteket-Eval-Suffix-Chars"] == "0"
    assert response.headers["X-Skriptoteket-Eval-Raw-Chars"] == "42"
    assert response.headers["X-Skriptoteket-Eval-Normalized-Chars"] == "4"
    assert response.headers["X-Skriptoteket-Eval-Prefix-Overlap-Chars"] == "12"
    assert response.headers["X-Skriptoteket-Eval-Suffix-Overlap-Chars"] == "0"
    assert response.headers["X-Skriptoteket-Eval-Prepare-Ms"] == "5"
    assert response.headers["X-Skriptoteket-Eval-Provider-Ms"] == "321"
    assert response.headers["X-Skriptoteket-Eval-Normalize-Ms"] == "2"
    assert response.headers["X-Skriptoteket-Eval-Total-Ms"] == "330"


@pytest.mark.asyncio
async def test_inline_completion_eval_headers_denied_in_production(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    now: datetime,
) -> None:
    settings.ENVIRONMENT = "production"

    user = make_user(role=Role.SUPERUSER)
    session = make_session(user_id=user.id, now=now)

    current_user_provider.get_current_user.return_value = user
    sessions.get_by_id.return_value = session

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        "/api/v1/editor/completions",
        headers={
            "X-CSRF-Token": session.csrf_token,
            "X-Skriptoteket-Eval": "1",
        },
        json={"prefix": "def x():\n    ", "suffix": ""},
    )

    assert response.status_code == 403
