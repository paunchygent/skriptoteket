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
    JsonObject,
    JsonValue,
    RenderedClassroomPlannerShare,
)
from skriptoteket.protocols.classroom_planner_shares import (
    ClassroomPlannerShareRendererProtocol,
)

_RENDERER_VERSION = "klassrumskartan-share-renderer-v1"
_GROUPING_SCHEMA_VERSION = "grouping-share-v1"
_SEATING_SCHEMA_VERSION = "seating-share-v1"

_SHARE_CSS = """
:root {
  color-scheme: light;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
    sans-serif;
  background: #f8f8f1;
  color: #171714;
}
* {
  box-sizing: border-box;
}
body {
  margin: 0;
  background: #f8f8f1;
}
.share-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 32px 20px 48px;
}
.share-kicker {
  color: #5d5b4f;
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
h1 {
  margin: 8px 0 20px;
  font-size: clamp(2rem, 4vw, 3.5rem);
  line-height: 1.05;
}
h2 {
  margin: 0 0 12px;
  font-size: 1.15rem;
}
.group-list,
.seat-list {
  display: grid;
  gap: 14px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.share-card {
  border: 1px solid #2d2b24;
  background: #fffef8;
  padding: 16px;
}
.member-list {
  margin: 0;
  padding-left: 20px;
}
.seat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}
.seat-meta {
  color: #5d5b4f;
  font-size: 0.9rem;
}
@media print {
  body {
    background: #fff;
  }
  .share-page {
    max-width: none;
    padding: 0;
  }
}
""".strip()


class StaticClassroomPlannerShareRenderer(ClassroomPlannerShareRendererProtocol):
    """Render share pages from canonical backend presentation models."""

    def render_grouping(
        self,
        *,
        prepared_export: PreparedGroupingExportContract,
    ) -> RenderedClassroomPlannerShare:
        presentation = prepared_export.presentation
        title = f"{presentation.class_name} - {presentation.title}"
        description = f"Gruppindelning för {presentation.class_name}."
        body = "\n".join(
            [
                '<p class="share-kicker">Klassrumskartan</p>',
                f"<h1>{_escape(title)}</h1>",
                '<ul class="group-list">',
                *[
                    _render_group_card(
                        label=group.group_label,
                        members=[member.display_name for member in group.members],
                    )
                    for group in presentation.groups
                ],
                "</ul>",
            ]
        )
        return RenderedClassroomPlannerShare(
            title=title,
            preview_description=description,
            renderer_version=_RENDERER_VERSION,
            presentation_schema_version=_GROUPING_SCHEMA_VERSION,
            presentation_payload=_json_object(presentation),
            rendered_html=_document(title=title, description=description, body=body),
            rendered_css=_SHARE_CSS,
        )

    def render_seating(
        self,
        *,
        prepared_export: PreparedSeatingExportContract,
    ) -> RenderedClassroomPlannerShare:
        scene = prepared_export.poster_scene
        title = f"{prepared_export.roster_name} - Sittschema"
        description = (
            f"Sittschema för {prepared_export.roster_name} i {prepared_export.template_name}."
        )
        assigned_seats = [seat for seat in scene.seats if seat.label]
        body = "\n".join(
            [
                '<p class="share-kicker">Klassrumskartan</p>',
                f"<h1>{_escape(title)}</h1>",
                f'<p class="seat-meta">{_escape(prepared_export.template_name)}</p>',
                '<div class="seat-grid">',
                *[
                    _render_seat_card(
                        label=seat.label or "Tom plats",
                        x=seat.x,
                        y=seat.y,
                    )
                    for seat in assigned_seats
                ],
                "</div>",
            ]
        )
        return RenderedClassroomPlannerShare(
            title=title,
            preview_description=description,
            renderer_version=_RENDERER_VERSION,
            presentation_schema_version=_SEATING_SCHEMA_VERSION,
            presentation_payload=_json_object(prepared_export),
            rendered_html=_document(title=title, description=description, body=body),
            rendered_css=_SHARE_CSS,
        )


def _render_group_card(*, label: str, members: list[str]) -> str:
    member_items = "\n".join(f"<li>{_escape(member)}</li>" for member in members)
    return "\n".join(
        [
            '<li class="share-card">',
            f"<h2>{_escape(label)}</h2>",
            f'<ol class="member-list">{member_items}</ol>',
            "</li>",
        ]
    )


def _render_seat_card(*, label: str, x: int, y: int) -> str:
    return "\n".join(
        [
            '<article class="share-card">',
            f"<h2>{_escape(label)}</h2>",
            f'<p class="seat-meta">Rad {y + 1}, plats {x + 1}</p>',
            "</article>",
        ]
    )


def _document(*, title: str, description: str, body: str) -> str:
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
            f'<main class="share-page">{body}</main>',
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
