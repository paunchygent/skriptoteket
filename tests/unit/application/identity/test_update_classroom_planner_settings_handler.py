"""Classroom planner profile preference handler tests.

Purpose:
    Verify authenticated Smart settings are persisted through profile-owned
    identity application state rather than browser-local draft defaults.

Relationships:
    - Covers `UpdateClassroomPlannerSettingsHandler`.
    - Supports Klassrumskartan new-draft preference continuity.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from skriptoteket.application.identity.commands import UpdateClassroomPlannerSettingsCommand
from skriptoteket.application.identity.handlers.update_classroom_planner_settings import (
    UpdateClassroomPlannerSettingsHandler,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    ProfileRepositoryProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.identity_fixtures import make_user, make_user_profile


@pytest.mark.asyncio
async def test_update_classroom_planner_settings_persists_explicit_profile_preferences(
    now: datetime,
) -> None:
    user = make_user()
    profile = make_user_profile(user_id=user.id, now=now)

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_by_id.return_value = user

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    profiles.get_by_user_id.return_value = profile
    profiles.update.side_effect = lambda *, profile: profile

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    handler = UpdateClassroomPlannerSettingsHandler(
        uow=uow,
        users=users,
        profiles=profiles,
        clock=clock,
    )

    result = await handler.handle(
        UpdateClassroomPlannerSettingsCommand(
            user_id=user.id,
            smart_enabled=False,
            use_history=True,
            grouping_seating_distance_enabled=False,
        )
    )

    assert result.profile.classroom_planner_smart_enabled is False
    assert result.profile.classroom_planner_use_history is True
    assert result.profile.classroom_planner_grouping_seating_distance_enabled is False
    profiles.update.assert_awaited_once()
