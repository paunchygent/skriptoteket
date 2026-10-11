"""WeasyPrint rendering with recovery fallbacks."""

from __future__ import annotations

import re
from pathlib import Path
from time import perf_counter
from typing import TypedDict

from .html_prep import (
    build_page_css_fallback,
    build_weasyprint_recovery_css,
    extract_all_css,
    inject_author_css,
    normalize_html_for_weasyprint,
    select_print_css_for_document,
    wrap_pdf_html,
)
from .perf import perf_event, perf_record


class _WeasyprintRenderOptions(TypedDict, total=False):
    cache: dict[str, object]
    image_cache: dict[str, object]


def try_weasyprint(
    *,
    source: Path,
    pdf_path: Path,
    page_size: str,
    orientation: str,
    perf_log: list[dict[str, object]] | None = None,
) -> str | None:
    try:
        from weasyprint import DEFAULT_OPTIONS, HTML
    except Exception:
        return None

    source_name = source.name
    html_raw = source.read_text(encoding="utf-8", errors="replace")
    base_dir = source.parent.resolve()
    base_url = source.parent.resolve().as_uri() + "/"
    render_options: _WeasyprintRenderOptions = {}
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
        perf_record(perf_log, source=source_name, label=label, start=start)

    html_raw = wrap_pdf_html(html=html_raw)

    css_start = perf_counter()
    doc_css = extract_all_css(html=html_raw, base_dir=base_dir)
    perf_record(perf_log, source=source_name, label="css:extract", start=css_start)

    select_start = perf_counter()
    size_css, is_tool_editor_doc = select_print_css_for_document(
        html=html_raw,
        base_dir=base_dir,
        page_size=page_size,
        orientation=orientation,
        doc_css=doc_css,
    )
    perf_record(perf_log, source=source_name, label="css:select_print", start=select_start)

    try:
        html_content = normalize_html_for_weasyprint(
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
        perf_event(perf_log, source=source_name, label="fallback:grid")
        html_no_grid = html_raw.replace("display: grid", "display: block").replace(
            "display:grid", "display:block"
        )
        html_no_grid = normalize_html_for_weasyprint(
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
        perf_event(perf_log, source=source_name, label="fallback:assert")
        recovery_css = build_weasyprint_recovery_css()
        normalized_html = locals().get("html_content")
        if not isinstance(normalized_html, str) or not normalized_html.strip():
            normalized_html = normalize_html_for_weasyprint(
                html=html_raw,
                base_dir=base_dir,
                print_css=size_css,
                doc_css=doc_css,
                perf_log=perf_log,
                perf_source=source_name,
                perf_label="normalize:assert_retry",
            )
        normalized_html = re.sub(r"display\s*:\s*grid", "display: block", normalized_html)
        html_recovery = inject_author_css(html=normalized_html, css=recovery_css)
        try:
            _render_timed(html=html_recovery, label="render:assert_recovery")
        except AssertionError:
            if not is_tool_editor_doc:
                raise
            perf_event(perf_log, source=source_name, label="fallback:tool_editor")
            size_css = build_page_css_fallback(page_size=page_size, orientation=orientation)
            html_content = normalize_html_for_weasyprint(
                html=html_raw,
                base_dir=base_dir,
                print_css=size_css,
                doc_css=doc_css,
                perf_log=perf_log,
                perf_source=source_name,
                perf_label="normalize:tool_editor_fallback",
            )
            html_recovery = inject_author_css(html=html_content, css=recovery_css)
            _render_timed(html=html_recovery, label="render:tool_editor_fallback")
    return "weasyprint"
