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

from scripts._proof_live_monitoring import _capture_docker_service_state


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
                '"Health":{"Status":"healthy"}} '
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
