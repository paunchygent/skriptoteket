"""Audio Transcription parity proof launcher tests.

Domain purpose:
    Prove the lane-aware Audio Transcription parity launcher fails closed before
    browser proof or media upload when remote-proof runtime truth drifts.

Relationships:
    Exercises `scripts.transcript_parity_proof_launcher`, which orchestrates
    HuleEdu Gateway, Skriptoteket producer, Sir Convert readyz, and the retained
    Playwright parity proof command.
"""

from __future__ import annotations

import json
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from scripts import transcript_parity_proof_launcher as launcher
from scripts.transcript_parity_proof_launcher import (
    GATEWAY_BACKEND_ENV_KEY,
    PRODUCER_BACKEND_ENV_KEY,
    CommandResult,
    LauncherError,
    main,
)

ROOT = Path(__file__).resolve().parents[3]
TEST_SIGNER_FINGERPRINT = "46aefc0edc2f71267e2df783ca27f4df2b0da269cc7e84b43cbe2de6ac7c1992"
DOCKER_INSPECT_STATE_FORMAT = (
    "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}no-health{{end}}"
)


@dataclass
class RecordedCommand:
    command: tuple[str, ...]
    cwd: Path | None
    env: dict[str, str]


class FakeExecutor:
    def __init__(
        self,
        *,
        gateway_backend_url: str = "http://host.docker.internal:38085",
        web_producer_url: str = "http://host.docker.internal:38085",
        worker_producer_url: str = "http://host.docker.internal:38085",
        trust_profile_fingerprint: str = TEST_SIGNER_FINGERPRINT,
        fail_proof: bool = False,
        fail_gateway_restore: bool = False,
        fail_auth_integration: bool = False,
        auth_integration_results: Sequence[CommandResult] | None = None,
        failure_summary_root: Path | None = None,
        container_logs: Mapping[str, str] | None = None,
    ) -> None:
        self.gateway_backend_url = gateway_backend_url
        self.web_producer_url = web_producer_url
        self.worker_producer_url = worker_producer_url
        self.trust_profile_fingerprint = trust_profile_fingerprint
        self.fail_proof = fail_proof
        self.fail_gateway_restore = fail_gateway_restore
        self.fail_auth_integration = fail_auth_integration
        self.auth_integration_results = list(auth_integration_results or ())
        self.failure_summary_root = failure_summary_root
        self.container_logs = dict(container_logs or {})
        self.auth_integration_failed = False
        self.failure_summary_seen_before_cleanup = False
        self.commands: list[RecordedCommand] = []

    def __call__(
        self,
        command: Sequence[str],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        timeout_seconds: int | None = None,
    ) -> CommandResult:
        del timeout_seconds
        command_tuple = tuple(command)
        self.commands.append(
            RecordedCommand(
                command=command_tuple,
                cwd=cwd,
                env=dict(env or {}),
            )
        )
        if command_tuple[-2:] == ("printenv", "API_GATEWAY_SIR_CONVERT_PROTECTED_API_BACKEND_URL"):
            return CommandResult(returncode=0, stdout=f"{self.gateway_backend_url}\n", stderr="")
        if command_tuple[-2:] == ("printenv", "SIR_CONVERT_A_LOT_V2_BASE_URL"):
            container = command_tuple[-3]
            if container == "skriptoteket_web":
                return CommandResult(returncode=0, stdout=f"{self.web_producer_url}\n", stderr="")
            if container == "skriptoteket_worker":
                return CommandResult(
                    returncode=0, stdout=f"{self.worker_producer_url}\n", stderr=""
                )
        if command_tuple[:2] == ("docker", "inspect"):
            return CommandResult(returncode=0, stdout="running healthy\n", stderr="")
        if command_tuple[:3] == ("docker", "logs", "--tail"):
            container = command_tuple[-1]
            return CommandResult(
                returncode=0,
                stdout=self.container_logs.get(container, f"{container} log ok\n"),
                stderr="",
            )
        if "hemma-sir-convert-internal-identity-trust-profile" in command_tuple:
            payload = '{"spki_sha256_fingerprint":"' + self.trust_profile_fingerprint + '"}\n'
            return CommandResult(returncode=0, stdout=payload, stderr="")
        if _is_auth_integration_check_command(command_tuple):
            if self.auth_integration_results:
                result = self.auth_integration_results.pop(0)
                if result.returncode != 0:
                    self.auth_integration_failed = True
                return result
            if self.fail_auth_integration:
                self.auth_integration_failed = True
                stdout = (
                    "auth integration preflight started\n"
                    "API_KEY=stdout-secret-value\n"
                    "Authorization: Bearer child-secret-token\n"
                    "Cookie: session=child-cookie-secret; csrf=child-csrf-secret\n"
                    + ("stdout detail " * 120)
                )
                stderr = (
                    "PASSWORD=stderr-secret-value\n"
                    "Set-Cookie: gateway=child-set-cookie-secret; Path=/; HttpOnly\n"
                    "downstream accepted bearer child-freeform-bearer-token\n"
                    "gateway check failed\n" + ("stderr detail " * 120)
                )
                return CommandResult(returncode=31, stdout=stdout, stderr=stderr)
        if command_tuple == (
            "pdm",
            "run",
            "run-local-pdm",
            "dev-recreate",
            "api_gateway_service",
        ) and GATEWAY_BACKEND_ENV_KEY not in dict(env or {}):
            if self.auth_integration_failed and self.failure_summary_root is not None:
                self.failure_summary_seen_before_cleanup = bool(
                    list(self.failure_summary_root.glob("*/failure-summary.json"))
                )
            if self.fail_gateway_restore:
                return CommandResult(returncode=19, stdout="", stderr="restore failed")
        if "scripts.audio_transcription_parity_live" in command_tuple and self.fail_proof:
            return CommandResult(returncode=23, stdout="", stderr="proof failed")
        return CommandResult(returncode=0, stdout="", stderr="")


@pytest.fixture(autouse=True)
def auth_retry_sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    sleeps: list[float] = []
    monkeypatch.setattr(launcher, "_sleep_for_huleedu_auth_retry", sleeps.append, raising=False)
    return sleeps


def _readyz(profile: str = "remote-proof") -> dict[str, object]:
    return {
        "ready": True,
        "service_profile": profile,
        "expected_service_profile": profile,
        "service_revision": "test-revision",
    }


def _fetch_readyz(profile: str = "remote-proof"):
    def fetch(url: str) -> dict[str, object]:
        assert url == "http://127.0.0.1:38085/readyz"
        return _readyz(profile)

    return fetch


class SequencedReadyFetcher:
    def __init__(self, *results: dict[str, object] | LauncherError) -> None:
        self.results = list(results)
        self.urls: list[str] = []

    def __call__(self, url: str) -> dict[str, object]:
        self.urls.append(url)
        if not self.results:
            raise AssertionError("readyz fetcher was called more often than expected")
        result = self.results.pop(0)
        if isinstance(result, LauncherError):
            raise result
        return result


def _readyz_unreachable() -> LauncherError:
    return LauncherError(
        "sir_convert_readyz_unreachable",
        "Sir Convert ready endpoint is unreachable.",
    )


def _command_values(executor: FakeExecutor) -> list[str]:
    return [value for item in executor.commands for value in item.command]


def _ssh_commands(executor: FakeExecutor) -> list[tuple[str, ...]]:
    return [item.command for item in executor.commands if item.command[:1] == ("ssh",)]


def _runtime_mutation_commands(executor: FakeExecutor) -> list[tuple[str, ...]]:
    return [
        item.command
        for item in executor.commands
        if item.command
        in {
            ("pdm", "run", "run-local-pdm", "dev-recreate", "api_gateway_service"),
            ("pdm", "run", "dev-stack", "recreate", "web", "worker"),
        }
    ]


def _is_auth_integration_check_command(command: tuple[str, ...]) -> bool:
    return command[:5] == (
        "pdm",
        "run",
        "run-local-pdm",
        "auth-integration",
        "check",
    )


def _auth_integration_check_commands(executor: FakeExecutor) -> list[RecordedCommand]:
    return [item for item in executor.commands if _is_auth_integration_check_command(item.command)]


def _container_env_inspection_commands(executor: FakeExecutor) -> list[tuple[str, ...]]:
    return [
        item.command
        for item in executor.commands
        if item.command[:2] == ("docker", "exec") and "printenv" in item.command
    ]


def _runtime_evidence_commands(executor: FakeExecutor) -> list[tuple[str, ...]]:
    return [
        item.command for item in executor.commands if _is_runtime_evidence_command(item.command)
    ]


def _is_runtime_evidence_command(command: tuple[str, ...]) -> bool:
    return command[:2] == ("docker", "inspect") or command[:2] == ("docker", "logs")


def _auth_timeout_result() -> CommandResult:
    return CommandResult(
        returncode=31,
        stdout="gateway-localhost-session pending\n",
        stderr=(
            "TimeoutError: gateway-localhost-session "
            "http://localhost:8080/v1/auth/session timed out\n"
        ),
    )


def _command_index(executor: FakeExecutor, command: tuple[str, ...]) -> int:
    for index, item in enumerate(executor.commands):
        if item.command == command:
            return index
    raise AssertionError(f"command was not invoked: {command}")


def _proof_command_index(executor: FakeExecutor) -> int:
    for index, item in enumerate(executor.commands):
        if "scripts.audio_transcription_parity_live" in item.command:
            return index
    raise AssertionError("proof command was not invoked")


def _restore_commands(executor: FakeExecutor) -> list[RecordedCommand]:
    return [
        item
        for item in executor.commands[_proof_command_index(executor) + 1 :]
        if not _is_runtime_evidence_command(item.command)
    ]


def _huleedu_commands(executor: FakeExecutor) -> list[RecordedCommand]:
    return [
        item for item in executor.commands if item.command[:3] == ("pdm", "run", "run-local-pdm")
    ]


def _skriptoteket_proof_lane_mutations(executor: FakeExecutor) -> list[RecordedCommand]:
    return [
        item
        for item in executor.commands
        if item.command == ("pdm", "run", "dev-stack", "recreate", "web", "worker")
        and PRODUCER_BACKEND_ENV_KEY in item.env
    ]


def test_wrong_service_profile_fails_before_runtime_recreate(tmp_path: Path) -> None:
    executor = FakeExecutor()

    with pytest.raises(LauncherError) as exc_info:
        main(
            ["remote-proof", "--artifact-root", str(tmp_path)],
            executor=executor,
            fetch_json=_fetch_readyz("prod"),
        )

    assert exc_info.value.code == "sir_convert_service_profile_mismatch"
    assert executor.commands == []


def test_forbidden_local_proof_target_8085_fails_before_proof(tmp_path: Path) -> None:
    executor = FakeExecutor()

    with pytest.raises(LauncherError) as exc_info:
        main(
            [
                "remote-proof",
                "--artifact-root",
                str(tmp_path),
                "--container-target-url",
                "http://host.docker.internal:8085",
            ],
            executor=executor,
            fetch_json=_fetch_readyz(),
        )

    assert exc_info.value.code == "forbidden_sir_convert_target"
    assert executor.commands == []


def test_unreachable_readyz_opens_owned_tunnel_before_runtime_mutation(
    tmp_path: Path,
) -> None:
    executor = FakeExecutor()
    fetcher = SequencedReadyFetcher(_readyz_unreachable(), _readyz())

    assert (
        main(
            ["remote-proof", "--artifact-root", str(tmp_path)],
            executor=executor,
            fetch_json=fetcher,
        )
        == 0
    )

    ssh_commands = _ssh_commands(executor)
    assert len(ssh_commands) == 2
    open_command, stop_command = ssh_commands
    assert open_command[:3] == ("ssh", "-M", "-S")
    control_socket = Path(open_command[3])
    assert control_socket.name == "remote-proof-ssh.sock"
    assert control_socket.parent.parent == tmp_path
    assert open_command[4] == "-fnNT"
    assert "ExitOnForwardFailure=yes" in open_command
    assert "38085:127.0.0.1:38085" in open_command
    assert stop_command[:2] == ("ssh", "-S")
    assert stop_command[2] == open_command[3]
    assert stop_command[-3:] == ("-O", "exit", "hemma")
    assert fetcher.urls == [
        "http://127.0.0.1:38085/readyz",
        "http://127.0.0.1:38085/readyz",
    ]
    assert _command_index(executor, open_command) < _command_index(
        executor,
        _runtime_mutation_commands(executor)[0],
    )


def test_readyz_reachable_does_not_open_or_stop_tunnel(tmp_path: Path) -> None:
    executor = FakeExecutor()

    assert (
        main(
            ["remote-proof", "--artifact-root", str(tmp_path)],
            executor=executor,
            fetch_json=_fetch_readyz(),
        )
        == 0
    )

    assert _ssh_commands(executor) == []


def test_unreachable_readyz_profile_mismatch_stops_tunnel_before_runtime_mutation(
    tmp_path: Path,
) -> None:
    executor = FakeExecutor()
    fetcher = SequencedReadyFetcher(_readyz_unreachable(), _readyz("prod"))

    with pytest.raises(LauncherError) as exc_info:
        main(
            ["remote-proof", "--artifact-root", str(tmp_path)],
            executor=executor,
            fetch_json=fetcher,
        )

    assert exc_info.value.code == "sir_convert_service_profile_mismatch"
    ssh_commands = _ssh_commands(executor)
    assert len(ssh_commands) == 2
    assert ssh_commands[1][2] == ssh_commands[0][3]
    assert _runtime_mutation_commands(executor) == []


def test_generated_proof_invocation_uses_remote_proof_38085_values(tmp_path: Path) -> None:
    executor = FakeExecutor()

    assert (
        main(
            ["remote-proof", "--artifact-root", str(tmp_path)],
            executor=executor,
            fetch_json=_fetch_readyz(),
        )
        == 0
    )

    proof_command = executor.commands[_proof_command_index(executor)].command
    assert proof_command[:4] == ("pdm", "run", "python", "-m")
    assert "scripts.audio_transcription_parity_live" in proof_command
    assert "--sir-convert-proof-lane" in proof_command
    assert "hemma-remote-proof" in proof_command
    assert ".artifacts/audio-transcription-parity-live" in proof_command
    assert "http://host.docker.internal:38085" in proof_command
    assert "http://127.0.0.1:38085/readyz" in proof_command
    assert "http://127.0.0.1:5173" in proof_command
    assert "http://host.docker.internal:8085" not in _command_values(executor)
    assert "http://host.docker.internal:28085" not in _command_values(executor)


def test_runtime_env_inspection_uses_portable_docker_exec_shape(tmp_path: Path) -> None:
    executor = FakeExecutor()

    assert (
        main(
            ["remote-proof", "--artifact-root", str(tmp_path)],
            executor=executor,
            fetch_json=_fetch_readyz(),
        )
        == 0
    )

    assert _container_env_inspection_commands(executor) == [
        (
            "docker",
            "exec",
            "huleedu_api_gateway_service",
            "printenv",
            GATEWAY_BACKEND_ENV_KEY,
        ),
        ("docker", "exec", "skriptoteket_web", "printenv", PRODUCER_BACKEND_ENV_KEY),
        (
            "docker",
            "exec",
            "skriptoteket_worker",
            "printenv",
            PRODUCER_BACKEND_ENV_KEY,
        ),
    ]


def test_runtime_state_is_restored_after_successful_proof(tmp_path: Path) -> None:
    executor = FakeExecutor()

    assert (
        main(
            ["remote-proof", "--artifact-root", str(tmp_path)],
            executor=executor,
            fetch_json=_fetch_readyz(),
        )
        == 0
    )

    restores = _restore_commands(executor)
    assert [item.command for item in restores] == [
        ("pdm", "run", "run-local-pdm", "dev-recreate", "api_gateway_service"),
        ("pdm", "run", "dev-stack", "recreate", "web", "worker"),
    ]
    assert GATEWAY_BACKEND_ENV_KEY not in restores[0].env
    assert PRODUCER_BACKEND_ENV_KEY not in restores[1].env


def test_runtime_state_is_restored_after_proof_failure(tmp_path: Path) -> None:
    executor = FakeExecutor(fail_proof=True)

    with pytest.raises(LauncherError) as exc_info:
        main(
            ["remote-proof", "--artifact-root", str(tmp_path)],
            executor=executor,
            fetch_json=_fetch_readyz(),
        )

    assert exc_info.value.code == "transcript_parity_proof_failed"
    restores = _restore_commands(executor)
    assert [item.command for item in restores] == [
        ("pdm", "run", "run-local-pdm", "dev-recreate", "api_gateway_service"),
        ("pdm", "run", "dev-stack", "recreate", "web", "worker"),
    ]
    assert GATEWAY_BACKEND_ENV_KEY not in restores[0].env
    assert PRODUCER_BACKEND_ENV_KEY not in restores[1].env


def test_runtime_evidence_is_captured_before_cleanup_when_proof_fails(
    tmp_path: Path,
) -> None:
    gateway_log = (
        "Gateway poll failed\n"
        "Authorization: Bearer gateway-secret-token\n"
        "Cookie: session=gateway-cookie-secret\n"
        "EXTERNAL_SERVICE_ERROR 502 from Sir Convert\n" + ("gateway detail " * 500)
    )
    executor = FakeExecutor(
        fail_proof=True,
        container_logs={
            "huleedu_api_gateway_service": gateway_log,
            "skriptoteket_web": "web accepted transcript poll\n",
            "skriptoteket_worker": "worker heartbeat ok\n",
        },
    )

    with pytest.raises(LauncherError) as exc_info:
        main(
            ["remote-proof", "--artifact-root", str(tmp_path)],
            executor=executor,
            fetch_json=_fetch_readyz(),
        )

    assert exc_info.value.code == "transcript_parity_proof_failed"
    evidence_commands = _runtime_evidence_commands(executor)
    expected_containers = [
        "huleedu_api_gateway_service",
        "skriptoteket_web",
        "skriptoteket_worker",
    ]
    expected_evidence_commands: list[tuple[str, ...]] = []
    for container in expected_containers:
        expected_evidence_commands.append(
            (
                "docker",
                "inspect",
                "--format",
                DOCKER_INSPECT_STATE_FORMAT,
                container,
            )
        )
        expected_evidence_commands.append(("docker", "logs", "--tail", "160", container))
    assert evidence_commands == expected_evidence_commands
    first_restore_index = executor.commands.index(_restore_commands(executor)[0])
    evidence_indexes = [
        index for index, item in enumerate(executor.commands) if item.command in evidence_commands
    ]
    assert max(evidence_indexes) < first_restore_index

    summary_paths = list(tmp_path.glob("*/failure-summary.json"))
    assert len(summary_paths) == 1
    summary_path = summary_paths[0]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["blocker_code"] == "transcript_parity_proof_failed"
    runtime_evidence = summary["runtime_evidence"]
    assert runtime_evidence["classification"] == "gateway"
    assert list(runtime_evidence["containers"]) == expected_containers
    gateway_entry = runtime_evidence["containers"]["huleedu_api_gateway_service"]
    gateway_log_path = summary_path.parent / gateway_entry["logs_artifact"]
    assert gateway_log_path.is_file()
    gateway_log_text = gateway_log_path.read_text(encoding="utf-8")
    assert "EXTERNAL_SERVICE_ERROR 502" in gateway_log_text
    assert "[REDACTED]" in gateway_log_text
    assert "[truncated]" in gateway_log_text
    assert "gateway-secret-token" not in gateway_log_text
    assert "gateway-cookie-secret" not in gateway_log_text
    serialized_summary = json.dumps(summary, sort_keys=True)
    assert "gateway-secret-token" not in serialized_summary
    assert "gateway-cookie-secret" not in serialized_summary


def test_runtime_evidence_redacts_structured_json_log_secrets(
    tmp_path: Path,
) -> None:
    gateway_log = "\n".join(
        [
            json.dumps(
                {
                    "event": "gateway_poll_failed",
                    "status": 502,
                    "code": "EXTERNAL_SERVICE_ERROR",
                    "route": "/sir-convert/transcripts/jobs/job_transcript_1",
                    "authorization": "Bearer json-authorization-secret",
                    "cookie": "session=json-cookie-secret",
                    "set_cookie": "gateway=json-set-cookie-secret",
                    "api_key": "json-api-key-secret",
                    "password": "json-password-secret",
                    "token": "json-token-secret",
                    "nested": {
                        "csrf": "json-csrf-secret",
                        "private_key": "json-private-key-secret",
                        "context": "poll still has job progress",
                    },
                },
                sort_keys=True,
            ),
            json.dumps(
                {
                    "event": "gateway_poll_context",
                    "job_id": "job_transcript_1",
                    "progress": {"percent_complete": 42},
                    "message": "EXTERNAL_SERVICE_ERROR 502 from Sir Convert",
                },
                sort_keys=True,
            ),
        ]
    )
    executor = FakeExecutor(
        fail_proof=True,
        container_logs={
            "huleedu_api_gateway_service": gateway_log,
            "skriptoteket_web": json.dumps(
                {
                    "event": "web_poll_proxy",
                    "token": "web-json-token-secret",
                    "job_id": "job_transcript_1",
                }
            ),
            "skriptoteket_worker": json.dumps(
                {
                    "event": "worker_heartbeat",
                    "api_key": "worker-json-api-key-secret",
                    "job_id": "job_transcript_1",
                }
            ),
        },
    )

    with pytest.raises(LauncherError) as exc_info:
        main(
            ["remote-proof", "--artifact-root", str(tmp_path)],
            executor=executor,
            fetch_json=_fetch_readyz(),
        )

    assert exc_info.value.code == "transcript_parity_proof_failed"
    summary_paths = list(tmp_path.glob("*/failure-summary.json"))
    assert len(summary_paths) == 1
    summary_path = summary_paths[0]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["runtime_evidence"]["classification"] == "gateway"
    serialized_summary = json.dumps(summary, sort_keys=True)
    forbidden_values = {
        "json-authorization-secret",
        "json-cookie-secret",
        "json-set-cookie-secret",
        "json-api-key-secret",
        "json-password-secret",
        "json-token-secret",
        "json-csrf-secret",
        "json-private-key-secret",
        "web-json-token-secret",
        "worker-json-api-key-secret",
    }
    assert all(value not in serialized_summary for value in forbidden_values)

    log_paths = [
        summary_path.parent / entry["logs_artifact"]
        for entry in summary["runtime_evidence"]["containers"].values()
    ]
    combined_logs = "\n".join(path.read_text(encoding="utf-8") for path in log_paths)
    assert "EXTERNAL_SERVICE_ERROR" in combined_logs
    assert "job_transcript_1" in combined_logs
    assert "poll still has job progress" in combined_logs
    assert "[REDACTED]" in combined_logs
    assert all(value not in combined_logs for value in forbidden_values)


def test_cleanup_restores_skriptoteket_after_huleedu_restore_failure(
    tmp_path: Path,
) -> None:
    executor = FakeExecutor(fail_proof=True, fail_gateway_restore=True)
    fetcher = SequencedReadyFetcher(_readyz_unreachable(), _readyz())

    with pytest.raises(LauncherError) as exc_info:
        main(
            ["remote-proof", "--artifact-root", str(tmp_path)],
            executor=executor,
            fetch_json=fetcher,
        )

    assert exc_info.value.code == "transcript_parity_proof_failed"
    assert getattr(exc_info.value, "__notes__", []) == [
        "cleanup_failed: huleedu_gateway_restore_failed: Required launcher command failed.",
    ]
    cleanup_commands = _restore_commands(executor)
    assert [item.command for item in cleanup_commands] == [
        ("pdm", "run", "run-local-pdm", "dev-recreate", "api_gateway_service"),
        ("pdm", "run", "dev-stack", "recreate", "web", "worker"),
        _ssh_commands(executor)[1],
    ]
    assert GATEWAY_BACKEND_ENV_KEY not in cleanup_commands[0].env
    assert PRODUCER_BACKEND_ENV_KEY not in cleanup_commands[1].env
    ssh_commands = _ssh_commands(executor)
    assert len(ssh_commands) == 2
    assert ssh_commands[1][2] == ssh_commands[0][3]


def test_huleedu_commands_use_cross_repo_sanitized_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executor = FakeExecutor()
    current_venv_bin = ROOT / ".venv" / "bin"
    monkeypatch.setenv("PDM_PROJECT_ROOT", str(ROOT))
    monkeypatch.setenv("PDM_RUN_CWD", str(ROOT))
    monkeypatch.setenv("VIRTUAL_ENV", str(ROOT / ".venv"))
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "src"))
    monkeypatch.setenv("PATH", f"{current_venv_bin}:/usr/local/bin:/usr/bin")

    assert (
        main(
            ["remote-proof", "--artifact-root", str(tmp_path)],
            executor=executor,
            fetch_json=_fetch_readyz(),
        )
        == 0
    )

    forbidden_keys = {"PDM_PROJECT_ROOT", "PDM_RUN_CWD", "VIRTUAL_ENV", "PYTHONPATH"}
    for item in _huleedu_commands(executor):
        assert forbidden_keys.isdisjoint(item.env), item.command
        assert item.env["PATH"].split(":")[:1] != [str(current_venv_bin)]
    gateway_mutation_commands = [
        item
        for item in _huleedu_commands(executor)
        if item.command[-2:] == ("dev-recreate", "api_gateway_service")
        and GATEWAY_BACKEND_ENV_KEY in item.env
    ]
    assert len(gateway_mutation_commands) == 1
    assert gateway_mutation_commands[0].env[GATEWAY_BACKEND_ENV_KEY] == (
        "http://host.docker.internal:38085"
    )


def test_auth_integration_check_retries_gateway_settle_and_then_proceeds(
    tmp_path: Path,
    auth_retry_sleeps: list[float],
) -> None:
    executor = FakeExecutor(
        auth_integration_results=[
            _auth_timeout_result(),
            CommandResult(returncode=0, stdout="auth integration ready\n", stderr=""),
        ]
    )

    assert (
        main(
            ["remote-proof", "--artifact-root", str(tmp_path)],
            executor=executor,
            fetch_json=_fetch_readyz(),
        )
        == 0
    )

    auth_commands = _auth_integration_check_commands(executor)
    assert len(auth_commands) == 2
    assert auth_retry_sleeps == [2.0]
    for item in auth_commands:
        assert "--timeout-seconds" in item.command
        assert "15" in item.command
        assert item.env[GATEWAY_BACKEND_ENV_KEY] == "http://host.docker.internal:38085"
    assert _skriptoteket_proof_lane_mutations(executor)
    assert _proof_command_index(executor) > executor.commands.index(auth_commands[1])


def test_persistent_auth_integration_failure_blocks_before_skriptoteket_mutation(
    tmp_path: Path,
    auth_retry_sleeps: list[float],
) -> None:
    executor = FakeExecutor(
        auth_integration_results=[
            _auth_timeout_result(),
            _auth_timeout_result(),
            _auth_timeout_result(),
        ],
        failure_summary_root=tmp_path,
    )

    with pytest.raises(LauncherError) as exc_info:
        main(
            ["remote-proof", "--artifact-root", str(tmp_path)],
            executor=executor,
            fetch_json=_fetch_readyz(),
        )

    assert exc_info.value.code == "huleedu_auth_integration_check_failed"
    assert len(_auth_integration_check_commands(executor)) == 3
    assert auth_retry_sleeps == [2.0, 2.0]
    assert not any(
        item.command == ("pdm", "run", "dev-stack", "recreate", "web", "worker")
        for item in executor.commands
    )
    assert all(
        "scripts.audio_transcription_parity_live" not in item.command for item in executor.commands
    )
    assert executor.failure_summary_seen_before_cleanup is True

    summary_paths = list(tmp_path.glob("*/failure-summary.json"))
    assert len(summary_paths) == 1
    summary = json.loads(summary_paths[0].read_text(encoding="utf-8"))
    assert summary["blocker_code"] == "huleedu_auth_integration_check_failed"
    assert "gateway-localhost-session" in summary["metadata"]["stderr_snippet"]


def test_auth_integration_failure_writes_safe_failure_summary(
    tmp_path: Path,
) -> None:
    executor = FakeExecutor(
        fail_auth_integration=True,
        failure_summary_root=tmp_path,
    )
    fetcher = SequencedReadyFetcher(_readyz_unreachable(), _readyz())

    with pytest.raises(LauncherError) as exc_info:
        main(
            ["remote-proof", "--artifact-root", str(tmp_path)],
            executor=executor,
            fetch_json=fetcher,
        )

    assert exc_info.value.code == "huleedu_auth_integration_check_failed"
    metadata = exc_info.value.metadata
    assert metadata["returncode"] == 31
    assert "auth integration preflight started" in metadata["stdout_snippet"]
    assert "gateway check failed" in metadata["stderr_snippet"]
    assert metadata["stdout_truncated"] is True
    assert metadata["stderr_truncated"] is True
    serialized_metadata = json.dumps(metadata, sort_keys=True)
    forbidden_values = {
        "stdout-secret-value",
        "stderr-secret-value",
        "child-secret-token",
        "child-cookie-secret",
        "child-csrf-secret",
        "child-set-cookie-secret",
        "child-freeform-bearer-token",
    }
    assert all(value not in serialized_metadata for value in forbidden_values)
    assert "[REDACTED]" in serialized_metadata
    assert executor.failure_summary_seen_before_cleanup is True

    summary_paths = list(tmp_path.glob("*/failure-summary.json"))
    assert len(summary_paths) == 1
    summary = json.loads(summary_paths[0].read_text(encoding="utf-8"))
    assert summary["status"] == "failed"
    assert summary["blocker_code"] == "huleedu_auth_integration_check_failed"
    assert summary["metadata"]["stdout_snippet"] == metadata["stdout_snippet"]
    assert summary["metadata"]["stderr_snippet"] == metadata["stderr_snippet"]
    assert summary["descriptor"]["ready_url"] == "http://127.0.0.1:38085/readyz"
    assert summary["readyz"]["service_profile"] == "remote-proof"
    serialized_summary = json.dumps(summary, sort_keys=True)
    assert all(value not in serialized_summary for value in forbidden_values)
    assert "API_KEY=" not in serialized_summary
    assert "PASSWORD=" not in serialized_summary
    assert "Authorization:" not in serialized_summary
    assert "Cookie:" not in serialized_summary
    assert "Set-Cookie:" not in serialized_summary


def test_runtime_env_mismatch_fails_before_proof_invocation(tmp_path: Path) -> None:
    executor = FakeExecutor(web_producer_url="http://host.docker.internal:28085")

    with pytest.raises(LauncherError) as exc_info:
        main(
            ["remote-proof", "--artifact-root", str(tmp_path)],
            executor=executor,
            fetch_json=_fetch_readyz(),
        )

    assert exc_info.value.code == "skriptoteket_runtime_env_mismatch"
    assert all(
        "scripts.audio_transcription_parity_live" not in item.command for item in executor.commands
    )


def test_pdm_command_exposes_transcript_parity_launcher() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert (
        pyproject["tool"]["pdm"]["scripts"]["transcript-parity-proof"]
        == "python -m scripts.transcript_parity_proof_launcher"
    )
