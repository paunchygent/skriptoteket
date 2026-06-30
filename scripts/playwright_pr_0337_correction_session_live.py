"""PR-0337 live proof for durable Exam Converter correction sessions.

Domain purpose:
    Exercise the authenticated correction-session workflow through browser
    reload, Skriptoteket readback, Sir Convert stateless replay, and artifact
    download inspection.

Relationships:
    - Targets `PR-0337` / `ST-21-04` durable teacher correction proof.
    - Uses the shared HuleEdu browser-session login helper.
    - Retains UI, network, replay, artifact, and service-log evidence under
      `.artifacts/playwright-pr-0337-correction-session-live/`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import signal
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from zipfile import ZipFile

from playwright.sync_api import (
    Locator,
    Page,
    Response,
    expect,
    sync_playwright,
)
from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
)
from pypdf import PdfReader

from scripts._correction_session_runtime_evidence import (
    start_correction_session_runtime_evidence,
)
from scripts._playwright_auth import login_via_auth_entry
from scripts._playwright_browser import launch_chromium
from scripts._playwright_config import get_config
from scripts._pr_0331_reviewed_ai_facit_artifacts import (
    FORBIDDEN_ARTIFACT_TEXT,
    inspect_qti,
)
from scripts._proof_manifest import write_proof_manifest
from scripts._story58_artifact_route_probe import (
    probe_safe_correction_replay_artifacts,
    story58_latest_correction_request_context,
    story58_snapshot_evidence_with_request_context,
)
from scripts._story58_artifact_set_invariants import (
    record_story58_artifact_set_snapshot,
    refresh_story58_artifact_set_invariants,
)
from scripts._story58_mismatched_artifact_probe import (
    probe_mismatched_replay_artifact_download,
    safe_correction_replay_artifact_references,
)
from scripts._story58_private_request_capture import Story58PrivateRequestCapture

ARTIFACT_ROOT = Path(".artifacts/playwright-pr-0337-correction-session-live")
DEFAULT_SOURCE_DXE = Path(
    ".artifacts/pr-0325-live/fresh-inputs/1811577114-ekologiprov-v-49-25d-e-fresh-probe.dxe"
)
APP_PATH = "/apps/documents.conversion_hub"
CORRECTION_APPLY_MARKER = "/sir-convert/v2/exam-authoring/corrections/apply"
CORRECTION_SESSION_MARKER = "/api/v1/apps/documents.conversion_hub/exam-converter/jobs/"
CORRECTION_SOURCE_STATE_MARKER = "/sir-convert/v2/exam-authoring/corrections/source-state/issue"
SIR_CONVERT_SUBMIT_MARKER = "/sir-convert/v2/convert/jobs"
USER_FILE_SAVE_MARKER = "/api/v1/apps/documents.conversion_hub/exam-converter/artifacts/save"
CORRECTION_REPLAY_ROUTE_MARKER = "/correction-replays/"
TARGET_ITEM_ID = "item-001"
UPDATED_ITEM_POINTS = "3"
UPDATED_ITEM_PROMPT = "Vilken process frigör energi ur socker med hjälp av syre?"
DEFAULT_PROOF_TIMEOUT_SECONDS = 60
COMPACT_REVIEW_REQUIRED_LABEL = "Granska"
COMPACT_COMPLETE_LABEL = "Klart"
COMPACT_TEACHER_MODIFIED_LABEL = "Ändrat"
COMPACT_VALIDATION_REQUIRED_LABEL = "Kontrollera"
MANUAL_GAP_FILL_VALUE_PREFIX = "live-proof-facit"
START_CONVERSION_SELECTOR = '[data-test="exam-converter-start-conversion"]'
SELECTED_QUESTION_DETAIL_SELECTOR = '[data-test="exam-converter-selected-question-detail"]'
MANUAL_ANSWER_KEY_EDITOR_SELECTOR = '[data-test="exam-converter-manual-answer-key-editor"]'
MANUAL_ANSWER_KEY_SAVE_SELECTOR = '[data-test="exam-converter-apply-manual-answer-key-action"]'
ADVISORY_ANSWER_KEY_PANEL_SELECTOR = '[data-test="exam-converter-selected-question-ai-suggestion"]'
ADVISORY_ANSWER_KEY_ACCEPT_SELECTOR = (
    '[data-test="exam-converter-accept-advisory-answer-key-action"]'
)
ADVISORY_ANSWER_KEY_EDIT_SELECTOR = '[data-test="exam-converter-edit-advisory-answer-key-action"]'
LocatorRoot = Page | Locator


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PR-0337 durable correction-session live proof")
    parser.add_argument("--source-dxe", default=str(DEFAULT_SOURCE_DXE))
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--dotenv", default=".env")
    parser.add_argument("--artifact-root", default=str(ARTIFACT_ROOT))
    parser.add_argument("--timeout-seconds", default=DEFAULT_PROOF_TIMEOUT_SECONDS, type=int)
    parser.add_argument(
        "--preserve-source-filename",
        action="store_true",
        help="Upload the provided source path directly instead of copying it to a run-scoped name.",
    )
    parser.add_argument(
        "--expect-submit-idempotency-reason",
        default=None,
        help="Require at least one create-job response with this idempotency reason.",
    )
    parser.add_argument(
        "--allow-existing-ready-session",
        action="store_true",
        help=(
            "When the uploaded file already has a ready persisted correction session, "
            "prove replay download/save actions without creating more correction intents."
        ),
    )
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
    parser.add_argument(
        "--story58-private-request-capture-dir",
        type=Path,
        default=None,
        help=(
            "Private out-of-band directory for raw Story 58 correction request "
            "bodies. Public manifests retain only approved digests/counts."
        ),
    )
    return parser.parse_args(argv)


def _run_dir(root: Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = root / timestamp
    path.mkdir(parents=True, exist_ok=False)
    return path


def _write_summary(summary: dict[str, Any], artifact_dir: Path) -> None:
    write_proof_manifest(artifact_dir, summary)


def _write_final_summary(
    summary: dict[str, Any],
    artifact_dir: Path,
    *,
    active_exception: BaseException | None,
) -> None:
    try:
        _write_summary(summary, artifact_dir)
    except Exception as summary_exc:
        if active_exception is None:
            raise
        _record_failure_artifact_error(
            summary,
            artifact="final_summary",
            exc=summary_exc,
        )


def _mark_progress(summary: dict[str, Any], artifact_dir: Path, step: str) -> None:
    summary.setdefault("progress", []).append({"at": datetime.now(UTC).isoformat(), "step": step})
    _write_summary(summary, artifact_dir)


def _safe_url(url: str) -> str:
    return urlparse(url).path


def _safe_url_with_query(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path


def _fresh_source_copy(source_dxe: Path, artifact_dir: Path) -> Path:
    fresh_path = artifact_dir / f"pr-0337-{artifact_dir.name}-{source_dxe.name}"
    shutil.copyfile(source_dxe, fresh_path)
    return fresh_path


def _exam_converter_main(page: Page) -> Any:
    return page.locator('main[aria-labelledby="exam-converter-auth-title"]')


def _json_request_payload(request: Any) -> dict[str, Any] | None:
    post_data = request.post_data
    if not post_data:
        return None
    try:
        payload = json.loads(post_data)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _request_body_sha256(request: Any) -> str | None:
    post_data = request.post_data
    if post_data is None:
        return None
    if isinstance(post_data, bytes):
        body = post_data
    elif isinstance(post_data, str):
        body = post_data.encode("utf-8")
    else:
        return None
    return hashlib.sha256(body).hexdigest()


def _summarize_apply_request(request: Any) -> dict[str, Any]:
    payload = _json_request_payload(request) or {}
    corrections = payload.get("corrections")
    correction_rows = corrections if isinstance(corrections, list) else []
    summary: dict[str, Any] = {
        "correction_count": len(correction_rows),
        "method": request.method,
        "path": _safe_url(request.url),
        "requested_targets": payload.get("requested_targets"),
        "schema_version": payload.get("schema_version"),
    }
    body_sha256 = _request_body_sha256(request)
    if body_sha256:
        summary["body_sha256"] = body_sha256
    if correction_rows:
        summary["corrections_sha256"] = hashlib.sha256(
            json.dumps(correction_rows, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
    _copy_safe_string(summary, "request_id", payload.get("request_id"))
    _copy_safe_string(summary, "request_digest", payload.get("request_digest"))
    _copy_safe_string(summary, "request_digest", payload.get("request_sha256"))
    _copy_safe_string(summary, "request_digest", payload.get("correction_request_sha256"))
    source_binding = payload.get("source_binding")
    source_payload = source_binding if isinstance(source_binding, dict) else payload
    _copy_safe_string(summary, "job_id", payload.get("job_id"))
    _copy_safe_string(summary, "job_id", payload.get("source_job_id"))
    _copy_safe_string(summary, "source_bundle_id", source_payload.get("source_bundle_id"))
    _copy_safe_string(summary, "source_file_sha256", source_payload.get("source_file_sha256"))
    _copy_safe_string(summary, "source_state_sha256", source_payload.get("source_state_sha256"))
    return summary


def _copy_safe_string(target: dict[str, Any], key: str, value: object) -> None:
    if key in target:
        return
    if isinstance(value, str) and value:
        target[key] = value


def _summarize_json_payload(payload: dict[str, Any]) -> dict[str, Any]:
    report = payload.get("correction_report")
    accepted_entries = report.get("accepted_entries", []) if isinstance(report, dict) else []
    rejected_entries = report.get("rejected_entries", []) if isinstance(report, dict) else []
    target_readiness = payload.get("target_readiness")
    readiness_rows = (
        target_readiness.get("targets", []) if isinstance(target_readiness, dict) else []
    )
    effective_state = payload.get("effective_state")
    active_intents = payload.get("active_intents")
    target_rows = [
        {
            "artifact_key": row.get("artifact_key"),
            "export_enabled": row.get("export_enabled"),
            "message": row.get("message"),
            "message_key": row.get("message_key"),
            "readiness": row.get("readiness"),
            "reason_code": row.get("reason_code"),
            "target": row.get("target"),
            "teacher_action": row.get("teacher_action"),
        }
        for row in readiness_rows
        if isinstance(row, dict)
    ]
    summary: dict[str, Any] = {
        "accepted_correction_count": len(accepted_entries)
        if isinstance(accepted_entries, list)
        else 0,
        "active_intent_count": len(active_intents) if isinstance(active_intents, list) else None,
        "accepted_kinds": [
            entry.get("kind") for entry in accepted_entries if isinstance(entry, dict)
        ],
        "rejected_correction_count": len(rejected_entries)
        if isinstance(rejected_entries, list)
        else 0,
        "effective_item_count": len(effective_state.get("items", []))
        if isinstance(effective_state, dict)
        else None,
        "target_readiness_rows": target_rows,
        "exportable_targets": [
            {
                "artifact_key": row.get("artifact_key"),
                "readiness": row.get("readiness"),
                "target": row.get("target"),
            }
            for row in readiness_rows
            if isinstance(row, dict) and row.get("export_enabled") is True
        ],
        "ready_targets": [
            row.get("target")
            for row in readiness_rows
            if isinstance(row, dict) and row.get("export_enabled") is True
        ],
        "request_id": payload.get("request_id"),
        "schema_version": payload.get("schema_version"),
        "session_version": payload.get("session_version"),
    }
    replay_references = safe_correction_replay_artifact_references(payload)
    if replay_references:
        summary["correction_replay_artifact_references"] = replay_references
    return summary


def _summarize_create_job_payload(payload: dict[str, Any]) -> dict[str, Any]:
    job = payload.get("job")
    idempotency = payload.get("idempotency")
    job_payload = job if isinstance(job, dict) else {}
    idempotency_payload = idempotency if isinstance(idempotency, dict) else {}
    previous_attempts = idempotency_payload.get("previous_attempts")
    previous_attempt_rows = previous_attempts if isinstance(previous_attempts, list) else []
    return {
        "idempotency": {
            "active_job_id": idempotency_payload.get("active_job_id"),
            "attempt_count": idempotency_payload.get("attempt_count"),
            "current_attempt": idempotency_payload.get("current_attempt"),
            "idempotent_replay": idempotency_payload.get("idempotent_replay"),
            "previous_attempts": [
                {
                    "failure_retryable": row.get("failure_retryable"),
                    "job_id": row.get("job_id"),
                    "status": row.get("status"),
                }
                for row in previous_attempt_rows
                if isinstance(row, dict)
            ],
            "reason": idempotency_payload.get("reason"),
            "reattempt_of_job_id": idempotency_payload.get("reattempt_of_job_id"),
            "replayed_job_id": idempotency_payload.get("replayed_job_id"),
            "state": idempotency_payload.get("state"),
        },
        "job": {
            "job_id": job_payload.get("job_id"),
            "output_format": job_payload.get("output_format"),
            "source_format": job_payload.get("source_format"),
            "status": job_payload.get("status"),
        },
    }


def _download_response_predicate(response: Response) -> bool:
    parsed = urlparse(response.url)
    query = parse_qs(parsed.query)
    return (
        "/sir-convert/v2/convert/jobs/" in parsed.path
        and CORRECTION_REPLAY_ROUTE_MARKER in parsed.path
        and "/artifacts/" in parsed.path
        and bool(query.get("content_sha256"))
        and response.request.method == "GET"
        and "application/json" not in (response.headers.get("content-type") or "")
    )


def _correction_replay_artifact_evidence(response: Response) -> dict[str, str]:
    parsed = urlparse(response.url)
    route_tail = parsed.path.split(CORRECTION_REPLAY_ROUTE_MARKER, 1)[1]
    route_parts = route_tail.split("/")
    query = parse_qs(parsed.query)
    content_sha256 = query.get("content_sha256", [""])[0]
    artifact_set_id = route_parts[0] if len(route_parts) >= 3 else ""
    artifact_key = route_parts[-1] if route_parts else ""
    if not artifact_set_id or not artifact_key or not content_sha256:
        raise AssertionError("Corrected artifact response did not include replay route authority.")
    return {
        "artifact_key": artifact_key,
        "artifact_set_id": artifact_set_id,
        "content_sha256": content_sha256,
    }


def _download_replayed_file(
    page: Page, *, artifact_key: str, artifact_dir: Path, expected_filename: str
) -> tuple[Path, dict[str, Any]]:
    button = page.locator(f'[data-test="exam-converter-download-file-{artifact_key}"]').first
    expect(button).to_be_enabled(timeout=30_000)
    with page.expect_response(_download_response_predicate, timeout=30_000) as response_info:
        with page.expect_download() as download_info:
            button.click()
    response = response_info.value
    if response.status >= 400:
        raise AssertionError(f"Artifact download failed with HTTP {response.status}.")
    replay_evidence = _correction_replay_artifact_evidence(response)
    replay_artifact_key = replay_evidence["artifact_key"]
    if not replay_artifact_key.startswith("correction_replay_"):
        raise AssertionError("Corrected download did not use a replay-scoped artifact key.")
    download = download_info.value
    output_path = artifact_dir / (download.suggested_filename or f"{artifact_key}.bin")
    if output_path.name != expected_filename:
        raise AssertionError(
            f"Replay download used {output_path.name}, expected {expected_filename}."
        )
    download.save_as(str(output_path))
    return output_path, {
        "content_type": response.headers.get("content-type"),
        "content_sha256": replay_evidence["content_sha256"],
        "path": _safe_url_with_query(response.url),
        "replay_artifact_key": replay_artifact_key,
        "replay_artifact_set_id": replay_evidence["artifact_set_id"],
        "status": response.status,
        "suggested_filename": output_path.name,
        "ui_artifact_key": artifact_key,
    }


def _record_story58_product_route_snapshot(
    summary: dict[str, Any],
    evidence: dict[str, Any],
    *,
    observed_via: str,
) -> None:
    request_context = story58_latest_correction_request_context(summary)
    record_story58_artifact_set_snapshot(
        summary,
        story58_snapshot_evidence_with_request_context(evidence, request_context),
        observed_via=observed_via,
    )


def _observe_replayed_pdf_artifact_set(
    page: Page,
    *,
    artifact_dir: Path,
    expected_pdf_filename: str,
    observed_via: str,
    summary: dict[str, Any],
) -> None:
    page.locator('[data-test="exam-converter-inspection-tab-files"]').click()
    expect(page.locator('[data-test="exam-converter-files-readiness-list"]')).to_be_visible(
        timeout=30_000,
    )
    enabled_downloads = page.locator('[data-test^="exam-converter-download-file-"]:enabled')
    if enabled_downloads.count() < 2:
        raise AssertionError("Replay did not expose exportable file downloads.")
    _pdf_path, pdf_download = _download_replayed_file(
        page,
        artifact_key="examnet_pdf",
        artifact_dir=artifact_dir,
        expected_filename=expected_pdf_filename,
    )
    summary["artifact_downloads"].append(pdf_download)
    _record_story58_product_route_snapshot(
        summary,
        pdf_download,
        observed_via=observed_via,
    )
    _write_summary(summary, artifact_dir)


def _save_replayed_file(page: Page, *, artifact_key: str, expected_filename: str) -> dict[str, Any]:
    last_error = ""
    for _ in range(3):
        result = _save_replayed_file_once(page, artifact_key=artifact_key)
        save_status = result["save_status"]
        if save_status < 400:
            saved_filename = result.get("saved_filename")
            if saved_filename != expected_filename:
                raise AssertionError(
                    f"Replay save used {saved_filename}, expected {expected_filename}."
                )
            return result
        last_error = f"HTTP {save_status}: {result.get('save_body', '')}"
        if save_status == 429:
            retry_after = _retry_after_seconds(str(result.get("save_body", "")))
            retry_after = retry_after if retry_after is not None else 5
            page.wait_for_timeout((retry_after + 3) * 1_000)
            continue
        break
    raise AssertionError(f"Artifact save failed with {last_error}.")


def _visible(locator: Locator) -> bool:
    return locator.count() > 0 and locator.first.is_visible()


def _assert_no_visible_selected_detail(page: Page) -> None:
    detail = page.locator(SELECTED_QUESTION_DETAIL_SELECTOR)
    if _visible(detail):
        raise AssertionError("Files/report mobile surfaces must not show selected-question detail.")


def _mobile_overflow_geometry(page: Page) -> dict[str, int | bool]:
    geometry = page.evaluate(
        """() => ({
            bodyScrollWidth: document.body.scrollWidth,
            bodyClientWidth: document.body.clientWidth,
            documentScrollWidth: document.documentElement.scrollWidth,
            documentClientWidth: document.documentElement.clientWidth,
        })"""
    )
    body_scroll_width = int(geometry["bodyScrollWidth"])
    body_client_width = int(geometry["bodyClientWidth"])
    document_scroll_width = int(geometry["documentScrollWidth"])
    document_client_width = int(geometry["documentClientWidth"])
    return {
        "body_client_width": body_client_width,
        "body_scroll_width": body_scroll_width,
        "document_client_width": document_client_width,
        "document_scroll_width": document_scroll_width,
        "has_horizontal_overflow": (
            body_scroll_width > body_client_width + 1
            or document_scroll_width > document_client_width + 1
        ),
    }


def _capture_mobile_surface_checks(page: Page, *, artifact_dir: Path) -> dict[str, Any]:
    page.set_viewport_size({"height": 844, "width": 390})
    page.locator('[data-test="exam-converter-inspection-tab-questions"]').click()
    expect(page.locator(SELECTED_QUESTION_DETAIL_SELECTOR)).to_be_visible(
        timeout=30_000,
    )
    mobile_detail = artifact_dir / "05-mobile-detail.png"
    page.screenshot(path=str(mobile_detail), full_page=True)

    back_to_questions = page.locator('[data-test="exam-converter-compact-back-to-questions"]')
    if _visible(back_to_questions):
        back_to_questions.first.click()
    expect(page.locator('[data-test="exam-converter-question-list-surface"]')).to_be_visible(
        timeout=30_000,
    )
    mobile_questions = artifact_dir / "06-mobile-questions.png"
    page.screenshot(path=str(mobile_questions), full_page=True)

    page.locator('[data-test="exam-converter-inspection-tab-files"]').click()
    expect(page.locator('[data-test="exam-converter-files-readiness-list"]')).to_be_visible(
        timeout=30_000,
    )
    _assert_no_visible_selected_detail(page)
    mobile_files = artifact_dir / "07-mobile-files.png"
    page.screenshot(path=str(mobile_files), full_page=True)

    page.locator('[data-test="exam-converter-inspection-tab-report"]').click()
    expect(page.locator('[data-test="exam-converter-report-summary"]')).to_be_visible(
        timeout=30_000,
    )
    _assert_no_visible_selected_detail(page)
    mobile_report = artifact_dir / "08-mobile-report.png"
    page.screenshot(path=str(mobile_report), full_page=True)

    geometry = _mobile_overflow_geometry(page)
    if geometry["has_horizontal_overflow"]:
        raise AssertionError(f"Mobile surface has horizontal overflow: {geometry!r}")
    page.set_viewport_size({"height": 1117, "width": 1728})
    return {
        "files_omits_selected_detail": True,
        "geometry": geometry,
        "report_omits_selected_detail": True,
        "screenshots": [
            str(mobile_questions),
            str(mobile_detail),
            str(mobile_files),
            str(mobile_report),
        ],
        "viewport": {"height": 844, "width": 390},
    }


def _save_replayed_file_once(page: Page, *, artifact_key: str) -> dict[str, Any]:
    button = page.locator(f'[data-test="exam-converter-save-file-{artifact_key}"]').first
    expect(button).to_be_enabled(timeout=30_000)
    with page.expect_response(
        _download_response_predicate, timeout=30_000
    ) as artifact_response_info:
        with page.expect_response(
            lambda response: (
                USER_FILE_SAVE_MARKER in response.url and response.request.method == "POST"
            ),
            timeout=30_000,
        ) as save_response_info:
            button.click()
    artifact_response = artifact_response_info.value
    save_response = save_response_info.value
    if artifact_response.status >= 400:
        raise AssertionError(f"Artifact save download failed with HTTP {artifact_response.status}.")
    replay_evidence = _correction_replay_artifact_evidence(artifact_response)
    replay_artifact_key = replay_evidence["artifact_key"]
    if not replay_artifact_key.startswith("correction_replay_"):
        raise AssertionError("Corrected save did not use a replay-scoped artifact key.")
    if save_response.status < 400:
        expect(button).to_contain_text("Sparad", timeout=10_000)
    save_payload = save_response.json() if save_response.status < 400 else {}
    saved_filename = (
        save_payload.get("vault_artifact", {}).get("name")
        if isinstance(save_payload, dict)
        else None
    )
    return {
        "content_sha256": replay_evidence["content_sha256"],
        "download_status": artifact_response.status,
        "download_path": _safe_url_with_query(artifact_response.url),
        "replay_artifact_key": replay_artifact_key,
        "replay_artifact_set_id": replay_evidence["artifact_set_id"],
        "save_body": save_response.text() if save_response.status >= 400 else "",
        "saved_filename": saved_filename,
        "save_path": _safe_url(save_response.url),
        "save_status": save_response.status,
        "ui_artifact_key": artifact_key,
    }


def _summarize_response(response: Response) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "content_type": response.headers.get("content-type"),
        "method": response.request.method,
        "path": _safe_url(response.url),
        "status": response.status,
    }
    if "application/json" not in (entry["content_type"] or ""):
        return entry
    try:
        payload = response.json()
    except Exception as exc:  # pragma: no cover - diagnostic evidence only.
        entry["json_error"] = str(exc)
        return entry
    if isinstance(payload, dict) and "error" in payload:
        entry["error"] = payload["error"]
    if isinstance(payload, dict):
        if "job" in payload and "idempotency" in payload:
            entry["job_create"] = _summarize_create_job_payload(payload)
        entry["json"] = _summarize_json_payload(payload)
    return entry


def _assert_submit_idempotency_reason(summary: dict[str, Any], expected_reason: str) -> None:
    matches: list[dict[str, Any]] = []
    for response in summary.get("sir_convert_submit_responses", []):
        if not isinstance(response, dict):
            continue
        job_create = response.get("job_create")
        if not isinstance(job_create, dict):
            continue
        idempotency = job_create.get("idempotency")
        if not isinstance(idempotency, dict):
            continue
        if idempotency.get("reason") == expected_reason:
            matches.append(response)
    if not matches:
        raise AssertionError(
            f"No Sir Convert submit response had idempotency.reason={expected_reason!r}."
        )
    summary["submit_idempotency_reason_match_count"] = len(matches)


def _retry_after_seconds(response_body: str) -> int | None:
    try:
        payload = json.loads(response_body)
    except json.JSONDecodeError:
        return None
    retry_after = payload.get("retry_after_seconds") if isinstance(payload, dict) else None
    return retry_after if isinstance(retry_after, int) and retry_after >= 0 else None


def _latest_correction_session_path(summary: dict[str, Any]) -> str:
    pattern = re.compile(
        r"^/api/v1/apps/documents\.conversion_hub/exam-converter/jobs/"
        r"[^/]+/correction-session$"
    )
    for entry in reversed(summary.get("correction_session_responses", [])):
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        if isinstance(path, str) and pattern.match(path):
            return path
    raise AssertionError("No correction-session readback path was observed.")


def _load_shared_csrf_token(page: Page, *, base_url: str) -> dict[str, str]:
    parsed = urlparse(base_url)
    host = parsed.hostname or "127.0.0.1"
    scheme = parsed.scheme or "http"
    cookie_urls = [
        base_url.rstrip("/"),
        f"{scheme}://{host}:8080",
        f"{scheme}://{host}:9000",
    ]
    for cookie in page.context.cookies(cookie_urls):
        cookie_name = cookie.get("name")
        cookie_value = cookie.get("value")
        if (
            isinstance(cookie_name, str)
            and "csrf" in cookie_name.lower()
            and isinstance(cookie_value, str)
            and cookie_value
        ):
            return {"source": "csrf-cookie", "token": cookie_value}
    candidates = [
        f"{scheme}://{host}:8080/v1/auth/csrf",
        f"{base_url.rstrip('/')}/v1/auth/csrf",
        f"{scheme}://{host}:9000/v1/auth/csrf",
    ]
    errors: list[str] = []
    for candidate in candidates:
        response = page.request.get(candidate, timeout=10_000)
        if response.status != 200:
            errors.append(f"{_safe_url(candidate)}:{response.status}")
            continue
        payload = response.json()
        token = payload.get("csrf_token") if isinstance(payload, dict) else None
        if isinstance(token, str) and token:
            return {"source": _safe_url(candidate), "token": token}
        errors.append(f"{_safe_url(candidate)}:missing-token")
    raise AssertionError(f"Could not load shared CSRF token: {errors!r}")


def _protected_api_base_url(base_url: str) -> str:
    """Return the protected API origin for browser-session API proof calls."""

    parsed = urlparse(base_url)
    if parsed.hostname == "skriptoteket.hule.education":
        return "https://api.hule.education"
    return base_url.rstrip("/")


def _revert_active_correction_intents(
    page: Page, *, base_url: str, summary: dict[str, Any]
) -> dict[str, Any]:
    session_path = _latest_correction_session_path(summary)
    api_base_url = _protected_api_base_url(base_url)
    session_url = f"{api_base_url}{session_path}"
    session_response = page.request.get(session_url, timeout=30_000)
    if session_response.status >= 400:
        raise AssertionError(
            f"Correction-session readback failed with HTTP {session_response.status}."
        )
    session = session_response.json()
    active_intents = session.get("active_intents") if isinstance(session, dict) else None
    if not isinstance(active_intents, list):
        raise AssertionError("Correction-session readback did not return active intents.")
    csrf = _load_shared_csrf_token(page, base_url=api_base_url)
    reverted_target_keys: list[str] = []
    for intent in list(active_intents):
        if not isinstance(intent, dict):
            continue
        target_key = intent.get("target_key")
        if not isinstance(target_key, str):
            continue
        session_version = session.get("session_version") if isinstance(session, dict) else None
        delete_response = page.request.delete(
            f"{session_url}/intents",
            data={
                "expected_session_version": session_version
                if isinstance(session_version, int)
                else None,
                "target_key": target_key,
            },
            headers={"X-CSRF-Token": csrf["token"]},
            timeout=30_000,
        )
        if delete_response.status >= 400:
            raise AssertionError(
                "Correction-session revert failed with "
                f"HTTP {delete_response.status}: {delete_response.text()}"
            )
        session = delete_response.json()
        reverted_target_keys.append(target_key)
    return {
        "active_intent_count_before": len(active_intents),
        "path": session_path,
        "reverted_target_keys": reverted_target_keys,
        "session_request_origin": urlparse(api_base_url).netloc,
        "shared_csrf_source": csrf["source"],
        "shared_csrf_value_retained": False,
        "session_version_after": session.get("session_version")
        if isinstance(session, dict)
        else None,
    }


def _reload_and_wait_for_replay(page: Page) -> None:
    last_error = ""
    for _ in range(3):
        with page.expect_response(
            lambda response: (
                CORRECTION_APPLY_MARKER in response.url and response.request.method == "POST"
            ),
            timeout=45_000,
        ) as reload_apply_response_info:
            page.reload()
        reload_apply_response = reload_apply_response_info.value
        if reload_apply_response.status < 400:
            return
        response_body = reload_apply_response.text()
        last_error = f"HTTP {reload_apply_response.status}: {response_body}"
        if reload_apply_response.status == 429:
            retry_after = _retry_after_seconds(response_body)
            retry_after = retry_after if retry_after is not None else 5
            page.wait_for_timeout((retry_after + 3) * 1_000)
            continue
        break
    raise AssertionError(f"Reload replay failed with {last_error}")


def _visible_indexes(locator: Any) -> list[int]:
    return [index for index in range(locator.count()) if locator.nth(index).is_visible()]


def _compact_status_selector(label: str) -> str:
    return f'[aria-label="{label}"]'


def _row_has_compact_status(row: Any, label: str) -> bool:
    status = row.locator(_compact_status_selector(label))
    return status.count() > 0 and status.first.is_visible()


def _compact_status_counts(page: Page) -> dict[str, int]:
    page.locator('[data-test="exam-converter-inspection-tab-questions"]').click()
    rows = page.locator('[data-test^="exam-converter-question-row-"]')
    labels = (
        COMPACT_REVIEW_REQUIRED_LABEL,
        COMPACT_COMPLETE_LABEL,
        COMPACT_TEACHER_MODIFIED_LABEL,
        COMPACT_VALIDATION_REQUIRED_LABEL,
    )
    counts = {label: 0 for label in labels}
    for index in range(rows.count()):
        row = rows.nth(index)
        for label in labels:
            if _row_has_compact_status(row, label):
                counts[label] += 1
    return counts


def _is_correction_session_write(response: Response) -> bool:
    return CORRECTION_SESSION_MARKER in response.url and response.request.method in {
        "PUT",
        "DELETE",
    }


def _is_correction_apply_response(response: Response) -> bool:
    return CORRECTION_APPLY_MARKER in response.url and response.request.method == "POST"


def _is_source_state_failure(response: Response) -> bool:
    return (
        CORRECTION_SOURCE_STATE_MARKER in response.url
        and response.request.method == "POST"
        and response.status >= 400
    )


def _wait_for_apply_or_source_state_failure(page: Page) -> Response:
    return page.wait_for_event(
        "response",
        predicate=lambda response: (
            _is_correction_apply_response(response) or _is_source_state_failure(response)
        ),
        timeout=45_000,
    )


def _wait_for_correction_idle(page: Page) -> None:
    expect(page.locator(START_CONVERSION_SELECTOR)).to_be_enabled(timeout=90_000)
    page.wait_for_timeout(300)


def _click_and_wait_for_apply(
    page: Page,
    action: str | Locator,
    *,
    action_timeout_ms: int = 30_000,
    before_click: Callable[[], Any] | None = None,
) -> Any:
    last_error = ""
    for _attempt in range(4):
        with page.expect_response(_is_correction_session_write, timeout=30_000) as session_info:
            target = page.locator(action) if isinstance(action, str) else action
            expect(target).to_have_count(1, timeout=action_timeout_ms)
            expect(target).to_be_visible(timeout=action_timeout_ms)
            expect(target).to_be_enabled(timeout=action_timeout_ms)
            target.scroll_into_view_if_needed(timeout=action_timeout_ms)
            click_context = before_click() if before_click is not None else None
            target.click(timeout=action_timeout_ms)
        session_response = session_info.value
        if session_response.status >= 400:
            response_body = session_response.text()
            last_error = f"HTTP {session_response.status}: {response_body}"
            if session_response.status == 429:
                retry_after = _retry_after_seconds(response_body)
                retry_after = retry_after if retry_after is not None else 8
                page.wait_for_timeout((retry_after + 3) * 1_000)
                continue
            raise AssertionError(
                f"Correction-session write failed with HTTP {session_response.status}."
            )
        try:
            replay_response = _wait_for_apply_or_source_state_failure(page)
        except PlaywrightTimeoutError as error:
            raise AssertionError("Correction replay did not produce an apply response.") from error
        if _is_correction_apply_response(replay_response):
            if replay_response.status >= 400:
                raise AssertionError(
                    "Correction replay failed with "
                    f"HTTP {replay_response.status}: {replay_response.text()}"
                )
            _wait_for_correction_idle(page)
            return click_context
        response_body = replay_response.text()
        last_error = f"HTTP {replay_response.status}: {response_body}"
        if replay_response.status == 429:
            retry_after = _retry_after_seconds(response_body)
            retry_after = retry_after if retry_after is not None else 8
            page.wait_for_timeout((retry_after + 3) * 1_000)
            continue
        raise AssertionError(f"Correction source-state issue failed with {last_error}")
    raise AssertionError(f"Correction source-state issue stayed rate-limited with {last_error}")


def _selected_question_detail_selector(item_id: str | None = None) -> str:
    if item_id is None:
        return SELECTED_QUESTION_DETAIL_SELECTOR
    return f"{SELECTED_QUESTION_DETAIL_SELECTOR}[data-selected-item-id={json.dumps(item_id)}]"


def _selected_question_detail(page: Page, item_id: str | None = None) -> Locator:
    return page.locator(_selected_question_detail_selector(item_id))


def _current_selected_detail_item_id(page: Page) -> str:
    item_id = _selected_question_detail(page).get_attribute("data-selected-item-id")
    if not item_id:
        raise AssertionError("Selected question detail did not expose an item id.")
    return item_id


def _wait_for_selected_question_detail(page: Page, item_id: str) -> Locator:
    detail = _selected_question_detail(page)
    expect(detail).to_have_attribute("data-selected-item-id", item_id, timeout=10_000)
    return _selected_question_detail(page, item_id)


def _select_question(page: Page, item_id: str) -> None:
    page.locator('[data-test="exam-converter-inspection-tab-questions"]').click()
    page.locator(f'[data-test="exam-converter-question-row-{item_id}"]').click()
    expect(page.locator(f'[data-test="exam-converter-question-row-{item_id}"]')).to_have_attribute(
        "aria-selected",
        "true",
        timeout=10_000,
    )
    _wait_for_selected_question_detail(page, item_id)


def _manual_answer_key_editor(container: LocatorRoot) -> Locator:
    return container.locator(MANUAL_ANSWER_KEY_EDITOR_SELECTOR)


def _manual_answer_key_save_button(container: LocatorRoot) -> Locator:
    return container.locator(MANUAL_ANSWER_KEY_SAVE_SELECTOR)


def _advisory_answer_key_panel(container: LocatorRoot) -> Locator:
    return container.locator(ADVISORY_ANSWER_KEY_PANEL_SELECTOR)


def _advisory_answer_key_accept_button(container: LocatorRoot) -> Locator:
    return container.locator(ADVISORY_ANSWER_KEY_ACCEPT_SELECTOR)


def _advisory_answer_key_edit_button(container: LocatorRoot) -> Locator:
    return container.locator(ADVISORY_ANSWER_KEY_EDIT_SELECTOR)


def _selected_advisory_accept_button_is_ready(page: Page) -> bool:
    accept_button = _advisory_answer_key_accept_button(_selected_question_detail(page))
    return (
        accept_button.count() == 1
        and accept_button.first.is_visible()
        and accept_button.first.is_enabled()
    )


def _manual_answer_key_save_is_enabled(container: LocatorRoot) -> bool:
    save_button = _manual_answer_key_save_button(container)
    return save_button.count() > 0 and save_button.first.is_enabled()


def _fill_visible_gap_answers(container: LocatorRoot) -> int:
    gap_inputs = container.locator('[data-test^="exam-converter-manual-gap-"]')
    filled_count = 0
    for index in _visible_indexes(gap_inputs):
        gap_input = gap_inputs.nth(index)
        if not gap_input.is_enabled():
            continue
        gap_input.fill(f"{MANUAL_GAP_FILL_VALUE_PREFIX}-{filled_count + 1}")
        filled_count += 1
    return filled_count


def _prepare_visible_answer_key_editor(container: LocatorRoot) -> str | None:
    if _manual_answer_key_save_is_enabled(container):
        return "unchanged"
    choices = container.locator('[data-test^="exam-converter-manual-choice-"]')
    if _visible_indexes(choices):
        choice_id = _choose_manual_choice(container)
        expect(_manual_answer_key_save_button(container)).to_be_enabled(timeout=5_000)
        return f"choice:{choice_id}"
    filled_gap_count = _fill_visible_gap_answers(container)
    if filled_gap_count > 0:
        expect(_manual_answer_key_save_button(container)).to_be_enabled(timeout=5_000)
        return f"gap_fill:{filled_gap_count}"
    return None


def _prepare_visible_answer_key_editor_for_edit(container: LocatorRoot) -> str:
    choices = container.locator('[data-test^="exam-converter-manual-choice-"]')
    visible_choice_indexes = _visible_indexes(choices)
    unselected_choices = [
        index
        for index in visible_choice_indexes
        if choices.nth(index).get_attribute("aria-pressed") != "true"
    ]
    if unselected_choices:
        choice = choices.nth(unselected_choices[-1])
        choice_test_id = choice.get_attribute("data-test")
        if not choice_test_id:
            raise AssertionError("Manual choice did not expose a data-test id.")
        choice.click()
        expect(_manual_answer_key_save_button(container)).to_be_enabled(timeout=5_000)
        return f"changed_choice:{choice_test_id.removeprefix('exam-converter-manual-choice-')}"
    filled_gap_count = _fill_visible_gap_answers(container)
    if filled_gap_count > 0:
        expect(_manual_answer_key_save_button(container)).to_be_enabled(timeout=5_000)
        return f"changed_gap_fill:{filled_gap_count}"
    preparation = _prepare_visible_answer_key_editor(container)
    if preparation is None:
        raise AssertionError("Advisory edit path did not expose an answer-key editor.")
    return preparation


def _find_compact_status_manual_answer_key_question(
    page: Page,
    *,
    excluded_item_ids: set[str] | None = None,
    status_label: str,
) -> tuple[str, str]:
    excluded_item_ids = excluded_item_ids or set()
    page.locator('[data-test="exam-converter-inspection-tab-questions"]').click()
    rows = page.locator('[data-test^="exam-converter-question-row-"]')
    for index in range(rows.count()):
        row = rows.nth(index)
        row_test_id = row.get_attribute("data-test")
        if not row_test_id:
            continue
        item_id = row_test_id.removeprefix("exam-converter-question-row-")
        if item_id in excluded_item_ids:
            continue
        if not _row_has_compact_status(row, status_label):
            continue
        row.click()
        detail = _wait_for_selected_question_detail(page, item_id)
        try:
            expect(_manual_answer_key_editor(detail)).to_be_visible(timeout=5_000)
        except AssertionError:
            continue
        preparation = _prepare_visible_answer_key_editor(detail)
        if preparation is not None:
            return item_id, preparation
    raise AssertionError(
        f"No visible answer-key editor was found for compact '{status_label}' state."
    )


def _find_review_required_advisory_question(
    page: Page, *, excluded_item_ids: set[str] | None = None
) -> str:
    excluded_item_ids = excluded_item_ids or set()
    page.locator('[data-test="exam-converter-inspection-tab-questions"]').click()
    rows = page.locator('[data-test^="exam-converter-question-row-"]')
    for index in range(rows.count()):
        row = rows.nth(index)
        row_test_id = row.get_attribute("data-test")
        if not row_test_id:
            continue
        item_id = row_test_id.removeprefix("exam-converter-question-row-")
        if item_id in excluded_item_ids:
            continue
        if not _row_has_compact_status(row, COMPACT_REVIEW_REQUIRED_LABEL):
            continue
        row.click()
        detail = _wait_for_selected_question_detail(page, item_id)
        try:
            expect(_advisory_answer_key_panel(detail)).to_be_visible(timeout=5_000)
            expect(_advisory_answer_key_accept_button(detail)).to_be_enabled(timeout=5_000)
            expect(_advisory_answer_key_edit_button(detail)).to_be_enabled(timeout=5_000)
        except AssertionError:
            continue
        return item_id
    raise AssertionError("No visible advisory review panel was found for compact 'Granska' state.")


def _assert_untouched_advisory_sibling_preserved(
    page: Page, *, accepted_item_id: str
) -> dict[str, Any]:
    sibling_item_id = _find_review_required_advisory_question(
        page,
        excluded_item_ids={accepted_item_id},
    )
    row = page.locator(f'[data-test="exam-converter-question-row-{sibling_item_id}"]')
    expect(row.locator(_compact_status_selector(COMPACT_REVIEW_REQUIRED_LABEL))).to_be_visible(
        timeout=10_000
    )
    detail = _wait_for_selected_question_detail(page, sibling_item_id)
    expect(_advisory_answer_key_panel(detail)).to_be_visible(timeout=10_000)
    expect(_advisory_answer_key_accept_button(detail)).to_be_enabled(timeout=10_000)
    expect(_advisory_answer_key_edit_button(detail)).to_be_enabled(timeout=10_000)
    return {
        "accepted_item_id": accepted_item_id,
        "sibling_item_id": sibling_item_id,
        "sibling_status": COMPACT_REVIEW_REQUIRED_LABEL,
        "sibling_advisory_panel_visible": True,
    }


def _selected_question_id(page: Page) -> str:
    rows = page.locator('[data-test^="exam-converter-question-row-"]')
    for index in range(rows.count()):
        row = rows.nth(index)
        if row.get_attribute("aria-selected") == "true":
            row_test_id = row.get_attribute("data-test")
            if row_test_id:
                return row_test_id.removeprefix("exam-converter-question-row-")
    raise AssertionError("No selected question row was visible.")


def _assert_row_status_is_one_of(page: Page, item_id: str, labels: Sequence[str]) -> str:
    row = page.locator(f'[data-test="exam-converter-question-row-{item_id}"]')
    for label in labels:
        status = row.locator(_compact_status_selector(label))
        try:
            expect(status).to_be_visible(timeout=10_000)
        except AssertionError:
            continue
        return label
    expected_labels = ", ".join(labels)
    raise AssertionError(f"Question {item_id} did not move to one of: {expected_labels}.")


def _save_visible_answer_key(page: Page, *, expected_statuses: Sequence[str]) -> str:
    item_id = _selected_question_id(page)
    detail = _wait_for_selected_question_detail(page, item_id)
    _click_and_wait_for_apply(
        page,
        _manual_answer_key_save_button(detail),
    )
    _assert_row_status_is_one_of(page, item_id, expected_statuses)
    return item_id


def _save_review_required_answer_key(
    page: Page,
    *,
    excluded_item_ids: set[str] | None = None,
    expected_item_id: str | None = None,
) -> str:
    excluded_item_ids = excluded_item_ids or set()
    last_error: AssertionError | None = None
    if expected_item_id is not None:
        _select_question(page, expected_item_id)
    for _attempt in range(8):
        item_id = _selected_question_id(page)
        if expected_item_id is not None and item_id != expected_item_id:
            raise AssertionError(
                "Advisory answer-key save selected a different question: "
                f"expected {expected_item_id}, got {item_id}."
            )
        _wait_for_selected_question_detail(page, item_id)
        if not _selected_advisory_accept_button_is_ready(page):
            if expected_item_id is not None:
                raise AssertionError(f"Selected question {expected_item_id} has no advisory save.")
            _find_review_required_advisory_question(page, excluded_item_ids=excluded_item_ids)
            continue
        try:
            saved_item_id = _click_and_wait_for_apply(
                page,
                _advisory_answer_key_accept_button(_selected_question_detail(page)),
                action_timeout_ms=5_000,
                before_click=lambda: _current_selected_detail_item_id(page),
            )
        except AssertionError as exc:
            last_error = exc
            page.wait_for_timeout(500)
            continue
        if not isinstance(saved_item_id, str):
            raise AssertionError("Advisory answer-key click did not capture the selected item id.")
        _assert_row_status_is_one_of(page, saved_item_id, (COMPACT_COMPLETE_LABEL,))
        return saved_item_id
    if last_error is not None:
        raise AssertionError("Advisory answer-key save did not settle.") from last_error
    raise AssertionError("Advisory answer-key save did not find a saveable question.")


def _save_review_required_answer_key_edit(page: Page) -> tuple[str, str]:
    item_id = _find_review_required_advisory_question(page)
    detail = _wait_for_selected_question_detail(page, item_id)
    _advisory_answer_key_edit_button(detail).click()
    expect(_manual_answer_key_editor(detail)).to_be_visible(timeout=5_000)
    preparation = _prepare_visible_answer_key_editor_for_edit(detail)
    saved_item_id = _save_visible_answer_key(
        page,
        expected_statuses=(COMPACT_TEACHER_MODIFIED_LABEL, COMPACT_COMPLETE_LABEL),
    )
    if saved_item_id != item_id:
        raise AssertionError("Advisory edit save changed the selected question unexpectedly.")
    return item_id, preparation


def _save_validation_required_answer_key(page: Page) -> str:
    return _save_visible_answer_key(
        page,
        expected_statuses=(COMPACT_TEACHER_MODIFIED_LABEL, COMPACT_COMPLETE_LABEL),
    )


def _save_review_required_manual_answer_key(page: Page) -> str:
    return _save_visible_answer_key(
        page,
        expected_statuses=(
            COMPACT_TEACHER_MODIFIED_LABEL,
            COMPACT_COMPLETE_LABEL,
            COMPACT_REVIEW_REQUIRED_LABEL,
        ),
    )


def _save_all_review_required_answer_keys(page: Page) -> list[str]:
    saved_item_ids: list[str] = []
    for _ in range(12):
        try:
            item_id = _find_review_required_advisory_question(page)
        except AssertionError:
            return saved_item_ids
        if item_id in saved_item_ids:
            raise AssertionError(f"Review-required answer-key flow did not advance past {item_id}.")
        try:
            saved_item_id = _save_review_required_answer_key(
                page,
                excluded_item_ids=set(saved_item_ids),
            )
        except AssertionError as exc:
            if "No visible advisory review panel" in str(exc):
                return saved_item_ids
            raise
        if saved_item_id in saved_item_ids:
            raise AssertionError(
                f"Review-required answer-key flow repeated saved item {saved_item_id}."
            )
        saved_item_ids.append(saved_item_id)
        page.wait_for_timeout(250)
    raise AssertionError("Review-required answer-key flow exceeded the expected item count.")


def _save_all_review_required_manual_answer_keys(
    page: Page, *, excluded_item_ids: set[str]
) -> list[dict[str, str]]:
    saved_items: list[dict[str, str]] = []
    for _ in range(12):
        excluded = excluded_item_ids | {entry["item_id"] for entry in saved_items}
        try:
            item_id, preparation = _find_compact_status_manual_answer_key_question(
                page,
                excluded_item_ids=excluded,
                status_label=COMPACT_REVIEW_REQUIRED_LABEL,
            )
        except AssertionError:
            return saved_items
        saved_item_id = _save_review_required_manual_answer_key(page)
        if saved_item_id in excluded:
            raise AssertionError(
                f"Review-required manual answer-key flow repeated {saved_item_id}."
            )
        saved_items.append(
            {
                "item_id": saved_item_id,
                "preparation": preparation,
            }
        )
        page.wait_for_timeout(250)
    raise AssertionError("Review-required manual answer-key flow exceeded the expected item count.")


def _save_all_validation_required_answer_keys(page: Page) -> list[dict[str, str]]:
    saved_items: list[dict[str, str]] = []
    for _ in range(12):
        try:
            item_id, preparation = _find_compact_status_manual_answer_key_question(
                page,
                status_label=COMPACT_VALIDATION_REQUIRED_LABEL,
            )
        except AssertionError:
            return saved_items
        if any(entry["item_id"] == item_id for entry in saved_items):
            raise AssertionError(f"Validation-required answer-key flow repeated {item_id}.")
        saved_items.append(
            {
                "item_id": _save_validation_required_answer_key(page),
                "preparation": preparation,
            }
        )
        page.wait_for_timeout(250)
    raise AssertionError("Validation-required answer-key flow exceeded the expected item count.")


def _assert_selected_moved_to_next_review_required(page: Page, previous_item_id: str) -> str:
    next_item_id = _selected_question_id(page)
    if next_item_id == previous_item_id:
        rows = page.locator('[data-test^="exam-converter-question-row-"]')
        for index in range(rows.count()):
            row = rows.nth(index)
            row_test_id = row.get_attribute("data-test")
            if row_test_id == f"exam-converter-question-row-{previous_item_id}":
                continue
            if not _row_has_compact_status(row, COMPACT_REVIEW_REQUIRED_LABEL):
                continue
            row.click()
            item_id = row_test_id.removeprefix("exam-converter-question-row-")
            detail = _wait_for_selected_question_detail(page, item_id)
            editor = _manual_answer_key_editor(detail)
            has_review_required_editor = (
                editor.count() > 0
                and editor.first.is_visible()
                and _manual_answer_key_save_is_enabled(detail)
            )
            if has_review_required_editor:
                raise AssertionError("Saving a review-required answer key did not advance review.")
        _select_question(page, previous_item_id)
    return next_item_id


def _assert_local_draft_does_not_unlock_files(page: Page) -> dict[str, Any]:
    page.locator('[data-test="exam-converter-point-correction-input"]').fill("2")
    page.locator('[data-test="exam-converter-inspection-tab-files"]').click()
    expect(page.locator('[data-test="exam-converter-files-readiness-list"]')).to_be_visible(
        timeout=10_000,
    )
    enabled_downloads = page.locator('[data-test^="exam-converter-download-file-"]:enabled')
    enabled_saves = page.locator('[data-test^="exam-converter-save-file-"]:enabled')
    if enabled_downloads.count() > 0 or enabled_saves.count() > 0:
        raise AssertionError("Local draft unexpectedly unlocked file actions.")
    return {
        "enabled_download_count": enabled_downloads.count(),
        "enabled_save_count": enabled_saves.count(),
    }


def _choose_manual_choice(container: LocatorRoot) -> str:
    choices = container.locator('[data-test^="exam-converter-manual-choice-"]')
    visible_indexes = _visible_indexes(choices)
    if not visible_indexes:
        raise AssertionError("Manual choice editor has no visible choices after suppression.")
    choice = choices.nth(visible_indexes[-1])
    choice_test_id = choice.get_attribute("data-test")
    if not choice_test_id:
        raise AssertionError("Manual choice did not expose a data-test id.")
    choice.click()
    return choice_test_id.removeprefix("exam-converter-manual-choice-")


def _inspect_pdf(path: Path, *, expected_texts: Sequence[str]) -> dict[str, Any]:
    reader = PdfReader(str(path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return {
        "forbidden_text_hits": [value for value in FORBIDDEN_ARTIFACT_TEXT if value in text],
        "missing_expected_texts": [value for value in expected_texts if value not in text],
        "page_count": len(reader.pages),
        "path": str(path),
    }


def _qti_contains_text(path: Path, expected_text: str) -> bool:
    with ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.endswith(".xml"):
                continue
            text = archive.read(name).decode("utf-8", errors="ignore")
            if expected_text in text:
                return True
    return False


def _prove_replayed_file_actions(
    page: Page,
    *,
    artifact_dir: Path,
    base_url: str,
    summary: dict[str, Any],
    expected_pdf_filename: str,
    expected_qti_filename: str,
) -> None:
    page.locator('[data-test="exam-converter-inspection-tab-files"]').click()
    expect(page.locator('[data-test="exam-converter-files-readiness-list"]')).to_be_visible(
        timeout=30_000,
    )
    page.screenshot(path=str(artifact_dir / "03-replayed-files.png"), full_page=True)
    summary["screenshots"].append(str(artifact_dir / "03-replayed-files.png"))
    _write_summary(summary, artifact_dir)
    enabled_downloads = page.locator('[data-test^="exam-converter-download-file-"]:enabled')
    if enabled_downloads.count() < 2:
        raise AssertionError("Replay did not expose both file downloads after reload.")
    summary["story58_apply_response_reference_probe"] = probe_safe_correction_replay_artifacts(
        page.request,
        api_base_url=_protected_api_base_url(base_url),
        summary=summary,
    )
    pdf_path, pdf_download = _download_replayed_file(
        page,
        artifact_key="examnet_pdf",
        artifact_dir=artifact_dir,
        expected_filename=expected_pdf_filename,
    )
    summary["artifact_downloads"].append(pdf_download)
    _record_story58_product_route_snapshot(summary, pdf_download, observed_via="download")
    qti_path, qti_download = _download_replayed_file(
        page,
        artifact_key="qti_package",
        artifact_dir=artifact_dir,
        expected_filename=expected_qti_filename,
    )
    summary["artifact_downloads"].append(qti_download)
    _record_story58_product_route_snapshot(summary, qti_download, observed_via="download")
    pdf_save = _save_replayed_file(
        page,
        artifact_key="examnet_pdf",
        expected_filename=expected_pdf_filename,
    )
    summary["file_saves"].append(pdf_save)
    _record_story58_product_route_snapshot(summary, pdf_save, observed_via="save")
    qti_save = _save_replayed_file(
        page,
        artifact_key="qti_package",
        expected_filename=expected_qti_filename,
    )
    summary["file_saves"].append(qti_save)
    _record_story58_product_route_snapshot(summary, qti_save, observed_via="save")
    summary["mismatched_artifact_download_probe"] = probe_mismatched_replay_artifact_download(
        page.request,
        api_base_url=_protected_api_base_url(base_url),
        artifact_download=pdf_download,
    )
    _write_summary(summary, artifact_dir)
    summary["pdf_inspection"] = _inspect_pdf(
        pdf_path,
        expected_texts=(f"Poängvärde: {UPDATED_ITEM_POINTS}",),
    )
    summary["qti_inspection"] = inspect_qti(qti_path)
    summary["qti_inspection"]["expected_prompt_present"] = _qti_contains_text(
        qti_path,
        UPDATED_ITEM_PROMPT,
    )
    if summary["pdf_inspection"]["forbidden_text_hits"]:
        raise AssertionError("PDF exposes forbidden internal diagnostics.")
    if summary["qti_inspection"]["forbidden_text_hits"]:
        raise AssertionError("QTI exposes forbidden internal diagnostics.")
    if summary["qti_inspection"]["correct_response_count"] == 0:
        raise AssertionError("QTI contains no correctResponse entries.")
    if summary["pdf_inspection"]["missing_expected_texts"]:
        raise AssertionError("PDF did not include the replayed point correction.")
    if not summary["qti_inspection"]["expected_prompt_present"]:
        raise AssertionError("QTI did not include the replayed prompt correction.")


def _write_failure_text(page: Page, artifact_dir: Path) -> None:
    state: dict[str, Any] = {
        "title": page.title(),
        "url": page.url,
    }
    try:
        text = _exam_converter_main(page).inner_text(timeout=2_000)
        state["text_source"] = "exam_converter_main"
    except Exception as exc:  # pragma: no cover - diagnostic evidence only.
        state["main_text_error"] = type(exc).__name__
        try:
            text = page.locator("body").inner_text(timeout=2_000)
            state["text_source"] = "body"
        except Exception as body_exc:  # pragma: no cover - diagnostic evidence only.
            text = ""
            state["body_text_error"] = type(body_exc).__name__
            state["text_source"] = "unavailable"
    (artifact_dir / "failure-page-state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (artifact_dir / "failure-main-text.txt").write_text(text, encoding="utf-8")


def _enabled_count(locator: Locator) -> int:
    return sum(1 for index in range(locator.count()) if locator.nth(index).is_enabled())


def _selected_detail_dom_diagnostics(page: Page) -> dict[str, Any]:
    details = page.locator(SELECTED_QUESTION_DETAIL_SELECTOR)
    rows = page.locator('[data-test^="exam-converter-question-row-"]')
    accept_buttons = page.locator(ADVISORY_ANSWER_KEY_ACCEPT_SELECTOR)
    detail_entries: list[dict[str, Any]] = []
    for index in range(details.count()):
        detail = details.nth(index)
        scoped_accept_buttons = _advisory_answer_key_accept_button(detail)
        detail_entries.append(
            {
                "accept_button_count": scoped_accept_buttons.count(),
                "accept_button_enabled_count": _enabled_count(scoped_accept_buttons),
                "accept_button_visible_count": len(_visible_indexes(scoped_accept_buttons)),
                "advisory_panel_count": _advisory_answer_key_panel(detail).count(),
                "data_selected_item_id": detail.get_attribute("data-selected-item-id"),
                "index": index,
                "visible": detail.is_visible(),
            }
        )
    selected_row_ids: list[str] = []
    review_required_row_ids: list[str] = []
    for index in range(rows.count()):
        row = rows.nth(index)
        row_test_id = row.get_attribute("data-test")
        if not row_test_id:
            continue
        item_id = row_test_id.removeprefix("exam-converter-question-row-")
        if row.get_attribute("aria-selected") == "true":
            selected_row_ids.append(item_id)
        if _row_has_compact_status(row, COMPACT_REVIEW_REQUIRED_LABEL):
            review_required_row_ids.append(item_id)
    return {
        "advisory_accept_button_count": accept_buttons.count(),
        "advisory_accept_button_enabled_count": _enabled_count(accept_buttons),
        "advisory_accept_button_visible_count": len(_visible_indexes(accept_buttons)),
        "details": detail_entries,
        "review_required_row_ids": review_required_row_ids,
        "selected_row_ids": selected_row_ids,
    }


def _write_failure_dom_diagnostics(page: Page, artifact_dir: Path) -> dict[str, Any]:
    diagnostics = _selected_detail_dom_diagnostics(page)
    path = artifact_dir / "failure-dom-diagnostics.json"
    path.write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"path": str(path), **diagnostics}


def _exception_metadata(exc: BaseException) -> dict[str, str]:
    return {
        "exception_type": type(exc).__name__,
        "message": str(exc),
    }


def _record_failure_artifact_error(
    summary: dict[str, Any],
    *,
    artifact: str,
    exc: BaseException,
) -> None:
    summary.setdefault("failure_artifact_errors", []).append(
        {
            "artifact": artifact,
            **_exception_metadata(exc),
        }
    )


def _record_failure_artifacts(
    page: Page,
    *,
    artifact_dir: Path,
    original_exception: BaseException,
    summary: dict[str, Any],
) -> None:
    summary["failed_at"] = datetime.now(UTC).isoformat()
    summary["failure"] = _exception_metadata(original_exception)
    failure_screenshot = artifact_dir / "failure.png"
    try:
        page.screenshot(path=str(failure_screenshot), full_page=True)
    except Exception as screenshot_exc:  # pragma: no cover - covered via unit double.
        _record_failure_artifact_error(
            summary,
            artifact="screenshot",
            exc=screenshot_exc,
        )
    else:
        summary["screenshots"].append(str(failure_screenshot))
    try:
        _write_failure_text(page, artifact_dir)
    except Exception as failure_text_exc:  # pragma: no cover - covered via unit double.
        _record_failure_artifact_error(
            summary,
            artifact="failure_text",
            exc=failure_text_exc,
        )
    try:
        summary["failure_dom_diagnostics"] = _write_failure_dom_diagnostics(
            page,
            artifact_dir,
        )
    except Exception as diagnostics_exc:  # pragma: no cover - diagnostic best effort.
        _record_failure_artifact_error(
            summary,
            artifact="failure_dom_diagnostics",
            exc=diagnostics_exc,
        )
    try:
        _write_summary(summary, artifact_dir)
    except Exception as summary_exc:  # pragma: no cover - diagnostic best effort.
        _record_failure_artifact_error(
            summary,
            artifact="summary",
            exc=summary_exc,
        )


def _handle_request(
    request: Any,
    *,
    summary: dict[str, Any],
    story58_capture: Story58PrivateRequestCapture | None,
) -> None:
    if CORRECTION_APPLY_MARKER in request.url and request.method == "POST":
        summary["correction_apply_requests"].append(_summarize_apply_request(request))
    if story58_capture is not None:
        story58_capture.handle_request(request)


def run(argv: Sequence[str] | None = None) -> dict[str, Any]:
    args = _parse_args(argv)
    if args.timeout_seconds <= 0:
        raise ValueError("--timeout-seconds must be greater than zero")
    signal.signal(
        signal.SIGALRM,
        lambda _signum, _frame: (_ for _ in ()).throw(
            TimeoutError(f"PR-0337 proof exceeded {args.timeout_seconds} seconds.")
        ),
    )
    signal.alarm(args.timeout_seconds)
    source_dxe = Path(args.source_dxe).expanduser()
    if not source_dxe.is_absolute():
        source_dxe = Path.cwd() / source_dxe
    if not source_dxe.is_file():
        raise FileNotFoundError(source_dxe)

    artifact_dir = _run_dir(Path(args.artifact_root))
    story58_capture = (
        Story58PrivateRequestCapture(
            private_dir=args.story58_private_request_capture_dir,
            retained_artifact_dir=artifact_dir,
        )
        if args.story58_private_request_capture_dir is not None
        else None
    )
    config = get_config(["--base-url", args.base_url, "--dotenv", args.dotenv])
    uploaded_source_dxe = (
        source_dxe
        if args.preserve_source_filename
        else _fresh_source_copy(source_dxe, artifact_dir)
    )
    expected_pdf_filename = f"{uploaded_source_dxe.stem}.pdf"
    expected_qti_filename = f"{uploaded_source_dxe.stem}.zip"
    summary: dict[str, Any] = {
        "artifact_dir": str(artifact_dir),
        "base_url": config.base_url,
        "artifact_downloads": [],
        "browser_console": [],
        "browser_page_errors": [],
        "correction_apply_requests": [],
        "correction_apply_responses": [],
        "correction_session_responses": [],
        "correction_source_state_responses": [],
        "file_saves": [],
        "screenshots": [],
        "sir_convert_submit_responses": [],
        "source_dxe": str(source_dxe),
        "source_filename_mode": "preserved" if args.preserve_source_filename else "run_scoped_copy",
        "story58_artifact_set_snapshots": [],
        "submit_idempotency_reason_expectation": args.expect_submit_idempotency_reason,
        "uploaded_source_dxe": str(uploaded_source_dxe),
        "started_at": datetime.now(UTC).isoformat(),
    }
    refresh_story58_artifact_set_invariants(summary)
    _mark_progress(summary, artifact_dir, "artifact_dir_created")
    runtime_evidence = start_correction_session_runtime_evidence(
        artifact_dir=artifact_dir,
        base_url=config.base_url,
        capture_local_backend_logs=args.capture_local_backend_logs,
        capture_hemma_service_logs=args.capture_hemma_service_logs,
        hemma_ssh_host=args.hemma_ssh_host,
    )

    with sync_playwright() as playwright:
        _mark_progress(summary, artifact_dir, "playwright_started")
        browser = launch_chromium(playwright)
        context = browser.new_context(
            accept_downloads=True,
            viewport={"height": 1117, "width": 1728},
        )
        page = context.new_page()
        page.set_default_timeout(10_000)
        page.set_default_navigation_timeout(15_000)
        _mark_progress(summary, artifact_dir, "browser_context_ready")
        page.on(
            "console",
            lambda message: summary["browser_console"].append(
                {"text": message.text, "type": message.type}
            ),
        )
        page.on("pageerror", lambda error: summary["browser_page_errors"].append(str(error)))
        page.on(
            "request",
            lambda request: _handle_request(
                request,
                summary=summary,
                story58_capture=story58_capture,
            ),
        )
        page.on(
            "response",
            lambda response: (
                summary["correction_apply_responses"].append(_summarize_response(response))
                if CORRECTION_APPLY_MARKER in response.url
                else summary["correction_source_state_responses"].append(
                    _summarize_response(response)
                )
                if CORRECTION_SOURCE_STATE_MARKER in response.url
                else summary["correction_session_responses"].append(_summarize_response(response))
                if CORRECTION_SESSION_MARKER in response.url
                else summary["sir_convert_submit_responses"].append(_summarize_response(response))
                if SIR_CONVERT_SUBMIT_MARKER in response.url
                else None
            ),
        )

        active_exception: BaseException | None = None
        try:
            _mark_progress(summary, artifact_dir, "login_start")
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
            _mark_progress(summary, artifact_dir, "login_complete")
            page.screenshot(path=str(artifact_dir / "01-authenticated.png"), full_page=True)
            summary["screenshots"].append(str(artifact_dir / "01-authenticated.png"))
            _write_summary(summary, artifact_dir)

            page.locator('[data-test="exam-converter-reset-local-choices"]').click()
            _mark_progress(summary, artifact_dir, "local_choices_reset")
            page.set_input_files(
                '[data-test="exam-converter-rail-source-file-input"]', str(uploaded_source_dxe)
            )
            expect(page.locator(START_CONVERSION_SELECTOR)).to_be_enabled(timeout=10_000)
            page.locator(START_CONVERSION_SELECTOR).click()
            _mark_progress(summary, artifact_dir, "conversion_started")
            expect(page.locator('[data-test="exam-converter-inspection-surface"]')).to_be_visible(
                timeout=45_000
            )
            _mark_progress(summary, artifact_dir, "inspection_surface_visible")
            page.screenshot(path=str(artifact_dir / "02-review-surface.png"), full_page=True)
            summary["screenshots"].append(str(artifact_dir / "02-review-surface.png"))
            summary["compact_status_counts_before_review"] = _compact_status_counts(page)
            _write_summary(summary, artifact_dir)
            if args.allow_existing_ready_session:
                page.locator('[data-test="exam-converter-inspection-tab-files"]').click()
                expect(
                    page.locator('[data-test="exam-converter-files-readiness-list"]')
                ).to_be_visible(timeout=30_000)
                enabled_downloads = page.locator(
                    '[data-test^="exam-converter-download-file-"]:enabled'
                )
                if enabled_downloads.count() >= 2:
                    summary["existing_ready_session_file_actions_only"] = True
                    _mark_progress(summary, artifact_dir, "existing_ready_session_detected")
                    _prove_replayed_file_actions(
                        page,
                        artifact_dir=artifact_dir,
                        base_url=config.base_url,
                        summary=summary,
                        expected_pdf_filename=expected_pdf_filename,
                        expected_qti_filename=expected_qti_filename,
                    )
                    if args.expect_submit_idempotency_reason:
                        _assert_submit_idempotency_reason(
                            summary,
                            args.expect_submit_idempotency_reason,
                        )
                    summary["completed_at"] = datetime.now(UTC).isoformat()
                    _mark_progress(summary, artifact_dir, "proof_complete")
                    return summary
                page.locator('[data-test="exam-converter-inspection-tab-questions"]').click()

            accept_probe_item_id = _find_review_required_advisory_question(page)
            summary["accept_unchanged_advisory_item_id"] = accept_probe_item_id
            summary["accept_unchanged_advisory_action"] = "Acceptera"
            summary["accept_unchanged_advisory_saved_item_id"] = _save_review_required_answer_key(
                page,
                expected_item_id=accept_probe_item_id,
            )
            summary["accept_unchanged_advisory_status"] = COMPACT_COMPLETE_LABEL
            summary["compact_status_counts_after_accept_probe"] = _compact_status_counts(page)
            summary["post_accept_untouched_advisory_sibling"] = (
                _assert_untouched_advisory_sibling_preserved(
                    page,
                    accepted_item_id=summary["accept_unchanged_advisory_saved_item_id"],
                )
            )
            page.screenshot(path=str(artifact_dir / "02a-accept-advisory.png"), full_page=True)
            summary["screenshots"].append(str(artifact_dir / "02a-accept-advisory.png"))
            _mark_progress(summary, artifact_dir, "accept_unchanged_advisory_saved")
            summary["accept_probe_correction_session_revert"] = _revert_active_correction_intents(
                page,
                base_url=config.base_url,
                summary=summary,
            )
            _mark_progress(summary, artifact_dir, "accept_probe_correction_session_reverted")

            page.locator('[data-test="exam-converter-reset-local-choices"]').click()
            _mark_progress(summary, artifact_dir, "local_choices_reset_after_accept_probe")
            page.set_input_files(
                '[data-test="exam-converter-rail-source-file-input"]', str(uploaded_source_dxe)
            )
            expect(page.locator(START_CONVERSION_SELECTOR)).to_be_enabled(timeout=10_000)
            page.locator(START_CONVERSION_SELECTOR).click()
            _mark_progress(summary, artifact_dir, "second_conversion_started")
            expect(page.locator('[data-test="exam-converter-inspection-surface"]')).to_be_visible(
                timeout=45_000
            )
            _mark_progress(summary, artifact_dir, "second_inspection_surface_visible")
            page.screenshot(
                path=str(artifact_dir / "02b-review-surface-edit-proof.png"), full_page=True
            )
            summary["screenshots"].append(str(artifact_dir / "02b-review-surface-edit-proof.png"))
            summary["compact_status_counts_before_full_correction"] = _compact_status_counts(page)
            _write_summary(summary, artifact_dir)

            _select_question(page, TARGET_ITEM_ID)
            summary["draft_negative_proof"] = _assert_local_draft_does_not_unlock_files(page)
            _mark_progress(summary, artifact_dir, "draft_negative_proof_complete")
            _select_question(page, TARGET_ITEM_ID)

            review_required_edit_item_id, review_required_edit_preparation = (
                _save_review_required_answer_key_edit(page)
            )
            summary["review_required_edit_item_id"] = review_required_edit_item_id
            summary["review_required_edit_action"] = "Ändra"
            summary["review_required_edit_preparation"] = review_required_edit_preparation
            summary["review_required_edit_status"] = _assert_row_status_is_one_of(
                page,
                review_required_edit_item_id,
                (COMPACT_TEACHER_MODIFIED_LABEL, COMPACT_COMPLETE_LABEL),
            )
            _mark_progress(summary, artifact_dir, "review_required_answer_key_edited")

            remaining_saved_review_required_item_ids = _save_all_review_required_answer_keys(page)
            summary["remaining_saved_review_required_item_ids"] = (
                remaining_saved_review_required_item_ids
            )
            review_required_excluded_item_ids = {
                review_required_edit_item_id,
                *remaining_saved_review_required_item_ids,
            }
            remaining_manual_review_required_items = _save_all_review_required_manual_answer_keys(
                page,
                excluded_item_ids=review_required_excluded_item_ids,
            )
            summary["remaining_manual_review_required_answer_key_items"] = (
                remaining_manual_review_required_items
            )
            summary["compact_status_counts_after_review_required"] = _compact_status_counts(page)
            _mark_progress(summary, artifact_dir, "remaining_review_required_answer_keys_saved")

            saved_validation_required_items = _save_all_validation_required_answer_keys(page)
            summary["saved_validation_required_answer_key_items"] = saved_validation_required_items
            summary["compact_status_counts_after_validation_required"] = _compact_status_counts(
                page
            )
            _mark_progress(summary, artifact_dir, "validation_required_answer_keys_saved")

            _observe_replayed_pdf_artifact_set(
                page,
                artifact_dir=artifact_dir,
                expected_pdf_filename=expected_pdf_filename,
                observed_via="exportable-baseline-download",
                summary=summary,
            )
            _mark_progress(summary, artifact_dir, "story58_exportable_baseline_observed")

            _select_question(page, TARGET_ITEM_ID)
            page.locator('[data-test="exam-converter-point-correction-input"]').fill(
                UPDATED_ITEM_POINTS
            )
            _click_and_wait_for_apply(
                page,
                '[data-test="exam-converter-apply-point-correction-action"]',
            )
            _mark_progress(summary, artifact_dir, "point_correction_saved")

            page.locator('[data-test="exam-converter-item-text-patch-input"]').fill(
                UPDATED_ITEM_PROMPT
            )
            _click_and_wait_for_apply(
                page,
                '[data-test="exam-converter-apply-item-text-patch-action"]',
            )
            _mark_progress(summary, artifact_dir, "prompt_correction_saved")

            _observe_replayed_pdf_artifact_set(
                page,
                artifact_dir=artifact_dir,
                expected_pdf_filename=expected_pdf_filename,
                observed_via="post-distinct-correction-download",
                summary=summary,
            )
            _mark_progress(summary, artifact_dir, "story58_distinct_correction_observed")

            page.locator('[data-test="exam-converter-inspection-tab-files"]').click()
            expect(page.locator('[data-test="exam-converter-files-readiness-list"]')).to_be_visible(
                timeout=30_000,
            )
            page.screenshot(path=str(artifact_dir / "03-replayed-files.png"), full_page=True)
            summary["screenshots"].append(str(artifact_dir / "03-replayed-files.png"))
            _write_summary(summary, artifact_dir)

            page.wait_for_timeout(45_000)
            _reload_and_wait_for_replay(page)
            _mark_progress(summary, artifact_dir, "page_reloaded")
            expect(page.locator('[data-test="exam-converter-inspection-surface"]')).to_be_visible(
                timeout=30_000
            )
            _select_question(page, TARGET_ITEM_ID)
            expect(
                page.locator('[data-test="exam-converter-item-text-patch-input"]')
            ).to_have_value(
                UPDATED_ITEM_PROMPT,
                timeout=30_000,
            )
            expect(
                page.locator('[data-test="exam-converter-point-correction-input"]')
            ).to_have_value(
                UPDATED_ITEM_POINTS,
                timeout=30_000,
            )
            detail_text = page.locator(SELECTED_QUESTION_DETAIL_SELECTOR).inner_text(timeout=10_000)
            summary["reload_detail_text"] = detail_text
            page.screenshot(path=str(artifact_dir / "04-after-reload.png"), full_page=True)
            summary["screenshots"].append(str(artifact_dir / "04-after-reload.png"))
            _write_summary(summary, artifact_dir)

            summary["mobile_surface_checks"] = _capture_mobile_surface_checks(
                page,
                artifact_dir=artifact_dir,
            )
            summary["screenshots"].extend(summary["mobile_surface_checks"]["screenshots"])
            _mark_progress(summary, artifact_dir, "mobile_surface_checks_complete")

            _prove_replayed_file_actions(
                page,
                artifact_dir=artifact_dir,
                base_url=config.base_url,
                summary=summary,
                expected_pdf_filename=expected_pdf_filename,
                expected_qti_filename=expected_qti_filename,
            )
            if args.expect_submit_idempotency_reason:
                _assert_submit_idempotency_reason(summary, args.expect_submit_idempotency_reason)
            summary["completed_at"] = datetime.now(UTC).isoformat()
            _mark_progress(summary, artifact_dir, "proof_complete")
        except Exception as exc:
            active_exception = exc
            _record_failure_artifacts(
                page,
                artifact_dir=artifact_dir,
                original_exception=exc,
                summary=summary,
            )
            raise
        finally:
            runtime_evidence.stop()
            runtime_evidence.attach_to_summary(summary, artifact_dir)
            if story58_capture is not None:
                story58_capture.attach_to_summary(summary)
            _write_final_summary(
                summary,
                artifact_dir,
                active_exception=active_exception,
            )
            signal.alarm(0)
            browser.close()

    return summary


def main(argv: Sequence[str] | None = None) -> None:
    summary = run(argv)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
