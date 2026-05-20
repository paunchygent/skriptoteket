"""PR-0337 live proof for durable Exam Converter correction sessions.

Domain purpose:
    Exercise the authenticated correction-session workflow through browser
    reload, Skriptoteket readback, Sir Convert stateless replay, and artifact
    download inspection.

Relationships:
    - Targets `PR-0337` / `ST-21-04` durable teacher correction proof.
    - Uses the shared HuleEdu browser-session login helper.
    - Retains redacted UI, network, replay, and artifact evidence under
      `.artifacts/playwright-pr-0337-correction-session-live/`.
"""

from __future__ import annotations

import argparse
import json
import shutil
import signal
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zipfile import ZipFile

from playwright.sync_api import Page, Response, expect, sync_playwright
from pypdf import PdfReader

from scripts._playwright_auth import login_via_auth_entry
from scripts._playwright_browser import launch_chromium
from scripts._playwright_config import get_config
from scripts._pr_0331_reviewed_ai_facit_artifacts import (
    FORBIDDEN_ARTIFACT_TEXT,
    inspect_qti,
)

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
TARGET_ITEM_ID = "item-001"
UPDATED_ITEM_POINTS = "3"
UPDATED_ITEM_PROMPT = "Vilken process frigör energi ur socker med hjälp av syre?"
DEFAULT_PROOF_TIMEOUT_SECONDS = 60


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PR-0337 durable correction-session live proof")
    parser.add_argument("--source-dxe", default=str(DEFAULT_SOURCE_DXE))
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--dotenv", default=".env")
    parser.add_argument("--artifact-root", default=str(ARTIFACT_ROOT))
    parser.add_argument("--timeout-seconds", default=DEFAULT_PROOF_TIMEOUT_SECONDS, type=int)
    return parser.parse_args(argv)


def _run_dir(root: Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = root / timestamp
    path.mkdir(parents=True, exist_ok=False)
    return path


def _write_summary(summary: dict[str, Any], artifact_dir: Path) -> None:
    (artifact_dir / "manifest.redacted.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _mark_progress(summary: dict[str, Any], artifact_dir: Path, step: str) -> None:
    summary.setdefault("progress", []).append({"at": datetime.now(UTC).isoformat(), "step": step})
    _write_summary(summary, artifact_dir)


def _safe_url(url: str) -> str:
    return urlparse(url).path


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


def _summarize_apply_request(request: Any) -> dict[str, Any]:
    payload = _json_request_payload(request) or {}
    corrections = payload.get("corrections")
    correction_rows = corrections if isinstance(corrections, list) else []
    return {
        "correction_count": len(correction_rows),
        "corrections": [
            {
                "entry_id": entry.get("entry_id"),
                "item_id": entry.get("item_id"),
                "kind": entry.get("kind"),
                "sequence": entry.get("sequence"),
            }
            for entry in correction_rows
            if isinstance(entry, dict)
        ],
        "has_source_binding": isinstance(payload.get("source_binding"), dict),
        "method": request.method,
        "path": _safe_url(request.url),
        "requested_targets": payload.get("requested_targets"),
        "schema_version": payload.get("schema_version"),
    }


def _summarize_json_payload(payload: dict[str, Any]) -> dict[str, Any]:
    report = payload.get("correction_report")
    accepted_entries = report.get("accepted_entries", []) if isinstance(report, dict) else []
    rejected_entries = report.get("rejected_entries", []) if isinstance(report, dict) else []
    target_readiness = payload.get("target_readiness")
    readiness_rows = (
        target_readiness.get("targets", []) if isinstance(target_readiness, dict) else []
    )
    effective_state = payload.get("effective_state")
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
    return {
        "accepted_correction_count": len(accepted_entries)
        if isinstance(accepted_entries, list)
        else 0,
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
    }


def _download_response_predicate(response: Response) -> bool:
    path = _safe_url(response.url)
    return (
        "/sir-convert/v2/convert/jobs/" in path
        and "/artifacts/" in path
        and response.request.method == "GET"
        and "application/json" not in (response.headers.get("content-type") or "")
    )


def _artifact_key_from_download_response(response: Response) -> str:
    return _safe_url(response.url).rsplit("/", 1)[-1]


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
    replay_artifact_key = _artifact_key_from_download_response(response)
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
        "path": _safe_url(response.url),
        "replay_artifact_key": replay_artifact_key,
        "status": response.status,
        "suggested_filename": output_path.name,
        "ui_artifact_key": artifact_key,
    }


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
    replay_artifact_key = _artifact_key_from_download_response(artifact_response)
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
        "download_path": _safe_url(artifact_response.url),
        "replay_artifact_key": replay_artifact_key,
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
        entry["json"] = _summarize_json_payload(payload)
    return entry


def _retry_after_seconds(response_body: str) -> int | None:
    try:
        payload = json.loads(response_body)
    except json.JSONDecodeError:
        return None
    retry_after = payload.get("retry_after_seconds") if isinstance(payload, dict) else None
    return retry_after if isinstance(retry_after, int) and retry_after >= 0 else None


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


def _row_has_ai_suggestion(row: Any) -> bool:
    status = row.locator('[aria-label="AI-förslag"]')
    return status.count() > 0 and status.first.is_visible()


def _click_and_wait_for_apply(page: Page, selector: str) -> None:
    with page.expect_response(
        lambda response: (
            CORRECTION_SESSION_MARKER in response.url
            and response.request.method in {"PUT", "DELETE"}
        ),
        timeout=30_000,
    ) as session_response_info:
        page.locator(selector).click()
    session_response = session_response_info.value
    if session_response.status >= 400:
        raise AssertionError(
            f"Correction-session write failed with HTTP {session_response.status}."
        )
    apply_response = page.wait_for_event(
        "response",
        predicate=lambda response: (
            CORRECTION_APPLY_MARKER in response.url and response.request.method == "POST"
        ),
        timeout=30_000,
    )
    if apply_response.status >= 400:
        raise AssertionError(
            f"Correction replay failed with HTTP {apply_response.status}: {apply_response.text()}"
        )
    page.wait_for_timeout(1_000)


def _select_question(page: Page, item_id: str) -> None:
    page.locator('[data-test="exam-converter-inspection-tab-questions"]').click()
    page.locator(f'[data-test="exam-converter-question-row-{item_id}"]').click()
    expect(page.locator(f'[data-test="exam-converter-question-row-{item_id}"]')).to_have_attribute(
        "aria-selected",
        "true",
        timeout=10_000,
    )


def _find_ai_suggestion_question(page: Page) -> str:
    page.locator('[data-test="exam-converter-inspection-tab-questions"]').click()
    rows = page.locator('[data-test^="exam-converter-question-row-"]')
    for index in range(rows.count()):
        row = rows.nth(index)
        row_test_id = row.get_attribute("data-test")
        if not row_test_id:
            continue
        if not _row_has_ai_suggestion(row):
            continue
        row.click()
        editor = page.locator('[data-test="exam-converter-manual-answer-key-editor"]')
        save_button = page.locator('[data-test="exam-converter-apply-manual-answer-key-action"]')
        if editor.count() > 0 and editor.first.is_visible() and save_button.is_enabled():
            return row_test_id.removeprefix("exam-converter-question-row-")
    raise AssertionError("No visible AI-suggested answer-key editor was found.")


def _selected_question_id(page: Page) -> str:
    rows = page.locator('[data-test^="exam-converter-question-row-"]')
    for index in range(rows.count()):
        row = rows.nth(index)
        if row.get_attribute("aria-selected") == "true":
            row_test_id = row.get_attribute("data-test")
            if row_test_id:
                return row_test_id.removeprefix("exam-converter-question-row-")
    raise AssertionError("No selected question row was visible.")


def _save_visible_answer_key(page: Page) -> str:
    item_id = _selected_question_id(page)
    _click_and_wait_for_apply(
        page,
        '[data-test="exam-converter-apply-manual-answer-key-action"]',
    )
    return item_id


def _save_all_ai_suggestion_answer_keys(page: Page) -> list[str]:
    saved_item_ids: list[str] = []
    for _ in range(12):
        try:
            item_id = _find_ai_suggestion_question(page)
        except AssertionError:
            return saved_item_ids
        if item_id in saved_item_ids:
            raise AssertionError(f"AI suggestion review did not advance past {item_id}.")
        saved_item_ids.append(_save_visible_answer_key(page))
        page.wait_for_timeout(250)
    raise AssertionError("AI suggestion review exceeded the expected item count.")


def _assert_selected_moved_to_next_suggestion(page: Page, previous_item_id: str) -> str:
    next_item_id = _selected_question_id(page)
    if next_item_id == previous_item_id:
        rows = page.locator('[data-test^="exam-converter-question-row-"]')
        for index in range(rows.count()):
            row = rows.nth(index)
            row_test_id = row.get_attribute("data-test")
            if row_test_id == f"exam-converter-question-row-{previous_item_id}":
                continue
            if not _row_has_ai_suggestion(row):
                continue
            row.click()
            editor = page.locator('[data-test="exam-converter-manual-answer-key-editor"]')
            save_button = page.locator(
                '[data-test="exam-converter-apply-manual-answer-key-action"]'
            )
            if editor.count() > 0 and editor.first.is_visible() and save_button.is_enabled():
                raise AssertionError("Saving an AI-suggested answer key did not advance review.")
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


def _choose_manual_choice(page: Page) -> str:
    choices = page.locator('[data-test^="exam-converter-manual-choice-"]')
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


def _write_failure_text(page: Page, artifact_dir: Path) -> None:
    (artifact_dir / "failure-main-text.txt").write_text(
        _exam_converter_main(page).inner_text(timeout=10_000),
        encoding="utf-8",
    )


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
    config = get_config(["--base-url", args.base_url, "--dotenv", args.dotenv])
    fresh_source_dxe = _fresh_source_copy(source_dxe, artifact_dir)
    expected_pdf_filename = f"{fresh_source_dxe.stem}.pdf"
    expected_qti_filename = f"{fresh_source_dxe.stem}.zip"
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
        "uploaded_source_dxe": str(fresh_source_dxe),
        "started_at": datetime.now(UTC).isoformat(),
    }
    _mark_progress(summary, artifact_dir, "artifact_dir_created")

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
            lambda request: (
                summary["correction_apply_requests"].append(_summarize_apply_request(request))
                if CORRECTION_APPLY_MARKER in request.url and request.method == "POST"
                else None
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

        try:
            _mark_progress(summary, artifact_dir, "login_start")
            login_via_auth_entry(
                page,
                base_url=config.base_url.rstrip("/"),
                email=config.email,
                password=config.password,
                next_path=APP_PATH,
                success_heading_pattern=r"^Konvertera prov$",
                attempts=1,
                failure_artifacts_dir=artifact_dir,
                failure_screenshot_name="login-failure.png",
                form_timeout_ms=8_000,
                success_timeout_ms=10_000,
            )
            _mark_progress(summary, artifact_dir, "login_complete")
            page.screenshot(path=str(artifact_dir / "01-authenticated.png"), full_page=True)
            summary["screenshots"].append(str(artifact_dir / "01-authenticated.png"))
            _write_summary(summary, artifact_dir)

            page.locator('[data-test="exam-converter-reset-local-choices"]').click()
            _mark_progress(summary, artifact_dir, "local_choices_reset")
            page.set_input_files(
                '[data-test="exam-converter-rail-source-file-input"]', str(fresh_source_dxe)
            )
            expect(page.locator('[data-test="exam-converter-start-conversion"]')).to_be_enabled(
                timeout=10_000
            )
            page.locator('[data-test="exam-converter-start-conversion"]').click()
            _mark_progress(summary, artifact_dir, "conversion_started")
            expect(page.locator('[data-test="exam-converter-inspection-surface"]')).to_be_visible(
                timeout=45_000
            )
            _mark_progress(summary, artifact_dir, "inspection_surface_visible")
            page.screenshot(path=str(artifact_dir / "02-review-surface.png"), full_page=True)
            summary["screenshots"].append(str(artifact_dir / "02-review-surface.png"))
            _write_summary(summary, artifact_dir)

            _select_question(page, TARGET_ITEM_ID)
            summary["draft_negative_proof"] = _assert_local_draft_does_not_unlock_files(page)
            _mark_progress(summary, artifact_dir, "draft_negative_proof_complete")
            _select_question(page, TARGET_ITEM_ID)

            ai_item_id = _find_ai_suggestion_question(page)
            summary["first_ai_suggestion_item_id"] = ai_item_id
            saved_ai_item_id = _save_visible_answer_key(page)
            summary["first_saved_ai_suggestion_item_id"] = saved_ai_item_id
            summary["next_ai_suggestion_item_id"] = _assert_selected_moved_to_next_suggestion(
                page,
                saved_ai_item_id,
            )
            _mark_progress(summary, artifact_dir, "first_ai_suggestion_saved")

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

            remaining_saved_ai_item_ids = _save_all_ai_suggestion_answer_keys(page)
            summary["remaining_saved_ai_suggestion_item_ids"] = remaining_saved_ai_item_ids
            _mark_progress(summary, artifact_dir, "remaining_ai_suggestions_saved")
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
            detail_text = page.locator(
                '[data-test="exam-converter-selected-question-detail"]'
            ).inner_text(timeout=10_000)
            summary["reload_detail_text"] = detail_text
            page.screenshot(path=str(artifact_dir / "04-after-reload.png"), full_page=True)
            summary["screenshots"].append(str(artifact_dir / "04-after-reload.png"))
            _write_summary(summary, artifact_dir)

            page.locator('[data-test="exam-converter-inspection-tab-files"]').click()
            expect(page.locator('[data-test="exam-converter-files-readiness-list"]')).to_be_visible(
                timeout=30_000,
            )
            enabled_downloads = page.locator('[data-test^="exam-converter-download-file-"]:enabled')
            if enabled_downloads.count() < 2:
                raise AssertionError("Replay did not expose both file downloads after reload.")
            pdf_path, pdf_download = _download_replayed_file(
                page,
                artifact_key="examnet_pdf",
                artifact_dir=artifact_dir,
                expected_filename=expected_pdf_filename,
            )
            summary["artifact_downloads"].append(pdf_download)
            qti_path, qti_download = _download_replayed_file(
                page,
                artifact_key="qti_package",
                artifact_dir=artifact_dir,
                expected_filename=expected_qti_filename,
            )
            summary["artifact_downloads"].append(qti_download)
            summary["file_saves"].append(
                _save_replayed_file(
                    page,
                    artifact_key="examnet_pdf",
                    expected_filename=expected_pdf_filename,
                )
            )
            summary["file_saves"].append(
                _save_replayed_file(
                    page,
                    artifact_key="qti_package",
                    expected_filename=expected_qti_filename,
                )
            )
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
            summary["completed_at"] = datetime.now(UTC).isoformat()
            _mark_progress(summary, artifact_dir, "proof_complete")
        except Exception:
            summary["failed_at"] = datetime.now(UTC).isoformat()
            page.screenshot(path=str(artifact_dir / "failure.png"), full_page=True)
            summary["screenshots"].append(str(artifact_dir / "failure.png"))
            _write_failure_text(page, artifact_dir)
            _write_summary(summary, artifact_dir)
            raise
        finally:
            _write_summary(summary, artifact_dir)
            signal.alarm(0)
            browser.close()

    return summary


def main(argv: Sequence[str] | None = None) -> None:
    summary = run(argv)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
