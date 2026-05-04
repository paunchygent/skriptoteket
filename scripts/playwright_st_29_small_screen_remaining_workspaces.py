"""Live browser proof for the remaining Klassrumskartan small-screen slices.

Purpose:
    Exercise the signed HuleEdu app-continuation path, seed a realistic class
    list and classroom, then capture responsive screenshots for the ST-29 small
    screen shell, grouping, seating, and rules workspaces.

Relationships:
    - Complements component tests for `PlannerTopPanel`,
      `PlannerGroupingWorkspacePane`, `PlannerSeatingWorkspacePane`, and
      `PlannerRulesWorkspacePane`.
    - Reuses the shared local HuleEdu auth and Klassrumskartan Playwright
      helpers instead of bypassing the protected route.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Sequence
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from playwright.sync_api import APIRequestContext, Locator, Page, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import (
    APP_PATH,
    focus_workspace_mode,
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

ARTIFACTS_DIR = Path(".artifacts/st-29-small-screen-remaining-workspaces")
PROVIDER_SUBJECT = f"{DEFAULT_PROVIDER_SUBJECT}-st-29-remaining"
PROVIDER_EMAIL = "st-29-remaining-live-huleedu@example.test"
DISPLAY_NAME = "ST 29 Teacher"
VIEWPORTS = (
    ("phone", 390, 844),
    ("tablet", 768, 1024),
    ("laptop", 1366, 768),
    ("desktop", 1440, 900),
)
STUDENT_NAMES = (
    "Anders Bergman",
    "Andreas Fransson",
    "Bengt Fransson",
    "Birgitta Håkansson",
    "Camilla Lundin",
    "Carina Holmberg",
    "Carina Lundin",
    "Carina Svensson",
    "Caroline Lindberg",
    "Felix Lindberg",
    "Helena Bergström",
    "Ingrid Lindqvist",
    "Johanna Larsson",
    "Magnus Wikström",
    "Mats Bergström",
    "Oliver Persson",
    "Peter Lindqvist",
    "Ulf Danielsson",
    "Anna Sjögren",
    "David Nyberg",
    "Elin Persson",
    "Fatima Hassan",
    "Gustav Ek",
    "Hanna Öberg",
    "Isak Norén",
    "Julia Sand",
    "Karin Holm",
    "Leo Ström",
    "Maja Vik",
    "Nora Berg",
)


def _is_local_vite_url(base_url: str) -> bool:
    """Return whether the proof is running against a local Vite host."""

    return "127.0.0.1" in base_url or "localhost" in base_url


def _csrf_headers() -> dict[str, str]:
    """Return the local CSRF header accepted by app-continuation proofs."""

    return {"X-CSRF-Token": "huleedu-gateway-context"}


def _create_roster(
    request_context: APIRequestContext,
    *,
    name: str,
) -> str:
    """Create a visual-proof roster and return its id."""

    response = request_context.post(
        "/api/v1/apps/classroom.group-seating-studio/rosters",
        headers=_csrf_headers(),
        data={
            "name": name,
            "students": [
                {"id": f"student-{index + 1:02d}", "display_name": student_name}
                for index, student_name in enumerate(STUDENT_NAMES)
            ],
        },
    )
    if response.status != 201:
        raise AssertionError(f"Expected roster creation to succeed, got {response.status}")
    return response.json()["id"]


def _create_template(
    request_context: APIRequestContext,
    *,
    name: str,
) -> str:
    """Create a 30-seat classroom template and return its id."""

    seats = [
        {"id": f"seat-{index + 1:02d}", "x": index % 6, "y": index // 6, "zone": "front"}
        for index in range(30)
    ]
    response = request_context.post(
        "/api/v1/apps/classroom.group-seating-studio/templates",
        headers=_csrf_headers(),
        data={
            "name": name,
            "grid_cols": 8,
            "grid_rows": 6,
            "seats": seats,
            "fixtures": [],
        },
    )
    if response.status != 201:
        raise AssertionError(f"Expected template creation to succeed, got {response.status}")
    return response.json()["id"]


def _open_local_app(page: Page, *, base_url: str) -> None:
    """Open the planner through the protected local app route."""

    page.goto(f"{base_url.rstrip('/')}{APP_PATH}", wait_until="domcontentloaded")
    wait_for_app_heading(page)


def _first_visible(page: Page, selector: str) -> Locator:
    """Return the first visible locator matching a selector across transition copies."""

    for _ in range(20):
        matches = page.locator(selector)
        for index in range(matches.count()):
            candidate = matches.nth(index)
            if candidate.is_visible():
                return candidate
        page.wait_for_timeout(250)
    raise AssertionError(f"No visible element matched {selector!r}")


def _start_grouping_draft(page: Page) -> None:
    """Create one grouping draft so the phone grouping surface has groups."""

    focus_workspace_mode(page, label="Grupper")
    with page.expect_response(re.compile(r".*/drafts/grouping/new$")) as response_info:
        page.get_by_role(
            "button", name=re.compile(r"Nytt (grupputkast|utkast)", re.IGNORECASE)
        ).click()
    if not response_info.value.ok:
        raise AssertionError(
            f"Expected grouping draft creation to succeed, got {response_info.value.status}"
        )
    expect(page.locator('[data-test="grouping-board-lane"]')).to_be_visible()


def _start_seating_draft(page: Page) -> None:
    """Create one seating draft so the phone seating surface has a live map."""

    focus_workspace_mode(page, label="Sittplatser")
    with page.expect_response(re.compile(r".*/drafts/seating/new$")) as response_info:
        page.locator('[data-test="new-seating-draft"]').click()
    if not response_info.value.ok:
        raise AssertionError(
            f"Expected seating draft creation to succeed, got {response_info.value.status}"
        )
    expect(page.locator('[data-test="seating-workspace"]')).to_be_visible()


def _choose_mode(page: Page, *, mode: str, label: str) -> None:
    """Choose a workspace through the phone sheet or desktop selector."""

    phone_switch = page.locator('[data-test="planner-phone-mode-switch"]')
    if phone_switch.count() > 0 and phone_switch.first.is_visible():
        page.locator('[data-test="planner-phone-mode-sheet-trigger"]').first.click()
        sheet = page.locator('[data-test="planner-phone-mode-sheet"]').first
        expect(sheet).to_be_visible()
        sheet.locator(f'[data-test="planner-phone-mode-sheet-{mode}"]').click()
        expect(sheet).not_to_be_visible()
        return

    focus_workspace_mode(page, label=label)


def _capture_mode_shell(page: Page, *, viewport_label: str, width: int) -> None:
    """Capture the mode shell state for one viewport."""

    if width < 1024:
        trigger = page.locator('[data-test="planner-phone-mode-sheet-trigger"]').first
        expect(trigger).to_be_visible()
        trigger.click()
        sheet = page.locator('[data-test="planner-phone-mode-sheet"]').first
        expect(sheet).to_be_visible()
        for mode in ("overview", "grouping", "seating", "rules"):
            expect(sheet.locator(f'[data-test="planner-phone-mode-sheet-{mode}"]')).to_be_visible()
        page.screenshot(
            path=str(ARTIFACTS_DIR / f"{viewport_label}-mode-sheet-open.png"),
            full_page=True,
        )
        sheet.locator('[data-test="planner-phone-mode-sheet-close"]').click()
        expect(sheet).not_to_be_visible()
        return

    expect(page.locator('[data-test="planner-workspace-switch"]').first).to_be_visible()
    page.screenshot(
        path=str(ARTIFACTS_DIR / f"{viewport_label}-desktop-mode-switch.png"),
        full_page=True,
    )


def _capture_workspace(page: Page, *, mode: str, label: str, viewport_label: str) -> None:
    """Switch to one workspace, assert its surface, and capture it."""

    _choose_mode(page, mode=mode, label=label)
    if mode == "grouping":
        _first_visible(
            page, '[data-test="phone-grouping-workspace"], [data-test="grouping-layout-lane"]'
        )
    elif mode == "seating":
        _first_visible(
            page, '[data-test="phone-seating-workspace"], [data-test="seating-layout-lane"]'
        )
    elif mode == "rules":
        _first_visible(
            page, '[data-test="phone-rules-workspace"], [data-test="rules-workspace-layout"]'
        )
    page.screenshot(
        path=str(ARTIFACTS_DIR / f"{viewport_label}-{mode}.png"),
        full_page=True,
    )
    if mode == "seating":
        student_toggle = page.locator('[data-test="phone-seating-show-students"]')
        if student_toggle.count() > 0 and student_toggle.first.is_visible():
            student_toggle.first.click()
            _first_visible(page, '[data-test="phone-seating-student-sheet"]')
            page.screenshot(
                path=str(ARTIFACTS_DIR / f"{viewport_label}-seating-students-open.png"),
                full_page=True,
            )
            student_toggle.first.click()


def _verify_viewport(page: Page, *, viewport_label: str, width: int, height: int) -> None:
    """Capture one viewport across the remaining ST-29 workspaces."""

    page.set_viewport_size({"width": width, "height": height})
    page.wait_for_timeout(300)
    _choose_mode(page, mode="overview", label="Översikt")
    _capture_mode_shell(page, viewport_label=viewport_label, width=width)
    _capture_workspace(page, mode="grouping", label="Grupper", viewport_label=viewport_label)
    _capture_workspace(page, mode="seating", label="Sittplatser", viewport_label=viewport_label)
    _capture_workspace(page, mode="rules", label="Regler", viewport_label=viewport_label)


def _seed_assets(
    playwright_request_context: APIRequestContext,
    *,
    suffix: str,
) -> tuple[str, str]:
    """Seed the roster and room used by the visual proof."""

    roster_id = _create_roster(playwright_request_context, name=f"ST29 Klass {suffix}")
    template_id = _create_template(playwright_request_context, name=f"ST29 Sal {suffix}")
    return roster_id, template_id


def _run(
    *,
    base_url: str,
    backend_base_url: str,
    private_key: RSAPrivateKey,
) -> None:
    """Run the live ST-29 remaining workspace proof."""

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    suffix = str(int(time.time()))
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
        jti=f"st-29-small-screen-remaining-{suffix}",
    )

    with sync_playwright() as playwright:
        verify_profile_continuation_api(
            playwright,
            backend_url=backend_base_url,
            signed_headers=signed_headers,
            local_user_id=local_user_id,
        )
        request_context = playwright.request.new_context(
            base_url=backend_base_url,
            extra_http_headers=signed_headers,
        )
        try:
            roster_id, template_id = _seed_assets(request_context, suffix=suffix)
        finally:
            request_context.dispose()

        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
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

        page.add_init_script(
            f"""(() => {{
                const [rosterId, templateId] = {json.dumps([roster_id, template_id])};
                window.localStorage.setItem('skriptoteket:classroom-planner:selected-roster-id', rosterId);
                window.localStorage.setItem('skriptoteket:classroom-planner:selected-template-id', templateId);
            }})()""",
        )
        _open_local_app(page, base_url=base_url)
        open_class_workspace(page, roster_name=f"ST29 Klass {suffix}")
        open_grouping_workspace(page, template_name=f"ST29 Sal {suffix}")
        _start_grouping_draft(page)
        open_seating_workspace(page, template_name=f"ST29 Sal {suffix}")
        _start_seating_draft(page)

        for viewport_label, width, height in VIEWPORTS:
            _verify_viewport(page, viewport_label=viewport_label, width=width, height=height)

        context.close()
        browser.close()

    print(f"st-29-small-screen-remaining-proof: ok artifacts={ARTIFACTS_DIR}")


def main(argv: Sequence[str] | None = None) -> None:
    """Parse proof options and run the browser proof."""

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

    run_with_base_url(config.base_url, backend_url_for_spa(config.base_url))


if __name__ == "__main__":  # pragma: no cover
    main()
