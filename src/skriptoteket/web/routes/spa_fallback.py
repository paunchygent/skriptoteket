"""Crawler files and SPA history fallback routes for Skriptoteket.

Purpose:
    Serve launch crawler resources and preserve Vue history routing for
    explicitly owned app route families.

Relationships:
    - Registered last from `skriptoteket.web.router` so API, static, and
      observability routes keep precedence.
    - Uses `app.state.public_app_base_url` set by `skriptoteket.web.app` to
      build canonical sitemap and robots URLs.

NOTE: Do NOT use `from __future__ import annotations` in router modules.
See .codex/rules/040-fastapi-blueprint.md (OpenAPI-safe typing).
"""

from pathlib import Path
from xml.sax.saxutils import escape

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from skriptoteket.web.spa_metadata import (
    PUBLIC_CLASSROOM_APP_PATH,
    build_not_found_html,
    inject_spa_head_metadata,
)

router = APIRouter(tags=["spa"])

_SPA_INDEX_PATH = Path(__file__).resolve().parent.parent / "static" / "spa" / "index.html"
_DEFAULT_PUBLIC_APP_BASE_URL = "https://skriptoteket.hule.education"
_INDEXABLE_PUBLIC_PATHS = ("/", PUBLIC_CLASSROOM_APP_PATH)
_EXCLUDED_PREFIXES = (
    "/api/",
    "/static/",
    "/healthz",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
)
_EXACT_SPA_PATHS = frozenset(
    {
        "/",
        PUBLIC_CLASSROOM_APP_PATH,
        "/auth/login",
        "/auth/callback",
        "/auth/provisioning-required",
        "/forgot-password",
        "/register",
        "/reset-password",
        "/verify-email",
        "/profile",
        "/forbidden",
        "/vault",
        "/my-tools",
        "/editor",
        "/suggestions/new",
    }
)


def _split_path_segments(path: str) -> list[str]:
    """Split a normalized absolute route path into segments."""
    if path == "/":
        return []
    return [segment for segment in path.strip("/").split("/") if segment]


def _has_segments(path: str, *, prefix: str, count: int) -> bool:
    """Check that a route path has a fixed prefix and segment count."""
    segments = _split_path_segments(path)
    prefix_segments = _split_path_segments(prefix)
    return len(segments) == count and segments[: len(prefix_segments)] == prefix_segments


def _is_browse_route(path: str) -> bool:
    """Return whether a path belongs to the Vue browse route family."""
    segments = _split_path_segments(path)
    if segments == ["browse"]:
        return True
    return len(segments) in {2, 3, 4} and segments[:2] == ["browse", "professions"]


def _is_single_param_route(path: str, *, prefix: str) -> bool:
    """Return whether a path is a one-parameter Vue route under the prefix."""
    return _has_segments(path, prefix=prefix, count=len(_split_path_segments(prefix)) + 1)


def _is_optional_param_route(path: str, *, prefix: str) -> bool:
    """Return whether a path is an exact route or one-parameter route."""
    return path == prefix or _is_single_param_route(path, prefix=prefix)


def _is_valid_spa_route(path: str) -> bool:
    """Check whether the backend should preserve Vue history fallback for a path."""
    if path in _EXACT_SPA_PATHS:
        return True
    if _is_browse_route(path):
        return True
    if _is_single_param_route(path, prefix="/apps"):
        return True
    if _has_segments(path, prefix="/tools", count=3) and path.endswith("/run"):
        return True
    if _is_optional_param_route(path, prefix="/my-runs"):
        return True
    if _is_optional_param_route(path, prefix="/admin/tools"):
        return True
    if _is_optional_param_route(path, prefix="/admin/users"):
        return True
    if _is_single_param_route(path, prefix="/admin/tool-versions"):
        return True
    if _is_optional_param_route(path, prefix="/admin/suggestions"):
        return True
    return False


def _public_app_base_url(request: Request) -> str:
    """Resolve the canonical public app base URL for crawler files."""
    configured = getattr(request.app.state, "public_app_base_url", "")
    if isinstance(configured, str) and configured.strip():
        return configured.strip().rstrip("/")
    return _DEFAULT_PUBLIC_APP_BASE_URL


def _canonical_url(*, request: Request, path: str) -> str:
    """Build a canonical absolute URL for a public path."""
    if path == "/":
        return f"{_public_app_base_url(request)}/"
    return f"{_public_app_base_url(request)}{path}"


def _build_sitemap_xml(*, request: Request) -> str:
    """Build the launch sitemap XML from the approved public route allowlist."""
    urls = "\n".join(
        f"  <url>\n    <loc>{escape(_canonical_url(request=request, path=path))}</loc>\n  </url>"
        for path in _INDEXABLE_PUBLIC_PATHS
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n"
        "</urlset>\n"
    )


def _should_serve_spa(path: str) -> bool:
    """Check if path should be served by the Vue SPA history fallback.

    Args:
        path: The request path including leading slash.

    Returns:
        True if the path should be served by the SPA, False if it should be excluded.
    """
    if any(path.startswith(prefix) for prefix in _EXCLUDED_PREFIXES):
        return False
    return _is_valid_spa_route(path)


@router.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
async def robots_txt(request: Request) -> Response:
    """Return the launch crawler policy file."""
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {_canonical_url(request=request, path='/sitemap.xml')}\n"
    )
    return PlainTextResponse(
        content=body,
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/sitemap.xml", response_class=Response, include_in_schema=False)
async def sitemap_xml(request: Request) -> Response:
    """Return the launch sitemap for approved public URLs."""
    return Response(
        content=_build_sitemap_xml(request=request),
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
async def spa_fallback(request: Request, full_path: str) -> Response:
    """Serve SPA index.html for client-side routing (history fallback).

    This enables deep linking for the Vue SPA. Vue Router handles client-side
    route matching and authentication guards via /api/v1/auth/me.

    Args:
        full_path: The captured path segment (without leading slash).

    Returns:
        The SPA index.html as FileResponse, or an error HTMLResponse.
    """
    path = f"/{full_path}" if full_path else "/"

    public_base_url = _public_app_base_url(request)

    if not _should_serve_spa(path):
        return HTMLResponse(
            content=build_not_found_html(public_base_url=public_base_url),
            status_code=404,
        )

    if not _SPA_INDEX_PATH.is_file():
        return HTMLResponse(
            content="SPA not built. Run 'pdm run fe-build'.",
            status_code=500,
        )

    html = _SPA_INDEX_PATH.read_text(encoding="utf-8")
    return HTMLResponse(
        content=inject_spa_head_metadata(
            index_html=html,
            path=path,
            public_base_url=public_base_url,
        )
    )
