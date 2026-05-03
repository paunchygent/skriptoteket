"""Generate PR-0279 shared-link seating label typography proof artifacts.

Purpose:
    Render a static Klassrumskartan seating share page with short, long,
    hyphenated, and extreme student labels, then capture desktop, mobile, and
    1200x630 preview screenshots plus layout assertions.

Relationships:
    - Exercises `StaticClassroomPlannerShareRenderer` and the production
      preview-fit CSS used by `share_preview_renderer.py`.
    - Writes review artifacts under
      `.artifacts/pr-0279-share-label-typography/`.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    PosterSceneFixture,
    PosterSceneFixtureKind,
    PosterSceneFixturePlacement,
    PosterSceneRoom,
    PosterSceneSeat,
    PosterSceneWallSide,
    PreparedSeatingExportContract,
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingPosterScene,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.share_preview_renderer import (
    _with_preview_fit_css,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.share_renderer import (
    StaticClassroomPlannerShareRenderer,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / ".artifacts/pr-0279-share-label-typography"


def main() -> None:
    """Run the PR-0279 screenshot and layout proof."""

    run_dir = OUTPUT_ROOT / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir.mkdir(parents=True, exist_ok=True)
    prepared = _prepared_export()
    rendered = StaticClassroomPlannerShareRenderer().render_seating(prepared_export=prepared)
    share_html = rendered.rendered_html
    preview_html = _with_preview_fit_css(share_html)
    (run_dir / "share-page.html").write_text(share_html, encoding="utf-8")

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        try:
            desktop = _capture_and_assert(
                browser=browser,
                html=share_html,
                output_path=run_dir / "desktop.png",
                viewport={"width": 1440, "height": 900},
            )
            mobile = _capture_and_assert(
                browser=browser,
                html=share_html,
                output_path=run_dir / "mobile.png",
                viewport={"width": 390, "height": 844},
            )
            preview = _capture_and_assert(
                browser=browser,
                html=preview_html,
                output_path=run_dir / "preview-1200x630.png",
                viewport={"width": 1200, "height": 630},
            )
        finally:
            browser.close()

    proof = {
        "renderer_version": rendered.renderer_version,
        "screenshots": {
            "desktop": str(run_dir / "desktop.png"),
            "mobile": str(run_dir / "mobile.png"),
            "preview_1200x630": str(run_dir / "preview-1200x630.png"),
        },
        "layout": {
            "desktop": desktop,
            "mobile": mobile,
            "preview_1200x630": preview,
        },
    }
    (run_dir / "proof.json").write_text(
        json.dumps(proof, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"pr-0279-proof: ok {run_dir}")


def _capture_and_assert(
    *,
    browser: Any,
    html: str,
    output_path: Path,
    viewport: dict[str, int],
) -> dict[str, object]:
    page = browser.new_page(viewport=viewport)
    page.set_content(html, wait_until="load")
    checks = page.evaluate(
        """() => {
            const tokenRects = [...document.querySelectorAll('.room-seat__token')]
              .map((token) => {
                const rect = token.getBoundingClientRect();
                return {
                  left: rect.left,
                  top: rect.top,
                  right: rect.right,
                  bottom: rect.bottom,
                  width: rect.width,
                  height: rect.height,
                };
              });
            const lineChecks = [...document.querySelectorAll('.room-seat:not(.room-seat--empty)')]
              .map((seat) => {
                const token = seat.querySelector('.room-seat__token').getBoundingClientRect();
                const isFallback = seat.classList.contains('room-seat--name-fallback');
                const lines = [...seat.querySelectorAll('.room-seat__name-line')]
                  .map((line) => {
                    const rect = line.getBoundingClientRect();
                    const text = line.textContent ?? '';
                    return {
                      text,
                      left: rect.left,
                      top: rect.top,
                      right: rect.right,
                      bottom: rect.bottom,
                      width: rect.width,
                      clientWidth: line.clientWidth,
                      scrollWidth: line.scrollWidth,
                      textOverflow: getComputedStyle(line).textOverflow,
                    };
                  });
                const visibleLines = lines.filter((line) => line.text.trim().length > 0);
                const visibleText = visibleLines.map((line) => line.text.trim()).join(' ');
                const title = seat.getAttribute('title') ?? '';
                const ariaLabel = seat.getAttribute('aria-label') ?? '';
                return {
                  title,
                  ariaLabel,
                  classes: seat.className,
                  isFallback,
                  lines,
                  visibleText,
                  contained: visibleLines.every((line) =>
                    line.left >= token.left - 1 &&
                    line.right <= token.right + 1 &&
                    line.top >= token.top - 1 &&
                    line.bottom <= token.bottom + 1
                  ),
                  separated: visibleLines.length < 2 || visibleLines[0].bottom <= visibleLines[1].top + 0.5,
                  noHiddenClip: visibleLines.every((line) => line.scrollWidth <= line.clientWidth + 1),
                  visibleLinesNotEmpty: lines.length > 0 && lines.every((line) => line.text.trim().length > 0),
                  noEllipsis: lines.every((line) =>
                    line.textOverflow !== 'ellipsis' &&
                    !line.text.includes('...') &&
                    line.text !== '…'
                  ),
                  fallbackPreservesFullLabel: !isFallback || (
                    title.length > 0 &&
                    ariaLabel === title &&
                    visibleText.length > 0 &&
                    visibleText !== title
                  ),
                };
              });
            const overlaps = [];
            for (let i = 0; i < tokenRects.length; i += 1) {
              for (let j = i + 1; j < tokenRects.length; j += 1) {
                const a = tokenRects[i];
                const b = tokenRects[j];
                const separated = a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top;
                if (!separated) {
                  overlaps.push([i, j]);
                }
              }
            }
            return { lineChecks, overlaps, tokenCount: tokenRects.length };
        }"""
    )
    failures = [
        check
        for check in checks["lineChecks"]
        if not (
            check["contained"]
            and check["separated"]
            and check["noHiddenClip"]
            and check["visibleLinesNotEmpty"]
            and check["noEllipsis"]
            and check["fallbackPreservesFullLabel"]
        )
    ]
    if failures:
        raise AssertionError(f"Seat label layout failures: {failures}")
    if checks["overlaps"]:
        raise AssertionError(f"Seat token overlap detected: {checks['overlaps']}")
    page.screenshot(path=str(output_path), full_page=False)
    page.close()
    return checks


def _prepared_export() -> PreparedSeatingExportContract:
    return PreparedSeatingExportContract(
        seating_draft_id=uuid4(),
        roster_id=uuid4(),
        roster_name="PR-0279 long-name proof",
        template_id=uuid4(),
        template_name="Sal G20",
        export_kind=SeatingExportKind.PDF,
        layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        poster_scene=SeatingPosterScene(
            room=PosterSceneRoom(grid_cols=7, grid_rows=4),
            seats=[
                PosterSceneSeat(seat_id="seat-1", x=0, y=1, label="Moa Ek"),
                PosterSceneSeat(seat_id="seat-2", x=1, y=1, label="KristofferJonatan Lo"),
                PosterSceneSeat(seat_id="seat-3", x=2, y=1, label="Alexanderthegreat"),
                PosterSceneSeat(
                    seat_id="seat-4",
                    x=3,
                    y=1,
                    label="WWWWWWWWWWWWWWWWWW Wide",
                ),
                PosterSceneSeat(
                    seat_id="seat-5",
                    x=4,
                    y=1,
                    label="Anna-Karin Schwerin",
                ),
                PosterSceneSeat(
                    seat_id="seat-6",
                    x=5,
                    y=1,
                    label="Otilia Olofsson-Reijer",
                ),
                PosterSceneSeat(
                    seat_id="seat-7",
                    x=0,
                    y=2,
                    label="Margareta Alexandersson",
                ),
                PosterSceneSeat(
                    seat_id="seat-8",
                    x=1,
                    y=2,
                    label="Supercalifragilisticexpialidocious Berg",
                ),
                PosterSceneSeat(seat_id="seat-9", x=2, y=2, label="Maximilian Lundqvistberg"),
                PosterSceneSeat(seat_id="seat-10", x=3, y=2, label="Katarina Svensson"),
                PosterSceneSeat(seat_id="seat-11", x=4, y=2, label="Alexandra Olofsson-Reijer"),
            ],
            fixtures=[
                PosterSceneFixture(
                    fixture_id="whiteboard-top",
                    kind=PosterSceneFixtureKind.WHITEBOARD,
                    x=1,
                    y=0,
                    width=4,
                    height=1,
                    placement=PosterSceneFixturePlacement.WALL,
                    wall_side=PosterSceneWallSide.TOP,
                    label="Whiteboard",
                ),
                PosterSceneFixture(
                    fixture_id="bench-middle",
                    kind=PosterSceneFixtureKind.BENCH,
                    x=0,
                    y=0,
                    width=5,
                    height=1,
                    placement=PosterSceneFixturePlacement.FLOOR,
                    label="Bänk",
                ),
            ],
        ),
    )


def _find_chromium_headless_shell() -> str | None:
    root = Path.home() / "Library" / "Caches" / "ms-playwright"
    if not root.exists():
        return None
    candidates = sorted(root.glob("chromium_headless_shell-*"), reverse=True)
    for candidate in candidates:
        for subdir in ("chrome-headless-shell-mac-arm64", "chrome-headless-shell-mac-x64"):
            binary = candidate / subdir / "chrome-headless-shell"
            if binary.is_file():
                return str(binary)
    return None


def _launch_chromium(playwright: Any) -> Any:
    try:
        return playwright.chromium.launch(headless=True)
    except PlaywrightError:
        executable_path = _find_chromium_headless_shell()
        if executable_path is None:
            raise
        return playwright.chromium.launch(headless=True, executable_path=executable_path)


if __name__ == "__main__":
    main()
