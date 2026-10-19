"""Playwright copy proof: exam workspace part 4 (TASK-SKRIPT-40-04 C4).

Captures the A1, A2, A4 and D1o texts in context for `ui-copy-reviewer`:
the outdated-format and blocked-click toasts in Öppna, the Tom lucka
button enabled and at the cap, a just-inserted empty gap with its popover,
the export drawer blockers, and the key guidance. No backend runs; every
screenshot is API-mocked. Reuses the C1 helpers by import. Follows
`scripts/_playwright_browser.py` and `python -m scripts.*`.
"""

from __future__ import annotations

import argparse
import json
from contextlib import contextmanager
from typing import Any, Iterator

from playwright.sync_api import Browser, Page, Route, sync_playwright

from scripts.playwright_exam_workspace_gap_copy import dropdown_gap
from scripts.playwright_exam_workspace_save_status_copy import (
    EVIDENCE_DIR,
    LINEAGE_ID,
    STATUS_SELECTOR,
    TITLE_BUTTON_SELECTOR,
    blank_document,
    blank_item,
    fulfilled,
    install_signed_in_routes,
    launch,
)

OLD_LINEAGE_ID = "99999999-9999-4999-8999-999999999999"
OTHER_LINEAGE_ID = "88888888-8888-4888-8888-888888888888"

OUTDATED_COPY = "Provet är sparat i ett äldre format och kan inte öppnas."
BLOCKED_COPY = "Vänta tills ändringarna har sparats."
EMPTY_GAP_LABEL = "Tom lucka"
EMPTY_GAP_CAP_REASON = "Tom lucka – högst 999 luckor"
PARTIAL_GAP_GUIDANCE = "Fyll i godkända svar i varje lucka."

ITEM_EDITOR_SELECTOR = '[data-test="exam-workspace-item-editor"]'
EMPTY_GAP_BUTTON_SELECTOR = '[data-test="exam-workspace-toolbar-empty-gap"]'
GAP_POPOVER_SELECTOR = '[data-test="exam-workspace-gap-popover"]'
OPEN_BUTTON_SELECTOR = '[data-test="exam-workspace-open"]'
OPEN_DRAWER_SELECTOR = '[data-test="exam-workspace-drawer-open"]'
EXPORT_BUTTON_SELECTOR = '[data-test="exam-workspace-export"]'
EXPORT_MORE_SELECTOR = '[data-test="exam-workspace-export-more"]'
EXPORT_DRAWER_BLOCKERS_SELECTOR = '[data-test="exam-workspace-export-drawer-blockers"]'
GAP_KEY_HINT_SELECTOR = '[data-test="exam-workspace-gap-key-hint"]'
TITLE_EDIT_SELECTOR = '[data-test="exam-workspace-title-input"]'

KEYED_ORIGIN = "teacher_authored"


def text_run(text: str) -> dict[str, Any]:
    return {"kind": "text", "marks": [], "text": text, "kept_gap_id": None}


def answered_gap(gap_id: str, values: list[str]) -> dict[str, Any]:
    return {
        "accepted_values": values,
        "automatic_values": [],
        "correct_option_id": None,
        "excluded_automatic_values": [],
        "gap_id": gap_id,
        "options": [],
    }


def keyed_gap_fill_item(
    seq: int, gaps: list[dict[str, Any]], segments: list[dict[str, Any]]
) -> dict[str, Any]:
    item = blank_item(seq)
    item.update(
        {
            "kind": "gap_fill",
            "answer_key": {
                "correct_choice_ids": [],
                "match_pairs": [],
                "origin": KEYED_ORIGIN,
            },
            "body": [{"heading_level": None, "segments": segments}],
            "gaps": gaps,
        }
    )
    return item


def dropdown_no_correct_item(seq: int) -> dict[str, Any]:
    item = blank_item(seq)
    item.update(
        {
            "kind": "inline_choice",
            "answer_key": {
                "correct_choice_ids": [],
                "match_pairs": [],
                "origin": KEYED_ORIGIN,
            },
            "body": [
                {
                    "heading_level": None,
                    "segments": [
                        text_run("Välj rätt ord: "),
                        {"kind": "gap", "gap_id": "gap_001"},
                        text_run("."),
                    ],
                }
            ],
            "gaps": [dropdown_gap("gap_001", ["R", "A", "B"], None)],
        }
    )
    return item


def summary_for(lineage_id: str, title: str) -> dict[str, Any]:
    return {
        "course_key": None,
        "lineage_id": lineage_id,
        "name": f"{title}.provdokument.zip",
        "saved_at": "2026-10-19T10:00:00+02:00",
        "title": title,
        "vault_file_id": f"file-{lineage_id[:8]}",
        "version": 1,
    }


def document_payload(document: dict[str, Any], lineage_id: str) -> dict[str, Any]:
    return {
        "conversion": None,
        "document": document,
        "export_blockers": [],
        "history_cursor": "44444444-4444-4444-8444-444444444444",
        "notes": [],
        "saved_document": document,
        "summary": summary_for(lineage_id, document["title"]),
    }


def install_part4_routes(page: Page, documents: dict[str, dict[str, Any] | None]) -> None:
    """C1 routes plus per-lineage documents; None means an outdated-format refusal."""
    current = next(document for document in documents.values() if document is not None)
    install_signed_in_routes(page, {"document": current, "mode": "ok"})

    def handle_document(route: Route) -> None:
        lineage_id = route.request.url.rsplit("/documents/", 1)[-1].split("?", 1)[0]
        document = documents.get(lineage_id)
        if document is None:
            fulfilled(
                route,
                {"error": {"code": "DOCUMENT_SCHEMA_OUTDATED", "message": "outdated"}},
                status=422,
            )
            return
        fulfilled(route, document_payload(document, lineage_id))

    def handle_autosaves(route: Route) -> None:
        body = json.loads(route.request.post_data or "{}")
        stored = dict(body.get("document") or blank_document())
        stored["revision"] = int(stored.get("revision", 1)) + 1
        fulfilled(
            route,
            {
                "document": stored,
                "export_blockers": [],
                "history": {
                    "baseline_step_id": "22222222-2222-4222-8222-222222222222",
                    "cursor": "66666666-6666-4666-8666-666666666666",
                    "position_step_id": "77777777-7777-4777-8777-777777777777",
                    "step_ids": [
                        "33333333-3333-4333-8333-333333333333",
                        "77777777-7777-4777-8777-777777777777",
                    ],
                },
            },
        )

    def handle_history(route: Route) -> None:
        fulfilled(
            route,
            {
                "baseline_step_id": "22222222-2222-4222-8222-222222222222",
                "cursor": "44444444-4444-4444-8444-444444444444",
                "position_step_id": "33333333-3333-4333-8333-333333333333",
                "step_ids": ["33333333-3333-4333-8333-333333333333"],
            },
        )

    def handle_history_step(route: Route) -> None:
        lineage_id = route.request.url.rsplit("/documents/", 1)[-1].split("/history/", 1)[0]
        fulfilled(
            route,
            {
                "document": documents.get(lineage_id) or blank_document(),
                "step_id": "33333333-3333-4333-8333-333333333333",
            },
        )

    def handle_position(route: Route) -> None:
        body = json.loads(route.request.post_data or "{}")
        fulfilled(
            route,
            {
                "document": body.get("document") or blank_document(),
                "export_blockers": [],
                "history": {},
            },
        )

    def handle_list(route: Route) -> None:
        fulfilled(
            route,
            {
                "documents": [
                    summary_for(
                        lineage_id, document["title"] if document is not None else "Gammalt prov"
                    )
                    for lineage_id, document in documents.items()
                ],
                "groups": [],
                "ordering": "newest",
            },
        )

    def handle_lease(route: Route) -> None:
        body = json.loads(route.request.post_data or "{}")
        fulfilled(
            route,
            {
                "holder_tab_id": body.get("tab_id"),
                "renewed_at": "2026-10-19T12:00:00+02:00",
                "takeover_requested": False,
                "takeover_requested_by": None,
            },
        )

    def handle_no_suggestions(route: Route) -> None:
        fulfilled(route, None)

    # Registered last, so these win over the C1 routes for the same URLs.
    workspace = "**/api/v1/apps/documents.conversion_hub/exam-workspace/**"
    page.route(f"{workspace}/documents/*/edit-lease/*", handle_lease)
    page.route(f"{workspace}/documents/*/autosaves", handle_autosaves)
    page.route(f"{workspace}/documents/*/history/position", handle_position)
    page.route(f"{workspace}/documents/*/history/*", handle_history_step)
    page.route(f"{workspace}/documents/*/history", handle_history)
    page.route(f"{workspace}/documents/*/answer-key-suggestions*", handle_no_suggestions)
    page.route(f"{workspace}/documents/*", handle_document)
    page.route(f"{workspace}/documents", handle_list)


def open_open_drawer(page: Page) -> None:
    """Open Öppna via the header; the first toggle after load is ignored, so retry."""
    for _ in range(3):
        page.locator(OPEN_BUTTON_SELECTOR).click()
        page.wait_for_timeout(800)
        if page.locator(OPEN_DRAWER_SELECTOR).count() > 0:
            return
    raise RuntimeError("the Öppna drawer never opened")


def open_part4(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/apps/exam-workspace?document={LINEAGE_ID}")
    for selector in (STATUS_SELECTOR, ITEM_EDITOR_SELECTOR):
        page.wait_for_selector(selector, timeout=30000)
    page.wait_for_timeout(2500)
    # Öppna stands open from mount until the teacher acts; close it for a settled start.
    if page.locator(OPEN_DRAWER_SELECTOR).count() > 0:
        page.locator('[data-test="exam-workspace-drawer-close"]').click()
        page.wait_for_selector(OPEN_DRAWER_SELECTOR, state="detached", timeout=30000)


def shot(page: Page, name: str, detail: str) -> None:
    path = EVIDENCE_DIR / f"{name}.png"
    page.screenshot(path=path)
    print(f"{name}: {detail} file={path.name} bytes={path.stat().st_size}")


@contextmanager
def fresh_page(
    browser: Browser, base_url: str, documents: dict[str, dict[str, Any] | None]
) -> Iterator[Page]:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    install_part4_routes(page, documents)
    open_part4(page, base_url)
    try:
        yield page
    finally:
        context.close()


def scenario_outdated(browser: Browser, base_url: str) -> None:
    docs = {LINEAGE_ID: blank_document(), OLD_LINEAGE_ID: None}
    with fresh_page(browser, base_url, docs) as page:
        open_open_drawer(page)
        page.get_by_test_id(f"exam-workspace-open-{OLD_LINEAGE_ID}").click()
        page.get_by_text(OUTDATED_COPY, exact=True).wait_for(timeout=30000)
        shot(page, "part4-outdated-toast", f"toast={OUTDATED_COPY!r}")


def type_title_draft(page: Page) -> None:
    """Type a rename without committing; the entry click's blur commits it first.

    C1's drawer-based helper is stale here (the 40-04-17 inline edit uses
    `exam-workspace-title-input`), and committing only on blur keeps the
    blocked click inside the debounce window with no sleeping mock.
    """
    page.locator(TITLE_BUTTON_SELECTOR).click()
    editor = page.locator(TITLE_EDIT_SELECTOR)
    editor.wait_for(timeout=15000)
    editor.click()
    page.keyboard.press("End")
    page.keyboard.type(" x", delay=50)


def scenario_blocked(browser: Browser, base_url: str) -> None:
    other = blank_document()
    other["title"] = "Andra provet"
    docs = {LINEAGE_ID: blank_document(), OTHER_LINEAGE_ID: other}
    with fresh_page(browser, base_url, docs) as page:
        open_open_drawer(page)
        type_title_draft(page)
        page.get_by_test_id(f"exam-workspace-open-{OTHER_LINEAGE_ID}").click()
        page.get_by_text(BLOCKED_COPY, exact=True).wait_for(timeout=30000)
        shot(page, "part4-blocked-toast", f"toast={BLOCKED_COPY!r}")


def capture_button(
    browser: Browser,
    base_url: str,
    document: dict[str, Any],
    name: str,
    expect_title: str,
    expect_disabled: bool,
) -> None:
    with fresh_page(browser, base_url, {LINEAGE_ID: document}) as page:
        button = page.locator(f"{ITEM_EDITOR_SELECTOR} {EMPTY_GAP_BUTTON_SELECTOR}").first
        button.wait_for(timeout=30000)
        button.hover()
        page.wait_for_timeout(400)
        title = button.get_attribute("title")
        disabled = button.get_attribute("disabled")
        if title != expect_title or (disabled is None) == expect_disabled:
            raise RuntimeError(f"unexpected Tom lucka: title={title!r} disabled={disabled!r}")
        detail = f"title={title!r} aria-label={button.get_attribute('aria-label')!r} disabled={disabled!r}"
        shot(page, name, detail)


def single_gap_doc(gap_id: str, values: list[str]) -> dict[str, Any]:
    document = blank_document()
    document["items"] = [
        keyed_gap_fill_item(
            1,
            [answered_gap(gap_id, values)],
            [
                text_run("Huvudstaden heter "),
                {"kind": "gap", "gap_id": gap_id},
                text_run("."),
            ],
        )
    ]
    return document


def scenario_buttons(browser: Browser, base_url: str) -> None:
    capture_button(
        browser,
        base_url,
        single_gap_doc("gap_001", ["Stockholm"]),
        "part4-empty-gap-enabled",
        EMPTY_GAP_LABEL,
        False,
    )
    capture_button(
        browser,
        base_url,
        single_gap_doc("gap_999", ["Slott"]),
        "part4-empty-gap-disabled",
        EMPTY_GAP_CAP_REASON,
        True,
    )


def scenario_popover(browser: Browser, base_url: str) -> None:
    document = blank_document()
    document["items"] = [
        keyed_gap_fill_item(1, [], [text_run("Solen är en stjärna som lyser starkt.")])
    ]
    with fresh_page(browser, base_url, {LINEAGE_ID: document}) as page:
        page.locator(f"{ITEM_EDITOR_SELECTOR} .tiptap").first.click()
        page.wait_for_timeout(400)
        page.locator(f"{ITEM_EDITOR_SELECTOR} {EMPTY_GAP_BUTTON_SELECTOR}").first.click()
        page.wait_for_selector(GAP_POPOVER_SELECTOR, timeout=30000)
        page.wait_for_timeout(400)
        shot(page, "part4-empty-gap-popover", "empty gap inserted, popover open")


def export_blocker_document() -> dict[str, Any]:
    document = single_gap_doc("gap_001", [])
    document["items"].append(dropdown_no_correct_item(2))
    return document


def scenario_export(browser: Browser, base_url: str) -> None:
    with fresh_page(browser, base_url, {LINEAGE_ID: export_blocker_document()}) as page:
        page.locator(EXPORT_BUTTON_SELECTOR).click()
        page.get_by_text("Fråga 1: lucka utan svar", exact=False).first.wait_for(timeout=30000)
        page.get_by_text("Fråga 2: rullista utan rätt svar", exact=False).first.wait_for(
            timeout=30000
        )
        page.locator(EXPORT_MORE_SELECTOR).click()
        page.wait_for_selector(EXPORT_DRAWER_BLOCKERS_SELECTOR, timeout=30000)
        page.wait_for_timeout(400)
        shot(
            page,
            "part4-export-blocker",
            "rows Fråga 1: lucka utan svar + Fråga 2: rullista utan rätt svar",
        )


def scenario_guidance(browser: Browser, base_url: str) -> None:
    with fresh_page(browser, base_url, {LINEAGE_ID: single_gap_doc("gap_001", [])}) as page:
        hint = page.locator(GAP_KEY_HINT_SELECTOR)
        hint.wait_for(timeout=30000)
        text = hint.inner_text().strip()
        if text != PARTIAL_GAP_GUIDANCE:
            raise RuntimeError(f"unexpected guidance: {text!r}")
        hint.scroll_into_view_if_needed()
        page.wait_for_timeout(400)
        shot(page, "part4-guidance", f"hint={text!r}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vite-port", type=int, default=5187)
    parser.add_argument(
        "--scenarios",
        default="outdated,blocked,buttons,popover,export,guidance",
        help="Comma-separated subset of outdated,blocked,buttons,popover,export,guidance",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    base_url = f"http://127.0.0.1:{args.vite_port}"
    selected = {name.strip() for name in args.scenarios.split(",")}
    runners = {
        "outdated": scenario_outdated,
        "blocked": scenario_blocked,
        "buttons": scenario_buttons,
        "popover": scenario_popover,
        "export": scenario_export,
        "guidance": scenario_guidance,
    }
    with sync_playwright() as playwright:
        playwright.selectors.set_test_id_attribute("data-test")
        browser = launch(playwright)
        try:
            for name in runners:
                if name in selected:
                    runners[name](browser, base_url)
        finally:
            browser.close()
    print("done")


if __name__ == "__main__":
    main()
