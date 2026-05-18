"""PR-0331 live proof for reviewed AI-facit artifact integrity.

Domain purpose:
    Exercise the authenticated Exam Converter reviewed-AI-facit flow through
    the browser, HuleEdu auth edge, Sir Convert Gateway, and live provider-backed
    DigiExam conversion runtime.

Relationships:
    - Targets `PR-0331` / `ST-21-03` final acceptance evidence.
    - Uses the shared HuleEdu browser-session login helper.
    - Retains redacted request, response, UI, and downloaded artifact evidence
      under `.artifacts/playwright-pr-0331-reviewed-ai-facit-live/`.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Page, Response, expect, sync_playwright

from scripts._playwright_auth import login_via_auth_entry
from scripts._playwright_browser import launch_chromium
from scripts._playwright_config import get_config
from scripts._pr_0331_reviewed_ai_facit_artifacts import (
    FORBIDDEN_ARTIFACT_TEXT,
    assert_artifact_integrity,
    download_file,
    extract_effective_keys,
    inspect_pdf,
    inspect_qti,
)

ARTIFACT_ROOT = Path(".artifacts/playwright-pr-0331-reviewed-ai-facit-live")
DEFAULT_SOURCE_DXE = Path(
    "/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/inputs/examples/"
    "digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe/"
    "1811577114-ekologiprov-v-49-25d-e.dxe"
)
APP_PATH = "/apps/documents.conversion_hub"
SIR_CONVERT_MARKER = "/sir-convert/v2/convert/"
PUBLIC_SIR_CONVERT_GATEWAY_BASE = "https://api.hule.education/sir-convert/v2/convert"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PR-0331 reviewed AI-facit live artifact proof")
    parser.add_argument("--source-dxe", default=str(DEFAULT_SOURCE_DXE))
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--dotenv", default=".env")
    parser.add_argument("--artifact-root", default=str(ARTIFACT_ROOT))
    return parser.parse_args(argv)


def _run_dir(root: Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = root / timestamp
    path.mkdir(parents=True, exist_ok=False)
    return path


def _safe_url(url: str) -> str:
    parsed = urlparse(url)
    return parsed.path


def _read_json_field(post_data: str, field_name: str) -> Any | None:
    header_pattern = re.compile(
        rf'name="{re.escape(field_name)}"(?:; filename="[^"]+")?'
        rf"(?:\r?\nContent-Type: [^\r\n]+)?\r?\n\r?\n",
    )
    match = header_pattern.search(post_data)
    if not match:
        return None
    end = post_data.find("\r\n--", match.end())
    if end == -1:
        return None
    raw_value = post_data[match.end() : end].strip()
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        return None


def _summarize_overlay(overlay: dict[str, Any] | None) -> dict[str, Any] | None:
    if overlay is None:
        return None
    items = overlay.get("items")
    item_rows = items if isinstance(items, list) else []
    reviewed_items = [
        item
        for item in item_rows
        if isinstance(item, dict) and item.get("reviewed_completion_answer_key")
    ]
    return {
        "item_count": len(item_rows),
        "reviewed_completion_item_count": len(reviewed_items),
        "reviewed_item_ids": [
            str(item.get("item_id")) for item in reviewed_items if item.get("item_id")
        ],
        "schema_version": overlay.get("schema_version"),
        "source_binding_present": isinstance(overlay.get("source_binding"), dict),
    }


def _summarize_submit_request(request: Any) -> dict[str, Any]:
    post_data = request.post_data or ""
    job_spec = _read_json_field(post_data, "job_spec")
    overlay = _read_json_field(post_data, "digiexam_ingestion_overlay")
    options = {}
    if isinstance(job_spec, dict):
        options = job_spec.get("digiexam_migration_options") or {}
    return {
        "method": request.method,
        "path": _safe_url(request.url),
        "has_correlation_id": bool(request.headers.get("x-correlation-id")),
        "has_idempotency_key": bool(request.headers.get("idempotency-key")),
        "has_csrf_token": bool(request.headers.get("x-csrf-token")),
        "post_data_available": bool(post_data),
        "completion_mode": options.get("completion_mode"),
        "ingestion_overlay_filename": options.get("ingestion_overlay_filename"),
        "ingestion_overlay_policy": options.get("ingestion_overlay_policy"),
        "targets": (job_spec.get("conversion") or {}).get("targets")
        if isinstance(job_spec, dict)
        else None,
        "overlay": _summarize_overlay(overlay if isinstance(overlay, dict) else None),
    }


def _summarize_response(response: Response) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "method": response.request.method,
        "path": _safe_url(response.url),
        "status": response.status,
        "content_type": response.headers.get("content-type"),
        "idempotent_replay": response.headers.get("x-idempotent-replay", "").lower() == "true",
    }
    if "application/json" not in (entry["content_type"] or ""):
        return entry
    try:
        payload = response.json()
    except Exception as exc:  # pragma: no cover - diagnostic only.
        entry["json_error"] = str(exc)
        return entry
    entry["json"] = payload
    return entry


def _job_id_from_response(entry: dict[str, Any]) -> str | None:
    payload = entry.get("json")
    if not isinstance(payload, dict):
        return None
    job = payload.get("job")
    if isinstance(job, dict):
        value = job.get("job_id") or job.get("id")
        return str(value) if value else None
    value = payload.get("job_id") or payload.get("id")
    return str(value) if value else None


def _correlation_id_for_submit(requests: list[dict[str, Any]], index: int) -> str | None:
    matching = [request for request in requests if request["method"] == "POST"]
    if index >= len(matching):
        return None
    # Do not persist the raw value in request summaries, but use it for follow-up
    # browser fetches from the same session.
    return matching[index].get("_correlation_id")


def _record_submit_request(target: list[dict[str, Any]], request: Any) -> None:
    if SIR_CONVERT_MARKER not in request.url or request.method != "POST":
        return
    entry = _summarize_submit_request(request)
    entry["_correlation_id"] = request.headers.get("x-correlation-id")
    target.append(entry)


def _public_request_summary(entry: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in entry.items() if not key.startswith("_")}


def _gateway_artifact_path(base_url: str, *, job_id: str, artifact_key: str) -> str:
    suffix = f"/jobs/{job_id}/artifacts/{artifact_key}"
    if base_url.rstrip("/") == "https://skriptoteket.hule.education":
        return f"{PUBLIC_SIR_CONVERT_GATEWAY_BASE}{suffix}"
    return f"/sir-convert/v2/convert{suffix}"


def _browser_fetch_json(page: Page, *, path: str, correlation_id: str, artifact_dir: Path) -> Any:
    response = page.context.request.get(
        path,
        headers={"Accept": "application/json", "X-Correlation-ID": correlation_id},
    )
    text = response.text()
    try:
        body = json.loads(text) if text else None
    except json.JSONDecodeError:
        body = text
    result = {"ok": response.ok, "status": response.status, "body": body}
    if not result["ok"]:
        failure_path = artifact_dir / "browser-fetch-failure.json"
        failure_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        raise AssertionError(f"Browser fetch failed for {path}: {result['status']}")
    return result["body"]


def _summarize_completion_report(report: Any) -> dict[str, Any]:
    if not isinstance(report, dict):
        return {"valid_suggestion_count": 0, "backend_failure_codes": {}, "item_count": 0}
    items = report.get("items")
    item_rows = items if isinstance(items, list) else []
    failure_codes: dict[str, int] = {}
    valid_suggestion_count = 0
    for item in item_rows:
        if not isinstance(item, dict):
            continue
        code = item.get("backend_failure_code")
        if code:
            failure_codes[str(code)] = failure_codes.get(str(code), 0) + 1
        if (
            item.get("decision_state") == "suggested"
            and item.get("validation_state") == "valid"
            and item.get("answer_payload") is not None
        ):
            valid_suggestion_count += 1
    return {
        "backend_failure_codes": failure_codes,
        "completion_mode": report.get("completion_mode"),
        "item_count": len(item_rows),
        "valid_suggestion_count": valid_suggestion_count,
    }


def _collect_advisory_report(
    page: Page,
    *,
    artifact_dir: Path,
    responses: list[dict[str, Any]],
    submit_requests: list[dict[str, Any]],
) -> dict[str, Any] | None:
    submit_responses = [
        entry
        for entry in responses
        if entry["method"] == "POST" and entry["path"].endswith("/jobs")
    ]
    if not submit_responses:
        return None
    job_id = _job_id_from_response(submit_responses[0])
    correlation_id = _correlation_id_for_submit(submit_requests, 0)
    if not job_id or not correlation_id:
        return None
    report = _browser_fetch_json(
        page,
        path=f"/sir-convert/v2/convert/jobs/{job_id}/artifacts/answer_key_completion_report",
        correlation_id=correlation_id,
        artifact_dir=artifact_dir,
    )
    (artifact_dir / "advisory-answer-key-completion-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return _summarize_completion_report(report)


def run(argv: Sequence[str] | None = None) -> dict[str, Any]:
    args = _parse_args(argv)
    source_dxe = Path(args.source_dxe).expanduser()
    if not source_dxe.is_file():
        raise FileNotFoundError(source_dxe)

    artifact_dir = _run_dir(Path(args.artifact_root))
    config = get_config(
        ["--base-url", args.base_url, "--dotenv", args.dotenv],
    )
    summary: dict[str, Any] = {
        "started_at": datetime.now(UTC).isoformat(),
        "artifact_dir": str(artifact_dir),
        "base_url": config.base_url,
        "source_dxe": str(source_dxe),
        "browser_console": [],
        "browser_page_errors": [],
        "sir_convert_submit_requests": [],
        "sir_convert_responses": [],
        "screenshots": [],
    }

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(
            accept_downloads=True, viewport={"width": 1728, "height": 1117}
        )
        page = context.new_page()
        page.on(
            "console",
            lambda message: summary["browser_console"].append(
                {"type": message.type, "text": message.text}
            ),
        )
        page.on("pageerror", lambda error: summary["browser_page_errors"].append(str(error)))
        page.on(
            "request",
            lambda request: _record_submit_request(summary["sir_convert_submit_requests"], request),
        )
        page.on(
            "response",
            lambda response: (
                summary["sir_convert_responses"].append(_summarize_response(response))
                if SIR_CONVERT_MARKER in response.url
                else None
            ),
        )
        run_idempotency_token = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        submit_sequence = 0

        def force_fresh_idempotency(route: Any) -> None:
            nonlocal submit_sequence
            request = route.request
            if SIR_CONVERT_MARKER in request.url and request.method == "POST":
                submit_sequence += 1
                headers = dict(request.headers)
                headers["idempotency-key"] = (
                    f"idem_skriptoteket_pr0331_{run_idempotency_token}_{submit_sequence}"
                )
                route.continue_(headers=headers)
                return
            route.continue_()

        page.route("**/sir-convert/v2/convert/jobs?*", force_fresh_idempotency)
        summary["fresh_idempotency_override"] = True

        try:
            login_via_auth_entry(
                page,
                base_url=config.base_url.rstrip("/"),
                email=config.email,
                password=config.password,
                next_path=APP_PATH,
                success_heading_pattern=r"^Konvertera prov$",
                failure_artifacts_dir=artifact_dir,
                failure_screenshot_name="login-failure.png",
            )
            page.screenshot(path=str(artifact_dir / "01-authenticated.png"), full_page=True)
            summary["screenshots"].append(str(artifact_dir / "01-authenticated.png"))

            page.set_input_files('[data-test="exam-converter-source-file-input"]', str(source_dxe))
            expect(page.locator('[data-test="exam-converter-start-conversion"]')).to_be_enabled(
                timeout=10_000
            )
            page.locator('[data-test="exam-converter-start-conversion"]').click()
            expect(page.locator('[data-test="exam-converter-inspection-surface"]')).to_be_visible(
                timeout=300_000
            )
            ai_panel = page.locator('[data-test="exam-converter-ai-review-action-panel"]')
            if ai_panel.count() == 0 or not ai_panel.first.is_visible():
                summary["advisory_report_summary"] = _collect_advisory_report(
                    page,
                    artifact_dir=artifact_dir,
                    responses=summary["sir_convert_responses"],
                    submit_requests=summary["sir_convert_submit_requests"],
                )
                summary["advisory_terminal_ui_text"] = (
                    page.locator('main[aria-labelledby="exam-converter-auth-title"]')
                    .inner_text(timeout=10_000)
                    .strip()
                )
                raise AssertionError("Advisory pass completed without usable AI-facit suggestions.")
            summary["advisory_ui_text"] = ai_panel.inner_text(timeout=10_000).strip()
            page.screenshot(path=str(artifact_dir / "02-advisory-review.png"), full_page=True)
            summary["screenshots"].append(str(artifact_dir / "02-advisory-review.png"))

            page.locator('[data-test="exam-converter-accept-all-ai-suggestions-action"]').click()
            apply_button = page.locator(
                '[data-test="exam-converter-apply-reviewed-ai-suggestions-action"]'
            )
            expect(apply_button).to_be_enabled(timeout=10_000)
            apply_button.click()
            files_list = page.locator('[data-test="exam-converter-files-readiness-list"]')
            expect(files_list).to_be_visible(timeout=300_000)
            page.screenshot(path=str(artifact_dir / "03-reviewed-files.png"), full_page=True)
            summary["screenshots"].append(str(artifact_dir / "03-reviewed-files.png"))
            summary["post_apply_ui_text"] = (
                page.locator('main[aria-labelledby="exam-converter-auth-title"]')
                .inner_text(timeout=10_000)
                .strip()
            )
            summary["accept_current_state_visible_after_reviewed_apply"] = (
                page.locator('[data-test="exam-converter-accept-current-state-action"]').count() > 0
            )
            summary["raw_reason_code_hits_in_ui"] = [
                value for value in FORBIDDEN_ARTIFACT_TEXT if value in summary["post_apply_ui_text"]
            ]

            submit_responses = [
                entry
                for entry in summary["sir_convert_responses"]
                if entry["method"] == "POST" and entry["path"].endswith("/jobs")
            ]
            reviewed_job_id = (
                _job_id_from_response(submit_responses[-1]) if submit_responses else None
            )
            reviewed_correlation_id = _correlation_id_for_submit(
                summary["sir_convert_submit_requests"], len(submit_responses) - 1
            )
            if not reviewed_job_id or not reviewed_correlation_id:
                raise AssertionError("Could not resolve reviewed apply job id/correlation id.")
            summary["reviewed_apply_job"] = {
                "job_id": reviewed_job_id,
                "correlation_id_present": True,
            }

            effective_ir = _browser_fetch_json(
                page,
                path=_gateway_artifact_path(
                    args.base_url,
                    job_id=reviewed_job_id,
                    artifact_key="effective_ir_json",
                ),
                correlation_id=reviewed_correlation_id,
                artifact_dir=artifact_dir,
            )
            ingestion_overlay_report = _browser_fetch_json(
                page,
                path=_gateway_artifact_path(
                    args.base_url,
                    job_id=reviewed_job_id,
                    artifact_key="ingestion_overlay_report",
                ),
                correlation_id=reviewed_correlation_id,
                artifact_dir=artifact_dir,
            )
            (artifact_dir / "effective-ir-json.json").write_text(
                json.dumps(effective_ir, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (artifact_dir / "ingestion-overlay-report.json").write_text(
                json.dumps(ingestion_overlay_report, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            summary["effective_key_summary"] = extract_effective_keys(effective_ir)
            summary["ingestion_overlay_report_summary"] = {
                "accepted_count": len(ingestion_overlay_report.get("accepted_entries") or [])
                if isinstance(ingestion_overlay_report, dict)
                else 0,
                "rejected_count": len(ingestion_overlay_report.get("rejected_entries") or [])
                if isinstance(ingestion_overlay_report, dict)
                else 0,
            }

            page.locator('[data-test="exam-converter-inspection-tab-files"]').click()
            pdf_path = download_file(page, artifact_key="examnet_pdf", artifact_dir=artifact_dir)
            qti_path = download_file(page, artifact_key="qti_package", artifact_dir=artifact_dir)
            summary["pdf_inspection"] = inspect_pdf(pdf_path, summary["effective_key_summary"])
            summary["qti_inspection"] = inspect_qti(qti_path)
            assert_artifact_integrity(summary)
            summary["completed_at"] = datetime.now(UTC).isoformat()
            return summary
        except Exception:
            summary["failed_at"] = datetime.now(UTC).isoformat()
            page.screenshot(path=str(artifact_dir / "failure.png"), full_page=True)
            summary["screenshots"].append(str(artifact_dir / "failure.png"))
            raise
        finally:
            summary["sir_convert_submit_requests"] = [
                _public_request_summary(entry) for entry in summary["sir_convert_submit_requests"]
            ]
            (artifact_dir / "manifest.redacted.json").write_text(
                json.dumps(summary, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            context.close()
            browser.close()


def main() -> None:
    summary = run()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
