"""Grid compatibility helpers for Document Converter project previews.

Purpose:
    Preserve readable teacher HTML/CSS when WeasyPrint's native Grid layout path
    fails internally, without rewriting visible document text or weakening the
    uploaded-project asset boundary.

Relationships:
    Used only by the WeasyPrint project preview renderer during its
    best-effort retry path and by the retry asset fetcher for linked CSS.
"""

from __future__ import annotations

from html import escape
from html.parser import HTMLParser
from types import TracebackType
from typing import Any, cast

_GRID_DISPLAY_VALUES = {"grid", "inline-grid"}
_GRID_PROPERTY_PREFIX = "grid"
_WEASYPRINT_GRID_TRACE_SEGMENT = "/weasyprint/layout/grid.py"
_WEASYPRINT_GRID_MESSAGES = ("advancements", "'NoneType' object has no attribute 'get'")
_GRID_BLOCK_OVERRIDE_CSS = (
    "body, main, article, section, header, footer, nav, aside, figure, figcaption, "
    "div, form, fieldset, ul, ol, li, p, h1, h2, h3, h4, h5, h6 { display: block !important; }\n"
    "span, a, strong, em, b, i, small, code { display: inline !important; }\n"
    "table { display: table !important; } thead { display: table-header-group !important; }\n"
    "tbody { display: table-row-group !important; }\n"
    "tfoot { display: table-footer-group !important; }\n"
    "tr { display: table-row !important; } th, td { display: table-cell !important; }\n"
    "img, svg, canvas { max-width: 100% !important; height: auto !important; }"
)


def is_weasyprint_grid_layout_error(exc: BaseException) -> bool:
    """Return whether ``exc`` is a known WeasyPrint Grid layout failure."""
    if not _traceback_contains_weasyprint_grid(exc.__traceback__):
        return False
    if isinstance(exc, AssertionError):
        return True
    return isinstance(exc, AttributeError) and any(
        message in str(exc) for message in _WEASYPRINT_GRID_MESSAGES
    )


def prepare_grid_compatibility_html(html: str) -> str:
    """Soften HTML-owned CSS without mutating visible body text."""
    parser = _GridCompatibilityHtmlParser()
    parser.feed(html)
    parser.close()
    return parser.result


def prepare_grid_compatibility_css(css_text: str) -> str:
    """Remove Grid-specific layout while preserving other print-relevant CSS."""
    try:
        softened = _soften_grid_css_with_tinycss2(css_text=css_text)
    except Exception:
        softened = css_text
    return f"{softened}\n{_GRID_BLOCK_OVERRIDE_CSS}"


def prepare_grid_compatibility_css_bytes(content: bytes) -> bytes:
    """Decode and soften linked CSS for the compatibility retry fetcher."""
    css_text = content.decode("utf-8-sig", errors="replace")
    return prepare_grid_compatibility_css(css_text).encode("utf-8")


def _traceback_contains_weasyprint_grid(traceback: TracebackType | None) -> bool:
    current = traceback
    while current is not None:
        filename = current.tb_frame.f_code.co_filename.replace("\\", "/")
        if (
            filename.endswith(_WEASYPRINT_GRID_TRACE_SEGMENT)
            or _WEASYPRINT_GRID_TRACE_SEGMENT in filename
        ):
            return True
        current = current.tb_next
    return False


def _prepare_grid_compatibility_inline_style(css_text: str) -> str:
    try:
        return _serialize_grid_compatible_declarations(css_text)
    except Exception:
        return css_text


class _GridCompatibilityHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._chunks: list[str] = []
        self._style_depth = 0

    @property
    def result(self) -> str:
        return "".join(self._chunks)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._chunks.append(self._start_tag(tag=tag, attrs=attrs, closed=False))
        if tag.lower() == "style":
            self._style_depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._chunks.append(self._start_tag(tag=tag, attrs=attrs, closed=True))

    def handle_endtag(self, tag: str) -> None:
        self._chunks.append(f"</{tag}>")
        if tag.lower() == "style" and self._style_depth:
            self._style_depth -= 1

    def handle_data(self, data: str) -> None:
        self._chunks.append(prepare_grid_compatibility_css(data) if self._style_depth else data)

    def handle_entityref(self, name: str) -> None:
        self._chunks.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self._chunks.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        self._chunks.append(f"<!--{data}-->")

    def handle_decl(self, decl: str) -> None:
        self._chunks.append(f"<!{decl}>")

    def handle_pi(self, data: str) -> None:
        self._chunks.append(f"<?{data}>")

    def _start_tag(self, *, tag: str, attrs: list[tuple[str, str | None]], closed: bool) -> str:
        attr_text = "".join(self._attribute_text(name=name, value=value) for name, value in attrs)
        suffix = " /" if closed else ""
        return f"<{tag}{attr_text}{suffix}>"

    def _attribute_text(self, *, name: str, value: str | None) -> str:
        if value is None:
            return f" {name}"
        prepared = (
            _prepare_grid_compatibility_inline_style(value) if name.lower() == "style" else value
        )
        return f' {name}="{escape(prepared, quote=True)}"'


def _soften_grid_css_with_tinycss2(*, css_text: str) -> str:
    import tinycss2  # type: ignore[import-untyped]

    rules = tinycss2.parse_stylesheet(css_text, skip_comments=True, skip_whitespace=True)
    return "".join(_serialize_grid_compatible_rule(rule=rule) for rule in rules)


def _serialize_grid_compatible_rule(*, rule: Any) -> str:
    import tinycss2  # type: ignore[import-untyped]

    if rule.type == "qualified-rule":
        selector = tinycss2.serialize(rule.prelude).strip()
        declarations = _serialize_grid_compatible_declarations(rule.content)
        return f"{selector}{{{declarations}}}" if selector and declarations else ""
    if rule.type == "at-rule" and rule.content is not None:
        keyword = rule.at_keyword.lower()
        prelude = tinycss2.serialize(rule.prelude).strip()
        if keyword in {"media", "supports", "layer"}:
            nested_rules = tinycss2.parse_rule_list(
                rule.content, skip_comments=True, skip_whitespace=True
            )
            nested = "".join(
                _serialize_grid_compatible_rule(rule=nested_rule) for nested_rule in nested_rules
            )
            spacer = " " if prelude else ""
            return f"@{rule.at_keyword}{spacer}{prelude}{{{nested}}}"
    return cast(str, tinycss2.serialize([rule]))


def _serialize_grid_compatible_declarations(content: Any) -> str:
    import tinycss2  # type: ignore[import-untyped]

    declarations = tinycss2.parse_blocks_contents(content, skip_comments=True, skip_whitespace=True)
    serialized: list[str] = []
    for declaration in declarations:
        if declaration.type != "declaration":
            serialized.append(tinycss2.serialize([declaration]))
            continue
        name = declaration.lower_name
        value = tinycss2.serialize(declaration.value).strip()
        important = " !important" if declaration.important else ""
        if name == "display" and value.lower() in _GRID_DISPLAY_VALUES:
            serialized.append(f"display:block{important};")
            continue
        if name.startswith(_GRID_PROPERTY_PREFIX):
            continue
        serialized.append(f"{declaration.name}:{value}{important};")
    return "".join(serialized)
