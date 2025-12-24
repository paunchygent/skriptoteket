from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from skriptoteket.application.identity.commands import ChangeEmailCommand
from skriptoteket.application.identity.handlers.change_email import ChangeEmailHandler
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import UserRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.asyncio
async def test_change_email_updates_user_and_resets_verification(now: datetime) -> None:
    user = make_user(email="old@example.com").model_copy(update={"email_verified": True})
    updated_user = user.model_copy(
        update={"email": "new@example.com", "email_verified": False, "updated_at": now}
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_by_id.return_value = user
    users.get_auth_by_email.return_value = None
    users.update.return_value = updated_user

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    handler = ChangeEmailHandler(uow=uow, users=users, clock=clock)

    result = await handler.handle(
        ChangeEmailCommand(user_id=user.id, new_email=" New@Example.com ")
    )

    assert result.user == updated_user
    users.get_auth_by_email.assert_awaited_once_with("new@example.com")
    users.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_email_rejects_same_email(now: datetime) -> None:
    user = make_user(email="same@example.com")

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_by_id.return_value = user

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    handler = ChangeEmailHandler(uow=uow, users=users, clock=clock)

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(ChangeEmailCommand(user_id=user.id, new_email=" Same@example.com "))

    assert exc_info.value.code == ErrorCode.DUPLICATE_ENTRY
    users.get_auth_by_email.assert_not_awaited()
    users.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_change_email_rejects_invalid_email() -> None:
    uow = AsyncMock(spec=UnitOfWorkProtocol)
    users = AsyncMock(spec=UserRepositoryProtocol)
    clock = Mock(spec=ClockProtocol)

    handler = ChangeEmailHandler(uow=uow, users=users, clock=clock)

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(ChangeEmailCommand(user_id=make_user().id, new_email="invalid"))

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    uow.__aenter__.assert_not_awaited()
    users.get_by_id.assert_not_awaited()
