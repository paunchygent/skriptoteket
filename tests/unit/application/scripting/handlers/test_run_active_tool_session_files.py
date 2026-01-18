from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.commands import (
    ExecuteToolVersionResult,
    RunActiveToolCommand,
    SessionFilesMode,
)
from skriptoteket.application.scripting.handlers.run_active_tool import RunActiveToolHandler
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
from skriptoteket.domain.scripting.ui.contract_v2 import UiPayloadV2
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
    now: datetime,
    created_by_user_id,
) -> ToolVersion:
    source_code = "def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>ok</p>'\n"
    entrypoint = "run_tool"
    return ToolVersion(
        id=version_id,
        tool_id=tool_id,
        version_number=1,
        state=VersionState.ACTIVE,
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
    now: datetime,
    ui_payload: UiPayloadV2 | None = None,
) -> ToolRun:
    return ToolRun(
        id=run_id,
        tool_id=tool_id,
        version_id=version_id,
        requested_by_user_id=requested_by_user_id,
        context=RunContext.PRODUCTION,
        status=RunStatus.SUCCEEDED,
        requested_at=now,
        started_at=now,
        finished_at=now,
        workdir_path="/tmp/run",
        input_filename="test.txt",
        input_size_bytes=0,
        input_manifest=InputManifest(files=[InputFileEntry(name="test.txt", bytes=0)]),
        html_output="<p>ok</p>",
        stdout="",
        stderr="",
        error_summary=None,
        artifacts_manifest={"artifacts": []},
        ui_payload=ui_payload,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_active_tool_reuses_session_files_when_requested(now: datetime) -> None:
    actor = make_user(role=Role.USER)
    tool = make_tool(now=now, is_published=True)
    version_id = uuid4()
    tool = tool.model_copy(update={"active_version_id": version_id, "is_published": True})

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_slug.return_value = tool
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = make_tool_version(
        tool_id=tool.id,
        version_id=version_id,
        now=now,
        created_by_user_id=actor.id,
    )
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    session_files = AsyncMock(spec=SessionFileStorageProtocol)

    persisted_files = [("persist.txt", b"data")]
    session_files.get_files.return_value = persisted_files

    run = make_tool_run(
        run_id=uuid4(),
        tool_id=tool.id,
        version_id=version_id,
        requested_by_user_id=actor.id,
        now=now,
    )
    execute.handle.return_value = ExecuteToolVersionResult(run=run, normalized_state={})

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
            session_files_mode=SessionFilesMode.REUSE,
        ),
    )

    command = execute.handle.call_args.kwargs["command"]
    assert command.input_files == persisted_files
    session_files.get_files.assert_awaited_once()
    session_files.store_files.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_active_tool_clears_session_files_when_requested(now: datetime) -> None:
    actor = make_user(role=Role.USER)
    tool = make_tool(now=now, is_published=True)
    version_id = uuid4()
    tool = tool.model_copy(update={"active_version_id": version_id, "is_published": True})

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_slug.return_value = tool
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = make_tool_version(
        tool_id=tool.id,
        version_id=version_id,
        now=now,
        created_by_user_id=actor.id,
    )
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    session_files = AsyncMock(spec=SessionFileStorageProtocol)

    run = make_tool_run(
        run_id=uuid4(),
        tool_id=tool.id,
        version_id=version_id,
        requested_by_user_id=actor.id,
        now=now,
    )
    execute.handle.return_value = ExecuteToolVersionResult(run=run, normalized_state={})

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
            session_files_mode=SessionFilesMode.CLEAR,
        ),
    )

    command = execute.handle.call_args.kwargs["command"]
    assert command.input_files == []
    session_files.clear_session.assert_awaited_once()
    session_files.store_files.assert_not_called()
