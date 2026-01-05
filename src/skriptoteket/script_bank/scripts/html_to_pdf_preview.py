"""
HTML → PDF med förhandsgranskning (Skriptoteket demo).

Demonstrerar alla Skriptoteket-funktioner:
- Tvåstegsflöde: förhandsgranska → konvertera
- html_sandboxed: Live HTML-förhandsgranskning
- vega_lite: Filstorleksjämförelse
- next_actions: Navigering mellan steg
- state: Spåra arbetsflödessteg
- settings: Användarpreferenser (sidstorlek, orientering)
- artifacts: PDF-nedladdning

Entrypoint: run_tool(input_dir: str, output_dir: str) -> dict
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from time import perf_counter
from typing import TypedDict
from urllib.parse import unquote, urlparse


class ManifestFile(TypedDict):
    name: str
    path: str
    bytes: int


# ─── HJÄLPFUNKTIONER ───


def _notice(level: str, message: str) -> dict[str, object]:
    return {"kind": "notice", "level": level, "message": message}


def _markdown(md: str) -> dict[str, object]:
    return {"kind": "markdown", "markdown": md}


def _shorten_for_table(message: str, *, max_chars: int = 200) -> str:
    normalized = " ".join(message.split())
    if len(normalized) <= max_chars:
        return normalized
    if max_chars <= 3:
        return "..."
    return normalized[: max_chars - 3] + "..."


def _perf_record(
    perf: list[dict[str, object]] | None,
    *,
    source: str,
    label: str,
    start: float,
    extra: dict[str, object] | None = None,
) -> None:
    if perf is None:
        return
    duration_ms = round((perf_counter() - start) * 1000.0, 2)
    entry: dict[str, object] = {"source": source, "label": label, "ms": duration_ms}
    if extra:
        entry.update(extra)
    perf.append(entry)


def _perf_event(
    perf: list[dict[str, object]] | None,
    *,
    source: str,
    label: str,
    extra: dict[str, object] | None = None,
) -> None:
    if perf is None:
        return
    entry: dict[str, object] = {"source": source, "label": label, "ms": 0.0}
    if extra:
        entry.update(extra)
    perf.append(entry)


def _read_input_manifest_files() -> list[ManifestFile]:
    raw = os.environ.get("SKRIPTOTEKET_INPUT_MANIFEST", "")
    if not raw.strip():
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, dict):
        return []
    files = payload.get("files")
    if not isinstance(files, list):
        return []

    result: list[ManifestFile] = []
    for item in files:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        path = item.get("path")
        bytes_ = item.get("bytes")
        if isinstance(name, str) and isinstance(path, str) and isinstance(bytes_, int):
            result.append({"name": name, "path": path, "bytes": bytes_})
    return result


def _select_input_files(*, input_dir: Path) -> list[ManifestFile]:
    manifest_files = _read_input_manifest_files()
    if manifest_files:
        return manifest_files

    if not input_dir.is_dir():
        return []

    return [
        {"name": path.name, "path": str(path), "bytes": path.stat().st_size}
        for path in sorted(input_dir.glob("*"))
        if path.is_file()
    ]


def _select_html_sources(*, input_files: list[ManifestFile]) -> list[Path]:
    html_files = [
        Path(file["path"])
        for file in input_files
        if Path(file["name"]).suffix.lower() in {".html", ".htm"}
    ]
    return sorted(html_files, key=lambda path: path.name.lower())


def _wrap_preview_html(*, html: str) -> str:
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


def _wrap_pdf_html(*, html: str) -> str:
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


def _read_user_settings() -> dict[str, object]:
    memory_path = os.environ.get("SKRIPTOTEKET_MEMORY_PATH")
    if not memory_path:
        return {}
    path = Path(memory_path)
    if not path.exists():
        return {}
    try:
        memory = json.loads(path.read_text(encoding="utf-8"))
        return memory.get("settings", {}) if isinstance(memory, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


@contextmanager
def _chdir(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


# ─── PDF-KONVERTERING ───


def _build_page_css(*, page_size: str, orientation: str) -> str:
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


def _build_weasyprint_recovery_css() -> str:
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


def _build_page_css_fallback(*, page_size: str, orientation: str) -> str:
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


def _inject_author_css(*, html: str, css: str) -> str:
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
    try:
        if not candidate.resolve().is_relative_to(base_resolved):
            return None
    except AttributeError:
        # Python < 3.9 not relevant, but keep defensive
        if not str(candidate.resolve()).startswith(str(base_resolved)):
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


def _extract_all_css(*, html: str, base_dir: Path) -> str:
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


def _select_print_css_for_document(
    *,
    html: str,
    base_dir: Path,
    page_size: str,
    orientation: str,
    doc_css: str | None = None,
) -> tuple[str, bool]:
    is_tool_editor = _looks_like_tool_editor_doc(html=html)
    if is_tool_editor:
        return _build_page_css(page_size=page_size, orientation=orientation), True

    if doc_css is None:
        doc_css = _extract_all_css(html=html, base_dir=base_dir)
    if _document_defines_at_page(css=doc_css):
        return "", False

    return _build_generic_page_css(page_size=page_size, orientation=orientation), False


def _inline_css_into_svgs(*, html: str, base_dir: Path, css: str | None = None) -> str:
    if css is None:
        css = _extract_all_css(html=html, base_dir=base_dir)
    if not css:
        return html
    svg_style = f'<style type="text/css"><![CDATA[\n{css}\n]]></style>'
    return re.sub(
        r"(?i)(<svg\b[^>]*>)(?!\s*<style\b)",
        rf"\1{svg_style}",
        html,
    )


def _normalize_html_for_weasyprint(
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
        _perf_record(
            perf_log,
            source=perf_source,
            label=f"{perf_label}:inline_svg",
            start=inline_start,
        )
    else:
        _perf_event(
            perf_log,
            source=perf_source,
            label=f"{perf_label}:inline_svg",
            extra={"skipped": True},
        )
    if not print_css.strip():
        _perf_record(
            perf_log,
            source=perf_source,
            label=f"{perf_label}:total",
            start=total_start,
        )
        return normalized
    normalized = _inject_author_css(html=normalized, css=print_css)
    _perf_record(
        perf_log,
        source=perf_source,
        label=f"{perf_label}:total",
        start=total_start,
    )
    return normalized


def _try_weasyprint(
    *,
    source: Path,
    pdf_path: Path,
    page_size: str,
    orientation: str,
    perf_log: list[dict[str, object]] | None = None,
) -> str | None:
    try:
        from weasyprint import DEFAULT_OPTIONS, HTML  # type: ignore
    except Exception:
        return None

    source_name = source.name
    html_raw = source.read_text(encoding="utf-8", errors="replace")
    base_dir = source.parent.resolve()
    base_url = source.parent.resolve().as_uri() + "/"
    render_options: dict[str, object] = {}
    cache: dict[str, object] = {}
    if "cache" in DEFAULT_OPTIONS:
        render_options["cache"] = cache
    elif "image_cache" in DEFAULT_OPTIONS:
        render_options["image_cache"] = cache

    def _render(*, html: str) -> None:
        HTML(string=html, base_url=base_url).write_pdf(str(pdf_path), **render_options)

    def _render_timed(*, html: str, label: str) -> None:
        start = perf_counter()
        _render(html=html)
        _perf_record(perf_log, source=source_name, label=label, start=start)

    html_raw = _wrap_pdf_html(html=html_raw)

    css_start = perf_counter()
    doc_css = _extract_all_css(html=html_raw, base_dir=base_dir)
    _perf_record(perf_log, source=source_name, label="css:extract", start=css_start)

    select_start = perf_counter()
    size_css, is_tool_editor_doc = _select_print_css_for_document(
        html=html_raw,
        base_dir=base_dir,
        page_size=page_size,
        orientation=orientation,
        doc_css=doc_css,
    )
    _perf_record(perf_log, source=source_name, label="css:select_print", start=select_start)

    try:
        html_content = _normalize_html_for_weasyprint(
            html=html_raw,
            base_dir=base_dir,
            print_css=size_css,
            doc_css=doc_css,
            perf_log=perf_log,
            perf_source=source_name,
            perf_label="normalize:initial",
        )
        _render_timed(html=html_content, label="render:initial")
    except AttributeError as exc:
        exc_text = str(exc)
        is_grid_crash = (
            "advancements" in exc_text
            or exc_text.strip() == "'NoneType' object has no attribute 'get'"
        )
        if not is_grid_crash:
            raise
        _perf_event(perf_log, source=source_name, label="fallback:grid")
        html_no_grid = html_raw.replace("display: grid", "display: block").replace(
            "display:grid", "display:block"
        )
        html_no_grid = _normalize_html_for_weasyprint(
            html=html_no_grid,
            base_dir=base_dir,
            print_css=size_css,
            doc_css=doc_css,
            perf_log=perf_log,
            perf_source=source_name,
            perf_label="normalize:grid_fallback",
        )
        _render_timed(html=html_no_grid, label="render:grid_fallback")
    except AssertionError:
        _perf_event(perf_log, source=source_name, label="fallback:assert")
        recovery_css = _build_weasyprint_recovery_css()
        normalized_html = locals().get("html_content")
        if not isinstance(normalized_html, str) or not normalized_html.strip():
            normalized_html = _normalize_html_for_weasyprint(
                html=html_raw,
                base_dir=base_dir,
                print_css=size_css,
                doc_css=doc_css,
                perf_log=perf_log,
                perf_source=source_name,
                perf_label="normalize:assert_retry",
            )
        normalized_html = re.sub(r"display\s*:\s*grid", "display: block", normalized_html)
        html_recovery = _inject_author_css(html=normalized_html, css=recovery_css)
        try:
            _render_timed(html=html_recovery, label="render:assert_recovery")
        except AssertionError:
            if not is_tool_editor_doc:
                raise
            _perf_event(perf_log, source=source_name, label="fallback:tool_editor")
            size_css = _build_page_css_fallback(page_size=page_size, orientation=orientation)
            html_content = _normalize_html_for_weasyprint(
                html=html_raw,
                base_dir=base_dir,
                print_css=size_css,
                doc_css=doc_css,
                perf_log=perf_log,
                perf_source=source_name,
                perf_label="normalize:tool_editor_fallback",
            )
            html_recovery = _inject_author_css(html=html_content, css=recovery_css)
            _render_timed(html=html_recovery, label="render:tool_editor_fallback")
    return "weasyprint"


def _try_pypandoc(
    *,
    source: Path,
    pdf_path: Path,
    page_size: str,
    orientation: str,  # noqa: ARG001
) -> str | None:
    try:
        import pypandoc  # type: ignore
    except Exception:
        return None

    # pypandoc stöder inte alla sidstorlekar direkt, men vi försöker
    extra_args = [f"--resource-path={source.parent}"]
    if page_size == "letter":
        extra_args.append("-V")
        extra_args.append("papersize=letter")

    with _chdir(source.parent):
        try:
            pypandoc.convert_file(
                str(source),
                to="pdf",
                outputfile=str(pdf_path),
                extra_args=["--pdf-engine=weasyprint", *extra_args],
            )
            return "pandoc(pypandoc, weasyprint-engine)"
        except Exception:
            pypandoc.convert_file(
                str(source),
                to="pdf",
                outputfile=str(pdf_path),
                extra_args=extra_args,
            )
            return "pandoc(pypandoc)"


# ─── STEG 1: FÖRHANDSGRANSKNING ───


def _handle_preview(*, input_files: list[ManifestFile]) -> dict[str, object]:
    html_sources = _select_html_sources(input_files=input_files)

    if not html_sources:
        return {
            "outputs": [
                _notice("error", "Ingen HTML-fil hittades. Ladda upp minst en .html/.htm-fil.")
            ],
            "next_actions": [],
            "state": None,
        }

    # Läs användarinställningar för standardvärden
    settings = _read_user_settings()
    default_page_size = settings.get("default_page_size", "a4")
    default_orientation = settings.get("default_orientation", "portrait")

    # Läs första HTML-filen för förhandsgranskning (max 96KB för html_sandboxed)
    first_html = html_sources[0]
    try:
        html_content = first_html.read_text(encoding="utf-8", errors="replace")
        # Begränsa till 90KB för att ha marginal
        if len(html_content) > 90_000:
            html_content = html_content[:90_000] + "\n<!-- ... (trunkerad) -->"
    except OSError:
        html_content = "<p>Kunde inte läsa HTML-filen.</p>"

    html_content = _wrap_preview_html(html=html_content)

    # Bygg outputs
    outputs: list[dict[str, object]] = [
        _notice("info", f"Förhandsgranska {len(html_sources)} HTML-fil(er) innan konvertering."),
        _markdown(
            f"**Första fil:** `{first_html.name}`\n\n"
            "Granska förhandsgranskningen nedan. När du är nöjd, klicka **Konvertera till PDF**."
        ),
        {"kind": "html_sandboxed", "html": html_content},
        {
            "kind": "table",
            "title": "Uppladdade filer",
            "columns": [
                {"key": "name", "label": "Namn"},
                {"key": "bytes", "label": "Storlek (byte)"},
            ],
            "rows": [{"name": f["name"], "bytes": f["bytes"]} for f in input_files],
        },
    ]

    # Bygg next_actions
    next_actions = [
        {
            "action_id": "convert",
            "label": "Konvertera till PDF",
            "kind": "form",
            "fields": [
                {
                    "name": "page_size",
                    "label": "Sidstorlek",
                    "kind": "enum",
                    "options": [
                        {"value": "a4", "label": "A4"},
                        {"value": "letter", "label": "Letter"},
                    ],
                },
                {
                    "name": "orientation",
                    "label": "Orientering",
                    "kind": "enum",
                    "options": [
                        {"value": "portrait", "label": "Stående"},
                        {"value": "landscape", "label": "Liggande"},
                    ],
                },
            ],
        },
        {
            "action_id": "reset",
            "label": "Börja om",
            "kind": "form",
            "fields": [],
        },
    ]

    # Spara state för nästa steg
    state = {
        "step": "preview",
        "html_files": [str(p) for p in html_sources],
        "input_files": input_files,
        "default_page_size": default_page_size,
        "default_orientation": default_orientation,
    }

    return {"outputs": outputs, "next_actions": next_actions, "state": state}


# ─── STEG 2: KONVERTERING ───


def _handle_action(*, action_path: Path, output_dir: Path) -> dict[str, object]:
    payload = json.loads(action_path.read_text(encoding="utf-8"))
    action_id = str(payload.get("action_id") or "").strip()
    input_data = payload.get("input") if isinstance(payload.get("input"), dict) else {}
    state = payload.get("state") if isinstance(payload.get("state"), dict) else {}

    # Hantera "börja om"
    if action_id == "reset":
        return {
            "outputs": [_notice("info", "Ladda upp nya filer för att fortsätta.")],
            "next_actions": [],
            "state": None,
        }

    # Hantera okänd action
    if action_id != "convert":
        return {
            "outputs": [_notice("error", f"Okänd action: '{action_id}'")],
            "next_actions": [],
            "state": None,
        }

    # Hämta konverteringsinställningar
    page_size = str(input_data.get("page_size", "a4"))
    orientation = str(input_data.get("orientation", "portrait"))
    page_css = _build_page_css(page_size=page_size, orientation=orientation)
    pdf_css_fingerprint = hashlib.sha256(page_css.encode("utf-8")).hexdigest()[:8]

    # Hämta filinfo från state
    html_file_paths = state.get("html_files", [])

    if not html_file_paths:
        return {
            "outputs": [_notice("error", "Ingen HTML-fil i state. Börja om.")],
            "next_actions": [],
            "state": None,
        }

    output_dir.mkdir(parents=True, exist_ok=True)

    # Konvertera alla HTML-filer
    used_pdf_names: set[str] = set()
    pdf_rows: list[dict[str, object]] = []
    chart_data: list[dict[str, object]] = []
    error_log_lines: list[str] = []
    perf_entries: list[dict[str, object]] = []

    for html_path_str in html_file_paths:
        source = Path(html_path_str)
        if not source.exists():
            continue

        html_size = source.stat().st_size

        # Generera unikt PDF-namn
        pdf_name_base = f"{source.stem}.pdf"
        pdf_name = pdf_name_base
        counter = 2
        while pdf_name in used_pdf_names:
            pdf_name = f"{source.stem}_{counter}.pdf"
            counter += 1
        used_pdf_names.add(pdf_name)
        pdf_path = output_dir / pdf_name

        # Försök konvertera
        backend: str | None = None
        errors: list[str] = []
        weasyprint_traceback: str | None = None

        try:
            backend = _try_weasyprint(
                source=source,
                pdf_path=pdf_path,
                page_size=page_size,
                orientation=orientation,
                perf_log=perf_entries,
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"WeasyPrint: {exc}")
            weasyprint_traceback = traceback.format_exc()

        if backend is None:
            full_message = " | ".join(errors) if errors else "Okänt fel"
            log_entry = f"{source.name}: {full_message}"
            if weasyprint_traceback:
                log_entry += "\n" + weasyprint_traceback.rstrip()
            error_log_lines.append(log_entry)
            pdf_rows.append(
                {
                    "source": source.name,
                    "pdf": pdf_name,
                    "status": "fel",
                    "bytes": 0,
                    "message": _shorten_for_table(full_message),
                }
            )
            continue

        if not pdf_path.exists():
            error_log_lines.append(f"{source.name}: Ingen PDF skapades")
            pdf_rows.append(
                {
                    "source": source.name,
                    "pdf": pdf_name,
                    "status": "fel",
                    "bytes": 0,
                    "message": "Ingen PDF skapades",
                }
            )
            continue

        pdf_size = pdf_path.stat().st_size
        pdf_rows.append(
            {
                "source": source.name,
                "pdf": pdf_name,
                "status": "ok",
                "bytes": pdf_size,
                "message": "",
            }
        )

        # Data för vega-lite diagram
        chart_data.append({"file": source.name, "type": "HTML", "bytes": html_size})
        chart_data.append({"file": pdf_name, "type": "PDF", "bytes": pdf_size})

    # Räkna resultat
    ok_count = sum(1 for row in pdf_rows if row["status"] == "ok")
    error_count = len(pdf_rows) - ok_count
    level = "info" if error_count == 0 else ("warning" if ok_count > 0 else "error")

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Bygg outputs
    error_suffix = f" ({error_count} fel)." if error_count else "."
    orient_label = "Liggande" if orientation == "landscape" else "Stående"
    outputs: list[dict[str, object]] = [
        _notice(level, f"{ok_count} PDF skapades{error_suffix}"),
        _markdown(
            f"**Konverterat:** {timestamp}\n\n"
            f"**Sidstorlek:** {page_size.upper()} | **Orientering:** {orient_label}\n\n"
            f"**PDF CSS:** `{pdf_css_fingerprint}`"
        ),
    ]

    if error_log_lines:
        (output_dir / "conversion-errors.txt").write_text(
            "\n".join(error_log_lines) + "\n",
            encoding="utf-8",
        )
        outputs.append(
            _markdown(
                "Fullständiga felmeddelanden finns i artefakten `conversion-errors.txt`. "
                "(Tabellen visar en kort sammanfattning.)"
            )
        )

    if perf_entries:
        (output_dir / "conversion-perf.json").write_text(
            json.dumps(perf_entries, indent=2) + "\n",
            encoding="utf-8",
        )
        outputs.append(
            _markdown(
                "Prestandalogg finns i artefakten `conversion-perf.json` "
                "(tider per steg/återförsök)."
            )
        )

    # Lägg till vega-lite diagram om vi har data
    if chart_data:
        outputs.append(
            {
                "kind": "vega_lite",
                "spec": {
                    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                    "width": 300,
                    "height": 200,
                    "title": "Filstorlek: HTML → PDF",
                    "data": {"values": chart_data},
                    "mark": "bar",
                    "encoding": {
                        "x": {"field": "file", "type": "nominal", "title": "Fil"},
                        "y": {"field": "bytes", "type": "quantitative", "title": "Storlek (byte)"},
                        "color": {"field": "type", "type": "nominal", "title": "Typ"},
                    },
                },
            }
        )

    # Resultattabell
    outputs.append(
        {
            "kind": "table",
            "title": "Konverteringsresultat",
            "columns": [
                {"key": "source", "label": "HTML"},
                {"key": "pdf", "label": "PDF"},
                {"key": "status", "label": "Status"},
                {"key": "bytes", "label": "Storlek (byte)"},
                {"key": "message", "label": "Meddelande"},
            ],
            "rows": pdf_rows,
        }
    )

    # next_actions för att börja om
    next_actions = [
        {
            "action_id": "reset",
            "label": "Konvertera nya filer",
            "kind": "form",
            "fields": [],
        },
    ]

    return {"outputs": outputs, "next_actions": next_actions, "state": None}


# ─── HUVUDENTRYPOINT ───


def run_tool(input_dir: str, output_dir: str) -> dict[str, object]:
    input_root = Path(input_dir)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    input_files = _select_input_files(input_dir=input_root)

    # Kolla om detta är en action-körning (från next_actions)
    action_file = next(
        (item for item in input_files if item.get("name") == "action.json"),
        None,
    )

    if action_file is not None:
        return _handle_action(action_path=Path(str(action_file["path"])), output_dir=output)

    # Fallback: kolla om action.json finns i input_dir
    action_path = input_root / "action.json"
    if action_path.is_file():
        return _handle_action(action_path=action_path, output_dir=output)

    # Vanlig körning: visa förhandsgranskning
    # Filtrera bort action.json från input_files
    filtered_files = [f for f in input_files if f.get("name") != "action.json"]

    if not filtered_files:
        return {
            "outputs": [_notice("error", "Ingen fil uppladdad. Ladda upp minst en HTML-fil.")],
            "next_actions": [],
            "state": None,
        }

    return _handle_preview(input_files=filtered_files)
