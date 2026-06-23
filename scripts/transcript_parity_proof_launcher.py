"""Audio Transcription transcript parity proof lane launcher.

Domain purpose:
    Prepare and validate the retained Audio Transcription parity proof lane so
    local operators use the fenced Sir Convert remote-proof runtime without
    copying ports, URLs, or public trust fingerprints by hand.

Relationships:
    Orchestrates HuleEdu Gateway auth-integration runtime, Skriptoteket Docker
    web/worker producer runtime, Sir Convert `/readyz`, and the retained Audio
    Transcription Playwright parity proof.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from scripts._transcript_parity_launcher_io import (
    CommandExecutor,
    CommandResult,
    run_subprocess,
)
from scripts._transcript_parity_runtime_evidence import (
    RuntimeEvidenceTarget,
    collect_runtime_evidence,
)

DEFAULT_BASE_URL = "http://127.0.0.1:5173"
DEFAULT_CONTAINER_TARGET_URL = "http://host.docker.internal:38085"
DEFAULT_EXPECTED_SERVICE_PROFILE = "remote-proof"
DEFAULT_HULEEDU_REPO = Path("/Users/olofs_mba/Documents/Repos/huleedu")
DEFAULT_PROOF_ARTIFACT_ROOT = Path(".artifacts/audio-transcription-parity-live")
DEFAULT_LAUNCH_ARTIFACT_ROOT = Path(".artifacts/transcript-parity-proof-lane")
COMMAND_OUTPUT_SNIPPET_CHARS = 800
HULEEDU_AUTH_CHECK_ATTEMPTS = 3
HULEEDU_AUTH_CHECK_RETRY_DELAY_SECONDS = 2.0
HULEEDU_AUTH_CHECK_HTTP_TIMEOUT_SECONDS = 15
HULEEDU_AUTH_CHECK_PROCESS_TIMEOUT_SECONDS = 30
FORBIDDEN_LOCAL_PROOF_TARGETS = {
    "http://host.docker.internal:8085",
    "http://127.0.0.1:8085",
    "http://localhost:8085",
}
GATEWAY_BACKEND_ENV_KEY = "API_GATEWAY_SIR_CONVERT_PROTECTED_API_BACKEND_URL"
PRODUCER_BACKEND_ENV_KEY = "SIR_CONVERT_A_LOT_V2_BASE_URL"
HULEEDU_GATEWAY_CONTAINER = "huleedu_api_gateway_service"
SKRIPTOTEKET_WEB_CONTAINER = "skriptoteket_web"
SKRIPTOTEKET_WORKER_CONTAINER = "skriptoteket_worker"
RUNTIME_EVIDENCE_TARGETS = (
    RuntimeEvidenceTarget("huleedu_gateway", HULEEDU_GATEWAY_CONTAINER),
    RuntimeEvidenceTarget("skriptoteket_web", SKRIPTOTEKET_WEB_CONTAINER),
    RuntimeEvidenceTarget("skriptoteket_worker", SKRIPTOTEKET_WORKER_CONTAINER),
)
HULEEDU_ENV_REMOVED_KEYS = frozenset(
    {
        "PYTHONHOME",
        "PYTHONPATH",
        "VIRTUAL_ENV",
        "VIRTUAL_ENV_PROMPT",
    }
)
SECRET_ENV_KEY_PATTERN = re.compile(
    r"(SECRET|TOKEN|PASSWORD|PASSWD|API_KEY|PRIVATE_KEY|COOKIE|AUTHORIZATION)",
    re.IGNORECASE,
)
SENSITIVE_HEADER_PATTERN = re.compile(
    r"(?im)^(\s*(?:authorization|proxy-authorization|cookie|set-cookie)\s*:\s*).*$"
)
BEARER_TOKEN_PATTERN = re.compile(r"(?i)\bbearer\s+([^\s,;]+)")
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)([A-Z0-9_.-]*(?:SECRET|TOKEN|PASSWORD|PASSWD|API[_-]?KEY|"
    r"PRIVATE[_-]?KEY|COOKIE|AUTHORIZATION)[A-Z0-9_.-]*\s*[:=]\s*)([^\s]+)"
)


class JsonFetcher(Protocol):
    """Fetch one JSON object from a URL."""

    def __call__(self, url: str) -> dict[str, object]:
        """Return the JSON object fetched from `url`."""


@dataclass(frozen=True, slots=True)
class TranscriptProofLaneDescriptor:
    """Executable lane facts for one transcript parity proof lane."""

    lane_name: str
    proof_lane: str
    local_tunnel_port: int
    container_target_url: str
    ready_url: str
    expected_service_profile: str
    base_url: str


class LauncherError(RuntimeError):
    """Raised when the launcher must fail before proof upload or browser proof."""

    def __init__(self, code: str, message: str, metadata: Mapping[str, object] | None = None):
        super().__init__(message)
        self.code = code
        self.metadata = dict(metadata or {})


def fetch_json(url: str) -> dict[str, object]:
    """Fetch a JSON object from an HTTP endpoint."""

    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise LauncherError(
            "sir_convert_readyz_unreachable",
            f"Sir Convert ready endpoint is unreachable: {url}",
            {"ready_url": url, "error_type": type(exc).__name__},
        ) from exc
    if not isinstance(payload, dict):
        raise LauncherError(
            "sir_convert_readyz_invalid",
            "Sir Convert ready endpoint did not return a JSON object.",
            {"ready_url": url},
        )
    return payload


def main(
    argv: Sequence[str] | None = None,
    *,
    executor: CommandExecutor = run_subprocess,
    fetch_json: JsonFetcher = fetch_json,
) -> int:
    """Run the lane-aware transcript parity proof launcher."""

    args = _parse_args(argv)
    descriptor = _remote_proof_descriptor(
        base_url=args.base_url,
        container_target_url=args.container_target_url or DEFAULT_CONTAINER_TARGET_URL,
    )
    _validate_descriptor(descriptor)
    run_dir = _new_run_dir(Path(args.artifact_root))
    opened_tunnel_socket: Path | None = None
    huleedu_gateway_mutated = False
    skriptoteket_producer_mutated = False
    huleedu_repo = Path(args.huleedu_repo).expanduser().resolve()
    gateway_env = _gateway_overlay_env(descriptor)
    producer_env = _producer_overlay_env(descriptor)
    primary_error: BaseException | None = None
    readyz_summary: dict[str, object] | None = None
    runtime_evidence: dict[str, object] | None = None
    try:
        readyz, opened_tunnel_socket = _fetch_readyz_with_optional_tunnel(
            descriptor=descriptor,
            executor=executor,
            fetch_json=fetch_json,
            run_dir=run_dir,
        )
        readyz_summary = _readyz_summary(readyz)
        _validate_readyz(readyz, descriptor=descriptor)
        _write_json(run_dir / "readyz-summary.json", readyz_summary)
        _write_runtime_overlays(run_dir, descriptor)

        signer_fingerprint = _gateway_signer_fingerprint(
            executor=executor,
            huleedu_repo=huleedu_repo,
        )

        huleedu_gateway_mutated = True
        _run_required(
            executor,
            ("pdm", "run", "run-local-pdm", "dev-recreate", "api_gateway_service"),
            cwd=huleedu_repo,
            env=_huleedu_command_env(gateway_env),
            code="huleedu_gateway_recreate_failed",
        )
        _wait_for_huleedu_auth_integration(
            cwd=huleedu_repo,
            executor=executor,
            gateway_env=gateway_env,
        )
        _assert_container_env(
            executor=executor,
            container_name=HULEEDU_GATEWAY_CONTAINER,
            key=GATEWAY_BACKEND_ENV_KEY,
            expected=descriptor.container_target_url,
            blocker_code="huleedu_gateway_runtime_env_mismatch",
        )

        skriptoteket_producer_mutated = True
        _run_required(
            executor,
            ("pdm", "run", "dev-stack", "recreate", "web", "worker"),
            cwd=Path.cwd(),
            env=_merged_env(producer_env),
            code="skriptoteket_recreate_failed",
        )
        for container_name in (SKRIPTOTEKET_WEB_CONTAINER, SKRIPTOTEKET_WORKER_CONTAINER):
            _assert_container_env(
                executor=executor,
                container_name=container_name,
                key=PRODUCER_BACKEND_ENV_KEY,
                expected=descriptor.container_target_url,
                blocker_code="skriptoteket_runtime_env_mismatch",
            )

        proof_command = _proof_command(
            descriptor=descriptor,
            dotenv=args.dotenv,
            proof_artifact_root=Path(args.proof_artifact_root),
            timeout_seconds=args.timeout_seconds,
            signer_fingerprint=signer_fingerprint,
            audio_file=args.audio_file,
        )
        _write_json(
            run_dir / "launch-manifest.json",
            {
                "status": "runtime_validated",
                "observed_at": _utc_now(),
                "descriptor": _descriptor_summary(descriptor),
                "proof_command": list(proof_command),
                "proof_artifact_root": str(Path(args.proof_artifact_root)),
            },
        )
        _run_required(
            executor,
            proof_command,
            cwd=Path.cwd(),
            env=_merged_env({}),
            code="transcript_parity_proof_failed",
            timeout_seconds=args.timeout_seconds + 120,
        )
    except BaseException as exc:
        primary_error = exc
        runtime_evidence = _capture_runtime_evidence(
            executor=executor,
            run_dir=run_dir,
            readyz_summary=readyz_summary,
            blocker=exc,
            huleedu_gateway_mutated=huleedu_gateway_mutated,
            skriptoteket_producer_mutated=skriptoteket_producer_mutated,
        )
        _write_failure_summary(
            run_dir=run_dir,
            descriptor=descriptor,
            readyz_summary=readyz_summary,
            blocker=exc,
            cleanup_errors=(),
            runtime_evidence=runtime_evidence,
        )
        raise
    finally:
        cleanup_errors = _cleanup_runtime_and_tunnel(
            executor=executor,
            huleedu_gateway_mutated=huleedu_gateway_mutated,
            skriptoteket_producer_mutated=skriptoteket_producer_mutated,
            huleedu_repo=huleedu_repo,
            gateway_overlay_keys=tuple(gateway_env),
            producer_overlay_keys=tuple(producer_env),
            opened_tunnel_socket=opened_tunnel_socket,
        )
        if cleanup_errors:
            if primary_error is None:
                _add_cleanup_notes(cleanup_errors[0], cleanup_errors[1:])
                _write_failure_summary(
                    run_dir=run_dir,
                    descriptor=descriptor,
                    readyz_summary=readyz_summary,
                    blocker=cleanup_errors[0],
                    cleanup_errors=cleanup_errors,
                    runtime_evidence=None,
                )
                _raise_cleanup_errors(cleanup_errors)
            _add_cleanup_notes(primary_error, cleanup_errors)
            _write_failure_summary(
                run_dir=run_dir,
                descriptor=descriptor,
                readyz_summary=readyz_summary,
                blocker=primary_error,
                cleanup_errors=cleanup_errors,
                runtime_evidence=runtime_evidence,
            )
    print(str(run_dir))
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audio Transcription parity proof launcher")
    parser.add_argument("lane", nargs="?", default="remote-proof", choices=["remote-proof"])
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--dotenv", default=".env")
    parser.add_argument("--artifact-root", default=str(DEFAULT_LAUNCH_ARTIFACT_ROOT))
    parser.add_argument("--proof-artifact-root", default=str(DEFAULT_PROOF_ARTIFACT_ROOT))
    parser.add_argument("--huleedu-repo", default=str(DEFAULT_HULEEDU_REPO))
    parser.add_argument("--audio-file", default=None)
    parser.add_argument("--timeout-seconds", type=int, default=1_200)
    parser.add_argument("--container-target-url", default=None, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def _remote_proof_descriptor(
    *,
    base_url: str,
    container_target_url: str,
) -> TranscriptProofLaneDescriptor:
    return TranscriptProofLaneDescriptor(
        lane_name="remote-proof",
        proof_lane="hemma-remote-proof",
        local_tunnel_port=38085,
        container_target_url=container_target_url,
        ready_url="http://127.0.0.1:38085/readyz",
        expected_service_profile=DEFAULT_EXPECTED_SERVICE_PROFILE,
        base_url=base_url,
    )


def _validate_descriptor(descriptor: TranscriptProofLaneDescriptor) -> None:
    target = descriptor.container_target_url.strip().rstrip("/")
    if target in FORBIDDEN_LOCAL_PROOF_TARGETS:
        raise LauncherError(
            "forbidden_sir_convert_target",
            "The transcript proof remote-proof lane must not target local port 8085.",
            _descriptor_summary(descriptor),
        )
    if target != DEFAULT_CONTAINER_TARGET_URL:
        raise LauncherError(
            "unsupported_sir_convert_target",
            "The remote-proof lane is pinned to host.docker.internal:38085.",
            _descriptor_summary(descriptor),
        )


def _validate_readyz(
    readyz: Mapping[str, object],
    *,
    descriptor: TranscriptProofLaneDescriptor,
) -> None:
    if readyz.get("ready") is not True:
        raise LauncherError(
            "sir_convert_readyz_not_ready",
            "Sir Convert remote-proof ready endpoint is not ready.",
            _readyz_summary(readyz),
        )
    observed = _string_field(readyz, "service_profile")
    expected_observed = _string_field(readyz, "expected_service_profile")
    expected = descriptor.expected_service_profile
    if observed != expected or expected_observed != expected:
        raise LauncherError(
            "sir_convert_service_profile_mismatch",
            "Sir Convert ready profile does not match the selected remote-proof lane.",
            {
                **_descriptor_summary(descriptor),
                **_readyz_summary(readyz),
            },
        )


def _fetch_readyz_with_optional_tunnel(
    *,
    descriptor: TranscriptProofLaneDescriptor,
    executor: CommandExecutor,
    fetch_json: JsonFetcher,
    run_dir: Path,
) -> tuple[dict[str, object], Path | None]:
    try:
        return fetch_json(descriptor.ready_url), None
    except LauncherError as exc:
        if exc.code != "sir_convert_readyz_unreachable":
            raise
    control_socket = _open_remote_proof_tunnel(
        descriptor=descriptor,
        executor=executor,
        run_dir=run_dir,
    )
    try:
        return fetch_json(descriptor.ready_url), control_socket
    except BaseException:
        _stop_remote_proof_tunnel(executor=executor, control_socket=control_socket)
        raise


def _open_remote_proof_tunnel(
    *,
    descriptor: TranscriptProofLaneDescriptor,
    executor: CommandExecutor,
    run_dir: Path,
) -> Path:
    control_socket = run_dir / "remote-proof-ssh.sock"
    forward = f"{descriptor.local_tunnel_port}:127.0.0.1:{descriptor.local_tunnel_port}"
    _run_required(
        executor,
        (
            "ssh",
            "-M",
            "-S",
            str(control_socket),
            "-fnNT",
            "-o",
            "ExitOnForwardFailure=yes",
            "-L",
            forward,
            "hemma",
        ),
        code="remote_proof_tunnel_open_failed",
    )
    return control_socket


def _stop_remote_proof_tunnel(
    *,
    executor: CommandExecutor,
    control_socket: Path,
) -> None:
    _run_required(
        executor,
        ("ssh", "-S", str(control_socket), "-O", "exit", "hemma"),
        code="remote_proof_tunnel_stop_failed",
    )


def _cleanup_runtime_and_tunnel(
    *,
    executor: CommandExecutor,
    huleedu_gateway_mutated: bool,
    skriptoteket_producer_mutated: bool,
    huleedu_repo: Path,
    gateway_overlay_keys: Sequence[str],
    producer_overlay_keys: Sequence[str],
    opened_tunnel_socket: Path | None,
) -> list[BaseException]:
    cleanup_errors: list[BaseException] = []
    if huleedu_gateway_mutated:
        try:
            _restore_huleedu_gateway_state(
                executor=executor,
                huleedu_repo=huleedu_repo,
                gateway_overlay_keys=gateway_overlay_keys,
            )
        except BaseException as exc:
            cleanup_errors.append(exc)
    if skriptoteket_producer_mutated:
        try:
            _restore_skriptoteket_runtime_state(
                executor=executor,
                producer_overlay_keys=producer_overlay_keys,
            )
        except BaseException as exc:
            cleanup_errors.append(exc)
    if opened_tunnel_socket is not None:
        try:
            _stop_remote_proof_tunnel(
                executor=executor,
                control_socket=opened_tunnel_socket,
            )
        except BaseException as exc:
            cleanup_errors.append(exc)
    return cleanup_errors


def _add_cleanup_notes(
    primary_error: BaseException,
    cleanup_errors: Sequence[BaseException],
) -> None:
    for cleanup_error in cleanup_errors:
        _add_cleanup_note(primary_error, cleanup_error)


def _add_cleanup_note(target_error: BaseException, cleanup_error: BaseException) -> None:
    cleanup_code = (
        cleanup_error.code
        if isinstance(cleanup_error, LauncherError)
        else type(cleanup_error).__name__
    )
    target_error.add_note(f"cleanup_failed: {cleanup_code}: {cleanup_error}")


def _raise_cleanup_errors(cleanup_errors: Sequence[BaseException]) -> None:
    raise cleanup_errors[0]


def _gateway_signer_fingerprint(
    *,
    executor: CommandExecutor,
    huleedu_repo: Path,
) -> str:
    command = (
        "pdm",
        "run",
        "run-local-pdm",
        "hemma-sir-convert-internal-identity-trust-profile",
        "--environment",
        "local-auth-integration",
    )
    result = _run_required(
        executor,
        command,
        cwd=huleedu_repo,
        env=_huleedu_command_env({}),
        code="huleedu_trust_profile_failed",
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise LauncherError(
            "huleedu_trust_profile_invalid",
            "HuleEdu trust-profile command did not return JSON.",
        ) from exc
    fingerprint = payload.get("spki_sha256_fingerprint")
    if not isinstance(fingerprint, str) or len(fingerprint.strip()) != 64:
        raise LauncherError(
            "huleedu_trust_profile_invalid",
            "HuleEdu trust-profile command did not include a SHA-256 SPKI fingerprint.",
        )
    return fingerprint.strip().lower()


def _wait_for_huleedu_auth_integration(
    *,
    cwd: Path,
    executor: CommandExecutor,
    gateway_env: Mapping[str, str],
) -> CommandResult:
    command = _huleedu_auth_integration_check_command()
    last_result: CommandResult | None = None
    for attempt_index in range(HULEEDU_AUTH_CHECK_ATTEMPTS):
        result = executor(
            command,
            cwd=cwd,
            env=_huleedu_command_env(gateway_env),
            timeout_seconds=HULEEDU_AUTH_CHECK_PROCESS_TIMEOUT_SECONDS,
        )
        if result.returncode == 0:
            return result
        last_result = result
        if attempt_index < HULEEDU_AUTH_CHECK_ATTEMPTS - 1:
            _sleep_for_huleedu_auth_retry(HULEEDU_AUTH_CHECK_RETRY_DELAY_SECONDS)
    if last_result is None:
        raise LauncherError(
            "huleedu_auth_integration_check_failed",
            "HuleEdu auth-integration readiness wait did not run.",
        )
    raise _launcher_command_failed_error(
        command,
        last_result,
        code="huleedu_auth_integration_check_failed",
        cwd=cwd,
    )


def _huleedu_auth_integration_check_command() -> tuple[str, ...]:
    return (
        "pdm",
        "run",
        "run-local-pdm",
        "auth-integration",
        "check",
        "--timeout-seconds",
        str(HULEEDU_AUTH_CHECK_HTTP_TIMEOUT_SECONDS),
    )


def _sleep_for_huleedu_auth_retry(seconds: float) -> None:
    time.sleep(seconds)


def _assert_container_env(
    *,
    executor: CommandExecutor,
    container_name: str,
    key: str,
    expected: str,
    blocker_code: str,
) -> None:
    result = _run_required(
        executor,
        ("docker", "exec", container_name, "printenv", key),
        code=f"{blocker_code}_inspect_failed",
    )
    actual = result.stdout.strip()
    if actual == expected:
        return
    raise LauncherError(
        blocker_code,
        f"{container_name} runtime environment does not match the selected proof lane.",
        {
            "container": container_name,
            "key": key,
            "expected": expected,
            "actual": actual,
        },
    )


def _proof_command(
    *,
    descriptor: TranscriptProofLaneDescriptor,
    dotenv: str,
    proof_artifact_root: Path,
    timeout_seconds: int,
    signer_fingerprint: str,
    audio_file: str | None,
) -> tuple[str, ...]:
    command = (
        "pdm",
        "run",
        "python",
        "-m",
        "scripts.audio_transcription_parity_live",
        "--base-url",
        descriptor.base_url,
        "--dotenv",
        dotenv,
        "--artifact-root",
        str(proof_artifact_root),
        "--sir-convert-proof-lane",
        descriptor.proof_lane,
        "--sir-convert-gateway-backend-url",
        descriptor.container_target_url,
        "--sir-convert-producer-backend-url",
        descriptor.container_target_url,
        "--sir-convert-ready-url",
        descriptor.ready_url,
        "--gateway-signer-fingerprint",
        signer_fingerprint,
        "--sir-convert-trusted-fingerprint",
        signer_fingerprint,
        "--timeout-seconds",
        str(timeout_seconds),
    )
    if audio_file is None:
        return command
    return (*command, "--audio-file", audio_file)


def _run_required(
    executor: CommandExecutor,
    command: Sequence[str],
    *,
    code: str,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout_seconds: int | None = None,
) -> CommandResult:
    result = executor(command, cwd=cwd, env=env, timeout_seconds=timeout_seconds)
    if result.returncode == 0:
        return result
    raise _launcher_command_failed_error(command, result, code=code, cwd=cwd)


def _capture_runtime_evidence(
    *,
    executor: CommandExecutor,
    run_dir: Path,
    readyz_summary: Mapping[str, object] | None,
    blocker: BaseException,
    huleedu_gateway_mutated: bool,
    skriptoteket_producer_mutated: bool,
) -> dict[str, object] | None:
    if not _should_capture_runtime_evidence(
        blocker=blocker,
        huleedu_gateway_mutated=huleedu_gateway_mutated,
        skriptoteket_producer_mutated=skriptoteket_producer_mutated,
    ):
        return None
    try:
        return collect_runtime_evidence(
            executor=executor,
            run_dir=run_dir,
            targets=RUNTIME_EVIDENCE_TARGETS,
            blocker_code=_exception_code(blocker),
            readyz_summary=readyz_summary,
            redact_sensitive_text=_redact_sensitive_text,
        )
    except Exception as exc:
        return {
            "status": "capture_failed",
            "classification": "unknown",
            "error": _exception_diagnostic(exc),
        }


def _should_capture_runtime_evidence(
    *,
    blocker: BaseException,
    huleedu_gateway_mutated: bool,
    skriptoteket_producer_mutated: bool,
) -> bool:
    return (
        _exception_code(blocker) == "transcript_parity_proof_failed"
        and huleedu_gateway_mutated
        and skriptoteket_producer_mutated
    )


def _launcher_command_failed_error(
    command: Sequence[str],
    result: CommandResult,
    *,
    code: str,
    cwd: Path | None,
) -> LauncherError:
    stdout_snippet, stdout_truncated = _command_output_snippet(result.stdout)
    stderr_snippet, stderr_truncated = _command_output_snippet(result.stderr)
    return LauncherError(
        code,
        "Required launcher command failed.",
        {
            "command": list(command),
            "cwd": str(cwd) if cwd is not None else None,
            "returncode": result.returncode,
            "stdout_snippet": stdout_snippet,
            "stdout_truncated": stdout_truncated,
            "stderr_snippet": stderr_snippet,
            "stderr_truncated": stderr_truncated,
        },
    )


def _command_output_snippet(output: str) -> tuple[str, bool]:
    redacted = _redact_sensitive_text(output)
    if len(redacted) <= COMMAND_OUTPUT_SNIPPET_CHARS:
        return redacted, False
    marker = "\n[truncated]"
    return f"{redacted[: COMMAND_OUTPUT_SNIPPET_CHARS - len(marker)]}{marker}", True


def _redact_sensitive_text(value: str) -> str:
    redacted = SENSITIVE_HEADER_PATTERN.sub("[REDACTED]", value)
    redacted = BEARER_TOKEN_PATTERN.sub("Bearer [REDACTED]", redacted)
    redacted = SECRET_ASSIGNMENT_PATTERN.sub("[REDACTED]", redacted)
    for key, secret_value in os.environ.items():
        if (
            SECRET_ENV_KEY_PATTERN.search(key)
            and len(secret_value) >= 8
            and secret_value in redacted
        ):
            redacted = redacted.replace(secret_value, "[REDACTED]")
    return redacted


def _write_failure_summary(
    *,
    run_dir: Path,
    descriptor: TranscriptProofLaneDescriptor,
    readyz_summary: Mapping[str, object] | None,
    blocker: BaseException,
    cleanup_errors: Sequence[BaseException],
    runtime_evidence: Mapping[str, object] | None,
) -> None:
    _write_json(
        run_dir / "failure-summary.json",
        {
            "status": "failed",
            "observed_at": _utc_now(),
            "blocker_code": _exception_code(blocker),
            "blocker_message": _safe_summary_value(str(blocker)),
            "metadata": _exception_metadata(blocker),
            "cleanup_diagnostics": [_exception_diagnostic(error) for error in cleanup_errors],
            "exception_notes": _exception_notes(blocker),
            "descriptor": _descriptor_summary(descriptor),
            "readyz": dict(readyz_summary) if readyz_summary is not None else None,
            "runtime_evidence": (dict(runtime_evidence) if runtime_evidence is not None else None),
        },
    )


def _exception_code(exc: BaseException) -> str:
    if isinstance(exc, LauncherError):
        return exc.code
    return type(exc).__name__


def _exception_metadata(exc: BaseException) -> dict[str, object]:
    if not isinstance(exc, LauncherError):
        return {}
    return {str(key): _safe_summary_value(value) for key, value in exc.metadata.items()}


def _exception_diagnostic(exc: BaseException) -> dict[str, object]:
    return {
        "code": _exception_code(exc),
        "message": _safe_summary_value(str(exc)),
        "metadata": _exception_metadata(exc),
    }


def _exception_notes(exc: BaseException) -> list[str]:
    notes = getattr(exc, "__notes__", ())
    if not isinstance(notes, list):
        return []
    return [_safe_summary_value(note) for note in notes if isinstance(note, str)]


def _safe_summary_value(value: object) -> object:
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        snippet, truncated = _command_output_snippet(value)
        return f"{snippet}\n[summary-truncated]" if truncated else snippet
    if isinstance(value, Mapping):
        return {str(key): _safe_summary_value(item) for key, item in value.items()}
    if isinstance(value, Sequence):
        return [_safe_summary_value(item) for item in value]
    return _safe_summary_value(str(value))


def _gateway_overlay_env(descriptor: TranscriptProofLaneDescriptor) -> dict[str, str]:
    return {
        "API_GATEWAY_SIR_CONVERT_PROTECTED_API_EDGE_ENABLED": "true",
        "API_GATEWAY_SIR_CONVERT_PROTECTED_API_PREFIX": "/sir-convert",
        GATEWAY_BACKEND_ENV_KEY: descriptor.container_target_url,
        "API_GATEWAY_SIR_CONVERT_PROTECTED_API_INTERNAL_IDENTITY_AUDIENCE": ("sir-convert-a-lot"),
    }


def _producer_overlay_env(descriptor: TranscriptProofLaneDescriptor) -> dict[str, str]:
    return {
        PRODUCER_BACKEND_ENV_KEY: descriptor.container_target_url,
    }


def _write_runtime_overlays(run_dir: Path, descriptor: TranscriptProofLaneDescriptor) -> None:
    _write_env_file(run_dir / "huleedu-gateway.env", _gateway_overlay_env(descriptor))
    _write_env_file(run_dir / "skriptoteket-producer.env", _producer_overlay_env(descriptor))


def _write_env_file(path: Path, values: Mapping[str, str]) -> None:
    lines = [f"{key}={value}" for key, value in sorted(values.items())]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _merged_env(overrides: Mapping[str, str]) -> dict[str, str]:
    return {**os.environ, **overrides}


def _huleedu_command_env(overrides: Mapping[str, str]) -> dict[str, str]:
    return {**_sanitized_huleedu_base_env(), **overrides}


def _huleedu_restore_env(removed_keys: Sequence[str]) -> dict[str, str]:
    env = _sanitized_huleedu_base_env()
    for key in removed_keys:
        env.pop(key, None)
    return env


def _sanitized_huleedu_base_env() -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("PDM_") and key not in HULEEDU_ENV_REMOVED_KEYS
    }
    path_value = env.get("PATH")
    if path_value is not None:
        env["PATH"] = _path_without_current_venv_bin(path_value)
    return env


def _path_without_current_venv_bin(path_value: str) -> str:
    current_venv_bin = (Path.cwd() / ".venv" / "bin").resolve(strict=False)
    retained_parts: list[str] = []
    for part in path_value.split(os.pathsep):
        if part and Path(part).expanduser().resolve(strict=False) == current_venv_bin:
            continue
        retained_parts.append(part)
    return os.pathsep.join(retained_parts)


def _restore_env(removed_keys: Sequence[str]) -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if key not in removed_keys}


def _restore_huleedu_gateway_state(
    *,
    executor: CommandExecutor,
    huleedu_repo: Path,
    gateway_overlay_keys: Sequence[str],
) -> None:
    _run_required(
        executor,
        ("pdm", "run", "run-local-pdm", "dev-recreate", "api_gateway_service"),
        cwd=huleedu_repo,
        env=_huleedu_restore_env(gateway_overlay_keys),
        code="huleedu_gateway_restore_failed",
    )


def _restore_skriptoteket_runtime_state(
    *,
    executor: CommandExecutor,
    producer_overlay_keys: Sequence[str],
) -> None:
    _run_required(
        executor,
        ("pdm", "run", "dev-stack", "recreate", "web", "worker"),
        cwd=Path.cwd(),
        env=_restore_env(producer_overlay_keys),
        code="skriptoteket_restore_failed",
    )


def _new_run_dir(root: Path) -> Path:
    run_dir = root / datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n")


def _descriptor_summary(descriptor: TranscriptProofLaneDescriptor) -> dict[str, object]:
    return {
        "lane": descriptor.lane_name,
        "proof_lane": descriptor.proof_lane,
        "local_tunnel_port": descriptor.local_tunnel_port,
        "container_target_url": descriptor.container_target_url,
        "ready_url": descriptor.ready_url,
        "expected_service_profile": descriptor.expected_service_profile,
        "base_url": descriptor.base_url,
    }


def _readyz_summary(readyz: Mapping[str, object]) -> dict[str, object]:
    return {
        "ready": readyz.get("ready"),
        "service_revision": readyz.get("service_revision"),
        "service_profile": readyz.get("service_profile"),
        "expected_service_profile": readyz.get("expected_service_profile"),
    }


def _string_field(value: Mapping[str, object], key: str) -> str | None:
    item = value.get(key)
    return item if isinstance(item, str) and item.strip() else None


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _print_exception_notes(exc: BaseException) -> None:
    notes = getattr(exc, "__notes__", ())
    if not isinstance(notes, list):
        return
    for note in notes:
        if isinstance(note, str):
            print(note, file=sys.stderr)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except LauncherError as exc:
        print(f"{exc.code}: {exc}", file=sys.stderr)
        _print_exception_notes(exc)
        raise SystemExit(1) from exc
