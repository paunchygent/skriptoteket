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
from skriptoteket.domain.llm_door import AiDailyLimit, AiDailyLimitReached, ai_limit_note
from skriptoteket.domain.scripting.tool_session_messages import ToolSessionMessage
from skriptoteket.domain.scripting.tool_session_turns import ToolSessionTurn
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.llm import (
    EditorChatDoneEnabledData,
    EditorChatDoneEvent,
    EditorChatHandlerProtocol,
    EditorChatHistoryHandlerProtocol,
    EditorChatHistoryResult,
    EditorChatStreamEvent,
)
from skriptoteket.web.api.v1.editor import chat as chat_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.editor_chat_handler_harness import make_chat_handler_harness
from tests.fixtures.profile_app_continuation_support import (
    ClockStub,
    ProfileContinuationApiProvider,
    ProfileRepositoryStub,
    UserRepositoryStub,
    seed_huleedu_projection,
    signed_huleedu_headers,
)


class EditorChatHistoryApiProvider(Provider):
    def __init__(
        self,
        *,
        maintainers: ToolMaintainerRepositoryProtocol,
        handler: EditorChatHistoryHandlerProtocol,
        chat_handler: EditorChatHandlerProtocol,
    ) -> None:
        super().__init__()
        self._maintainers = maintainers
        self._handler = handler
        self._chat_handler = chat_handler

    @provide(scope=Scope.REQUEST)
    def maintainers(self) -> ToolMaintainerRepositoryProtocol:
        return self._maintainers

    @provide(scope=Scope.REQUEST)
    def editor_chat_handler(self) -> EditorChatHandlerProtocol:
        return self._chat_handler

    @provide(scope=Scope.REQUEST)
    def editor_chat_history_handler(self) -> EditorChatHistoryHandlerProtocol:
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
def maintainers() -> AsyncMock:
    repo = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    repo.is_maintainer.return_value = True
    return repo


@pytest.fixture
def handler() -> AsyncMock:
    return AsyncMock(spec=EditorChatHistoryHandlerProtocol)


@pytest.fixture
def chat_handler() -> AsyncMock:
    return AsyncMock(spec=EditorChatHandlerProtocol)


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    maintainers: AsyncMock,
    handler: AsyncMock,
    chat_handler: AsyncMock,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(chat_api.router, prefix="/api/v1/editor", tags=["editor"])

    container = make_async_container(
        ProfileContinuationApiProvider(
            settings=settings,
            clock=clock,
            users=users,
            profiles=profiles,
        ),
        EditorChatHistoryApiProvider(
            maintainers=maintainers,
            handler=handler,
            chat_handler=chat_handler,
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
async def test_editor_chat_history_requires_auth(client: httpx.AsyncClient) -> None:
    response = await client.get(f"/api/v1/editor/tools/{uuid4()}/chat")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_editor_chat_history_returns_messages(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handler: AsyncMock,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.CONTRIBUTOR, now=now)

    tool_id = uuid4()
    base_version_id = uuid4()
    turn_id = uuid4()
    correlation_id = uuid4()
    first_message_id = uuid4()
    second_message_id = uuid4()

    handler.handle.return_value = EditorChatHistoryResult(
        turns=[
            ToolSessionTurn(
                id=turn_id,
                tool_session_id=uuid4(),
                status="complete",
                failure_outcome=None,
                provider="primary",
                correlation_id=correlation_id,
                sequence=1,
                created_at=now,
                updated_at=now,
            )
        ],
        messages=[
            ToolSessionMessage(
                id=uuid4(),
                tool_session_id=uuid4(),
                turn_id=turn_id,
                message_id=first_message_id,
                role="user",
                content="Hej",
                meta=None,
                sequence=1,
                created_at=now,
            ),
            ToolSessionMessage(
                id=uuid4(),
                tool_session_id=uuid4(),
                turn_id=turn_id,
                message_id=second_message_id,
                role="assistant",
                content="Svar",
                meta=None,
                sequence=2,
                created_at=now,
            ),
        ],
        base_version_id=base_version_id,
    )

    response = await client.get(
        f"/api/v1/editor/tools/{tool_id}/chat",
        params={"limit": 2},
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
    )

    assert response.status_code == 200
    payload = response.json()
    expected_timestamp = now.isoformat().replace("+00:00", "Z")
    assert payload["base_version_id"] == str(base_version_id)
    assert payload["messages"] == [
        {
            "message_id": str(first_message_id),
            "turn_id": str(turn_id),
            "role": "user",
            "content": "Hej",
            "created_at": expected_timestamp,
            "status": "complete",
            "correlation_id": str(correlation_id),
            "failure_outcome": None,
        },
        {
            "message_id": str(second_message_id),
            "turn_id": str(turn_id),
            "role": "assistant",
            "content": "Svar",
            "created_at": expected_timestamp,
            "status": "complete",
            "correlation_id": str(correlation_id),
            "failure_outcome": None,
        },
    ]

    called_query = handler.handle.call_args.kwargs["query"]
    assert called_query.tool_id == tool_id
    assert called_query.limit == 2


async def _chat_stream_events() -> AsyncIterator[EditorChatStreamEvent]:
    yield EditorChatDoneEvent(data=EditorChatDoneEnabledData(reason="stop"))


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [Role.USER, Role.CONTRIBUTOR])
async def test_editor_chat_ai_gate_rejects_non_admin_roles(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    chat_handler: AsyncMock,
    role: Role,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=role, now=now)

    response = await client.post(
        f"/api/v1/editor/tools/{uuid4()}/chat",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
        json={"message": "Hej"},
    )

    assert response.status_code == 403
    details = response.json()["error"]["details"]
    assert set(details["required_roles"]) == {"admin", "superuser"}
    assert details["actual_role"] == role.value
    chat_handler.stream.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [Role.ADMIN, Role.SUPERUSER])
async def test_editor_chat_ai_gate_admits_admin_roles(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    chat_handler: AsyncMock,
    role: Role,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=role, now=now)
    chat_handler.stream.return_value = _chat_stream_events()

    response = await client.post(
        f"/api/v1/editor/tools/{uuid4()}/chat",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
        json={"message": "Hej"},
    )

    assert response.status_code == 200
    chat_handler.stream.assert_called_once()


@pytest.mark.asyncio
async def test_editor_chat_door_limit_answers_429_before_any_sse_event_and_frees_the_slot(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    chat_handler: AsyncMock,
    now: datetime,
) -> None:
    user = seed_huleedu_projection(users=users, profiles=profiles, role=Role.ADMIN, now=now)
    tool_id = uuid4()
    harness = make_chat_handler_harness(tool_id=tool_id, user_id=user.id)
    chat_handler.stream.side_effect = harness.handler.stream

    async def refused() -> AsyncIterator[str]:
        raise AiDailyLimitReached(limit=AiDailyLimit.USER_SHARE)
        yield ""

    async def answered() -> AsyncIterator[str]:
        yield "Svar"

    harness.provider.stream_chat.side_effect = [refused(), answered()]
    headers = signed_huleedu_headers(private_key=private_key, clock=clock)

    refused_response = await client.post(
        f"/api/v1/editor/tools/{tool_id}/chat", headers=headers, json={"message": "Hej"}
    )

    assert refused_response.status_code == 429
    assert refused_response.headers["content-type"].startswith("application/json")
    error = refused_response.json()["error"]
    assert error["code"] == "AI_DAILY_LIMIT_REACHED"
    assert error["message"] == ai_limit_note(AiDailyLimit.USER_SHARE)
    assert error["details"] == {"limit": "user_share"}
    assert harness.guard.held == set()

    second_response = await client.post(
        f"/api/v1/editor/tools/{tool_id}/chat", headers=headers, json={"message": "Hej igen"}
    )

    assert second_response.status_code == 200
    assert second_response.headers["content-type"].startswith("text/event-stream")
    assert "event: delta" in second_response.text
