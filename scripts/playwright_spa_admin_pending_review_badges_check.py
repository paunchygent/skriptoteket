from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import expect, sync_playwright

from scripts._playwright_config import get_config


HULEEDU_WARNING_BORDER = "rgb(217, 119, 6)"


def _find_chromium_headless_shell() -> str | None:
    root = Path.home() / "Library" / "Caches" / "ms-playwright"
    if not root.exists():
        return None

    candidates = sorted(root.glob("chromium_headless_shell-*"), reverse=True)
    for candidate in candidates:
        for subdir in [
            "chrome-headless-shell-mac-arm64",
            "chrome-headless-shell-mac-x64",
        ]:
            binary = candidate / subdir / "chrome-headless-shell"
            if binary.is_file():
                return str(binary)

    return None


def _launch_chromium(playwright: object) -> object:
    try:
        return playwright.chromium.launch(headless=True)
    except PlaywrightError as exc:
        executable_path = _find_chromium_headless_shell()
        if not executable_path:
            raise

        message = str(exc)
        if "chromium_headless_shell" not in message and "Executable doesn't exist" not in message:
            raise

        print("Chromium launch failed; retrying with explicit headless shell executable_path.")
        return playwright.chromium.launch(headless=True, executable_path=executable_path)


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/spa-admin-pending-review-badges-check")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Login (SPA)
        page.goto(f"{base_url}/login", wait_until="domcontentloaded")
        page.get_by_label("E-post").fill(email)
        page.get_by_label("Lösenord").fill(password)
        page.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()
        expect(page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE))).to_be_visible()

        # Fetch pending review count from the API (same data source as the dashboard card).
        response = context.request.get(f"{base_url}/api/v1/admin/tools")
        expect(response).to_be_ok()
        payload = response.json()
        tools = payload.get("tools", [])
        api_pending = sum(1 for tool in tools if tool.get("has_pending_review"))

        # Admin tools: count "Granskas" badges across both sections
        page.goto(f"{base_url}/admin/tools", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name=re.compile(r"Verktyg", re.IGNORECASE))).to_be_visible()

        badges_count = page.locator("main span").filter(
            has_text=re.compile(r"granskas", re.IGNORECASE)
        ).count()
        review_ctas = page.locator("main").get_by_role("link", name=re.compile(r"Granska", re.IGNORECASE))
        action_ctas = page.locator("main").get_by_role(
            "link",
            name=re.compile(r"^(Redigera|Granska)$", re.IGNORECASE),
        )
        page.screenshot(path=str(artifacts_dir / "admin-tools.png"), full_page=True)

        (artifacts_dir / "counts.txt").write_text(
            f"api_pending={api_pending}\nadmin_tools_badges={badges_count}\nadmin_tools_review_ctas={review_ctas.count()}\n",
            encoding="utf-8",
        )

        assert badges_count == api_pending, (
            "Mismatch between API pending review count and Admin Tools 'Granskas' badges. "
            f"api_pending={api_pending}, admin_tools_badges={badges_count}."
        )
        expect(review_ctas).to_have_count(api_pending)
        if api_pending > 0:
            bg = review_ctas.first.evaluate("el => getComputedStyle(el).backgroundColor")
            fg = review_ctas.first.evaluate("el => getComputedStyle(el).color")
            assert bg == "rgb(107, 28, 46)", f"Unexpected review CTA bg: {bg}"
            assert fg == "rgb(250, 250, 246)", f"Unexpected review CTA fg: {fg}"

            review_ctas.first.hover()
            expect(review_ctas.first).to_have_css("border-top-color", HULEEDU_WARNING_BORDER)

        # Hover state: any CTA should highlight amber (same as outline buttons).
        if action_ctas.count() > 0:
            action_ctas.first.hover()
            expect(action_ctas.first).to_have_css("border-top-color", HULEEDU_WARNING_BORDER)

        # Outline CTA hover state: subtle canvas fill + amber border (REDIGERA).
        outline_index = action_ctas.evaluate_all(
            "els => els.findIndex(el => getComputedStyle(el).backgroundColor === 'rgb(255, 255, 255)')"
        )
        if outline_index != -1:
            outline_cta = action_ctas.nth(outline_index)
            outline_cta.hover()
            expect(outline_cta).to_have_css("background-color", "rgb(250, 250, 246)")
            expect(outline_cta).to_have_css("border-top-color", HULEEDU_WARNING_BORDER)

        # Ledger alignment: all action CTAs share the same left edge and width.
        cta_lefts = action_ctas.evaluate_all(
            "els => els.map(el => Math.round(el.getBoundingClientRect().left))"
        )
        cta_widths = action_ctas.evaluate_all(
            "els => els.map(el => Math.round(el.getBoundingClientRect().width))"
        )
        if cta_lefts and cta_widths:
            assert max(cta_lefts) - min(cta_lefts) <= 1, (
                "Action CTAs are not aligned to the same column. "
                f"min_left={min(cta_lefts)}, max_left={max(cta_lefts)}"
            )
            assert max(cta_widths) - min(cta_widths) <= 1, (
                "Action CTAs are not equal width. "
                f"min_width={min(cta_widths)}, max_width={max(cta_widths)}"
            )

        # Dev status badges: left edge aligned (Utkast vs Granskas).
        dev_status_badges = page.locator("main span").filter(
            has_text=re.compile(r"^(Utkast|Granskas)$", re.IGNORECASE)
        )
        dev_lefts = dev_status_badges.evaluate_all(
            "els => els.map(el => Math.round(el.getBoundingClientRect().left))"
        )
        if dev_lefts:
            assert max(dev_lefts) - min(dev_lefts) <= 1, (
                "Dev status badges are not aligned to the same column. "
                f"min_left={min(dev_lefts)}, max_left={max(dev_lefts)}"
            )

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
