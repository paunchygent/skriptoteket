"""Shared Playwright helpers for the Klassrumskartan planner flows.

This module holds the reusable planner-specific login, room/class creation, and
workspace mode helpers so browser proofs do not depend on another script's
private helper functions.

Planner Playwright taxonomy:
  - `scripts.playwright_classroom_planner_smoke` is the canonical end-to-end
    browser baseline that should stay green for the shipped planner contract.
  - `scripts.playwright_pr_*.py` planner checks are targeted proof scripts for
    bounded slices and are disposable once their scoped contract is superseded.
"""

from __future__ import annotations

import re

from playwright.sync_api import Locator, Page, expect

from scripts._playwright_auth import login_via_auth_entry

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


def _wait_for_visible_heading_or_text(page: Page, *, label: str) -> None:
    """Wait until a matching heading or exact text becomes visible."""

    heading = page.get_by_role("heading", name=re.compile(re.escape(label)))
    text_match = page.get_by_text(label, exact=True)
    for _ in range(20):
        if heading.count() > 0 and heading.first.is_visible():
            return
        if text_match.count() > 0 and text_match.first.is_visible():
            return
        page.wait_for_timeout(250)

    raise AssertionError(f"{label!r} did not become visible in the live planner UI.")


def _wait_for_select_option(page: Page, *, selector: str, label: str) -> None:
    """Wait until a select control contains an option matching the label."""

    selects = page.locator(selector)
    for _ in range(40):
        for index in range(selects.count()):
            select = selects.nth(index)
            if not select.is_visible():
                continue
            option_rows = select.evaluate(
                """element => Array.from(element.options).map(option => ({
                    value: option.value,
                    label: option.label,
                }))"""
            )
            if any(option["value"] and label in option["label"] for option in option_rows):
                return
        page.wait_for_timeout(250)

    raise AssertionError(f"{label!r} did not become available in {selector}.")


def workspace_toggle(page: Page) -> Locator:
    """Return the planner workspace switch used for mode changes."""

    toggles = page.locator('[data-test="planner-workspace-switch"]')
    for _ in range(40):
        for index in range(toggles.count()):
            toggle = toggles.nth(index)
            if toggle.is_visible():
                return toggle
        page.wait_for_timeout(100)
    return toggles.first


def login_to_app(page: Page, *, base_url: str, email: str, password: str) -> None:
    """Log in through the shared repo flow, then open the protected app route."""

    login_via_auth_entry(
        page,
        base_url=base_url,
        email=email,
        password=password,
        next_path=APP_PATH,
        success_heading_pattern=r"Klassrumskartan",
    )
    wait_for_app_heading(page)


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
    _wait_for_visible_heading_or_text(page, label=roster_name)


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

    expect(
        builder_viewport.get_by_text(re.compile(r"^(seat|plats)-1$", re.IGNORECASE))
    ).to_be_visible()
    expect(
        builder_viewport.get_by_text(re.compile(r"^(seat|plats)-2$", re.IGNORECASE))
    ).to_be_visible()
    page.get_by_role("button", name=re.compile(r"Bänk", re.IGNORECASE)).click()
    grid_buttons.nth(15).click()
    page.locator('[data-test="builder-clear-room"]').click()
    expect(
        builder_viewport.get_by_text(re.compile(r"^(seat|plats)-1$", re.IGNORECASE))
    ).not_to_be_visible()
    expect(
        builder_viewport.get_by_text(re.compile(r"^(seat|plats)-2$", re.IGNORECASE))
    ).not_to_be_visible()

    page.get_by_role("button", name=re.compile(r"Sittplats", re.IGNORECASE)).click()
    grid_buttons.nth(0).click()
    grid_buttons.nth(1).click()
    expect(
        builder_viewport.get_by_text(re.compile(r"^(seat|plats)-1$", re.IGNORECASE))
    ).to_be_visible()
    expect(
        builder_viewport.get_by_text(re.compile(r"^(seat|plats)-2$", re.IGNORECASE))
    ).to_be_visible()

    with page.expect_response(re.compile(r".*/templates$")) as response_info:
        page.get_by_role("button", name=re.compile(r"Skapa klassrum", re.IGNORECASE)).click()
    if not response_info.value.ok:
        raise AssertionError(
            f"Expected classroom template creation to succeed, got {response_info.value.status}"
        )
    page.reload(wait_until="domcontentloaded")
    wait_for_app_heading(page)
    _wait_for_select_option(
        page,
        selector='[data-test="overview-template-select"], [data-test="phone-overview-template-select"]',
        label=template_name,
    )


def focus_workspace_mode(page: Page, *, label: str) -> None:
    """Select one compact class-workspace mode through the segmented toggle."""

    matcher = re.compile(re.escape(label), re.IGNORECASE)
    desktop_toggles = page.locator('[data-test="planner-workspace-switch"]')
    for _ in range(10):
        for index in range(desktop_toggles.count()):
            toggle = desktop_toggles.nth(index)
            if not toggle.is_visible():
                continue
            radio_option = toggle.get_by_role("radio", name=matcher)
            if radio_option.count() > 0:
                radio_option.first.click()
                return
            toggle.get_by_role("button", name=matcher).click()
            return
        page.wait_for_timeout(100)

    phone_switch = page.locator('[data-test="planner-phone-mode-switch"]')
    expect(phone_switch).to_be_visible()
    page.locator('[data-test="planner-phone-mode-sheet-trigger"]').click()
    phone_sheet = page.locator('[data-test="planner-phone-mode-sheet"]')
    expect(phone_sheet).to_be_visible()
    phone_sheet.get_by_role("button", name=matcher).click()
    expect(phone_sheet).not_to_be_visible()


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
    _wait_for_visible_heading_or_text(page, label=roster_name)
    expect(workspace_toggle(page)).to_be_visible()


def open_grouping_history(page: Page) -> None:
    """Open the grouping history drawer from the grouping toolbar."""

    page.locator('[data-test="grouping-actions-menu"]').click()
    page.locator('[data-test="grouping-history"]').click()


def close_history_drawer(page: Page, *, title: str) -> None:
    """Close one visible history drawer without hitting unrelated close buttons."""

    history_drawer = page.locator("aside").filter(
        has=page.get_by_role("heading", name=re.compile(re.escape(title), re.IGNORECASE))
    )
    if history_drawer.count() == 0 or not history_drawer.first.is_visible():
        return
    history_drawer.get_by_role(
        "button", name=re.compile(r"(×|Stäng historik)", re.IGNORECASE)
    ).click()


def verify_grouping_history_starts_empty(page: Page) -> None:
    """Verify the grouping history drawer starts empty before a second draft exists."""

    open_grouping_history(page)
    expect(page.get_by_text("Ingen grupphistorik ännu.", exact=True)).to_be_visible()
    close_history_drawer(page, title="Grupper")
    expect(page.get_by_text("Ingen grupphistorik ännu.", exact=True)).not_to_be_visible()


def open_grouping_workspace(page: Page, *, template_name: str) -> None:
    """Open grouping and choose a classroom through the current Smart settings drawer."""

    focus_workspace_mode(page, label="Grupper")
    expect(page.locator('[data-test="grouping-actions-menu"]')).to_be_visible()
    inline_settings = page.locator('[data-test="grouping-open-settings"]')
    if inline_settings.count() > 0 and inline_settings.first.is_visible():
        inline_settings.first.click()
    else:
        page.locator('[data-test="grouping-actions-menu"]').click()
        page.locator('[data-test="grouping-overflow-open-settings"]').click()
    settings_drawer = page.locator('[data-test="grouping-settings-drawer"]')
    expect(settings_drawer).to_be_visible()
    template_select = settings_drawer.locator('[data-test="grouping-settings-template-select"]')
    expect(template_select).to_be_visible()
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
    expect(template_select).to_have_value(matching_option["value"])
    drawer_box = settings_drawer.bounding_box()
    assert drawer_box is not None
    page.mouse.click(max(24, drawer_box["x"] / 2), max(200, drawer_box["y"] + 120))
    expect(settings_drawer).not_to_be_visible()


def open_seating_workspace(page: Page, *, template_name: str) -> None:
    """Open seating directly from the selector, then choose a room in that workspace."""

    focus_workspace_mode(page, label="Sittplatser")
    setup_surface = page.locator('[data-test="seating-workspace-setup"]')
    expect(setup_surface).to_be_visible()
    expect(page.locator('[data-test="grouping-history"]')).to_have_count(0)
    template_select = setup_surface.get_by_role("combobox")
    expect(template_select).to_be_visible()
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
    expect(page.locator('[data-test="seating-actions-menu"]')).to_be_visible()


def switch_seating_workspace_template(page: Page, *, template_name: str) -> None:
    """Switch room inside the same seating workspace."""

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
    expect(template_select).to_have_value(matching_option["value"])
    expect(page.locator('[data-test="seating-workspace"]')).to_be_visible()
    expect(page.locator('[data-test="seating-actions-menu"]')).to_be_visible()


def open_rules_workspace(page: Page) -> None:
    """Open the current rules workspace and verify its dedicated shell renders."""

    focus_workspace_mode(page, label="Regler")
    expect(page.locator('[data-test="rules-workspace-layout"]')).to_be_visible()
    expect(page.locator('[data-test="rules-map-view-planning"]')).to_be_visible()


def return_to_class_workspace(page: Page) -> None:
    """Return to the class workspace without discarding the active draft."""

    focus_workspace_mode(page, label="Översikt")
    expect(workspace_toggle(page)).to_be_visible()
    expect(page.locator('[data-test="overview-roster-select"]')).to_be_visible()


def verify_seating_toolbar(page: Page) -> None:
    """Ensure seating exposes the intended continuity, history, and classroom actions."""

    undo_button = page.locator('[data-test="undo-seating-draft"]')
    expect(undo_button).to_be_visible()
    expect(undo_button).to_have_attribute("aria-label", re.compile(r"Ångra", re.IGNORECASE))
    redo_button = page.locator('[data-test="redo-seating-draft"]')
    expect(redo_button).to_be_visible()
    expect(redo_button).to_have_attribute("aria-label", re.compile(r"Gör om", re.IGNORECASE))
    seating_actions_menu = page.locator('[data-test="seating-actions-menu"]')
    expect(seating_actions_menu).to_be_visible()
    new_seating_button = page.locator('[data-test="new-seating-draft"]')
    expect(new_seating_button).to_be_visible()
    expect(new_seating_button).to_have_text(re.compile(r"Nytt utkast", re.IGNORECASE))
    seating_actions_menu.click()
    edit_classroom_button = page.locator('[data-test="edit-current-template"]')
    expect(edit_classroom_button).to_be_visible()
    expect(edit_classroom_button).to_have_text(re.compile(r"Redigera klassrum", re.IGNORECASE))
    seating_actions_menu.click()


def verify_seating_zoom_surface(page: Page) -> None:
    """Verify seating zoom parity without depending on drag-and-drop state."""

    seating_viewport = page.locator('[data-test="room-canvas-viewport"]')
    seating_zoom_percent = page.locator('[data-test="seating-zoom-percent"]')
    expect(seating_viewport).to_be_visible()
    expect(seating_zoom_percent).to_be_visible()

    initial_zoom = seating_zoom_percent.inner_text()
    seating_scroll_fits = seating_viewport.evaluate(
        """element => ({
            widthFits: element.scrollWidth <= element.clientWidth + 2,
            heightFits: element.scrollHeight <= element.clientHeight + 2,
        })"""
    )
    assert seating_scroll_fits["widthFits"] and seating_scroll_fits["heightFits"]

    page.locator('[data-test="seating-zoom-in"]').click()
    expect(seating_zoom_percent).not_to_have_text(initial_zoom)
    zoomed_in = seating_zoom_percent.inner_text()
    expect(seating_viewport).to_have_js_property("scrollLeft", 0)
    viewport_box = seating_viewport.bounding_box()
    seat_box = page.locator('[data-test="room-seat-token"]').first.bounding_box()
    assert viewport_box is not None
    assert seat_box is not None
    assert seat_box["x"] >= viewport_box["x"] - 1

    expect(page.locator('[data-test="room-seat-token"]').first).to_contain_text(
        re.compile(r"(seat|plats)-1", re.IGNORECASE)
    )

    page.locator('[data-test="seating-zoom-out"]').click()
    expect(seating_zoom_percent).not_to_have_text(zoomed_in)
    page.locator('[data-test="seating-zoom-fit"]').click()
    expect(seating_zoom_percent).to_have_text(initial_zoom)


def open_seating_history(page: Page) -> None:
    """Open the seating history drawer from the seating toolbar."""

    page.locator('[data-test="seating-actions-menu"]').click()
    page.locator('[data-test="seating-history"]').click()


def verify_seating_history_starts_empty(page: Page) -> None:
    """Verify the seating drawer starts empty before a second draft exists."""

    open_seating_history(page)
    expect(page.get_by_text("Ingen sitthistorik ännu.", exact=True)).to_be_visible()
    close_history_drawer(page, title="Sittplatser")
    expect(page.get_by_text("Ingen sitthistorik ännu.", exact=True)).not_to_be_visible()


def start_second_seating_draft(page: Page) -> None:
    """Create a second seating draft in the current classroom."""

    page.locator('[data-test="new-seating-draft"]').click()
    expect(page.locator('[data-test="seating-workspace"]')).to_be_visible()
    page.wait_for_timeout(500)


def reopen_historic_seating_draft(page: Page) -> None:
    """Open the older seating draft from the seating history drawer."""

    open_seating_history(page)
    aside = page.locator("aside").filter(
        has=page.get_by_role("heading", name=re.compile(r"Sittplatser", re.IGNORECASE))
    )
    expect(aside.get_by_text("Tidigare sittscheman", exact=True)).to_be_visible()
    expect(aside.get_by_role("button", name="Ta bort historiskt utkast").first).to_be_visible()
    history_button = aside.get_by_role(
        "button", name=re.compile(r"Revision \d+", re.IGNORECASE)
    ).first
    history_button.click()
    expect(page.locator('[data-test="seating-workspace"]')).to_be_visible()
    expect(page.locator('[data-test="seating-actions-menu"]')).to_be_visible()
    open_seating_history(page)
    expect(page.get_by_text("Aktivt nu", exact=True)).to_be_visible()
    close_history_drawer(page, title="Sittplatser")


def delete_remaining_historic_seating_draft(page: Page) -> None:
    """Delete one historic seating draft and keep the active one intact."""

    open_seating_history(page)
    initial_history_count = page.get_by_role("button", name="Ta bort historiskt utkast").count()
    page.get_by_role("button", name="Ta bort historiskt utkast").first.click()
    confirmation = page.locator("article").filter(
        has=page.get_by_text("Ta bort utkast?", exact=True)
    )
    expect(confirmation).to_be_visible()
    confirmation.get_by_role(
        "button",
        name=re.compile(r"^Ta bort$", re.IGNORECASE),
    ).click(force=True)
    page.wait_for_timeout(300)

    remaining_history_count = initial_history_count
    for _ in range(10):
        open_seating_history(page)
        remaining_history_count = page.get_by_role(
            "button", name="Ta bort historiskt utkast"
        ).count()
        if remaining_history_count == initial_history_count - 1:
            break
        close_history_drawer(page, title="Sittplatser")
        page.wait_for_timeout(300)

    assert remaining_history_count == initial_history_count - 1
    if remaining_history_count == 0:
        expect(page.get_by_text("Ingen sitthistorik ännu.", exact=True)).to_be_visible()
    else:
        expect(page.get_by_role("button", name="Ta bort historiskt utkast").first).to_be_visible()
    close_history_drawer(page, title="Sittplatser")
    expect(page.locator('[data-test="seating-actions-menu"]')).to_be_visible()


def exit_to_origin(page: Page) -> None:
    """Leave the class workspace and land on the current planner origin."""

    page.get_by_role("button", name=re.compile(r"Avsluta", re.IGNORECASE)).first.click()
    expect(page).to_have_url(re.compile(r"/browse(?:\?.*)?$"))
    expect(page.get_by_role("heading", name=re.compile(r"Katalog", re.IGNORECASE))).to_be_visible()


def unseated_pool(page: Page) -> Locator:
    """Return the live unseated-students pool in the seating workspace."""

    return page.locator("aside").filter(has=page.get_by_text("Ej placerade", exact=True)).first


def assign_student_to_seat(page: Page, *, student_name: str, seat_id: str) -> None:
    """Create a visible seating change so historic reopen can be proven honestly."""

    student_button = unseated_pool(page).get_by_role("button", name=re.compile(student_name))
    target_seat = (
        page.locator('[data-test="room-seat-token"]')
        .filter(has=page.get_by_text(seat_id, exact=True))
        .first
    )
    expect(student_button).to_be_visible()
    expect(target_seat).to_be_visible()
    student_button.drag_to(target_seat)
    expect(unseated_pool(page).get_by_role("button", name=re.compile(student_name))).to_have_count(
        0
    )
    expect(
        page.locator('[data-test="room-seat-token"]')
        .filter(has=page.get_by_text(student_name, exact=True))
        .first
    ).to_be_visible()


def wait_for_autosave(page: Page) -> None:
    """Wait through autosave so backend history is the source of truth."""

    page.wait_for_timeout(1400)
    expect(page.get_by_text("Sparad", exact=True).first).to_be_visible()
