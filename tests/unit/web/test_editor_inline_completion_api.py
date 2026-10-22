"""Inline-completion route tests.

Purpose:
    Verify editor inline-completion API auth, CSRF, response mapping, and
    the 429 daily-limit mapping.

Relationships:
    - Exercises the FastAPI route module directly with Dishka protocol stubs.
    - Freezes that the command carries only prefix, suffix and active file.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from unittest.mock import AsyncMock

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.llm_door import AiDailyLimit
from skriptoteket.protocols.llm import (
    InlineCompletionHandlerProtocol,
    InlineCompletionResult,
    PromptEvalMeta,
)
from skriptoteket.web.api.v1.editor import completions as completions_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.profile_app_continuation_support import (
    ClockStub,
    ProfileContinuationApiProvider,
    ProfileRepositoryStub,
    UserRepositoryStub,
    seed_huleedu_projection,
    signed_huleedu_headers,
)


class EditorCompletionApiProvider(Provider):
    def __init__(
        self,
        *,
        handler: InlineCompletionHandlerProtocol,
    ) -> None:
        super().__init__()
        self._handler = handler

    @provide(scope=Scope.REQUEST)
    def inline_completion_handler(self) -> InlineCompletionHandlerProtocol:
        return self._handler


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
def handler() -> AsyncMock:
    return AsyncMock(spec=InlineCompletionHandlerProtocol)


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handler: AsyncMock,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(completions_api.router, prefix="/api/v1/editor", tags=["editor"])

    container = make_async_container(
        ProfileContinuationApiProvider(
            settings=settings,
            clock=clock,
            users=users,
            profiles=profiles,
        ),
        EditorCompletionApiProvider(
            handler=handler,
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


@pytest.mark.asyncio
async def test_inline_completion_requires_auth(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/editor/completions",
        json={"prefix": "def x():\n    ", "suffix": ""},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_inline_completion_rejects_stale_csrf_without_signed_context(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/editor/completions",
        headers={"X-CSRF-Token": "stale-local-csrf"},
        json={"prefix": "def x():\n    ", "suffix": ""},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_inline_completion_success(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handler: AsyncMock,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.ADMIN, now=now)
    handler.handle.return_value = InlineCompletionResult(completion="pass\n", enabled=True)

    response = await client.post(
        "/api/v1/editor/completions",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
        json={"prefix": "def x():\n    ", "suffix": ""},
    )

    assert response.status_code == 200
    assert response.json() == {"completion": "pass\n", "enabled": True}

    handler.handle.assert_awaited_once()


@pytest.mark.asyncio
async def test_inline_completion_includes_replace_suffix_chars(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handler: AsyncMock,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.ADMIN, now=now)
    handler.handle.return_value = InlineCompletionResult(
        completion="rn",
        enabled=True,
        replace_suffix_chars=2,
    )

    response = await client.post(
        "/api/v1/editor/completions",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
        json={"prefix": "retu", "suffix": "rn"},
    )

    assert response.status_code == 200
    assert response.json() == {"completion": "rn", "enabled": True, "replace_suffix_chars": 2}


@pytest.mark.asyncio
async def test_inline_completion_passes_only_the_editor_text_to_handler(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handler: AsyncMock,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.ADMIN, now=now)
    handler.handle.return_value = InlineCompletionResult(completion="pass\n", enabled=True)

    response = await client.post(
        "/api/v1/editor/completions",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
        json={"prefix": "def x():\n    ", "suffix": "", "active_file": "tool.py"},
    )

    assert response.status_code == 200
    command = handler.handle.call_args.kwargs["command"]
    assert command.model_dump() == {
        "prefix": "def x():\n    ",
        "suffix": "",
        "active_file": "tool.py",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("limit", "message"),
    [
        (
            AiDailyLimit.USER_SHARE,
            "Du har nått din gräns för AI-hjälp i dag. Försök igen i morgon.",
        ),
        (AiDailyLimit.POOL, "Appens AI-hjälp har nått dagens gräns. Försök igen i morgon."),
    ],
)
async def test_inline_completion_daily_limit_answers_429(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handler: AsyncMock,
    now: datetime,
    limit: AiDailyLimit,
    message: str,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.ADMIN, now=now)
    handler.handle.side_effect = DomainError(
        code=ErrorCode.AI_DAILY_LIMIT_REACHED,
        message=message,
        details={"limit": limit.value},
    )

    response = await client.post(
        "/api/v1/editor/completions",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
        json={"prefix": "def x():\n    ", "suffix": ""},
    )

    assert response.status_code == 429
    error = response.json()["error"]
    assert error["code"] == "AI_DAILY_LIMIT_REACHED"
    assert error["message"] == message
    assert error["details"] == {"limit": limit.value}


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [Role.USER, Role.CONTRIBUTOR])
async def test_inline_completion_ai_gate_rejects_non_admin_roles(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handler: AsyncMock,
    role: Role,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=role, now=now)

    response = await client.post(
        "/api/v1/editor/completions",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
        json={"prefix": "def x():\n    ", "suffix": ""},
    )

    assert response.status_code == 403
    details = response.json()["error"]["details"]
    assert set(details["required_roles"]) == {"admin", "superuser"}
    assert details["actual_role"] == role.value
    handler.handle.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [Role.ADMIN, Role.SUPERUSER])
async def test_inline_completion_ai_gate_admits_admin_roles(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handler: AsyncMock,
    role: Role,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=role, now=now)
    handler.handle.return_value = InlineCompletionResult(completion="pass\n", enabled=True)

    response = await client.post(
        "/api/v1/editor/completions",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
        json={"prefix": "def x():\n    ", "suffix": ""},
    )

    assert response.status_code == 200
    handler.handle.assert_awaited_once()


@pytest.mark.asyncio
async def test_inline_completion_includes_eval_headers_for_superuser(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handler: AsyncMock,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.SUPERUSER, now=now)
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

    headers = signed_huleedu_headers(private_key=private_key, clock=clock)
    headers["X-Skriptoteket-Eval"] = "1"
    response = await client.post(
        "/api/v1/editor/completions",
        headers=headers,
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
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    now: datetime,
) -> None:
    settings.ENVIRONMENT = "production"

    seed_huleedu_projection(users=users, profiles=profiles, role=Role.SUPERUSER, now=now)

    headers = signed_huleedu_headers(private_key=private_key, clock=clock)
    headers["X-Skriptoteket-Eval"] = "1"
    response = await client.post(
        "/api/v1/editor/completions",
        headers=headers,
        json={"prefix": "def x():\n    ", "suffix": ""},
    )

    assert response.status_code == 403
