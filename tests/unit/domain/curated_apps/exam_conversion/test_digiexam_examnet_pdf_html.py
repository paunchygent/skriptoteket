"""The PDF stylesheet styles each class the export emits for parents and matching."""

import re

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_html import (
    build_examnet_pdf_html,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_pdf_export import (
    native_exam_to_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
)
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import (
    parent_over,
    recorded_document,
    recorded_items,
)

_NEW_CLASSES = ("parent-instruction", "match-left", "match-right")


def _rules(html: str) -> dict[str, str]:
    style = html.split("<style>")[1].split("</style>")[0]
    return {
        " ".join(selector.split()): body.strip()
        for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", style)
    }


def _document_with_parent_and_matching():
    items = recorded_items()
    assert any(item.kind is NativeExamItemKind.MATCHING for item in items)
    parent = parent_over("parent_001", "Shared instruction line.", 1, 2, 3, 4)
    return native_exam_to_pdf_document(recorded_document((parent,), items=items))


def test_every_class_the_export_emits_for_parents_and_matching_has_a_rule():
    document = _document_with_parent_and_matching()
    selectors = " ".join(_rules(document.html))

    for name in _NEW_CLASSES:
        assert f'class="{name}"' in document.html
        assert f".{name}" in selectors
    assert "font-weight: 700" in _rules(document.html)[".parent-instruction"]


def test_the_new_rules_select_only_their_own_classes():
    html = build_examnet_pdf_html(source_filename="exam.docx", items=())

    new = [s for s in _rules(html) if any(name in s for name in _NEW_CLASSES)]
    assert new
    for selector in new:
        for part in selector.split(","):
            assert part.strip().split()[0] in {f".{name}" for name in _NEW_CLASSES}


def test_weasyprint_renders_the_styled_parent_and_matching_document():
    document = _document_with_parent_and_matching()

    assert WeasyPrintExamNetPdfRenderer().render_pdf(document=document).startswith(b"%PDF")
