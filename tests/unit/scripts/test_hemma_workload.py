from __future__ import annotations

import subprocess
from collections.abc import Sequence

import pytest
from repository_governance.hemma_workload import (
    AdapterResult,
    ExpectedState,
    TerminalOutcome,
    WorkloadRegistry,
)

from scripts import hemma_workload


class RecordingExecutor:
    """Return scripted command results without invoking Docker or Hemma."""

    def __init__(self, results: Sequence[hemma_workload.CommandResult | Exception]) -> None:
        self.calls: list[tuple[tuple[str, ...], float]] = []
        self._results = list(results)

    def run(self, argv: tuple[str, ...], *, timeout: float) -> hemma_workload.CommandResult:
        self.calls.append((argv, timeout))
        if not self._results:
            raise AssertionError(f"unexpected command: {argv!r}")
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class ScriptedClock:
    """Expose deterministic elapsed time for bounded readiness polling."""

    def __init__(self, values: Sequence[float]) -> None:
        self._values = list(values)

    def __call__(self) -> float:
        if not self._values:
            raise AssertionError("unexpected monotonic clock read")
        return self._values.pop(0)


def command_result(
    *, returncode: int = 0, stdout: str = "", stderr: str = ""
) -> hemma_workload.CommandResult:
    return hemma_workload.CommandResult(returncode, stdout, stderr)


def test_declarations_bind_exact_skriptoteket_service_membership() -> None:
    declarations = hemma_workload.workload_declarations(executor=RecordingExecutor([]))
    WorkloadRegistry("hemma", declarations).validate()

    web, worker = declarations
    assert web.identity == "skriptoteket-web"
    assert web.service_identities == ("skriptoteket-web",)
    assert web.dependencies == ()
    assert worker.identity == "skriptoteket-worker"
    assert worker.service_identities == ("skriptoteket-worker",)
    assert worker.dependencies == ("skriptoteket-web",)
    for declaration in declarations:
        assert declaration.resource_claims == frozenset({"product:skriptoteket"})
        assert declaration.conflicts == frozenset()
        assert declaration.accepted_terminal_outcomes == frozenset({TerminalOutcome.SUCCEEDED})


def test_adapter_uses_exact_bounded_lifecycle_and_readiness_argv() -> None:
    executor = RecordingExecutor(
        [
            command_result(),
            command_result(),
            command_result(stdout="true\n"),
            command_result(stdout="healthy\n"),
        ]
    )
    timing = hemma_workload.ReadinessTiming(
        timeout_seconds=12.0,
        poll_interval_seconds=1.0,
        command_timeout_seconds=4.0,
    )
    adapter = hemma_workload.SkriptoteketWorkloadAdapter(
        "skriptoteket-worker", executor, timing=timing
    )

    assert adapter.start().outcome is TerminalOutcome.SUCCEEDED
    assert adapter.stop().outcome is TerminalOutcome.SUCCEEDED
    assert adapter.status(ExpectedState.RUNNING).outcome is TerminalOutcome.SUCCEEDED
    assert adapter.readiness().outcome is TerminalOutcome.SUCCEEDED

    assert executor.calls == [
        (("sudo", "-n", "/snap/bin/docker", "start", "skriptoteket-worker"), 4.0),
        (("sudo", "-n", "/snap/bin/docker", "stop", "--time", "30", "skriptoteket-worker"), 34.0),
        (
            (
                "sudo",
                "-n",
                "/snap/bin/docker",
                "inspect",
                "--type",
                "container",
                "--format",
                "{{.State.Running}}",
                "skriptoteket-worker",
            ),
            4.0,
        ),
        (
            (
                "sudo",
                "-n",
                "/snap/bin/docker",
                "inspect",
                "--type",
                "container",
                "--format",
                "{{.State.Health.Status}}",
                "skriptoteket-worker",
            ),
            4.0,
        ),
    ]


def test_default_readiness_timing_matches_the_production_health_window() -> None:
    assert hemma_workload.ReadinessTiming().timeout_seconds == 120.0


def test_lifecycle_os_error_maps_fail_closed_to_failed() -> None:
    executor = RecordingExecutor([OSError("Docker executable unavailable")])
    adapter = hemma_workload.SkriptoteketWorkloadAdapter("skriptoteket-web", executor)

    result = adapter.start()

    assert result.outcome is TerminalOutcome.FAILED


@pytest.mark.parametrize(
    ("stdout", "expected", "outcome"),
    [
        ("true\n", ExpectedState.RUNNING, TerminalOutcome.SUCCEEDED),
        ("false\n", ExpectedState.STOPPED, TerminalOutcome.SUCCEEDED),
        ("", ExpectedState.RUNNING, TerminalOutcome.FAILED),
        ("maybe\n", ExpectedState.RUNNING, TerminalOutcome.FAILED),
        ("true\nfalse\n", ExpectedState.RUNNING, TerminalOutcome.FAILED),
    ],
)
def test_status_maps_exact_state_and_fails_closed_for_unusable_output(
    stdout: str, expected: ExpectedState, outcome: TerminalOutcome
) -> None:
    executor = RecordingExecutor([command_result(stdout=stdout)])
    adapter = hemma_workload.SkriptoteketWorkloadAdapter("skriptoteket-web", executor)

    result = adapter.status(expected)

    assert result.outcome is outcome


def test_status_command_failure_fails_closed() -> None:
    executor = RecordingExecutor([command_result(returncode=7, stderr="inspect denied")])
    adapter = hemma_workload.SkriptoteketWorkloadAdapter("skriptoteket-web", executor)

    result = adapter.status(ExpectedState.RUNNING)

    assert result.outcome is TerminalOutcome.FAILED


def test_status_os_error_maps_fail_closed_to_failed() -> None:
    executor = RecordingExecutor([OSError("Docker socket unavailable")])
    adapter = hemma_workload.SkriptoteketWorkloadAdapter("skriptoteket-web", executor)

    result = adapter.status(ExpectedState.RUNNING)

    assert result.outcome is TerminalOutcome.FAILED


def test_readiness_succeeds_after_bounded_starting_polls_without_hule_readiness() -> None:
    executor = RecordingExecutor(
        [
            command_result(stdout="starting\n"),
            command_result(stdout="starting\n"),
            command_result(stdout="healthy\n"),
        ]
    )
    sleeps: list[float] = []
    adapter = hemma_workload.SkriptoteketWorkloadAdapter(
        "skriptoteket-web",
        executor,
        timing=hemma_workload.ReadinessTiming(5.0, 2.0, 3.0),
        monotonic=ScriptedClock([0.0, 0.0, 2.0]),
        sleeper=sleeps.append,
    )

    result = adapter.readiness()

    assert result.outcome is TerminalOutcome.SUCCEEDED
    assert sleeps == [2.0, 2.0]
    assert [call[0] for call in executor.calls] == [
        (
            "sudo",
            "-n",
            "/snap/bin/docker",
            "inspect",
            "--type",
            "container",
            "--format",
            "{{.State.Health.Status}}",
            "skriptoteket-web",
        ),
    ] * 3


def test_readiness_returns_dependency_unhealthy_at_bounded_exhaustion() -> None:
    executor = RecordingExecutor([command_result(stdout="starting\n")])
    sleeps: list[float] = []
    adapter = hemma_workload.SkriptoteketWorkloadAdapter(
        "skriptoteket-web",
        executor,
        timing=hemma_workload.ReadinessTiming(2.0, 1.0, 3.0),
        monotonic=ScriptedClock([0.0, 2.0]),
        sleeper=sleeps.append,
    )

    result = adapter.readiness()

    assert result.outcome is TerminalOutcome.DEPENDENCY_UNHEALTHY
    assert sleeps == []


def test_readiness_maps_subprocess_timeout_to_timed_out() -> None:
    executor = RecordingExecutor([subprocess.TimeoutExpired(("docker",), 3.0)])
    adapter = hemma_workload.SkriptoteketWorkloadAdapter("skriptoteket-web", executor)

    result = adapter.readiness()

    assert result.outcome is TerminalOutcome.TIMED_OUT


def test_readiness_os_error_maps_fail_closed_to_failed() -> None:
    executor = RecordingExecutor([OSError("Docker health inspection unavailable")])
    adapter = hemma_workload.SkriptoteketWorkloadAdapter("skriptoteket-web", executor)

    result = adapter.readiness()

    assert result.outcome is TerminalOutcome.FAILED


def test_unknown_workload_identity_refuses_before_any_runner_call() -> None:
    executor = RecordingExecutor([])

    with pytest.raises(ValueError):
        hemma_workload.workload_declaration("not-skriptoteket", executor=executor)

    assert executor.calls == []


@pytest.mark.parametrize("selector", ("cleanup-session-files", "cleanup-sandbox-snapshots"))
def test_cleanup_invokes_released_wrapper_and_succeeds(selector: str) -> None:
    executor = RecordingExecutor([command_result(stdout="cleanup completed\n")])

    result = hemma_workload.run_cleanup(selector, executor=executor, timeout_seconds=19.0)

    assert result.outcome is TerminalOutcome.SUCCEEDED
    assert executor.calls == [
        (
            (
                "sudo",
                "-n",
                "/usr/local/libexec/skriptoteket-cleanup-if-running",
                selector,
            ),
            19.0,
        )
    ]


@pytest.mark.parametrize("state", ("absent", "stopped"))
def test_cleanup_preserves_released_idle_machine_decision(state: str) -> None:
    executor = RecordingExecutor(
        [command_result(stdout=f"Cleanup skipped: state={state} container=skriptoteket-web.\n")]
    )

    result = hemma_workload.run_cleanup("cleanup-session-files", executor=executor)

    assert result.outcome is TerminalOutcome.INTENTIONALLY_IDLE
    assert not hemma_workload.cleanup_gate_satisfied(result)


def test_cleanup_failure_and_unknown_selector_do_not_advance_gate() -> None:
    failing_executor = RecordingExecutor([command_result(returncode=11, stderr="cleanup failed")])

    failed = hemma_workload.run_cleanup("cleanup-session-files", executor=failing_executor)
    refused_executor = RecordingExecutor([])
    refused = hemma_workload.run_cleanup("unknown-cleanup", executor=refused_executor)

    assert failed.outcome is TerminalOutcome.FAILED
    assert not hemma_workload.cleanup_gate_satisfied(failed)
    assert refused.outcome is TerminalOutcome.REFUSED
    assert refused_executor.calls == []
    assert hemma_workload.cleanup_gate_satisfied(
        AdapterResult("cleanup-session-files", TerminalOutcome.SUCCEEDED)
    )


def test_cleanup_timeout_maps_to_timed_out_and_does_not_advance_gate() -> None:
    executor = RecordingExecutor(
        [subprocess.TimeoutExpired(("skriptoteket-cleanup-if-running",), 120.0)]
    )

    result = hemma_workload.run_cleanup("cleanup-session-files", executor=executor)

    assert result.outcome is TerminalOutcome.TIMED_OUT
    assert not hemma_workload.cleanup_gate_satisfied(result)


def test_cleanup_os_error_maps_fail_closed_to_failed() -> None:
    executor = RecordingExecutor([OSError("cleanup wrapper unavailable")])

    result = hemma_workload.run_cleanup("cleanup-session-files", executor=executor)

    assert result.outcome is TerminalOutcome.FAILED


def test_module_exports_no_host_or_hule_owned_orchestration_surface() -> None:
    forbidden_exports = {
        "HostLock",
        "InventoryAdapter",
        "InventorySnapshot",
        "ReceiptStore",
        "WorkloadController",
        "WorkloadRegistry",
    }

    assert not forbidden_exports.intersection(vars(hemma_workload))
    assert not any(
        "inventory" in export.lower() or "composer" in export.lower()
        for export in vars(hemma_workload)
    )
