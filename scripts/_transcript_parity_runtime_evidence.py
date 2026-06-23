"""Transcript proof runtime evidence capture.

Domain purpose:
    Capture bounded, redacted runtime evidence from the containers that serve
    the retained Audio Transcription parity proof lane.

Relationships:
    Used by `scripts.transcript_parity_proof_launcher` after proof failure and
    before runtime cleanup so Gateway, Skriptoteket web, and worker state is
    preserved without exposing secrets or media payloads.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from scripts._transcript_parity_launcher_io import CommandExecutor, CommandResult

RUNTIME_EVIDENCE_LOG_TAIL_LINES = 160
RUNTIME_EVIDENCE_MAX_ARTIFACT_CHARS = 4_000
DOCKER_INSPECT_STATE_FORMAT = (
    "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}no-health{{end}}"
)
SENSITIVE_JSON_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "bearer",
        "cookie",
        "csrf",
        "passwd",
        "password",
        "private_key",
        "privatekey",
        "proxy_authorization",
        "secret",
        "session",
        "set_cookie",
        "setcookie",
        "token",
        "x_api_key",
        "xapikey",
        "xsrf",
    }
)


@dataclass(frozen=True, slots=True)
class RuntimeEvidenceTarget:
    """One container to capture for proof failure evidence."""

    role: str
    container: str


def collect_runtime_evidence(
    *,
    executor: CommandExecutor,
    run_dir: Path,
    targets: Sequence[RuntimeEvidenceTarget],
    blocker_code: str,
    readyz_summary: Mapping[str, object] | None,
    redact_sensitive_text: Callable[[str], str],
) -> dict[str, object]:
    """Capture bounded container state and logs for a failed proof run."""

    evidence_dir = run_dir / "runtime-evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    container_summaries: dict[str, object] = {}
    text_by_role: dict[str, str] = {}

    for target in targets:
        inspect_result = executor(
            (
                "docker",
                "inspect",
                "--format",
                DOCKER_INSPECT_STATE_FORMAT,
                target.container,
            )
        )
        inspect_text, inspect_truncated = _bounded_redacted_result(
            inspect_result,
            redact_sensitive_text,
        )
        inspect_path = evidence_dir / f"{target.container}.inspect.txt"
        inspect_path.write_text(inspect_text, encoding="utf-8")

        logs_result = executor(
            (
                "docker",
                "logs",
                "--tail",
                str(RUNTIME_EVIDENCE_LOG_TAIL_LINES),
                target.container,
            )
        )
        logs_text, logs_truncated = _bounded_redacted_result(
            logs_result,
            redact_sensitive_text,
        )
        logs_path = evidence_dir / f"{target.container}.logs.txt"
        logs_path.write_text(logs_text, encoding="utf-8")

        text_by_role[target.role] = f"{inspect_text}\n{logs_text}"
        container_summaries[target.container] = {
            "role": target.role,
            "inspect_artifact": _relative_artifact_path(run_dir, inspect_path),
            "logs_artifact": _relative_artifact_path(run_dir, logs_path),
            "inspect_returncode": inspect_result.returncode,
            "logs_returncode": logs_result.returncode,
            "inspect_truncated": inspect_truncated,
            "logs_truncated": logs_truncated,
        }

    return {
        "status": "captured",
        "classification": _classify_failure(
            blocker_code=blocker_code,
            readyz_summary=readyz_summary,
            text_by_role=text_by_role,
        ),
        "artifact_root": "runtime-evidence",
        "log_tail_lines": RUNTIME_EVIDENCE_LOG_TAIL_LINES,
        "max_artifact_chars": RUNTIME_EVIDENCE_MAX_ARTIFACT_CHARS,
        "containers": container_summaries,
    }


def _bounded_redacted_result(
    result: CommandResult,
    redact_sensitive_text: Callable[[str], str],
) -> tuple[str, bool]:
    text = _result_text(result)
    redacted = _redact_runtime_evidence_text(text, redact_sensitive_text)
    if len(redacted) <= RUNTIME_EVIDENCE_MAX_ARTIFACT_CHARS:
        return redacted, False
    marker = "\n[truncated]"
    limit = RUNTIME_EVIDENCE_MAX_ARTIFACT_CHARS - len(marker)
    return f"{redacted[:limit]}{marker}", True


def _result_text(result: CommandResult) -> str:
    if result.stderr:
        return f"{result.stdout}\n[stderr]\n{result.stderr}"
    return result.stdout


def _redact_runtime_evidence_text(
    text: str,
    redact_sensitive_text: Callable[[str], str],
) -> str:
    redacted_lines = [
        _redact_runtime_evidence_line(line, redact_sensitive_text) for line in text.splitlines()
    ]
    if text.endswith("\n"):
        return "\n".join(redacted_lines) + "\n"
    return "\n".join(redacted_lines)


def _redact_runtime_evidence_line(
    line: str,
    redact_sensitive_text: Callable[[str], str],
) -> str:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return redact_sensitive_text(line)
    redacted_payload = _redact_json_value(payload)
    redacted_line = json.dumps(redacted_payload, ensure_ascii=True, sort_keys=True)
    return redact_sensitive_text(redacted_line)


def _redact_json_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): (
                "[REDACTED]" if _is_sensitive_json_key(str(key)) else _redact_json_value(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_json_value(item) for item in value]
    return value


def _is_sensitive_json_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    if normalized in SENSITIVE_JSON_KEYS:
        return True
    sensitive_fragments = (
        "api_key",
        "authorization",
        "bearer",
        "cookie",
        "csrf",
        "passwd",
        "password",
        "private_key",
        "secret",
        "session",
        "token",
        "xsrf",
    )
    return any(fragment in normalized for fragment in sensitive_fragments)


def _relative_artifact_path(run_dir: Path, path: Path) -> str:
    return str(path.relative_to(run_dir))


def _classify_failure(
    *,
    blocker_code: str,
    readyz_summary: Mapping[str, object] | None,
    text_by_role: Mapping[str, str],
) -> str:
    if blocker_code.startswith("sir_convert_readyz") or "service_profile" in blocker_code:
        return "sir_convert_remote_proof_readyz"
    if "tunnel" in blocker_code or "network" in blocker_code:
        return "tunnel_network"
    if readyz_summary is not None and readyz_summary.get("ready") is False:
        return "sir_convert_remote_proof_readyz"
    if _contains_failure_signal(text_by_role.get("huleedu_gateway", "")):
        return "gateway"
    if _contains_failure_signal(text_by_role.get("skriptoteket_web", "")):
        return "skriptoteket_web"
    if _contains_failure_signal(text_by_role.get("skriptoteket_worker", "")):
        return "skriptoteket_worker"
    return "unknown"


def _contains_failure_signal(text: str) -> bool:
    lowered = text.lower()
    return (
        "external_service_error" in lowered
        or " 502" in lowered
        or " 500" in lowered
        or "traceback" in lowered
        or "exception" in lowered
    )
