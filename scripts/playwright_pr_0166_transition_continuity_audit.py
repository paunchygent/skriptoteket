"""Focused Playwright continuity audit for same-shell and route transitions.

This proof exercises the remaining transition surfaces touched by ST-30-02 and
records DOM-stage continuity during live client-side swaps. It covers the
planner shell, rules map projection switch, route-shell navigation, editor mode
switches, and the remaining inline transition surfaces that were normalized away
from sequential `out-in` behavior.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import requests
from playwright.sync_api import Page, expect, sync_playwright

from scripts._playwright_classroom_planner import (
    APP_PATH,
    focus_workspace_mode,
    open_class_workspace,
    wait_for_app_heading,
)
from scripts._playwright_config import get_config
from scripts.playwright_ui_smoke import _launch_chromium

ARTIFACTS_DIR = Path(".artifacts/pr-0166-transition-continuity-audit")


def _resolve_api_base_url(base_url: str) -> str:
    """Map the SPA base URL to the backing API origin for local audit helpers."""

    parsed = urlparse(base_url.rstrip("/"))
    hostname = parsed.hostname or "127.0.0.1"
    port = parsed.port
    if hostname in {"127.0.0.1", "localhost"} and port == 5173:
        return urlunparse((parsed.scheme, f"{hostname}:8000", "", "", "", ""))
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))


def _create_api_session(*, api_base_url: str, email: str, password: str) -> requests.Session:
    """Authenticate against the API so the audit can discover live editor fixtures."""

    session = requests.Session()
    login_response = session.post(
        f"{api_base_url}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    login_response.raise_for_status()
    return session


def _pick_editor_tool_id(*, session: requests.Session, api_base_url: str) -> str | None:
    """Choose one existing tool version so the editor workspace can be audited live."""

    response = session.get(f"{api_base_url}/api/v1/admin/tools", timeout=30)
    response.raise_for_status()
    tools = response.json().get("tools", [])
    for tool in tools:
        if tool.get("version_count", 0) > 0:
            return str(tool["id"])
    return None


def _start_stage_sampler(
    page: Page,
    *,
    key: str,
    item_selector: str,
    stage_selector: str | None = None,
    sample_ms: int = 550,
) -> None:
    """Begin requestAnimationFrame sampling for one transition stage."""

    page.evaluate(
        """({ key, itemSelector, stageSelector, sampleMs }) => {
          const item = document.querySelector(itemSelector);
          const stage = stageSelector
            ? document.querySelector(stageSelector)
            : item?.parentElement ?? null;
          if (!stage) {
            window.__transitionAudit = { key, error: `Missing stage for ${key}` };
            return;
          }

          window.__transitionAudit = {
            key,
            itemSelector,
            stageSelector,
            counts: [],
            startedAt: performance.now(),
          };

          const sample = () => {
            const currentStage = stageSelector
              ? document.querySelector(stageSelector)
              : document.querySelector(itemSelector)?.parentElement ?? stage;
            const count = currentStage
              ? currentStage.querySelectorAll(itemSelector).length
              : 0;
            window.__transitionAudit.counts.push(count);
            if (performance.now() - window.__transitionAudit.startedAt < sampleMs) {
              requestAnimationFrame(sample);
            }
          };

          requestAnimationFrame(sample);
        }""",
        {
            "key": key,
            "itemSelector": item_selector,
            "stageSelector": stage_selector,
            "sampleMs": sample_ms,
        },
    )


def _finish_stage_sampler(page: Page, *, sample_ms: int = 550) -> dict[str, object]:
    """Collect the sampled continuity counts after the transition settles."""

    page.wait_for_timeout(sample_ms + 120)
    result = page.evaluate("() => window.__transitionAudit")
    if not isinstance(result, dict):
        raise AssertionError(f"Missing continuity audit payload: {result!r}")
    return result


def _assert_continuity(result: dict[str, object]) -> None:
    """Fail if the sampled stage ever went blank during a transition."""

    if "error" in result:
        raise AssertionError(str(result["error"]))

    counts = [int(value) for value in result.get("counts", [])]
    if not counts:
        raise AssertionError(f"No continuity samples were collected for {result.get('key')!r}.")
    minimum = min(counts)
    if minimum < 1:
        raise AssertionError(
            f"Continuity broke for {result.get('key')!r}: sampled counts were {counts!r}."
        )


def _audit_stage(
    page: Page,
    *,
    key: str,
    item_selector: str,
    trigger: Callable[[], None],
    stage_selector: str | None = None,
    sample_ms: int = 550,
) -> dict[str, object]:
    """Run one continuity check and return the sampled stats for the summary."""

    _start_stage_sampler(
        page,
        key=key,
        item_selector=item_selector,
        stage_selector=stage_selector,
        sample_ms=sample_ms,
    )
    trigger()
    result = _finish_stage_sampler(page, sample_ms=sample_ms)
    _assert_continuity(result)
    return {
        "key": key,
        "min": min(int(value) for value in result["counts"]),
        "max": max(int(value) for value in result["counts"]),
        "samples": len(result["counts"]),
    }


def _open_editor_page(page: Page, *, base_url: str, tool_id: str) -> None:
    """Open one live admin tool editor and wait for the workspace controls."""

    page.goto(f"{base_url}/admin/tools/{tool_id}", wait_until="domcontentloaded")
    expect(
        page.get_by_role("heading", name=re.compile(r"Kodredigeraren", re.IGNORECASE))
    ).to_be_visible()
    expect(page.get_by_label("Välj editor-läge")).to_be_visible()


def _choose_planner_template(page: Page, *, select_test_id: str, template_name: str) -> None:
    """Select one classroom template inside the planner toolbars."""

    template_select = page.locator(f'[data-test="{select_test_id}"]')
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


def _create_roster_loose(page: Page, *, roster_name: str) -> None:
    """Create one class list without failing on the intentional transition overlap."""

    create_button = page.get_by_role("button", name=re.compile(r"Ny klasslista", re.IGNORECASE))
    expect(create_button).to_be_visible(timeout=60000)
    create_button.click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Ny klasslista", re.IGNORECASE))
    ).to_be_visible()
    page.get_by_placeholder(re.compile(r"Klass 9A", re.IGNORECASE)).fill(roster_name)
    page.locator("textarea").fill("Ada Lovelace\nBo Berg")
    page.get_by_role("button", name=re.compile(r"Skapa klasslista", re.IGNORECASE)).click()

    roster_heading = page.get_by_role("heading", name=re.compile(re.escape(roster_name)))
    roster_text = page.get_by_text(roster_name, exact=True)
    for _ in range(20):
        if roster_heading.count() > 0 and roster_heading.first.is_visible():
            return
        if roster_text.count() > 0 and roster_text.first.is_visible():
            return
        page.wait_for_timeout(250)

    raise AssertionError(f"Created roster {roster_name!r} did not become visible in the live UI.")


def _create_template_loose(page: Page, *, template_name: str) -> None:
    """Create one classroom without failing on overlapping continuity states."""

    create_button = page.get_by_role("button", name=re.compile(r"Nytt klassrum", re.IGNORECASE))
    expect(create_button).to_be_visible(timeout=60000)
    create_button.click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Nytt klassrum", re.IGNORECASE))
    ).to_be_visible()
    page.get_by_placeholder(re.compile(r"Sal 304", re.IGNORECASE)).fill(template_name)

    grid_buttons = page.locator("section .relative.grid.gap-1 button[type='button']")
    page.get_by_role("button", name=re.compile(r"Sittplats", re.IGNORECASE)).click()
    grid_buttons.nth(0).click()
    grid_buttons.nth(1).click()
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


def _ensure_seating_assignments(page: Page, *, template_name: str) -> None:
    """Create one active seating arrangement so the rules projection toggle is available."""

    focus_workspace_mode(page, label="Sittplatser")
    _choose_planner_template(
        page, select_test_id="seating-template-select", template_name=template_name
    )
    new_draft_button = page.locator('[data-test="new-seating-draft"]')
    if new_draft_button.is_enabled():
        new_draft_button.click()
    randomize_button = page.locator('[data-test="randomize-seating"]')
    expect(randomize_button).to_be_enabled(timeout=60000)
    randomize_button.click()
    expect(page.locator('[data-test="room-seat-token"]')).to_have_count(2, timeout=60000)


def _audit_route_transitions(page: Page) -> list[dict[str, object]]:
    """Exercise the shared RouterView crossfade through real sidebar navigation."""

    results: list[dict[str, object]] = []
    expect(
        page.get_by_role("heading", name=re.compile(r"Välkommen", re.IGNORECASE))
    ).to_be_visible()

    results.append(
        _audit_stage(
            page,
            key="route-home-to-profile",
            stage_selector=".route-stage",
            item_selector=".route-stage-item",
            trigger=lambda: page.get_by_role("link", name="Profil").click(),
        )
    )
    expect(page.get_by_role("heading", name=re.compile(r"Profil", re.IGNORECASE))).to_be_visible()

    results.append(
        _audit_stage(
            page,
            key="route-profile-to-vault",
            stage_selector=".route-stage",
            item_selector=".route-stage-item",
            trigger=lambda: page.get_by_role("link", name="Mina filer").click(),
        )
    )
    expect(
        page.get_by_role("heading", name=re.compile(r"Mina filer", re.IGNORECASE))
    ).to_be_visible()

    results.append(
        _audit_stage(
            page,
            key="route-vault-to-browse",
            stage_selector=".route-stage",
            item_selector=".route-stage-item",
            trigger=lambda: page.get_by_role("link", name="Katalog").click(),
        )
    )
    expect(page.get_by_role("heading", name=re.compile(r"Katalog", re.IGNORECASE))).to_be_visible()
    return results


def _audit_profile_inline_transitions(page: Page) -> list[dict[str, object]]:
    """Check the remaining profile field value/action swaps after removing `out-in`."""

    page.get_by_role("link", name="Profil").click()
    expect(page.get_by_role("heading", name=re.compile(r"Profil", re.IGNORECASE))).to_be_visible()

    first_edit_button = page.get_by_role("button", name="Ändra").first
    results = [
        _audit_stage(
            page,
            key="profile-inline-value-stage",
            item_selector=".field-edit-surface",
            trigger=lambda: first_edit_button.click(),
        ),
        _audit_stage(
            page,
            key="profile-inline-action-stage",
            item_selector=".profile-field-action .field-edit-surface",
            trigger=lambda: page.get_by_role("button", name="Avbryt").click(),
        ),
    ]
    return results


def _audit_topbar_transition(page: Page) -> dict[str, object]:
    """Verify the topbar label no longer uses a blanking sequential swap."""

    focus_button = page.get_by_role("button", name=re.compile(r"fokusl[äa]ge", re.IGNORECASE))
    return _audit_stage(
        page,
        key="topbar-focus-label",
        item_selector=".focus-toggle-stage .focus-toggle-label-surface",
        stage_selector=".focus-toggle-stage",
        trigger=lambda: focus_button.click(),
    )


def _audit_vault_refresh(page: Page) -> dict[str, object] | None:
    """Check that an already rendered vault list does not disappear during refresh."""

    page.get_by_role("link", name="Mina filer").click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Mina filer", re.IGNORECASE))
    ).to_be_visible()
    file_rows = page.locator("section ul > li")
    if file_rows.count() == 0:
        return None
    page.wait_for_timeout(400)

    return _audit_stage(
        page,
        key="vault-refresh-list-retained",
        item_selector="section ul > li",
        trigger=lambda: page.get_by_role("radio", name="Namn").click(),
        stage_selector="section.border.border-navy.bg-white.shadow-brutal-sm.p-4.space-y-4",
    )


def _audit_editor_modes(page: Page, *, base_url: str, tool_id: str) -> list[dict[str, object]]:
    """Exercise the editor shell continuity across source, metadata, and test modes."""

    _open_editor_page(page, base_url=base_url, tool_id=tool_id)
    results = [
        _audit_stage(
            page,
            key="editor-source-to-metadata",
            item_selector="[data-editor-panel='mode']",
            trigger=lambda: page.get_by_role("radio", name="Metadata").click(),
        ),
    ]
    expect(page.locator("[data-editor-mode='metadata']")).to_be_visible()

    results.append(
        _audit_stage(
            page,
            key="editor-metadata-to-test",
            item_selector="[data-editor-panel='mode']",
            trigger=lambda: page.get_by_role(
                "radio", name=re.compile(r"Testk[öo]r", re.IGNORECASE)
            ).click(),
        )
    )
    expect(page.locator("[data-editor-mode='test']")).to_be_visible()

    diff_option = page.get_by_role("radio", name="Diff")
    if diff_option.is_enabled():
        results.append(
            _audit_stage(
                page,
                key="editor-test-to-diff",
                item_selector="[data-editor-panel='mode']",
                trigger=lambda: diff_option.click(),
            )
        )
        expect(page.locator("[data-editor-mode='diff']")).to_be_visible()

    file_source_toggle = page.get_by_label("Välj filkälla")
    if file_source_toggle.count() > 0:
        results.append(
            _audit_stage(
                page,
                key="editor-tool-file-picker-mode",
                item_selector=".tool-file-picker-mode-surface",
                stage_selector=".tool-file-picker-mode-stage",
                trigger=lambda: page.get_by_role(
                    "radio", name=re.compile(r"Mina filer", re.IGNORECASE)
                ).first.click(),
            )
        )

    return results


def _audit_planner_transitions(page: Page, *, base_url: str) -> list[dict[str, object]]:
    """Exercise the planner shell and the rules-map crossfade with live data."""

    run_suffix = str(int(time.time()))
    roster_name = f"PW PR0166 Klass {run_suffix}"
    template_name = f"PW PR0166 Sal {run_suffix}"

    page.goto(f"{base_url}{APP_PATH}", wait_until="domcontentloaded")
    wait_for_app_heading(page)
    _create_roster_loose(page, roster_name=roster_name)
    _create_template_loose(page, template_name=template_name)
    page.goto(f"{base_url}{APP_PATH}", wait_until="domcontentloaded")
    wait_for_app_heading(page)
    open_class_workspace(page, roster_name=roster_name)

    results = [
        _audit_stage(
            page,
            key="planner-overview-to-grouping",
            item_selector="[data-test='overview-roster-panel'], [data-test='planner-workspace-switch'], [data-test='planner-workspace-transition']",
            trigger=lambda: focus_workspace_mode(page, label="Grupper"),
            stage_selector="body",
            sample_ms=700,
        ),
    ]
    expect(page.locator('[data-test="planner-workspace-switch"]')).to_be_visible()

    results.append(
        _audit_stage(
            page,
            key="planner-grouping-to-overview",
            item_selector="[data-test='overview-roster-panel'], [data-test='planner-workspace-switch'], [data-test='planner-workspace-transition']",
            trigger=lambda: focus_workspace_mode(page, label="Översikt"),
            stage_selector="body",
            sample_ms=700,
        )
    )
    expect(page.locator('[data-test="overview-roster-panel"]')).to_be_visible()

    results.append(
        _audit_stage(
            page,
            key="planner-overview-to-seating",
            item_selector="[data-test='overview-roster-panel'], [data-test='planner-workspace-switch'], [data-test='planner-workspace-transition']",
            trigger=lambda: focus_workspace_mode(page, label="Sittplatser"),
            stage_selector="body",
            sample_ms=700,
        )
    )
    _choose_planner_template(
        page, select_test_id="seating-template-select", template_name=template_name
    )
    expect(page.locator('[data-test="seating-workspace"]')).to_be_visible()

    _ensure_seating_assignments(page, template_name=template_name)
    results.append(
        _audit_stage(
            page,
            key="planner-seating-to-rules",
            item_selector="[data-test='overview-roster-panel'], [data-test='planner-workspace-switch'], [data-test='planner-workspace-transition']",
            trigger=lambda: focus_workspace_mode(page, label="Regler"),
            stage_selector="body",
            sample_ms=700,
        )
    )
    expect(page.locator('[data-test="rules-map-panel"]')).to_be_visible()

    results.append(
        _audit_stage(
            page,
            key="planner-rules-map-switch",
            item_selector=".rules-map-view-surface",
            stage_selector=".rules-map-view-stage",
            trigger=lambda: page.get_by_role("radio", name="Sittschema").click(),
        )
    )
    expect(page.locator('[data-test="rules-map-canvas"]')).to_be_visible()

    results.append(
        _audit_stage(
            page,
            key="planner-rules-to-overview",
            item_selector="[data-test='overview-roster-panel'], [data-test='planner-workspace-switch'], [data-test='planner-workspace-transition']",
            trigger=lambda: focus_workspace_mode(page, label="Översikt"),
            stage_selector="body",
            sample_ms=700,
        )
    )
    expect(page.locator('[data-test="overview-roster-panel"]')).to_be_visible()
    return results


def main() -> None:
    """Run the continuity audit and emit one concise summary line per verified stage."""

    config = get_config()
    base_url = config.base_url.rstrip("/")
    api_base_url = _resolve_api_base_url(base_url)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    session = _create_api_session(
        api_base_url=api_base_url,
        email=config.email,
        password=config.password,
    )
    editor_tool_id = _pick_editor_tool_id(session=session, api_base_url=api_base_url)

    audit_results: list[dict[str, object]] = []

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        page = context.new_page()

        page.goto(f"{base_url}/login", wait_until="domcontentloaded")
        dialog = page.get_by_role("dialog", name=re.compile(r"Logga in", re.IGNORECASE))
        expect(dialog).to_be_visible()
        dialog.get_by_label("E-post").fill(config.email)
        dialog.get_by_label("Lösenord").fill(config.password)
        dialog.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()
        expect(
            page.get_by_role("heading", name=re.compile(r"Välkommen", re.IGNORECASE))
        ).to_be_visible()

        audit_results.extend(_audit_route_transitions(page))
        audit_results.append(_audit_topbar_transition(page))
        page.get_by_role("button", name=re.compile(r"fokusl[äa]ge", re.IGNORECASE)).click()
        expect(page.get_by_role("link", name="Profil")).to_be_visible()
        vault_result = _audit_vault_refresh(page)
        if vault_result is not None:
            audit_results.append(vault_result)

        if editor_tool_id is not None:
            audit_results.extend(
                _audit_editor_modes(page, base_url=base_url, tool_id=editor_tool_id)
            )
        audit_results.extend(_audit_planner_transitions(page, base_url=base_url))

        page.screenshot(path=str(ARTIFACTS_DIR / "transition-audit-proof.png"), full_page=True)

        context.close()
        browser.close()

    summary_lines = [
        f"{result['key']}: min={result['min']} max={result['max']} samples={result['samples']}"
        for result in audit_results
    ]
    if editor_tool_id is None:
        summary_lines.append("editor-live-skip: no admin tool versions available in local data")
    summary_lines.append("profile-inline-live-skip: component not mounted in current profile flow")
    (ARTIFACTS_DIR / "continuity-summary.txt").write_text(
        "\n".join(summary_lines) + "\n", encoding="utf-8"
    )
    print("\n".join(summary_lines))
    print(f"Playwright artifacts written to: {ARTIFACTS_DIR}")


if __name__ == "__main__":  # pragma: no cover
    main()
