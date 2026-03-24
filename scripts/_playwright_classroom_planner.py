"""Shared Playwright helpers for the Klassrumskartan planner flows.

This module holds the reusable planner-specific login, room/class creation, and
workspace mode helpers so PR-level browser proofs do not depend on another
script's private helper functions.
"""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect

APP_PATH = "/apps/classroom.group-seating-studio"


def wait_for_app_heading(page: Page) -> None:
    """Poll for the planner root through the SPA transition after login."""

    app_heading = page.get_by_role("heading", name="Klassrumskartan", exact=True)
    landing_copy = page.get_by_text(
        "Välj en klass för att arbeta vidare med grupper eller sittplatser.",
        exact=True,
    )
    for _ in range(40):
        if app_heading.count() > 0 and app_heading.first.is_visible():
            return
        if landing_copy.count() > 0 and landing_copy.first.is_visible():
            return
        page.wait_for_timeout(500)

    raise AssertionError("Klassrumskartan did not render after protected-route login.")


def login_to_app(page: Page, *, base_url: str, email: str, password: str) -> None:
    """Log in through the shared repo flow, then open the protected app route."""

    for attempt in range(3):
        page.goto(f"{base_url}{APP_PATH}", wait_until="domcontentloaded")
        try:
            wait_for_app_heading(page)
            return
        except AssertionError:
            dialog = page.get_by_role("dialog", name=re.compile(r"Logga in", re.IGNORECASE))
            if dialog.count() > 0:
                expect(dialog).to_be_visible()
                dialog.get_by_label("E-post").fill(email)
                dialog.get_by_label("Lösenord").fill(password)
                dialog.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()
                page.wait_for_timeout(750)
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
                    page.wait_for_timeout(750)
            if attempt == 2:
                raise
            page.wait_for_timeout(1000)


def create_roster(page: Page, *, roster_name: str) -> None:
    """Create a deterministic class list through the live roster modal."""

    create_button = page.get_by_role("button", name=re.compile(r"Ny klasslista", re.IGNORECASE))
    expect(create_button).to_be_visible(timeout=60000)
    create_button.click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Ny klasslista", re.IGNORECASE))
    ).to_be_visible()
    page.get_by_placeholder(re.compile(r"Klass 9A", re.IGNORECASE)).fill(roster_name)
    page.locator("textarea").fill("Ada Lovelace\nBo Berg")
    page.get_by_role("button", name=re.compile(r"Skapa klasslista", re.IGNORECASE)).click()
    expect(page.get_by_role("heading", name=re.compile(re.escape(roster_name)))).to_be_visible()


def create_template(page: Page, *, template_name: str) -> None:
    """Create a tiny classroom through the live room modal."""

    create_button = page.get_by_role("button", name=re.compile(r"Nytt klassrum", re.IGNORECASE))
    expect(create_button).to_be_visible(timeout=60000)
    create_button.click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Nytt klassrum", re.IGNORECASE))
    ).to_be_visible()
    page.get_by_placeholder(re.compile(r"Sal 304", re.IGNORECASE)).fill(template_name)

    builder_viewport = page.locator('[data-test="room-builder-viewport"]')
    expect(builder_viewport).to_be_visible()
    initial_zoom = page.locator('[data-test="builder-zoom-percent"]').inner_text()
    builder_scroll_fits = builder_viewport.evaluate(
        """element => ({
            widthFits: element.scrollWidth <= element.clientWidth + 2,
            heightFits: element.scrollHeight <= element.clientHeight + 2,
        })"""
    )
    assert builder_scroll_fits["widthFits"] and builder_scroll_fits["heightFits"]

    page.locator('[data-test="builder-zoom-in"]').click()
    expect(page.locator('[data-test="builder-zoom-percent"]')).not_to_have_text(initial_zoom)
    page.locator('[data-test="builder-zoom-fit"]').click()
    expect(page.locator('[data-test="builder-zoom-percent"]')).to_have_text(initial_zoom)

    grid_buttons = page.locator("section .relative.grid.gap-1 button[type='button']")
    grid_buttons.nth(0).click()
    grid_buttons.nth(1).click()

    expect(builder_viewport.get_by_text("seat-1", exact=True)).to_be_visible()
    expect(builder_viewport.get_by_text("seat-2", exact=True)).to_be_visible()
    page.get_by_role("button", name=re.compile(r"Bänk", re.IGNORECASE)).click()
    grid_buttons.nth(15).click()
    page.locator('[data-test="builder-clear-room"]').click()
    expect(builder_viewport.get_by_text("seat-1", exact=True)).not_to_be_visible()
    expect(builder_viewport.get_by_text("seat-2", exact=True)).not_to_be_visible()

    page.get_by_role("button", name=re.compile(r"Placera plats", re.IGNORECASE)).click()
    grid_buttons.nth(0).click()
    grid_buttons.nth(1).click()
    expect(builder_viewport.get_by_text("seat-1", exact=True)).to_be_visible()
    expect(builder_viewport.get_by_text("seat-2", exact=True)).to_be_visible()

    page.get_by_role("button", name=re.compile(r"Skapa klassrum", re.IGNORECASE)).click()
    template_heading = page.get_by_role("heading", name=re.compile(re.escape(template_name)))
    template_text = page.get_by_text(template_name, exact=True)
    for _ in range(20):
        if template_heading.count() > 0 and template_heading.first.is_visible():
            return
        if template_text.count() > 0 and template_text.first.is_visible():
            return
        page.wait_for_timeout(250)

    raise AssertionError(
        f"Created classroom {template_name!r} did not become visible in the live UI."
    )


def focus_workspace_mode(page: Page, *, label: str) -> None:
    """Select one compact class-workspace mode through the segmented toggle."""

    toggle = page.locator('[data-ui="segmented-toggle"]')
    toggle.get_by_role("button", name=re.compile(re.escape(label), re.IGNORECASE)).click()


def open_class_workspace(page: Page, *, roster_name: str) -> None:
    """Select the target roster through the overview control and verify the shell."""

    roster_select = page.locator('[data-test="overview-roster-select"]')
    expect(roster_select).to_be_visible()
    option_rows = roster_select.evaluate(
        """element => Array.from(element.options).map(option => ({
            value: option.value,
            label: option.label,
        }))"""
    )
    matching_option = next(
        option for option in option_rows if option["value"] and roster_name in option["label"]
    )
    roster_select.select_option(value=matching_option["value"])
    expect(roster_select).to_have_value(matching_option["value"])
    expect(page.get_by_text("Klassarbetsyta", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name=re.compile(re.escape(roster_name)))).to_be_visible()
    expect(page.locator('[data-ui="segmented-toggle"]')).to_be_visible()
