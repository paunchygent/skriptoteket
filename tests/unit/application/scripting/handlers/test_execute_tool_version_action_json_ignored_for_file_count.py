from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.commands import ExecuteToolVersionCommand
from skriptoteket.application.scripting.handlers.execute_tool_version import (
    ExecuteToolVersionHandler,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.domain.scripting.models import (
    RunContext,
    RunStatus,
    ToolVersion,
    VersionState,
    compute_content_hash,
)
from skriptoteket.domain.scripting.tool_inputs import ToolInputStringField
from skriptoteket.domain.scripting.ui.contract_v2 import ToolUiContractV2Result
from skriptoteket.domain.scripting.ui.normalizer import DeterministicUiPayloadNormalizer
from skriptoteket.infrastructure.scripting_ui.backend_actions import NoopBackendActionProvider
from skriptoteket.infrastructure.scripting_ui.policy_provider import DefaultUiPolicyProvider
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.runner import ToolRunnerProtocol
from skriptoteket.protocols.scripting import (
    ToolRunRepositoryProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.identity_fixtures import make_user


class FakeUow(UnitOfWorkProtocol):
    async def __aenter__(self) -> UnitOfWorkProtocol:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_tool_version_ignores_action_json_for_input_schema_file_count(
    now: datetime,
) -> None:
    """Action runs always include action.json, even when the tool schema has no file field."""
    actor = make_user(role=Role.USER)
    tool_id = uuid4()
    version_id = uuid4()
    run_id = uuid4()

    source_code = "def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>ok</p>'\n"
    entrypoint = "run_tool"
    version = ToolVersion(
        id=version_id,
        tool_id=tool_id,
        version_number=1,
        state=VersionState.ACTIVE,
        source_code=source_code,
        entrypoint=entrypoint,
        content_hash=compute_content_hash(entrypoint=entrypoint, source_code=source_code),
        input_schema=[ToolInputStringField(name="title", label="Title")],
        derived_from_version_id=None,
        created_by_user_id=actor.id,
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

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = version

    runs = AsyncMock(spec=ToolRunRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    runner = AsyncMock(spec=ToolRunnerProtocol)
    runner.execute.return_value = ToolExecutionResult(
        status=RunStatus.SUCCEEDED,
        stdout="",
        stderr="",
        ui_result=ToolUiContractV2Result(
            status="succeeded",
            error_summary=None,
            outputs=[],
            next_actions=[],
            state=None,
            artifacts=[],
        ),
        artifacts_manifest=ArtifactsManifest(artifacts=[]),
    )

    ui_policy_provider = DefaultUiPolicyProvider()
    backend_actions = NoopBackendActionProvider()
    ui_normalizer = DeterministicUiPayloadNormalizer()

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = run_id

    handler = ExecuteToolVersionHandler(
        uow=uow,
        versions=versions,
        runs=runs,
        sessions=sessions,
        runner=runner,
        ui_policy_provider=ui_policy_provider,
        backend_actions=backend_actions,
        ui_normalizer=ui_normalizer,
        clock=clock,
        id_generator=id_generator,
    )

    await handler.handle(
        actor=actor,
        command=ExecuteToolVersionCommand(
            tool_id=tool_id,
            version_id=version_id,
            context=RunContext.PRODUCTION,
            input_files=[("action.json", b"{}")],
            input_values={},
        ),
    )

    runner.execute.assert_awaited_once()
