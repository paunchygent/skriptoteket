"""PR-0332 live proof for teacher-authored Exam Converter corrections.

Domain purpose:
    Exercise the authenticated Exam Converter manual correction flow through
    the browser, HuleEdu auth edge, Skriptoteket Gateway client, and Sir Convert
    unified correction runtime.

Relationships:
    - Targets `PR-0332` / `ST-21-03` teacher-owned non-matching correction UI.
    - Uses the shared HuleEdu browser-session login helper.
    - Retains UI screenshots, redacted network summaries, and assertion output
      under `.artifacts/playwright-pr-0332-teacher-corrections-live/`.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Page, Response, expect, sync_playwright

from scripts._playwright_auth import login_via_auth_entry
from scripts._playwright_browser import launch_chromium
from scripts._playwright_config import get_config

ARTIFACT_ROOT = Path(".artifacts/playwright-pr-0332-teacher-corrections-live")
DEFAULT_SOURCE_DXE = Path(
    ".artifacts/pr-0325-live/fresh-inputs/1811577114-ekologiprov-v-49-25d-e-fresh-probe.dxe"
)
APP_PATH = "/apps/documents.conversion_hub"
CORRECTION_APPLY_MARKER = "/sir-convert/v2/exam-authoring/corrections/apply"
CORRECTION_SOURCE_STATE_MARKER = "/sir-convert/v2/exam-authoring/corrections/source-state/issue"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PR-0332 teacher correction live proof")
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
    return urlparse(url).path


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
    except Exception as exc:  # pragma: no cover - diagnostic only.
        entry["json_error"] = str(exc)
        return entry
    if isinstance(payload, dict):
        entry["json"] = _summarize_json_payload(payload)
    return entry


def _summarize_json_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") == "exam_authoring_correction_source_state_issue_result_v1":
        source_binding = payload.get("source_binding")
        source_state = payload.get("source_authoring_state")
        return {
            "schema_version": payload.get("schema_version"),
            "source_bundle_id": source_binding.get("source_bundle_id")
            if isinstance(source_binding, dict)
            else None,
            "source_file_sha256": source_binding.get("source_file_sha256")
            if isinstance(source_binding, dict)
            else None,
            "source_state_item_count": len(source_state.get("items", []))
            if isinstance(source_state, dict)
            else None,
            "source_state_sha256": source_binding.get("source_state_sha256")
            if isinstance(source_binding, dict)
            else None,
        }

    report = payload.get("correction_report")
    effective_state = payload.get("effective_state")
    return {
        "accepted_entries": _summarize_accepted_entries(report),
        "accepted_entry_count": len(report.get("accepted_entries", []))
        if isinstance(report, dict)
        else None,
        "effective_answer_keys": _summarize_effective_answer_keys(effective_state),
        "effective_item_count": len(effective_state.get("items", []))
        if isinstance(effective_state, dict)
        else None,
        "effective_state_sha256": effective_state.get("effective_state_sha256")
        if isinstance(effective_state, dict)
        else None,
        "request_id": payload.get("request_id"),
        "schema_version": payload.get("schema_version"),
    }


def _summarize_accepted_entries(report: object) -> list[dict[str, Any]]:
    if not isinstance(report, dict):
        return []
    accepted_entries = report.get("accepted_entries")
    if not isinstance(accepted_entries, list):
        return []
    rows: list[dict[str, Any]] = []
    for entry in accepted_entries:
        if not isinstance(entry, dict):
            continue
        rows.append(
            {
                "applied_fields": entry.get("applied_fields"),
                "entry_id": entry.get("entry_id"),
                "item_id": entry.get("item_id"),
                "kind": entry.get("kind"),
            }
        )
    return rows


def _summarize_effective_answer_keys(effective_state: object) -> list[dict[str, Any]]:
    if not isinstance(effective_state, dict):
        return []
    items = effective_state.get("items")
    if not isinstance(items, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        for interaction in item.get("choice_interactions") or []:
            if not isinstance(interaction, dict):
                continue
            answer_key = interaction.get("answer_key")
            if not isinstance(answer_key, dict) or answer_key.get("provenance") == "absent":
                continue
            rows.append(
                {
                    "correct_choice_ids": answer_key.get("correct_choice_ids"),
                    "interaction_id": interaction.get("interaction_id"),
                    "item_id": item.get("item_id"),
                    "kind": "choice",
                    "provenance": answer_key.get("provenance"),
                }
            )
        for interaction in item.get("gap_open_cloze_interactions") or []:
            if not isinstance(interaction, dict):
                continue
            answer_key = interaction.get("answer_key")
            if not isinstance(answer_key, dict) or answer_key.get("provenance") == "absent":
                continue
            rows.append(
                {
                    "accepted_value_count": len(answer_key.get("accepted_values") or []),
                    "interaction_id": interaction.get("interaction_id"),
                    "item_id": item.get("item_id"),
                    "kind": "gap_open_cloze",
                    "provenance": answer_key.get("provenance"),
                }
            )
    return rows


def _visible_count(locator: Any) -> int:
    total = locator.count()
    return sum(1 for index in range(total) if locator.nth(index).is_visible())


def _find_manual_choice_question(page: Page) -> tuple[str, str]:
    rows = page.locator('[data-test^="exam-converter-question-row-"]')
    row_count = rows.count()
    for index in range(row_count):
        row = rows.nth(index)
        row_test_id = row.get_attribute("data-test")
        if not row_test_id:
            continue
        row.click()
        choices = page.locator('[data-test^="exam-converter-manual-choice-"]')
        if _visible_count(choices) == 0:
            continue
        return row_test_id.removeprefix("exam-converter-question-row-"), row_test_id
    raise AssertionError("No visible manual choice-answer-key editor was found after conversion.")


def _choose_manual_choice(page: Page) -> str:
    choices = page.locator('[data-test^="exam-converter-manual-choice-"]')
    visible_indexes = [index for index in range(choices.count()) if choices.nth(index).is_visible()]
    if not visible_indexes:
        raise AssertionError("Manual choice editor has no visible choices.")
    target_index = visible_indexes[1] if len(visible_indexes) > 1 else visible_indexes[0]
    choice = choices.nth(target_index)
    choice_test_id = choice.get_attribute("data-test")
    if not choice_test_id:
        raise AssertionError("Manual choice button did not expose a data-test id.")
    choice.click()
    return choice_test_id.removeprefix("exam-converter-manual-choice-")


def _leave_and_return(page: Page, item_id: str) -> None:
    rows = page.locator('[data-test^="exam-converter-question-row-"]')
    for index in range(rows.count()):
        row = rows.nth(index)
        row_test_id = row.get_attribute("data-test")
        if row_test_id and row_test_id != f"exam-converter-question-row-{item_id}":
            row.click()
            break
    page.locator(f'[data-test="exam-converter-question-row-{item_id}"]').click()


def _assert_persisted_choice_visible(page: Page, selected_choice_id: str) -> dict[str, Any]:
    detail = page.locator('[data-test="exam-converter-selected-question-detail"]')
    detail_text = detail.inner_text(timeout=10_000)
    if "Facit" not in detail_text or "Ändrat" not in detail_text:
        raise AssertionError("Persisted answer-key summary is not visible after navigation.")
    if page.locator('[data-test="exam-converter-manual-answer-key-editor"]').count() > 0:
        raise AssertionError("Manual answer-key editor remained visible after returned correction.")

    panel = page.locator(f'[data-test="exam-converter-effective-choice-{selected_choice_id}"]')
    ordinal = page.locator(
        f'[data-test="exam-converter-effective-choice-ordinal-{selected_choice_id}"]'
    )
    expect(panel).to_be_visible(timeout=10_000)
    expect(ordinal).to_be_visible(timeout=10_000)
    panel_class = panel.get_attribute("class") or ""
    ordinal_class = ordinal.get_attribute("class") or ""
    if "bg-success" in panel_class:
        raise AssertionError(
            "The full choice panel is highlighted; only the ordinal may turn green."
        )
    if "bg-success" not in ordinal_class:
        raise AssertionError("The selected choice ordinal is not visibly highlighted.")
    return {
        "detail_text": detail_text,
        "ordinal_class": ordinal_class,
        "panel_class": panel_class,
    }


def run(argv: Sequence[str] | None = None) -> dict[str, Any]:
    args = _parse_args(argv)
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
        "correction_apply_responses": [],
        "correction_source_state_responses": [],
        "screenshots": [],
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
            "response",
            lambda response: (
                summary["correction_apply_responses"].append(_summarize_response(response))
                if CORRECTION_APPLY_MARKER in response.url
                else summary["correction_source_state_responses"].append(
                    _summarize_response(response)
                )
                if CORRECTION_SOURCE_STATE_MARKER in response.url
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

            page.set_input_files('[data-test="exam-converter-source-file-input"]', str(source_dxe))
            expect(page.locator('[data-test="exam-converter-start-conversion"]')).to_be_enabled(
                timeout=10_000
            )
            page.locator('[data-test="exam-converter-start-conversion"]').click()
            expect(page.locator('[data-test="exam-converter-inspection-surface"]')).to_be_visible(
                timeout=300_000
            )
            page.screenshot(path=str(artifact_dir / "02-review-surface.png"), full_page=True)
            summary["screenshots"].append(str(artifact_dir / "02-review-surface.png"))

            item_id, row_test_id = _find_manual_choice_question(page)
            selected_choice_id = _choose_manual_choice(page)
            summary["manual_choice"] = {
                "item_id": item_id,
                "row_test_id": row_test_id,
                "selected_choice_id": selected_choice_id,
            }

            apply_button = page.locator(
                '[data-test="exam-converter-apply-manual-answer-key-action"]'
            )
            expect(apply_button).to_be_enabled(timeout=10_000)
            with page.expect_response(
                lambda response: (
                    CORRECTION_APPLY_MARKER in response.url and response.request.method == "POST"
                ),
                timeout=120_000,
            ):
                apply_button.click()

            expect(
                page.locator('[data-test="exam-converter-effective-answer-key-summary"]')
            ).to_be_visible(timeout=30_000)
            _leave_and_return(page, item_id)
            summary["persisted_choice_ui"] = _assert_persisted_choice_visible(
                page,
                selected_choice_id,
            )
            page.screenshot(path=str(artifact_dir / "03-persisted-choice.png"), full_page=True)
            summary["screenshots"].append(str(artifact_dir / "03-persisted-choice.png"))
        except Exception:
            page.screenshot(path=str(artifact_dir / "failure.png"), full_page=True)
            (artifact_dir / "failure-main-text.txt").write_text(
                page.locator("main").inner_text(timeout=10_000),
                encoding="utf-8",
            )
            raise
        finally:
            browser.close()

    (artifact_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def main(argv: Sequence[str] | None = None) -> None:
    summary = run(argv)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
