from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def _read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _get_config_value(*, key: str, dotenv: dict[str, str]) -> str | None:
    return os.environ.get(key) or dotenv.get(key)


def main() -> None:
    dotenv = _read_dotenv(Path(".env"))

    base_url = _get_config_value(key="BASE_URL", dotenv=dotenv) or "http://127.0.0.1:8000"
    email = _get_config_value(key="BOOTSTRAP_SUPERUSER_EMAIL", dotenv=dotenv)
    password = _get_config_value(key="BOOTSTRAP_SUPERUSER_PASSWORD", dotenv=dotenv)

    if not email or not password:
        raise SystemExit(
            "Missing BOOTSTRAP_SUPERUSER_EMAIL/BOOTSTRAP_SUPERUSER_PASSWORD. "
            "Set them in .env (gitignored) or export them in your shell."
        )

    artifacts_dir = Path(".artifacts/ui-smoke")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        device = playwright.devices["iPhone 12"]
        browser = playwright.webkit.launch(headless=True)
        context = browser.new_context(**device)
        page = context.new_page()

        # Login
        page.goto(f"{base_url}/login", wait_until="domcontentloaded")
        page.get_by_label("E-post").fill(email)
        page.get_by_label("Lösenord").fill(password)
        page.get_by_role("button", name="Logga in").click()
        expect(page.get_by_text("Inloggad som")).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "home.png"), full_page=True)

        # Browse professions + categories
        page.goto(f"{base_url}/browse", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name="Välj yrke")).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "browse-professions.png"), full_page=True)

        first_profession = page.locator(".huleedu-list-item a").first
        first_profession.click()
        expect(page.locator(".huleedu-list")).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "browse-categories.png"), full_page=True)

        # Admin tools (publish/unpublish button hover determinism on touch)
        page.goto(f"{base_url}/admin/tools", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name="Testyta")).to_be_visible()

        publish_btn = page.locator(
            ".huleedu-tool-actions button:has-text('Publicera'):not([disabled])"
        ).first
        if publish_btn.count() > 0:
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
            avpub_btn.scroll_into_view_if_needed()

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

    print(f"Playwright UI smoke screenshots written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
