from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.scripting.commands import (
    ExecuteToolVersionCommand,
    ExecuteToolVersionResult,
)
from skriptoteket.application.scripting.handlers.get_interactive_session_state import (
    GetSessionStateHandler,
)
from skriptoteket.application.scripting.handlers.get_tool_run import GetRunHandler
from skriptoteket.application.scripting.handlers.list_run_artifacts import ListArtifactsHandler
from skriptoteket.application.scripting.handlers.start_action import StartActionHandler
from skriptoteket.application.scripting.interactive_tools import (
    GetRunQuery,
    GetSessionStateQuery,
    ListArtifactsQuery,
    StartActionCommand,
)
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    curated_app_tool_id,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.domain.scripting.input_files import InputManifest
from skriptoteket.domain.scripting.models import RunContext, RunStatus, ToolRun
from skriptoteket.domain.scripting.tool_sessions import ToolSession
from skriptoteket.domain.scripting.ui.contract_v2 import ToolUiContractV2Result, UiPayloadV2
from skriptoteket.domain.scripting.ui.normalization import UiNormalizationResult
from skriptoteket.domain.scripting.ui.policy import UiPolicyProfileId, get_ui_policy
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import (
    CuratedAppExecutorProtocol,
    CuratedAppRegistryProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import (
    ExecuteToolVersionHandlerProtocol,
    ToolRunRepositoryProtocol,
)
from skriptoteket.protocols.scripting_ui import (
    BackendActionProviderProtocol,
    UiPayloadNormalizerProtocol,
    UiPolicyProviderProtocol,
)
from skriptoteket.protocols.session_files import SessionFileStorageProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.catalog_fixtures import make_tool
from tests.fixtures.identity_fixtures import make_user


class FakeUow(UnitOfWorkProtocol):
    def __init__(self) -> None:
        self.active = False
        self.enter_count = 0
        self.exit_count = 0

    async def __aenter__(self) -> UnitOfWorkProtocol:
        self.active = True
        self.enter_count += 1
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.active = False
        self.exit_count += 1


def make_tool_run(
    *,
    run_id: UUID,
    tool_id: UUID,
    version_id: UUID,
    requested_by_user_id: UUID,
    now: datetime,
    artifacts_manifest: dict[str, object] | None = None,
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
        input_filename=None,
        input_size_bytes=0,
        input_manifest=InputManifest(),
        html_output=None,
        stdout="",
        stderr="",
        error_summary=None,
        artifacts_manifest=artifacts_manifest or {"artifacts": []},
        ui_payload=None,
    )


def make_tool_session(
    *,
    session_id: UUID,
    tool_id: UUID,
    user_id: UUID,
    context: str,
    now: datetime,
    state: dict[str, object] | None = None,
    state_rev: int = 0,
) -> ToolSession:
    return ToolSession(
        id=session_id,
        tool_id=tool_id,
        user_id=user_id,
        context=context,
        state={} if state is None else state,
        state_rev=state_rev,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_action_executes_with_session_state_and_updates_state_rev(
    now: datetime,
) -> None:
    actor = make_user(user_id=uuid4())
    tool_id = uuid4()
    active_version_id = uuid4()
    session_id = uuid4()

    tool = make_tool(now=now, is_published=True, tool_id=tool_id).model_copy(
        update={"active_version_id": active_version_id}
    )

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool

    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    sessions.get_or_create.return_value = make_tool_session(
        session_id=session_id,
        tool_id=tool_id,
        user_id=actor.id,
        context="default",
        now=now,
        state={"step": "one"},
        state_rev=3,
    )
    sessions.update_state.return_value = make_tool_session(
        session_id=session_id,
        tool_id=tool_id,
        user_id=actor.id,
        context="default",
        now=now,
        state={"step": "two"},
        state_rev=4,
    )

    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)
    run = make_tool_run(
        run_id=uuid4(),
        tool_id=tool_id,
        version_id=active_version_id,
        requested_by_user_id=actor.id,
        now=now,
    )

    session_files = AsyncMock(spec=SessionFileStorageProtocol)
    session_files.get_files.return_value = [("original.txt", b"hello")]

    async def _execute(
        *,
        actor: object,
        command: ExecuteToolVersionCommand,
    ) -> ExecuteToolVersionResult:
        del actor
        assert uow.active is False
        assert ("original.txt", b"hello") in command.input_files
        assert command.action_payload == {
            "action_id": "confirm_flags",
            "input": {"notify_guardians": True},
            "state": {"step": "one"},
        }
        return ExecuteToolVersionResult(run=run, normalized_state={"step": "two"})

    execute.handle.side_effect = _execute

    curated_apps = Mock(spec=CuratedAppRegistryProtocol)
    curated_apps.get_by_tool_id.return_value = None
    curated_executor = AsyncMock(spec=CuratedAppExecutorProtocol)
    runs_repo = AsyncMock(spec=ToolRunRepositoryProtocol)
    ui_policy_provider = AsyncMock(spec=UiPolicyProviderProtocol)
    backend_actions = AsyncMock(spec=BackendActionProviderProtocol)
    ui_normalizer = Mock(spec=UiPayloadNormalizerProtocol)
    clock = Mock(spec=ClockProtocol)

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = session_id

    handler = StartActionHandler(
        uow=uow,
        tools=tools,
        curated_apps=curated_apps,
        curated_executor=curated_executor,
        sessions=sessions,
        runs=runs_repo,
        execute=execute,
        ui_policy_provider=ui_policy_provider,
        backend_actions=backend_actions,
        ui_normalizer=ui_normalizer,
        clock=clock,
        id_generator=id_generator,
        session_files=session_files,
    )

    result = await handler.handle(
        actor=actor,
        command=StartActionCommand(
            tool_id=tool_id,
            context="default",
            action_id="confirm_flags",
            input={"notify_guardians": True},
            expected_state_rev=3,
        ),
    )

    assert result.run_id == run.id
    assert result.state_rev == 4
    assert uow.enter_count == 2
    assert uow.exit_count == 2
    sessions.update_state.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_action_rejects_state_rev_conflict_without_executing(now: datetime) -> None:
    actor = make_user(user_id=uuid4())
    tool_id = uuid4()
    active_version_id = uuid4()
    session_id = uuid4()

    tool = make_tool(now=now, is_published=True, tool_id=tool_id).model_copy(
        update={"active_version_id": active_version_id}
    )

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool

    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    sessions.get_or_create.return_value = make_tool_session(
        session_id=session_id,
        tool_id=tool_id,
        user_id=actor.id,
        context="default",
        now=now,
        state={"step": "one"},
        state_rev=2,
    )

    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = session_id

    curated_apps = Mock(spec=CuratedAppRegistryProtocol)
    curated_apps.get_by_tool_id.return_value = None
    curated_executor = AsyncMock(spec=CuratedAppExecutorProtocol)
    runs_repo = AsyncMock(spec=ToolRunRepositoryProtocol)
    ui_policy_provider = AsyncMock(spec=UiPolicyProviderProtocol)
    backend_actions = AsyncMock(spec=BackendActionProviderProtocol)
    ui_normalizer = Mock(spec=UiPayloadNormalizerProtocol)
    clock = Mock(spec=ClockProtocol)
    session_files = AsyncMock(spec=SessionFileStorageProtocol)

    handler = StartActionHandler(
        uow=uow,
        tools=tools,
        curated_apps=curated_apps,
        curated_executor=curated_executor,
        sessions=sessions,
        runs=runs_repo,
        execute=execute,
        ui_policy_provider=ui_policy_provider,
        backend_actions=backend_actions,
        ui_normalizer=ui_normalizer,
        clock=clock,
        id_generator=id_generator,
        session_files=session_files,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=StartActionCommand(
                tool_id=tool_id,
                context="default",
                action_id="confirm_flags",
                input={},
                expected_state_rev=3,
            ),
        )

    assert exc_info.value.code is ErrorCode.CONFLICT
    execute.handle.assert_not_called()
    sessions.update_state.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_action_executes_curated_app_without_tool_version(now: datetime) -> None:
    actor = make_user(user_id=uuid4(), role=Role.USER)

    app_id = "demo.test"
    tool_id = curated_app_tool_id(app_id=app_id)
    session_id = uuid4()
    run_id = uuid4()

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = None

    curated_app = CuratedAppDefinition(
        app_id=app_id,
        tool_id=tool_id,
        app_version="test",
        title="Test app",
        summary=None,
        min_role=Role.USER,
        placements=[CuratedAppPlacement(profession_slug="larare", category_slug="ovrigt")],
    )
    curated_apps = Mock(spec=CuratedAppRegistryProtocol)
    curated_apps.get_by_tool_id.return_value = curated_app

    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    sessions.get_or_create.return_value = make_tool_session(
        session_id=session_id,
        tool_id=tool_id,
        user_id=actor.id,
        context="default",
        now=now,
        state={},
        state_rev=0,
    )
    sessions.update_state.return_value = make_tool_session(
        session_id=session_id,
        tool_id=tool_id,
        user_id=actor.id,
        context="default",
        now=now,
        state={"count": 2},
        state_rev=1,
    )

    raw_result = ToolUiContractV2Result(
        status="succeeded",
        error_summary=None,
        outputs=[],
        next_actions=[],
        state={"count": 2},
        artifacts=[],
    )

    curated_executor = AsyncMock(spec=CuratedAppExecutorProtocol)
    artifacts_manifest = ArtifactsManifest(
        artifacts=[
            {
                "artifact_id": "output_counter_txt",
                "path": "output/counter.txt",
                "bytes": 12,
            }
        ]
    )
    curated_executor.execute_action.return_value = ToolExecutionResult(
        status=RunStatus.SUCCEEDED,
        stdout="",
        stderr="",
        ui_result=raw_result,
        artifacts_manifest=artifacts_manifest,
    )

    runs_repo = AsyncMock(spec=ToolRunRepositoryProtocol)
    runs_repo.create.return_value = make_tool_run(
        run_id=run_id,
        tool_id=tool_id,
        version_id=uuid4(),
        requested_by_user_id=actor.id,
        now=now,
    )
    runs_repo.update.return_value = make_tool_run(
        run_id=run_id,
        tool_id=tool_id,
        version_id=uuid4(),
        requested_by_user_id=actor.id,
        now=now,
    )

    ui_policy_provider = AsyncMock(spec=UiPolicyProviderProtocol)
    ui_policy_provider.get_profile_id_for_curated_app.return_value = UiPolicyProfileId.CURATED
    ui_policy_provider.get_policy.return_value = get_ui_policy(profile_id=UiPolicyProfileId.CURATED)

    backend_actions = AsyncMock(spec=BackendActionProviderProtocol)
    backend_actions.list_backend_actions.return_value = []

    ui_normalizer = Mock(spec=UiPayloadNormalizerProtocol)
    ui_normalizer.normalize.return_value = UiNormalizationResult(
        ui_payload=UiPayloadV2(outputs=[], next_actions=[]),
        state={"count": 2},
    )

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.side_effect = [session_id, run_id]

    session_files = AsyncMock(spec=SessionFileStorageProtocol)

    handler = StartActionHandler(
        uow=uow,
        tools=tools,
        curated_apps=curated_apps,
        curated_executor=curated_executor,
        sessions=sessions,
        runs=runs_repo,
        execute=execute,
        ui_policy_provider=ui_policy_provider,
        backend_actions=backend_actions,
        ui_normalizer=ui_normalizer,
        clock=clock,
        id_generator=id_generator,
        session_files=session_files,
    )

    result = await handler.handle(
        actor=actor,
        command=StartActionCommand(
            tool_id=tool_id,
            context="default",
            action_id="start",
            input={},
            expected_state_rev=0,
        ),
    )

    assert result.run_id == run_id
    assert result.state_rev == 1
    execute.handle.assert_not_called()

    created_run = runs_repo.create.call_args.kwargs["run"]
    assert created_run.tool_id == tool_id
    assert created_run.source_kind.value == "curated_app"
    assert created_run.version_id is None
    assert created_run.curated_app_id == app_id
    assert created_run.curated_app_version == "test"

    curated_executor.execute_action.assert_awaited_once()
    assert curated_executor.execute_action.call_args.kwargs["run_id"] == run_id

    updated_run = runs_repo.update.call_args.kwargs["run"]
    assert updated_run.artifacts_manifest == artifacts_manifest.model_dump()

    sessions.update_state.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_session_state_returns_latest_run_id(now: datetime) -> None:
    actor = make_user(user_id=uuid4())
    tool_id = uuid4()
    active_version_id = uuid4()
    session_id = uuid4()
    run_id = uuid4()

    tool = make_tool(now=now, is_published=True, tool_id=tool_id).model_copy(
        update={"active_version_id": active_version_id}
    )

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool

    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    sessions.get_or_create.return_value = make_tool_session(
        session_id=session_id,
        tool_id=tool_id,
        user_id=actor.id,
        context="default",
        now=now,
        state={"step": "one"},
        state_rev=0,
    )

    runs = AsyncMock(spec=ToolRunRepositoryProtocol)
    runs.get_latest_for_user_and_tool.return_value = make_tool_run(
        run_id=run_id,
        tool_id=tool_id,
        version_id=active_version_id,
        requested_by_user_id=actor.id,
        now=now,
    )

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = session_id

    curated_apps = Mock(spec=CuratedAppRegistryProtocol)
    curated_apps.get_by_tool_id.return_value = None

    handler = GetSessionStateHandler(
        uow=uow,
        tools=tools,
        curated_apps=curated_apps,
        sessions=sessions,
        runs=runs,
        id_generator=id_generator,
    )

    result = await handler.handle(
        actor=actor,
        query=GetSessionStateQuery(tool_id=tool_id, context="default"),
    )

    assert result.session_state.tool_id == tool_id
    assert result.session_state.context == "default"
    assert result.session_state.state_rev == 0
    assert result.session_state.latest_run_id == run_id
    runs.get_latest_for_user_and_tool.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_run_returns_artifact_download_urls(now: datetime) -> None:
    actor = make_user(user_id=uuid4())
    tool_id = uuid4()
    version_id = uuid4()
    run_id = uuid4()

    run = make_tool_run(
        run_id=run_id,
        tool_id=tool_id,
        version_id=version_id,
        requested_by_user_id=actor.id,
        now=now,
        artifacts_manifest={
            "artifacts": [
                {
                    "artifact_id": "output_report_pdf",
                    "path": "output/report.pdf",
                    "bytes": 123,
                }
            ]
        },
    )

    uow = FakeUow()
    runs = AsyncMock(spec=ToolRunRepositoryProtocol)
    runs.get_by_id.return_value = run

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = make_tool(
        now=now,
        is_published=True,
        tool_id=tool_id,
    )
    curated_apps = Mock(spec=CuratedAppRegistryProtocol)
    curated_apps.get_by_tool_id.return_value = None

    handler = GetRunHandler(uow=uow, runs=runs, tools=tools, curated_apps=curated_apps)

    result = await handler.handle(actor=actor, query=GetRunQuery(run_id=run_id))

    assert result.run.tool_id == tool_id
    assert result.run.tool_slug == "demo-tool"
    assert result.run.tool_title == "Demo tool"
    assert result.run.run_id == run_id
    assert result.run.status is RunStatus.SUCCEEDED
    expected_url = f"/api/v1/runs/{run_id}/artifacts/output_report_pdf"
    assert result.run.artifacts[0].download_url == expected_url


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_artifacts_raises_not_found_for_other_user(now: datetime) -> None:
    actor = make_user(user_id=uuid4())
    tool_id = uuid4()
    version_id = uuid4()
    run_id = uuid4()

    run = make_tool_run(
        run_id=run_id,
        tool_id=tool_id,
        version_id=version_id,
        requested_by_user_id=uuid4(),
        now=now,
    )

    uow = FakeUow()
    runs = AsyncMock(spec=ToolRunRepositoryProtocol)
    runs.get_by_id.return_value = run

    handler = ListArtifactsHandler(uow=uow, runs=runs)

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, query=ListArtifactsQuery(run_id=run_id))

    assert exc_info.value.code is ErrorCode.NOT_FOUND
