from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner import (
    DeleteRoomTemplateHandler,
    DeleteRosterHandler,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import RoomTemplate, Roster
from skriptoteket.protocols.classroom_planner import (
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
)
from tests.fixtures.application_fixtures import FakeUow


@pytest.fixture
def uow():
    return FakeUow()


@pytest.fixture
def now():
    return datetime(2025, 1, 1, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_delete_roster_removes_dependent_drafts_before_roster(now):
    owner_id = uuid4()
    roster_id = uuid4()
    rosters = AsyncMock(spec=RosterRepositoryProtocol)
    drafts = AsyncMock(spec=PlanDraftRepositoryProtocol)
    rosters.get_by_id.return_value = Roster(
        id=roster_id,
        owner_user_id=owner_id,
        name="SA24D",
        students=[],
        created_at=now,
        updated_at=now,
    )
    handler = DeleteRosterHandler(FakeUow(), rosters, drafts)

    await handler.handle(roster_id=roster_id, owner_user_id=owner_id)

    drafts.delete_for_roster.assert_awaited_once_with(owner_user_id=owner_id, roster_id=roster_id)
    rosters.delete.assert_awaited_once_with(roster_id=roster_id)


@pytest.mark.asyncio
async def test_delete_template_removes_dependent_drafts_before_template(now):
    owner_id = uuid4()
    template_id = uuid4()
    templates = AsyncMock(spec=RoomTemplateRepositoryProtocol)
    drafts = AsyncMock(spec=PlanDraftRepositoryProtocol)
    templates.get_by_id.return_value = RoomTemplate(
        id=template_id,
        owner_user_id=owner_id,
        name="Sal 101",
        seats=[],
        fixtures=[],
        created_at=now,
        updated_at=now,
    )
    handler = DeleteRoomTemplateHandler(FakeUow(), templates, drafts)

    await handler.handle(template_id=template_id, owner_user_id=owner_id)

    drafts.delete_for_template.assert_awaited_once_with(
        owner_user_id=owner_id,
        template_id=template_id,
    )
    templates.delete.assert_awaited_once_with(template_id=template_id)
