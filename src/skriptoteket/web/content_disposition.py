"""Safe HTTP Content-Disposition values for downloadable artifacts."""

from __future__ import annotations

from urllib.parse import quote


def attachment_content_disposition(*, filename: str) -> str:
    """Build an attachment header while preserving Unicode filenames."""
    if filename.isascii() and filename.isprintable() and '"' not in filename:
        return f'attachment; filename="{filename}"'
    return f"attachment; filename*=utf-8''{quote(filename)}"
