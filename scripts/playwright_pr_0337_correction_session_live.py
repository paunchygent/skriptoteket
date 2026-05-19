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
import signal
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Page, Response, expect, sync_playwright
from pypdf import PdfReader

from scripts._playwright_auth import login_via_auth_entry
from scripts._playwright_browser import launch_chromium
from scripts._playwright_config import get_config
from scripts._pr_0331_reviewed_ai_facit_artifacts import (
    FORBIDDEN_ARTIFACT_TEXT,
    download_file,
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
TARGET_ITEM_ID = "item-004"
UPDATED_ITEM_POINTS = "3"
UPDATED_ITEM_TITLE = "Fråga 4 - ändrad i Skriptoteket"
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


def _safe_url(url: str) -> str:
    return urlparse(url).path


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
    target_readiness = payload.get("target_readiness")
    readiness_rows = (
        target_readiness.get("targets", []) if isinstance(target_readiness, dict) else []
    )
    effective_state = payload.get("effective_state")
    return {
        "accepted_correction_count": len(accepted_entries)
        if isinstance(accepted_entries, list)
        else 0,
        "accepted_kinds": [
            entry.get("kind") for entry in accepted_entries if isinstance(entry, dict)
        ],
        "effective_item_count": len(effective_state.get("items", []))
        if isinstance(effective_state, dict)
        else None,
        "ready_targets": [
            row.get("target")
            for row in readiness_rows
            if isinstance(row, dict) and row.get("export_enabled") is True
        ],
        "request_id": payload.get("request_id"),
        "schema_version": payload.get("schema_version"),
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


def _visible_indexes(locator: Any) -> list[int]:
    return [index for index in range(locator.count()) if locator.nth(index).is_visible()]


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


def _assert_selected_moved_to_next_suggestion(page: Page, previous_item_id: str) -> str:
    next_item_id = _selected_question_id(page)
    if next_item_id == previous_item_id:
        raise AssertionError("Saving an AI-suggested answer key did not advance review.")
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


def _inspect_pdf(path: Path, *, expected_text: str) -> dict[str, Any]:
    reader = PdfReader(str(path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return {
        "forbidden_text_hits": [value for value in FORBIDDEN_ARTIFACT_TEXT if value in text],
        "page_count": len(reader.pages),
        "path": str(path),
        "updated_title_present": expected_text in text,
    }


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
    summary: dict[str, Any] = {
        "artifact_dir": str(artifact_dir),
        "base_url": config.base_url,
        "browser_console": [],
        "browser_page_errors": [],
        "correction_apply_requests": [],
        "correction_apply_responses": [],
        "correction_session_responses": [],
        "correction_source_state_responses": [],
        "screenshots": [],
        "sir_convert_submit_responses": [],
        "source_dxe": str(source_dxe),
        "started_at": datetime.now(UTC).isoformat(),
    }

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(
            accept_downloads=True,
            viewport={"height": 1117, "width": 1728},
        )
        page = context.new_page()
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

            page.locator('[data-test="exam-converter-reset-local-choices"]').click()
            page.set_input_files(
                '[data-test="exam-converter-rail-source-file-input"]', str(source_dxe)
            )
            expect(page.locator('[data-test="exam-converter-start-conversion"]')).to_be_enabled(
                timeout=10_000
            )
            page.locator('[data-test="exam-converter-start-conversion"]').click()
            expect(page.locator('[data-test="exam-converter-inspection-surface"]')).to_be_visible(
                timeout=300_000
            )
            page.screenshot(path=str(artifact_dir / "02-review-surface.png"), full_page=True)
            summary["screenshots"].append(str(artifact_dir / "02-review-surface.png"))

            _select_question(page, TARGET_ITEM_ID)
            summary["draft_negative_proof"] = _assert_local_draft_does_not_unlock_files(page)
            _select_question(page, TARGET_ITEM_ID)

            ai_item_id = _find_ai_suggestion_question(page)
            summary["candidate_suppression_item_id"] = ai_item_id
            _click_and_wait_for_apply(
                page,
                '[data-test="exam-converter-reject-ai-suggestion-action"]',
            )
            summary["candidate_suppression_manual_choice_id"] = _choose_manual_choice(page)
            _click_and_wait_for_apply(
                page,
                '[data-test="exam-converter-apply-manual-answer-key-action"]',
            )

            _select_question(page, TARGET_ITEM_ID)
            page.locator('[data-test="exam-converter-point-correction-input"]').fill(
                UPDATED_ITEM_POINTS
            )
            _click_and_wait_for_apply(
                page,
                '[data-test="exam-converter-apply-point-correction-action"]',
            )

            page.locator('[data-test="exam-converter-item-text-patch-field"]').select_option(
                "item_title"
            )
            page.locator('[data-test="exam-converter-item-text-patch-input"]').fill(
                UPDATED_ITEM_TITLE
            )
            _click_and_wait_for_apply(
                page,
                '[data-test="exam-converter-apply-item-text-patch-action"]',
            )

            page.locator('[data-test="exam-converter-accept-all-ai-suggestions-action"]').click()
            _click_and_wait_for_apply(
                page,
                '[data-test="exam-converter-apply-reviewed-ai-suggestions-action"]',
            )
            expect(page.locator('[data-test="exam-converter-files-readiness-list"]')).to_be_visible(
                timeout=120_000,
            )
            page.screenshot(path=str(artifact_dir / "03-replayed-files.png"), full_page=True)
            summary["screenshots"].append(str(artifact_dir / "03-replayed-files.png"))

            page.reload()
            expect(page.locator('[data-test="exam-converter-inspection-surface"]')).to_be_visible(
                timeout=120_000
            )
            _select_question(page, TARGET_ITEM_ID)
            expect(page.locator('[data-test="exam-converter-effective-item-title"]')).to_have_text(
                UPDATED_ITEM_TITLE,
                timeout=30_000,
            )
            detail_text = page.locator(
                '[data-test="exam-converter-selected-question-detail"]'
            ).inner_text(timeout=10_000)
            if f"{UPDATED_ITEM_POINTS} p" not in detail_text or "Ändrad" not in detail_text:
                raise AssertionError("Reloaded detail did not show replayed point correction.")
            if page.locator('[data-test="exam-converter-manual-answer-key-editor"]').count() > 0:
                raise AssertionError("Manual answer-key editor remained after persisted readback.")
            summary["reload_detail_text"] = detail_text
            page.screenshot(path=str(artifact_dir / "04-after-reload.png"), full_page=True)
            summary["screenshots"].append(str(artifact_dir / "04-after-reload.png"))

            page.locator('[data-test="exam-converter-inspection-tab-files"]').click()
            expect(page.locator('[data-test="exam-converter-files-readiness-list"]')).to_be_visible(
                timeout=30_000,
            )
            enabled_downloads = page.locator('[data-test^="exam-converter-download-file-"]:enabled')
            if enabled_downloads.count() < 2:
                raise AssertionError("Replay did not expose both file downloads after reload.")
            pdf_path = download_file(page, artifact_key="examnet_pdf", artifact_dir=artifact_dir)
            qti_path = download_file(page, artifact_key="qti_package", artifact_dir=artifact_dir)
            summary["pdf_inspection"] = _inspect_pdf(pdf_path, expected_text=UPDATED_ITEM_TITLE)
            summary["qti_inspection"] = inspect_qti(qti_path)
            if summary["pdf_inspection"]["forbidden_text_hits"]:
                raise AssertionError("PDF exposes forbidden internal diagnostics.")
            if summary["qti_inspection"]["forbidden_text_hits"]:
                raise AssertionError("QTI exposes forbidden internal diagnostics.")
            if summary["qti_inspection"]["correct_response_count"] == 0:
                raise AssertionError("QTI contains no correctResponse entries.")
            if not summary["pdf_inspection"]["updated_title_present"]:
                raise AssertionError("PDF did not include the replayed title correction.")
            summary["completed_at"] = datetime.now(UTC).isoformat()
        except Exception:
            summary["failed_at"] = datetime.now(UTC).isoformat()
            page.screenshot(path=str(artifact_dir / "failure.png"), full_page=True)
            summary["screenshots"].append(str(artifact_dir / "failure.png"))
            _write_failure_text(page, artifact_dir)
            raise
        finally:
            (artifact_dir / "manifest.redacted.json").write_text(
                json.dumps(summary, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            signal.alarm(0)
            browser.close()

    return summary


def main(argv: Sequence[str] | None = None) -> None:
    summary = run(argv)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
