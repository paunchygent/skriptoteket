"""Render DOCX pages to PNG images through LibreOffice and pdftoppm."""

from __future__ import annotations

import base64
import shutil
import subprocess
from pathlib import Path

_SOFFICE_FALLBACK = "/opt/homebrew/bin/soffice"
_PDFTOPPM_FALLBACK = "/opt/homebrew/bin/pdftoppm"


def _binary(name: str, fallback: str) -> str:
    """Return the path of an external binary or raise when it is missing."""
    found = shutil.which(name)
    if found:
        return found
    if Path(fallback).is_file():
        return fallback
    raise RuntimeError(f"{name} not found on PATH or at {fallback}; install it to render pages")


def _page_number(png: Path) -> int:
    """Return the page number pdftoppm encoded after the last hyphen."""
    return int(png.stem.rsplit("-", 1)[1])


def render_docx_pages(docx_path: Path, work_dir: Path, *, dpi: int = 60) -> list[bytes]:
    """Return PNG bytes for each page of a DOCX file in page order."""
    soffice = _binary("soffice", _SOFFICE_FALLBACK)
    pdftoppm = _binary("pdftoppm", _PDFTOPPM_FALLBACK)
    pdf_dir = work_dir / "pdf"
    png_dir = work_dir / "png"
    profile_dir = work_dir / "lo-profile"
    for directory in (pdf_dir, png_dir, profile_dir):
        directory.mkdir(parents=True, exist_ok=True)
    for stale in png_dir.glob("page-*.png"):
        stale.unlink()
    subprocess.run(
        [
            soffice,
            f"-env:UserInstallation={profile_dir.resolve().as_uri()}",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(pdf_dir),
            str(docx_path),
        ],
        check=True,
        capture_output=True,
        timeout=180,
    )
    pdf_path = pdf_dir / f"{docx_path.stem}.pdf"
    if not pdf_path.is_file():
        raise RuntimeError(f"LibreOffice produced no PDF for {docx_path}")
    subprocess.run(
        [pdftoppm, "-png", "-r", str(dpi), str(pdf_path), str(png_dir / "page")],
        check=True,
        capture_output=True,
        timeout=120,
    )
    pages = sorted(png_dir.glob("page-*.png"), key=_page_number)
    return [page.read_bytes() for page in pages]


def png_data_url(png: bytes) -> str:
    """Return a base64 data URL for PNG bytes."""
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")
