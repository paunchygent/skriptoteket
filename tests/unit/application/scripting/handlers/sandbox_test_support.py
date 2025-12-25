"""Shared test utilities for sandbox handler tests (ADR-0038)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

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
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class FakeUow(UnitOfWorkProtocol):
    """Fake UoW that tracks context manager usage."""

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


def make_tool_version(
    *,
    version_id: UUID | None = None,
    tool_id: UUID | None = None,
    now: datetime,
    created_by_user_id: UUID,
    state: VersionState = VersionState.DRAFT,
    version_number: int = 1,
) -> ToolVersion:
    """Create a ToolVersion for testing."""
    source_code = "def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>ok</p>'\n"
    entrypoint = "run_tool"
    return ToolVersion(
        id=version_id or uuid4(),
        tool_id=tool_id or uuid4(),
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


def make_tool_session(
    *,
    session_id: UUID | None = None,
    tool_id: UUID,
    user_id: UUID,
    context: str,
    now: datetime,
    state: dict[str, object] | None = None,
    state_rev: int = 0,
) -> ToolSession:
    """Create a ToolSession for testing."""
    return ToolSession(
        id=session_id or uuid4(),
        tool_id=tool_id,
        user_id=user_id,
        context=context,
        state={} if state is None else state,
        state_rev=state_rev,
        created_at=now,
        updated_at=now,
    )


def make_tool_run(
    *,
    run_id: UUID | None = None,
    tool_id: UUID,
    version_id: UUID,
    requested_by_user_id: UUID,
    now: datetime,
    ui_payload: UiPayloadV2 | None = None,
    context: RunContext = RunContext.SANDBOX,
) -> ToolRun:
    """Create a ToolRun for testing."""
    return ToolRun(
        id=run_id or uuid4(),
        tool_id=tool_id,
        version_id=version_id,
        requested_by_user_id=requested_by_user_id,
        context=context,
        status=RunStatus.SUCCEEDED,
        started_at=now,
        finished_at=now,
        workdir_path="/tmp/run",
        input_filename="action.json",
        input_size_bytes=0,
        input_manifest=InputManifest(files=[InputFileEntry(name="action.json", bytes=0)]),
        html_output=None,
        stdout="",
        stderr="",
        error_summary=None,
        artifacts_manifest={"artifacts": []},
        ui_payload=ui_payload,
    )


def make_ui_payload_with_next_actions() -> UiPayloadV2:
    """Create a UiPayloadV2 with next_actions for testing multi-step tools."""
    return UiPayloadV2(
        next_actions=[
            UiFormAction(action_id="next_step", label="Continue", fields=[]),
        ],
    )
