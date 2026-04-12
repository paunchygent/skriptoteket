"""PR-0254 live Playwright proof for cross-app HuleEdu auth cutover.

Purpose:
    Verify the real local Docker dev lane where Skriptoteket starts the
    HuleEdu-owned auth ceremony, HuleEdu login runs on port 5174, and
    Skriptoteket bootstraps through the Gateway-signed app-continuation route.

Relationships:
    - Targets PR-0254 / ST-28-04 cutover evidence.
    - Uses the normal Skriptoteket Vite frontend on port 5173 and HuleEdu
      Gateway on port 8080.
    - Persists reviewer-auditable proof artifacts without storing credentials.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urljoin, urlparse

from playwright.sync_api import Page, expect, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from scripts._playwright_browser import launch_chromium

ARTIFACTS_DIR = Path(".artifacts/playwright-pr-0254-auth-cutover")
DEFAULT_BASE_URL = "http://localhost:5173"
DEFAULT_HULEEDU_LOGIN_ORIGIN = "http://localhost:5174"
DEFAULT_HULEEDU_AUTH_ORIGIN = "http://localhost:8080"
DEFAULT_DOTENV_PATH = "../../huledu-reboot/.env"
PUBLIC_CLASSROOM_APP_PATH = "/public/apps/classroom.group-seating-studio"


@dataclass(frozen=True)
class AuthCutoverConfig:
    """Resolved PR-0254 auth-cutover proof settings."""

    base_url: str
    huleedu_login_origin: str
    huleedu_auth_origin: str
    email: str
    password: str


def _read_dotenv(path: Path) -> dict[str, str]:
    """Read simple dotenv files without evaluating shell syntax."""
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _value(
    *,
    cli_value: str | None,
    env_key: str,
    dotenv: dict[str, str],
    default: str | None = None,
) -> str | None:
    """Resolve one config value from CLI, env, dotenv, then default."""
    return cli_value or os.environ.get(env_key) or dotenv.get(env_key) or default


def _credentials(
    *,
    email: str | None,
    password: str | None,
    dotenv: dict[str, str],
) -> tuple[str | None, str | None]:
    """Resolve Playwright credentials without printing or persisting secrets."""
    resolved_email = (
        email
        or os.environ.get("PLAYWRIGHT_EMAIL")
        or dotenv.get("PLAYWRIGHT_EMAIL")
        or os.environ.get("BOOTSTRAP_SUPERUSER_EMAIL")
        or dotenv.get("BOOTSTRAP_SUPERUSER_EMAIL")
    )
    resolved_password = (
        password
        or os.environ.get("PLAYWRIGHT_PASSWORD")
        or dotenv.get("PLAYWRIGHT_PASSWORD")
        or os.environ.get("BOOTSTRAP_SUPERUSER_PASSWORD")
        or dotenv.get("BOOTSTRAP_SUPERUSER_PASSWORD")
    )
    return resolved_email, resolved_password


def _normalize_origin(value: str, *, field_name: str) -> str:
    """Validate and normalize an origin-like URL."""
    normalized = value.rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SystemExit(f"Invalid {field_name}: {value}")
    return normalized


def _parse_args(argv: Sequence[str] | None = None) -> AuthCutoverConfig:
    """Parse CLI args and dotenv-backed defaults."""
    parser = argparse.ArgumentParser(
        description="PR-0254 live HuleEdu/Skriptoteket auth-cutover proof"
    )
    parser.add_argument(
        "--dotenv",
        default=os.environ.get("DOTENV_PATH") or DEFAULT_DOTENV_PATH,
        help=(f"Dotenv file for proof credentials (default: DOTENV_PATH or {DEFAULT_DOTENV_PATH})"),
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help=f"Skriptoteket frontend base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--huleedu-login-origin",
        default=None,
        help=f"HuleEdu login UI origin (default: {DEFAULT_HULEEDU_LOGIN_ORIGIN})",
    )
    parser.add_argument(
        "--huleedu-auth-origin",
        default=None,
        help=f"HuleEdu Gateway auth origin (default: {DEFAULT_HULEEDU_AUTH_ORIGIN})",
    )
    parser.add_argument("--email", default=None, help="Login email override")
    parser.add_argument("--password", default=None, help="Login password override")
    args = parser.parse_args(argv)

    dotenv = _read_dotenv(Path(args.dotenv))
    email, password = _credentials(email=args.email, password=args.password, dotenv=dotenv)
    if not email or not password:
        parser.error(
            "Missing credentials. Provide --email/--password, PLAYWRIGHT_* values, "
            "or BOOTSTRAP_SUPERUSER_* values in --dotenv."
        )

    base_url = _normalize_origin(
        _value(
            cli_value=args.base_url,
            env_key="BASE_URL",
            dotenv=dotenv,
            default=DEFAULT_BASE_URL,
        )
        or DEFAULT_BASE_URL,
        field_name="--base-url",
    )
    huleedu_login_origin = _normalize_origin(
        _value(
            cli_value=args.huleedu_login_origin,
            env_key="HULEEDU_LOGIN_ORIGIN",
            dotenv=dotenv,
            default=DEFAULT_HULEEDU_LOGIN_ORIGIN,
        )
        or DEFAULT_HULEEDU_LOGIN_ORIGIN,
        field_name="--huleedu-login-origin",
    )
    huleedu_auth_origin = _normalize_origin(
        _value(
            cli_value=args.huleedu_auth_origin,
            env_key="HULEEDU_AUTH_ORIGIN",
            dotenv=dotenv,
            default=DEFAULT_HULEEDU_AUTH_ORIGIN,
        )
        or DEFAULT_HULEEDU_AUTH_ORIGIN,
        field_name="--huleedu-auth-origin",
    )
    return AuthCutoverConfig(
        base_url=base_url,
        huleedu_login_origin=huleedu_login_origin,
        huleedu_auth_origin=huleedu_auth_origin,
        email=email,
        password=password,
    )


def _record_matching_response(
    *,
    observed: list[dict[str, Any]],
    response,
) -> None:
    """Record only proof-relevant response metadata."""
    url = response.url
    markers = (
        "/auth/login",
        "/v1/auth/login",
        "/api/v1/public/apps/classroom.group-seating-studio",
        "/api/v1/profile/app-continuation",
        "/auth/callback",
    )
    if any(marker in url for marker in markers):
        observed.append({"status": response.status, "url": url})


def _wait_for_app_continuation(observed: list[dict[str, Any]], page: Page) -> None:
    """Wait until the live app-continuation route has returned 200."""
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if any(
            item["status"] == 200 and "/api/v1/profile/app-continuation" in str(item["url"])
            for item in observed
        ):
            return
        page.wait_for_timeout(250)
    raise AssertionError(f"app-continuation 200 not observed: {observed}")


def _wait_for_public_app_bootstrap(observed: list[dict[str, Any]], page: Page) -> None:
    """Wait until the public app bootstrap route has returned 200."""
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if any(
            item["status"] == 200
            and "/api/v1/public/apps/classroom.group-seating-studio" in str(item["url"])
            for item in observed
        ):
            return
        page.wait_for_timeout(250)
    raise AssertionError(f"public app bootstrap 200 not observed: {observed}")


def _assert_public_app_accessible(
    *,
    page: Page,
    config: AuthCutoverConfig,
    observed: list[dict[str, Any]],
) -> None:
    """Assert public Klassrumskartan remains unauthenticated before login."""
    page.goto(f"{config.base_url}{PUBLIC_CLASSROOM_APP_PATH}", wait_until="domcontentloaded")
    _wait_for_public_app_bootstrap(observed, page)
    expect(page.get_by_role("heading", name="Klassrumskartan", exact=True)).to_be_visible()
    body_text = page.locator("body").inner_text(timeout=10_000)
    if "Not authenticated" in body_text or "Inte autentiserad" in body_text:
        raise AssertionError(f"Public app showed authentication failure: {body_text[:200]}")


def _run(config: AuthCutoverConfig) -> dict[str, Any]:
    """Run the browser proof and return sanitized evidence."""
    observed: list[dict[str, Any]] = []
    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.set_default_timeout(60_000)
        page.on(
            "response",
            lambda response: _record_matching_response(observed=observed, response=response),
        )

        _assert_public_app_accessible(page=page, config=config, observed=observed)
        page.goto(config.base_url, wait_until="domcontentloaded", timeout=60_000)
        login_link = page.get_by_role("link", name=re.compile("logga in", re.I)).first
        login_link.wait_for(state="visible")
        href = login_link.get_attribute("href") or ""
        expected_auth_entry = urljoin(config.huleedu_auth_origin + "/", "auth/login")
        if not href.startswith(f"{expected_auth_entry}?"):
            raise AssertionError(f"Unexpected login href: {href}")

        login_link.click()
        page.wait_for_url(re.compile(rf"^{re.escape(config.huleedu_login_origin)}/login"))
        page.locator("#email").fill(config.email)
        page.locator("#password").fill(config.password)
        page.get_by_role("button", name=re.compile("logga in", re.I)).click()

        page.wait_for_url(re.compile(rf"^{re.escape(config.base_url)}/auth/callback"))
        _wait_for_app_continuation(observed, page)
        try:
            page.wait_for_load_state("networkidle", timeout=10_000)
        except PlaywrightTimeoutError:
            pass

        body_text = page.locator("body").inner_text(timeout=10_000)
        if "VALIDATION_ERROR" in body_text or "Return target origin is not allowed" in body_text:
            raise AssertionError("Validation error still visible after login ceremony")
        if "LOGGA UT" not in body_text.upper():
            raise AssertionError(f"Authenticated navigation not visible: {body_text[:200]}")

        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        screenshot_path = ARTIFACTS_DIR / "authenticated-home.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        result: dict[str, Any] = {
            "status": "ok",
            "base_url": config.base_url,
            "huleedu_auth_origin": config.huleedu_auth_origin,
            "huleedu_login_origin": config.huleedu_login_origin,
            "login_href_origin": href.split("/auth/login", 1)[0],
            "public_classroom_app_status": 200,
            "app_continuation_status": 200,
            "final_url": page.url,
            "observed": observed,
            "body_prefix": body_text[:160],
            "screenshot": str(screenshot_path),
        }
        (ARTIFACTS_DIR / "proof.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        context.close()
        browser.close()
        return result


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entrypoint."""
    result = _run(_parse_args(argv))
    print(
        "playwright-pr-0254-auth-cutover: ok "
        f"auth_origin={result['huleedu_auth_origin']} "
        f"login_origin={result['huleedu_login_origin']} "
        f"public_classroom_app_status={result['public_classroom_app_status']} "
        f"app_continuation_status={result['app_continuation_status']} "
        f"final_url={result['final_url']}"
    )


if __name__ == "__main__":
    main()
