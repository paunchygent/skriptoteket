"""Playwright copy proof: exam workspace save status states (TASK-SKRIPT-40-04 C1).

Captures `Sparar …`, `Sparat HH:MM`, `Sparat i webbläsaren HH:MM`, `Inte sparat`
with each reason kind, and the saved tooltip, in context for `ui-copy-reviewer`.
Serves this worktree's frontend on a free port (never 5173/5174) and drives it
with Playwright route interception; no backend runs. Signed-in states mock the
HuleEdu session, app continuation, CSRF and exam-workspace endpoints; the guest
state runs the public route with only its bootstrap/blank/courses endpoints
mocked. Every intercepted screenshot is API-mocked, not observed on a server.
Follows `scripts/_playwright_browser.py` and the `python -m scripts.*` convention.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Page, Route, sync_playwright

from scripts._playwright_browser import launch_chromium

REPO_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = Path(
    "/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/"
    "01a1541f-38b9-7a10-a94e-9fd8a0bd1bcc/evidence/copy"
)
LOG_PATH = Path("/tmp/opencode/vite-save-status-copy.log")

LINEAGE_ID = "11111111-1111-4111-8111-111111111111"
BASE_STEP_ID = "22222222-2222-4222-8222-222222222222"
FIRST_STEP_ID = "33333333-3333-4333-8333-333333333333"
CURSOR_ZERO = "44444444-4444-4444-8444-444444444444"

STATUS_SELECTOR = '[data-test="exam-workspace-save-state"]'
TITLE_INPUT_SELECTOR = '[data-test="exam-workspace-metadata-title"]'
TITLE_BUTTON_SELECTOR = '[data-test="exam-workspace-title"]'

GUARD_COPY = (
    "Provet kunde inte sparas. Vänta tills frågorna har konverterats "
    "innan du ändrar, flyttar eller tar bort dem."
)
FAILURE_COPY = "Ändringarna kunde inte sparas. Vi försöker igen automatiskt."
SAVED_TITLE = "Provet i Mina filer har alla ändringar"


def blank_item(sequence: int, *, points: float = 2) -> dict[str, Any]:
    return {
        "ai_suggestion": None,
        "answer_key": {
            "correct_choice_ids": [],
            "match_pairs": [],
            "origin": "absent",
        },
        "body": [
            {
                "heading_level": None,
                "segments": [
                    {
                        "kind": "text",
                        "marks": [],
                        "text": f"Fråga {sequence}: vad heter huvudstaden?",
                    }
                ],
            }
        ],
        "choices": [],
        "criteria": [],
        "facit_text": None,
        "gaps": [],
        "import_record": None,
        "item_id": f"item_{sequence:03d}",
        "kept_gaps": [],
        "kind": "free_text",
        "match_left": [],
        "match_right": [],
        "points": points,
        "points_estimated": False,
        "print_order": [],
        "printed_label": None,
        "retry_source": None,
        "review": {
            "confidence": 0.9,
            "parse_origin": "deterministic",
            "reasons": [],
            "state": "review_complete",
        },
        "sequence": sequence,
        "source_anchor": None,
        "suggested_kind": None,
        "tick_points": None,
        "writing_lines": None,
    }


def blank_document(*, points: float = 2) -> dict[str, Any]:
    return {
        "assets": [],
        "document_id": "00000000-0000-4000-8000-000000000001",
        "header": {"tags": []},
        "instructions": [],
        "items": [blank_item(1, points=points)],
        "origin": {"kind": "manual"},
        "parents": [],
        "revision": 1,
        "schema_version": "native_exam_document_v8",
        "title": "Kopians prov",
    }


def document_response(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "conversion": None,
        "document": document,
        "export_blockers": [],
        "history_cursor": CURSOR_ZERO,
        "notes": [],
        "saved_document": document,
        "summary": {
            "course_key": None,
            "lineage_id": LINEAGE_ID,
            "name": "Kopians prov",
            "saved_at": "2026-10-19T10:00:00+02:00",
            "title": document["title"],
            "vault_file_id": "55555555-5555-4555-8555-555555555555",
            "version": 1,
        },
    }


def history_response() -> dict[str, Any]:
    return {
        "baseline_step_id": BASE_STEP_ID,
        "cursor": CURSOR_ZERO,
        "position_step_id": FIRST_STEP_ID,
        "step_ids": [FIRST_STEP_ID],
    }


def step_response(document: dict[str, Any]) -> dict[str, Any]:
    stored = dict(document)
    stored["revision"] = int(document.get("revision", 1)) + 1
    return {
        "document": stored,
        "export_blockers": [],
        "history": {
            "baseline_step_id": BASE_STEP_ID,
            "cursor": "66666666-6666-4666-8666-666666666666",
            "position_step_id": "77777777-7777-4777-8777-777777777777",
            "step_ids": [FIRST_STEP_ID, "77777777-7777-4777-8777-777777777777"],
        },
    }


def fulfilled(route: Route, payload: Any, *, status: int = 200) -> None:
    route.fulfill(
        status=status,
        content_type="application/json",
        body=json.dumps(payload),
    )


def install_signed_in_routes(page: Page, store_mode: dict[str, Any]) -> None:
    """Mock auth, continuation, CSRF and the exam-workspace endpoints."""

    def handle_session(route: Route) -> None:
        fulfilled(
            route,
            {
                "authenticated": True,
                "context": {},
                "policy": {"feature_flags": [], "grants": [], "roles": ["user"]},
                "profile": {
                    "display_name": "Kopia",
                    "locale": "sv-SE",
                    "person_name": {"first_name": "Kopia"},
                },
                "session": {
                    "csrf_required": True,
                    "expires_at": None,
                    "session_id": "copy-session",
                    "transport": "cookie",
                },
                "user": {
                    "email": "copy@example.se",
                    "email_verified": True,
                    "user_id": "copy-user",
                },
            },
        )

    def handle_continuation(route: Route) -> None:
        fulfilled(
            route,
            {
                "ai_policy": {
                    "completion_external_available": False,
                    "completion_local_available": False,
                    "remote_providers_enabled": False,
                },
                "allow_remote_fallback": None,
                "inline_completion_provider": None,
                "local_user": {
                    "auth_provider": "huleedu",
                    "created_at": "2026-10-19T08:00:00Z",
                    "email": "copy@example.se",
                    "id": "copy-user",
                    "role": "user",
                    "updated_at": "2026-10-19T08:00:00Z",
                },
                "profile": {
                    "created_at": "2026-10-19T08:00:00Z",
                    "updated_at": "2026-10-19T08:00:00Z",
                    "user_id": "copy-user",
                },
            },
        )

    def handle_document(route: Route) -> None:
        fulfilled(route, document_response(store_mode["document"]))

    def handle_history(route: Route) -> None:
        fulfilled(route, history_response())

    def handle_history_step(route: Route) -> None:
        fulfilled(
            route,
            {"document": store_mode["document"], "step_id": FIRST_STEP_ID},
        )

    def handle_autosaves(route: Route) -> None:
        mode = store_mode["mode"]
        if mode == "delay":
            # A long store window so the screenshot lands mid-store.
            time.sleep(10)
            body = json.loads(route.request.post_data or "{}")
            fulfilled(route, step_response(body.get("document", store_mode["document"])))
        elif mode == "fail":
            fulfilled(route, {"error": {"code": "HTTP_ERROR", "message": "boom"}}, status=500)
        elif mode == "guard":
            fulfilled(
                route,
                {
                    "error": {
                        "code": "CONVERSION_IN_PROGRESS",
                        "details": {"item_ids": ["item_001"]},
                        "message": GUARD_COPY,
                    }
                },
                status=422,
            )
        else:
            body = json.loads(route.request.post_data or "{}")
            fulfilled(route, step_response(body.get("document", store_mode["document"])))

    def handle_position(route: Route) -> None:
        body = json.loads(route.request.post_data or "{}")
        _ = body
        fulfilled(route, step_response(store_mode["document"]))

    def handle_courses(route: Route) -> None:
        fulfilled(
            route,
            {
                "courses": [],
                "generated_at": "2026-10-19T00:00:00Z",
                "registered_course_keys": [],
            },
        )

    def handle_list(route: Route) -> None:
        fulfilled(route, {"documents": [], "groups": [], "ordering": "newest"})

    def handle_no_suggestions(route: Route) -> None:
        fulfilled(route, None)

    page.route("**/v1/auth/session", handle_session)
    page.route("**/api/v1/profile/app-continuation", handle_continuation)
    page.route("**/v1/auth/csrf", lambda route: fulfilled(route, {"csrf_token": "mock"}))
    workspace = "**/api/v1/apps/documents.conversion_hub/exam-workspace/**"
    page.route(f"{workspace}/documents/{LINEAGE_ID}/autosaves", handle_autosaves)
    page.route(f"{workspace}/documents/{LINEAGE_ID}/history/position", handle_position)
    page.route(f"{workspace}/documents/{LINEAGE_ID}/history/*", handle_history_step)
    page.route(f"{workspace}/documents/{LINEAGE_ID}/history", handle_history)
    page.route(f"{workspace}/documents/{LINEAGE_ID}/answer-key-suggestions*", handle_no_suggestions)
    page.route(f"{workspace}/documents/{LINEAGE_ID}", handle_document)
    page.route(f"{workspace}/documents", handle_list)
    page.route(f"{workspace}/courses", handle_courses)


def install_guest_routes(page: Page) -> None:
    def handle_blank(route: Route) -> None:
        fulfilled(route, {"document": blank_document(), "export_blockers": []})

    def handle_catalog(route: Route) -> None:
        fulfilled(
            route,
            {
                "courses": [],
                "generated_at": "2026-10-19T00:00:00Z",
                "registered_course_keys": [],
            },
        )

    def handle_bootstrap(route: Route) -> None:
        fulfilled(
            route,
            {
                "app_id": "documents.conversion_hub",
                "host_mode": "public",
                "public_access_profile": "public_browser_workspace_with_upgrade",
                "summary": "Konvertera och redigera prov i webbläsaren.",
                "title": "Provkonverteraren",
                "ui_mode": "bespoke_required",
            },
        )

    public = "**/api/v1/public/apps/documents.conversion_hub/exam-converter/workspace/**"
    page.route("**/api/v1/public/apps/documents.conversion_hub", handle_bootstrap)
    page.route(f"{public}/blank", handle_blank)
    page.route(f"{public}/courses", handle_catalog)


def open_signed_in(page: Page, base_url: str, store_mode: dict[str, Any]) -> None:
    install_signed_in_routes(page, store_mode)
    page.goto(f"{base_url}/apps/exam-workspace?document={LINEAGE_ID}")
    page.wait_for_selector(STATUS_SELECTOR, timeout=30000)
    page.wait_for_timeout(2500)


def type_title(page: Page, suffix: str) -> None:
    page.click(TITLE_BUTTON_SELECTOR)
    page.wait_for_selector(TITLE_INPUT_SELECTOR, timeout=15000)
    page.locator(TITLE_INPUT_SELECTOR).click()
    page.keyboard.press("End")
    page.keyboard.type(" x", delay=50)
    page.locator(STATUS_SELECTOR).click()
    page.wait_for_timeout(500)


def read_status(page: Page) -> tuple[str, str | None]:
    status = page.locator(STATUS_SELECTOR)
    return status.inner_text().strip(), status.get_attribute("title")


def hover_shot(page: Page, name: str) -> Path:
    page.locator(STATUS_SELECTOR).hover()
    page.wait_for_timeout(400)
    path = EVIDENCE_DIR / f"{name}.png"
    page.screenshot(path=path)
    return path


def report(name: str, text: str, title: str | None, path: Path) -> None:
    size = path.stat().st_size
    print(f"{name}: text={text!r} title={title!r} file={path.name} bytes={size}")


def scenario_guest_saved(browser: Browser, base_url: str) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    install_guest_routes(page)
    page.goto(f"{base_url}/public/apps/documents.conversion_hub")
    page.get_by_test_id("exam-workspace-guest-blank").click(timeout=30000)
    page.get_by_text("Sparat i webbläsaren", exact=False).wait_for(timeout=30000)
    page.click(TITLE_BUTTON_SELECTOR)
    page.wait_for_selector(TITLE_INPUT_SELECTOR, timeout=15000)
    page.fill(TITLE_INPUT_SELECTOR, "Kopians prov gäst")
    page.locator(STATUS_SELECTOR).click()
    page.get_by_text("Sparat i webbläsaren ", exact=False).wait_for(timeout=30000)
    page.wait_for_timeout(1000)
    text, title = read_status(page)
    path = EVIDENCE_DIR / "guest-saved.png"
    page.screenshot(path=path)
    report("guest-saved", text, title, path)
    context.close()


def scenario_saving(browser: Browser, base_url: str) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    open_signed_in(page, base_url, {"document": blank_document(), "mode": "delay"})
    type_title(page, "sparar")
    page.get_by_text("Sparar …", exact=True).wait_for(timeout=15000)
    path = EVIDENCE_DIR / "saving.png"
    page.screenshot(path=path)
    # The artifact is only valid mid-store; confirm the state held for the shot.
    text, title = read_status(page)
    if text != "Sparar …":
        raise RuntimeError(f"saving screenshot missed the window: {text!r}")
    report("saving", text, title, path)
    page.get_by_text("Sparat", exact=False).first.wait_for(timeout=30000)
    text, title = read_status(page)
    path = EVIDENCE_DIR / "saved.png"
    page.screenshot(path=path)
    report("saved", text, title, path)
    tooltip_path = hover_shot(page, "saved-tooltip")
    report("saved-tooltip", text, title, tooltip_path)
    context.close()


def scenario_failure(browser: Browser, base_url: str) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    open_signed_in(page, base_url, {"document": blank_document(), "mode": "fail"})
    type_title(page, "fel")
    page.get_by_text("Inte sparat", exact=True).wait_for(timeout=30000)
    text, title = read_status(page)
    path = hover_shot(page, "unsaved-failure")
    report("unsaved-failure", text, title, path)
    context.close()


def scenario_rule(browser: Browser, base_url: str) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    open_signed_in(page, base_url, {"document": blank_document(points=-1), "mode": "ok"})
    type_title(page, "regel")
    page.get_by_text("Inte sparat", exact=True).wait_for(timeout=30000)
    text, title = read_status(page)
    path = hover_shot(page, "unsaved-rule")
    report("unsaved-rule", text, title, path)
    context.close()


def scenario_guard(browser: Browser, base_url: str) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    open_signed_in(page, base_url, {"document": blank_document(), "mode": "guard"})
    type_title(page, "skydd")
    page.get_by_text("Inte sparat", exact=True).wait_for(timeout=30000)
    text, title = read_status(page)
    path = hover_shot(page, "unsaved-guard")
    report("unsaved-guard", text, title, path)
    context.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vite-port", type=int, default=5179)
    parser.add_argument(
        "--scenarios",
        default="guest,saving,failure,rule,guard",
        help="Comma-separated subset of guest,saving,failure,rule,guard",
    )
    return parser.parse_args()


def launch(browser_factory: Any) -> Browser:
    try:
        return launch_chromium(browser_factory)
    except Exception as exc:
        message = str(exc)
        if "Executable doesn't exist" not in message and "chromium" not in message.lower():
            raise
        chrome = "/usr/bin/google-chrome"
        print("Falling back to system Chrome at /usr/bin/google-chrome.")
        return browser_factory.chromium.launch(headless=True, executable_path=chrome)


def main() -> None:
    args = parse_args()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    base_url = f"http://127.0.0.1:{args.vite_port}"
    selected = {name.strip() for name in args.scenarios.split(",")}
    with sync_playwright() as playwright:
        playwright.selectors.set_test_id_attribute("data-test")
        browser = launch(playwright)
        try:
            if "guest" in selected:
                scenario_guest_saved(browser, base_url)
            if "saving" in selected:
                scenario_saving(browser, base_url)
            if "failure" in selected:
                scenario_failure(browser, base_url)
            if "rule" in selected:
                scenario_rule(browser, base_url)
            if "guard" in selected:
                scenario_guard(browser, base_url)
        finally:
            browser.close()
    print("done")


if __name__ == "__main__":
    main()
