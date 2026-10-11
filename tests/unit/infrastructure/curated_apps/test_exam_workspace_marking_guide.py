"""Marking guide (rättningsmall) on free_text items: field rule, container, DOCX and PDF (D31)."""

import io
import json
from uuid import uuid4

import pytest
from docx import Document
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_pdf_export import (
    native_exam_to_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeChoice,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeItemReview,
    NativeItemReviewState,
    NativeParagraph,
    NativeParseOrigin,
    NativeTextSegment,
    native_exam_document_json_bytes,
    parse_native_exam_document,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    exam_workspace_docx_writer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)

_SWEDISH_BODY = "Förklara vad som är en bisats och hur den används för att binda ihop en text."
_ENGLISH_BODY = "Explain what the clause is and how it is used to connect the text."
_GUIDE = "Ge 2 poäng för definitionen\n1 poäng för <exemplet> & motiveringen"


def _review() -> NativeItemReview:
    return NativeItemReview(
        state=NativeItemReviewState.REVIEW_COMPLETE,
        parse_origin=NativeParseOrigin.TEACHER_CREATED,
    )


def _paragraph(text: str) -> NativeParagraph:
    return NativeParagraph(segments=(NativeTextSegment(text=text),))


def _free_text(body: str, *, marking_guide: str | None) -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        body=(_paragraph(body),),
        points=3,
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        marking_guide=marking_guide,
        review=_review(),
    )


def _document(body: str, *, marking_guide: str | None) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Prov",
        items=(_free_text(body, marking_guide=marking_guide),),
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def _docx_lines(document: NativeExamDocument) -> list[str]:
    content = exam_workspace_docx_writer.ExamWorkspaceDocxWriter().build_docx_bytes(document)
    return [paragraph.text for paragraph in Document(io.BytesIO(content)).paragraphs]


def test_guide_on_a_choice_item_is_rejected() -> None:
    with pytest.raises(ValidationError, match="only free_text items carry a marking guide"):
        NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.SINGLE_CHOICE,
            body=(_paragraph("Vilket är rätt?"),),
            points=1,
            choices=(
                NativeChoice(choice_id="choice_001", text="a"),
                NativeChoice(choice_id="choice_002", text="b"),
            ),
            answer_key=NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
                correct_choice_ids=("choice_001",),
            ),
            marking_guide="Rätt är a",
            review=_review(),
        )


def test_document_json_without_the_field_loads_with_no_guide() -> None:
    document = _document(_SWEDISH_BODY, marking_guide=None)
    payload = json.loads(native_exam_document_json_bytes(document))
    del payload["items"][0]["marking_guide"]
    loaded = parse_native_exam_document(json.dumps(payload).encode("utf-8"))
    assert loaded.items[0].marking_guide is None


def test_guide_survives_the_container_round_trip() -> None:
    document = _document(_SWEDISH_BODY, marking_guide=_GUIDE)
    codec = ExamWorkspaceContainerCodec()
    built = codec.build(content=ExamWorkspaceContainerContent(document=document))
    assert codec.parse(content=built).document.items[0].marking_guide == _GUIDE


@pytest.mark.parametrize(
    ("body", "label"),
    [(_SWEDISH_BODY, "Rättningsmall"), (_ENGLISH_BODY, "Marking guide")],
)
def test_docx_answer_key_prints_the_guide_in_the_exam_language(body: str, label: str) -> None:
    lines = _docx_lines(_document(body, marking_guide=_GUIDE))
    assert f"{label}: {_GUIDE}" in lines
    other = "Marking guide" if label == "Rättningsmall" else "Rättningsmall"
    assert not any(line.startswith(other) for line in lines)


@pytest.mark.parametrize("body", [_SWEDISH_BODY, _ENGLISH_BODY])
def test_docx_without_a_guide_has_no_answer_key_section(body: str) -> None:
    lines = _docx_lines(_document(body, marking_guide=None))
    assert not any(line in ("Facit", "Answer key") for line in lines)
    assert not any(line.startswith(("Rättningsmall", "Marking guide")) for line in lines)


@pytest.mark.parametrize(
    ("body", "label"),
    [(_SWEDISH_BODY, "Rättningsmall"), (_ENGLISH_BODY, "Marking guide")],
)
def test_pdf_prints_the_escaped_guide_under_the_language_label(body: str, label: str) -> None:
    result = native_exam_to_pdf_document(_document(body, marking_guide=_GUIDE))
    assert result.status is DigiExamExamNetPdfStatus.SUCCESS
    assert (
        f'<p class="answer-key">{label}: Ge 2 poäng för definitionen<br>'
        "1 poäng för &lt;exemplet&gt; &amp; motiveringen</p>"
    ) in result.html


@pytest.mark.parametrize("body", [_SWEDISH_BODY, _ENGLISH_BODY])
def test_pdf_without_a_guide_prints_no_answer_key(body: str) -> None:
    result = native_exam_to_pdf_document(_document(body, marking_guide=None))
    assert result.status is DigiExamExamNetPdfStatus.SUCCESS
    assert 'class="answer-key"' not in result.html
