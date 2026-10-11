from __future__ import annotations

from datetime import datetime

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
from skriptoteket.protocols.uow import UnitOfWorkProtocol


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
        content_hash=compute_content_hash(
            entrypoint=entrypoint,
            source_code=source_code,
            bundle_files={},
        ),
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
        session_context="default",
        status=RunStatus.SUCCEEDED,
        requested_at=now,
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
