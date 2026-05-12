"""Playwright proof for PR-0316 Smart-history first-run soft degrade.

Purpose:
    Prove that authenticated Klassrumskartan Smart seating and grouping runs
    apply normally when `Historik` is enabled but no eligible export/share
    checkpoints exist yet.

Relationships:
    - Uses the shared HuleEdu browser-session login helper so proof follows the
      same protected-route ceremony as the SPA.
    - Creates share-backed checkpoints, then verifies the next draft uses the
      canonical checkpoint history instead of draft or undo/redo state.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import login_to_app
from scripts._playwright_config import get_config

ARTIFACTS_DIR = Path(".artifacts/playwright-pr-0316-smart-history-first-run")
FAILURE_SCREENSHOT_PATH = ARTIFACTS_DIR / "failure.png"
APP_ID = "classroom.group-seating-studio"
API_PREFIX = f"/api/v1/apps/{APP_ID}"
CSRF_TOKEN: str | None = None


def _load_csrf_token(page: Page) -> dict[str, str]:
    """Fetch the shared HuleEdu CSRF token for browser-session writes."""

    result = page.evaluate(
        """async () => {
            const locationUrl = new URL(window.location.href);
            const candidates = [`${locationUrl.origin}/v1/auth/csrf`];
            if (["127.0.0.1", "localhost"].includes(locationUrl.hostname)) {
                candidates.push(`${locationUrl.protocol}//${locationUrl.hostname}:8080/v1/auth/csrf`);
                candidates.push(`${locationUrl.protocol}//${locationUrl.hostname}:9000/v1/auth/csrf`);
            }
            const attempts = [];
            for (const url of candidates) {
                try {
                    const response = await fetch(url, {
                        method: "GET",
                        credentials: "include",
                        headers: { "Accept": "application/json" },
                    });
                    const text = await response.text();
                    let body = null;
                    try {
                        body = text ? JSON.parse(text) : null;
                    } catch {
                        body = text;
                    }
                    attempts.push({ url, status: response.status });
                    if (response.ok && body && typeof body.csrf_token === "string") {
                        return { ok: true, source: url, token: body.csrf_token, attempts };
                    }
                } catch (error) {
                    attempts.push({ url, error: String(error) });
                }
            }
            return { ok: false, attempts };
        }"""
    )
    if not result["ok"]:
        raise AssertionError(f"Could not fetch shared CSRF token: {result['attempts']!r}")
    return {"source": result["source"], "token": result["token"]}


def _api_json(
    page: Page,
    *,
    path: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one authenticated same-origin API request from the browser page."""

    if payload is not None and CSRF_TOKEN is None:
        raise AssertionError("CSRF token must be loaded before unsafe API requests.")

    result = page.evaluate(
        """async ({ path, method, payload, csrfToken }) => {
            const headers = { "Accept": "application/json" };
            const init = { method, credentials: "include", headers };
            if (payload !== null) {
                headers["Content-Type"] = "application/json";
                headers["X-CSRF-Token"] = csrfToken;
                init.body = JSON.stringify(payload);
            }
            const response = await fetch(path, init);
            const text = await response.text();
            let body = null;
            try {
                body = text ? JSON.parse(text) : null;
            } catch {
                body = text;
            }
            return { ok: response.ok, status: response.status, body };
        }""",
        {
            "path": path,
            "method": method,
            "payload": payload,
            "csrfToken": CSRF_TOKEN,
        },
    )
    if not result["ok"]:
        raise AssertionError(f"{method} {path} returned {result['status']}: {result['body']!r}")
    body = result["body"]
    if not isinstance(body, dict):
        raise AssertionError(f"{method} {path} did not return a JSON object: {body!r}")
    return body


def _create_roster(page: Page, *, suffix: str) -> str:
    """Create one unique roster and return its id."""

    roster = _api_json(
        page,
        path=f"{API_PREFIX}/rosters",
        method="POST",
        payload={
            "name": f"PR-0316 Klass {suffix}",
            "students": [
                {"id": "s1", "display_name": "Ada Lovelace"},
                {"id": "s2", "display_name": "Bo Berg"},
                {"id": "s3", "display_name": "Cecilia Ceder"},
                {"id": "s4", "display_name": "David Dahl"},
            ],
        },
    )
    return str(roster["id"])


def _create_template(page: Page, *, suffix: str) -> str:
    """Create one unique four-seat classroom and return its id."""

    template = _api_json(
        page,
        path=f"{API_PREFIX}/templates",
        method="POST",
        payload={
            "name": f"PR-0316 Sal {suffix}",
            "grid_cols": 4,
            "grid_rows": 2,
            "seats": [
                {"id": "seat-1", "x": 0, "y": 0, "zone": "front"},
                {"id": "seat-2", "x": 1, "y": 0, "zone": "front"},
                {"id": "seat-3", "x": 2, "y": 0, "zone": "middle"},
                {"id": "seat-4", "x": 3, "y": 0, "zone": "middle"},
            ],
            "fixtures": [],
        },
    )
    return str(template["id"])


def _create_draft(
    page: Page,
    *,
    kind: str,
    roster_id: str,
    template_id: str,
) -> dict[str, Any]:
    """Create one explicit seating or grouping draft."""

    path = f"{API_PREFIX}/drafts/{kind}/new"
    payload: dict[str, Any] = {"roster_id": roster_id}
    if kind == "seating":
        payload["template_id"] = template_id
    else:
        payload["template_id"] = None
    return _api_json(page, path=path, method="POST", payload=payload)


def _ensure_smart_history_on(page: Page, *, draft: dict[str, Any]) -> dict[str, Any]:
    """Patch only when a draft is not already in the desired Smart state."""

    wants_patch = not draft["smart_enabled"] or not draft["use_history"]
    wants_grouping_distance_off = (
        draft["draft_kind"] == "grouping" and draft["grouping_seating_distance_enabled"]
    )
    if not wants_patch and not wants_grouping_distance_off:
        return draft

    payload: dict[str, Any] = {
        "expected_revision": draft["revision"],
        "smart_enabled": True,
        "use_history": True,
    }
    if draft["draft_kind"] == "grouping":
        payload["grouping_seating_distance_enabled"] = False
    workspace = _api_json(
        page,
        path=f"{API_PREFIX}/drafts/{draft['id']}",
        method="PATCH",
        payload=payload,
    )
    return workspace["draft"]


def _run_smart(
    page: Page,
    *,
    kind: str,
    draft: dict[str, Any],
    expected_used_history: bool,
) -> dict[str, Any]:
    """Run Smart for one draft and assert the PR-0316 payload shape."""

    result = _api_json(
        page,
        path=f"{API_PREFIX}/drafts/{kind}/{draft['id']}/smart-run",
        method="POST",
        payload={"expected_revision": draft["revision"]},
    )
    if result["status"] != "applied":
        raise AssertionError(f"Expected applied {kind} result, got {result!r}")
    if "reason" in result:
        raise AssertionError(f"Authenticated {kind} result still exposes blocked reason.")
    if result["used_history"] is not expected_used_history:
        raise AssertionError(
            f"Expected {kind} used_history={expected_used_history}, got {result!r}"
        )
    message = str(result.get("message") or "")
    if not expected_used_history and "historik" in message.lower():
        raise AssertionError(f"First-run {kind} message still looks history-blocked: {message!r}")
    if not isinstance(result.get("workspace"), dict):
        raise AssertionError(f"Expected {kind} smart run to return a workspace.")
    return result


def _share_draft(page: Page, *, kind: str, result: dict[str, Any]) -> dict[str, Any]:
    """Create one authenticated share, which records the Smart-history checkpoint."""

    draft = result["workspace"]["draft"]
    return _api_json(
        page,
        path=f"{API_PREFIX}/drafts/{kind}/{draft['id']}/share",
        method="POST",
        payload={"expected_revision": draft["revision"]},
    )


def _run_kind(
    page: Page,
    *,
    kind: str,
    roster_id: str,
    template_id: str,
) -> dict[str, Any]:
    """Verify first-run soft degrade and checkpoint-backed follow-up for one kind."""

    first_draft = _ensure_smart_history_on(
        page,
        draft=_create_draft(
            page,
            kind=kind,
            roster_id=roster_id,
            template_id=template_id,
        ),
    )
    first_result = _run_smart(
        page,
        kind=kind,
        draft=first_draft,
        expected_used_history=False,
    )
    share = _share_draft(page, kind=kind, result=first_result)

    second_draft = _ensure_smart_history_on(
        page,
        draft=_create_draft(
            page,
            kind=kind,
            roster_id=roster_id,
            template_id=template_id,
        ),
    )
    second_result = _run_smart(
        page,
        kind=kind,
        draft=second_draft,
        expected_used_history=True,
    )
    return {
        "first_draft_id": first_draft["id"],
        "first_revision_after_run": first_result["workspace"]["draft"]["revision"],
        "first_used_history": first_result["used_history"],
        "share_artifact_id": share["artifact"]["id"],
        "second_draft_id": second_draft["id"],
        "second_revision_after_run": second_result["workspace"]["draft"]["revision"],
        "second_used_history": second_result["used_history"],
    }


def main() -> None:
    """Run the PR-0316 authenticated Smart-history proof."""

    config = get_config()
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)
    suffix = str(int(time.time()))

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        try:
            login_to_app(
                page,
                base_url=config.base_url.rstrip("/"),
                email=config.email,
                password=config.password,
            )
            global CSRF_TOKEN
            csrf = _load_csrf_token(page)
            CSRF_TOKEN = csrf["token"]
            roster_id = _create_roster(page, suffix=suffix)
            template_id = _create_template(page, suffix=suffix)
            summary = {
                "base_url": config.base_url,
                "csrf_source": csrf["source"],
                "roster_id": roster_id,
                "template_id": template_id,
                "seating": _run_kind(
                    page,
                    kind="seating",
                    roster_id=roster_id,
                    template_id=template_id,
                ),
                "grouping": _run_kind(
                    page,
                    kind="grouping",
                    roster_id=roster_id,
                    template_id=template_id,
                ),
            }
        except Exception:
            page.screenshot(path=str(FAILURE_SCREENSHOT_PATH), full_page=True)
            raise
        finally:
            context.close()
            browser.close()

    summary_path = ARTIFACTS_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"PR-0316 Smart-history proof summary written to: {summary_path}")


if __name__ == "__main__":
    main()
