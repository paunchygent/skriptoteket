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

from pathlib import Path

PDF_BRANDING_ASSETS_DIR = Path(__file__).resolve().parent / "assets"
HORIZONTAL_LOGO_SVG_PATH = PDF_BRANDING_ASSETS_DIR / "logo-horizontal.svg"
HORIZONTAL_LOGO_PNG_PATH = PDF_BRANDING_ASSETS_DIR / "logo-horizontal.png"


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
