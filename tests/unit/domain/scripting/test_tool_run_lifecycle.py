from datetime import datetime, timezone
from uuid import uuid4

import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.input_files import InputFileEntry, InputManifest
from skriptoteket.domain.scripting.models import (
    RunContext,
    RunStatus,
    finish_run,
    start_tool_version_run,
)
from skriptoteket.domain.scripting.ui.contract_v2 import UiPayloadV2


def test_start_and_finish_tool_run() -> None:
    now = datetime.now(timezone.utc)
    run_id = uuid4()

    # Start
    run = start_tool_version_run(
        run_id=run_id,
        tool_id=uuid4(),
        version_id=uuid4(),
        context=RunContext.SANDBOX,
        requested_by_user_id=uuid4(),
        session_context="default",
        workdir_path="/tmp/run",
        input_filename="input.txt",
        input_size_bytes=100,
        input_manifest=InputManifest(files=[InputFileEntry(name="input.txt", bytes=100)]),
        now=now,
    )

    assert run.status == RunStatus.RUNNING
    assert run.started_at == now

    # Finish
    finished = finish_run(
        run=run,
        status=RunStatus.SUCCEEDED,
        now=now,
        stdout="ok",
        stderr=None,
        artifacts_manifest={},
        error_summary=None,
        ui_payload=UiPayloadV2(outputs=[], next_actions=[]),
    )

    assert finished.status == RunStatus.SUCCEEDED
    assert finished.finished_at == now


def test_start_tool_run_validation() -> None:
    now = datetime.now(timezone.utc)

    # Empty workdir
    with pytest.raises(DomainError) as exc:
        start_tool_version_run(
            run_id=uuid4(),
            tool_id=uuid4(),
            version_id=uuid4(),
            context=RunContext.SANDBOX,
            requested_by_user_id=uuid4(),
            session_context="default",
            workdir_path="  ",
            input_filename="input.txt",
            input_size_bytes=100,
            input_manifest=InputManifest(files=[InputFileEntry(name="input.txt", bytes=100)]),
            now=now,
        )
    assert exc.value.code == ErrorCode.VALIDATION_ERROR

    # Empty input filename
    with pytest.raises(DomainError) as exc:
        start_tool_version_run(
            run_id=uuid4(),
            tool_id=uuid4(),
            version_id=uuid4(),
            context=RunContext.SANDBOX,
            requested_by_user_id=uuid4(),
            session_context="default",
            workdir_path="/tmp/run",
            input_filename="  ",
            input_size_bytes=100,
            input_manifest=InputManifest(files=[InputFileEntry(name="input.txt", bytes=100)]),
            now=now,
        )
    assert exc.value.code == ErrorCode.VALIDATION_ERROR

    # Negative size
    with pytest.raises(DomainError) as exc:
        start_tool_version_run(
            run_id=uuid4(),
            tool_id=uuid4(),
            version_id=uuid4(),
            context=RunContext.SANDBOX,
            requested_by_user_id=uuid4(),
            session_context="default",
            workdir_path="/tmp/run",
            input_filename="input.txt",
            input_size_bytes=-1,
            input_manifest=InputManifest(files=[InputFileEntry(name="input.txt", bytes=100)]),
            now=now,
        )
    assert exc.value.code == ErrorCode.VALIDATION_ERROR


def test_finish_tool_run_validation() -> None:
    now = datetime.now(timezone.utc)

    run = start_tool_version_run(
        run_id=uuid4(),
        tool_id=uuid4(),
        version_id=uuid4(),
        context=RunContext.SANDBOX,
        requested_by_user_id=uuid4(),
        session_context="default",
        workdir_path="/tmp/run",
        input_filename="input.txt",
        input_size_bytes=100,
        input_manifest=InputManifest(files=[InputFileEntry(name="input.txt", bytes=100)]),
        now=now,
    )

    # 1. Fail if run already finished
    finished = finish_run(
        run=run,
        status=RunStatus.SUCCEEDED,
        now=now,
        stdout=None,
        stderr=None,
        artifacts_manifest={},
        error_summary=None,
        ui_payload=UiPayloadV2(outputs=[], next_actions=[]),
    )
    with pytest.raises(DomainError) as exc:
        finish_run(
            run=finished,
            status=RunStatus.FAILED,
            now=now,
            stdout=None,
            stderr=None,
            artifacts_manifest={},
            error_summary=None,
            ui_payload=UiPayloadV2(outputs=[], next_actions=[]),
        )
    assert exc.value.code == ErrorCode.CONFLICT

    # 2. Fail if new status is RUNNING
    with pytest.raises(DomainError) as exc:
        finish_run(
            run=run,
            status=RunStatus.RUNNING,  # Invalid
            now=now,
            stdout=None,
            stderr=None,
            artifacts_manifest={},
            error_summary=None,
            ui_payload=UiPayloadV2(outputs=[], next_actions=[]),
        )
    assert exc.value.code == ErrorCode.VALIDATION_ERROR

    # 3. Fail if finished_at before started_at
    past = datetime(2000, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(DomainError) as exc:
        finish_run(
            run=run,
            status=RunStatus.SUCCEEDED,
            now=past,
            stdout=None,
            stderr=None,
            artifacts_manifest={},
            error_summary=None,
            ui_payload=UiPayloadV2(outputs=[], next_actions=[]),
        )
    assert exc.value.code == ErrorCode.VALIDATION_ERROR
