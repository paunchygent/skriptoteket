"""Static HTML renderer for Klassrumskartan share artifacts.

Purpose:
    Render immutable share-link HTML/CSS from canonical grouping and seating
    presentation contracts produced by the backend export preparation path.

Relationships:
    - Implements `ClassroomPlannerShareRendererProtocol`.
    - Consumed by authenticated share application handlers.
    - Persists no browser-supplied HTML, CSS, or metadata.
"""

from __future__ import annotations

import html
import json

from pydantic import BaseModel

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    PreparedGroupingExportContract,
    PreparedSeatingExportContract,
)
from skriptoteket.application.curated_apps.classroom_planner.shares import (
    CLASSROOM_PLANNER_PUBLIC_APP_PATH,
    SHARE_CREATED_DATE_CHROME_SLOT,
    SHARE_PDF_DOWNLOAD_HREF_CHROME_SLOT,
    JsonObject,
    JsonValue,
    RenderedClassroomPlannerShare,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.share_group_renderer import (
    GROUPING_SHARE_CSS,
    render_grouping_share_body,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.share_scene_renderer import (
    SEATING_SHARE_CSS,
    render_seating_scene_body,
)
from skriptoteket.protocols.classroom_planner_shares import (
    ClassroomPlannerShareRendererProtocol,
)

_RENDERER_VERSION = "klassrumskartan-share-renderer-v1"
_GROUPING_SCHEMA_VERSION = "grouping-share-v1"
_SEATING_SCHEMA_VERSION = "seating-share-v1"

_SHARE_CSS = (
    """
:root {
  color-scheme: light;
  --canvas: #fafaf6;
  --navy: #1c2e4a;
  --navy-05: rgba(28, 46, 74, 0.05);
  --navy-10: rgba(28, 46, 74, 0.10);
  --navy-15: rgba(28, 46, 74, 0.15);
  --navy-20: rgba(28, 46, 74, 0.20);
  --navy-30: rgba(28, 46, 74, 0.30);
  --navy-40: rgba(28, 46, 74, 0.40);
  --navy-50: rgba(28, 46, 74, 0.50);
  --navy-60: rgba(28, 46, 74, 0.60);
  --navy-70: rgba(28, 46, 74, 0.70);
  --font-sans: "IBM Plex Sans", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
    sans-serif;
  --font-serif: "IBM Plex Serif", Georgia, "Times New Roman", serif;
  --font-mono: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
    "Liberation Mono", "Courier New", monospace;
  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.125rem;
  --text-3xl: 2rem;
  --text-4xl: 2.5rem;
  --tracking-label: 0.08em;
  --tracking-wide: 0.10em;
  background: var(--canvas);
  color: var(--navy);
  font-family: var(--font-sans);
}
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}
body {
  margin: 0;
  background: var(--canvas);
  min-height: 100vh;
}
.share-page {
  margin: 0 auto;
  max-width: 1200px;
  padding: 32px 20px 48px;
}
.share-page--seating {
  max-width: 1440px;
}
.share-header {
  align-items: flex-start;
  display: flex;
  gap: 24px;
  justify-content: space-between;
  margin-bottom: 22px;
}
.share-header__main {
  min-width: 0;
}
.share-kicker {
  color: var(--navy-60);
  font-size: var(--text-xs);
  font-weight: 700;
  letter-spacing: var(--tracking-wide);
  margin-bottom: 8px;
  text-transform: uppercase;
}
.share-title {
  font-family: var(--font-serif);
  font-size: var(--text-3xl);
  font-weight: 600;
  letter-spacing: 0;
  line-height: 1.15;
  margin: 0 0 10px;
}
.share-created {
  color: var(--navy-60);
  font-size: var(--text-sm);
  font-weight: 500;
  line-height: 1.4;
  margin: 0;
}
.share-actions {
  align-items: flex-end;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 8px;
}
.share-download-pdf,
.share-origin-link {
  color: var(--navy);
  text-decoration: none;
  white-space: nowrap;
}
.share-download-pdf {
  border: 1px solid var(--navy);
  font-size: var(--text-sm);
  font-weight: 700;
  line-height: 1;
  padding: 10px 12px;
}
.share-origin-link {
  border-bottom: 1px solid currentColor;
  color: var(--navy);
  font-size: var(--text-xs);
  font-weight: 600;
  padding-bottom: 2px;
}
@media (min-width: 768px) {
  .share-page {
    padding: 40px 32px 56px;
  }
  .share-title {
    font-size: var(--text-4xl);
  }
}
@media (max-width: 767px) {
  .share-page {
    padding: 18px 12px 28px;
  }
  .share-header {
    flex-direction: column;
    gap: 12px;
  }
  .share-title {
    font-size: clamp(1.6rem, 8vw, 2.2rem);
  }
  .share-actions {
    align-items: flex-start;
    flex-direction: row;
    flex-wrap: wrap;
    padding-top: 0;
  }
}
@media print {
  body {
    background: #fff;
  }
  .share-page {
    max-width: none;
    padding: 0;
  }
  .share-actions {
    display: none;
  }
}
""".strip()
    + "\n"
    + GROUPING_SHARE_CSS
    + "\n"
    + SEATING_SHARE_CSS
)


class StaticClassroomPlannerShareRenderer(ClassroomPlannerShareRendererProtocol):
    """Render share pages from canonical backend presentation models."""

    def render_grouping(
        self,
        *,
        prepared_export: PreparedGroupingExportContract,
    ) -> RenderedClassroomPlannerShare:
        presentation = prepared_export.presentation
        title = f"{presentation.class_name} – {presentation.title}"
        description = f"Gruppindelning för {presentation.class_name}."
        body = "\n".join(
            [
                _share_header(title=title, subtitle=None),
                render_grouping_share_body(presentation=presentation),
            ]
        )
        return RenderedClassroomPlannerShare(
            title=title,
            preview_description=description,
            renderer_version=_RENDERER_VERSION,
            presentation_schema_version=_GROUPING_SCHEMA_VERSION,
            presentation_payload=_json_object(presentation),
            rendered_html=_document(
                title=title,
                description=description,
                body=body,
                page_modifier="share-page--grouping",
            ),
            rendered_css=_SHARE_CSS,
        )

    def render_seating(
        self,
        *,
        prepared_export: PreparedSeatingExportContract,
    ) -> RenderedClassroomPlannerShare:
        title = f"{prepared_export.roster_name} - Sittschema"
        description = (
            f"Sittschema för {prepared_export.roster_name} i {prepared_export.template_name}."
        )
        body = "\n".join(
            [
                _share_header(title=title, subtitle=prepared_export.template_name),
                render_seating_scene_body(prepared_export=prepared_export),
            ]
        )
        return RenderedClassroomPlannerShare(
            title=title,
            preview_description=description,
            renderer_version=_RENDERER_VERSION,
            presentation_schema_version=_SEATING_SCHEMA_VERSION,
            presentation_payload=_json_object(prepared_export),
            rendered_html=_document(
                title=title,
                description=description,
                body=body,
                page_modifier="share-page--seating",
            ),
            rendered_css=_SHARE_CSS,
        )


def _document(
    *,
    title: str,
    description: str,
    body: str,
    page_modifier: str,
) -> str:
    escaped_title = _escape(title)
    escaped_description = _escape(description)
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="sv">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            '<meta name="robots" content="noindex,nofollow">',
            f"<title>{escaped_title}</title>",
            f'<meta name="description" content="{escaped_description}">',
            f'<meta property="og:title" content="{escaped_title}">',
            f'<meta property="og:description" content="{escaped_description}">',
            f"<style>{_SHARE_CSS}</style>",
            "</head>",
            "<body>",
            f'<main class="share-page {page_modifier}">{body}</main>',
            "</body>",
            "</html>",
        ]
    )


def _json_object(model: BaseModel) -> JsonObject:
    payload: object = json.loads(model.model_dump_json())
    if not isinstance(payload, dict):
        raise TypeError("Share presentation payload must serialize to a JSON object.")
    return {str(key): _json_value(value) for key, value in payload.items()}


def _json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    raise TypeError(f"Unsupported share presentation JSON value: {type(value).__name__}")


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def _share_header(*, title: str, subtitle: str | None) -> str:
    """Render common immutable share-page chrome."""

    subtitle_markup = (
        f'<p class="share-subtitle">{_escape(subtitle)}</p>' if subtitle is not None else ""
    )
    return "\n".join(
        [
            '<header class="share-header">',
            '<div class="share-header__main">',
            '<p class="share-kicker">Klassrumskartan</p>',
            f'<h1 class="share-title">{_escape(title)}</h1>',
            subtitle_markup,
            f'<p class="share-created">Skapad: {SHARE_CREATED_DATE_CHROME_SLOT}</p>',
            "</div>",
            '<nav class="share-actions" aria-label="Delningsåtgärder">',
            (
                '<a class="share-download-pdf" '
                f"{SHARE_PDF_DOWNLOAD_HREF_CHROME_SLOT} download>Ladda ner PDF</a>"
            ),
            (
                '<a class="share-origin-link" '
                f'href="{CLASSROOM_PLANNER_PUBLIC_APP_PATH}" rel="noopener">'
                "Skapad av Klassrumskartan</a>"
            ),
            "</nav>",
            "</header>",
        ]
    )
