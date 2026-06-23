"""Live proof monitoring helpers.

Domain purpose:
    Capture bounded operational logs alongside browser proof artifacts so live
    proof failures can be tied to the product backend that handled the request.

Relationships:
    Used by `scripts.audio_transcription_parity_live` to retain the
    Skriptoteket Docker dev web logs for local transcript proof runs.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from scripts._sir_convert_trust_lane_preflight import (
    SirConvertTrustLanePreflightError,
    preflight_failure_summary,
)
from scripts._transcript_parity_evidence import captured_artifact_summary, write_json

COMPOSE_DEV: tuple[str, ...] = ("docker", "compose", "-f", "compose.yaml", "-f", "compose.dev.yaml")
HEMMA_NATIVE_CONTAINERS: tuple[str, ...] = (
    "skriptoteket-web",
    "skriptoteket-worker",
    "huleedu_api_gateway_service",
    "huleedu_identity_service",
    "huleedu_bff_teacher_service",
    "sir_convert_a_lot_prod",
    "sir_convert_a_lot_gpu_worker",
    "sir_convert_a_lot_stt_sidecar",
)


@dataclass
class ProofLogMonitor:
    """Own one live backend log capture subprocess and its output files."""

    process: subprocess.Popen[str]
    log_file: TextIO
    log_path: Path
    metadata_path: Path
    started_at: str
    command: tuple[str, ...]

    def stop(self) -> None:
        """Stop log capture and persist process metadata."""

        stopped_at = _utc_now()
        status = "stopped"
        returncode: int | None = None
        self.process.terminate()
        try:
            returncode = self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            returncode = self.process.wait(timeout=5)
            status = "killed"
        finally:
            self.log_file.close()
        write_json(
            self.metadata_path,
            {
                "status": status,
                "started_at": self.started_at,
                "stopped_at": stopped_at,
                "returncode": returncode,
                "command": list(self.command),
                "log_path": str(self.log_path),
            },
        )


def start_local_backend_log_monitor(*, artifact_dir: Path) -> ProofLogMonitor:
    """Start Skriptoteket Docker dev web log capture for one local proof run."""

    command = (
        *COMPOSE_DEV,
        "logs",
        "-f",
        "--since=0s",
        "web",
    )
    log_path = artifact_dir / "backend-live.log"
    metadata_path = artifact_dir / "backend-monitor.json"
    log_file = log_path.open("w", encoding="utf-8")
    started_at = _utc_now()
    try:
        process = subprocess.Popen(
            command,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except OSError:
        log_file.close()
        write_json(
            metadata_path,
            {
                "status": "failed_to_start",
                "started_at": started_at,
                "command": list(command),
                "log_path": str(log_path),
            },
        )
        raise
    write_json(
        metadata_path,
        {
            "status": "running",
            "started_at": started_at,
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


def start_hemma_native_service_monitors(*, artifact_dir: Path) -> list[ProofLogMonitor]:
    """Capture bounded Hemma service logs for a native production proof interval."""

    snapshot = capture_hemma_native_service_snapshot(
        artifact_dir=artifact_dir,
        containers=HEMMA_NATIVE_CONTAINERS,
    )
    services = snapshot.get("services")
    if not isinstance(services, list):
        return []
    logs_dir = artifact_dir / "service-logs"
    logs_dir.mkdir(exist_ok=True)
    monitors: list[ProofLogMonitor] = []
    for service in services:
        if not isinstance(service, dict) or service.get("status") == "not_found":
            continue
        name = service.get("name")
        if not isinstance(name, str):
            continue
        monitor = _start_docker_log_monitor(
            artifact_dir=artifact_dir,
            logs_dir=logs_dir,
            container_name=name,
        )
        if monitor is not None:
            monitors.append(monitor)
    return monitors


def capture_hemma_native_service_snapshot(
    *,
    artifact_dir: Path,
    containers: Sequence[str],
) -> dict[str, object]:
    """Capture safe Docker state for services involved in native transcript proof."""

    snapshot: dict[str, object] = {
        "status": "captured",
        "captured_at": _utc_now(),
        "containers": list(containers),
        "services": [
            _capture_docker_service_state(container_name=container_name)
            for container_name in containers
        ],
    }
    write_json(artifact_dir / "service-monitoring.json", snapshot)
    return snapshot


def capture_local_backend_container_snapshot(*, artifact_dir: Path) -> dict[str, object]:
    """Capture safe runtime settings from the running Docker dev web container."""

    command = (*COMPOSE_DEV, "exec", "-T", "web", "printenv")
    metadata_path = artifact_dir / "backend-container.json"
    started_at = _utc_now()
    completed_at: str | None = None
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        completed_at = _utc_now()
        env = _parse_env_output(result.stdout)
        snapshot: dict[str, object] = {
            "status": "captured" if result.returncode == 0 else "failed",
            "started_at": started_at,
            "completed_at": completed_at,
            "returncode": result.returncode,
            "command": list(command),
            "environment": _safe_container_environment(env),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        snapshot = {
            "status": "failed",
            "started_at": started_at,
            "completed_at": completed_at or _utc_now(),
            "command": list(command),
            "error_type": type(exc).__name__,
            "environment": {},
        }
    write_json(metadata_path, snapshot)
    return snapshot


def _start_docker_log_monitor(
    *,
    artifact_dir: Path,
    logs_dir: Path,
    container_name: str,
) -> ProofLogMonitor | None:
    safe_name = _safe_filename(container_name)
    command = ("sudo", "docker", "logs", "-f", "--since=0s", container_name)
    log_path = logs_dir / f"{safe_name}.log"
    metadata_path = logs_dir / f"{safe_name}.monitor.json"
    log_file = log_path.open("w", encoding="utf-8")
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
        write_json(
            metadata_path,
            {
                "status": "failed_to_start",
                "started_at": started_at,
                "container": container_name,
                "command": list(command),
                "log_path": str(log_path),
                "error_type": type(exc).__name__,
            },
        )
        return None
    write_json(
        metadata_path,
        {
            "status": "running",
            "started_at": started_at,
            "container": container_name,
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


def _capture_docker_service_state(*, container_name: str) -> dict[str, object]:
    inspect_result = _run_docker_inspect_json(container_name=container_name)
    if inspect_result["status"] != "captured":
        return inspect_result
    state = inspect_result.get("state")
    networks = inspect_result.get("networks")
    return {
        "name": container_name,
        "status": "captured",
        "state": _safe_container_state(state),
        "networks": _safe_container_networks(networks),
    }


def _run_docker_inspect_json(*, container_name: str) -> dict[str, object]:
    command = (
        "sudo",
        "docker",
        "inspect",
        "--format",
        "{{json .State}} {{json .NetworkSettings.Networks}}",
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
            "stderr": _bounded_text(result.stderr),
        }
    try:
        state_raw, networks_raw = result.stdout.strip().split(" ", 1)
        return {
            "name": container_name,
            "status": "captured",
            "state": json.loads(state_raw),
            "networks": json.loads(networks_raw),
        }
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "name": container_name,
            "status": "parse_failed",
            "command": list(command),
            "error_type": type(exc).__name__,
            "stdout": _bounded_text(result.stdout),
        }


def _safe_container_state(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    health = value.get("Health")
    return {
        "status": value.get("Status"),
        "running": value.get("Running"),
        "paused": value.get("Paused"),
        "restarting": value.get("Restarting"),
        "oom_killed": value.get("OOMKilled"),
        "dead": value.get("Dead"),
        "exit_code": value.get("ExitCode"),
        "started_at": value.get("StartedAt"),
        "finished_at": value.get("FinishedAt"),
        "health_status": health.get("Status") if isinstance(health, dict) else None,
    }


def _safe_container_networks(value: object) -> list[dict[str, object]]:
    if not isinstance(value, dict):
        return []
    networks: list[dict[str, object]] = []
    for name, network in sorted(value.items()):
        if not isinstance(network, dict):
            continue
        aliases = network.get("Aliases")
        dns_names = network.get("DNSNames")
        networks.append(
            {
                "name": name,
                "aliases": aliases if isinstance(aliases, list) else [],
                "dns_names": dns_names if isinstance(dns_names, list) else [],
            }
        )
    return networks


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._") or "service"


def _bounded_text(value: str, *, limit: int = 500) -> str:
    return " ".join(value.split())[:limit] if value.strip() else ""


def block_if_running_backend_target_differs(
    *,
    artifact_dir: Path,
    app_path: str,
    config_base_url: str,
    trust_lane_summary: dict[str, object],
) -> None:
    """Fail local proof if the running Docker producer lane differs from preflight."""

    snapshot = capture_local_backend_container_snapshot(artifact_dir=artifact_dir)
    environment = snapshot.get("environment")
    actual = environment.get("sir_convert_base_url") if isinstance(environment, dict) else None
    expected = trust_lane_summary.get("producer_backend_url")
    if expected == actual:
        return
    metadata = {
        **trust_lane_summary,
        "running_producer_backend_url": actual,
        "backend_container": str(artifact_dir / "backend-container.json"),
        "job_submit_allowed": False,
    }
    error = SirConvertTrustLanePreflightError(
        blocker_kind="sir_convert_running_producer_lane_mismatch",
        message=(
            "Running Skriptoteket web container producer target does not match "
            "the verified proof producer target."
        ),
        metadata=metadata,
    )
    summary = preflight_failure_summary(
        error,
        base_url=config_base_url,
        app_path=app_path,
        artifact_dir=str(artifact_dir),
    )
    summary["artifacts"] = captured_artifact_summary(artifact_dir)
    write_json(artifact_dir / "proof-summary.json", summary)
    raise SystemExit(error.blocker_kind)


def _parse_env_output(value: str) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in value.splitlines():
        if "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        env[key] = raw_value
    return env


def _safe_container_environment(env: dict[str, str]) -> dict[str, object]:
    api_key = env.get("SIR_CONVERT_A_LOT_V2_API_KEY", "")
    return {
        "environment": env.get("ENVIRONMENT"),
        "sir_convert_base_url": env.get("SIR_CONVERT_A_LOT_V2_BASE_URL"),
        "sir_convert_api_key_length": len(api_key),
        "sir_convert_callback_base_url": env.get("SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL"),
    }


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
