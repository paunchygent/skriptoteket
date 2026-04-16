"""TASK-0376 production protected API browser proof.

Purpose:
    Prove the deployed Skriptoteket SPA uses the HuleEdu Gateway production
    protected API edge for browser-session reads and CSRF-protected writes.

Relationships:
    - Complements HuleEdu TASK-0376 by exercising the live cross-repo contract.
    - Uses `scripts._playwright_browser.launch_chromium` for repo-standard
      headless Chromium launch behavior.
    - Writes sanitized proof artifacts under `.artifacts/`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence
from urllib.parse import parse_qs, quote, urlparse

from playwright.sync_api import Page, Response, expect, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from scripts._playwright_browser import launch_chromium

DEFAULT_BASE_URL = "https://skriptoteket.hule.education"
DEFAULT_HULEEDU_AUTH_ORIGIN = "https://api.hule.education"
DEFAULT_HULEEDU_LOGIN_ORIGIN = "https://hule.education"
DEFAULT_DOTENV_PATH = ".env.prod-smoke"
ARTIFACT_ROOT = Path(".artifacts/playwright-task-0376-production-protected-api")
PUBLIC_CLASSROOM_APP_PATH = "/public/apps/classroom.group-seating-studio"
APP_CONTINUATION_PATH = "/api/v1/profile/app-continuation"
AI_SETTINGS_PATH = "/api/v1/profile/ai-settings"
PROTECTED_NEXT_PATH = "/editor"


@dataclass(frozen=True)
class ProofConfig:
    """Resolved proof configuration without credential exposure."""

    base_url: str
    huleedu_auth_origin: str
    huleedu_login_origin: str
    artifact_root: Path
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


def _normalize_origin(value: str, *, field_name: str) -> str:
    """Validate and normalize an origin-like URL."""
    normalized = value.rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path:
        raise SystemExit(f"Invalid {field_name}: {value}")
    return normalized


def _config_value(
    *,
    cli_value: str | None,
    env_key: str,
    dotenv: dict[str, str],
    default: str,
) -> str:
    """Resolve one config value from CLI, env, dotenv, then default."""
    return cli_value or os.environ.get(env_key) or dotenv.get(env_key) or default


def _parse_args(argv: Sequence[str] | None = None) -> ProofConfig:
    """Parse CLI and dotenv-backed proof config."""
    parser = argparse.ArgumentParser(description="TASK-0376 production protected API proof")
    parser.add_argument("--dotenv", default=os.environ.get("DOTENV_PATH") or DEFAULT_DOTENV_PATH)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--huleedu-auth-origin", default=None)
    parser.add_argument("--huleedu-login-origin", default=None)
    parser.add_argument("--artifact-dir", default=None)
    parser.add_argument("--email", default=None)
    parser.add_argument("--password", default=None)
    args = parser.parse_args(argv)

    dotenv = _read_dotenv(Path(args.dotenv))
    email = args.email or os.environ.get("PLAYWRIGHT_EMAIL") or dotenv.get("PLAYWRIGHT_EMAIL")
    password = (
        args.password or os.environ.get("PLAYWRIGHT_PASSWORD") or dotenv.get("PLAYWRIGHT_PASSWORD")
    )
    if not email or not password:
        parser.error("Missing credentials. Provide --email/--password or PLAYWRIGHT_* values.")

    return ProofConfig(
        base_url=_normalize_origin(
            _config_value(
                cli_value=args.base_url,
                env_key="BASE_URL",
                dotenv=dotenv,
                default=DEFAULT_BASE_URL,
            ),
            field_name="--base-url",
        ),
        huleedu_auth_origin=_normalize_origin(
            _config_value(
                cli_value=args.huleedu_auth_origin,
                env_key="HULEEDU_AUTH_ORIGIN",
                dotenv=dotenv,
                default=DEFAULT_HULEEDU_AUTH_ORIGIN,
            ),
            field_name="--huleedu-auth-origin",
        ),
        huleedu_login_origin=_normalize_origin(
            _config_value(
                cli_value=args.huleedu_login_origin,
                env_key="HULEEDU_LOGIN_ORIGIN",
                dotenv=dotenv,
                default=DEFAULT_HULEEDU_LOGIN_ORIGIN,
            ),
            field_name="--huleedu-login-origin",
        ),
        artifact_root=Path(args.artifact_dir).expanduser() if args.artifact_dir else ARTIFACT_ROOT,
        email=email,
        password=password,
    )


def _run_id() -> str:
    """Return the UTC run id used for retained artifacts."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _origin_label(url: str, config: ProofConfig) -> str:
    """Classify one observed response origin without retaining volatile values."""
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin == config.base_url:
        return "skriptoteket_app_host"
    if origin == config.huleedu_auth_origin:
        return "huleedu_gateway"
    if origin == config.huleedu_login_origin:
        return "huleedu_login_ui"
    return "other"


def _safe_query_summary(url: str, config: ProofConfig) -> dict[str, object]:
    """Return only non-secret route intent from a URL query."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    summary: dict[str, object] = {}
    if query.get("app"):
        summary["app"] = query["app"][0]
    if query.get("product_identity_realm"):
        summary["product_identity_realm"] = query["product_identity_realm"][0]
    if query.get("return_to"):
        return_to = urlparse(query["return_to"][0])
        summary["return_to_path"] = return_to.path
        summary["return_to_origin_allowed"] = (
            f"{return_to.scheme}://{return_to.netloc}" == config.base_url
        )
    if query.get("next"):
        next_path = query["next"][0]
        summary["next_path"] = (
            next_path if next_path.startswith("/") and not next_path.startswith("//") else "unsafe"
        )
        summary["next_safe"] = summary["next_path"] != "unsafe"
    return summary


def _sanitize_response(response: Response, config: ProofConfig) -> dict[str, object] | None:
    """Keep only redacted route/status evidence from relevant browser responses."""
    parsed = urlparse(response.url)
    markers = (
        "/auth/login",
        "/v1/auth/login",
        "/v1/auth/session",
        "/v1/auth/csrf",
        "/v1/auth/logout",
        "/api/v1/public/apps/classroom.group-seating-studio",
        APP_CONTINUATION_PATH,
        AI_SETTINGS_PATH,
        "/auth/callback",
    )
    if not any(marker in parsed.path for marker in markers):
        return None
    return {
        "origin_label": _origin_label(response.url, config),
        "path": parsed.path,
        "status": response.status,
        "query": _safe_query_summary(response.url, config),
    }


def _wait_for_response(
    observed: list[dict[str, object]],
    page: Page,
    *,
    path: str,
    origin_label: str,
    statuses: set[int],
    label: str,
) -> dict[str, object]:
    """Wait for one observed response by path, origin label, and status."""
    deadline = datetime.now(UTC).timestamp() + 45
    while datetime.now(UTC).timestamp() < deadline:
        for item in observed:
            status = item.get("status")
            if (
                item.get("path") == path
                and item.get("origin_label") == origin_label
                and isinstance(status, int)
                and status in statuses
            ):
                return item
        page.wait_for_timeout(250)
    raise AssertionError(f"{label} not observed from {origin_label} with {sorted(statuses)}")


def _browser_fetch(
    page: Page,
    *,
    target: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict[str, object] | None = None,
) -> dict[str, object]:
    """Run a browser fetch with credentials and return status plus JSON payload."""
    raw_response: object = page.evaluate(
        """async ({ target, method, headers, body }) => {
            const response = await fetch(target, {
                method,
                credentials: "include",
                headers: {
                    Accept: "application/json",
                    ...(body ? { "Content-Type": "application/json" } : {}),
                    ...(headers || {}),
                },
                body: body ? JSON.stringify(body) : undefined,
            });
            const contentType = response.headers.get("content-type") || "";
            const text = await response.text().catch(() => "");
            let payload = null;
            try {
                payload = text ? JSON.parse(text) : null;
            } catch {
                payload = null;
            }
            return {
                status: response.status,
                ok: response.ok,
                contentType,
                payload,
                textExcerpt: text.slice(0, 500),
            };
        }""",
        {"target": target, "method": method, "headers": headers or {}, "body": body},
    )
    if not isinstance(raw_response, dict):
        raise AssertionError("Browser fetch did not return an object")
    status = raw_response.get("status")
    ok = raw_response.get("ok")
    if not isinstance(status, int) or not isinstance(ok, bool):
        raise AssertionError("Browser fetch returned malformed status metadata")
    return {
        "status": status,
        "ok": ok,
        "content_type": raw_response.get("contentType"),
        "payload": raw_response.get("payload"),
        "text_excerpt": raw_response.get("textExcerpt"),
    }


def _redact_failure_payload(value: object) -> object:
    """Keep failure diagnostics while removing likely user or token fields."""
    if isinstance(value, dict):
        redacted: dict[str, object] = {}
        for key, item in value.items():
            normalized_key = str(key).lower()
            if normalized_key in {
                "email",
                "csrf_token",
                "token",
                "access_token",
                "refresh_token",
                "password",
                "session_id",
            }:
                redacted[str(key)] = "[redacted]"
            else:
                redacted[str(key)] = _redact_failure_payload(item)
        return redacted
    if isinstance(value, list):
        return [_redact_failure_payload(item) for item in value]
    return value


def _redact_failure_text(value: object) -> object:
    """Redact likely emails from short retained response text."""
    if not isinstance(value, str):
        return value
    return re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[redacted-email]", value)


def _failure_probe(page: Page, *, config: ProofConfig) -> dict[str, object]:
    """Fetch the protected continuation endpoint once for retained failure context."""
    try:
        response = _browser_fetch(
            page,
            target=f"{config.huleedu_auth_origin}{APP_CONTINUATION_PATH}",
        )
    except Exception as exc:
        return {"error_type": type(exc).__name__, "error_message": str(exc)}
    return {
        "status": response["status"],
        "ok": response["ok"],
        "content_type": response.get("content_type"),
        "payload": _redact_failure_payload(response.get("payload")),
        "text_excerpt": _redact_failure_text(response.get("text_excerpt")),
    }


def _login(page: Page, *, config: ProofConfig) -> None:
    """Enter the production HuleEdu login flow from a protected Skriptoteket route."""
    encoded_next = quote(PROTECTED_NEXT_PATH, safe="")
    page.goto(f"{config.base_url}/auth/login?next={encoded_next}", wait_until="domcontentloaded")
    page.wait_for_url(
        re.compile(rf"^{re.escape(config.huleedu_login_origin)}/login"),
        timeout=60_000,
    )
    page.locator("#email").fill(config.email)
    page.locator("#password").fill(config.password)
    page.get_by_role("button", name=re.compile("logga in", re.I)).click()
    page.wait_for_url(
        re.compile(rf"^{re.escape(config.base_url)}/(auth/callback|editor)"),
        timeout=60_000,
    )
    page.wait_for_url(
        re.compile(rf"^{re.escape(config.base_url + PROTECTED_NEXT_PATH)}(?:$|\?)"),
        timeout=60_000,
    )
    expect(page.get_by_role("heading", name="Kodredigeraren")).to_be_visible(timeout=20_000)
    try:
        page.wait_for_load_state("networkidle", timeout=10_000)
    except PlaywrightTimeoutError:
        pass


def _assert_public_app(page: Page, observed: list[dict[str, object]], config: ProofConfig) -> dict:
    """Assert the public app-host route still works from production."""
    page.goto(f"{config.base_url}{PUBLIC_CLASSROOM_APP_PATH}", wait_until="domcontentloaded")
    public_response = _wait_for_response(
        observed,
        page,
        path="/api/v1/public/apps/classroom.group-seating-studio",
        origin_label="skriptoteket_app_host",
        statuses={200},
        label="public app bootstrap",
    )
    expect(page.get_by_role("heading", name="Klassrumskartan", exact=True)).to_be_visible()
    return {
        "public_app_path": PUBLIC_CLASSROOM_APP_PATH,
        "public_bootstrap_origin": public_response["origin_label"],
        "public_bootstrap_status": public_response["status"],
        "public_app_host_route_still_works": True,
    }


def _assert_protected_api(page: Page, config: ProofConfig) -> dict[str, object]:
    """Assert reads and writes use the HuleEdu protected API edge."""
    protected_app_continuation = f"{config.huleedu_auth_origin}/api/v1/profile/app-continuation"
    protected_ai_settings = f"{config.huleedu_auth_origin}/api/v1/profile/ai-settings"
    direct_app_host_app_continuation = f"{config.base_url}/api/v1/profile/app-continuation"

    read = _browser_fetch(page, target=protected_app_continuation)
    if read["status"] != 200 or not isinstance(read.get("payload"), dict):
        raise AssertionError(f"Expected protected app-continuation 200, got {read['status']}")

    direct = _browser_fetch(page, target=direct_app_host_app_continuation)
    if direct["status"] == 200:
        raise AssertionError("Direct app-host protected app-continuation unexpectedly returned 200")

    negative = _browser_fetch(
        page,
        target=protected_ai_settings,
        method="PATCH",
        body={"remote_fallback_preference": "deny"},
    )
    if negative["status"] != 403:
        raise AssertionError(f"Expected missing-CSRF write 403, got {negative['status']}")

    csrf = _browser_fetch(page, target=f"{config.huleedu_auth_origin}/v1/auth/csrf")
    csrf_payload = csrf.get("payload")
    if csrf["status"] != 200 or not isinstance(csrf_payload, dict):
        raise AssertionError(f"Expected CSRF fetch 200, got {csrf['status']}")
    csrf_value = csrf_payload.get("csrf_token")
    if not isinstance(csrf_value, str) or not csrf_value:
        raise AssertionError("CSRF response did not include a token")

    positive = _browser_fetch(
        page,
        target=protected_ai_settings,
        method="PATCH",
        headers={"X-CSRF-Token": csrf_value},
        body={"remote_fallback_preference": "deny"},
    )
    if positive["status"] != 200:
        raise AssertionError(f"Expected CSRF-protected write 200, got {positive['status']}")

    return {
        "protected_read_path": APP_CONTINUATION_PATH,
        "protected_read_origin": "huleedu_gateway",
        "protected_read_status": read["status"],
        "direct_app_host_protected_read_status": direct["status"],
        "direct_app_host_protected_read_rejected": True,
        "protected_write_path": AI_SETTINGS_PATH,
        "missing_csrf_write_status": negative["status"],
        "csrf_fetch_origin": "huleedu_gateway",
        "csrf_fetch_status": csrf["status"],
        "csrf_protected_write_origin": "huleedu_gateway",
        "csrf_protected_write_status": positive["status"],
    }


def _assert_spa_observed_gateway(
    observed: list[dict[str, object]],
    page: Page,
) -> dict[str, object]:
    """Assert deployed SPA bootstrap used the HuleEdu Gateway for protected API."""
    app_continuation = _wait_for_response(
        observed,
        page,
        path=APP_CONTINUATION_PATH,
        origin_label="huleedu_gateway",
        statuses={200},
        label="SPA app-continuation",
    )
    app_host_protected = [
        item
        for item in observed
        if item.get("origin_label") == "skriptoteket_app_host"
        and item.get("path") in {APP_CONTINUATION_PATH, AI_SETTINGS_PATH}
    ]
    if app_host_protected:
        raise AssertionError("Observed protected app-host API calls before direct rejection probe")
    return {
        "spa_app_continuation_origin": app_continuation["origin_label"],
        "spa_app_continuation_status": app_continuation["status"],
        "protected_app_host_calls_before_direct_probe": 0,
    }


def _run(config: ProofConfig) -> Path:
    """Run the live browser proof and write a redacted manifest."""
    run_dir = config.artifact_root / _run_id()
    run_dir.mkdir(parents=True, exist_ok=True)
    observed: list[dict[str, object]] = []
    screenshot_path = run_dir / "editor-after-production-gateway-bootstrap.png"

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.set_default_timeout(60_000)
        page.on(
            "response",
            lambda response: (
                observed.append(summary)
                if (summary := _sanitize_response(response, config)) is not None
                else None
            ),
        )
        try:
            public_assertions = _assert_public_app(page, observed, config)
            _login(page, config=config)
            spa_assertions = _assert_spa_observed_gateway(observed, page)
            page.screenshot(path=str(screenshot_path), full_page=True)
            protected_assertions = _assert_protected_api(page, config)
        except Exception as exc:
            failure_screenshot_path = run_dir / "failure-page.png"
            try:
                page.screenshot(path=str(failure_screenshot_path), full_page=True)
            except Exception:
                failure_screenshot_path = None
            failure_manifest = {
                "task": "TASK-0376",
                "environment": "production",
                "run_id": run_dir.name,
                "status": "failed",
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "current_url": page.url,
                "observed_route_summaries": observed,
                "protected_app_continuation_failure_probe": _failure_probe(
                    page,
                    config=config,
                ),
                "failure_screenshot": (
                    str(failure_screenshot_path) if failure_screenshot_path else None
                ),
                "credentials_retained": False,
                "cookies_or_csrf_retained": False,
            }
            failure_manifest_path = run_dir / "failure.redacted.json"
            failure_manifest_path.write_text(
                json.dumps(failure_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            raise RuntimeError(f"TASK-0376 proof failed; see {failure_manifest_path}") from exc
        finally:
            context.close()
            browser.close()

    manifest = {
        "task": "TASK-0376",
        "environment": "production",
        "run_id": run_dir.name,
        "origins": {
            "skriptoteket_app_host": config.base_url,
            "huleedu_gateway": config.huleedu_auth_origin,
            "huleedu_login_ui": config.huleedu_login_origin,
        },
        "public_route_assertions": public_assertions,
        "spa_bootstrap_assertions": spa_assertions,
        "protected_api_assertions": protected_assertions,
        "observed_route_summaries": observed,
        "artifacts": [str(screenshot_path)],
        "credentials_retained": False,
        "cookies_or_csrf_retained": False,
    }
    manifest_path = run_dir / "manifest.redacted.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entrypoint."""
    manifest_path = _run(_parse_args(argv))
    print(f"playwright-task-0376-production-protected-api: ok manifest={manifest_path}")


if __name__ == "__main__":
    main()
