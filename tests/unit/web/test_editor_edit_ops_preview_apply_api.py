from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    CurrentUserProviderProtocol,
    SessionRepositoryProtocol,
)
from skriptoteket.protocols.llm import (
    EditOpsApplyHandlerProtocol,
    EditOpsHandlerProtocol,
    EditOpsPreviewHandlerProtocol,
    EditOpsPreviewMeta,
    EditOpsPreviewResult,
)
from skriptoteket.web.api.v1.editor import edit_ops as edit_ops_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.identity_fixtures import make_session, make_user


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class EditorEditOpsApiProvider(Provider):
    def __init__(
        self,
        *,
        settings: Settings,
        clock: ClockProtocol,
        current_user_provider: AsyncMock,
        sessions: AsyncMock,
        maintainers: AsyncMock,
        handler: AsyncMock,
        preview_handler: AsyncMock,
        apply_handler: AsyncMock,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._clock = clock
        self._current_user_provider = current_user_provider
        self._sessions = sessions
        self._maintainers = maintainers
        self._handler = handler
        self._preview_handler = preview_handler
        self._apply_handler = apply_handler

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
    def maintainers(self) -> ToolMaintainerRepositoryProtocol:
        return cast(ToolMaintainerRepositoryProtocol, self._maintainers)

    @provide(scope=Scope.REQUEST)
    def edit_ops_handler(self) -> EditOpsHandlerProtocol:
        return cast(EditOpsHandlerProtocol, self._handler)

    @provide(scope=Scope.REQUEST)
    def edit_ops_preview_handler(self) -> EditOpsPreviewHandlerProtocol:
        return cast(EditOpsPreviewHandlerProtocol, self._preview_handler)

    @provide(scope=Scope.REQUEST)
    def edit_ops_apply_handler(self) -> EditOpsApplyHandlerProtocol:
        return cast(EditOpsApplyHandlerProtocol, self._apply_handler)


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
def maintainers() -> AsyncMock:
    repo = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    repo.is_maintainer.return_value = True
    return repo


@pytest.fixture
def handler() -> AsyncMock:
    return AsyncMock(spec=EditOpsHandlerProtocol)


@pytest.fixture
def preview_handler() -> AsyncMock:
    return AsyncMock(spec=EditOpsPreviewHandlerProtocol)


@pytest.fixture
def apply_handler() -> AsyncMock:
    return AsyncMock(spec=EditOpsApplyHandlerProtocol)


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockProtocol,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    maintainers: AsyncMock,
    handler: AsyncMock,
    preview_handler: AsyncMock,
    apply_handler: AsyncMock,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(edit_ops_api.router, prefix="/api/v1/editor", tags=["editor"])

    container = make_async_container(
        EditorEditOpsApiProvider(
            settings=settings,
            clock=clock,
            current_user_provider=current_user_provider,
            sessions=sessions,
            maintainers=maintainers,
            handler=handler,
            preview_handler=preview_handler,
            apply_handler=apply_handler,
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


def _virtual_files(tool_py: str) -> dict[str, str]:
    return {
        "tool.py": tool_py,
        "entrypoint.txt": "run_tool\n",
        "settings_schema.json": "{}",
        "input_schema.json": "{}",
        "usage_instructions.md": "",
    }


@pytest.mark.asyncio
async def test_edit_ops_preview_maps_web_ops_to_domain_command(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    preview_handler: AsyncMock,
    now: datetime,
) -> None:
    user = make_user(role=Role.CONTRIBUTOR)
    session = make_session(user_id=user.id, now=now)
    current_user_provider.get_current_user.return_value = user
    sessions.get_by_id.return_value = session

    tool_id = uuid4()
    preview_handler.handle.return_value = EditOpsPreviewResult(
        ok=True,
        after_virtual_files=_virtual_files("print('preview')\n"),
        errors=[],
        error_details=[],
        meta=EditOpsPreviewMeta(
            base_hash="sha256:base",
            patch_id="sha256:patch",
            requires_confirmation=False,
            fuzz_level_used=0,
            max_offset=0,
            normalizations_applied=[],
            applied_cleanly=True,
        ),
    )

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        "/api/v1/editor/edit-ops/preview",
        headers={"X-CSRF-Token": session.csrf_token},
        json={
            "tool_id": str(tool_id),
            "active_file": "tool.py",
            "virtual_files": _virtual_files("print('hi')\n"),
            "ops": [
                {
                    "op": "patch",
                    "target_file": "tool.py",
                    "patch_lines": [
                        "@@ -1 +1 @@",
                        "-print('hi')",
                        "+print('preview')",
                    ],
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True

    called = preview_handler.handle.call_args.kwargs["command"]
    assert called.ops[0].op == "patch"
    assert called.ops[0].target_file == "tool.py"


@pytest.mark.asyncio
async def test_edit_ops_apply_maps_web_ops_and_includes_gating_tokens(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    apply_handler: AsyncMock,
    now: datetime,
) -> None:
    user = make_user(role=Role.CONTRIBUTOR)
    session = make_session(user_id=user.id, now=now)
    current_user_provider.get_current_user.return_value = user
    sessions.get_by_id.return_value = session

    tool_id = uuid4()
    apply_handler.handle.return_value = EditOpsPreviewResult(
        ok=True,
        after_virtual_files=_virtual_files("print('applied')\n"),
        errors=[],
        error_details=[],
        meta=EditOpsPreviewMeta(
            base_hash="sha256:base",
            patch_id="sha256:patch",
            requires_confirmation=False,
            fuzz_level_used=0,
            max_offset=0,
            normalizations_applied=[],
            applied_cleanly=True,
        ),
    )

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        "/api/v1/editor/edit-ops/apply",
        headers={"X-CSRF-Token": session.csrf_token},
        json={
            "tool_id": str(tool_id),
            "active_file": "tool.py",
            "virtual_files": _virtual_files("print('hi')\n"),
            "ops": [
                {
                    "op": "patch",
                    "target_file": "tool.py",
                    "patch_lines": [
                        "@@ -1 +1 @@",
                        "-print('hi')",
                        "+print('applied')",
                    ],
                }
            ],
            "base_hash": "sha256:base",
            "patch_id": "sha256:patch",
        },
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True

    called = apply_handler.handle.call_args.kwargs["command"]
    assert called.base_hash == "sha256:base"
    assert called.patch_id == "sha256:patch"
    assert called.ops[0].op == "patch"
