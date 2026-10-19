"""Playwright copy proof: exam workspace gap chips and kept words (TASK-SKRIPT-40-04 C2).

Captures a "Lucktext med rullista" (inline_choice) question with three
dropdown gaps (correct option, no correct option, no options) and a kept-gap
word with the gap tool on and off, in context for `ui-copy-reviewer`. Serves
this worktree's frontend on a free port (never 5173/5174) and drives it with
Playwright route interception; no backend runs. Signed-in states mock the
HuleEdu session, app continuation, CSRF and exam-workspace endpoints. Every
screenshot is API-mocked, not observed on a server. Reuses the C1 route and
launch helpers by import instead of copying them. Follows
`scripts/_playwright_browser.py` and the `python -m scripts.*` convention.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Page, sync_playwright

from scripts.playwright_exam_workspace_save_status_copy import (
    EVIDENCE_DIR,
    LINEAGE_ID,
    STATUS_SELECTOR,
    blank_document,
    blank_item,
    install_signed_in_routes,
    launch,
)

ITEM_EDITOR_SELECTOR = '[data-test="exam-workspace-item-editor"]'
GAP_TOOL_SELECTOR = '[data-test="exam-workspace-toolbar-gap-tool"]'

KEPT_TOOLTIP = "Har sparade svar för en lucka"


def option_body(text: str) -> list[dict[str, Any]]:
    return [
        {
            "heading_level": None,
            "segments": [{"kind": "text", "marks": [], "text": text, "kept_gap_id": None}],
        }
    ]


def dropdown_gap(gap_id: str, texts: list[str], correct_index: int | None) -> dict[str, Any]:
    return {
        "accepted_values": [],
        "automatic_values": [],
        "correct_option_id": (None if correct_index is None else f"choice_{correct_index + 1:03d}"),
        "excluded_automatic_values": [],
        "gap_id": gap_id,
        "options": [
            {"body": option_body(text), "choice_id": f"choice_{index + 1:03d}"}
            for index, text in enumerate(texts)
        ],
    }


def text_run(text: str, kept_gap_id: str | None = None) -> dict[str, Any]:
    return {"kind": "text", "marks": [], "text": text, "kept_gap_id": kept_gap_id}


def dropdown_item() -> dict[str, Any]:
    """An inline_choice question with one gap per dropdown state."""
    item = blank_item(1)
    item.update(
        {
            "kind": "inline_choice",
            "body": [
                {
                    "heading_level": None,
                    "segments": [
                        text_run("Välj rätt ord i varje lucka: "),
                        {"kind": "gap", "gap_id": "gap_001"},
                        text_run(" sedan "),
                        {"kind": "gap", "gap_id": "gap_002"},
                        text_run(" och till sist "),
                        {"kind": "gap", "gap_id": "gap_003"},
                        text_run("."),
                    ],
                }
            ],
            "gaps": [
                dropdown_gap("gap_001", ["R", "A", "B"], 1),
                dropdown_gap("gap_002", ["R", "A", "B"], None),
                dropdown_gap("gap_003", [], None),
            ],
        }
    )
    return item


def kept_item() -> dict[str, Any]:
    """A gap_fill question whose word keeps hidden answers for one gap."""
    item = blank_item(1)
    item.update(
        {
            "kind": "gap_fill",
            "body": [
                {
                    "heading_level": None,
                    "segments": [
                        text_run("Hon heter "),
                        text_run("Stockholm", "gap_003"),
                        text_run(" i "),
                        {"kind": "gap", "gap_id": "gap_001"},
                        text_run("."),
                    ],
                }
            ],
            "gaps": [
                {
                    "accepted_values": ["Sverige"],
                    "automatic_values": [],
                    "correct_option_id": None,
                    "excluded_automatic_values": [],
                    "gap_id": "gap_001",
                    "options": [],
                }
            ],
            "kept_gaps": [
                {
                    "accepted_values": ["Stockholm", "Sthlm"],
                    "automatic_values": [],
                    "correct_option_id": None,
                    "excluded_automatic_values": [],
                    "gap_id": "gap_003",
                    "options": [],
                }
            ],
        }
    )
    return item


def open_signed_in(page: Page, base_url: str, document: dict[str, Any]) -> None:
    install_signed_in_routes(page, {"document": document, "mode": "ok"})
    page.goto(f"{base_url}/apps/exam-workspace?document={LINEAGE_ID}")
    page.wait_for_selector(STATUS_SELECTOR, timeout=30000)
    page.wait_for_selector(ITEM_EDITOR_SELECTOR, timeout=30000)
    page.wait_for_timeout(2500)


def report(name: str, detail: str, path: Path) -> None:
    size = path.stat().st_size
    print(f"{name}: {detail} file={path.name} bytes={size}")


def chip_state(page: Page, gap_id: str) -> tuple[str | None, str | None]:
    chip = page.locator(f'.xw-gap[data-gap-id="{gap_id}"]')
    return chip.get_attribute("data-label"), chip.get_attribute("aria-label")


def scenario_dropdowns(browser: Browser, base_url: str) -> None:
    document = blank_document()
    document["items"] = [dropdown_item()]
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    open_signed_in(page, base_url, document)
    for gap_id, name in [
        ("gap_001", "gap-dropdown-correct"),
        ("gap_002", "gap-dropdown-no-correct"),
        ("gap_003", "gap-dropdown-no-options"),
    ]:
        chip = page.locator(f'.xw-gap[data-gap-id="{gap_id}"]')
        chip.wait_for(timeout=30000)
        chip.scroll_into_view_if_needed()
        page.wait_for_timeout(400)
        path = EVIDENCE_DIR / f"{name}.png"
        page.screenshot(path=path)
        label, accessible = chip_state(page, gap_id)
        report(name, f"label={label!r} aria-label={accessible!r}", path)
    context.close()


def scenario_kept(browser: Browser, base_url: str) -> None:
    document = blank_document()
    document["items"] = [kept_item()]
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    open_signed_in(page, base_url, document)
    tool = page.locator(f"{ITEM_EDITOR_SELECTOR} {GAP_TOOL_SELECTOR}").first
    tool.click()
    kept = page.locator(".xw-kept-gap")
    kept.wait_for(timeout=30000)
    kept.scroll_into_view_if_needed()
    kept.hover()
    page.wait_for_timeout(400)
    path = EVIDENCE_DIR / "kept-gap-word.png"
    page.screenshot(path=path)
    report(
        "kept-gap-word",
        f"text={kept.inner_text()!r} title={kept.get_attribute('title')!r} "
        f"class={kept.get_attribute('class')!r}",
        path,
    )
    tool.click()
    page.wait_for_selector(".xw-kept-gap", state="detached", timeout=30000)
    page.wait_for_timeout(400)
    path = EVIDENCE_DIR / "kept-gap-word-tool-off.png"
    page.screenshot(path=path)
    report("kept-gap-word-tool-off", "tool off, decoration gone", path)
    context.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vite-port", type=int, default=5181)
    parser.add_argument(
        "--scenarios",
        default="dropdowns,kept",
        help="Comma-separated subset of dropdowns,kept",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    base_url = f"http://127.0.0.1:{args.vite_port}"
    selected = {name.strip() for name in args.scenarios.split(",")}
    with sync_playwright() as playwright:
        playwright.selectors.set_test_id_attribute("data-test")
        browser = launch(playwright)
        try:
            if "dropdowns" in selected:
                scenario_dropdowns(browser, base_url)
            if "kept" in selected:
                scenario_kept(browser, base_url)
        finally:
            browser.close()
    print("done")


if __name__ == "__main__":
    main()
