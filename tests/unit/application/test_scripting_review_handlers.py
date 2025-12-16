from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.scripting.commands import PublishVersionCommand, RequestChangesCommand
from skriptoteket.application.scripting.handlers.publish_version import PublishVersionHandler
from skriptoteket.application.scripting.handlers.request_changes import RequestChangesHandler
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
async def test_publish_version_requires_admin(now: datetime) -> None:
    actor = make_user(role=Role.CONTRIBUTOR)

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol)

    handler = PublishVersionHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        clock=clock,
        id_generator=id_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=PublishVersionCommand(version_id=uuid4(), change_summary=None),
        )

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    assert uow.entered is False
    versions.get_by_id.assert_not_called()
    tools.get_by_id.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_version_rejects_missing_version(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = None

    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(return_value=uuid4()))

    handler = PublishVersionHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        clock=clock,
        id_generator=id_generator,
    )

    version_id = uuid4()
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=PublishVersionCommand(version_id=version_id, change_summary=None),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert uow.entered is True
    assert uow.exited is True
    tools.get_by_id.assert_not_called()
    versions.get_active_for_tool.assert_not_called()
    versions.update.assert_not_called()
    versions.create.assert_not_called()
    tools.set_active_version_id.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_version_rejects_missing_tool(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    reviewed_version = make_tool_version(
        tool_id=tool_id,
        version_id=uuid4(),
        version_number=1,
        state=VersionState.IN_REVIEW,
        created_by_user_id=uuid4(),
        now=now,
    )

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = None

    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = reviewed_version

    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(return_value=uuid4()))

    handler = PublishVersionHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        clock=clock,
        id_generator=id_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=PublishVersionCommand(version_id=reviewed_version.id, change_summary=None),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert uow.entered is True
    assert uow.exited is True
    versions.get_active_for_tool.assert_not_called()
    versions.update.assert_not_called()
    versions.create.assert_not_called()
    tools.set_active_version_id.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_version_archives_reviewed_and_previous_active_and_updates_pointer(
    now: datetime,
) -> None:
    actor = make_user(role=Role.ADMIN, user_id=uuid4())
    tool = make_tool(now=now)

    reviewed_version = make_tool_version(
        tool_id=tool.id,
        version_id=uuid4(),
        version_number=4,
        state=VersionState.IN_REVIEW,
        created_by_user_id=uuid4(),
        now=now,
        change_summary="Original summary",
    )
    previous_active = make_tool_version(
        tool_id=tool.id,
        version_id=uuid4(),
        version_number=3,
        state=VersionState.ACTIVE,
        created_by_user_id=uuid4(),
        now=now,
    )

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool

    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = reviewed_version
    versions.get_active_for_tool.return_value = previous_active
    versions.get_next_version_number.return_value = 5
    versions.update.side_effect = lambda *, version: version
    versions.create.side_effect = lambda *, version: version

    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    new_active_version_id = uuid4()
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(return_value=new_active_version_id))

    handler = PublishVersionHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        clock=clock,
        id_generator=id_generator,
    )

    result = await handler.handle(
        actor=actor,
        command=PublishVersionCommand(version_id=reviewed_version.id, change_summary=None),
    )

    assert result.new_active_version.id == new_active_version_id
    assert result.new_active_version.state is VersionState.ACTIVE
    assert result.new_active_version.version_number == 5
    assert result.new_active_version.derived_from_version_id == reviewed_version.id
    assert result.new_active_version.change_summary == "Original summary"

    assert result.archived_reviewed_version.id == reviewed_version.id
    assert result.archived_reviewed_version.state is VersionState.ARCHIVED
    assert result.archived_reviewed_version.published_by_user_id == actor.id
    assert result.archived_reviewed_version.published_at == now

    assert result.archived_previous_active_version is not None
    assert result.archived_previous_active_version.id == previous_active.id
    assert result.archived_previous_active_version.state is VersionState.ARCHIVED

    tools.set_active_version_id.assert_awaited_once_with(
        tool_id=tool.id,
        active_version_id=new_active_version_id,
        now=now,
    )
    tools.set_published.assert_awaited_once_with(
        tool_id=tool.id,
        is_published=True,
        now=now,
    )
    assert uow.entered is True
    assert uow.exited is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_version_does_not_set_published_when_tool_already_published(
    now: datetime,
) -> None:
    actor = make_user(role=Role.ADMIN, user_id=uuid4())
    tool = make_tool(now=now, is_published=True)

    reviewed_version = make_tool_version(
        tool_id=tool.id,
        version_id=uuid4(),
        version_number=2,
        state=VersionState.IN_REVIEW,
        created_by_user_id=uuid4(),
        now=now,
    )
    previous_active = make_tool_version(
        tool_id=tool.id,
        version_id=uuid4(),
        version_number=1,
        state=VersionState.ACTIVE,
        created_by_user_id=uuid4(),
        now=now,
    )

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool

    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = reviewed_version
    versions.get_active_for_tool.return_value = previous_active
    versions.get_next_version_number.return_value = 3
    versions.update.side_effect = lambda *, version: version
    versions.create.side_effect = lambda *, version: version

    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    new_active_version_id = uuid4()
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(return_value=new_active_version_id))

    handler = PublishVersionHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        clock=clock,
        id_generator=id_generator,
    )

    result = await handler.handle(
        actor=actor,
        command=PublishVersionCommand(version_id=reviewed_version.id, change_summary=None),
    )

    assert result.new_active_version.id == new_active_version_id
    assert result.new_active_version.state is VersionState.ACTIVE

    tools.set_active_version_id.assert_awaited_once_with(
        tool_id=tool.id,
        active_version_id=new_active_version_id,
        now=now,
    )
    tools.set_published.assert_not_called()
    assert uow.entered is True
    assert uow.exited is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_changes_requires_admin(now: datetime) -> None:
    actor = make_user(role=Role.CONTRIBUTOR)

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol)

    handler = RequestChangesHandler(
        uow=uow,
        versions=versions,
        clock=clock,
        id_generator=id_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RequestChangesCommand(version_id=uuid4(), message=None),
        )

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    assert uow.entered is False
    versions.get_by_id.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_changes_rejects_missing_version(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = None
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol)

    handler = RequestChangesHandler(
        uow=uow,
        versions=versions,
        clock=clock,
        id_generator=id_generator,
    )

    version_id = uuid4()
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RequestChangesCommand(version_id=version_id, message=None),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert uow.entered is True
    assert uow.exited is True
    versions.update.assert_not_called()
    versions.create.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_changes_rejects_when_version_is_not_in_review(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)

    reviewed_version = make_tool_version(
        tool_id=uuid4(),
        version_id=uuid4(),
        version_number=1,
        state=VersionState.DRAFT,
        created_by_user_id=uuid4(),
        now=now,
    )

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = reviewed_version
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol)

    handler = RequestChangesHandler(
        uow=uow,
        versions=versions,
        clock=clock,
        id_generator=id_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RequestChangesCommand(version_id=reviewed_version.id, message="please"),
        )

    assert exc_info.value.code is ErrorCode.CONFLICT
    versions.update.assert_not_called()
    versions.create.assert_not_called()
    assert uow.entered is True
    assert uow.exited is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_changes_archives_in_review_and_creates_new_draft(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN, user_id=uuid4())
    author_id = uuid4()
    in_review_version = make_tool_version(
        tool_id=uuid4(),
        version_id=uuid4(),
        version_number=1,
        state=VersionState.IN_REVIEW,
        created_by_user_id=author_id,
        now=now,
    )

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = in_review_version
    versions.get_next_version_number.return_value = 2
    versions.update.side_effect = lambda *, version: version
    versions.create.side_effect = lambda *, version: version

    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    new_draft_id = uuid4()
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(return_value=new_draft_id))

    handler = RequestChangesHandler(
        uow=uow,
        versions=versions,
        clock=clock,
        id_generator=id_generator,
    )

    result = await handler.handle(
        actor=actor,
        command=RequestChangesCommand(version_id=in_review_version.id, message="  Please fix  "),
    )

    assert result.archived_in_review_version.id == in_review_version.id
    assert result.archived_in_review_version.state is VersionState.ARCHIVED
    assert result.archived_in_review_version.reviewed_by_user_id == actor.id
    assert result.archived_in_review_version.reviewed_at == now

    assert result.new_draft_version.id == new_draft_id
    assert result.new_draft_version.state is VersionState.DRAFT
    assert result.new_draft_version.created_by_user_id == author_id
    assert result.new_draft_version.derived_from_version_id == in_review_version.id
    assert result.new_draft_version.entrypoint == in_review_version.entrypoint
    assert result.new_draft_version.source_code == in_review_version.source_code
    assert result.new_draft_version.change_summary == "Please fix"

    assert uow.entered is True
    assert uow.exited is True
