"""Live proof monitoring helpers.

Domain purpose:
    Capture bounded operational logs alongside browser proof artifacts so live
    proof failures can be tied to the product backend that handled the request.

Relationships:
    Used by `scripts.playwright_pr_0349_transcript_parity_live` to retain the
    Skriptoteket Docker dev web logs for local transcript proof runs.
"""

from __future__ import annotations

import subprocess
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
