"""Live proof Docker monitoring tests.

Domain purpose:
    Protect native Hemma transcript proof monitoring from losing service-state
    evidence or retaining unsafe container environment details.

Relationships:
    Exercises `scripts._proof_live_monitoring`, which supplies operational
    evidence to the PR-0349 transcript parity proof script.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence

from scripts._proof_live_monitoring import (
    _capture_docker_service_state,
    start_hemma_ssh_service_monitors,
)


def test_docker_service_state_keeps_safe_state_and_network_metadata(
    monkeypatch,
) -> None:
    captured_commands: list[Sequence[str]] = []

    def fake_run(
        command: Sequence[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        captured_commands.append(command)
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout=(
                '{"Status":"running","Running":true,"Paused":false,'
                '"Restarting":false,"OOMKilled":false,"Dead":false,'
                '"ExitCode":0,"StartedAt":"2026-06-15T16:24:00Z",'
                '"FinishedAt":"0001-01-01T00:00:00Z",'
                '"Health":{"Status":"healthy"}}__SKRIPTOTEKET_NETWORKS__'
                '{"hule-network":{"Aliases":["sir_convert_a_lot_prod"],'
                '"DNSNames":["sir_convert_a_lot_prod","container-id"],'
                '"IPAddress":"172.18.0.8"}}'
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    snapshot = _capture_docker_service_state(container_name="sir_convert_a_lot_prod")

    assert snapshot["status"] == "captured"
    assert snapshot["state"] == {
        "status": "running",
        "running": True,
        "paused": False,
        "restarting": False,
        "oom_killed": False,
        "dead": False,
        "exit_code": 0,
        "started_at": "2026-06-15T16:24:00Z",
        "finished_at": "0001-01-01T00:00:00Z",
        "health_status": "healthy",
    }
    assert snapshot["networks"] == [
        {
            "name": "hule-network",
            "aliases": ["sir_convert_a_lot_prod"],
            "dns_names": ["sir_convert_a_lot_prod", "container-id"],
        }
    ]
    command_text = " ".join(captured_commands[0])
    assert ".Config.Env" not in command_text
    assert "IPAddress" not in str(snapshot)


def test_ssh_service_monitors_write_remote_container_logs(monkeypatch, tmp_path) -> None:
    run_commands: list[Sequence[str]] = []
    popen_commands: list[Sequence[str]] = []

    def fake_run(
        command: Sequence[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        run_commands.append(command)
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout=(
                '{"Status":"running","Running":true,"Paused":false,'
                '"Restarting":false,"OOMKilled":false,"Dead":false,'
                '"ExitCode":0,"StartedAt":"2026-06-30T01:20:00Z",'
                '"FinishedAt":"0001-01-01T00:00:00Z",'
                '"Health":{"Status":"healthy"}}__SKRIPTOTEKET_NETWORKS__'
                '{"hule-network":{"Aliases":["huleedu_api_gateway_service"],'
                '"DNSNames":["huleedu_api_gateway_service","container-id"],'
                '"IPAddress":"172.18.0.8"}}'
            ),
            stderr="",
        )

    class FakeProcess:
        def terminate(self) -> None:
            return None

        def wait(self, timeout: int) -> int:
            return 0

    def fake_popen(
        command: Sequence[str],
        *,
        stdout,
        stderr: int,
        text: bool,
    ) -> FakeProcess:
        popen_commands.append(command)
        stdout.write(f"{command[-1]} handled correction replay artifact\n")
        stdout.flush()
        return FakeProcess()

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    monitors = start_hemma_ssh_service_monitors(
        artifact_dir=tmp_path,
        containers=("huleedu_api_gateway_service", "huleedu_file_service"),
        ssh_host="hemma",
    )
    for monitor in monitors:
        monitor.stop()

    assert len(monitors) == 2
    assert tuple(run_commands[0][:2]) == ("ssh", "hemma")
    assert (
        "sudo docker inspect --format '{{json .State}}__SKRIPTOTEKET_NETWORKS__"
        "{{json .NetworkSettings.Networks}}'" in run_commands[0][2]
    )
    assert tuple(popen_commands[0][:2]) == ("ssh", "hemma")
    assert (tmp_path / "service-monitoring.json").read_text(encoding="utf-8").find(
        '"transport": "ssh"'
    ) >= 0
    assert (tmp_path / "service-logs" / "huleedu_api_gateway_service.log").read_text(
        encoding="utf-8"
    ) == ("huleedu_api_gateway_service handled correction replay artifact\n")
    assert (tmp_path / "service-logs" / "huleedu_file_service.monitor.json").is_file()
