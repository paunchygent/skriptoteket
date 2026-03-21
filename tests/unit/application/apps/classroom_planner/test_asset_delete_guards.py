from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner import (
    DeleteRoomTemplateHandler,
    DeleteRosterHandler,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import RoomTemplate, Roster
from skriptoteket.domain.errors import DomainError, ErrorCode
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
async def test_delete_roster_blocks_when_active_draft_depends_on_it(now):
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
    drafts.has_active_for_roster.return_value = True
    handler = DeleteRosterHandler(FakeUow(), rosters, drafts)

    with pytest.raises(DomainError) as exc:
        await handler.handle(roster_id=roster_id, owner_user_id=owner_id)

    assert exc.value.code == ErrorCode.CONFLICT
    rosters.delete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_template_blocks_when_active_draft_depends_on_it(now):
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
    drafts.has_active_for_template.return_value = True
    handler = DeleteRoomTemplateHandler(FakeUow(), templates, drafts)

    with pytest.raises(DomainError) as exc:
        await handler.handle(template_id=template_id, owner_user_id=owner_id)

    assert exc.value.code == ErrorCode.CONFLICT
    templates.delete.assert_not_called()
