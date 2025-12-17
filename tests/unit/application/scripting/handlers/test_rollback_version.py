from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.scripting.commands import RollbackVersionCommand
from skriptoteket.application.scripting.handlers.rollback_version import RollbackVersionHandler
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.models import ToolVersion, VersionState, compute_content_hash
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.catalog_fixtures import make_tool
from tests.fixtures.identity_fixtures import make_user


class FakeUow(UnitOfWorkProtocol):
    def __init__(self) -> None:
        self.entered = False
        self.exited = False

    async def __aenter__(self) -> UnitOfWorkProtocol:
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.exited = True


def make_tool_version(
    *,
    tool_id: UUID,
    version_id: UUID,
    version_number: int,
    state: VersionState,
    created_by_user_id: UUID,
    now: datetime,
    change_summary: str | None = None,
) -> ToolVersion:
    source_code = "def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>ok</p>'\n"
    entrypoint = "run_tool"
    return ToolVersion(
        id=version_id,
        tool_id=tool_id,
        version_number=version_number,
        state=state,
        source_code=source_code,
        entrypoint=entrypoint,
        content_hash=compute_content_hash(entrypoint=entrypoint, source_code=source_code),
        derived_from_version_id=None,
        created_by_user_id=created_by_user_id,
        created_at=now,
        submitted_for_review_by_user_id=None,
        submitted_for_review_at=None,
        reviewed_by_user_id=None,
        reviewed_at=None,
        published_by_user_id=None,
        published_at=None,
        change_summary=change_summary,
        review_note=None,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rollback_version_requires_superuser(now: datetime) -> None:
    """Admin should not be able to rollback - only superuser."""
    actor = make_user(role=Role.ADMIN)

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol)

    handler = RollbackVersionHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        clock=clock,
        id_generator=id_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, command=RollbackVersionCommand(version_id=uuid4()))

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    assert uow.entered is False
    versions.get_by_id.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rollback_version_rejects_missing_version(now: datetime) -> None:
    actor = make_user(role=Role.SUPERUSER)
    version_id = uuid4()

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = None

    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(return_value=uuid4()))

    handler = RollbackVersionHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        clock=clock,
        id_generator=id_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, command=RollbackVersionCommand(version_id=version_id))

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert uow.entered is True
    assert uow.exited is True
    tools.get_by_id.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rollback_version_rejects_missing_tool(now: datetime) -> None:
    actor = make_user(role=Role.SUPERUSER)
    tool_id = uuid4()
    archived_version = make_tool_version(
        tool_id=tool_id,
        version_id=uuid4(),
        version_number=1,
        state=VersionState.ARCHIVED,
        created_by_user_id=uuid4(),
        now=now,
    )

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = None

    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = archived_version

    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(return_value=uuid4()))

    handler = RollbackVersionHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        clock=clock,
        id_generator=id_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor, command=RollbackVersionCommand(version_id=archived_version.id)
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert uow.entered is True
    assert uow.exited is True
    versions.get_active_for_tool.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rollback_version_rejects_non_archived_version(now: datetime) -> None:
    """Only ARCHIVED versions can be rolled back."""
    actor = make_user(role=Role.SUPERUSER)
    tool = make_tool(now=now)
    draft_version = make_tool_version(
        tool_id=tool.id,
        version_id=uuid4(),
        version_number=1,
        state=VersionState.DRAFT,  # Not archived
        created_by_user_id=uuid4(),
        now=now,
    )

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool

    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = draft_version
    versions.get_active_for_tool.return_value = None
    versions.get_next_version_number.return_value = 2

    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(return_value=uuid4()))

    handler = RollbackVersionHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        clock=clock,
        id_generator=id_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor, command=RollbackVersionCommand(version_id=draft_version.id)
        )

    assert exc_info.value.code is ErrorCode.CONFLICT
    assert uow.entered is True
    assert uow.exited is True
    versions.update.assert_not_called()
    versions.create.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rollback_version_creates_new_active_and_archives_previous(now: datetime) -> None:
    """Happy path: rollback with existing active version."""
    actor = make_user(role=Role.SUPERUSER, user_id=uuid4())
    tool = make_tool(now=now)

    archived_version = make_tool_version(
        tool_id=tool.id,
        version_id=uuid4(),
        version_number=2,
        state=VersionState.ARCHIVED,
        created_by_user_id=uuid4(),
        now=now,
        change_summary="Original v2",
    )

    previous_active = make_tool_version(
        tool_id=tool.id,
        version_id=uuid4(),
        version_number=3,
        state=VersionState.ACTIVE,
        created_by_user_id=uuid4(),
        now=now,
    )

    new_active_version_id = uuid4()

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool

    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = archived_version
    versions.get_active_for_tool.return_value = previous_active
    versions.get_next_version_number.return_value = 4
    versions.update.side_effect = lambda *, version: version
    versions.create.side_effect = lambda *, version: version

    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(return_value=new_active_version_id))

    handler = RollbackVersionHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        clock=clock,
        id_generator=id_generator,
    )

    result = await handler.handle(
        actor=actor, command=RollbackVersionCommand(version_id=archived_version.id)
    )

    assert result.new_active_version.id == new_active_version_id
    assert result.new_active_version.state is VersionState.ACTIVE
    assert result.new_active_version.version_number == 4
    assert result.new_active_version.derived_from_version_id == archived_version.id
    assert result.new_active_version.source_code == archived_version.source_code
    assert result.new_active_version.entrypoint == archived_version.entrypoint

    assert result.archived_previous_active_version is not None
    assert result.archived_previous_active_version.id == previous_active.id
    assert result.archived_previous_active_version.state is VersionState.ARCHIVED

    tools.set_active_version_id.assert_awaited_once_with(
        tool_id=tool.id,
        active_version_id=new_active_version_id,
        now=now,
    )
    assert uow.entered is True
    assert uow.exited is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rollback_version_creates_new_active_without_previous(now: datetime) -> None:
    """Rollback when there's no current active version (edge case)."""
    actor = make_user(role=Role.SUPERUSER, user_id=uuid4())
    tool = make_tool(now=now)

    archived_version = make_tool_version(
        tool_id=tool.id,
        version_id=uuid4(),
        version_number=1,
        state=VersionState.ARCHIVED,
        created_by_user_id=uuid4(),
        now=now,
    )

    new_active_version_id = uuid4()

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool

    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = archived_version
    versions.get_active_for_tool.return_value = None  # No previous active
    versions.get_next_version_number.return_value = 2
    versions.update.side_effect = lambda *, version: version
    versions.create.side_effect = lambda *, version: version

    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(return_value=new_active_version_id))

    handler = RollbackVersionHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        clock=clock,
        id_generator=id_generator,
    )

    result = await handler.handle(
        actor=actor, command=RollbackVersionCommand(version_id=archived_version.id)
    )

    assert result.new_active_version.id == new_active_version_id
    assert result.new_active_version.state is VersionState.ACTIVE
    assert result.new_active_version.version_number == 2
    assert result.archived_previous_active_version is None

    tools.set_active_version_id.assert_awaited_once_with(
        tool_id=tool.id,
        active_version_id=new_active_version_id,
        now=now,
    )
    assert uow.entered is True
    assert uow.exited is True
