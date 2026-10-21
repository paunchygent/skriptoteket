"""Tests for the kept Exam.net PDF item strategies and live PDF rendering.

Purpose:
    Prove that the kept Exam.net PDF target strategies render neutral item
    semantics to the promoted Exam.net PDF-converter shape with fail-closed
    warnings, and that the assembled HTML still produces live PDF artifacts
    through WeasyPrint, asserted with pypdf.

Relationships:
    - Exercises the kept strategy registry in
      `domain.examnet_pdf_item_registry` with hand-built neutral
      `domain.exam_pdf_item_semantics` values.
    - Assembles live documents with `domain.digiexam_examnet_pdf_html` and
      renders them through the in-process Exam.net PDF renderer seam.
"""

from __future__ import annotations

import base64
from io import BytesIO

import pytest
from pypdf import PdfReader

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfAssetFile,
    DigiExamExamNetPdfDocument,
    DigiExamExamNetPdfItemRender,
    DigiExamExamNetPdfStatus,
    DigiExamExamNetPdfWarningCode,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_html import (
    build_examnet_pdf_html,
)
from skriptoteket.domain.curated_apps.exam_conversion.exam_pdf_item_semantics import (
    PdfExamAnswerKeySemantics,
    PdfExamGapAnswerSemantics,
    PdfExamGapSemantics,
    PdfExamItemKind,
    PdfExamItemSemantics,
    PdfExamOptionSemantics,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_pdf_item_registry import (
    DEFAULT_EXAMNET_PDF_ITEM_STRATEGY_REGISTRY,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_pdf_target_profile import (
    DEFAULT_EXAMNET_PDF_TARGET_PROFILE_CONTEXT,
    ExamNetPdfItemLabelPolicy,
    ExamNetPdfTargetProfileContext,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
)

pytestmark = pytest.mark.unit

_REGISTRY = DEFAULT_EXAMNET_PDF_ITEM_STRATEGY_REGISTRY
_CONTEXT = DEFAULT_EXAMNET_PDF_TARGET_PROFILE_CONTEXT

_ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def _render_html(item: PdfExamItemSemantics) -> str:
    result = _REGISTRY.render(item=item, context=_CONTEXT)
    assert result.warnings == ()
    assert result.item is not None
    return result.item.html


def _open_response(
    *,
    item_id: str = "item-001",
    sequence: int = 1,
    points: int | float = 3,
    prompt_html: str = "<p>Explain the water cycle.</p>",
) -> PdfExamItemSemantics:
    return PdfExamItemSemantics(
        item_id=item_id,
        sequence=sequence,
        kind=PdfExamItemKind.OPEN_RESPONSE,
        points=points,
        prompt_html=prompt_html,
    )


def _single_choice(
    *,
    item_id: str = "item-002",
    options: tuple[tuple[int, str], ...] = ((1, "Alpha"), (2, "Beta")),
    correct_option_ids: tuple[int, ...] = (2,),
    available: bool = True,
) -> PdfExamItemSemantics:
    return PdfExamItemSemantics(
        item_id=item_id,
        sequence=2,
        kind=PdfExamItemKind.SINGLE_CHOICE,
        points=2,
        prompt_html="<p>Choose the Greek letter.</p>",
        options=tuple(
            PdfExamOptionSemantics(option_id=option_id, text=text) for option_id, text in options
        ),
        answer_key=PdfExamAnswerKeySemantics(
            available=available, correct_option_ids=correct_option_ids
        ),
    )


def _multiple_response(
    *,
    options: tuple[tuple[int, str], ...] = ((1, "First"), (2, "Between"), (3, "Third")),
    correct_option_ids: tuple[int, ...] = (1, 3),
) -> PdfExamItemSemantics:
    return PdfExamItemSemantics(
        item_id="item-003",
        sequence=3,
        kind=PdfExamItemKind.MULTIPLE_RESPONSE,
        points=4,
        prompt_html="<p>Choose the ordinal words.</p>",
        options=tuple(
            PdfExamOptionSemantics(option_id=option_id, text=text) for option_id, text in options
        ),
        answer_key=PdfExamAnswerKeySemantics(available=True, correct_option_ids=correct_option_ids),
    )


def _gap_fill(
    *,
    gaps: tuple[str, ...] = ("gap-1",),
    answers: tuple[tuple[str, str], ...] = (("gap-1", "Stockholm"), ("gap-1", "stockholm")),
) -> PdfExamItemSemantics:
    return PdfExamItemSemantics(
        item_id="item-004",
        sequence=4,
        kind=PdfExamItemKind.GAP_OPEN_CLOZE,
        points=1,
        prompt_html="<p>Name Sweden's capital.</p>",
        gaps=tuple(PdfExamGapSemantics(gap_id=gap_id) for gap_id in gaps),
        answer_key=PdfExamAnswerKeySemantics(
            available=True,
            correct_gap_answers=tuple(
                PdfExamGapAnswerSemantics(gap_id=gap_id, value=value) for gap_id, value in answers
            ),
        ),
    )


def test_registry_uses_promoted_converter_shape_without_option_labels() -> None:
    html = "\n".join(
        (
            _render_html(_open_response()),
            _render_html(_single_choice()),
            _render_html(_multiple_response()),
            _render_html(_gap_fill()),
        )
    )

    assert "Points:" not in html
    assert "Poängvärde: 2" in html
    assert "Typ: Fritext" in html
    assert "Skriv ditt svar i Exam.net." not in html
    assert "Type: Multiple choice" in html
    assert "Choose one answer" not in html
    assert "<p>Alpha</p>" in html
    assert "<p>Beta</p>" in html
    assert "Correct answer: Beta" in html
    assert "Type: Multiple response" in html
    assert "Choose all correct answers" not in html
    assert "Correct answers: First; Third" in html
    assert html.count("Typ: Fritext") == 1
    assert "Typ: Lucktext" in html
    assert "Type: Short answer" not in html
    assert "Correct answers: Stockholm; stockholm" in html
    assert "A. Alpha" not in html
    assert "<li>" not in html


def test_registry_blocks_machine_marked_item_without_answer_key() -> None:
    result = _REGISTRY.render(item=_single_choice(available=False), context=_CONTEXT)

    assert result.item is None
    assert DigiExamExamNetPdfWarningCode.MANUAL_ANSWER_KEY_REQUIRED in {
        warning.code for warning in result.warnings
    }


def test_registry_keeps_multigap_blocked_without_key() -> None:
    item = _gap_fill(
        gaps=tuple(f"gap-{index}" for index in range(1, 6)),
        answers=(),
    )
    result = _REGISTRY.render(
        item=PdfExamItemSemantics(
            item_id=item.item_id,
            sequence=item.sequence,
            kind=item.kind,
            points=5,
            prompt_html="<p>Fyll i ___ ___ ___ ___ ___.</p>",
            gaps=item.gaps,
            answer_key=PdfExamAnswerKeySemantics(available=False),
        ),
        context=_CONTEXT,
    )

    assert result.item is None
    assert DigiExamExamNetPdfWarningCode.MANUAL_ANSWER_KEY_REQUIRED in {
        warning.code for warning in result.warnings
    }


def test_registry_keeps_manual_multigap_keys_in_lucktext_shape() -> None:
    item = _gap_fill(
        gaps=tuple(f"gap-{index}" for index in range(1, 6)),
        answers=tuple((f"gap-{index}", f"facit {index}") for index in range(1, 6)),
    )
    html = _render_html(
        PdfExamItemSemantics(
            item_id=item.item_id,
            sequence=item.sequence,
            kind=item.kind,
            points=5,
            prompt_html="<p>Fyll i ___ ___ ___ ___ ___.</p>",
            gaps=item.gaps,
            answer_key=item.answer_key,
        )
    )

    assert "Typ: Lucktext" in html
    assert "Type: Short answer" not in html
    assert "Correct answers:" in html
    assert "Lucka 1: facit 1" in html
    assert "Lucka 5: facit 5" in html
    assert "Manuell bedömning" not in html


def test_examnet_pdf_target_profile_labels_do_not_mutate_item_semantics() -> None:
    original_item = _open_response()
    target_context = ExamNetPdfTargetProfileContext(
        target_id="examnet_pdf",
        profile_version="test-profile",
        label_policy=ExamNetPdfItemLabelPolicy(free_text_type_label="Profile free text"),
    )

    result = _REGISTRY.render(item=original_item, context=target_context)

    assert not result.warnings
    assert result.item is not None
    assert "Typ: Profile free text" in result.item.html
    assert original_item == _open_response()


def test_registry_strips_source_labelled_options_at_target_boundary() -> None:
    html = "\n".join(
        (
            _render_html(_single_choice(options=((1, "A. Alpha"), (2, "B) Beta")))),
            _render_html(
                _multiple_response(
                    options=((1, "1. First"), (2, "Between"), (3, "3) Third")),
                )
            ),
        )
    )

    assert "<p>Alpha</p>" in html
    assert "<p>Beta</p>" in html
    assert "Correct answer: Beta" in html
    assert "Correct answers: First; Third" in html
    assert "A. Alpha" not in html
    assert "B) Beta" not in html
    assert "1. First" not in html
    assert "3) Third" not in html


def test_registry_blocks_duplicate_options_after_label_stripping() -> None:
    result = _REGISTRY.render(
        item=_single_choice(options=((1, "A. Alpha"), (2, "B. Alpha"))),
        context=_CONTEXT,
    )

    assert result.item is None
    assert DigiExamExamNetPdfWarningCode.ALTERNATIVE_ANSWER_KEY_MISMATCH in {
        warning.code for warning in result.warnings
    }
    assert [
        warning.message
        for warning in result.warnings
        if warning.code == DigiExamExamNetPdfWarningCode.ALTERNATIVE_ANSWER_KEY_MISMATCH
    ] == ["Item item-002 cannot render safely: duplicate option text is unsafe."]


def test_registry_preserves_unsupported_source_type_warning() -> None:
    result = _REGISTRY.render(
        item=PdfExamItemSemantics(
            item_id="item-001",
            sequence=1,
            kind=PdfExamItemKind.UNSUPPORTED,
            points=3,
            prompt_html="<p>Explain the water cycle.</p>",
            source_item_type_label="unknown",
        ),
        context=_CONTEXT,
    )

    assert result.item is None
    assert [
        warning.message
        for warning in result.warnings
        if warning.code == DigiExamExamNetPdfWarningCode.UNSUPPORTED_ITEM_TYPE
    ] == ["Item type unknown has no governed Exam.net PDF-converter target shape yet."]


def test_live_examnet_pdf_renderer_generates_pdf_with_embedded_image() -> None:
    html = _render_html(
        _open_response(
            points=1,
            prompt_html=(
                "<p>Look at the embedded prompt image.</p>"
                '<p><img src="images/asset.png" class="prompt-image"></p>'
            ),
        )
    )
    document = DigiExamExamNetPdfDocument(
        status=DigiExamExamNetPdfStatus.SUCCESS,
        html=build_examnet_pdf_html(
            source_filename="embedded-open-ended.dxe",
            items=(DigiExamExamNetPdfItemRender(html=html),),
        ),
        asset_files=(
            DigiExamExamNetPdfAssetFile(
                asset_id="asset",
                relative_path="images/asset.png",
                media_type="image/png",
                payload=_ONE_PIXEL_PNG,
            ),
        ),
        warnings=(),
    )

    assert document.status == DigiExamExamNetPdfStatus.SUCCESS
    assert "data-image-id" not in document.html
    assert len(document.asset_files) == 1

    pdf_bytes = WeasyPrintExamNetPdfRenderer().render_pdf(document=document)
    reader = PdfReader(BytesIO(pdf_bytes))

    assert len(reader.pages) == 1
    page = reader.pages[0]
    text = page.extract_text()
    assert "Fråga 1" in text
    assert "Poängvärde: 1" in text
    assert "Typ: Fritext" in text
    assert "Skriv ditt svar i Exam.net." not in text
    assert "Look at the embedded prompt image." in text
    assert page.images


def test_live_pdf_preserves_fractional_points_and_image_placeholders() -> None:
    placeholder = "Bild saknas – lägg till bilden innan du använder provet."
    html = _render_html(
        _open_response(
            points=0.25,
            prompt_html=(f"<p>Besvara frågan.</p><p>{placeholder}</p><p>{placeholder}</p>"),
        )
    )

    assert html.count(placeholder) == 2

    live_document = DigiExamExamNetPdfDocument(
        status=DigiExamExamNetPdfStatus.SUCCESS,
        html=build_examnet_pdf_html(
            source_filename="fractional-missing-images.dxe",
            items=(DigiExamExamNetPdfItemRender(html=html),),
        ),
        asset_files=(),
        warnings=(),
    )

    pdf_bytes = WeasyPrintExamNetPdfRenderer().render_pdf(document=live_document)
    reader = PdfReader(BytesIO(pdf_bytes))
    text = " ".join(page.extract_text() for page in reader.pages)

    assert pdf_bytes.startswith(b"%PDF")
    assert "Fråga 1" in text
    assert "Poängvärde: 0.25" in text
    assert text.count("Bild saknas") == 2
