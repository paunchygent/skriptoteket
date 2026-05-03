"""Generate PR-0282 shared-link PDF download handoff proof artifacts.

Purpose:
    Render real static Klassrumskartan grouping and seating share pages, click
    the owned `Ladda ner PDF` action, and prove the browser-handoff guard
    returns the action to idle after Playwright observes a download event.

Relationships:
    - Exercises `StaticClassroomPlannerShareRenderer` and share chrome
      finalization without introducing a live API, Vue hydration, or polling.
    - Writes review artifacts under
      `.artifacts/pr-0282-share-pdf-download-handoff/`.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from playwright.sync_api import Browser, Download, Page, Route, sync_playwright

from scripts._playwright_browser import launch_chromium
from skriptoteket.application.curated_apps.classroom_planner.exports import (
    GroupingExportKind,
    GroupingExportPaperSize,
    GroupingExportPresentation,
    GroupingPresentationGroup,
    GroupingPresentationMember,
    PosterSceneRoom,
    PosterSceneSeat,
    PreparedGroupingExportContract,
    PreparedSeatingExportContract,
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingPosterScene,
)
from skriptoteket.application.curated_apps.classroom_planner.shares import (
    finalize_share_rendered_html,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.share_renderer import (
    StaticClassroomPlannerShareRenderer,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / ".artifacts/pr-0282-share-pdf-download-handoff"
PDF_BYTES = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF\n"
PDF_ROUTE_PATTERN = "**/share/classroom/*/download.pdf"


def main() -> None:
    """Run the PR-0282 browser-handoff proof."""

    run_dir = OUTPUT_ROOT / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir.mkdir(parents=True, exist_ok=False)
    cases = {
        "grouping_desktop": _build_case(
            html=_render_grouping_html(),
            width=1200,
            height=800,
            route="/proof/grouping-desktop",
        ),
        "grouping_mobile": _build_case(
            html=_render_grouping_html(),
            width=390,
            height=760,
            route="/proof/grouping-mobile",
        ),
        "seating_desktop": _build_case(
            html=_render_seating_html(),
            width=1200,
            height=800,
            route="/proof/seating-desktop",
        ),
        "seating_mobile": _build_case(
            html=_render_seating_html(),
            width=390,
            height=760,
            route="/proof/seating-mobile",
        ),
    }

    proof: dict[str, object] = {}
    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        try:
            for case_id, case in cases.items():
                proof[case_id] = _run_case(browser=browser, output_dir=run_dir, **case)
        finally:
            browser.close()

    manifest_path = run_dir / "proof.json"
    manifest_path.write_text(
        json.dumps(proof, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"pr-0282-download-handoff-proof: ok artifacts={run_dir}")


def _build_case(*, html: str, width: int, height: int, route: str) -> dict[str, Any]:
    return {
        "html": html,
        "width": width,
        "height": height,
        "route": route,
    }


def _run_case(
    *,
    browser: Browser,
    output_dir: Path,
    html: str,
    width: int,
    height: int,
    route: str,
) -> dict[str, object]:
    context = browser.new_context(
        accept_downloads=True, viewport={"width": width, "height": height}
    )
    page = context.new_page()
    downloads: list[Download] = []
    page.on("download", lambda download: downloads.append(download))
    url = f"http://skriptoteket-pr-0282.local{route}"
    page.route(f"**{route}", lambda routed: _fulfill_html(routed, html))
    page.route(PDF_ROUTE_PATTERN, _fulfill_pdf)

    try:
        page.goto(url, wait_until="load")
        action = page.locator('[data-skriptoteket-share-pdf-download="owned"]')
        action.wait_for(state="visible")
        idle_rect = _rect(page)
        idle_details = _details(page)
        idle_path = output_dir / f"{route.strip('/').replace('/', '-')}-idle.png"
        page.screenshot(path=idle_path)

        with page.expect_download() as download_info:
            action.click(no_wait_after=True)
            page.wait_for_function(
                """() => {
                  const action = document.querySelector(
                    '[data-skriptoteket-share-pdf-download="owned"]'
                  );
                  return action?.getAttribute('data-skriptoteket-share-pdf-download-state') === 'busy'
                    && !action.hasAttribute('href');
                }""",
                timeout=1000,
            )
            busy_rect = _rect(page)
            busy_details = _details(page)
            busy_path = output_dir / f"{route.strip('/').replace('/', '-')}-busy.png"
            page.screenshot(path=busy_path)

            action.click()
            action.press("Enter")
            page.wait_for_timeout(250)
        download = download_info.value
        _wait_for_downloads(page=page, downloads=downloads, expected_count=1)
        duplicate_event_count = len(downloads)

        page.wait_for_function(
            """() => {
              const action = document.querySelector(
                '[data-skriptoteket-share-pdf-download="owned"]'
              );
              return action?.getAttribute('data-skriptoteket-share-pdf-download-state') === 'idle'
                && action.hasAttribute('href')
                && !action.hasAttribute('aria-busy')
                && !action.hasAttribute('aria-disabled');
            }""",
            timeout=2500,
        )
        recovered_rect = _rect(page)
        recovered_details = _details(page)
        recovered_path = output_dir / f"{route.strip('/').replace('/', '-')}-recovered.png"
        page.screenshot(path=recovered_path)

        if duplicate_event_count != 1:
            raise AssertionError(
                f"Expected one download event during guard, got {duplicate_event_count}."
            )
        _assert_stable_geometry(idle_rect, busy_rect, recovered_rect)
        _assert_busy_details(busy_details)
        _assert_recovered_details(recovered_details)

        return {
            "download_event_count_after_duplicate_attempts": duplicate_event_count,
            "download_filename": download.suggested_filename,
            "idle_details": idle_details,
            "busy_details": busy_details,
            "recovered_details": recovered_details,
            "idle_rect": idle_rect,
            "busy_rect": busy_rect,
            "recovered_rect": recovered_rect,
            "screenshots": {
                "idle": str(idle_path.relative_to(REPO_ROOT)),
                "busy": str(busy_path.relative_to(REPO_ROOT)),
                "recovered": str(recovered_path.relative_to(REPO_ROOT)),
            },
        }
    finally:
        context.close()


def _fulfill_html(route: Route, html: str) -> None:
    route.fulfill(status=200, content_type="text/html; charset=utf-8", body=html)


def _fulfill_pdf(route: Route) -> None:
    route.fulfill(
        status=200,
        headers={
            "content-type": "application/pdf",
            "content-disposition": 'attachment; filename="klassrumskartan-proof.pdf"',
        },
        body=PDF_BYTES,
    )


def _wait_for_downloads(*, page: Page, downloads: list[Download], expected_count: int) -> None:
    for _ in range(40):
        if len(downloads) >= expected_count:
            return
        page.wait_for_timeout(50)
    raise AssertionError(f"Expected {expected_count} download event, got {len(downloads)}.")


def _rect(page: Page) -> dict[str, float]:
    rect = page.locator('[data-skriptoteket-share-pdf-download="owned"]').bounding_box()
    if rect is None:
        raise AssertionError("PDF download action is not visible.")
    return {key: float(rect[key]) for key in ("x", "y", "width", "height")}


def _details(page: Page) -> dict[str, object]:
    details = page.evaluate(
        """() => {
          const action = document.querySelector('[data-skriptoteket-share-pdf-download="owned"]');
          const spinner = document.querySelector('.share-download-pdf__spinner');
          if (!(action instanceof HTMLAnchorElement) || !(spinner instanceof HTMLElement)) {
            throw new Error('Missing PDF download action or spinner.');
          }
          const spinnerStyle = window.getComputedStyle(spinner);
          return {
            state: action.getAttribute('data-skriptoteket-share-pdf-download-state'),
            ariaBusy: action.getAttribute('aria-busy'),
            ariaDisabled: action.getAttribute('aria-disabled'),
            ariaLabel: action.getAttribute('aria-label'),
            href: action.getAttribute('href'),
            cursor: window.getComputedStyle(action).cursor,
            spinnerVisible: spinnerStyle.visibility === 'visible' && spinnerStyle.opacity !== '0',
          };
        }"""
    )
    if not isinstance(details, dict):
        raise AssertionError("Expected browser details object.")
    return details


def _assert_stable_geometry(*rects: dict[str, float]) -> None:
    baseline = rects[0]
    for rect in rects[1:]:
        for key in ("x", "width"):
            if abs(rect[key] - baseline[key]) > 0.5:
                raise AssertionError(f"Action {key} changed from {baseline[key]} to {rect[key]}.")


def _assert_busy_details(details: dict[str, object]) -> None:
    expected = {
        "state": "busy",
        "ariaBusy": "true",
        "ariaDisabled": "true",
        "ariaLabel": "Förbereder PDF",
        "href": None,
        "cursor": "progress",
        "spinnerVisible": True,
    }
    if details != expected:
        raise AssertionError(f"Unexpected busy details: {details!r}")


def _assert_recovered_details(details: dict[str, object]) -> None:
    if details["state"] != "idle":
        raise AssertionError(f"Expected idle recovery, got {details!r}")
    for attr in ("ariaBusy", "ariaDisabled"):
        if details[attr] is not None:
            raise AssertionError(f"Expected cleared {attr}, got {details!r}")
    if not isinstance(details["href"], str) or not details["href"].endswith("/download.pdf"):
        raise AssertionError(f"Expected restored PDF href, got {details!r}")
    if details["spinnerVisible"] is not False:
        raise AssertionError(f"Expected hidden spinner after recovery, got {details!r}")


def _render_grouping_html() -> str:
    rendered = StaticClassroomPlannerShareRenderer().render_grouping(
        prepared_export=PreparedGroupingExportContract(
            grouping_draft_id=uuid4(),
            roster_id=uuid4(),
            export_kind=GroupingExportKind.PDF,
            paper_size=GroupingExportPaperSize.A4_PORTRAIT,
            presentation=GroupingExportPresentation(
                draft_id=uuid4(),
                class_name="Klass 7A",
                title="Gruppindelning",
                filename_stem="klass-7a-gruppindelning",
                groups=(
                    GroupingPresentationGroup(
                        group_label="Grupp 1",
                        group_order=0,
                        members=(
                            GroupingPresentationMember(member_order=1, display_name="Ada Alm"),
                            GroupingPresentationMember(member_order=2, display_name="Bo Berg"),
                        ),
                    ),
                ),
            ),
        )
    )
    return _finalize_html(rendered.rendered_html)


def _render_seating_html() -> str:
    rendered = StaticClassroomPlannerShareRenderer().render_seating(
        prepared_export=PreparedSeatingExportContract(
            seating_draft_id=uuid4(),
            roster_id=uuid4(),
            roster_name="Klass 7A",
            template_id=uuid4(),
            template_name="Sal 204",
            export_kind=SeatingExportKind.PDF,
            layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
            poster_scene=SeatingPosterScene(
                room=PosterSceneRoom(grid_cols=4, grid_rows=3),
                seats=[
                    PosterSceneSeat(seat_id="seat-1", x=0, y=1, student_id="s1", label="Ada Alm"),
                    PosterSceneSeat(seat_id="seat-2", x=1, y=1, student_id="s2", label="Bo Berg"),
                    PosterSceneSeat(seat_id="seat-3", x=2, y=1),
                ],
                fixtures=[],
            ),
        )
    )
    return _finalize_html(rendered.rendered_html)


def _finalize_html(rendered_html: str) -> str:
    return finalize_share_rendered_html(
        rendered_html=rendered_html,
        created_at=datetime(2026, 5, 3, tzinfo=timezone.utc),
        pdf_download_path="/share/classroom/pr-0282-proof-token/download.pdf",
    )


if __name__ == "__main__":
    main()
