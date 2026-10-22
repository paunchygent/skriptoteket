"""The execution worker runs N enrichment slots beside one tool-run loop."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide

from skriptoteket.config import Settings
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.domain.scripting.models import RunStatus
from skriptoteket.domain.scripting.ui.contract_v2 import ToolUiContractV2Result
from skriptoteket.domain.scripting.ui.normalizer import DeterministicUiPayloadNormalizer
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.promotions import PromotionApplierProtocol
from skriptoteket.protocols.run_inputs import RunInputStorageProtocol
from skriptoteket.protocols.runner import ToolRunnerAdoptionProtocol, ToolRunnerProtocol
from skriptoteket.protocols.scripting_ui import (
    BackendActionProviderProtocol,
    UiPayloadNormalizerProtocol,
    UiPolicyProviderProtocol,
)
from skriptoteket.protocols.sleeper import SleeperProtocol
from skriptoteket.workers import exam_answer_key_enrichment as enrichment_worker
from skriptoteket.workers import execution_queue_worker as worker
from tests.unit.workers.execution_queue_repository_fakes import FakeRunInputStorage
from tests.unit.workers.execution_queue_runtime_fakes import (
    FakeBackendActionProvider,
    FakeClock,
    FakeIdGenerator,
    FakePromotionApplier,
    FakeRunner,
    FakeRunnerAdoption,
    FakeSleeper,
    FakeUiPolicyProvider,
)

BASE_WORKER_ID = "worker-a"
SLOTS = 4


class RecordingEnrichmentLane:
    """Stands in for `process_next_answer_key_enrichment_job`, one call per slot step."""

    def __init__(self, *, first_step_barrier: asyncio.Barrier | None = None) -> None:
        self.worker_ids: list[str] = []
        self.active = 0
        self.peak = 0
        self._barrier = first_step_barrier
        self._seen: set[str] = set()

    async def __call__(
        self,
        *,
        container: AsyncContainer,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
        clock: object,
        enrichment_enabled: bool = True,
    ) -> bool:
        del container, now, lease_ttl, clock, enrichment_enabled
        self.worker_ids.append(worker_id)
        self.active += 1
        self.peak = max(self.peak, self.active)
        try:
            if self._barrier is not None and worker_id not in self._seen:
                self._seen.add(worker_id)
                await self._barrier.wait()
            await asyncio.sleep(0)
            return False
        finally:
            self.active -= 1


def _succeeded_result() -> ToolExecutionResult:
    return ToolExecutionResult(
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


class WorkerRuntimeProvider(Provider):
    """The worker-process dependencies the tool-run loop resolves, as protocol-bound doubles."""

    scope = Scope.APP

    @provide
    def clock(self) -> ClockProtocol:
        return FakeClock(now=datetime(2026, 10, 22, 12))

    @provide
    def sleeper(self) -> SleeperProtocol:
        return FakeSleeper()

    @provide
    def runner(self) -> ToolRunnerProtocol:
        return FakeRunner(result=_succeeded_result())

    @provide
    def runner_adoption(self) -> ToolRunnerAdoptionProtocol:
        return FakeRunnerAdoption(result=None)

    @provide
    def run_inputs(self) -> RunInputStorageProtocol:
        return FakeRunInputStorage()

    @provide
    def promotion_applier(self) -> PromotionApplierProtocol:
        return FakePromotionApplier()

    @provide
    def ui_policy_provider(self) -> UiPolicyProviderProtocol:
        return FakeUiPolicyProvider()

    @provide
    def backend_actions_provider(self) -> BackendActionProviderProtocol:
        return FakeBackendActionProvider()

    @provide
    def ui_normalizer(self) -> UiPayloadNormalizerProtocol:
        return DeterministicUiPayloadNormalizer()

    @provide
    def id_generator(self) -> IdGeneratorProtocol:
        return FakeIdGenerator()


def _runtime_container(_settings: Settings) -> AsyncContainer:
    return make_async_container(WorkerRuntimeProvider())


@pytest.fixture
def tool_run_boundary(monkeypatch: pytest.MonkeyPatch) -> tuple[AsyncMock, AsyncMock]:
    claim = AsyncMock(return_value=None)
    clear = AsyncMock(return_value=0)
    monkeypatch.setattr(worker, "_claim_next_job", claim)
    monkeypatch.setattr(worker, "_clear_stale_leases", clear)
    monkeypatch.setattr(worker, "Settings", lambda: _settings())
    monkeypatch.setattr(worker, "configure_logging", lambda **_: None)
    monkeypatch.setattr(worker, "create_container", _runtime_container)
    return claim, clear


def _settings() -> Settings:
    return Settings(
        LLM_WORKER_JOB_CONCURRENCY=SLOTS,
        RUNNER_QUEUE_POLL_INTERVAL_SECONDS=0.001,
    )


def patch_lane(monkeypatch: pytest.MonkeyPatch, lane: RecordingEnrichmentLane) -> None:
    monkeypatch.setattr(enrichment_worker, "process_next_answer_key_enrichment_job", lane)
    monkeypatch.setattr(worker, "process_next_answer_key_enrichment_job", lane)


async def stop_worker(task: asyncio.Task[None]) -> None:
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def wait_until(condition: Callable[[], bool], *, timeout: float = 5.0) -> None:
    async def poll() -> None:
        while not condition():
            await asyncio.sleep(0.001)

    await asyncio.wait_for(poll(), timeout=timeout)


@pytest.mark.asyncio
async def test_worker_runs_every_slot_at_once_under_distinct_worker_ids(
    monkeypatch: pytest.MonkeyPatch,
    tool_run_boundary: tuple[AsyncMock, AsyncMock],
) -> None:
    claim, _ = tool_run_boundary
    barrier = asyncio.Barrier(SLOTS)
    lane = RecordingEnrichmentLane(first_step_barrier=barrier)
    patch_lane(monkeypatch, lane)

    task = asyncio.create_task(
        worker.run_execution_queue_worker(worker_id=BASE_WORKER_ID, once=False)
    )
    await wait_until(lambda: claim.await_count > 0 and len(lane.worker_ids) > SLOTS)
    await stop_worker(task)

    assert set(lane.worker_ids) == {f"{BASE_WORKER_ID}:{slot}" for slot in range(SLOTS)}
    assert lane.peak == SLOTS
    assert {call.kwargs["worker_id"] for call in claim.await_args_list} == {BASE_WORKER_ID}


@pytest.mark.asyncio
async def test_slot_count_caps_concurrent_enrichment_steps(
    monkeypatch: pytest.MonkeyPatch,
    tool_run_boundary: tuple[AsyncMock, AsyncMock],
) -> None:
    del tool_run_boundary
    lane = RecordingEnrichmentLane()
    patch_lane(monkeypatch, lane)

    task = asyncio.create_task(
        worker.run_execution_queue_worker(worker_id=BASE_WORKER_ID, once=False)
    )
    await wait_until(lambda: len(lane.worker_ids) >= SLOTS * 10)
    await stop_worker(task)

    assert 1 <= lane.peak <= SLOTS


@pytest.mark.asyncio
async def test_slot_crash_stops_the_worker(
    monkeypatch: pytest.MonkeyPatch,
    tool_run_boundary: tuple[AsyncMock, AsyncMock],
) -> None:
    del tool_run_boundary

    async def crashing_lane(**_: object) -> bool:
        raise RuntimeError("slot crashed")

    monkeypatch.setattr(enrichment_worker, "process_next_answer_key_enrichment_job", crashing_lane)

    with pytest.raises(ExceptionGroup) as raised:
        await asyncio.wait_for(
            worker.run_execution_queue_worker(worker_id=BASE_WORKER_ID, once=False), timeout=5.0
        )

    assert raised.group_contains(RuntimeError, match="slot crashed")


@pytest.mark.asyncio
async def test_once_runs_one_sequential_step_with_the_base_worker_id(
    monkeypatch: pytest.MonkeyPatch,
    tool_run_boundary: tuple[AsyncMock, AsyncMock],
) -> None:
    claim, clear = tool_run_boundary
    lane = RecordingEnrichmentLane()
    patch_lane(monkeypatch, lane)

    await asyncio.wait_for(
        worker.run_execution_queue_worker(worker_id=BASE_WORKER_ID, once=True), timeout=5.0
    )

    assert lane.worker_ids == [BASE_WORKER_ID]
    clear.assert_awaited_once()
    claim.assert_awaited_once()
    assert claim.await_args is not None
    assert claim.await_args.kwargs["worker_id"] == BASE_WORKER_ID


@pytest.mark.asyncio
async def test_once_stops_after_an_enrichment_step_without_claiming_a_tool_run(
    monkeypatch: pytest.MonkeyPatch,
    tool_run_boundary: tuple[AsyncMock, AsyncMock],
) -> None:
    claim, _ = tool_run_boundary
    calls: list[str] = []

    async def processed(*, worker_id: str, **_: object) -> bool:
        calls.append(worker_id)
        return True

    monkeypatch.setattr(worker, "process_next_answer_key_enrichment_job", processed)

    await asyncio.wait_for(
        worker.run_execution_queue_worker(worker_id=BASE_WORKER_ID, once=True), timeout=5.0
    )

    assert calls == [BASE_WORKER_ID]
    claim.assert_not_awaited()
