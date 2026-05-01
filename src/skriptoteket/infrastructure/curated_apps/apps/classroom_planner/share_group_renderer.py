"""Grouping-card HTML helpers for Klassrumskartan share artifacts.

Purpose:
    Render static, CSS-only grouping share markup from the canonical grouping
    export presentation contract.

Relationships:
    - Used by `share_renderer.py` for immutable grouping share pages.
    - Consumes renderer-independent models from the application export layer.
    - Does not emit JavaScript, app API calls, or browser-supplied HTML/CSS.
"""

from __future__ import annotations

from html import escape

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    GroupingExportPresentation,
    GroupingPresentationGroup,
    GroupingPresentationMember,
)

GROUPING_SHARE_CSS = """
.share-page--grouping {
  max-width: 1200px;
}
.groups-grid {
  display: grid;
  gap: 20px;
  grid-template-columns: 1fr;
  margin-bottom: 40px;
}
.group-card {
  background: #fff;
  border: 2px solid var(--navy);
  padding: 20px;
}
.group-header {
  align-items: center;
  border-bottom: 1px solid var(--navy-15);
  display: flex;
  gap: 16px;
  justify-content: space-between;
  margin-bottom: 16px;
  padding-bottom: 12px;
}
.group-name {
  font-size: var(--text-lg);
  font-weight: 700;
  line-height: 1.2;
  margin: 0;
}
.group-count {
  color: var(--navy-50);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: var(--tracking-label);
  text-transform: uppercase;
  white-space: nowrap;
}
.student-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  list-style: none;
  margin: 0;
  padding: 0;
}
.student-item {
  align-items: center;
  display: flex;
  gap: 12px;
}
.student-number {
  align-items: center;
  background: var(--navy);
  border-radius: 50%;
  color: #fff;
  display: flex;
  flex: 0 0 auto;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 500;
  height: 28px;
  justify-content: center;
  line-height: 1;
  width: 28px;
}
.student-name {
  font-size: var(--text-base);
  font-weight: 500;
  line-height: 1.4;
  min-width: 0;
}
.student-empty {
  color: var(--navy-60);
  font-size: var(--text-base);
  font-weight: 500;
  line-height: 1.4;
  margin: 0;
}
@media (min-width: 768px) {
  .groups-grid {
    gap: 24px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .group-card {
    padding: 24px;
  }
}
@media print {
  .groups-grid {
    gap: 14px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .group-card {
    break-inside: avoid;
    padding: 16px;
  }
}
""".strip()


def render_grouping_share_body(*, presentation: GroupingExportPresentation) -> str:
    """Render the grouping share body as the approved card grid."""

    title = f"{presentation.class_name} – {presentation.title}"
    return "\n".join(
        [
            '<p class="share-kicker">Klassrumskartan</p>',
            f'<h1 class="share-title">{escape(title)}</h1>',
            '<div class="groups-grid" aria-label="Delad gruppindelning">',
            *[_render_group_card(group=group) for group in presentation.groups],
            "</div>",
        ]
    )


def _render_group_card(*, group: GroupingPresentationGroup) -> str:
    """Render one group card with member count and ordered members."""

    members = list(group.members)
    body = _render_member_list(members=members)
    return "\n".join(
        [
            '<article class="group-card">',
            '<div class="group-header">',
            f'<h2 class="group-name">{escape(group.group_label)}</h2>',
            f'<span class="group-count">{_member_count_text(len(members))}</span>',
            "</div>",
            body,
            "</article>",
        ]
    )


def _render_member_list(*, members: list[GroupingPresentationMember]) -> str:
    """Render ordered group members using the mockup's circular number markers."""

    if not members:
        return '<p class="student-empty">Inga elever i gruppen.</p>'

    member_items = "\n".join(_render_member_item(member=member) for member in members)
    return f'<ol class="student-list">{member_items}</ol>'


def _render_member_item(*, member: GroupingPresentationMember) -> str:
    """Render one member row."""

    return "\n".join(
        [
            '<li class="student-item">',
            f'<span class="student-number">{member.member_order}</span>',
            f'<span class="student-name">{escape(member.display_name)}</span>',
            "</li>",
        ]
    )


def _member_count_text(member_count: int) -> str:
    """Return Swedish count text for one group card."""

    if member_count == 1:
        return "1 elev"
    return f"{member_count} elever"
