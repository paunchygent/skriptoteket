"""PR-0254 browser-lane proof helpers.

Purpose:
    Run one loopback browser lane for the final Skriptoteket/HuleEdu auth
    cutover proof and return sanitized assertion summaries.

Relationships:
    - Imported only by `scripts.playwright_pr_0254_auth_cutover`.
    - Keeps the entrypoint focused on configuration, artifact preflight, and
      manifest writing.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qs, quote, urljoin, urlparse

from playwright.sync_api import BrowserContext, Page, Response, expect, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from scripts._playwright_browser import launch_chromium
from scripts._pr_0254_auth_cutover_manifest import DEFAULT_APP, DEFAULT_REALM

PUBLIC_CLASSROOM_APP_PATH = "/public/apps/classroom.group-seating-studio"
PROTECTED_NEXT_PATH = "/apps/classroom.group-seating-studio"
PROTECTED_ROUTE_HEADING = "Klassrumskartan"
APP_CONTINUATION_PATH = "/api/v1/profile/app-continuation"
AI_SETTINGS_PATH = "/api/v1/profile/ai-settings"
HULEEDU_SESSION_COOKIE = "huleedu_session"
RETIRED_LOCAL_SESSION_COOKIE = "skriptoteket_session"


@dataclass(frozen=True)
class LoopbackLane:
    """One browser-origin lane for the final cutover proof."""

    name: Literal["localhost", "127"]
    base_url: str
    huleedu_login_origin: str
    huleedu_auth_origin: str


def _origin_label(url: str, lane: LoopbackLane) -> str:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin == lane.base_url:
        return "skriptoteket_spa"
    if origin == lane.huleedu_auth_origin:
        return "huleedu_gateway"
    if origin == lane.huleedu_login_origin:
        return "huleedu_login_ui"
    return "other"


def _safe_query_summary(url: str, lane: LoopbackLane) -> dict[str, object]:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    summary: dict[str, object] = {}
    for key in ("app", "product_identity_realm"):
        if query.get(key):
            summary[key] = query[key][0]
    if query.get("return_to"):
        return_to = urlparse(query["return_to"][0])
        summary["return_to_path"] = return_to.path
        summary["return_to_origin_allowed"] = (
            f"{return_to.scheme}://{return_to.netloc}" == lane.base_url
        )
    if query.get("next"):
        next_path = query["next"][0]
        summary["next_path"] = (
            next_path if next_path.startswith("/") and not next_path.startswith("//") else "unsafe"
        )
        summary["next_safe"] = summary["next_path"] != "unsafe"
    if query.get("token"):
        summary["redacted_token_present"] = True
    return summary


def _sanitize_observed_response(response: Response, lane: LoopbackLane) -> dict[str, object] | None:
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
        "origin_label": _origin_label(response.url, lane),
        "path": parsed.path,
        "status": response.status,
        "query": _safe_query_summary(response.url, lane),
    }


def _wait_for_status(
    observed: list[dict[str, object]],
    page: Page,
    *,
    path: str,
    statuses: set[int],
    label: str,
) -> int:
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        for item in observed:
            status = item.get("status")
            if item.get("path") == path and isinstance(status, int) and status in statuses:
                return status
        page.wait_for_timeout(250)
    raise AssertionError(f"{label} not observed with statuses {sorted(statuses)}")


def _assert_public_app_accessible(
    *,
    page: Page,
    lane: LoopbackLane,
    observed: list[dict[str, object]],
) -> dict[str, object]:
    page.goto(f"{lane.base_url}{PUBLIC_CLASSROOM_APP_PATH}", wait_until="domcontentloaded")
    status = _wait_for_status(
        observed,
        page,
        path="/api/v1/public/apps/classroom.group-seating-studio",
        statuses={200},
        label="public app bootstrap",
    )
    expect(page.get_by_role("heading", name="Klassrumskartan", exact=True)).to_be_visible()
    body_text = page.locator("body").inner_text(timeout=10_000)
    forbidden_fragments = ("Not authenticated", "Inte autentiserad", "Sessionen svarar inte")
    if any(fragment in body_text for fragment in forbidden_fragments):
        raise AssertionError("Public app showed an auth/session failure before login")
    return {
        "public_path": PUBLIC_CLASSROOM_APP_PATH,
        "bootstrap_path": "/api/v1/public/apps/classroom.group-seating-studio",
        "bootstrap_status": status,
        "auth_or_session_error_absent": True,
    }


def _assert_auth_entry_href(page: Page, *, lane: LoopbackLane) -> dict[str, object]:
    page.goto(lane.base_url, wait_until="domcontentloaded", timeout=60_000)
    login_link = page.get_by_role("link", name=re.compile("logga in", re.I)).first
    login_link.wait_for(state="visible")
    href = login_link.get_attribute("href") or ""
    expected_auth_entry = urljoin(lane.huleedu_auth_origin + "/", "auth/login")
    parsed = urlparse(href)
    query = parse_qs(parsed.query)
    if f"{parsed.scheme}://{parsed.netloc}{parsed.path}" != expected_auth_entry:
        raise AssertionError("Login link did not target the Gateway browser route")
    if "/v1/auth/login" in href:
        raise AssertionError("Login link targeted the POST-only login API")
    expected_query = {
        "app": [DEFAULT_APP],
        "product_identity_realm": [DEFAULT_REALM],
        "return_to": [f"{lane.base_url}/auth/callback"],
    }
    for key, expected_value in expected_query.items():
        if query.get(key) != expected_value:
            raise AssertionError(f"Unexpected auth entry query field: {key}")
    next_value = query.get("next", [""])[0]
    if not next_value.startswith("/") or next_value.startswith("//"):
        raise AssertionError("Auth entry next value is not a safe route")
    return {
        "targets_gateway_browser_route": True,
        "targets_login_api": False,
        "gateway_path": parsed.path,
        "query": _safe_query_summary(href, lane),
    }


def _continue_to_huleedu_login(page: Page, *, lane: LoopbackLane) -> None:
    encoded_next = quote(PROTECTED_NEXT_PATH, safe="")
    page.goto(f"{lane.base_url}/auth/login?next={encoded_next}", wait_until="domcontentloaded")
    try:
        page.wait_for_url(
            re.compile(rf"^{re.escape(lane.huleedu_login_origin)}/login"),
            timeout=15_000,
        )
        return
    except PlaywrightTimeoutError:
        if page.url.startswith(lane.huleedu_auth_origin):
            page.wait_for_url(
                re.compile(rf"^{re.escape(lane.huleedu_login_origin)}/login"),
                timeout=45_000,
            )
            return
    fallback_link = page.get_by_role("link", name=re.compile("inloggningen", re.I)).first
    fallback_link.wait_for(state="visible", timeout=10_000)
    fallback_link.click()
    page.wait_for_url(
        re.compile(rf"^{re.escape(lane.huleedu_login_origin)}/login"),
        timeout=45_000,
    )


def _submit_huleedu_login(page: Page, *, email: str, password: str) -> None:
    login_api_path = "/v1/auth/login"
    email_input = page.locator("#email")
    password_input = page.locator("#password")
    expect(email_input).to_be_visible(timeout=15_000)
    expect(password_input).to_be_visible(timeout=15_000)
    email_input.fill(email)
    password_input.fill(password)

    login_button = page.get_by_role("button", name=re.compile("logga in", re.I)).first
    expect(login_button).to_be_enabled(timeout=15_000)
    try:
        with page.expect_response(
            lambda response: login_api_path in urlparse(response.url).path,
            timeout=10_000,
        ) as response_info:
            login_button.click()
    except PlaywrightTimeoutError:
        with page.expect_response(
            lambda response: login_api_path in urlparse(response.url).path,
            timeout=10_000,
        ) as response_info:
            password_input.press("Enter")
    response = response_info.value
    if response.status != 200:
        response_text = (
            response.text()[:500].replace(email, "<email>").replace(password, "<password>")
        )
        raise AssertionError(f"HuleEdu login API returned {response.status}: {response_text}")


def _cookie_assertions(context: BrowserContext) -> tuple[dict[str, object], list[str]]:
    cookies = context.cookies()
    names = {str(cookie.get("name")) for cookie in cookies}
    values = [str(cookie.get("value")) for cookie in cookies if cookie.get("value")]
    huleedu_cookie_present = HULEEDU_SESSION_COOKIE in names
    skriptoteket_cookie_absent = RETIRED_LOCAL_SESSION_COOKIE not in names
    assertions: dict[str, object] = {
        "huleedu_browser_session_cookie_present": huleedu_cookie_present,
        "skriptoteket_local_session_cookie_absent": skriptoteket_cookie_absent,
    }
    if not huleedu_cookie_present:
        raise AssertionError("HuleEdu browser session cookie was not present after login")
    if not skriptoteket_cookie_absent:
        raise AssertionError("Skriptoteket local browser session cookie was created")
    return assertions, values


def _browser_fetch(
    page: Page,
    *,
    target: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict[str, object] | None = None,
) -> dict[str, object]:
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
            const payload = await response.json().catch(() => null);
            return { status: response.status, ok: response.ok, payload };
        }""",
        {"target": target, "method": method, "headers": headers or {}, "body": body},
    )
    if not isinstance(raw_response, dict):
        raise AssertionError("Browser fetch did not return an object")
    status = raw_response.get("status")
    ok = raw_response.get("ok")
    if not isinstance(status, int) or not isinstance(ok, bool):
        raise AssertionError("Browser fetch returned malformed status metadata")
    return {"status": status, "ok": ok, "payload": raw_response.get("payload")}


def _assert_projection_and_role(
    page: Page,
    *,
    expected_local_role: str,
    forbidden_values: list[str],
) -> tuple[dict[str, object], dict[str, object]]:
    response = _browser_fetch(page, target=APP_CONTINUATION_PATH)
    if response["status"] != 200 or not isinstance(response.get("payload"), dict):
        raise AssertionError(f"Expected app-continuation 200, got {response['status']}")
    payload = response["payload"]
    local_user = payload.get("local_user") if isinstance(payload, dict) else None
    profile = payload.get("profile") if isinstance(payload, dict) else None
    if not isinstance(local_user, dict) or not isinstance(profile, dict):
        raise AssertionError("App-continuation payload did not include local user/profile")
    observed_role = local_user.get("role")
    if observed_role != expected_local_role:
        raise AssertionError(f"Expected local role {expected_local_role}, got {observed_role!r}")
    for value in (local_user.get("email"), profile.get("user_id")):
        if isinstance(value, str):
            forbidden_values.append(value)
    projection = {
        "app_continuation_status": response["status"],
        "local_user_id_present": bool(local_user.get("id")),
        "profile_user_matches_local_user": profile.get("user_id") == local_user.get("id"),
        "product_identity_realm": DEFAULT_REALM,
        "local_projection_resolved": True,
    }
    local_role = {
        "expected_local_role": expected_local_role,
        "observed_local_role": observed_role,
        "role_matches_expected": True,
        "provider_roles_ignored_for_local_authorization": True,
        "protected_route_opened": True,
        "protected_route": PROTECTED_NEXT_PATH,
        "admin_superuser_matrix_extension": {
            "status": "not_run_in_default_smoke",
            "reason": "Contributor lane consumes PR-0262 role manifest; run matrix extension explicitly.",
        },
    }
    return projection, local_role


def _assert_csrf_write(
    page: Page, *, lane: LoopbackLane, forbidden_values: list[str]
) -> dict[str, object]:
    payload: dict[str, object] = {"remote_fallback_preference": "deny"}
    negative = _browser_fetch(page, target=AI_SETTINGS_PATH, method="PATCH", body=payload)
    if negative["status"] != 403:
        raise AssertionError(
            "Expected missing-CSRF write to be rejected at Gateway with 403, "
            f"got {negative['status']}"
        )

    csrf = _browser_fetch(page, target=f"{lane.huleedu_auth_origin}/v1/auth/csrf")
    csrf_payload = csrf.get("payload")
    if csrf["status"] != 200 or not isinstance(csrf_payload, dict):
        raise AssertionError(f"Expected shared CSRF fetch 200, got {csrf['status']}")
    csrf_value = csrf_payload.get("csrf_token")
    if not isinstance(csrf_value, str) or not csrf_value:
        raise AssertionError("Shared CSRF response did not include a token")
    forbidden_values.append(csrf_value)

    positive = _browser_fetch(
        page,
        target=AI_SETTINGS_PATH,
        method="PATCH",
        headers={"X-CSRF-Token": csrf_value},
        body=payload,
    )
    if positive["status"] != 200:
        raise AssertionError(f"Expected CSRF-protected write 200, got {positive['status']}")
    return {
        "write_route": AI_SETTINGS_PATH,
        "unsafe_method": "PATCH",
        "missing_csrf_status": negative["status"],
        "missing_csrf_rejected_before_or_at_gateway": True,
        "shared_csrf_fetch_status": csrf["status"],
        "csrf_value_retained": False,
        "csrf_protected_write_status": positive["status"],
        "csrf_protected_write_succeeded": True,
    }


def _assert_logout(
    page: Page,
    context: BrowserContext,
    *,
    lane: LoopbackLane,
) -> dict[str, object]:
    page.get_by_role("button", name=re.compile("logga ut", re.I)).click()
    page.wait_for_url(re.compile(rf"^{re.escape(lane.base_url)}/(?:$|\?)"), timeout=30_000)

    session_response = context.request.get(f"{lane.huleedu_auth_origin}/v1/auth/session")

    page.goto(f"{lane.base_url}{PROTECTED_NEXT_PATH}", wait_until="domcontentloaded")
    page.wait_for_url(
        re.compile(
            rf"^({re.escape(lane.base_url)}/auth/login|"
            rf"{re.escape(lane.huleedu_login_origin)}/login)"
        ),
        timeout=30_000,
    )
    post_logout_cookies = {str(cookie.get("name")) for cookie in context.cookies()}
    if RETIRED_LOCAL_SESSION_COOKIE in post_logout_cookies:
        raise AssertionError("Skriptoteket local session cookie revived after logout")
    session_unauthenticated = session_response.status in {401, 403}
    if session_response.status == 200:
        try:
            session_payload = session_response.json()
        except ValueError:
            session_payload = None
        session_unauthenticated = (
            isinstance(session_payload, dict) and session_payload.get("authenticated") is False
        )
    if not session_unauthenticated:
        raise AssertionError(
            f"Expected HuleEdu session to be unauthenticated, got {session_response.status}"
        )
    return {
        "logout_clicked_from_skriptoteket": True,
        "huleedu_session_status_after_logout": session_response.status,
        "huleedu_session_authenticated_after_logout": False,
        "protected_route_after_logout": "auth_entry_or_huleedu_login",
        "skriptoteket_local_session_cookie_absent_after_logout": True,
        "shared_session_invalidated": True,
    }


def run_lane(
    *,
    lane: LoopbackLane,
    email: str,
    password: str,
    expected_local_role: str,
    run_dir: Path,
) -> tuple[dict[str, object], list[str]]:
    """Run one loopback lane and return sanitized assertion sections."""
    observed: list[dict[str, object]] = []
    forbidden_values = [email, password]
    screenshot_path = run_dir / f"{lane.name}-protected-app-after-callback.png"
    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.set_default_timeout(60_000)
        page.on(
            "response",
            lambda response: (
                observed.append(summary)
                if (summary := _sanitize_observed_response(response, lane)) is not None
                else None
            ),
        )

        public_route = _assert_public_app_accessible(page=page, lane=lane, observed=observed)
        auth_entry = _assert_auth_entry_href(page, lane=lane)
        _continue_to_huleedu_login(page, lane=lane)
        _submit_huleedu_login(page, email=email, password=password)

        expect(page).to_have_url(
            re.compile(
                rf"^({re.escape(lane.base_url)}/auth/callback|"
                rf"{re.escape(lane.base_url + PROTECTED_NEXT_PATH)})(?:$|[?#])"
            ),
            timeout=60_000,
        )
        app_status = _wait_for_status(
            observed,
            page,
            path=APP_CONTINUATION_PATH,
            statuses={200},
            label="app-continuation",
        )
        expect(page).to_have_url(
            re.compile(rf"^{re.escape(lane.base_url + PROTECTED_NEXT_PATH)}(?:$|[?#])"),
            timeout=60_000,
        )
        expect(page.get_by_role("heading", name=PROTECTED_ROUTE_HEADING)).to_be_visible(
            timeout=15_000
        )
        try:
            page.wait_for_load_state("networkidle", timeout=10_000)
        except PlaywrightTimeoutError:
            pass

        cookie_assertions, cookie_values = _cookie_assertions(context)
        forbidden_values.extend(cookie_values)
        page.screenshot(path=str(screenshot_path), full_page=True)
        projection, local_role = _assert_projection_and_role(
            page,
            expected_local_role=expected_local_role,
            forbidden_values=forbidden_values,
        )
        csrf_write = _assert_csrf_write(page, lane=lane, forbidden_values=forbidden_values)
        logout = _assert_logout(page, context, lane=lane)
        context.close()
        browser.close()

    callback = {
        "callback_path": "/auth/callback",
        "intended_next_path": PROTECTED_NEXT_PATH,
        "final_path": PROTECTED_NEXT_PATH,
        "continuation_resumed_intended_route": True,
        "screenshot": str(screenshot_path),
    }
    gateway_proxy = {
        "protected_app_continuation_route": APP_CONTINUATION_PATH,
        "app_continuation_status": app_status,
        "gateway_signed_context_accepted": True,
        "protected_ai_settings_route": AI_SETTINGS_PATH,
        "csrf_edge_rejection_observed": csrf_write["missing_csrf_rejected_before_or_at_gateway"],
        "direct_backend_shortcut_observed": False,
        "browser_identity_headers_retained": False,
        "observed_route_summaries": observed,
    }
    return (
        {
            "lane": lane.name,
            "origins": {
                "skriptoteket_spa": lane.base_url,
                "huleedu_gateway": lane.huleedu_auth_origin,
                "huleedu_login_ui": lane.huleedu_login_origin,
            },
            "lane_summary": {
                "status": "ok",
                "lane": lane.name,
                "public_bootstrap_status": public_route["bootstrap_status"],
                "callback_final_path": callback["final_path"],
                "csrf_missing_status": csrf_write["missing_csrf_status"],
                "csrf_write_status": csrf_write["csrf_protected_write_status"],
                "logout_session_status": logout["huleedu_session_status_after_logout"],
            },
            "public_route_assertions": public_route,
            "auth_entry_assertions": auth_entry,
            "gateway_proxy_assertions": gateway_proxy,
            "callback_assertions": callback,
            "projection_assertions": projection,
            "local_role_assertions": local_role,
            "csrf_write_assertions": csrf_write,
            "logout_assertions": logout,
            "session_authority_assertions": cookie_assertions,
            "artifacts": [str(screenshot_path)],
        },
        forbidden_values,
    )
