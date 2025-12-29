"""Tests for admin user login events API (ST-17-07)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.identity.admin_users import GetUserResult, ListUsersResult
from skriptoteket.application.identity.login_events import ListLoginEventsResult
from skriptoteket.domain.identity.login_events import LoginEvent, LoginEventStatus
from skriptoteket.domain.identity.models import AuthProvider, Role
from skriptoteket.protocols.identity import GetUserHandlerProtocol, ListUsersHandlerProtocol
from skriptoteket.protocols.login_events import ListLoginEventsHandlerProtocol
from skriptoteket.web.api.v1 import admin_users
from tests.unit.web.admin_scripting_test_support import _original, _user


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_admin_users_calls_handler() -> None:
    handler = AsyncMock(spec=ListUsersHandlerProtocol)
    superuser = _user(role=Role.SUPERUSER)
    handler.handle.return_value = ListUsersResult(users=[superuser], total=1)

    result = await _original(admin_users.list_admin_users)(
        handler=handler,
        user=superuser,
        limit=10,
        offset=5,
    )

    assert result.total == 1
    assert result.users[0].id == superuser.id
    handler.handle.assert_awaited_once()
    assert handler.handle.call_args.kwargs["query"].limit == 10
    assert handler.handle.call_args.kwargs["query"].offset == 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_admin_user_login_events_calls_handlers() -> None:
    events_handler = AsyncMock(spec=ListLoginEventsHandlerProtocol)
    user_handler = AsyncMock(spec=GetUserHandlerProtocol)
    superuser = _user(role=Role.SUPERUSER)
    target_user = _user(role=Role.USER)

    user_handler.handle.return_value = GetUserResult(user=target_user)
    now = datetime.now(timezone.utc)
    event = LoginEvent(
        id=uuid4(),
        user_id=target_user.id,
        status=LoginEventStatus.SUCCESS,
        failure_code=None,
        ip_address="127.0.0.1",
        user_agent="pytest",
        auth_provider=AuthProvider.LOCAL,
        correlation_id=uuid4(),
        geo_country_code=None,
        geo_region=None,
        geo_city=None,
        geo_latitude=None,
        geo_longitude=None,
        created_at=now,
    )
    events_handler.handle.return_value = ListLoginEventsResult(events=[event])

    result = await _original(admin_users.get_admin_user_login_events)(
        user_id=target_user.id,
        handler=events_handler,
        user_handler=user_handler,
        user=superuser,
        limit=25,
    )

    assert result.user.id == target_user.id
    assert result.events[0].id == event.id
    events_handler.handle.assert_awaited_once()
    assert events_handler.handle.call_args.kwargs["query"].user_id == target_user.id
    assert events_handler.handle.call_args.kwargs["query"].limit == 25
