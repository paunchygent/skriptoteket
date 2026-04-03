"""Focused Playwright proof for the PR-0120 seating export affordance.

This script is a targeted browser proof for a bounded slice. It is not a
canonical release gate and should be pruned once its scoped contract is covered
elsewhere.


This script validates the live teacher-facing seating export flow through the
real planner UI. It checks the compact export subsection, the default
`Exportera` happy path, and a forced reload/reopen recovery path where the
backend must fall back from a broken newer in-flight job to the latest
downloadable PDF for the same draft.
"""

from __future__ import annotations

import asyncio
import re
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import requests
from playwright.sync_api import Download, Page, expect, sync_playwright
from sqlalchemy import select

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import (
    APP_PATH,
    create_roster,
    create_template,
    focus_workspace_mode,
    open_class_workspace,
    wait_for_app_heading,
)
from scripts._playwright_config import get_config

ARTIFACTS_DIR = Path(".artifacts/pr-0120-seating-export-check")


def _slugify(value: str) -> str:
    """Mirror the conservative output slug contract used by the poster renderer."""

    filtered = [character.lower() if character.isalnum() else "-" for character in value.strip()]
    slug = "".join(filtered).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "klassrumskarta"


def _open_seating_workspace(page: Page, *, template_name: str) -> None:
    """Open seating and choose the target classroom in the setup row."""

    focus_workspace_mode(page, label="Sittplatser")
    setup_surface = page.locator('[data-test="seating-workspace-setup"]')
    expect(setup_surface).to_be_visible()
    template_select = setup_surface.get_by_role("combobox")
    option_rows = template_select.evaluate(
        """element => Array.from(element.options).map(option => ({
            value: option.value,
            label: option.label,
        }))"""
    )
    matching_option = next(
        option for option in option_rows if option["value"] and template_name in option["label"]
    )
    template_select.select_option(value=matching_option["value"])
    expect(page.locator('[data-test="seating-workspace"]')).to_be_visible()
    expect(page.locator('[data-test="seating-export-group"]')).to_be_visible()


def _assign_first_student_to_first_seat(page: Page) -> None:
    """Place one student in the first visible seat before export."""

    seat_drop_target = (
        page.locator('[data-test="room-seat-token"]')
        .filter(has_text=re.compile(r"seat-1", re.IGNORECASE))
        .locator("xpath=ancestor::div[contains(@class, 'absolute')][1]")
    )
    data_transfer = page.evaluate_handle("new DataTransfer()")
    page.get_by_role("button", name=re.compile(r"Ada Lovelace", re.IGNORECASE)).dispatch_event(
        "dragstart",
        {"dataTransfer": data_transfer},
    )
    seat_drop_target.dispatch_event("dragover", {"dataTransfer": data_transfer})
    seat_drop_target.dispatch_event("drop", {"dataTransfer": data_transfer})
    expect(page.locator('[data-test="room-seat-token"]').first).to_contain_text(
        re.compile(r"Ada Lovelace", re.IGNORECASE)
    )


def _save_download(download: Download, *, target_name: str) -> Path:
    """Persist one browser download into the PR artifact directory."""

    target_path = ARTIFACTS_DIR / target_name
    download.save_as(target_path)
    assert target_path.exists()
    return target_path


def _assert_suggested_filename(
    *,
    suggested_name: str,
    roster_name: str,
    paper_size: str,
) -> None:
    """Assert the browser download keeps the teacher-facing export filename semantics."""

    assert suggested_name == f"{_slugify(roster_name)}-{paper_size}.pdf"


def _create_authenticated_context(
    browser,
    *,
    base_url: str,
    email: str,
    password: str,
):
    """Authenticate through the real API and preload the browser session cookie."""

    response = requests.post(
        f"{base_url}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    response.raise_for_status()
    session_cookie = response.cookies.get("skriptoteket_session")
    assert session_cookie, "Expected skriptoteket_session cookie after API login."

    parsed_base_url = urlparse(base_url)
    context = browser.new_context(
        viewport={"width": 1440, "height": 960},
        accept_downloads=True,
    )
    context.add_cookies(
        [
            {
                "name": "skriptoteket_session",
                "value": session_cookie,
                "domain": parsed_base_url.hostname or "127.0.0.1",
                "path": "/",
                "httpOnly": True,
            }
        ]
    )
    return context


def _export_default_a3(page: Page, *, roster_name: str) -> Path:
    """Run the default `Exportera` path and save the downloaded PDF."""

    export_button = page.locator('[data-test="seating-export-default"]')
    expect(export_button).to_have_text(re.compile(r"Exportera", re.IGNORECASE))
    with page.expect_download(timeout=120000) as download_info:
        export_button.click()
    download = download_info.value
    suggested_name = download.suggested_filename
    _assert_suggested_filename(
        suggested_name=suggested_name,
        roster_name=roster_name,
        paper_size="a3_landscape",
    )
    expect(page.locator('[data-test="seating-export-download-latest"]')).to_be_visible(
        timeout=120000
    )
    expect(page.locator('[data-test="seating-export-status"]')).to_contain_text(
        re.compile(r"PDF hämtad och sparad i Mina filer", re.IGNORECASE),
        timeout=120000,
    )
    return _save_download(download, target_name="seating-export-a3.pdf")


async def _insert_broken_in_flight_job(*, output_filename: str) -> None:
    """Insert a newer fake in-flight job so recovery must survive refresh failure."""

    project_root = Path(__file__).resolve().parents[1]
    source_root = str(project_root / "src")
    if source_root not in sys.path:
        sys.path.insert(0, source_root)

    from skriptoteket.cli._db import open_session
    from skriptoteket.config import Settings
    from skriptoteket.infrastructure.db.models import (
        classroom_planner_plan_draft as plan_draft_model,
    )
    from skriptoteket.infrastructure.db.models import user as user_model
    from skriptoteket.infrastructure.db.models import user_vault_file as user_vault_file_model
    from skriptoteket.infrastructure.db.models.classroom_planner_seating_export_job import (
        SeatingExportJobModel,
    )

    _registered_models = (plan_draft_model, user_model, user_vault_file_model)

    settings = Settings()
    async with open_session(settings) as session:
        result = await session.execute(
            select(SeatingExportJobModel)
            .where(
                SeatingExportJobModel.output_filename == output_filename,
                SeatingExportJobModel.status == "succeeded",
            )
            .order_by(
                SeatingExportJobModel.created_at.desc(),
                SeatingExportJobModel.updated_at.desc(),
            )
            .limit(1)
        )
        successful_job = result.scalar_one()
        injected_at = datetime.now(UTC)
        session.add(
            SeatingExportJobModel(
                id=uuid4(),
                owner_user_id=successful_job.owner_user_id,
                draft_id=successful_job.draft_id,
                roster_id=successful_job.roster_id,
                template_id=successful_job.template_id,
                export_kind=successful_job.export_kind,
                layout_id=successful_job.layout_id,
                paper_size=successful_job.paper_size,
                output_filename=successful_job.output_filename,
                status="processing",
                upstream_job_id=f"missing-upstream-{uuid4()}",
                webhook_subscription_id=successful_job.webhook_subscription_id,
                webhook_secret=successful_job.webhook_secret,
                vault_file_id=None,
                error_message=None,
                created_at=injected_at,
                updated_at=injected_at,
            )
        )
        await session.commit()


def _insert_broken_in_flight_job_sync(*, output_filename: str) -> None:
    """Run the async DB injection outside Playwright's active event loop."""

    error: Exception | None = None

    def _runner() -> None:
        nonlocal error
        try:
            asyncio.run(_insert_broken_in_flight_job(output_filename=output_filename))
        except Exception as exc:  # pragma: no cover - surfaced to caller
            error = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()
    if error is not None:
        raise error


def _reload_and_redownload_latest_export(
    page: Page,
    *,
    roster_name: str,
    template_name: str,
) -> Path:
    """Reload, reopen the same seating draft context, and verify fallback recovery."""

    page.reload(wait_until="domcontentloaded")
    open_class_workspace(page, roster_name=roster_name)
    _open_seating_workspace(page, template_name=template_name)
    expect(page.locator('[data-test="seating-export-download-latest"]')).to_be_visible(
        timeout=120000
    )
    expect(page.locator('[data-test="seating-export-status"]')).to_contain_text(
        re.compile(r"PDF klar för nedladdning", re.IGNORECASE),
        timeout=120000,
    )
    with page.expect_download(timeout=120000) as download_info:
        page.locator('[data-test="seating-export-download-latest"]').click()
    download = download_info.value
    _assert_suggested_filename(
        suggested_name=download.suggested_filename,
        roster_name=roster_name,
        paper_size="a3_landscape",
    )
    return _save_download(download, target_name="seating-export-a3-reloaded.pdf")


def main() -> None:
    """Run the focused reload-recovery fallback browser proof."""

    config = get_config()
    base_url = config.base_url.rstrip("/")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    run_suffix = str(int(time.time()))
    roster_name = f"PW PR0120 Klass {run_suffix}"
    template_name = f"PW PR0120 Sal {run_suffix}"

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = _create_authenticated_context(
            browser,
            base_url=base_url,
            email=config.email,
            password=config.password,
        )
        page = context.new_page()

        page.goto(f"{base_url}{APP_PATH}", wait_until="domcontentloaded")
        wait_for_app_heading(page)
        create_roster(page, roster_name=roster_name)
        create_template(page, template_name=template_name)
        page.goto(f"{base_url}{APP_PATH}", wait_until="domcontentloaded")
        open_class_workspace(page, roster_name=roster_name)
        _open_seating_workspace(page, template_name=template_name)
        _assign_first_student_to_first_seat(page)

        a3_download = _export_default_a3(page, roster_name=roster_name)
        _insert_broken_in_flight_job_sync(
            output_filename=f"{_slugify(roster_name)}-a3_landscape.pdf",
        )
        a3_reload_download = _reload_and_redownload_latest_export(
            page,
            roster_name=roster_name,
            template_name=template_name,
        )

        page.screenshot(
            path=str(ARTIFACTS_DIR / "seating-export-ui.png"),
            full_page=True,
        )

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {ARTIFACTS_DIR}")
    print(f"A3 download: {a3_download}")
    print(f"A3 download after reload: {a3_reload_download}")


if __name__ == "__main__":  # pragma: no cover
    main()
