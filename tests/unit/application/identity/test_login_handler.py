from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.identity.commands import LoginCommand
from skriptoteket.application.identity.handlers.login import LoginHandler
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import UserAuth
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import (
    PasswordHasherProtocol,
    SessionRepositoryProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.token_generator import TokenGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.asyncio
async def test_login_creates_session_and_returns_user(now: datetime) -> None:
    settings = Settings()
    fixed_now = now
    user = make_user(email="teacher@example.com")
    user_auth = UserAuth(user=user, password_hash="hash")

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_auth_by_email.return_value = user_auth

    sessions = AsyncMock(spec=SessionRepositoryProtocol)

    password_hasher = Mock(spec=PasswordHasherProtocol)
    password_hasher.verify.return_value = True

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = fixed_now

    session_id = uuid4()
    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = session_id

    token_generator = Mock(spec=TokenGeneratorProtocol)
    token_generator.new_token.return_value = "csrf"

    handler = LoginHandler(
        settings=settings,
        uow=uow,
        users=users,
        sessions=sessions,
        password_hasher=password_hasher,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    result = await handler.handle(LoginCommand(email=" Teacher@Example.com ", password="pw"))

    assert result.session_id == session_id
    assert result.csrf_token == "csrf"
    assert result.user == user

    sessions.create.assert_awaited_once()
    created_session = sessions.create.call_args.kwargs["session"]
    assert created_session.user_id == user.id
    assert created_session.created_at == fixed_now
    assert created_session.expires_at == fixed_now + timedelta(seconds=settings.SESSION_TTL_SECONDS)


@pytest.mark.asyncio
async def test_login_raises_for_invalid_credentials() -> None:
    settings = Settings()

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_auth_by_email.return_value = None

    sessions = AsyncMock(spec=SessionRepositoryProtocol)

    password_hasher = Mock(spec=PasswordHasherProtocol)
    clock = Mock(spec=ClockProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    token_generator = Mock(spec=TokenGeneratorProtocol)

    handler = LoginHandler(
        settings=settings,
        uow=uow,
        users=users,
        sessions=sessions,
        password_hasher=password_hasher,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(LoginCommand(email="nope@example.com", password="pw"))

    assert exc_info.value.code == ErrorCode.INVALID_CREDENTIALS
    sessions.create.assert_not_awaited()
