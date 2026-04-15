"""Route-level metadata rendering for the Skriptoteket SPA shell.

Purpose:
    Own the backend-visible head metadata contract for launch-facing SPA
    routes without moving broad rendering responsibilities into FastAPI
    routers or the Vue client.

Relationships:
    - Used by `skriptoteket.web.routes.spa_fallback` after it has decided the
      HTTP status and route family.
    - Mirrors the public route allowlist from EPIC-35 so crawler-visible
      metadata, sitemap coverage, and fallback status semantics stay aligned.
"""

import re
from dataclasses import dataclass
from html import escape

PUBLIC_CLASSROOM_APP_PATH = "/public/apps/classroom.group-seating-studio"
DEFAULT_PUBLIC_APP_BASE_URL = "https://skriptoteket.hule.education"

_GENERATED_HEAD_START = "<!-- skriptoteket:route-metadata:start -->"
_GENERATED_HEAD_END = "<!-- skriptoteket:route-metadata:end -->"
_GENERATED_HEAD_RE = re.compile(
    rf"\s*{re.escape(_GENERATED_HEAD_START)}.*?{re.escape(_GENERATED_HEAD_END)}",
    re.IGNORECASE | re.DOTALL,
)
_HEAD_CLOSE_RE = re.compile(r"</head>", re.IGNORECASE)
_TITLE_RE = re.compile(r"<title>.*?</title>", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True, slots=True)
class SpaRouteMetadata:
    """Metadata fields required for a backend-served SPA route."""

    title: str
    description: str
    robots: str
    canonical_path: str | None = None
    share: bool = False


_PUBLIC_ROUTE_METADATA = {
    "/": SpaRouteMetadata(
        title="Skriptoteket | Lektionsplanering direkt i webbläsaren",
        description=(
            "Skriptoteket samlar lärarverktyg och öppna appar som Klassrumskartan "
            "för planering direkt i webbläsaren."
        ),
        robots="index,follow",
        canonical_path="/",
        share=True,
    ),
    PUBLIC_CLASSROOM_APP_PATH: SpaRouteMetadata(
        title="Klassrumskartan | Skriptoteket",
        description=(
            "Planera grupper och placeringar direkt i webbläsaren med Klassrumskartan, "
            "en öppen app i Skriptoteket."
        ),
        robots="index,follow",
        canonical_path=PUBLIC_CLASSROOM_APP_PATH,
        share=True,
    ),
}

_PRIVATE_ROUTE_METADATA = SpaRouteMetadata(
    title="Skriptoteket",
    description="Skriptoteket kräver inloggning för den här sidan.",
    robots="noindex,follow",
)
_NOT_FOUND_METADATA = SpaRouteMetadata(
    title="Sidan hittades inte | Skriptoteket",
    description="Sidan finns inte eller kan inte visas i Skriptoteket.",
    robots="noindex,nofollow",
)


def metadata_for_spa_route(path: str) -> SpaRouteMetadata:
    """Return the initial-HTML metadata contract for a valid SPA route."""
    return _PUBLIC_ROUTE_METADATA.get(path, _PRIVATE_ROUTE_METADATA)


def not_found_metadata() -> SpaRouteMetadata:
    """Return the initial-HTML metadata contract for backend-owned 404 pages."""
    return _NOT_FOUND_METADATA


def absolute_public_url(*, public_base_url: str, path: str) -> str:
    """Build the canonical public URL for a normalized app path."""
    base_url = (public_base_url or DEFAULT_PUBLIC_APP_BASE_URL).strip().rstrip("/")
    if not base_url:
        base_url = DEFAULT_PUBLIC_APP_BASE_URL
    if path == "/":
        return f"{base_url}/"
    return f"{base_url}{path}"


def inject_spa_head_metadata(*, index_html: str, path: str, public_base_url: str) -> str:
    """Inject route metadata into the built SPA shell.

    Args:
        index_html: The built Vite `index.html` shell.
        path: The normalized request path served by the fallback.
        public_base_url: The configured public app base URL used for canonicals.

    Returns:
        The SPA shell with the route-specific title and metadata block.
    """
    metadata = metadata_for_spa_route(path)
    return _replace_head_metadata(
        html=index_html,
        metadata=metadata,
        public_base_url=public_base_url,
    )


def build_not_found_html(*, public_base_url: str) -> str:
    """Build a minimal backend-owned 404 HTML response with crawler metadata."""
    metadata = not_found_metadata()
    body = (
        "<!doctype html>\n"
        '<html lang="sv">\n'
        "  <head>\n"
        '    <meta charset="UTF-8" />\n'
        f"    <title>{_escape_attr(metadata.title)}</title>\n"
        f"{_render_metadata_block(metadata=metadata, public_base_url=public_base_url)}\n"
        "  </head>\n"
        "  <body>Not Found</body>\n"
        "</html>\n"
    )
    return body


def _replace_head_metadata(
    *,
    html: str,
    metadata: SpaRouteMetadata,
    public_base_url: str,
) -> str:
    """Replace generated metadata in a normal SPA shell."""
    html_without_generated_block = _GENERATED_HEAD_RE.sub("", html)
    title = f"<title>{_escape_attr(metadata.title)}</title>"
    if _TITLE_RE.search(html_without_generated_block):
        html_with_title = _TITLE_RE.sub(title, html_without_generated_block, count=1)
    else:
        html_with_title = html_without_generated_block

    block = _render_metadata_block(metadata=metadata, public_base_url=public_base_url)
    if not _HEAD_CLOSE_RE.search(html_with_title):
        return html_with_title
    return _HEAD_CLOSE_RE.sub(f"{block}\n  </head>", html_with_title, count=1)


def _render_metadata_block(*, metadata: SpaRouteMetadata, public_base_url: str) -> str:
    """Render the backend-owned metadata tags that live after the title tag."""
    tags = [
        _GENERATED_HEAD_START,
        _meta_name("description", metadata.description),
        _meta_name("robots", metadata.robots),
    ]
    canonical_url = None
    if metadata.canonical_path is not None:
        canonical_url = absolute_public_url(
            public_base_url=public_base_url,
            path=metadata.canonical_path,
        )
        tags.append(f'    <link rel="canonical" href="{_escape_attr(canonical_url)}" />')

    if metadata.share and canonical_url is not None:
        tags.extend(
            [
                _meta_property("og:title", metadata.title),
                _meta_property("og:description", metadata.description),
                _meta_property("og:url", canonical_url),
                _meta_property("og:type", "website"),
                _meta_name("twitter:card", "summary"),
                _meta_name("twitter:title", metadata.title),
                _meta_name("twitter:description", metadata.description),
            ]
        )

    tags.append(_GENERATED_HEAD_END)
    return "\n".join(f"    {tag}" if tag.startswith("<!--") else tag for tag in tags)


def _meta_name(name: str, content: str) -> str:
    """Render a `name` meta tag."""
    return f'    <meta name="{_escape_attr(name)}" content="{_escape_attr(content)}" />'


def _meta_property(property_name: str, content: str) -> str:
    """Render an Open Graph `property` meta tag."""
    return (
        f'    <meta property="{_escape_attr(property_name)}" content="{_escape_attr(content)}" />'
    )


def _escape_attr(value: str) -> str:
    """Escape text for safe HTML attribute and title contexts."""
    return escape(value, quote=True)
