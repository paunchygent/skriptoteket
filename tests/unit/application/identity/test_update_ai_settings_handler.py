from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from skriptoteket.application.identity.commands import UpdateAiSettingsCommand
from skriptoteket.application.identity.handlers.update_ai_settings import UpdateAiSettingsHandler
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import UserProfile
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    ProfileRepositoryProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.asyncio
async def test_update_ai_settings_rejects_allow_when_remote_providers_disabled(
    now: datetime,
) -> None:
    settings = Settings(AI_REMOTE_PROVIDERS_ENABLED=False)
    user = make_user()
    profile = UserProfile(
        user_id=user.id,
        allow_remote_fallback=None,
        inline_completion_provider=None,
        created_at=now,
        updated_at=now,
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_by_id.return_value = user

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    profiles.get_by_user_id.return_value = profile

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    handler = UpdateAiSettingsHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        clock=clock,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            UpdateAiSettingsCommand(user_id=user.id, remote_fallback_preference="allow")
        )

    assert exc_info.value.code == ErrorCode.FORBIDDEN
    profiles.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_ai_settings_rejects_external_completion_when_remote_fallback_not_allowed(
    now: datetime,
) -> None:
    settings = Settings(AI_REMOTE_PROVIDERS_ENABLED=True)
    user = make_user()
    profile = UserProfile(
        user_id=user.id,
        allow_remote_fallback=None,
        inline_completion_provider=None,
        created_at=now,
        updated_at=now,
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_by_id.return_value = user

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    profiles.get_by_user_id.return_value = profile

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    handler = UpdateAiSettingsHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        clock=clock,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            UpdateAiSettingsCommand(
                user_id=user.id,
                inline_completion_provider_preference="external",
            )
        )

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    profiles.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_ai_settings_can_set_allow_and_external_completion_together(
    now: datetime,
) -> None:
    settings = Settings(AI_REMOTE_PROVIDERS_ENABLED=True)
    user = make_user()
    profile = UserProfile(
        user_id=user.id,
        allow_remote_fallback=None,
        inline_completion_provider=None,
        created_at=now,
        updated_at=now,
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_by_id.return_value = user

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    profiles.get_by_user_id.return_value = profile

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    expected_profile = profile.model_copy(
        update={
            "allow_remote_fallback": True,
            "inline_completion_provider": "external",
            "updated_at": now,
        }
    )
    profiles.update.return_value = expected_profile

    handler = UpdateAiSettingsHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        clock=clock,
    )

    result = await handler.handle(
        UpdateAiSettingsCommand(
            user_id=user.id,
            remote_fallback_preference="allow",
            inline_completion_provider_preference="external",
        )
    )

    assert result.profile == expected_profile
    profiles.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_ai_settings_clears_external_completion_when_remote_fallback_denied(
    now: datetime,
) -> None:
    settings = Settings(AI_REMOTE_PROVIDERS_ENABLED=True)
    user = make_user()
    profile = UserProfile(
        user_id=user.id,
        allow_remote_fallback=True,
        inline_completion_provider="external",
        created_at=now,
        updated_at=now,
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_by_id.return_value = user

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    profiles.get_by_user_id.return_value = profile

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    expected_profile = profile.model_copy(
        update={
            "allow_remote_fallback": False,
            "inline_completion_provider": None,
            "updated_at": now,
        }
    )
    profiles.update.return_value = expected_profile

    handler = UpdateAiSettingsHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        clock=clock,
    )

    result = await handler.handle(
        UpdateAiSettingsCommand(user_id=user.id, remote_fallback_preference="deny")
    )

    assert result.profile == expected_profile
    profiles.update.assert_awaited_once()
