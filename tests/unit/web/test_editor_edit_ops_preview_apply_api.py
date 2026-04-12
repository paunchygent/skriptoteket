from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.llm import (
    EditOpsApplyHandlerProtocol,
    EditOpsHandlerProtocol,
    EditOpsPreviewHandlerProtocol,
    EditOpsPreviewMeta,
    EditOpsPreviewResult,
)
from skriptoteket.web.api.v1.editor import edit_ops as edit_ops_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.profile_app_continuation_support import (
    ClockStub,
    ProfileContinuationApiProvider,
    ProfileRepositoryStub,
    UserRepositoryStub,
    seed_huleedu_projection,
    signed_huleedu_headers,
)


class EditorEditOpsApiProvider(Provider):
    def __init__(
        self,
        *,
        maintainers: ToolMaintainerRepositoryProtocol,
        handler: EditOpsHandlerProtocol,
        preview_handler: EditOpsPreviewHandlerProtocol,
        apply_handler: EditOpsApplyHandlerProtocol,
    ) -> None:
        super().__init__()
        self._maintainers = maintainers
        self._handler = handler
        self._preview_handler = preview_handler
        self._apply_handler = apply_handler

    @provide(scope=Scope.REQUEST)
    def maintainers(self) -> ToolMaintainerRepositoryProtocol:
        return self._maintainers

    @provide(scope=Scope.REQUEST)
    def edit_ops_handler(self) -> EditOpsHandlerProtocol:
        return self._handler

    @provide(scope=Scope.REQUEST)
    def edit_ops_preview_handler(self) -> EditOpsPreviewHandlerProtocol:
        return self._preview_handler

    @provide(scope=Scope.REQUEST)
    def edit_ops_apply_handler(self) -> EditOpsApplyHandlerProtocol:
        return self._apply_handler


@pytest.fixture
def private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def settings(private_key: rsa.RSAPrivateKey) -> Settings:
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    settings = Settings()
    settings.HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY = public_key.decode("utf-8")
    return settings


@pytest.fixture
def clock(now: datetime) -> ClockStub:
    return ClockStub(now=now)


@pytest.fixture
def users() -> UserRepositoryStub:
    return UserRepositoryStub()


@pytest.fixture
def profiles() -> ProfileRepositoryStub:
    return ProfileRepositoryStub()


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
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    maintainers: AsyncMock,
    handler: AsyncMock,
    preview_handler: AsyncMock,
    apply_handler: AsyncMock,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(edit_ops_api.router, prefix="/api/v1/editor", tags=["editor"])

    container = make_async_container(
        ProfileContinuationApiProvider(
            settings=settings,
            clock=clock,
            users=users,
            profiles=profiles,
        ),
        EditorEditOpsApiProvider(
            maintainers=maintainers,
            handler=handler,
            preview_handler=preview_handler,
            apply_handler=apply_handler,
        ),
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
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    preview_handler: AsyncMock,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.CONTRIBUTOR, now=now)

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

    response = await client.post(
        "/api/v1/editor/edit-ops/preview",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
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
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    apply_handler: AsyncMock,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.CONTRIBUTOR, now=now)

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

    response = await client.post(
        "/api/v1/editor/edit-ops/apply",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
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
