from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.domain.scripting.models import RunStatus
from skriptoteket.domain.scripting.ui.contract_v2 import ToolUiContractV2Result, UiFormAction
from skriptoteket.protocols.execution_queue import ToolRunJobClaim
from skriptoteket.workers.execution_queue.processor import process_claim
from tests.unit.workers.execution_queue_job_processor_test_support import make_harness


def _success_result(*, stdout: str = "ok") -> ToolExecutionResult:
    return ToolExecutionResult(
        status=RunStatus.SUCCEEDED,
        stdout=stdout,
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


def _interactive_result(
    *,
    state: dict[str, object] | None,
) -> ToolExecutionResult:
    return ToolExecutionResult(
        status=RunStatus.SUCCEEDED,
        stdout="ok",
        stderr="",
        ui_result=ToolUiContractV2Result(
            status="succeeded",
            error_summary=None,
            outputs=[],
            next_actions=[UiFormAction(action_id="next", label="Next")],
            state=state,
            artifacts=[],
        ),
        artifacts_manifest=ArtifactsManifest(artifacts=[]),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_claim_adoption_missing_container_requeues_without_finalizing() -> None:
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    h = await make_harness(
        now=now,
        worker_id="worker-1",
        attempts=1,
        max_attempts=3,
        execute_result=_success_result(stdout=""),
        adopt_result=None,
    )

    await process_claim(
        container=h.container,
        service_name="test",
        worker_id=h.worker_id,
        queue="default",
        claim=ToolRunJobClaim(job=h.job, is_adoption=True),
        lease_ttl=timedelta(seconds=30),
        heartbeat_interval=60.0,
        adopt_missing_backoff_seconds=10,
        runner=h.runner,
        runner_adoption=h.runner_adoption,
        run_inputs=h.run_inputs,
        promotion_applier=h.promotion_applier,
        ui_policy_provider=h.ui_policy_provider,
        backend_actions_provider=h.backend_actions_provider,
        ui_normalizer=h.ui_normalizer,
        clock=h.clock,
        id_generator=h.id_generator,
        sleeper=h.sleeper,
    )

    assert h.runner_adoption.called is True
    assert h.runner.called is False
    assert h.run_inputs.deleted == []

    job_after = await h.jobs.get_by_run_id(run_id=h.run_id)
    assert job_after is not None
    assert job_after.status is RunStatus.QUEUED
    assert job_after.locked_by is None
    assert job_after.locked_until is None
    assert job_after.last_error is not None
    assert job_after.available_at >= now


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_claim_adoption_missing_container_exhausted_attempts_finalizes_failed() -> (
    None
):
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    h = await make_harness(
        now=now,
        worker_id="worker-1",
        attempts=2,
        max_attempts=2,
        execute_result=_success_result(stdout=""),
        adopt_result=None,
    )

    await process_claim(
        container=h.container,
        service_name="test",
        worker_id=h.worker_id,
        queue="default",
        claim=ToolRunJobClaim(job=h.job, is_adoption=True),
        lease_ttl=timedelta(seconds=30),
        heartbeat_interval=60.0,
        adopt_missing_backoff_seconds=10,
        runner=h.runner,
        runner_adoption=h.runner_adoption,
        run_inputs=h.run_inputs,
        promotion_applier=h.promotion_applier,
        ui_policy_provider=h.ui_policy_provider,
        backend_actions_provider=h.backend_actions_provider,
        ui_normalizer=h.ui_normalizer,
        clock=h.clock,
        id_generator=h.id_generator,
        sleeper=h.sleeper,
    )

    assert h.runner_adoption.called is True
    assert h.runner.called is False
    assert h.run_inputs.deleted == [h.run_id]

    run_after = await h.runs.get_by_id(run_id=h.run_id)
    assert run_after is not None
    assert run_after.status is RunStatus.FAILED
    assert run_after.finished_at == now

    job_after = await h.jobs.get_by_run_id(run_id=h.run_id)
    assert job_after is not None
    assert job_after.status is RunStatus.FAILED
    assert job_after.finished_at == now
    assert job_after.locked_by is None
    assert job_after.locked_until is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_claim_non_adoption_runner_success_finalizes_and_deletes_inputs() -> None:
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    h = await make_harness(
        now=now,
        worker_id="worker-1",
        attempts=1,
        max_attempts=3,
        execute_result=_success_result(stdout="ok"),
        adopt_result=None,
        input_files=[("input.txt", b"input")],
    )

    await process_claim(
        container=h.container,
        service_name="test",
        worker_id=h.worker_id,
        queue="default",
        claim=ToolRunJobClaim(job=h.job, is_adoption=False),
        lease_ttl=timedelta(seconds=30),
        heartbeat_interval=60.0,
        adopt_missing_backoff_seconds=10,
        runner=h.runner,
        runner_adoption=h.runner_adoption,
        run_inputs=h.run_inputs,
        promotion_applier=h.promotion_applier,
        ui_policy_provider=h.ui_policy_provider,
        backend_actions_provider=h.backend_actions_provider,
        ui_normalizer=h.ui_normalizer,
        clock=h.clock,
        id_generator=h.id_generator,
        sleeper=h.sleeper,
    )

    assert h.runner.called is True
    assert h.runner_adoption.called is False
    assert h.run_inputs.deleted == [h.run_id]

    run_after = await h.runs.get_by_id(run_id=h.run_id)
    assert run_after is not None
    assert run_after.status is RunStatus.SUCCEEDED
    assert run_after.finished_at == now

    job_after = await h.jobs.get_by_run_id(run_id=h.run_id)
    assert job_after is not None
    assert job_after.status is RunStatus.SUCCEEDED
    assert job_after.finished_at == now


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_claim_persists_interactive_state_to_run_session_context() -> None:
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    h = await make_harness(
        now=now,
        worker_id="worker-1",
        attempts=1,
        max_attempts=3,
        execute_result=_interactive_result(state=None),  # state omitted/null -> NoChange
        adopt_result=None,
        session_context="testyta",
        session_state={"full_name": "Ada Lovelace"},
        session_state_rev=0,
    )

    await process_claim(
        container=h.container,
        service_name="test",
        worker_id=h.worker_id,
        queue="default",
        claim=ToolRunJobClaim(job=h.job, is_adoption=False),
        lease_ttl=timedelta(seconds=30),
        heartbeat_interval=60.0,
        adopt_missing_backoff_seconds=10,
        runner=h.runner,
        runner_adoption=h.runner_adoption,
        run_inputs=h.run_inputs,
        promotion_applier=h.promotion_applier,
        ui_policy_provider=h.ui_policy_provider,
        backend_actions_provider=h.backend_actions_provider,
        ui_normalizer=h.ui_normalizer,
        clock=h.clock,
        id_generator=h.id_generator,
        sleeper=h.sleeper,
    )

    assert h.sessions.update_calls == [
        {
            "tool_id": h.tool_id,
            "user_id": h.actor.id,
            "context": "testyta",
            "expected_state_rev": 0,
            "state": {"full_name": "Ada Lovelace"},
        }
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_claim_state_clear_overwrites_existing_state() -> None:
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    h = await make_harness(
        now=now,
        worker_id="worker-1",
        attempts=1,
        max_attempts=3,
        execute_result=_interactive_result(state={}),  # explicit {} -> Clear
        adopt_result=None,
        session_context="default",
        session_state={"full_name": "Ada Lovelace"},
        session_state_rev=2,
    )

    await process_claim(
        container=h.container,
        service_name="test",
        worker_id=h.worker_id,
        queue="default",
        claim=ToolRunJobClaim(job=h.job, is_adoption=False),
        lease_ttl=timedelta(seconds=30),
        heartbeat_interval=60.0,
        adopt_missing_backoff_seconds=10,
        runner=h.runner,
        runner_adoption=h.runner_adoption,
        run_inputs=h.run_inputs,
        promotion_applier=h.promotion_applier,
        ui_policy_provider=h.ui_policy_provider,
        backend_actions_provider=h.backend_actions_provider,
        ui_normalizer=h.ui_normalizer,
        clock=h.clock,
        id_generator=h.id_generator,
        sleeper=h.sleeper,
    )

    assert h.sessions.update_calls == [
        {
            "tool_id": h.tool_id,
            "user_id": h.actor.id,
            "context": "default",
            "expected_state_rev": 2,
            "state": {},
        }
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_claim_session_persistence_failure_marks_run_and_job_failed() -> None:
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    h = await make_harness(
        now=now,
        worker_id="worker-1",
        attempts=1,
        max_attempts=3,
        execute_result=_interactive_result(state={"step": "one"}),
        adopt_result=None,
        session_context="default",
        fail_session_update=True,
    )

    await process_claim(
        container=h.container,
        service_name="test",
        worker_id=h.worker_id,
        queue="default",
        claim=ToolRunJobClaim(job=h.job, is_adoption=False),
        lease_ttl=timedelta(seconds=30),
        heartbeat_interval=60.0,
        adopt_missing_backoff_seconds=10,
        runner=h.runner,
        runner_adoption=h.runner_adoption,
        run_inputs=h.run_inputs,
        promotion_applier=h.promotion_applier,
        ui_policy_provider=h.ui_policy_provider,
        backend_actions_provider=h.backend_actions_provider,
        ui_normalizer=h.ui_normalizer,
        clock=h.clock,
        id_generator=h.id_generator,
        sleeper=h.sleeper,
    )

    run_after = await h.runs.get_by_id(run_id=h.run_id)
    assert run_after is not None
    assert run_after.status is RunStatus.FAILED
    assert run_after.error_summary == "Execution failed (session state persistence error)."
    assert run_after.ui_payload is not None
    assert run_after.ui_payload.next_actions == []

    job_after = await h.jobs.get_by_run_id(run_id=h.run_id)
    assert job_after is not None
    assert job_after.status is RunStatus.FAILED
    assert job_after.last_error == "Session state persistence error."
