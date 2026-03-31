"""Shared branding asset helpers for classroom-planner PDF exports.

Purpose:
    Keep the teacher-facing PDF renderers on one consistent Skriptoteket logo
    source so grouping and seating exports do not drift in branding behavior.
    The asset lives beside the backend renderers so local host runs and Docker
    dev containers resolve the same file path.

Relationships:
    - Consumed by the grouping WeasyPrint renderer.
    - Consumed by the seating poster HTML renderer.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

PDF_BRANDING_ASSETS_DIR = Path(__file__).resolve().parent / "assets"
HORIZONTAL_LOGO_SVG_PATH = PDF_BRANDING_ASSETS_DIR / "logo-horizontal.svg"
HORIZONTAL_LOGO_PNG_PATH = PDF_BRANDING_ASSETS_DIR / "logo-horizontal.png"
PDF_BRAND_FOOTER_LABEL = "skriptoteket.hule.education"
PDF_BRAND_FOOTER_URL = "https://skriptoteket.hule.education"


def resolve_local_horizontal_logo_filename() -> str | None:
    """Return the preferred local logo filename for relative asset references."""

    if HORIZONTAL_LOGO_SVG_PATH.exists():
        return HORIZONTAL_LOGO_SVG_PATH.name
    if HORIZONTAL_LOGO_PNG_PATH.exists():
        return HORIZONTAL_LOGO_PNG_PATH.name
    return None


def resolve_local_horizontal_logo_base_dir() -> Path:
    """Return the filesystem base directory used for local PDF asset resolution."""

    return PDF_BRANDING_ASSETS_DIR


def resolve_local_horizontal_logo_url() -> str | None:
    """Return an absolute local URL for the bundled horizontal logo asset."""

    if HORIZONTAL_LOGO_SVG_PATH.exists():
        return HORIZONTAL_LOGO_SVG_PATH.as_uri()
    if HORIZONTAL_LOGO_PNG_PATH.exists():
        return HORIZONTAL_LOGO_PNG_PATH.as_uri()
    return None


def resolve_bundled_horizontal_logo_filename() -> str | None:
    """Return the preferred bundled logo filename for export resource zips.

    The HTML-to-PDF seating lane prefers PNG for maximum compatibility when
    the converter expands relative resources from a bundle.
    """

    if HORIZONTAL_LOGO_PNG_PATH.exists():
        return HORIZONTAL_LOGO_PNG_PATH.name
    if HORIZONTAL_LOGO_SVG_PATH.exists():
        return HORIZONTAL_LOGO_SVG_PATH.name
    return None


def build_pdf_brand_footer_margin_box_css() -> str:
    """Return the WeasyPrint margin-box rule for the shared footer watermark."""

    return """
        @bottom-right {
          content: element(pdf-brand-footer);
          vertical-align: bottom;
        }
    """


def build_pdf_brand_footer_css() -> str:
    """Return the shared footer watermark CSS used by classroom-planner PDFs."""

    return """
      .pdf-brand-footer {
        position: running(pdf-brand-footer);
      }

      .pdf-brand-footer a {
        color: #64748b;
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
        font-size: 7.5pt;
        letter-spacing: 0.02em;
        text-decoration: none;
        white-space: nowrap;
      }
    """


def render_pdf_brand_footer_markup() -> str:
    """Return the shared footer watermark markup for running page elements."""

    return (
        '<div class="pdf-brand-footer" aria-hidden="true">'
        f'<a href="{escape(PDF_BRAND_FOOTER_URL)}">{escape(PDF_BRAND_FOOTER_LABEL)}</a>'
        "</div>"
    )
