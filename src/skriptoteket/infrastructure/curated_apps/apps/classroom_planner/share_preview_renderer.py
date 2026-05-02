"""Playwright PNG renderer for Klassrumskartan share-preview thumbnails.

Purpose:
    Convert the already-rendered immutable share HTML/CSS artifact into the
    1200x630 PNG used by Teams and other social unfurlers.

Relationships:
    - Implements `ClassroomPlannerSharePreviewRendererProtocol`.
    - Consumed by share creation and backfill application handlers.
    - Does not call SPA routes, owner-scoped APIs, cookies, or browser session
      state; it renders only the stored share artifact HTML.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright

from skriptoteket.application.curated_apps.classroom_planner.shares import (
    SHARE_PREVIEW_HEIGHT,
    SHARE_PREVIEW_WIDTH,
    ClassroomPlannerShareArtifact,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.classroom_planner_shares import (
    ClassroomPlannerSharePreviewRendererProtocol,
)


@dataclass(frozen=True, slots=True)
class ClassroomPlannerSharePreviewRendererSettings:
    """Configure Playwright thumbnail runtime limits."""

    timeout_seconds: float = 8.0
    max_concurrency: int = 2


class PlaywrightClassroomPlannerSharePreviewRenderer(ClassroomPlannerSharePreviewRendererProtocol):
    """Render Klassrumskartan share artifacts into PNG preview bytes."""

    def __init__(self, *, settings: ClassroomPlannerSharePreviewRendererSettings) -> None:
        self._settings = settings
        self._semaphore = asyncio.Semaphore(settings.max_concurrency)

    async def render_png(
        self,
        *,
        artifact: ClassroomPlannerShareArtifact,
    ) -> bytes:
        async with self._semaphore:
            try:
                return await asyncio.wait_for(
                    self._render_png(artifact=artifact),
                    timeout=self._settings.timeout_seconds,
                )
            except TimeoutError as exc:
                raise _preview_generation_error("classroom_share_preview_timeout") from exc
            except PlaywrightError as exc:
                raise _preview_generation_error("classroom_share_preview_playwright_error") from exc

    async def _render_png(self, *, artifact: ClassroomPlannerShareArtifact) -> bytes:
        html = _with_preview_fit_css(artifact.rendered_html)
        timeout_ms = int(self._settings.timeout_seconds * 1000)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                context = await browser.new_context(
                    viewport={"width": SHARE_PREVIEW_WIDTH, "height": SHARE_PREVIEW_HEIGHT},
                    device_scale_factor=1,
                    java_script_enabled=True,
                )
                page = await context.new_page()
                page.set_default_timeout(timeout_ms)
                await page.set_content(html, wait_until="load", timeout=timeout_ms)
                await page.evaluate(
                    """() => {
                        const page = document.querySelector('.share-page');
                        if (!page) {
                            return;
                        }
                        const widthScale = 1200 / Math.max(page.scrollWidth, 1);
                        const heightScale = 630 / Math.max(page.scrollHeight, 1);
                        const scale = Math.min(widthScale, heightScale, 1);
                        page.style.transform = `scale(${scale})`;
                    }"""
                )
                return await page.screenshot(
                    type="png",
                    full_page=False,
                    timeout=timeout_ms,
                )
            finally:
                await browser.close()


def _with_preview_fit_css(rendered_html: str) -> str:
    """Inject screenshot-only fitting CSS into the persisted share document."""

    fit_css = f"""
<style data-skriptoteket-share-preview-fit="owned">
html,
body {{
  background: #fafaf6;
  height: {SHARE_PREVIEW_HEIGHT}px;
  margin: 0;
  overflow: hidden;
  width: {SHARE_PREVIEW_WIDTH}px;
}}
body {{
  align-items: flex-start;
  display: flex;
  justify-content: center;
}}
.share-page {{
  max-width: none !important;
  padding: 24px !important;
  transform-origin: top center;
  width: {SHARE_PREVIEW_WIDTH}px !important;
}}
.share-page--seating {{
  width: min(1440px, {SHARE_PREVIEW_WIDTH}px) !important;
}}
.share-actions {{
  display: none !important;
}}
.share-header {{
  margin-bottom: 14px !important;
}}
.share-title {{
  font-size: 32px !important;
  line-height: 1.08 !important;
}}
.share-created,
.share-subtitle {{
  font-size: 14px !important;
}}
.room-frame,
.groups-grid {{
  box-shadow: none !important;
}}
.room-viewport {{
  overflow: visible !important;
}}
</style>
""".strip()
    return rendered_html.replace("</head>", f"{fit_css}\n</head>", 1)


def _preview_generation_error(reason_code: str) -> DomainError:
    return DomainError(
        code=ErrorCode.SERVICE_UNAVAILABLE,
        message="Could not generate Klassrumskartan share preview image.",
        details={"reason_code": reason_code},
    )
