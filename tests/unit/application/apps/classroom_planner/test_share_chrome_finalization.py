"""Tests for Klassrumskartan share chrome finalization.

Purpose:
    Prove creation date and PDF-link finalization is constrained to renderer-
    owned chrome slots and cannot rewrite escaped classroom content.

Relationships:
    - Exercises `finalize_share_rendered_html` from the application share
      contract module.
    - Complements renderer tests that emit the owned chrome slots.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone

import pytest

from skriptoteket.application.curated_apps.classroom_planner.shares import (
    SHARE_CREATED_DATE_CHROME_SLOT,
    SHARE_CREATED_DATE_PLACEHOLDER,
    SHARE_PDF_DOWNLOAD_HREF_CHROME_SLOT,
    SHARE_PDF_DOWNLOAD_PATH_PLACEHOLDER,
    finalize_share_rendered_html,
)


@pytest.mark.unit
def test_share_chrome_finalization_does_not_rewrite_user_content_sentinels() -> None:
    hostile_text = (
        f'Klass <{SHARE_CREATED_DATE_PLACEHOLDER}> elev "{SHARE_PDF_DOWNLOAD_PATH_PLACEHOLDER}"'
    )
    escaped_hostile_text = html.escape(hostile_text, quote=True)
    rendered_html = "\n".join(
        [
            "<main>",
            f'<p class="share-created">Skapad: {SHARE_CREATED_DATE_CHROME_SLOT}</p>',
            f"<a {SHARE_PDF_DOWNLOAD_HREF_CHROME_SLOT}>Ladda ner PDF</a>",
            f"<h1>{escaped_hostile_text}</h1>",
            f'<span class="student-name">{escaped_hostile_text}</span>',
            "</main>",
        ]
    )

    finalized = finalize_share_rendered_html(
        rendered_html=rendered_html,
        created_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        pdf_download_path="/share/classroom/public-token/download.pdf",
    )

    assert '<p class="share-created">Skapad: ' in finalized
    assert ">2026-05-01</span></p>" in finalized
    assert 'href="/share/classroom/public-token/download.pdf"' in finalized
    assert f"<h1>{escaped_hostile_text}</h1>" in finalized
    assert f'<span class="student-name">{escaped_hostile_text}</span>' in finalized


@pytest.mark.unit
def test_share_chrome_finalization_requires_owned_chrome_slots() -> None:
    with pytest.raises(ValueError, match="date chrome slot"):
        finalize_share_rendered_html(
            rendered_html=f"<main>{SHARE_CREATED_DATE_PLACEHOLDER}</main>",
            created_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
            pdf_download_path="/share/classroom/public-token/download.pdf",
        )
