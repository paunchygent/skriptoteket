"""Shared builders and inspectors for the print-HTML suites (TASK-SKRIPT-40-04-20).

The student/facit shell suite and the marked-runs suite both render
``PrintDocument`` values through ``render_print_html``; this module owns the
shared asset/document/render/stylesheet helpers so neither test file duplicates
them.
"""

import hashlib

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    ExamPrintVariant,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_document import (
    PrintDocument,
    PrintInstruction,
    PrintQuestion,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_html import (
    render_print_html,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
)

ASSET_ID = "asset_0123456789abcdef"
PNG_PAYLOAD = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"


def asset(
    payload: bytes,
    *,
    media_type: str = "image/png",
    sha256: str | None = None,
    byte_length: int | None = None,
) -> NativeExamAsset:
    return NativeExamAsset(
        asset_id=ASSET_ID,
        sha256=sha256 if sha256 is not None else hashlib.sha256(payload).hexdigest(),
        media_type=media_type,
        byte_length=byte_length if byte_length is not None else len(payload),
    )


def document(
    *entries: PrintInstruction | PrintQuestion,
    variant: ExamPrintVariant = ExamPrintVariant.STUDENT,
    title: str = "Omprov: grammatik",
) -> PrintDocument:
    return PrintDocument(variant=variant, title=title, entries=tuple(entries))


def render(
    print_document: PrintDocument,
    *,
    assets: tuple[NativeExamAsset, ...] = (),
    assets_by_id: dict[str, bytes] | None = None,
) -> str:
    return render_print_html(print_document, assets=assets, assets_by_id=assets_by_id or {})


def style_text(html: str) -> str:
    """The rendered document's stylesheet text, for asserting the generated house CSS."""
    start = html.index("<style>") + len("<style>")
    return html[start : html.index("</style>")]
