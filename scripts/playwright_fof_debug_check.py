import re

from playwright.sync_api import Page, expect, sync_playwright

from scripts._playwright_config import get_config

APP_PATH = "/apps/games.flunk_out_frenzy"


def wait_for_shell_ready(page: Page) -> None:
    """Wait for either a ready shell or a visible bootstrap error."""
    ready_state = page.locator('[data-test="bootstrap-ready"]')
    error_state = page.locator('[data-test="bootstrap-error"]')

    for _ in range(60):
        if ready_state.count() > 0 and ready_state.first.is_visible():
            return
        if error_state.count() > 0 and error_state.first.is_visible():
            raise AssertionError(
                f"Flunk-Out Frenzy bootstrap failed: {error_state.first.inner_text()}"
            )
        page.wait_for_timeout(500)

    raise AssertionError("Flunk-Out Frenzy did not reach a bootstrap-ready state.")


def login_to_flunk_out_frenzy(page: Page, *, base_url: str, email: str, password: str) -> None:
    """Log in through the protected game route and wait for the shell to load."""
    for attempt in range(3):
        page.goto(f"{base_url}{APP_PATH}", wait_until="domcontentloaded")
        try:
            wait_for_shell_ready(page)
            expect(page).to_have_url(re.compile(re.escape(APP_PATH) + r"$"))
            return
        except AssertionError:
            login_dialog = page.get_by_role("dialog", name=re.compile(r"Logga in", re.IGNORECASE))
            if login_dialog.count() > 0:
                expect(login_dialog).to_be_visible()
                login_dialog.get_by_label("E-post").fill(email)
                login_dialog.get_by_label("Lösenord").fill(password)
                login_dialog.get_by_role(
                    "button", name=re.compile(r"Logga in", re.IGNORECASE)
                ).click()
                page.wait_for_timeout(2000)
            elif attempt == 0:
                page.goto(f"{base_url}/login", wait_until="domcontentloaded")
                login_page_dialog = page.get_by_role(
                    "dialog", name=re.compile(r"Logga in", re.IGNORECASE)
                )
                if login_page_dialog.count() > 0:
                    expect(login_page_dialog).to_be_visible()
                    login_page_dialog.get_by_label("E-post").fill(email)
                    login_page_dialog.get_by_label("Lösenord").fill(password)
                    login_page_dialog.get_by_role(
                        "button", name=re.compile(r"Logga in", re.IGNORECASE)
                    ).click()
                    page.wait_for_timeout(2000)
            if attempt == 2:
                raise
            page.wait_for_timeout(2000)


def main():
    config = get_config()
    base_url = "http://127.0.0.1:5173"
    email = config.email
    password = config.password

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        login_to_flunk_out_frenzy(
            page,
            base_url=base_url,
            email=email,
            password=password,
        )

        # Start game
        page.get_by_role("button", name=re.compile(r"^Start$", re.IGNORECASE)).click()

        # Wait for runtime to be ready
        runtime_host = page.locator('[data-test="runtime-host-placeholder"]')
        expect(runtime_host).to_have_attribute("data-runtime-load-state", "ready", timeout=30000)
        expect(runtime_host).to_have_attribute("data-runtime-mounted", "true", timeout=30000)

        page.wait_for_timeout(2000)

        # Ensure __FOF_DEBUG__ is available
        for _ in range(10):
            if page.evaluate('typeof window.__FOF_DEBUG__ !== "undefined"'):
                break
            page.wait_for_timeout(500)
        else:
            raise AssertionError("window.__FOF_DEBUG__ not found after game start.")

        # Inject events and check HUD
        page.evaluate(
            'window.__FOF_DEBUG__.injectMachineEvents([{ "type": "popup-target-hit", "tag": "target/pop-study" }])'
        )
        hud = page.evaluate("window.__FOF_DEBUG__.hud()")
        print(
            f"HUD after popup hit: jackpot_lit={hud['jackpot']['lit']}, jackpot_points={hud['jackpot']['points']}"
        )

        page.evaluate(
            'window.__FOF_DEBUG__.injectMachineEvents([{ "type": "tripwire-crossed", "tag": "tripwire/right-orbit-return" }])'
        )
        hud = page.evaluate("window.__FOF_DEBUG__.hud()")
        print(
            f"HUD after jackpot collect: jackpot_lit={hud['jackpot']['lit']}, score={hud['score']}"
        )

        browser.close()


if __name__ == "__main__":
    main()
