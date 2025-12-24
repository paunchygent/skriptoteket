from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.identity.commands import RegisterUserCommand
from skriptoteket.application.identity.handlers.register_user import RegisterUserHandler
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import UserProfile
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import (
    PasswordHasherProtocol,
    ProfileRepositoryProtocol,
    SessionRepositoryProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.token_generator import TokenGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.asyncio
async def test_register_user_creates_profile_and_session(now: datetime) -> None:
    settings = Settings()
    user_id = uuid4()
    created_user = make_user(email="teacher@example.com", user_id=user_id).model_copy(
        update={"created_at": now, "updated_at": now}
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_auth_by_email.return_value = None
    users.create.return_value = created_user

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    expected_profile = UserProfile(
        user_id=user_id,
        first_name="Ada",
        last_name="Lovelace",
        display_name=None,
        locale="sv-SE",
        created_at=now,
        updated_at=now,
    )
    profiles.create.return_value = expected_profile

    sessions = AsyncMock(spec=SessionRepositoryProtocol)

    password_hasher = Mock(spec=PasswordHasherProtocol)
    password_hasher.hash.return_value = "hash"

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.side_effect = [user_id, uuid4()]

    token_generator = Mock(spec=TokenGeneratorProtocol)
    token_generator.new_token.return_value = "csrf"

    handler = RegisterUserHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        sessions=sessions,
        password_hasher=password_hasher,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    result = await handler.handle(
        RegisterUserCommand(
            email="Teacher@Example.com",
            password="password123",
            first_name=" Ada ",
            last_name=" Lovelace ",
        )
    )

    assert result.user == created_user
    assert result.profile == expected_profile
    assert result.csrf_token == "csrf"

    sessions.create.assert_awaited_once()
    created_session = sessions.create.call_args.kwargs["session"]
    assert created_session.user_id == user_id
    assert created_session.expires_at == now + timedelta(seconds=settings.SESSION_TTL_SECONDS)


@pytest.mark.asyncio
async def test_register_user_rejects_invalid_email(now: datetime) -> None:
    settings = Settings()

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    sessions = AsyncMock(spec=SessionRepositoryProtocol)

    password_hasher = Mock(spec=PasswordHasherProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    token_generator = Mock(spec=TokenGeneratorProtocol)

    handler = RegisterUserHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        sessions=sessions,
        password_hasher=password_hasher,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            RegisterUserCommand(
                email="not-an-email",
                password="password123",
                first_name="Ada",
                last_name="Lovelace",
            )
        )

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    users.get_auth_by_email.assert_not_awaited()
    users.create.assert_not_awaited()
    profiles.create.assert_not_awaited()
    sessions.create.assert_not_awaited()
