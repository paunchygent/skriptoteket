from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from skriptoteket.application.catalog.queries import ListToolsForAdminResult
from skriptoteket.domain.catalog.models import Tool
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider, Role, Session, User
from skriptoteket.protocols.catalog import (
    DepublishToolHandlerProtocol,
    ListToolsForAdminHandlerProtocol,
    PublishToolHandlerProtocol,
)
from skriptoteket.web.pages import admin_tools

type _AsyncHandler = Callable[..., Awaitable[Response]]


@runtime_checkable
class _DishkaWrappedHandler(Protocol):
    __dishka_orig_func__: _AsyncHandler

    def __call__(self, *args: object, **kwargs: object) -> Awaitable[Response]: ...


@runtime_checkable
class _TemplateProtocol(Protocol):
    name: str


@runtime_checkable
class _TemplateResponseProtocol(Protocol):
    status_code: int
    template: _TemplateProtocol
    context: dict[str, object]


def _original(fn: _AsyncHandler | _DishkaWrappedHandler) -> _AsyncHandler:
    return fn.__dishka_orig_func__ if isinstance(fn, _DishkaWrappedHandler) else fn


def _request(*, path: str, method: str = "GET") -> Request:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
        "query_string": b"",
    }
    return Request(scope)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _user(*, role: Role) -> User:
    now = _now()
    return User(
        id=uuid.uuid4(),
        email=f"{role.value}@example.com",
        role=role,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )


def _session(*, user_id: uuid.UUID) -> Session:
    now = _now()
    return Session(
        id=uuid.uuid4(),
        user_id=user_id,
        csrf_token="csrf",
        created_at=now,
        expires_at=now + timedelta(days=1),
    )


def _tool(*, title: str = "Tool") -> Tool:
    now = _now()
    return Tool(
        id=uuid.uuid4(),
        slug="tool",
        title=title,
        summary="Summary",
        is_published=False,
        active_version_id=None,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_tools_renders_admin_tools_template_with_csrf_and_tools() -> None:
    handler = AsyncMock(spec=ListToolsForAdminHandlerProtocol)
    tool = _tool(title="Example")
    handler.handle.return_value = ListToolsForAdminResult(tools=[tool])

    user = _user(role=Role.ADMIN)
    session = _session(user_id=user.id)
    request = _request(path="/admin/tools")

    response = await _original(admin_tools.list_tools)(
        request=request,
        handler=handler,
        user=user,
        session=session,
        updated="1",
    )

    assert isinstance(response, _TemplateResponseProtocol)
    assert response.status_code == 200
    assert response.template.name == "admin_tools.html"
    assert response.context["csrf_token"] == session.csrf_token
    assert response.context["updated"] == "1"
    assert response.context["error"] is None
    assert response.context["tools"] == [tool]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (ErrorCode.NOT_FOUND, 404),
        (ErrorCode.FORBIDDEN, 403),
        (ErrorCode.CONFLICT, 409),
        (ErrorCode.VALIDATION_ERROR, 400),
        (ErrorCode.INTERNAL_ERROR, 500),
    ],
)
def test_status_code_for_error_maps_domain_codes(code: ErrorCode, expected: int) -> None:
    exc = DomainError(code=code, message="boom")
    assert admin_tools._status_code_for_error(exc) == expected


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_tool_success_redirects_to_updated_flag() -> None:
    publish_handler = AsyncMock(spec=PublishToolHandlerProtocol)
    list_handler = AsyncMock(spec=ListToolsForAdminHandlerProtocol)

    tool_id = uuid.uuid4()
    user = _user(role=Role.ADMIN)
    request = _request(path=f"/admin/tools/{tool_id}/publish", method="POST")

    response = await _original(admin_tools.publish_tool)(
        request=request,
        tool_id=tool_id,
        publish_handler=publish_handler,
        list_handler=list_handler,
        user=user,
        session=None,
    )

    assert isinstance(response, RedirectResponse)
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/tools?updated=1"
    publish_handler.handle.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_tool_domain_error_renders_template_with_status_and_error() -> None:
    publish_handler = AsyncMock(spec=PublishToolHandlerProtocol)
    list_handler = AsyncMock(spec=ListToolsForAdminHandlerProtocol)
    tool = _tool()

    exc = DomainError(code=ErrorCode.CONFLICT, message="Already published")
    publish_handler.handle.side_effect = exc
    list_handler.handle.return_value = ListToolsForAdminResult(tools=[tool])

    user = _user(role=Role.ADMIN)
    session = _session(user_id=user.id)
    request = _request(path=f"/admin/tools/{tool.id}/publish", method="POST")

    response = await _original(admin_tools.publish_tool)(
        request=request,
        tool_id=tool.id,
        publish_handler=publish_handler,
        list_handler=list_handler,
        user=user,
        session=session,
    )

    assert isinstance(response, _TemplateResponseProtocol)
    assert response.status_code == 409
    assert response.template.name == "admin_tools.html"
    assert response.context["csrf_token"] == session.csrf_token
    assert response.context["updated"] is None
    assert response.context["error"] == exc.message
    assert response.context["tools"] == [tool]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_depublish_tool_success_redirects_to_updated_flag() -> None:
    depublish_handler = AsyncMock(spec=DepublishToolHandlerProtocol)
    list_handler = AsyncMock(spec=ListToolsForAdminHandlerProtocol)

    tool_id = uuid.uuid4()
    user = _user(role=Role.ADMIN)
    request = _request(path=f"/admin/tools/{tool_id}/depublish", method="POST")

    response = await _original(admin_tools.depublish_tool)(
        request=request,
        tool_id=tool_id,
        depublish_handler=depublish_handler,
        list_handler=list_handler,
        user=user,
        session=None,
    )

    assert isinstance(response, RedirectResponse)
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/tools?updated=1"
    depublish_handler.handle.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_depublish_tool_domain_error_renders_template_with_status_and_error() -> None:
    depublish_handler = AsyncMock(spec=DepublishToolHandlerProtocol)
    list_handler = AsyncMock(spec=ListToolsForAdminHandlerProtocol)
    tool = _tool()

    exc = DomainError(code=ErrorCode.FORBIDDEN, message="Not allowed")
    depublish_handler.handle.side_effect = exc
    list_handler.handle.return_value = ListToolsForAdminResult(tools=[tool])

    user = _user(role=Role.ADMIN)
    session = _session(user_id=user.id)
    request = _request(path=f"/admin/tools/{tool.id}/depublish", method="POST")

    response = await _original(admin_tools.depublish_tool)(
        request=request,
        tool_id=tool.id,
        depublish_handler=depublish_handler,
        list_handler=list_handler,
        user=user,
        session=session,
    )

    assert isinstance(response, _TemplateResponseProtocol)
    assert response.status_code == 403
    assert response.template.name == "admin_tools.html"
    assert response.context["csrf_token"] == session.csrf_token
    assert response.context["updated"] is None
    assert response.context["error"] == exc.message
    assert response.context["tools"] == [tool]
