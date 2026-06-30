"""Correction-session live proof runtime evidence.

Domain purpose:
    Select and retain service logs for the Exam Converter correction-session
    live proof so browser assertions can be tied to the services that handled
    conversion replay, download, and file-save requests.

Relationships:
    Used by `scripts.playwright_pr_0337_correction_session_live` and the shared
    proof monitoring helper to capture local dev backend logs or SSH-backed
    Hemma production service logs under the proof artifact directory.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO
from urllib.parse import urlparse

from scripts._proof_live_monitoring import (
    ProofLogMonitor,
    start_hemma_ssh_service_monitors,
    start_local_backend_log_monitor,
)

HEMMA_PRODUCTION_HOST = "skriptoteket.hule.education"
CORRECTION_SESSION_HEMMA_CONTAINERS: tuple[str, ...] = (
    "skriptoteket-web",
    "skriptoteket-worker",
    "huleedu_api_gateway_service",
    "huleedu_file_service",
    "sir_convert_a_lot_prod",
    "sir_convert_a_lot_gpu_worker",
)
CORRECTION_SESSION_LOCAL_CONTAINERS: tuple[str, ...] = (
    "skriptoteket_web",
    "huleedu_api_gateway_service",
    "huleedu_file_service",
    "sir_convert_a_lot_dev",
)


@dataclass(slots=True)
class CorrectionSessionRuntimeEvidence:
    """Own the log monitors attached to one correction-session proof run."""

    backend_log_monitor: ProofLogMonitor | None
    service_log_monitors: list[ProofLogMonitor]

    def stop(self) -> None:
        """Stop every monitor before the manifest is finalized."""

        if self.backend_log_monitor is not None:
            self.backend_log_monitor.stop()
            self.backend_log_monitor = None
        for monitor in self.service_log_monitors:
            monitor.stop()
        self.service_log_monitors = []

    def attach_to_summary(self, summary: dict[str, object], artifact_dir: Path) -> None:
        """Attach retained runtime evidence file paths to the proof summary."""

        runtime_evidence: dict[str, object] = {}
        backend_log = artifact_dir / "backend-live.log"
        service_monitoring = artifact_dir / "service-monitoring.json"
        service_logs = sorted((artifact_dir / "service-logs").glob("*.log"))
        if backend_log.is_file():
            runtime_evidence["backend_log"] = str(backend_log)
        if service_monitoring.is_file():
            runtime_evidence["service_monitoring"] = str(service_monitoring)
        if service_logs:
            runtime_evidence["service_logs"] = [str(path) for path in service_logs]
        if runtime_evidence:
            summary["runtime_log_evidence"] = runtime_evidence


def start_correction_session_runtime_evidence(
    *,
    artifact_dir: Path,
    base_url: str,
    capture_local_backend_logs: bool,
    capture_hemma_service_logs: bool,
    hemma_ssh_host: str,
) -> CorrectionSessionRuntimeEvidence:
    """Start log monitors for the selected correction-session proof lane."""

    backend_log_monitor: ProofLogMonitor | None = None
    service_log_monitors: list[ProofLogMonitor] = []
    is_production = _is_hemma_production_url(base_url)
    if capture_local_backend_logs and not is_production:
        backend_log_monitor = start_local_backend_log_monitor(artifact_dir=artifact_dir)
        service_log_monitors = _start_local_service_monitors(artifact_dir=artifact_dir)
    if capture_hemma_service_logs and is_production:
        service_log_monitors = start_hemma_ssh_service_monitors(
            artifact_dir=artifact_dir,
            containers=CORRECTION_SESSION_HEMMA_CONTAINERS,
            ssh_host=hemma_ssh_host,
        )
    return CorrectionSessionRuntimeEvidence(
        backend_log_monitor=backend_log_monitor,
        service_log_monitors=service_log_monitors,
    )


def _is_hemma_production_url(base_url: str) -> bool:
    return urlparse(base_url).hostname == HEMMA_PRODUCTION_HOST


def _start_local_service_monitors(*, artifact_dir: Path) -> list[ProofLogMonitor]:
    services = [
        _capture_local_service_state(container) for container in CORRECTION_SESSION_LOCAL_CONTAINERS
    ]
    _write_json(
        artifact_dir / "service-monitoring.json",
        {
            "status": "captured",
            "captured_at": _utc_now(),
            "containers": list(CORRECTION_SESSION_LOCAL_CONTAINERS),
            "transport": "local-docker",
            "services": services,
        },
    )
    logs_dir = artifact_dir / "service-logs"
    logs_dir.mkdir(exist_ok=True)
    monitors: list[ProofLogMonitor] = []
    for service in services:
        if service.get("status") != "captured":
            continue
        name = service.get("name")
        if isinstance(name, str):
            monitor = _start_local_docker_log_monitor(logs_dir=logs_dir, container_name=name)
            if monitor is not None:
                monitors.append(monitor)
    return monitors


def _capture_local_service_state(container_name: str) -> dict[str, object]:
    command = (
        "docker",
        "inspect",
        "--format",
        "{{json .State}}",
        container_name,
    )
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "name": container_name,
            "status": "inspect_failed",
            "command": list(command),
            "error_type": type(exc).__name__,
        }
    if result.returncode != 0:
        return {
            "name": container_name,
            "status": "not_found",
            "returncode": result.returncode,
            "command": list(command),
            "stderr": " ".join(result.stderr.split())[:500],
        }
    try:
        state = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {
            "name": container_name,
            "status": "parse_failed",
            "command": list(command),
            "error_type": type(exc).__name__,
            "stdout": " ".join(result.stdout.split())[:500],
        }
    health = state.get("Health") if isinstance(state, dict) else None
    return {
        "name": container_name,
        "status": "captured",
        "state": {
            "status": state.get("Status") if isinstance(state, dict) else None,
            "running": state.get("Running") if isinstance(state, dict) else None,
            "exit_code": state.get("ExitCode") if isinstance(state, dict) else None,
            "health_status": health.get("Status") if isinstance(health, dict) else None,
        },
    }


def _start_local_docker_log_monitor(
    *,
    logs_dir: Path,
    container_name: str,
) -> ProofLogMonitor | None:
    command = ("docker", "logs", "-f", "--since=0s", container_name)
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", container_name).strip("._") or "service"
    log_path = logs_dir / f"{safe_name}.log"
    metadata_path = logs_dir / f"{safe_name}.monitor.json"
    log_file: TextIO = log_path.open("w", encoding="utf-8")
    started_at = _utc_now()
    try:
        process = subprocess.Popen(
            command,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except OSError as exc:
        log_file.close()
        _write_json(
            metadata_path,
            {
                "status": "failed_to_start",
                "started_at": started_at,
                "container": container_name,
                "transport": "local-docker",
                "command": list(command),
                "log_path": str(log_path),
                "error_type": type(exc).__name__,
            },
        )
        return None
    _write_json(
        metadata_path,
        {
            "status": "running",
            "started_at": started_at,
            "container": container_name,
            "transport": "local-docker",
            "command": list(command),
            "log_path": str(log_path),
        },
    )
    return ProofLogMonitor(
        process=process,
        log_file=log_file,
        log_path=log_path,
        metadata_path=metadata_path,
        started_at=started_at,
        command=command,
    )


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
