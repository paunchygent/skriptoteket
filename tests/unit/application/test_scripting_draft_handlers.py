from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.scripting.commands import SaveDraftVersionCommand
from skriptoteket.application.scripting.handlers.save_draft_version import SaveDraftVersionHandler
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.draft_locks import DraftLock
from skriptoteket.domain.scripting.models import ToolVersion, VersionState, compute_content_hash
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.draft_locks import DraftLockRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
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
        change_summary=None,
        review_note=None,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_draft_version_rejects_when_draft_head_has_advanced(now: datetime) -> None:
    actor = make_user(role=Role.CONTRIBUTOR, user_id=uuid4())
    tool_id = uuid4()
    version_id = uuid4()
    previous = make_tool_version(
        tool_id=tool_id,
        version_id=version_id,
        version_number=1,
        state=VersionState.DRAFT,
        created_by_user_id=actor.id,
        now=now,
    )

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = previous
    versions.list_for_tool.return_value = [
        previous.model_copy(update={"id": uuid4(), "version_number": 2})
    ]
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    maintainers.is_maintainer.return_value = True

    settings = Mock(spec=Settings)
    settings.DRAFT_LOCK_TTL_SECONDS = 600

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    locks = AsyncMock(spec=DraftLockRepositoryProtocol)

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = uuid4()

    handler = SaveDraftVersionHandler(
        settings=settings,
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        locks=locks,
        clock=clock,
        id_generator=id_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=SaveDraftVersionCommand(
                version_id=version_id,
                entrypoint="run_tool",
                source_code=(
                    "def run_tool(input_path: str, output_dir: str) -> str:\n"
                    "    return '<p>ok</p>'\n"
                ),
                change_summary=None,
                expected_parent_version_id=version_id,
            ),
        )

    assert exc_info.value.code is ErrorCode.CONFLICT
    versions.create.assert_not_called()
    versions.get_next_version_number.assert_not_called()
    assert uow.entered is True
    assert uow.exited is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_draft_version_creates_new_snapshot_when_head_matches(now: datetime) -> None:
    actor = make_user(role=Role.CONTRIBUTOR, user_id=uuid4())
    tool_id = uuid4()
    version_id = uuid4()
    previous = make_tool_version(
        tool_id=tool_id,
        version_id=version_id,
        version_number=1,
        state=VersionState.DRAFT,
        created_by_user_id=actor.id,
        now=now,
    )
    new_version_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = previous
    versions.list_for_tool.return_value = [previous]
    versions.get_next_version_number.return_value = 2
    versions.create.side_effect = lambda *, version: version
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    maintainers.is_maintainer.return_value = True

    settings = Mock(spec=Settings)
    settings.DRAFT_LOCK_TTL_SECONDS = 600

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    locks = AsyncMock(spec=DraftLockRepositoryProtocol)
    locks.get_for_tool.return_value = DraftLock(
        tool_id=tool_id,
        draft_head_id=version_id,
        locked_by_user_id=actor.id,
        locked_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(minutes=5),
        forced_by_user_id=None,
    )

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = new_version_id

    handler = SaveDraftVersionHandler(
        settings=settings,
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        locks=locks,
        clock=clock,
        id_generator=id_generator,
    )

    result = await handler.handle(
        actor=actor,
        command=SaveDraftVersionCommand(
            version_id=version_id,
            entrypoint="run_tool",
            source_code=(
                "def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>new</p>'\n"
            ),
            change_summary="Update output",
            expected_parent_version_id=version_id,
        ),
    )

    assert result.version.id == new_version_id
    assert result.version.derived_from_version_id == version_id
    versions.create.assert_awaited_once()
    locks.upsert.assert_awaited_once()
    saved_lock = locks.upsert.call_args.kwargs["lock"]
    assert saved_lock.draft_head_id == new_version_id
    assert saved_lock.locked_by_user_id == actor.id
    assert uow.entered is True
    assert uow.exited is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_draft_version_requires_active_draft_lock(now: datetime) -> None:
    actor = make_user(role=Role.CONTRIBUTOR, user_id=uuid4())
    tool_id = uuid4()
    version_id = uuid4()
    previous = make_tool_version(
        tool_id=tool_id,
        version_id=version_id,
        version_number=1,
        state=VersionState.DRAFT,
        created_by_user_id=actor.id,
        now=now,
    )

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = previous
    versions.list_for_tool.return_value = [previous]
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    maintainers.is_maintainer.return_value = True

    settings = Mock(spec=Settings)
    settings.DRAFT_LOCK_TTL_SECONDS = 600

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = uuid4()

    locks = AsyncMock(spec=DraftLockRepositoryProtocol)
    locks.get_for_tool.return_value = None

    handler = SaveDraftVersionHandler(
        settings=settings,
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        locks=locks,
        clock=clock,
        id_generator=id_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=SaveDraftVersionCommand(
                version_id=version_id,
                entrypoint="run_tool",
                source_code="print('new')",
                change_summary=None,
                expected_parent_version_id=version_id,
            ),
        )

    assert exc_info.value.code is ErrorCode.CONFLICT
    versions.create.assert_not_called()
