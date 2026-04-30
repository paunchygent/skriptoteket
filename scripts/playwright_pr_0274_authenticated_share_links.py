"""Targeted browser proof for PR-0274 authenticated share links.

The script bootstraps an authenticated HuleEdu app-continuation session, creates
an isolated Klassrumskartan class/room pair, verifies that grouping and seating
export menus expose `Dela länk`, creates copyable share links, opens the
anonymous public read route, and proves revoke changes the public page to
unavailable.
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path
from typing import Sequence
from urllib.parse import urlsplit
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from playwright.sync_api import Page, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import (
    APP_PATH,
    create_roster,
    create_template,
    login_to_app,
    open_class_workspace,
    open_grouping_workspace,
    open_seating_workspace,
    wait_for_app_heading,
)
from scripts._playwright_config import get_config
from scripts._playwright_huleedu_auth import (
    DEFAULT_PROVIDER_SUBJECT,
    backend_url_for_spa,
    install_local_huleedu_auth_routes,
    new_private_key,
    public_key_pem,
    seed_huleedu_projection,
    signed_identity_headers,
    temporary_backend_server,
    temporary_vite_server,
    verify_profile_continuation_api,
)

ARTIFACTS_DIR = Path(".artifacts/playwright-pr-0274-authenticated-share-links")
PROVIDER_SUBJECT = f"{DEFAULT_PROVIDER_SUBJECT}-pr-0274"
PROVIDER_EMAIL = "pr-0274-live-huleedu@example.test"
DISPLAY_NAME = "PR 0274 Teacher"


def _backend_base_url(frontend_base_url: str) -> str:
    """Resolve the local backend public-read host for dev-server proofs."""

    parsed = urlsplit(frontend_base_url)
    if parsed.hostname in {"127.0.0.1", "localhost"} and parsed.port == 5173:
        return "http://127.0.0.1:8000"
    return frontend_base_url.rstrip("/")


def _is_local_vite_url(base_url: str) -> bool:
    """Return whether this proof is running against the local Vite dev host."""

    parsed = urlsplit(base_url)
    return parsed.hostname in {"127.0.0.1", "localhost"}


def _login_to_local_dev_app(page: Page, *, base_url: str) -> None:
    """Open the protected planner route and let app continuation bootstrap."""

    page.goto(f"{base_url}{APP_PATH}", wait_until="domcontentloaded")
    wait_for_app_heading(page)


def _login_for_proof(
    page: Page,
    *,
    base_url: str,
    email: str,
    password: str,
) -> None:
    """Log in through the right proof path for local dev or hosted targets."""

    if _is_local_vite_url(base_url):
        _login_to_local_dev_app(page, base_url=base_url)
        return

    login_to_app(page, base_url=base_url, email=email, password=password)


def _public_read_url(*, backend_base_url: str, copied_url: str) -> str:
    """Map the copied public URL path onto the local backend read host."""

    path = urlsplit(copied_url).path
    if not path.startswith("/share/classroom/"):
        raise AssertionError(f"Copied URL did not contain a classroom share path: {copied_url}")
    return f"{backend_base_url}{path}"


def _start_grouping_draft(page: Page) -> None:
    """Create a simple grouping draft before sharing."""

    with page.expect_response(re.compile(r".*/drafts/grouping/new$")) as response_info:
        page.get_by_role(
            "button", name=re.compile(r"Nytt (grupputkast|utkast)", re.IGNORECASE)
        ).click()
    response = response_info.value
    if not response.ok:
        raise AssertionError(f"Expected grouping draft creation to succeed, got {response.status}")
    expect(page.locator("input[type='text']").first).to_have_value("Grupp 1")


def _start_seating_draft(page: Page) -> None:
    """Create a simple seating draft before sharing."""

    with page.expect_response(re.compile(r".*/drafts/seating/new$")) as response_info:
        page.locator('[data-test="new-seating-draft"]').click()
    response = response_info.value
    if not response.ok:
        raise AssertionError(f"Expected seating draft creation to succeed, got {response.status}")
    expect(page.locator('[data-test="seating-export-menu-trigger"]')).to_be_visible()


def _create_open_and_revoke_share(
    page: Page,
    *,
    backend_base_url: str,
    kind: str,
    screenshot_name: str,
) -> None:
    """Exercise one authenticated share menu and its anonymous read route."""

    expect(page.locator('[data-test="planner-share-links-empty"]')).to_be_visible(timeout=60_000)
    page.locator(f'[data-test="{kind}-export-menu-trigger"]').click()
    share_option = page.locator(f'[data-test="{kind}-export-option-share"]')
    expect(share_option).to_have_text(re.compile(r"Dela länk", re.IGNORECASE))
    share_option.click()

    panel = page.locator('[data-test="planner-share-links-panel"]')
    expect(panel.get_by_text("Kopierad", exact=True)).to_be_visible(timeout=60_000)
    copied_url = page.evaluate("() => navigator.clipboard.readText()")
    if not isinstance(copied_url, str) or not copied_url:
        raise AssertionError("Share URL was not copied to the browser clipboard.")

    public_page = page.context.new_page()
    public_page.goto(_public_read_url(backend_base_url=backend_base_url, copied_url=copied_url))
    expect(public_page.locator("body")).to_contain_text("Klassrumskartan")
    expect(public_page.locator("script")).to_have_count(0)

    page.screenshot(path=str(ARTIFACTS_DIR / screenshot_name), full_page=True)

    page.locator('[data-test^="planner-share-revoke-"]').first.click()
    expect(panel.get_by_text("Återkallad", exact=True)).to_be_visible(timeout=30_000)
    public_page.reload()
    expect(public_page.get_by_role("heading", name="Delningen är inte tillgänglig")).to_be_visible()
    public_page.close()


def _run(
    *,
    base_url: str,
    backend_base_url: str,
    private_key: RSAPrivateKey,
    email: str,
    password: str,
) -> None:
    """Run the authenticated share-link browser proof against one stack."""

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    run_suffix = str(int(time.time()))
    roster_name = f"PR0274 Klass {run_suffix}"
    template_name = f"PR0274 Sal {run_suffix}"
    local_user_id = seed_huleedu_projection(
        local_user_id=str(uuid4()),
        provider_subject=PROVIDER_SUBJECT,
        email=PROVIDER_EMAIL,
        display_name=DISPLAY_NAME,
    )
    signed_headers = signed_identity_headers(
        private_key=private_key,
        subject=PROVIDER_SUBJECT,
        email=PROVIDER_EMAIL,
        display_name=DISPLAY_NAME,
        jti=f"pr-0274-share-links-{run_suffix}",
    )

    with sync_playwright() as playwright:
        verify_profile_continuation_api(
            playwright,
            backend_url=backend_base_url,
            signed_headers=signed_headers,
            local_user_id=local_user_id,
        )
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        context.grant_permissions(["clipboard-read", "clipboard-write"], origin=base_url)
        page = context.new_page()
        if _is_local_vite_url(base_url):
            install_local_huleedu_auth_routes(
                page,
                base_url=base_url,
                signed_headers=signed_headers,
                provider_subject=PROVIDER_SUBJECT,
                provider_email=PROVIDER_EMAIL,
                display_name=DISPLAY_NAME,
            )

        _login_for_proof(
            page,
            base_url=base_url,
            email=email,
            password=password,
        )
        create_roster(page, roster_name=roster_name)
        create_template(page, template_name=template_name)
        open_class_workspace(page, roster_name=roster_name)

        open_grouping_workspace(page, template_name=template_name)
        _start_grouping_draft(page)
        _create_open_and_revoke_share(
            page,
            backend_base_url=backend_base_url,
            kind="grouping",
            screenshot_name="grouping-share-links.png",
        )

        open_seating_workspace(page, template_name=template_name)
        _start_seating_draft(page)
        _create_open_and_revoke_share(
            page,
            backend_base_url=backend_base_url,
            kind="seating",
            screenshot_name="seating-share-links.png",
        )

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {ARTIFACTS_DIR}")


def main(argv: Sequence[str] | None = None) -> None:
    """Parse proof options and run the authenticated share-link browser proof."""

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--start-backend", action="store_true")
    parser.add_argument("--start-vite", action="store_true")
    proof_args, config_argv = parser.parse_known_args(argv)

    config = get_config(config_argv)
    private_key = new_private_key()
    public_key = public_key_pem(private_key)

    def run_with_base_url(base_url: str, backend_base_url: str) -> None:
        _run(
            base_url=base_url.rstrip("/"),
            backend_base_url=backend_base_url.rstrip("/"),
            private_key=private_key,
            email=config.email,
            password=config.password,
        )

    if proof_args.start_backend:
        with temporary_backend_server(
            public_key,
            artifacts_dir=ARTIFACTS_DIR,
            port=None if proof_args.start_vite else 8000,
        ) as live_backend:
            if proof_args.start_vite:
                with temporary_vite_server(proxy_target=live_backend) as live_base:
                    run_with_base_url(live_base, live_backend)
                return
            run_with_base_url(config.base_url, live_backend)
        return

    if proof_args.start_vite:
        with temporary_vite_server() as live_base:
            run_with_base_url(live_base, backend_url_for_spa(live_base))
        return

    run_with_base_url(config.base_url, _backend_base_url(config.base_url))


if __name__ == "__main__":  # pragma: no cover
    main()
