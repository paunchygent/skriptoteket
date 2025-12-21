from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import expect, sync_playwright

from scripts._playwright_config import get_config


def _find_chromium_headless_shell() -> str | None:
    root = Path.home() / "Library" / "Caches" / "ms-playwright"
    if not root.exists():
        return None

    candidates = sorted(root.glob("chromium_headless_shell-*"), reverse=True)
    for candidate in candidates:
        binary = candidate / "chrome-headless-shell-mac-arm64" / "chrome-headless-shell"
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
    base_url = config.base_url
    email = config.email
    password = config.password
    is_local_base_url = base_url.startswith("http://127.0.0.1") or base_url.startswith("http://localhost")

    artifacts_dir = Path(".artifacts/ui-smoke")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    def _assert_help_panel_inset(*, page: object, help_panel: object) -> None:
        box = help_panel.bounding_box()
        viewport = page.viewport_size
        assert viewport is not None, "Expected viewport size to be available"
        assert box is not None, "Expected help panel to have a bounding box"
        assert box["x"] > 0, f"Expected inset help panel x > 0, got {box['x']}"
        assert box["y"] > 0, f"Expected inset help panel y > 0, got {box['y']}"
        assert box["width"] < viewport["width"], (
            f"Expected help panel width < viewport width, got {box['width']} >= {viewport['width']}"
        )
        assert box["height"] < viewport["height"], (
            f"Expected help panel height < viewport height, got {box['height']} >= {viewport['height']}"
        )

    def _open_help_from_mobile_nav(*, page: object) -> object:
        menu_btn = page.get_by_role("button", name="Meny")
        expect(menu_btn).to_be_visible()

        menu_btn.click()
        nav = page.locator("#mobile-nav:not([hidden])")
        expect(nav).to_be_visible()

        help_link = nav.get_by_role("link", name="Hjälp")
        expect(help_link).to_be_visible()
        help_link.click()

        # Help opens and the menu collapses.
        help_panel = page.locator("#help-panel")
        expect(help_panel).to_be_visible()
        expect(page.locator("#mobile-nav")).to_be_hidden()
        expect(menu_btn).to_have_attribute("aria-expanded", "false")
        return help_panel

    with sync_playwright() as playwright:
        device = playwright.devices["iPhone 12"]
        browser = _launch_chromium(playwright)
        context = browser.new_context(**device)
        page = context.new_page()

        # Login
        page.goto(f"{base_url}/login", wait_until="domcontentloaded")

        # Mobile header regression: help is in the menu on small screens.
        help_toggle = page.locator("#help-toggle")
        if help_toggle.count() > 0:
            expect(help_toggle).to_be_hidden()

        # Help panel (logged out): open from the mobile nav.
        if page.locator("#help-panel").count() > 0:
            help_panel = _open_help_from_mobile_nav(page=page)
            _assert_help_panel_inset(page=page, help_panel=help_panel)
            expect(help_panel.get_by_role("heading", name="Logga in")).to_be_visible()
            page.screenshot(path=str(artifacts_dir / "help-logged-out-mobile.png"), full_page=False)

            help_panel.get_by_role("link", name="← Till hjälpindex").click()
            expect(help_panel.get_by_role("heading", name="Hjälpindex")).to_be_visible()
            expect(help_panel.get_by_role("link", name="Logga in")).to_be_visible()
            expect(help_panel.get_by_role("heading", name="Admin")).to_have_count(0)

            page.keyboard.press("Escape")
            expect(help_panel).to_be_hidden()

        page.get_by_label("E-post").fill(email)
        page.get_by_label("Lösenord").fill(password)
        page.get_by_role("button", name="Logga in").click()
        expect(page.get_by_text("Inloggad som")).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "home.png"), full_page=True)

        # Help panel (logged in, role-aware index): open from the mobile nav.
        if page.locator("#help-panel").count() > 0:
            help_panel = _open_help_from_mobile_nav(page=page)
            _assert_help_panel_inset(page=page, help_panel=help_panel)
            expect(help_panel.get_by_role("heading", name="Start")).to_be_visible()
            page.screenshot(path=str(artifacts_dir / "help-logged-in-mobile.png"), full_page=False)

            help_panel.get_by_role("link", name="← Till hjälpindex").click()
            expect(help_panel.get_by_role("heading", name="Admin")).to_be_visible()
            expect(help_panel.get_by_role("link", name="Logga in")).to_have_count(0)

            help_panel.get_by_role("button", name="Stäng").click()
            expect(help_panel).to_be_hidden()

        # Mobile nav logout button styling
        menu_btn = page.get_by_role("button", name="Meny")
        menu_btn.click()
        nav = page.locator("#mobile-nav:not([hidden])")
        expect(nav).to_be_visible()

        logout_btn = nav.get_by_role("button", name="Logga ut")
        bg = logout_btn.evaluate("el => getComputedStyle(el).backgroundColor")
        border_color = logout_btn.evaluate("el => getComputedStyle(el).borderTopColor")
        border_width = logout_btn.evaluate("el => getComputedStyle(el).borderTopWidth")
        assert bg in {"rgba(0, 0, 0, 0)", "transparent"}, f"Unexpected logout bg: {bg}"
        assert border_color == "rgb(28, 46, 74)", f"Unexpected logout border color: {border_color}"
        assert border_width != "0px", f"Unexpected logout border width: {border_width}"

        page.screenshot(path=str(artifacts_dir / "mobile-nav.png"), full_page=True)
        menu_btn.click()

        # Browse professions + categories
        page.goto(f"{base_url}/browse", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name="Välj yrke")).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "browse-professions.png"), full_page=True)

        first_profession = page.locator(".huleedu-list-item a").first
        first_profession.click()
        expect(page.locator("main .huleedu-list").first).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "browse-categories.png"), full_page=True)

        # Admin tools (publish/unpublish button hover determinism on touch)
        page.goto(f"{base_url}/admin/tools", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name="Testyta")).to_be_visible()

        publish_btn = page.locator(
            ".huleedu-tool-actions button:has-text('Publicera'):not([disabled])"
        ).first
        if publish_btn.count() > 0 and is_local_base_url:
            publish_form = publish_btn.locator("xpath=ancestor::form[1]")
            action = publish_form.get_attribute("action") or ""
            tool_id = action.strip("/").split("/")[-2] if "/admin/tools/" in action else ""
            if not tool_id:
                raise RuntimeError(f"Could not determine tool id from action: {action!r}")

            publish_btn.click()

            avpub_btn = page.locator(
                f"form[action='/admin/tools/{tool_id}/depublish'] button:has-text('Avpublicera')"
            ).first
            expect(avpub_btn).to_be_visible()

            bg = avpub_btn.evaluate("el => getComputedStyle(el).backgroundColor")
            fg = avpub_btn.evaluate("el => getComputedStyle(el).color")
            assert bg != "rgb(28, 46, 74)", f"Unexpected filled background on touch: {bg}"
            assert fg == "rgb(28, 46, 74)", f"Unexpected text color on touch: {fg}"

            page.screenshot(
                path=str(artifacts_dir / "admin-tools-after-publish.png"), full_page=True
            )

            avpub_btn.click()
            expect(
                page.locator(
                    f"form[action='/admin/tools/{tool_id}/publish'] button:has-text('Publicera')"
                )
            ).to_be_visible()
            page.screenshot(
                path=str(artifacts_dir / "admin-tools-after-depublish.png"), full_page=True
            )

        context.close()
        browser.close()

        # Desktop hover: CTA stays CTA + amber outline
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        page.goto(f"{base_url}/login", wait_until="domcontentloaded")

        # Help panel (desktop): outside click + escape closes
        help_btn = page.get_by_role("button", name="Hjälp")
        if help_btn.count() > 0:
            help_panel = page.locator("#help-panel")

            help_btn.click()
            expect(help_panel).to_be_visible()
            expect(help_panel.get_by_role("heading", name="Logga in")).to_be_visible()

            page.get_by_role("main").get_by_role("heading", name="Logga in").click()
            expect(help_panel).to_be_hidden()

            help_btn.click()
            expect(help_panel).to_be_visible()
            page.keyboard.press("Escape")
            expect(help_panel).to_be_hidden()

        login_btn = page.get_by_role("button", name="Logga in")
        login_btn.hover()
        page.wait_for_timeout(250)
        hover_shadow = login_btn.evaluate("el => getComputedStyle(el).boxShadow")
        assert "217, 119, 6" in hover_shadow, (
            f"Expected amber outline on hover, got: {hover_shadow}"
        )

        page.get_by_label("E-post").fill(email)
        page.get_by_label("Lösenord").fill(password)
        login_btn.click()
        expect(page.get_by_text("Inloggad som")).to_be_visible()

        catalog_link = page.get_by_role("link", name="Öppna verktygskatalogen")
        catalog_link.hover()
        page.wait_for_timeout(250)
        link_color = catalog_link.evaluate("el => getComputedStyle(el).color")
        link_border = catalog_link.evaluate("el => getComputedStyle(el).borderBottomColor")
        assert "217, 119, 6" in link_color, f"Expected amber link hover, got: {link_color}"
        assert "217, 119, 6" in link_border, f"Expected amber link border hover, got: {link_border}"

        # Help panel collapses when user continues (navigation)
        help_btn = page.get_by_role("button", name="Hjälp")
        if help_btn.count() > 0:
            help_panel = page.locator("#help-panel")
            help_btn.click()
            expect(help_panel).to_be_visible()
            expect(help_panel.get_by_role("heading", name="Start")).to_be_visible()

            catalog_link.click()
            expect(help_panel).to_be_hidden()
        else:
            catalog_link.click()
        expect(page.get_by_role("heading", name="Välj yrke")).to_be_visible()

        first_profession = page.locator(".huleedu-list-item a").first
        first_profession.hover()
        page.wait_for_timeout(250)
        hover_text = first_profession.evaluate("el => getComputedStyle(el).color")
        hover_arrow = first_profession.evaluate("el => getComputedStyle(el, '::after').color")
        assert hover_text != "rgb(217, 119, 6)", f"List text hover too strong: {hover_text}"
        assert hover_arrow == "rgb(107, 28, 46)", (
            f"Expected burgundy arrow hover, got: {hover_arrow}"
        )

        page.goto(f"{base_url}/admin/tools", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name="Testyta")).to_be_visible()

        publish_btn = page.locator(
            ".huleedu-tool-actions button:has-text('Publicera'):not([disabled])"
        ).first
        if publish_btn.count() > 0:
            bg_before = publish_btn.evaluate("el => getComputedStyle(el).backgroundColor")
            publish_btn.hover()
            page.wait_for_timeout(250)
            bg_hover = publish_btn.evaluate("el => getComputedStyle(el).backgroundColor")
            assert bg_before == bg_hover, (
                f"CTA background changed on hover: {bg_before} -> {bg_hover}"
            )

            hover_shadow = publish_btn.evaluate("el => getComputedStyle(el).boxShadow")
            assert "217, 119, 6" in hover_shadow, (
                f"Expected amber outline on hover, got: {hover_shadow}"
            )

        page.screenshot(path=str(artifacts_dir / "admin-tools-desktop.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright UI smoke screenshots written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
