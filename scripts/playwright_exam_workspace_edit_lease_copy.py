"""Playwright copy proof: exam workspace one-editing-tab lease (TASK-SKRIPT-40-04 C3).

Captures the `Öppet i en annan flik` notice with the `Ta över` action in
context for `ui-copy-reviewer`: a signed-in tab that does not hold the lease,
the same tab right after `Ta över` (now editing), the tab that lost the lease
after the takeover, the waiting state (action disabled), and the guest notice.
Serves this worktree's frontend on a free port (never 5173/5174) and drives it
with Playwright route interception; no backend runs. The signed-in lease is a
shared in-test fake behind the mocked `.../edit-lease/*` routes, shaped like
the generated `ExamWorkspaceEditLeaseResponse` types; the guest lease is the
real IndexedDB record shared by two pages in one browser context. Every
screenshot is API-mocked, not observed against a server. Reuses the C1 route
and launch helpers by import instead of copying them. Follows
`scripts/_playwright_browser.py` and the `python -m scripts.*` convention.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Page, Route, sync_playwright

from scripts.playwright_exam_workspace_save_status_copy import (
    EVIDENCE_DIR,
    LINEAGE_ID,
    STATUS_SELECTOR,
    blank_document,
    fulfilled,
    install_guest_routes,
    install_signed_in_routes,
    launch,
)

NOTICE_SELECTOR = '[data-test="exam-workspace-edit-lease"]'
NOTICE_TEXT_SELECTOR = '[data-test="exam-workspace-edit-lease-text"]'
TAKEOVER_SELECTOR = '[data-test="exam-workspace-edit-lease-takeover"]'
ITEM_EDITOR_SELECTOR = '[data-test="exam-workspace-item-editor"]'

LEASE_HELD_COPY = "Provet redigeras i en annan flik."
RENEWED_AT = "2026-10-19T12:00:00+02:00"


def lease_response(holder: str | None, *, waiting: str | None = None) -> dict[str, Any]:
    return {
        "holder_tab_id": holder,
        "renewed_at": RENEWED_AT,
        "takeover_requested": waiting is not None,
        "takeover_requested_by": waiting,
    }


def lease_refused(route: Route) -> None:
    fulfilled(
        route,
        {"error": {"code": "EDIT_LEASE_HELD", "message": LEASE_HELD_COPY}},
        status=409,
    )


def install_lease_routes(page: Page, lease: dict[str, Any]) -> None:
    """One shared fake lease behind the four mocked `edit-lease` operations."""

    def handle_lease(route: Route) -> None:
        operation = route.request.url.rsplit("/edit-lease/", 1)[-1]
        body = json.loads(route.request.post_data or "{}")
        tab_id = body.get("tab_id")
        holder = lease["holder"]
        waiting = lease["waiting"]
        if operation == "claim":
            if holder in (None, tab_id):
                lease["holder"] = tab_id
                if waiting == tab_id:
                    lease["waiting"] = None
                fulfilled(route, lease_response(tab_id))
            else:
                lease_refused(route)
        elif operation == "renew":
            if holder == tab_id:
                other = waiting if waiting != tab_id else None
                fulfilled(route, lease_response(tab_id, waiting=other))
            else:
                lease_refused(route)
        elif operation == "takeover":
            if holder in (None, tab_id):
                lease["holder"] = tab_id
                if waiting == tab_id:
                    lease["waiting"] = None
                fulfilled(route, lease_response(tab_id))
            else:
                lease["waiting"] = tab_id
                fulfilled(route, lease_response(holder))
        elif operation == "release":
            if holder == tab_id:
                lease["holder"] = None
            fulfilled(route, lease_response(None))
        else:
            raise RuntimeError(f"unknown lease operation: {operation}")

    workspace = "**/api/v1/apps/documents.conversion_hub/exam-workspace/**"
    page.route(f"{workspace}/documents/{LINEAGE_ID}/edit-lease/*", handle_lease)


def open_lease_page(page: Page, base_url: str, lease: dict[str, Any]) -> None:
    install_signed_in_routes(page, {"document": blank_document(), "mode": "ok"})
    install_lease_routes(page, lease)
    page.goto(f"{base_url}/apps/exam-workspace?document={LINEAGE_ID}")
    page.wait_for_selector(STATUS_SELECTOR, timeout=30000)
    page.wait_for_selector(ITEM_EDITOR_SELECTOR, timeout=30000)
    page.wait_for_timeout(2500)


def report(name: str, detail: str, path: Path) -> None:
    size = path.stat().st_size
    print(f"{name}: {detail} file={path.name} bytes={size}")


def read_notice(page: Page) -> tuple[str, str, str | None]:
    notice = page.locator(NOTICE_SELECTOR)
    text = notice.locator(NOTICE_TEXT_SELECTOR).inner_text().strip()
    action = notice.locator(TAKEOVER_SELECTOR)
    return text, action.inner_text().strip(), action.get_attribute("disabled")


def scenario_signed_in(browser: Browser, base_url: str) -> None:
    lease: dict[str, Any] = {"holder": None, "waiting": None}
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    first = context.new_page()
    open_lease_page(first, base_url, lease)
    if first.locator(NOTICE_SELECTOR).count() != 0:
        raise RuntimeError("holder tab shows the lease notice")
    second = context.new_page()
    open_lease_page(second, base_url, lease)
    notice = second.locator(NOTICE_SELECTOR)
    notice.wait_for(timeout=30000)
    path = EVIDENCE_DIR / "lease-notice-signed-in.png"
    second.screenshot(path=path)
    text, action, disabled = read_notice(second)
    status = second.locator(STATUS_SELECTOR).inner_text().strip()
    report(
        "lease-notice-signed-in",
        f"notice={text!r} action={action!r} disabled={disabled!r} status={status!r}",
        path,
    )
    second.locator(TAKEOVER_SELECTOR).click()
    waiting_path = EVIDENCE_DIR / "lease-takeover-waiting.png"
    second.screenshot(path=waiting_path)
    _, waiting_action, waiting_disabled = read_notice(second)
    report(
        "lease-takeover-waiting",
        f"action={waiting_action!r} disabled={waiting_disabled!r}",
        waiting_path,
    )
    if waiting_disabled is None:
        raise RuntimeError("takeover did not enter the waiting state")
    notice.wait_for(state="detached", timeout=30000)
    second.wait_for_timeout(1500)
    if second.locator(NOTICE_SELECTOR).count() != 0:
        raise RuntimeError("takeover tab still shows the lease notice")
    path = EVIDENCE_DIR / "lease-after-takeover.png"
    second.screenshot(path=path)
    status = second.locator(STATUS_SELECTOR).inner_text().strip()
    report("lease-after-takeover", f"notice gone, status={status!r}", path)
    loser = first.locator(NOTICE_SELECTOR)
    loser.wait_for(timeout=30000)
    path = EVIDENCE_DIR / "lease-loser.png"
    first.screenshot(path=path)
    text, action, disabled = read_notice(first)
    report(
        "lease-loser",
        f"notice={text!r} action={action!r} disabled={disabled!r}",
        path,
    )
    context.close()


def scenario_guest(browser: Browser, base_url: str) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    first = context.new_page()
    install_guest_routes(first)
    first.goto(f"{base_url}/public/apps/documents.conversion_hub")
    first.get_by_test_id("exam-workspace-guest-blank").click(timeout=30000)
    first.get_by_text("Sparat i webbläsaren", exact=False).wait_for(timeout=30000)
    first.wait_for_timeout(3000)
    if first.locator(NOTICE_SELECTOR).count() != 0:
        raise RuntimeError("guest holder tab shows the lease notice")
    second = context.new_page()
    install_guest_routes(second)
    second.goto(f"{base_url}/public/apps/documents.conversion_hub")
    second.get_by_test_id("exam-workspace-guest-blank").click(timeout=30000)
    notice = second.locator(NOTICE_SELECTOR)
    notice.wait_for(timeout=30000)
    path = EVIDENCE_DIR / "lease-guest.png"
    second.screenshot(path=path)
    text, action, disabled = read_notice(second)
    report(
        "lease-guest",
        f"notice={text!r} action={action!r} disabled={disabled!r}",
        path,
    )
    if first.locator(NOTICE_SELECTOR).count() != 0:
        raise RuntimeError("guest holder lost the lease to the second tab")
    context.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vite-port", type=int, default=5185)
    parser.add_argument(
        "--scenarios",
        default="signed-in,guest",
        help="Comma-separated subset of signed-in,guest",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    base_url = f"http://127.0.0.1:{args.vite_port}"
    selected = {name.strip() for name in args.scenarios.split(",")}
    with sync_playwright() as playwright:
        playwright.selectors.set_test_id_attribute("data-test")
        browser = launch(playwright)
        try:
            if "signed-in" in selected:
                scenario_signed_in(browser, base_url)
            if "guest" in selected:
                scenario_guest(browser, base_url)
        finally:
            browser.close()
    print("done")


if __name__ == "__main__":
    main()
