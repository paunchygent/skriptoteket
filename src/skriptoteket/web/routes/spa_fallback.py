"""SPA history fallback route.

Serves SPA index.html for all paths not handled by API routes or static files.
Must be registered LAST in the router to avoid intercepting API responses.

NOTE: Do NOT use `from __future__ import annotations` in router modules.
See .agent/rules/040-fastapi-blueprint.md (OpenAPI-safe typing).
"""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse, Response

router = APIRouter(tags=["spa"])

_SPA_INDEX_PATH = Path(__file__).resolve().parent.parent / "static" / "spa" / "index.html"


def _should_serve_spa(path: str) -> bool:
    """Check if path should be served by SPA (exclude API, static, observability).

    Args:
        path: The request path including leading slash.

    Returns:
        True if the path should be served by the SPA, False if it should be excluded.
    """
    excluded_prefixes = (
        "/api/",
        "/static/",
        "/healthz",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
    )
    return not any(path.startswith(prefix) for prefix in excluded_prefixes)


@router.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
async def spa_fallback(full_path: str) -> Response:
    """Serve SPA index.html for client-side routing (history fallback).

    This enables deep linking for the Vue SPA. Vue Router handles client-side
    route matching and authentication guards via /api/v1/auth/me.

    Args:
        full_path: The captured path segment (without leading slash).

    Returns:
        The SPA index.html as FileResponse, or an error HTMLResponse.
    """
    path = f"/{full_path}" if full_path else "/"

    if not _should_serve_spa(path):
        return HTMLResponse(content="Not Found", status_code=404)

    if not _SPA_INDEX_PATH.is_file():
        return HTMLResponse(
            content="SPA not built. Run 'pdm run fe-build'.",
            status_code=500,
        )

    return FileResponse(_SPA_INDEX_PATH, media_type="text/html")
