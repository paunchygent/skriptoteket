from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.commands import (
    ExecuteToolVersionCommand,
    ExecuteToolVersionResult,
    RunActiveToolCommand,
)
from skriptoteket.application.scripting.handlers.run_active_tool import (
    RunActiveToolHandler,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.input_files import InputFileEntry, InputManifest
from skriptoteket.domain.scripting.models import (
    RunContext,
    RunStatus,
    ToolRun,
    ToolVersion,
    VersionState,
    compute_content_hash,
)
from skriptoteket.domain.scripting.tool_sessions import ToolSession
from skriptoteket.domain.scripting.ui.contract_v2 import UiFormAction, UiPayloadV2
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import (
    ExecuteToolVersionHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.session_files import SessionFileStorageProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
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
    tool_id,
    version_id,
    version_number: int,
    state: VersionState,
    created_by_user_id,
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


def make_tool_run(
    *,
    run_id,
    tool_id,
    version_id,
    requested_by_user_id,
    context: RunContext,
    now: datetime,
    ui_payload: UiPayloadV2 | None = None,
) -> ToolRun:
    return ToolRun(
        id=run_id,
        tool_id=tool_id,
        version_id=version_id,
        requested_by_user_id=requested_by_user_id,
        context=context,
        status=RunStatus.SUCCEEDED,
        started_at=now,
        finished_at=now,
        workdir_path="/tmp/run",
        input_filename="test.xlsx",
        input_size_bytes=0,
        input_manifest=InputManifest(files=[InputFileEntry(name="test.xlsx", bytes=0)]),
        html_output="<p>ok</p>",
        stdout="",
        stderr="",
        error_summary=None,
        artifacts_manifest={"artifacts": []},
        ui_payload=ui_payload,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_active_tool_raises_not_found_when_tool_missing(now: datetime) -> None:
    actor = make_user(role=Role.USER)

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_slug.return_value = None
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    session_files = AsyncMock(spec=SessionFileStorageProtocol)

    handler = RunActiveToolHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        execute=execute,
        sessions=sessions,
        id_generator=id_generator,
        session_files=session_files,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RunActiveToolCommand(
                tool_slug="nonexistent-tool",
                input_files=[("test.xlsx", b"test")],
            ),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert uow.entered is True
    assert uow.exited is True
    versions.get_by_id.assert_not_called()
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_active_tool_raises_not_found_when_tool_not_published(
    now: datetime,
) -> None:
    actor = make_user(role=Role.USER)
    tool = make_tool(now=now, is_published=False)

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_slug.return_value = tool
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    session_files = AsyncMock(spec=SessionFileStorageProtocol)

    handler = RunActiveToolHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        execute=execute,
        sessions=sessions,
        id_generator=id_generator,
        session_files=session_files,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RunActiveToolCommand(
                tool_slug=tool.slug,
                input_files=[("test.xlsx", b"test")],
            ),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert uow.entered is True
    assert uow.exited is True
    versions.get_by_id.assert_not_called()
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_active_tool_raises_not_found_when_no_active_version_id(
    now: datetime,
) -> None:
    actor = make_user(role=Role.USER)
    tool = make_tool(now=now, is_published=True)
    # Tool is published but has no active_version_id (default is None)

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_slug.return_value = tool
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    session_files = AsyncMock(spec=SessionFileStorageProtocol)

    handler = RunActiveToolHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        execute=execute,
        sessions=sessions,
        id_generator=id_generator,
        session_files=session_files,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RunActiveToolCommand(
                tool_slug=tool.slug,
                input_files=[("test.xlsx", b"test")],
            ),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert uow.entered is True
    assert uow.exited is True
    versions.get_by_id.assert_not_called()
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_active_tool_raises_not_found_when_version_missing(
    now: datetime,
) -> None:
    actor = make_user(role=Role.USER)
    active_version_id = uuid4()
    tool = make_tool(now=now, is_published=True).model_copy(
        update={"active_version_id": active_version_id}
    )

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_slug.return_value = tool
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = None
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    session_files = AsyncMock(spec=SessionFileStorageProtocol)

    handler = RunActiveToolHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        execute=execute,
        sessions=sessions,
        id_generator=id_generator,
        session_files=session_files,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RunActiveToolCommand(
                tool_slug=tool.slug,
                input_files=[("test.xlsx", b"test")],
            ),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert uow.entered is True
    assert uow.exited is True
    versions.get_by_id.assert_awaited_once_with(version_id=active_version_id)
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_active_tool_raises_not_found_when_version_not_active(
    now: datetime,
) -> None:
    actor = make_user(role=Role.USER)
    active_version_id = uuid4()
    tool = make_tool(now=now, is_published=True).model_copy(
        update={"active_version_id": active_version_id}
    )

    # Version exists but is not in ACTIVE state (data drift)
    version = make_tool_version(
        tool_id=tool.id,
        version_id=active_version_id,
        version_number=1,
        state=VersionState.DRAFT,  # Wrong state!
        created_by_user_id=uuid4(),
        now=now,
    )

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_slug.return_value = tool
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = version
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    session_files = AsyncMock(spec=SessionFileStorageProtocol)

    handler = RunActiveToolHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        execute=execute,
        sessions=sessions,
        id_generator=id_generator,
        session_files=session_files,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RunActiveToolCommand(
                tool_slug=tool.slug,
                input_files=[("test.xlsx", b"test")],
            ),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert uow.entered is True
    assert uow.exited is True
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_active_tool_success_returns_tool_run(now: datetime) -> None:
    actor = make_user(role=Role.USER)
    active_version_id = uuid4()
    tool = make_tool(now=now, is_published=True).model_copy(
        update={"active_version_id": active_version_id}
    )

    version = make_tool_version(
        tool_id=tool.id,
        version_id=active_version_id,
        version_number=1,
        state=VersionState.ACTIVE,
        created_by_user_id=uuid4(),
        now=now,
    )

    run = make_tool_run(
        run_id=uuid4(),
        tool_id=tool.id,
        version_id=version.id,
        requested_by_user_id=actor.id,
        context=RunContext.PRODUCTION,
        now=now,
    )

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_slug.return_value = tool
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = version
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)
    execute.handle.return_value = ExecuteToolVersionResult(run=run)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    session_files = AsyncMock(spec=SessionFileStorageProtocol)

    handler = RunActiveToolHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        execute=execute,
        sessions=sessions,
        id_generator=id_generator,
        session_files=session_files,
    )

    result = await handler.handle(
        actor=actor,
        command=RunActiveToolCommand(
            tool_slug=tool.slug,
            input_files=[("test.xlsx", b"test data")],
        ),
    )

    assert result.run.id == run.id
    assert result.run.context is RunContext.PRODUCTION

    # Verify execute was called with PRODUCTION context
    execute.handle.assert_awaited_once()
    call_args = execute.handle.call_args
    assert call_args.kwargs["actor"] == actor
    cmd = call_args.kwargs["command"]
    assert isinstance(cmd, ExecuteToolVersionCommand)
    assert cmd.tool_id == tool.id
    assert cmd.version_id == version.id
    assert cmd.context is RunContext.PRODUCTION
    assert cmd.input_files == [("test.xlsx", b"test data")]
    session_files.store_files.assert_awaited_once()

    assert uow.entered is True
    assert uow.exited is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_active_tool_persists_session_state_when_run_has_next_actions(
    now: datetime,
) -> None:
    actor = make_user(role=Role.USER)
    active_version_id = uuid4()
    tool = make_tool(now=now, is_published=True).model_copy(
        update={"active_version_id": active_version_id}
    )

    version = make_tool_version(
        tool_id=tool.id,
        version_id=active_version_id,
        version_number=1,
        state=VersionState.ACTIVE,
        created_by_user_id=uuid4(),
        now=now,
    )

    run = make_tool_run(
        run_id=uuid4(),
        tool_id=tool.id,
        version_id=version.id,
        requested_by_user_id=actor.id,
        context=RunContext.PRODUCTION,
        now=now,
        ui_payload=UiPayloadV2(next_actions=[UiFormAction(action_id="next", label="Next")]),
    )

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_slug.return_value = tool
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = version
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)
    execute.handle.return_value = ExecuteToolVersionResult(
        run=run, normalized_state={"step": "one"}
    )

    session_id = uuid4()
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    sessions.get_or_create.return_value = ToolSession(
        id=session_id,
        tool_id=tool.id,
        user_id=actor.id,
        context="default",
        state={},
        state_rev=0,
        created_at=now,
        updated_at=now,
    )
    sessions.update_state.return_value = ToolSession(
        id=session_id,
        tool_id=tool.id,
        user_id=actor.id,
        context="default",
        state={"step": "one"},
        state_rev=1,
        created_at=now,
        updated_at=now,
    )

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = session_id
    session_files = AsyncMock(spec=SessionFileStorageProtocol)

    handler = RunActiveToolHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        execute=execute,
        sessions=sessions,
        id_generator=id_generator,
        session_files=session_files,
    )

    await handler.handle(
        actor=actor,
        command=RunActiveToolCommand(
            tool_slug=tool.slug,
            input_files=[("input.txt", b"test")],
        ),
    )

    sessions.update_state.assert_awaited_once()
    update_kwargs = sessions.update_state.call_args.kwargs
    assert update_kwargs["tool_id"] == tool.id
    assert update_kwargs["user_id"] == actor.id
    assert update_kwargs["context"] == "default"
    assert update_kwargs["expected_state_rev"] == 0
    assert update_kwargs["state"] == {"step": "one"}
