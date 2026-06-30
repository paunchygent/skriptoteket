"""Story 58 authenticated Gateway stale-replay proof.

Domain purpose:
    Drive a single Sir Convert Service API v2 stale DigiExam replay through the
    HuleEdu browser-session Gateway edge and retain live service evidence for
    Story 58 closeout.

Relationships:
    - Uses the shared Playwright login helper for the HuleEdu browser-session
      ceremony.
    - Uses correction-session runtime evidence monitors to retain Docker logs
      from the services that handled the replay.
    - Exercises Sir Convert's create-job idempotency policy through the
      product edge, not by mutating production idempotency state.
"""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from playwright.sync_api import Page, sync_playwright

from scripts._correction_session_runtime_evidence import (
    start_correction_session_runtime_evidence,
)
from scripts._playwright_auth import login_via_auth_entry
from scripts._playwright_browser import launch_chromium
from scripts._playwright_config import get_config
from scripts._proof_manifest import write_proof_manifest
from scripts._story58_gateway_stale_replay_inputs import (
    add_story58_gateway_sensitive_input_args,
    resolve_story58_gateway_sensitive_inputs,
)
from scripts._story58_gateway_stale_replay_request import (
    build_story58_gateway_job_spec,
    stable_story58_gateway_json,
    story58_request_fingerprint,
    story58_scope_digest,
    story58_sha256_bytes,
)

ARTIFACT_ROOT = Path(".artifacts/story-58-gateway-stale-replay")
APP_PATH = "/apps/documents.conversion_hub"
EXPECTED_REATTEMPT_REASON = "terminal_artifact_contract_incompatible"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Story 58 Gateway stale-replay proof")
    parser.add_argument("--base-url", default="https://skriptoteket.hule.education")
    parser.add_argument("--dotenv", default=".artifacts/proof-env/pr-0406-production.env")
    parser.add_argument("--email", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--source-dxe", required=True)
    parser.add_argument("--expected-reattempt-of-job-id", required=True)
    parser.add_argument("--expected-request-fingerprint", required=True)
    parser.add_argument("--expected-scope-digest", required=True)
    add_story58_gateway_sensitive_input_args(parser)
    parser.add_argument("--artifact-root", default=str(ARTIFACT_ROOT))
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument(
        "--capture-local-backend-logs",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--capture-hemma-service-logs",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--hemma-ssh-host", default="hemma")
    return parser.parse_args(argv)


def _run_dir(root: Path) -> Path:
    path = root / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path.mkdir(parents=True, exist_ok=False)
    return path


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _config_argv(args: argparse.Namespace) -> list[str]:
    config_args = ["--base-url", args.base_url, "--dotenv", args.dotenv]
    if args.email:
        config_args.extend(["--email", args.email])
    if args.password:
        config_args.extend(["--password", args.password])
    return config_args


def _protected_api_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.hostname == "skriptoteket.hule.education":
        return "https://api.hule.education"
    return base_url.rstrip("/")


def _load_shared_csrf_token(page: Page, *, api_base_url: str) -> dict[str, object]:
    response = page.request.get(f"{api_base_url.rstrip('/')}/v1/auth/csrf", timeout=15_000)
    payload = response.json() if response.status == 200 else {}
    token = payload.get("csrf_token") if isinstance(payload, dict) else None
    if not isinstance(token, str) or token == "":
        raise AssertionError(f"Could not load shared CSRF token; status={response.status}.")
    return {
        "status": response.status,
        "source": "/v1/auth/csrf",
        "token": token,
        "csrf_value_retained": False,
    }


def _session_from_browser(page: Page, *, urls: Sequence[str]) -> requests.Session:
    session = requests.Session()
    for cookie in page.context.cookies(list(urls)):
        name = cookie.get("name")
        value = cookie.get("value")
        if not isinstance(name, str) or not isinstance(value, str):
            continue
        session.cookies.set(
            name,
            value,
            domain=cookie.get("domain") if isinstance(cookie.get("domain"), str) else None,
            path=cookie.get("path") if isinstance(cookie.get("path"), str) else "/",
        )
    return session


def _scrub_create_payload(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        return {"non_object_payload": True}
    job = payload.get("job") if isinstance(payload.get("job"), dict) else {}
    idempotency = payload.get("idempotency") if isinstance(payload.get("idempotency"), dict) else {}
    return {
        "job": {
            "job_id": job.get("job_id"),
            "status": job.get("status"),
            "route_id": job.get("route_id"),
            "source_format": job.get("source_format"),
            "output_format": job.get("output_format"),
        },
        "idempotency": {
            "state": idempotency.get("state"),
            "idempotent_replay": idempotency.get("idempotent_replay"),
            "active_job_id": idempotency.get("active_job_id"),
            "attempt_count": idempotency.get("attempt_count"),
            "current_attempt": idempotency.get("current_attempt"),
            "previous_attempts": idempotency.get("previous_attempts"),
            "replayed_job_id": idempotency.get("replayed_job_id"),
            "reattempt_of_job_id": idempotency.get("reattempt_of_job_id"),
            "reason": idempotency.get("reason"),
        },
    }


def _scrub_job_payload(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        return {"non_object_payload": True}
    job = payload.get("job") if isinstance(payload.get("job"), dict) else payload
    progress = job.get("progress") if isinstance(job.get("progress"), dict) else {}
    return {
        "job_id": job.get("job_id"),
        "status": job.get("status"),
        "route_id": job.get("route_id"),
        "source_format": job.get("source_format"),
        "output_format": job.get("output_format"),
        "phase": progress.get("phase") or progress.get("stage") or job.get("stage"),
    }


def _scrub_artifacts_payload(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        return {"non_object_payload": True}
    artifacts = payload.get("artifacts")
    rows = artifacts if isinstance(artifacts, list) else []
    return {
        "artifacts": [
            {
                "artifact_key": row.get("artifact_key"),
                "availability": row.get("availability"),
                "content_type": row.get("content_type"),
                "size_bytes": row.get("size_bytes"),
                "content_sha256": row.get("content_sha256"),
            }
            for row in rows
            if isinstance(row, dict)
        ]
    }


def _json_response(response: requests.Response) -> object:
    try:
        return response.json()
    except ValueError:
        return {"error": {"code": "non_json_response"}}


def _assert_create_response(
    *,
    payload: Mapping[str, object],
    expected_reattempt_of_job_id: str,
) -> str:
    idempotency = payload.get("idempotency")
    job = payload.get("job")
    if not isinstance(idempotency, dict) or not isinstance(job, dict):
        raise AssertionError("Create response did not include job and idempotency payloads.")
    if idempotency.get("state") != "service_reattempt":
        raise AssertionError(f"Expected service_reattempt, got {idempotency.get('state')!r}.")
    if idempotency.get("reason") != EXPECTED_REATTEMPT_REASON:
        raise AssertionError(f"Unexpected reattempt reason: {idempotency.get('reason')!r}.")
    if idempotency.get("reattempt_of_job_id") != expected_reattempt_of_job_id:
        raise AssertionError("Reattempt lineage did not point at the expected stale job.")
    active_job_id = idempotency.get("active_job_id")
    job_id = job.get("job_id")
    if not isinstance(active_job_id, str) or active_job_id != job_id:
        raise AssertionError("Create response active job id did not match returned job.")
    return active_job_id


def _gateway_headers(
    *, csrf_token: str, idempotency_key: str, correlation_id: str
) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Idempotency-Key": idempotency_key,
        "X-CSRF-Token": csrf_token,
        "X-Correlation-ID": correlation_id,
    }


def _poll_job(
    *,
    session: requests.Session,
    api_base_url: str,
    job_id: str,
    correlation_id: str,
    timeout_seconds: int,
    poll_seconds: float,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    observations: list[dict[str, object]] = []
    deadline = time.monotonic() + timeout_seconds
    headers = {"Accept": "application/json", "X-Correlation-ID": correlation_id}
    while time.monotonic() < deadline:
        response = session.get(
            f"{api_base_url.rstrip('/')}/sir-convert/v2/convert/jobs/{job_id}",
            headers=headers,
            timeout=30,
        )
        payload = _json_response(response)
        observed = {
            "status_code": response.status_code,
            "payload": _scrub_job_payload(payload),
        }
        observations.append(observed)
        status = (
            observed["payload"].get("status") if isinstance(observed["payload"], dict) else None
        )
        if status in {"succeeded", "failed", "canceled"}:
            return observations, observed
        time.sleep(poll_seconds)
    raise AssertionError(f"Timed out waiting for job {job_id} to reach a terminal state.")


def _fetch_artifacts(
    *,
    session: requests.Session,
    api_base_url: str,
    job_id: str,
    correlation_id: str,
) -> dict[str, object]:
    response = session.get(
        f"{api_base_url.rstrip('/')}/sir-convert/v2/convert/jobs/{job_id}/artifacts",
        headers={"Accept": "application/json", "X-Correlation-ID": correlation_id},
        timeout=30,
    )
    return {
        "status_code": response.status_code,
        "payload": _scrub_artifacts_payload(_json_response(response)),
    }


def run(argv: Sequence[str] | None = None) -> dict[str, object]:
    args = _parse_args(argv)
    sensitive_inputs = resolve_story58_gateway_sensitive_inputs(
        idempotency_key=args.idempotency_key,
        idempotency_key_env=args.idempotency_key_env,
        idempotency_key_file=args.idempotency_key_file,
        expected_owner_scope=args.expected_owner_scope,
        expected_owner_scope_env=args.expected_owner_scope_env,
        expected_owner_scope_file=args.expected_owner_scope_file,
    )
    config = get_config(_config_argv(args))
    artifact_dir = _run_dir(Path(args.artifact_root))
    source = Path(args.source_dxe).resolve()
    file_bytes = source.read_bytes()
    job_spec = build_story58_gateway_job_spec(source.name)
    job_spec_json = stable_story58_gateway_json(job_spec)
    file_sha256 = story58_sha256_bytes(file_bytes)
    request_fingerprint = story58_request_fingerprint(
        job_spec_json=job_spec_json,
        file_sha256=file_sha256,
    )
    summary: dict[str, object] = {
        "artifact_dir": str(artifact_dir),
        "started_at": datetime.now(UTC).isoformat(),
        "base_url": config.base_url,
        "source": {
            "sha256": f"sha256:{file_sha256}",
            "filename_retained": False,
            "uploaded_bytes_retained": False,
        },
        "expected": {
            "reattempt_of_job_id": args.expected_reattempt_of_job_id,
            "request_fingerprint": args.expected_request_fingerprint,
            "scope_digest": args.expected_scope_digest,
            "reason": EXPECTED_REATTEMPT_REASON,
        },
        "computed": {
            "request_fingerprint": request_fingerprint,
        },
        "csrf_value_retained": False,
        "service_responses": [],
        "screenshots": [],
    }
    write_proof_manifest(artifact_dir, summary)
    if request_fingerprint != args.expected_request_fingerprint:
        raise AssertionError(
            "Computed request fingerprint did not match the expected stale record."
        )

    runtime_evidence = start_correction_session_runtime_evidence(
        artifact_dir=artifact_dir,
        base_url=config.base_url,
        capture_local_backend_logs=args.capture_local_backend_logs,
        capture_hemma_service_logs=args.capture_hemma_service_logs,
        hemma_ssh_host=args.hemma_ssh_host,
    )
    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        page = browser.new_page()
        try:
            login_via_auth_entry(
                page,
                base_url=config.base_url.rstrip("/"),
                email=config.email,
                password=config.password,
                next_path=APP_PATH,
                success_heading_pattern=r"^Konvertera prov$",
                recover_to_next_path=True,
                attempts=3,
                failure_artifacts_dir=artifact_dir,
                failure_screenshot_name="login-failure.png",
                rate_limit_backoff=True,
                form_timeout_ms=15_000,
                success_timeout_ms=60_000,
            )
            screenshot_path = artifact_dir / "01-authenticated.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            summary["screenshots"] = [str(screenshot_path)]
            api_base_url = _protected_api_base_url(config.base_url)
            csrf = _load_shared_csrf_token(page, api_base_url=api_base_url)
            summary["csrf"] = {key: value for key, value in csrf.items() if key != "token"}
            session = _session_from_browser(page, urls=(config.base_url, api_base_url))
            computed = summary["computed"]
            if not isinstance(computed, dict):
                raise AssertionError("Proof summary computed section was not initialized.")
            computed["scope_digest"] = story58_scope_digest(
                owner_scope=sensitive_inputs.expected_owner_scope,
                idempotency_key=sensitive_inputs.idempotency_key,
            )
            if computed["scope_digest"] != args.expected_scope_digest:
                raise AssertionError("Computed scope digest did not match stale record.")
            correlation_id = f"story58-stale-replay-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
            response = session.post(
                f"{api_base_url.rstrip('/')}/sir-convert/v2/convert/jobs",
                params={"wait_seconds": "0"},
                headers=_gateway_headers(
                    csrf_token=str(csrf["token"]),
                    idempotency_key=sensitive_inputs.idempotency_key,
                    correlation_id=correlation_id,
                ),
                data={"job_spec": job_spec_json},
                files={
                    "file": (
                        source.name,
                        file_bytes,
                        "application/octet-stream",
                    )
                },
                timeout=90,
            )
            create_payload = _json_response(response)
            create_evidence = {
                "kind": "create_job",
                "method": "POST",
                "path": "/sir-convert/v2/convert/jobs?wait_seconds=0",
                "status_code": response.status_code,
                "request": {
                    "idempotency_key_retained": False,
                    "idempotency_key_sha256": (
                        f"sha256:{story58_sha256_bytes(sensitive_inputs.idempotency_key.encode('utf-8'))}"
                    ),
                    "correlation_id": correlation_id,
                    "job_spec_sha256": (
                        f"sha256:{story58_sha256_bytes(job_spec_json.encode('utf-8'))}"
                    ),
                    "source_sha256": f"sha256:{file_sha256}",
                },
                "payload": _scrub_create_payload(create_payload),
            }
            summary["service_responses"].append(create_evidence)
            write_proof_manifest(artifact_dir, summary)
            if response.status_code >= 400:
                raise AssertionError(
                    f"Gateway create-job replay failed with HTTP {response.status_code}."
                )
            if not isinstance(create_payload, dict):
                raise AssertionError("Gateway create-job replay returned non-object JSON.")
            active_job_id = _assert_create_response(
                payload=create_payload,
                expected_reattempt_of_job_id=args.expected_reattempt_of_job_id,
            )
            observations, terminal = _poll_job(
                session=session,
                api_base_url=api_base_url,
                job_id=active_job_id,
                correlation_id=correlation_id,
                timeout_seconds=args.timeout_seconds,
                poll_seconds=args.poll_seconds,
            )
            summary["job_observations"] = observations
            summary["terminal_job"] = terminal
            if terminal.get("payload", {}).get("status") != "succeeded":
                raise AssertionError(f"Reattempt job did not succeed: {terminal!r}")
            summary["artifact_manifest"] = _fetch_artifacts(
                session=session,
                api_base_url=api_base_url,
                job_id=active_job_id,
                correlation_id=correlation_id,
            )
            summary["completed_at"] = datetime.now(UTC).isoformat()
            write_proof_manifest(artifact_dir, summary)
        except Exception:
            summary["failed_at"] = datetime.now(UTC).isoformat()
            if not page.is_closed():
                failure_path = artifact_dir / "failure.png"
                page.screenshot(path=str(failure_path), full_page=True)
                summary.setdefault("screenshots", []).append(str(failure_path))
            write_proof_manifest(artifact_dir, summary)
            raise
        finally:
            runtime_evidence.stop()
            runtime_evidence.attach_to_summary(summary, artifact_dir)
            write_proof_manifest(artifact_dir, summary)
            browser.close()
    return summary


def main(argv: Sequence[str] | None = None) -> None:
    summary = run(argv)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
