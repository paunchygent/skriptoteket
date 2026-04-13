"""PR-0261 retained auth action matrix and consumer probe proof.

Purpose:
    Prove that Skriptoteket auth-entry and lifecycle compatibility routes land
    directly on the accepted HuleEdu action pages, and that the hidden
    consumer probe returns sanitized signed-context claim proof.

Relationships:
    - Complements focused Vitest coverage for `sharedAuth.ts`,
      `AuthLoginPanel.vue`, and `AuthLifecycleHandoffView.vue`.
    - Uses the real backend HuleEdu verifier via the PR-0261 diagnostic route.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from cryptography.hazmat.primitives.asymmetric import rsa
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, Playwright, Route, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_huleedu_auth import (
    backend_url_for_spa,
    new_private_key,
    public_key_pem,
    signed_identity_headers,
    temporary_backend_server,
    temporary_vite_server,
)

ARTIFACTS_DIR = Path(".artifacts/playwright-pr-0261-auth-action-matrix")
DEFAULT_REALM = "skriptoteket_standalone"
DEFAULT_HULEEDU_ENTRY_URL = "https://api.hule.education/auth/login"
PROOF_NEXT_PATH = "/editor?draft=head#debug"
PROOF_TOKEN = "pr-0261-token"
PROBE_PATH = "/api/v1/diagnostics/huleedu-internal-identity"


@dataclass(frozen=True)
class ActionCase:
    """Single Skriptoteket source route and expected HuleEdu action landing."""

    name: str
    local_path: str
    provider_path: str
    heading: str
    screenshot_name: str
    expected_next: str | None = None
    expects_token: bool = False


ACTION_CASES = (
    ActionCase(
        name="login",
        local_path=f"/auth/login?next={quote(PROOF_NEXT_PATH, safe='')}",
        provider_path="/auth/login",
        heading="HuleEdu login",
        expected_next=PROOF_NEXT_PATH,
        screenshot_name="login-action-page.png",
    ),
    ActionCase(
        name="register",
        local_path=f"/register?next={quote(PROOF_NEXT_PATH, safe='')}",
        provider_path="/auth/register",
        heading="HuleEdu create account",
        expected_next=PROOF_NEXT_PATH,
        screenshot_name="register-action-page.png",
    ),
    ActionCase(
        name="password-reset-request",
        local_path="/forgot-password",
        provider_path="/auth/password-reset",
        heading="HuleEdu password reset",
        screenshot_name="forgot-password-action-page.png",
    ),
    ActionCase(
        name="password-reset-completion",
        local_path=(
            f"/reset-password?token={quote(PROOF_TOKEN, safe='')}"
            f"&next={quote(PROOF_NEXT_PATH, safe='')}"
        ),
        provider_path="/auth/password-reset",
        heading="HuleEdu password reset",
        expected_next=PROOF_NEXT_PATH,
        expects_token=True,
        screenshot_name="reset-password-action-page.png",
    ),
    ActionCase(
        name="email-verification",
        local_path=(
            f"/verify-email?token={quote(PROOF_TOKEN, safe='')}"
            "&next=https%3A%2F%2Fevil.example%2Fphish"
        ),
        provider_path="/auth/email-verification",
        heading="HuleEdu email verification",
        expects_token=True,
        screenshot_name="email-verification-action-page.png",
    ),
)


@contextmanager
def _temporary_huleedu_env(entry_url: str) -> Iterator[None]:
    previous_entry_url = os.environ.get("VITE_HULEEDU_AUTH_ENTRY_URL")
    previous_base_url = os.environ.get("VITE_HULEEDU_AUTH_BASE_URL")
    parsed = urlparse(entry_url)
    os.environ["VITE_HULEEDU_AUTH_ENTRY_URL"] = entry_url
    os.environ["VITE_HULEEDU_AUTH_BASE_URL"] = f"{parsed.scheme}://{parsed.netloc}"
    try:
        yield
    finally:
        if previous_entry_url is None:
            os.environ.pop("VITE_HULEEDU_AUTH_ENTRY_URL", None)
        else:
            os.environ["VITE_HULEEDU_AUTH_ENTRY_URL"] = previous_entry_url
        if previous_base_url is None:
            os.environ.pop("VITE_HULEEDU_AUTH_BASE_URL", None)
        else:
            os.environ["VITE_HULEEDU_AUTH_BASE_URL"] = previous_base_url


def _mock_huleedu_action_page(url: str) -> str:
    path = urlparse(url).path
    headings = {case.provider_path: case.heading for case in ACTION_CASES}
    heading = headings.get(path, "HuleEdu action")
    return f"""<!doctype html>
<html lang="sv">
  <head><meta charset="utf-8"><title>{heading}</title></head>
  <body>
    <main>
      <h1>{heading}</h1>
      <button type="button">Continue</button>
    </main>
  </body>
</html>
"""


def _install_huleedu_action_page_mock(page: Page, *, entry_url: str) -> None:
    parsed = urlparse(entry_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    def fulfill_action(route: Route) -> None:
        request = route.request
        route.fulfill(
            status=200,
            content_type="text/html",
            body=_mock_huleedu_action_page(request.url),
        )

    page.route(f"{origin}/auth/**", fulfill_action)


def _redacted_url_summary(url: str) -> dict[str, object]:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    return {
        "origin": f"{parsed.scheme}://{parsed.netloc}",
        "path": parsed.path,
        "app": query.get("app", [None])[0],
        "product_identity_realm": query.get("product_identity_realm", [None])[0],
        "return_to_path": urlparse(query.get("return_to", [""])[0]).path,
        "next": query.get("next", [None])[0],
        "token": "present_redacted" if query.get("token") else "absent",
    }


def _assert_action_case(
    page: Page,
    *,
    base_url: str,
    entry_url: str,
    case: ActionCase,
) -> dict[str, object]:
    parsed_entry = urlparse(entry_url)
    expected_origin = f"{parsed_entry.scheme}://{parsed_entry.netloc}"
    try:
        page.goto(f"{base_url}{case.local_path}", wait_until="domcontentloaded")
    except PlaywrightError as exc:
        if "ERR_ABORTED" not in str(exc):
            raise
    expect(page).to_have_url(
        re.compile(rf"^{re.escape(expected_origin + case.provider_path)}(?:\?|$)"),
        timeout=15_000,
    )
    expect(page.get_by_role("heading", name=case.heading)).to_be_visible(timeout=10_000)

    parsed = urlparse(page.url)
    query = parse_qs(parsed.query)
    if f"{parsed.scheme}://{parsed.netloc}" != expected_origin:
        raise AssertionError(f"{case.name}: expected provider origin {expected_origin}.")
    if parsed.path != case.provider_path:
        raise AssertionError(f"{case.name}: expected provider path {case.provider_path}.")

    expected_query = {
        "app": ["skriptoteket"],
        "product_identity_realm": [DEFAULT_REALM],
        "return_to": [f"{base_url}/auth/callback"],
    }
    if case.expected_next:
        expected_query["next"] = [case.expected_next]
    for key, expected_value in expected_query.items():
        if query.get(key) != expected_value:
            raise AssertionError(f"{case.name}: unexpected {key} query value.")

    if not case.expected_next and query.get("next"):
        raise AssertionError(f"{case.name}: unexpected next query value.")
    if case.expects_token != bool(query.get("token")):
        raise AssertionError(f"{case.name}: unexpected token presence.")
    if query.get("token") and query["token"] != [PROOF_TOKEN]:
        raise AssertionError(f"{case.name}: unexpected redacted proof token shape.")

    screenshot_path = ARTIFACTS_DIR / case.screenshot_name
    page.screenshot(path=str(screenshot_path), full_page=True)
    return {
        "name": case.name,
        "source_path": case.local_path.split("token=", 1)[0]
        + ("token=<redacted>" if case.expects_token else ""),
        "provider": _redacted_url_summary(page.url),
        "screenshot": str(screenshot_path),
    }


def _verify_probe(
    playwright: Playwright,
    *,
    backend_url: str,
    signed_headers: dict[str, str],
) -> dict[str, object]:
    request_context = playwright.request.new_context(base_url=backend_url)
    try:
        valid = request_context.get(PROBE_PATH, headers=signed_headers)
        missing = request_context.get(PROBE_PATH)
        if valid.status != 200:
            raise AssertionError(f"Expected probe 200, got {valid.status}")
        if missing.status != 401:
            raise AssertionError(f"Expected missing-context probe 401, got {missing.status}")

        payload = valid.json()
        serialized = json.dumps(payload, sort_keys=True)
        forbidden_values = (
            "huleedu-live-session",
            "playwright-huleedu-context",
            "pr-live-huleedu@example.test",
            "X-Huledu-Identity",
        )
        for forbidden in forbidden_values:
            if forbidden in serialized:
                raise AssertionError(f"Probe retained forbidden value marker: {forbidden}")
        return payload
    finally:
        request_context.dispose()


def _write_manifest(*, actions: list[dict[str, object]], probe: dict[str, object]) -> Path:
    manifest = {
        "status": "ok",
        "command": "pdm run pr-0261-auth-action-matrix",
        "app": "skriptoteket",
        "product_identity_realm": DEFAULT_REALM,
        "actions": actions,
        "consumer_probe": probe,
        "redaction_checks": {
            "raw_tokens_retained": False,
            "raw_signed_context_retained": False,
            "raw_session_material_retained": False,
        },
    }
    manifest_path = ARTIFACTS_DIR / "manifest.redacted.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    serialized = manifest_path.read_text(encoding="utf-8")
    if PROOF_TOKEN in serialized:
        raise AssertionError("Manifest retained a raw proof token.")
    return manifest_path


def _run(
    *,
    base_url: str,
    backend_url: str,
    entry_url: str,
    private_key: rsa.RSAPrivateKey,
) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    signed_headers = signed_identity_headers(private_key=private_key)

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        _install_huleedu_action_page_mock(page, entry_url=entry_url)
        action_results = [
            _assert_action_case(page, base_url=base_url, entry_url=entry_url, case=case)
            for case in ACTION_CASES
        ]
        probe_payload = _verify_probe(
            playwright,
            backend_url=backend_url,
            signed_headers=signed_headers,
        )
        context.close()
        browser.close()

    manifest_path = _write_manifest(actions=action_results, probe=probe_payload)
    print(
        "playwright-pr-0261-auth-action-matrix: ok "
        f"actions={len(action_results)} manifest={manifest_path}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="PR-0261 auth action matrix proof")
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--backend-url", default=None)
    parser.add_argument("--huleedu-entry-url", default=DEFAULT_HULEEDU_ENTRY_URL)
    parser.add_argument("--start-vite", action="store_true")
    parser.add_argument("--start-backend", action="store_true")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    backend_url = (args.backend_url or backend_url_for_spa(base_url)).rstrip("/")

    with _temporary_huleedu_env(args.huleedu_entry_url):
        if args.start_backend:
            private_key = new_private_key()
            public_key = public_key_pem(private_key)
            with temporary_backend_server(
                public_key,
                artifacts_dir=ARTIFACTS_DIR,
                port=None,
            ) as live_backend:
                if args.start_vite:
                    with temporary_vite_server(proxy_target=live_backend) as live_base:
                        _run(
                            base_url=live_base,
                            backend_url=live_backend,
                            entry_url=args.huleedu_entry_url,
                            private_key=private_key,
                        )
                    return
                _run(
                    base_url=base_url,
                    backend_url=live_backend,
                    entry_url=args.huleedu_entry_url,
                    private_key=private_key,
                )
            return

        if args.start_vite:
            private_key = new_private_key()
            with temporary_vite_server() as live_base:
                _run(
                    base_url=live_base,
                    backend_url=backend_url,
                    entry_url=args.huleedu_entry_url,
                    private_key=private_key,
                )
            return

        private_key = new_private_key()
        _run(
            base_url=base_url,
            backend_url=backend_url,
            entry_url=args.huleedu_entry_url,
            private_key=private_key,
        )


if __name__ == "__main__":
    main()
