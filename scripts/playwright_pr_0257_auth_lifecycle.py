"""PR-0257 live proof for HuleEdu lifecycle handoff routes.

Purpose:
    Verify that Skriptoteket's old account lifecycle URLs render deliberate
    browser handoff links to the HuleEdu Gateway lifecycle ceremonies.

Relationships:
    - Complements focused Vitest coverage for `sharedAuth.ts` and
      `AuthLifecycleHandoffView.vue`.
    - Uses the provider contract published by HuleEdu `TASK-0318`.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from playwright.sync_api import Page, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_huleedu_auth import temporary_vite_server

ARTIFACTS_DIR = Path(".artifacts/playwright-pr-0257-auth-lifecycle")
DEFAULT_REALM = "skriptoteket_standalone"
PROOF_NEXT_PATH = "/editor?draft=head#debug"
PROOF_TOKEN = "pr-0257-token"


@dataclass(frozen=True)
class LifecycleCase:
    """Single old Skriptoteket lifecycle route and expected HuleEdu ceremony."""

    local_path: str
    link_name: str
    provider_path: str
    screenshot_name: str
    expected_next: str | None = None
    expected_token: str | None = None


CASES = (
    LifecycleCase(
        local_path=f"/register?next={quote(PROOF_NEXT_PATH, safe='')}",
        link_name="Fortsätt till registrering",
        provider_path="/auth/register",
        expected_next=PROOF_NEXT_PATH,
        screenshot_name="register-handoff.png",
    ),
    LifecycleCase(
        local_path="/forgot-password",
        link_name="Fortsätt till återställning",
        provider_path="/auth/password-reset",
        screenshot_name="forgot-password-handoff.png",
    ),
    LifecycleCase(
        local_path=(
            f"/reset-password?token={quote(PROOF_TOKEN, safe='')}"
            f"&next={quote(PROOF_NEXT_PATH, safe='')}"
        ),
        link_name="Fortsätt till lösenordsbyte",
        provider_path="/auth/password-reset",
        expected_next=PROOF_NEXT_PATH,
        expected_token=PROOF_TOKEN,
        screenshot_name="reset-password-handoff.png",
    ),
    LifecycleCase(
        local_path=(
            f"/verify-email?token={quote(PROOF_TOKEN, safe='')}"
            "&next=https%3A%2F%2Fevil.example%2Fphish"
        ),
        link_name="Fortsätt till verifiering",
        provider_path="/auth/email-verification",
        expected_token=PROOF_TOKEN,
        screenshot_name="verify-email-handoff.png",
    ),
)


def _assert_lifecycle_case(page: Page, *, base_url: str, case: LifecycleCase) -> None:
    """Assert an old lifecycle URL renders only a safe HuleEdu ceremony handoff."""
    page.goto(f"{base_url}{case.local_path}", wait_until="domcontentloaded")
    link = page.get_by_role("link", name=case.link_name)
    expect(link).to_be_visible(timeout=10_000)
    if page.locator("form").count() != 0:
        raise AssertionError(f"{case.local_path} rendered a local form.")

    href = link.get_attribute("href")
    if href is None:
        raise AssertionError(f"{case.local_path} did not render a lifecycle handoff href.")
    if "/v1/auth/" in href or "/api/v1/auth/" in href:
        raise AssertionError(f"{case.local_path} linked to an auth API endpoint: {href!r}")

    parsed = urlparse(href)
    query = parse_qs(parsed.query)
    provider_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    expected_provider_url = f"https://api.hule.education{case.provider_path}"
    if provider_url != expected_provider_url:
        raise AssertionError(f"Expected {expected_provider_url}, got {href!r}")

    expected_query = {
        "app": ["skriptoteket"],
        "product_identity_realm": [DEFAULT_REALM],
        "return_to": [f"{base_url}/auth/callback"],
    }
    if case.expected_next:
        expected_query["next"] = [case.expected_next]
    if case.expected_token:
        expected_query["token"] = [case.expected_token]

    for key, expected_value in expected_query.items():
        if query.get(key) != expected_value:
            raise AssertionError(
                f"Expected {key}={expected_value}, got {query.get(key)} in {href!r}"
            )

    if not case.expected_next and query.get("next"):
        raise AssertionError(f"Expected no next for {case.local_path}, got {query.get('next')}")
    if not case.expected_token and query.get("token"):
        raise AssertionError(f"Expected no token for {case.local_path}, got {query.get('token')}")

    page.screenshot(path=str(ARTIFACTS_DIR / case.screenshot_name), full_page=True)


def _run(base_url: str) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        for case in CASES:
            _assert_lifecycle_case(page, base_url=base_url, case=case)
        context.close()
        browser.close()

    print(
        "playwright-pr-0257-auth-lifecycle: ok "
        "old lifecycle routes hand off to HuleEdu Gateway app=skriptoteket "
        f"realm={DEFAULT_REALM}; reset/verify tokens preserved; hostile next dropped"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="PR-0257 HuleEdu lifecycle handoff proof")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:5173",
        help="Running SPA base URL; ignored when --start-vite is set.",
    )
    parser.add_argument(
        "--start-vite",
        action="store_true",
        help="Start a temporary Vite dev server for this proof.",
    )
    args = parser.parse_args()

    if args.start_vite:
        with temporary_vite_server() as base_url:
            _run(base_url)
        return

    _run(args.base_url.rstrip("/"))


if __name__ == "__main__":
    main()
