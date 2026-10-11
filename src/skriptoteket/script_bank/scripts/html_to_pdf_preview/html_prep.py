"""HTML and CSS preparation for PDF rendering and preview."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from time import perf_counter
from urllib.parse import unquote, urlparse

from .perf import perf_event, perf_record


def wrap_preview_html(*, html: str) -> str:
    if 'id="__preview_outer"' in html or "id='__preview_outer'" in html:
        return html

    css = (
        ":root { --preview-scale: 0.95; --preview-pad: clamp(10px, 2.2vh, 22px); }\n"
        "html, body { margin: 0; padding: 0; }\n"
        "#__preview_outer { box-sizing: border-box; padding: var(--preview-pad); }\n"
        "#__preview_outer { padding-bottom: calc(var(--preview-pad) * 1.3); }\n"
        "#__preview_inner { transform: scale(var(--preview-scale)); "
        "transform-origin: top center; }\n"
    )
    style_tag = f"<style>{css}</style>"

    head_close = html.lower().find("</head>")
    if head_close != -1:
        html = html[:head_close] + style_tag + html[head_close:]
    else:
        html = style_tag + html

    body_open = re.search(r"(?is)<body\b[^>]*>", html)
    if not body_open:
        return f'<div id="__preview_outer"><div id="__preview_inner">{html}</div></div>'

    body_close = re.search(r"(?is)</body>", html)
    if not body_close or body_close.start() <= body_open.end():
        return html

    start = body_open.end()
    end = body_close.start()
    inner = html[start:end]
    wrapped = f'<div id="__preview_outer"><div id="__preview_inner">{inner}</div></div>'
    return html[:start] + wrapped + html[end:]


def wrap_pdf_html(*, html: str) -> str:
    if 'id="__pdf_outer"' in html or "id='__pdf_outer'" in html:
        return html

    css = "html, body { margin: 0; }\n#__pdf_outer { box-sizing: border-box; }\n"
    style_tag = f"<style>{css}</style>"

    head_close = html.lower().find("</head>")
    if head_close != -1:
        html = html[:head_close] + style_tag + html[head_close:]
    else:
        html = style_tag + html

    body_open = re.search(r"(?is)<body\b[^>]*>", html)
    if not body_open:
        return f'<div id="__pdf_outer"><div id="__pdf_inner">{html}</div></div>'

    body_close = re.search(r"(?is)</body>", html)
    if not body_close or body_close.start() <= body_open.end():
        return html

    start = body_open.end()
    end = body_close.start()
    inner = html[start:end]
    wrapped = f'<div id="__pdf_outer"><div id="__pdf_inner">{inner}</div></div>'
    return html[:start] + wrapped + html[end:]


# ─── PDF-KONVERTERING ───


def build_page_css(*, page_size: str, orientation: str) -> str:
    orient = "landscape" if orientation == "landscape" else "portrait"
    normalized_page_size = str(page_size).strip().lower()
    size_token = "A4" if normalized_page_size == "a4" else "Letter"

    pad_tb, pad_lr = _page_margins_for_scale(
        page_size=normalized_page_size,
        orientation=orient,
        scale=0.95,
    )

    max_svg_height = "240mm" if orient == "portrait" else "175mm"
    return (
        f"@page {{ size: {size_token} {orient}; margin: 0; }}\n"
        "html, body { height: auto !important; }\n"
        f"#__pdf_outer {{ padding: {pad_tb}mm {pad_lr}mm; box-decoration-break: clone; "
        "-webkit-box-decoration-break: clone; }}\n"
        "pre, .card, .card-h, .card-b, .diagram, details, .details-body, .pdf-details { "
        "box-decoration-break: clone; -webkit-box-decoration-break: clone; }\n"
        "pre { overflow: visible !important; }\n"
        ".app { display: block !important; max-width: none !important; "
        "padding: 0 !important; }\n"
        ".sidebar { display: none !important; }\n"
        "details > :not(summary) { display: block !important; }\n"
        "details { overflow: visible !important; }\n"
        ".card, .diagram { overflow: visible !important; }\n"
        f".diagram svg {{ max-height: {max_svg_height}; "
        "max-width: 100%; height: auto; }}\n"
    )


def _build_generic_page_css(*, page_size: str, orientation: str) -> str:
    orient = "landscape" if orientation == "landscape" else "portrait"
    normalized_page_size = str(page_size).strip().lower()
    size_token = "A4" if normalized_page_size == "a4" else "Letter"

    pad_tb, pad_lr = _page_margins_for_scale(
        page_size=normalized_page_size,
        orientation=orient,
        scale=0.95,
    )
    return (
        f"@page {{ size: {size_token} {orient}; margin: 0; }}\n"
        "html, body { height: auto !important; }\n"
        f"#__pdf_outer {{ padding: {pad_tb}mm {pad_lr}mm; box-decoration-break: clone; "
        "-webkit-box-decoration-break: clone; }}\n"
        "pre, blockquote, table { box-decoration-break: clone; "
        "-webkit-box-decoration-break: clone; }\n"
        "pre { overflow: visible !important; }\n"
    )


def build_weasyprint_recovery_css() -> str:
    return (
        "html, body { height: auto !important; }\n"
        ".dropcap::first-letter { float: none !important; }\n"
        ".article, .cols, .columns { column-count: 1 !important; column-gap: 0 !important; }\n"
        ".span-all { column-span: none !important; }\n"
        ".grid, *[class*='grid'] { display: block !important; }\n"
        "section { break-inside: auto !important; page-break-inside: auto !important; }\n"
        "pre { overflow: visible !important; }\n"
        "pre, blockquote, table { break-inside: auto !important; "
        "page-break-inside: auto !important; }\n"
        "h1, h2, h3 { break-after: auto !important; page-break-after: auto !important; }\n"
        "details { break-inside: auto !important; page-break-inside: auto !important; }\n"
    )


def build_page_css_fallback(*, page_size: str, orientation: str) -> str:
    orient = "landscape" if orientation == "landscape" else "portrait"
    normalized_page_size = str(page_size).strip().lower()
    size_token = "A4" if normalized_page_size == "a4" else "Letter"

    pad_tb, pad_lr = _page_margins_for_scale(
        page_size=normalized_page_size,
        orientation=orient,
        scale=0.95,
    )

    max_svg_height = "200mm" if orient == "portrait" else "140mm"
    return (
        f"@page {{ size: {size_token} {orient}; margin: 0; }}\n"
        "html, body { height: auto !important; }\n"
        f"#__pdf_outer {{ padding: {pad_tb}mm {pad_lr}mm; box-decoration-break: clone; "
        "-webkit-box-decoration-break: clone; }}\n"
        "pre, .card, .card-h, .card-b, .diagram, details, .details-body, .pdf-details { "
        "box-decoration-break: clone; -webkit-box-decoration-break: clone; }\n"
        "pre { overflow: visible !important; }\n"
        ".app { display: block !important; max-width: none !important; "
        "padding: 0 !important; }\n"
        ".sidebar { display: none !important; }\n"
        "details > :not(summary) { display: block !important; }\n"
        "details { overflow: visible !important; }\n"
        ".card, .diagram { overflow: visible !important; }\n"
        f".diagram svg {{ max-height: {max_svg_height} !important; "
        "max-width: 100% !important; height: auto !important; }}\n"
    )


def _page_margins_for_scale(
    *, page_size: str, orientation: str, scale: float
) -> tuple[float, float]:
    if page_size == "a4":
        width_mm, height_mm = 210.0, 297.0
    else:
        width_mm, height_mm = 215.9, 279.4

    if orientation == "landscape":
        width_mm, height_mm = height_mm, width_mm

    margin_lr = round((width_mm * (1.0 - scale)) / 2.0, 1)
    margin_tb = round((height_mm * (1.0 - scale)) / 2.0, 1)
    margin_lr = max(margin_lr, 0.0)
    margin_tb = max(margin_tb, 0.0)
    return margin_tb, margin_lr


def inject_author_css(*, html: str, css: str) -> str:
    style_tag = f"<style>{css}</style>"
    if "</head>" in html:
        return html.replace("</head>", f"{style_tag}</head>", 1)
    if "<html" in html:
        return f"{html}{style_tag}"
    return f"<html><head>{style_tag}</head><body>{html}</body></html>"


def _force_details_open(*, html: str) -> str:
    return re.sub(r"<details(?![^>]*\\bopen\\b)", "<details open", html)


def _rewrite_details_to_divs(*, html: str) -> str:
    html = re.sub(r"(?i)<details\b[^>]*>", '<div class="pdf-details">', html)
    html = re.sub(r"(?i)</details>", "</div>", html)
    html = re.sub(r"(?i)<summary\b[^>]*>", '<div class="pdf-summary">', html)
    html = re.sub(r"(?i)</summary>", "</div>", html)
    return html


def _extract_style_blocks(*, html: str) -> str:
    blocks = re.findall(r"(?is)<style\b[^>]*>(.*?)</style>", html)
    return "\n".join(blocks).strip()


class _StylesheetLinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "link":
            return
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        rel = attr_map.get("rel", "").lower()
        if "stylesheet" not in rel:
            return
        href = attr_map.get("href", "").strip()
        if not href:
            return
        self.hrefs.append(href)


def _extract_linked_stylesheets(*, html: str) -> list[str]:
    parser = _StylesheetLinkCollector()
    parser.feed(html)
    return parser.hrefs


def _resolve_local_href(*, base_dir: Path, href: str) -> Path | None:
    parsed = urlparse(href)
    if parsed.scheme not in ("", "file"):
        return None

    if parsed.scheme == "file":
        candidate = Path(unquote(parsed.path))
    else:
        if href.startswith("//"):
            return None
        if href.startswith("/"):
            return None
        candidate = (base_dir / unquote(href)).resolve()

    base_resolved = base_dir.resolve()
    if not candidate.resolve().is_relative_to(base_resolved):
        return None

    if not candidate.is_file():
        return None
    return candidate


_IMPORT_RE = re.compile(r"(?im)@import\s+(?:url\()?\s*['\"]?([^'\"\)\s;]+)['\"]?\s*\)?[^;]*;")
_DETAILS_RE = re.compile(r"(?i)<details\b|<summary\b")
_SVG_RE = re.compile(r"(?i)<svg\b")


def _read_css_with_imports(*, base_dir: Path, path: Path, seen: set[Path]) -> str:
    resolved = path.resolve()
    if resolved in seen:
        return ""
    seen.add(resolved)

    try:
        css = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""

    def _replace(match: re.Match[str]) -> str:
        href = match.group(1)
        imported = _resolve_local_href(base_dir=base_dir, href=href)
        if imported is None:
            return ""
        return _read_css_with_imports(base_dir=base_dir, path=imported, seen=seen)

    return _IMPORT_RE.sub(_replace, css)


def extract_all_css(*, html: str, base_dir: Path) -> str:
    inline = _extract_style_blocks(html=html)
    linked_parts: list[str] = []
    seen: set[Path] = set()
    for href in _extract_linked_stylesheets(html=html):
        css_path = _resolve_local_href(base_dir=base_dir, href=href)
        if css_path is None:
            continue
        linked_parts.append(_read_css_with_imports(base_dir=base_dir, path=css_path, seen=seen))

    combined = "\n".join([p for p in [*linked_parts, inline] if p.strip()]).strip()
    return combined


def _document_defines_at_page(*, css: str) -> bool:
    return bool(re.search(r"(?is)@page\b", css))


def _looks_like_tool_editor_doc(*, html: str) -> bool:
    return bool(
        re.search(r"(?i)class=\"[^\"]*\bapp\b", html)
        and re.search(r"(?i)class=\"[^\"]*\bsidebar\b", html)
    )


def select_print_css_for_document(
    *,
    html: str,
    base_dir: Path,
    page_size: str,
    orientation: str,
    doc_css: str | None = None,
) -> tuple[str, bool]:
    is_tool_editor = _looks_like_tool_editor_doc(html=html)
    if is_tool_editor:
        return build_page_css(page_size=page_size, orientation=orientation), True

    if doc_css is None:
        doc_css = extract_all_css(html=html, base_dir=base_dir)
    if _document_defines_at_page(css=doc_css):
        return "", False

    return _build_generic_page_css(page_size=page_size, orientation=orientation), False


def _inline_css_into_svgs(*, html: str, base_dir: Path, css: str | None = None) -> str:
    if css is None:
        css = extract_all_css(html=html, base_dir=base_dir)
    if not css:
        return html
    svg_style = f'<style type="text/css"><![CDATA[\n{css}\n]]></style>'
    return re.sub(
        r"(?i)(<svg\b[^>]*>)(?!\s*<style\b)",
        rf"\1{svg_style}",
        html,
    )


def normalize_html_for_weasyprint(
    *,
    html: str,
    base_dir: Path,
    print_css: str,
    doc_css: str | None = None,
    perf_log: list[dict[str, object]] | None = None,
    perf_source: str = "",
    perf_label: str = "normalize",
) -> str:
    total_start = perf_counter()
    if _DETAILS_RE.search(html):
        normalized = _force_details_open(html=html)
        normalized = _rewrite_details_to_divs(html=normalized)
    else:
        normalized = html
    inline_start = perf_counter()
    if _SVG_RE.search(normalized):
        normalized = _inline_css_into_svgs(html=normalized, base_dir=base_dir, css=doc_css)
        perf_record(
            perf_log,
            source=perf_source,
            label=f"{perf_label}:inline_svg",
            start=inline_start,
        )
    else:
        perf_event(
            perf_log,
            source=perf_source,
            label=f"{perf_label}:inline_svg",
            extra={"skipped": True},
        )
    if not print_css.strip():
        perf_record(
            perf_log,
            source=perf_source,
            label=f"{perf_label}:total",
            start=total_start,
        )
        return normalized
    normalized = inject_author_css(html=normalized, css=print_css)
    perf_record(
        perf_log,
        source=perf_source,
        label=f"{perf_label}:total",
        start=total_start,
    )
    return normalized
