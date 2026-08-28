"""Typed subprocess boundary for Skriptoteket Hemma workload adapters."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Callable, Protocol, runtime_checkable

from repository_governance.hemma_workload import (
    AdapterResult,
    ExpectedState,
    TerminalOutcome,
    WorkloadDeclaration,
)

DOCKER = "/snap/bin/docker"
NONINTERACTIVE_SUDO = ("sudo", "-n")
WEB_IDENTITY = "skriptoteket-web"
WORKER_IDENTITY = "skriptoteket-worker"
PRODUCT_RESOURCE_CLAIM = "product:skriptoteket"
CLEANUP_EXECUTABLE = "/usr/local/libexec/skriptoteket-cleanup-if-running"
CLEANUP_SELECTORS = frozenset({"cleanup-session-files", "cleanup-sandbox-snapshots"})

Monotonic = Callable[[], float]
Sleeper = Callable[[float], None]


@dataclass(frozen=True)
class CommandResult:
    """Captured result from one completed workload command."""

    returncode: int
    stdout: str
    stderr: str


@runtime_checkable
class CommandExecutor(Protocol):
    """Execute one literal workload command."""

    def run(self, argv: tuple[str, ...], *, timeout: float) -> CommandResult:
        """Run one command and return its captured result."""


class CommandRunner:
    """Execute literal workload commands through ``subprocess.run``."""

    def run(self, argv: tuple[str, ...], *, timeout: float) -> CommandResult:
        """Run one command without invoking a shell."""

        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            shell=False,
        )
        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


@dataclass(frozen=True)
class ReadinessTiming:
    timeout_seconds: float = 120.0
    poll_interval_seconds: float = 2.0
    command_timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("readiness timeout must be positive")
        if self.poll_interval_seconds <= 0:
            raise ValueError("readiness poll interval must be positive")
        if self.command_timeout_seconds <= 0:
            raise ValueError("readiness command timeout must be positive")


class SkriptoteketWorkloadAdapter:
    """Bind one declared Skriptoteket service to its exact Docker container."""

    def __init__(
        self,
        identity: str,
        executor: CommandExecutor,
        *,
        timing: ReadinessTiming = ReadinessTiming(),
        monotonic: Monotonic = time.monotonic,
        sleeper: Sleeper = time.sleep,
    ) -> None:
        if identity not in {WEB_IDENTITY, WORKER_IDENTITY}:
            raise ValueError(f"unknown Skriptoteket workload identity {identity!r}")
        self._identity = identity
        self._executor = executor
        self._timing = timing
        self._monotonic = monotonic
        self._sleeper = sleeper

    def start(self) -> AdapterResult:
        return self._completed_operation(
            "start",
            (*NONINTERACTIVE_SUDO, DOCKER, "start", self._identity),
            timeout=self._timing.command_timeout_seconds,
        )

    def stop(self) -> AdapterResult:
        stop_seconds = 30
        return self._completed_operation(
            "stop",
            (
                *NONINTERACTIVE_SUDO,
                DOCKER,
                "stop",
                "--time",
                str(stop_seconds),
                self._identity,
            ),
            timeout=float(stop_seconds) + self._timing.command_timeout_seconds,
        )

    def status(self, expected: ExpectedState) -> AdapterResult:
        argv = (
            *NONINTERACTIVE_SUDO,
            DOCKER,
            "inspect",
            "--type",
            "container",
            "--format",
            "{{.State.Running}}",
            self._identity,
        )
        try:
            result = self._executor.run(
                argv,
                timeout=self._timing.command_timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return AdapterResult(
                self._identity,
                TerminalOutcome.TIMED_OUT,
                "Docker status inspection timed out",
            )
        except OSError as error:
            return self._os_error("status inspection", error)
        if result.returncode != 0:
            return self._command_failed("status inspection", result)
        running = _single_value(result.stdout)
        if running not in {"true", "false"}:
            return AdapterResult(
                self._identity,
                TerminalOutcome.FAILED,
                f"Docker status returned malformed running state {running!r}",
            )
        actual = ExpectedState.RUNNING if running == "true" else ExpectedState.STOPPED
        if actual is not expected:
            return AdapterResult(
                self._identity,
                TerminalOutcome.FAILED,
                f"expected {expected.value} but Docker reports {actual.value}",
            )
        return AdapterResult(self._identity, TerminalOutcome.SUCCEEDED)

    def readiness(self) -> AdapterResult:
        deadline = self._monotonic() + self._timing.timeout_seconds
        last_state = "unobserved"
        argv = (
            *NONINTERACTIVE_SUDO,
            DOCKER,
            "inspect",
            "--type",
            "container",
            "--format",
            "{{.State.Health.Status}}",
            self._identity,
        )
        while True:
            try:
                result = self._executor.run(
                    argv,
                    timeout=self._timing.command_timeout_seconds,
                )
            except subprocess.TimeoutExpired:
                return AdapterResult(
                    self._identity,
                    TerminalOutcome.TIMED_OUT,
                    "Docker health inspection timed out",
                )
            except OSError as error:
                return self._os_error("health inspection", error)
            if result.returncode != 0:
                return self._command_failed("health inspection", result)
            health = _single_value(result.stdout)
            if health not in {"healthy", "starting", "unhealthy"}:
                return AdapterResult(
                    self._identity,
                    TerminalOutcome.FAILED,
                    f"Docker health inspection returned malformed state {health!r}",
                )
            if health == "healthy":
                return AdapterResult(self._identity, TerminalOutcome.SUCCEEDED)
            last_state = health
            remaining = deadline - self._monotonic()
            if remaining <= 0:
                return AdapterResult(
                    self._identity,
                    TerminalOutcome.DEPENDENCY_UNHEALTHY,
                    f"Docker health did not become healthy; last state={last_state}",
                )
            self._sleeper(min(self._timing.poll_interval_seconds, remaining))

    def _completed_operation(
        self,
        operation: str,
        argv: tuple[str, ...],
        *,
        timeout: float,
    ) -> AdapterResult:
        try:
            result = self._executor.run(argv, timeout=timeout)
        except subprocess.TimeoutExpired:
            return AdapterResult(
                self._identity,
                TerminalOutcome.TIMED_OUT,
                f"Docker {operation} timed out",
            )
        except OSError as error:
            return self._os_error(operation, error)
        if result.returncode != 0:
            return self._command_failed(operation, result)
        return AdapterResult(self._identity, TerminalOutcome.SUCCEEDED)

    def _command_failed(self, operation: str, result: CommandResult) -> AdapterResult:
        diagnostic = _bounded_diagnostic(result.stderr)
        reason = f"Docker {operation} failed with rc={result.returncode}"
        if diagnostic:
            reason = f"{reason}: {diagnostic}"
        return AdapterResult(self._identity, TerminalOutcome.FAILED, reason)

    def _os_error(self, operation: str, error: OSError) -> AdapterResult:
        diagnostic = _bounded_diagnostic(str(error))
        reason = f"Docker {operation} could not execute"
        if diagnostic:
            reason = f"{reason}: {diagnostic}"
        return AdapterResult(self._identity, TerminalOutcome.FAILED, reason)


def workload_declaration(
    service_identity: str,
    *,
    executor: CommandExecutor | None = None,
    timing: ReadinessTiming = ReadinessTiming(),
    monotonic: Monotonic = time.monotonic,
    sleeper: Sleeper = time.sleep,
) -> WorkloadDeclaration:
    if service_identity not in {WEB_IDENTITY, WORKER_IDENTITY}:
        raise ValueError(f"unknown Skriptoteket workload identity {service_identity!r}")
    adapter = SkriptoteketWorkloadAdapter(
        service_identity,
        executor or CommandRunner(),
        timing=timing,
        monotonic=monotonic,
        sleeper=sleeper,
    )
    dependencies = (WEB_IDENTITY,) if service_identity == WORKER_IDENTITY else ()
    return WorkloadDeclaration(
        identity=service_identity,
        service_identities=(service_identity,),
        dependencies=dependencies,
        resource_claims=frozenset({PRODUCT_RESOURCE_CLAIM}),
        conflicts=frozenset(),
        adapter=adapter,
        accepted_terminal_outcomes=frozenset({TerminalOutcome.SUCCEEDED}),
    )


def workload_declarations(
    *,
    executor: CommandExecutor | None = None,
    timing: ReadinessTiming = ReadinessTiming(),
    monotonic: Monotonic = time.monotonic,
    sleeper: Sleeper = time.sleep,
) -> tuple[WorkloadDeclaration, WorkloadDeclaration]:
    shared_executor = executor or CommandRunner()
    return (
        workload_declaration(
            WEB_IDENTITY,
            executor=shared_executor,
            timing=timing,
            monotonic=monotonic,
            sleeper=sleeper,
        ),
        workload_declaration(
            WORKER_IDENTITY,
            executor=shared_executor,
            timing=timing,
            monotonic=monotonic,
            sleeper=sleeper,
        ),
    )


def run_cleanup(
    selector: str,
    *,
    executor: CommandExecutor | None = None,
    timeout_seconds: float = 120.0,
) -> AdapterResult:
    if selector not in CLEANUP_SELECTORS:
        return AdapterResult(
            selector,
            TerminalOutcome.REFUSED,
            f"unknown Skriptoteket cleanup selector {selector!r}",
        )
    if timeout_seconds <= 0:
        raise ValueError("cleanup timeout must be positive")
    runner = executor or CommandRunner()
    try:
        result = runner.run(
            (*NONINTERACTIVE_SUDO, CLEANUP_EXECUTABLE, selector),
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return AdapterResult(
            selector,
            TerminalOutcome.TIMED_OUT,
            "cleanup command timed out",
        )
    except OSError as error:
        diagnostic = _bounded_diagnostic(str(error))
        reason = "cleanup command could not execute"
        if diagnostic:
            reason = f"{reason}: {diagnostic}"
        return AdapterResult(selector, TerminalOutcome.FAILED, reason)
    if result.returncode != 0:
        diagnostic = _bounded_diagnostic(result.stderr)
        reason = f"cleanup command failed with rc={result.returncode}"
        if diagnostic:
            reason = f"{reason}: {diagnostic}"
        return AdapterResult(selector, TerminalOutcome.FAILED, reason)
    idle_messages = {
        "Cleanup skipped: state=absent container=skriptoteket-web.",
        "Cleanup skipped: state=stopped container=skriptoteket-web.",
    }
    if result.stdout.strip() in idle_messages:
        return AdapterResult(selector, TerminalOutcome.INTENTIONALLY_IDLE)
    return AdapterResult(selector, TerminalOutcome.SUCCEEDED)


def cleanup_gate_satisfied(result: AdapterResult) -> bool:
    return result.outcome is TerminalOutcome.SUCCEEDED


def _single_value(stdout: str) -> str | None:
    lines = stdout.splitlines()
    if len(lines) != 1:
        return None
    value = lines[0].strip()
    return value or None


def _bounded_diagnostic(stderr: str, *, limit: int = 500) -> str:
    return " ".join(stderr.split())[:limit]
