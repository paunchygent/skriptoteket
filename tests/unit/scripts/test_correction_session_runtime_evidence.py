"""Correction-session runtime evidence tests.

Domain purpose:
    Protect the Exam Converter correction-session live proof from drifting away
    from retained service-log evidence for Dev and Hemma production runs.

Relationships:
    Exercises `scripts._correction_session_runtime_evidence`, which selects the
    Docker service monitors used by the retained PR-0337/Story 58 proof script.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict

from scripts import _correction_session_runtime_evidence as evidence_module


class _StoppedMonitor:
    def __init__(self) -> None:
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


class _CapturedHemmaServiceMonitorCall(TypedDict):
    containers: tuple[str, ...]
    ssh_host: str


def test_production_correction_session_evidence_captures_service_logs(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: _CapturedHemmaServiceMonitorCall = {
        "containers": (),
        "ssh_host": "",
    }
    monitor = _StoppedMonitor()

    def fake_start_hemma_ssh_service_monitors(
        *,
        artifact_dir: Path,
        containers: tuple[str, ...],
        ssh_host: str,
    ) -> list[_StoppedMonitor]:
        captured["containers"] = containers
        captured["ssh_host"] = ssh_host
        logs_dir = artifact_dir / "service-logs"
        logs_dir.mkdir()
        (artifact_dir / "service-monitoring.json").write_text("{}\n", encoding="utf-8")
        (logs_dir / "huleedu_api_gateway_service.log").write_text(
            "GET /sir-convert/v2/convert/jobs/job/correction-replays/set/artifacts/pdf 200\n",
            encoding="utf-8",
        )
        return [monitor]

    monkeypatch.setattr(
        evidence_module,
        "start_hemma_ssh_service_monitors",
        fake_start_hemma_ssh_service_monitors,
    )

    evidence = evidence_module.start_correction_session_runtime_evidence(
        artifact_dir=tmp_path,
        base_url="https://skriptoteket.hule.education",
        capture_local_backend_logs=True,
        capture_hemma_service_logs=True,
        hemma_ssh_host="hemma",
    )
    evidence.stop()
    summary: dict[str, object] = {}
    evidence.attach_to_summary(summary, tmp_path)

    assert monitor.stopped is True
    assert captured["ssh_host"] == "hemma"
    assert "huleedu_api_gateway_service" in captured["containers"]
    assert "huleedu_file_service" in captured["containers"]
    assert "sir_convert_a_lot_prod" in captured["containers"]
    assert summary["runtime_log_evidence"] == {
        "service_monitoring": str(tmp_path / "service-monitoring.json"),
        "service_logs": [str(tmp_path / "service-logs" / "huleedu_api_gateway_service.log")],
    }


def test_local_correction_session_evidence_captures_service_logs(
    monkeypatch,
    tmp_path: Path,
) -> None:
    run_commands: list[Sequence[str]] = []
    popen_commands: list[Sequence[str]] = []
    backend_monitor = _StoppedMonitor()

    def fake_start_local_backend_log_monitor(*, artifact_dir: Path) -> _StoppedMonitor:
        (artifact_dir / "backend-live.log").write_text(
            "GET /api/v1/apps/documents.conversion_hub/exam-converter/artifacts/save 200\n",
            encoding="utf-8",
        )
        return backend_monitor

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
            stdout='{"Status":"running","Running":true,"ExitCode":0,"Health":{"Status":"healthy"}}',
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
        stdout.write(f"{command[-1]} served local correction replay artifact 200\n")
        stdout.flush()
        return FakeProcess()

    monkeypatch.setattr(
        evidence_module,
        "start_local_backend_log_monitor",
        fake_start_local_backend_log_monitor,
    )
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    evidence = evidence_module.start_correction_session_runtime_evidence(
        artifact_dir=tmp_path,
        base_url="http://127.0.0.1:5173",
        capture_local_backend_logs=True,
        capture_hemma_service_logs=True,
        hemma_ssh_host="hemma",
    )
    evidence.stop()
    summary: dict[str, object] = {}
    evidence.attach_to_summary(summary, tmp_path)

    assert backend_monitor.stopped is True
    assert run_commands[0][:3] == ("docker", "inspect", "--format")
    assert popen_commands[0][:3] == ("docker", "logs", "-f")
    assert (tmp_path / "service-monitoring.json").read_text(encoding="utf-8").find(
        '"transport": "local-docker"'
    ) >= 0
    assert "huleedu_api_gateway_service" in (tmp_path / "service-monitoring.json").read_text(
        encoding="utf-8"
    )
    assert summary["runtime_log_evidence"] == {
        "backend_log": str(tmp_path / "backend-live.log"),
        "service_monitoring": str(tmp_path / "service-monitoring.json"),
        "service_logs": [
            str(tmp_path / "service-logs" / "huleedu_api_gateway_service.log"),
            str(tmp_path / "service-logs" / "huleedu_file_service.log"),
            str(tmp_path / "service-logs" / "sir_convert_a_lot_dev.log"),
            str(tmp_path / "service-logs" / "skriptoteket_web.log"),
        ],
    }
