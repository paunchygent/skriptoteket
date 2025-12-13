from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.identity.commands import CreateLocalUserCommand
from skriptoteket.application.identity.handlers.provision_local_user import (
    ProvisionLocalUserHandler,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import PasswordHasherProtocol, UserRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.asyncio
async def test_provision_user_creates_local_user_for_admin(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN, email="admin@example.com")

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_auth_by_email.return_value = None

    new_user_id = uuid4()
    created_user = make_user(
        role=Role.USER, email="new@example.com", user_id=new_user_id
    ).model_copy(update={"created_at": now, "updated_at": now})
    users.create.return_value = created_user

    password_hasher = Mock(spec=PasswordHasherProtocol)
    password_hasher.hash.return_value = "hash"

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = new_user_id

    handler = ProvisionLocalUserHandler(
        uow=uow,
        users=users,
        password_hasher=password_hasher,
        clock=clock,
        id_generator=id_generator,
    )

    result = await handler.handle(
        actor=actor,
        command=CreateLocalUserCommand(email=" New@Example.com ", password="pw", role=Role.USER),
    )

    assert result.user == created_user
    users.get_auth_by_email.assert_awaited_once_with("new@example.com")
    users.create.assert_awaited_once()

    created = users.create.call_args.kwargs["user"]
    assert created.id == new_user_id
    assert created.email == "new@example.com"
    assert created.role == Role.USER


@pytest.mark.asyncio
async def test_provision_user_raises_for_non_admin(now: datetime) -> None:
    actor = make_user(role=Role.USER, email="user@example.com")

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    password_hasher = Mock(spec=PasswordHasherProtocol)
    clock = Mock(spec=ClockProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)

    handler = ProvisionLocalUserHandler(
        uow=uow,
        users=users,
        password_hasher=password_hasher,
        clock=clock,
        id_generator=id_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=CreateLocalUserCommand(email="new@example.com", password="pw", role=Role.USER),
        )

    assert exc_info.value.code == ErrorCode.FORBIDDEN
    uow.__aenter__.assert_not_awaited()
    users.get_auth_by_email.assert_not_awaited()


@pytest.mark.asyncio
async def test_provision_user_raises_when_admin_attempts_to_create_admin(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN, email="admin@example.com")

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    password_hasher = Mock(spec=PasswordHasherProtocol)
    clock = Mock(spec=ClockProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)

    handler = ProvisionLocalUserHandler(
        uow=uow,
        users=users,
        password_hasher=password_hasher,
        clock=clock,
        id_generator=id_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=CreateLocalUserCommand(email="new@example.com", password="pw", role=Role.ADMIN),
        )

    assert exc_info.value.code == ErrorCode.FORBIDDEN
    uow.__aenter__.assert_not_awaited()
    users.get_auth_by_email.assert_not_awaited()
