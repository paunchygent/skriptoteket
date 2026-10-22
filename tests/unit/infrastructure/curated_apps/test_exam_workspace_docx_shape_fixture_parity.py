"""The drawn figures of ``metodprov_med_bilder.docx`` reach every export below the UI.

TASK-SKRIPT-39-04-22 (D5, D6, D8-D11): the Word import gives questions 5 and 6 their
pictures at the places the PDF import puts them; each picture's asset keeps the Word
shapes it was drawn from; the Word export writes those shapes back and every other
export uses the picture; a picture the teacher replaces or removes takes its shapes with it.

The chunker, the build state and its admission, document assembly and the export renderer
with its real QTI, Word and print writers are the production code. The model's reply is a
scripted fixture, scoped to questions 5 to 7 (the questions that hold a picture); it is
not an AI result. The picture replacement mirrors the editor's document edit (a new asset
without shapes, the old asset leaves the document), because the editor is frontend code.
"""

from __future__ import annotations

import base64
import hashlib
import io
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest
from docx import Document
from lxml import etree  # type: ignore[import-untyped]  # transitive of python-docx, no stubs
from PIL import Image
from pydantic import JsonValue
from pypdf import PdfReader

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceExportTarget
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_export_renderer import (
    ExamWorkspaceExportRenderer,
)
from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    ExamPrintVariant,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import DocxBuildResult
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxImage,
    asset_id_for,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_own_instructions import (
    DRAWING_SHOWN,
    LEFT_OUT_REASON,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_document import (
    build_print_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_html import render_print_html
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_records import (
    NativeExamRetryChunk,
    NativeExamRetryImage,
    NativeExamRetrySource,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeItemReviewState,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_print_renderer import (
    WeasyPrintExamPrintRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_writer import (  # noqa: E501
    ExamWorkspaceDocxWriter,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_chunker import (  # noqa: E501
    PdfPlumberExamChunker,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)

pytestmark = pytest.mark.unit

_FIXTURES = Path("tests/fixtures/exam_conversion/pdf_corpus")
_DOCX = _FIXTURES / "metodprov_med_bilder.docx"
_PDF = _FIXTURES / "metodprov_med_bilder.pdf"

_NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "wpg": "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup",
}
_NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_Q5_ANCHOR, _Q6_ANCHOR, _CHART_ANCHOR = "body:0029", "body:0036", "body:0043"
_Q5_LABELS = ("Svenska gymnasieelever (populationen)", "Elever på ett program (urvalet)")
_Q6_LABELS = ("Alla elever på skolan", "Elever som är i biblioteket", "Svarar på frågan")
# The chunks questions 5 to 7 own, heading of question 5 to facit of question 7.
_FIRST_SCOPED, _LAST_SCOPED = 26, 46
_NEW_PICTURE = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAECAIAAAA8r+mnAAAAFElEQVR4nGOUbLJhwAaYsIqSJQEAVB8A33yzxnAAAAAASUVORK5CYII="
)


def _word_chunks() -> tuple[DocxChunk, ...]:
    return PythonDocxExamChunker().chunk(content=_DOCX.read_bytes())


def _words(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def _places(chunks: tuple[DocxChunk, ...]) -> list[tuple[str, str]]:
    """Each drawing's place: the text right before it and right after it."""
    return [
        (_words(chunks[index - 1].text), _words(chunks[index + 1].text))
        for index, chunk in enumerate(chunks)
        if chunk.kind == "drawing"
    ]


# --- Case 1: the places -------------------------------------------------------------


def test_word_and_pdf_imports_put_a_picture_at_each_of_the_three_drawings() -> None:
    docx = _word_chunks()
    pdf = PdfPlumberExamChunker().chunk(content=_PDF.read_bytes())

    assert len(_places(docx)) == 3
    assert _places(docx) == _places(pdf)
    for chunks in (docx, pdf):
        assert [len(chunk.images) for chunk in chunks if chunk.kind == "drawing"] == [1, 1, 1]
    assert [chunk.anchor for chunk in pdf] == [chunk.anchor for chunk in docx]


def test_the_two_drawn_figures_carry_their_word_shapes_and_the_chart_carries_none() -> None:
    chunks = {chunk.anchor: chunk for chunk in _word_chunks()}

    def shapes(anchor: str) -> str | None:
        return chunks[anchor].images[0].docx_shapes

    for anchor in (_Q5_ANCHOR, _Q6_ANCHOR):
        markup = shapes(anchor)
        assert markup is not None
        assert markup.count("<wpg:wgp") == 1, anchor
    assert shapes(_CHART_ANCHOR) is None


# --- The build, driven through the real admission and assembly ------------------------


def _anchors(first: int, last: int) -> tuple[str, ...]:
    return tuple(f"body:{number:04d}" for number in range(first, last + 1))


def _text(text: str) -> dict[str, JsonValue]:
    return {"kind": "text", "text": text, "accepted_values": []}


def _asset(asset_id: str) -> dict[str, JsonValue]:
    return {"kind": "asset", "text": None, "accepted_values": [], "asset_id": asset_id}


def _reply_item(
    chunks: dict[str, DocxChunk], *, first: int, label: str, kind: str, points: int
) -> dict[str, JsonValue]:
    """What a correct reply gives a choice question of the fixture: the question holds its
    heading, text, drawing, prompt, answer instruction and options (anchors ``first`` to
    ``first + 5``), the chunk after them is its facit. The drawing stays where the source
    puts it, between the question's text and its prompt."""
    anchors = _anchors(first, first + 5)
    _, stem, drawing, prompt, instruction, options = (chunks[a] for a in anchors)
    keyed = {
        part.strip()[0]
        for part in chunks[f"body:{first + 6:04d}"].text[len("Rätt svar: ") :].split("; ")
    }
    (image,) = drawing.images
    return {
        "source_anchors": list(anchors),
        "outcome": "converted",
        "conflict_kind": None,
        "review_reason": None,
        "kind": kind,
        "key_source": "copied",
        "facit_text": chunks[f"body:{first + 6:04d}"].text,
        "printed_label": label,
        "body": [
            {"segments": [_text(stem.text)]},
            {"segments": [_asset(image.asset_id)]},
            {"segments": [_text(prompt.text)]},
            {"segments": [_text(instruction.text)]},
        ],
        "points": points,
        "choices": [
            {"text": line[3:], "correct": line[0] in keyed} for line in options.text.split("\n")
        ],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "criteria": [],
    }


@dataclass(frozen=True)
class _Import:
    """Questions 5 to 7 of the Word import, built from the scripted reply."""

    chunks: dict[str, DocxChunk]
    result: DocxBuildResult

    @property
    def document(self) -> NativeExamDocument:
        return self.result.document

    def picture(self, anchor: str) -> DocxImage:
        (image,) = self.chunks[anchor].images
        return image

    def item_with(self, anchor: str) -> NativeExamItem:
        asset_id = self.picture(anchor).asset_id
        (item,) = (i for i in self.document.items if asset_id in i.body_asset_ids())
        return item


@pytest.fixture(scope="module")
def imported() -> _Import:
    chunks = _word_chunks()
    scoped = chunks[_FIRST_SCOPED : _LAST_SCOPED + 1]
    by_anchor = {chunk.anchor: chunk for chunk in scoped}
    state = DocxBuildState(
        origin_kind="docx_import",
        job_id=uuid4(),
        document_id=uuid4(),
        filename=_DOCX.name,
        source_sha256="0" * 64,
        chunks=scoped,
        # Each question's own chunks: heading to options, never its facit.
        questions=(_anchors(27, 32), _anchors(34, 39), _anchors(41, 46)),
    )
    reply: dict[str, JsonValue] = {
        "items": [
            _reply_item(by_anchor, first=27, label="5", kind="single_choice", points=1),
            _reply_item(by_anchor, first=34, label="6", kind="single_choice", points=1),
            _reply_item(by_anchor, first=41, label="7", kind="multiple_response", points=2),
        ],
        "answer_key_anchors": ["body:0033", "body:0040", "body:0047"],
    }
    admit_batch(reply, state)
    return _Import({chunk.anchor: chunk for chunk in chunks}, state.result())


# --- Case 2: the build (D5, D11) ----------------------------------------------------


@pytest.mark.parametrize("anchor", [_Q5_ANCHOR, _Q6_ANCHOR])
def test_a_drawn_figure_is_a_picture_in_its_question_and_no_review_item(
    imported: _Import, anchor: str
) -> None:
    image = imported.picture(anchor)
    item = imported.item_with(anchor)

    segments = [segment for paragraph in item.body for segment in paragraph.segments]
    place = next(
        index
        for index, segment in enumerate(segments)
        if isinstance(segment, NativeAssetSegment) and segment.asset_id == image.asset_id
    )
    assert 0 < place < len(segments) - 1
    assert item.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert item.review.reasons == ()
    assert LEFT_OUT_REASON not in item.review.reasons
    assert DRAWING_SHOWN not in item.review.reasons
    assert imported.result.assets_by_id[image.asset_id] == image.payload


def test_the_assets_of_the_figures_carry_the_word_shapes_and_the_charts_carries_none(
    imported: _Import,
) -> None:
    shapes = {asset.asset_id: asset.docx_shapes for asset in imported.document.assets}

    for anchor in (_Q5_ANCHOR, _Q6_ANCHOR):
        image = imported.picture(anchor)
        assert image.docx_shapes is not None
        assert shapes[image.asset_id] == image.docx_shapes
        assert "<wpg:wgp" in image.docx_shapes
    assert shapes[imported.picture(_CHART_ANCHOR).asset_id] is None
    assert len(shapes) == 3


def test_no_item_of_the_scoped_build_is_a_review_item(imported: _Import) -> None:
    assert len(imported.document.items) == 3
    assert all(
        item.review.state is NativeItemReviewState.REVIEW_COMPLETE
        for item in imported.document.items
    )


# --- The exports --------------------------------------------------------------------

_RENDERER = ExamWorkspaceExportRenderer(
    qti_writer=ExamNetQtiPackageWriter(),
    pdf_renderer=WeasyPrintExamNetPdfRenderer(),
    docx_writer=ExamWorkspaceDocxWriter(),
    print_renderer=WeasyPrintExamPrintRenderer(),
)


def _export(
    document: NativeExamDocument,
    assets_by_id: Mapping[str, bytes],
    target: ExamWorkspaceExportTarget,
) -> bytes:
    return _RENDERER.render(document=document, assets_by_id=assets_by_id, target=target).content


def _word_xml(content: bytes) -> etree._Element:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        return etree.fromstring(archive.read("word/document.xml"))


def _groups(root: etree._Element) -> list[etree._Element]:
    return list(root.iter(f"{{{_NS['wpg']}}}wgp"))


def _group_labels(group: etree._Element) -> list[str]:
    return [str(text) for text in group.xpath(".//w:t/text()", namespaces=_NS)]


def _paragraph_of(element: etree._Element) -> etree._Element:
    (paragraph,) = element.xpath("ancestor::w:p[1]", namespaces=_NS)
    return paragraph


def _own_text(paragraph: etree._Element) -> str:
    """The paragraph's own runs' text, without the text inside a drawing's text boxes."""
    return _words("".join(paragraph.xpath("./w:r/w:t/text()", namespaces=_NS)))


def _sibling_text(paragraph: etree._Element, axis: str) -> str:
    (sibling,) = paragraph.xpath(f"{axis}::w:p[1]", namespaces=_NS)
    return _own_text(sibling)


def _picture_payloads(content: bytes) -> list[bytes]:
    """The payload of each ``a:blip`` picture of the file, in document order."""
    parsed = Document(io.BytesIO(content))
    root = _word_xml(content)
    return [
        parsed.part.related_parts[str(rid)].blob
        for rid in root.xpath("//a:blip/@r:embed", namespaces={**_NS, "r": _NS_R})
    ]


# --- Case 3: the Word export (D9) ---------------------------------------------------


@pytest.fixture(scope="module")
def word_export(imported: _Import) -> bytes:
    return _export(imported.document, imported.result.assets_by_id, ExamWorkspaceExportTarget.DOCX)


def test_the_word_export_writes_the_two_groups_in_their_questions(
    imported: _Import, word_export: bytes
) -> None:
    root = _word_xml(word_export)
    groups = _groups(root)

    assert len(groups) == 2
    places = ((28, 30, _Q5_LABELS), (35, 37, _Q6_LABELS))
    for group, (text_number, prompt_number, labels) in zip(groups, places, strict=True):
        paragraph = _paragraph_of(group)
        text, prompt = (imported.chunks[f"body:{n:04d}"].text for n in (text_number, prompt_number))
        assert _sibling_text(paragraph, "preceding-sibling") == _words(text)
        assert _sibling_text(paragraph, "following-sibling") == _words(prompt)
        assert _group_labels(group) == list(labels)


def test_the_word_export_keeps_the_chart_as_the_only_picture(
    imported: _Import, word_export: bytes
) -> None:
    root = _word_xml(word_export)
    blips = root.xpath("//a:blip", namespaces=_NS)

    assert len(blips) == 1
    assert not blips[0].xpath("ancestor::wpg:wgp", namespaces=_NS)
    assert _picture_payloads(word_export) == [imported.picture(_CHART_ANCHOR).payload]


def test_the_word_export_validates_and_no_drawing_id_repeats(
    imported: _Import, word_export: bytes
) -> None:
    ExamWorkspaceDocxWriter().validate_docx_bytes(
        word_export, expected_item_count=len(imported.document.items)
    )
    ids = _word_xml(word_export).xpath("//wp:docPr/@id", namespaces=_NS)

    assert len(ids) == 3
    assert len(set(ids)) == len(ids)


# --- Case 4: every other export uses the picture (D8) -------------------------------

_SHAPE_MARKERS = (b"wordprocessingGroup", b"wordprocessingShape", b"txbxContent", b"<w:drawing")


def _figure_payloads(imported: _Import) -> list[bytes]:
    return [imported.picture(anchor).payload for anchor in (_Q5_ANCHOR, _Q6_ANCHOR)]


def test_the_exam_net_package_carries_the_pictures_and_no_shapes(imported: _Import) -> None:
    package = _export(
        imported.document, imported.result.assets_by_id, ExamWorkspaceExportTarget.QTI
    )

    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    for payload in (*_figure_payloads(imported), imported.picture(_CHART_ANCHOR).payload):
        assert list(members.values()).count(payload) == 1
    for name, data in members.items():
        assert not any(marker in data for marker in _SHAPE_MARKERS), name
    items = [data for name, data in members.items() if name.startswith("items/")]
    assert sum(data.count(b"<img") for data in items) == 3


@pytest.mark.parametrize("variant", [ExamPrintVariant.STUDENT, ExamPrintVariant.FACIT])
def test_the_print_html_inlines_the_pictures_and_no_shapes(
    imported: _Import, variant: ExamPrintVariant
) -> None:
    html = render_print_html(
        build_print_document(imported.document, variant=variant),
        assets=imported.document.assets,
        assets_by_id=imported.result.assets_by_id,
    )

    for payload in (*_figure_payloads(imported), imported.picture(_CHART_ANCHOR).payload):
        assert base64.b64encode(payload).decode("ascii") in html
    assert html.count("<img") == 3
    assert not any(marker.decode() in html for marker in _SHAPE_MARKERS)


@pytest.mark.parametrize(
    "target", [ExamWorkspaceExportTarget.PDF, ExamWorkspaceExportTarget.PDF_FACIT]
)
def test_the_print_pdf_draws_the_three_pictures_and_holds_no_shapes(
    imported: _Import, target: ExamWorkspaceExportTarget
) -> None:
    pdf = _export(imported.document, imported.result.assets_by_id, target)

    # WeasyPrint may repeat a picture's stream as a mask; the sizes name the pictures.
    pages = PdfReader(io.BytesIO(pdf)).pages
    sizes = {image.image.size for page in pages for image in page.images if image.image is not None}
    assert sizes == {
        (image.width, image.height)
        for image in (imported.picture(a) for a in (_Q5_ANCHOR, _Q6_ANCHOR, _CHART_ANCHOR))
    }
    assert not any(marker in pdf for marker in _SHAPE_MARKERS)


# --- Case 5: a replaced or removed picture leaves no shapes (D10) -------------------


@dataclass(frozen=True)
class _Edited:
    document: NativeExamDocument
    assets_by_id: dict[str, bytes]


def _edited(
    imported: _Import, replacements: Mapping[str, bytes | None], *, kept_by_source: bool = False
) -> _Edited:
    """The open exam after the teacher replaces (new PNG) or removes (None) pictures.

    This is the document edit the editor makes (``examWorkspaceStructure.ts``): the body
    cites the new picture or none, the new picture is a new asset without shapes, and an
    asset nothing cites any more leaves the document with its payload. ``kept_by_source``
    gives each item the stored retry source the Word pipeline attaches, which keeps citing
    the original picture.
    """
    items = {item.item_id: item for item in imported.document.items}
    assets = {asset.asset_id: asset for asset in imported.document.assets}
    payloads = dict(imported.result.assets_by_id)
    for anchor, payload in replacements.items():
        old = imported.picture(anchor)
        item = imported.item_with(anchor)
        new_id = asset_id_for(payload) if payload is not None else None
        paragraphs = []
        for paragraph in item.body:
            segments = tuple(
                segment
                for segment in (
                    (NativeAssetSegment(asset_id=new_id) if new_id else None)
                    if isinstance(segment, NativeAssetSegment) and segment.asset_id == old.asset_id
                    else segment
                    for segment in paragraph.segments
                )
                if segment is not None
            )
            if segments or not paragraph.segments:
                paragraphs.append(paragraph.model_copy(update={"segments": segments}))
        source = _retry_source(old) if kept_by_source else None
        items[item.item_id] = item.model_copy(
            update={"body": tuple(paragraphs), "retry_source": source}
        )
        if payload is not None and new_id is not None:
            with Image.open(io.BytesIO(payload)) as picture:
                width, height = picture.size
            assets[new_id] = NativeExamAsset(
                asset_id=new_id,
                sha256=hashlib.sha256(payload).hexdigest(),
                media_type="image/png",
                byte_length=len(payload),
                width=width,
                height=height,
            )
            payloads[new_id] = payload
        if not kept_by_source:
            del assets[old.asset_id]
            del payloads[old.asset_id]
    document = imported.document.model_copy(
        update={"items": tuple(items.values()), "assets": tuple(assets.values())}
    )
    return _Edited(NativeExamDocument.model_validate(document.model_dump()), payloads)


def _retry_source(image: DocxImage) -> NativeExamRetrySource:
    chunk = NativeExamRetryChunk(
        anchor="body:0001",
        kind="drawing",
        text="",
        marked_text="",
        images=(NativeExamRetryImage(asset_id=image.asset_id, offset=0, marked_offset=0),),
        runs=(),
        paragraphs=(),
    )
    return NativeExamRetrySource(
        chunks=(chunk,),
        owned_context_anchors=(),
        key_chunks=(),
        context_chunks=(),
        label_kind=NativeExamItemKind.SINGLE_CHOICE,
    )


def _word(edited: _Edited) -> bytes:
    return _export(edited.document, edited.assets_by_id, ExamWorkspaceExportTarget.DOCX)


def test_a_replaced_figure_leaves_one_group_and_a_picture_in_its_question(
    imported: _Import,
) -> None:
    edited = _edited(imported, {_Q5_ANCHOR: _NEW_PICTURE})
    content = _word(edited)
    root = _word_xml(content)

    (group,) = _groups(root)
    assert _group_labels(group) == list(_Q6_LABELS)
    assert _picture_payloads(content) == [_NEW_PICTURE, imported.picture(_CHART_ANCHOR).payload]
    (blip,) = root.xpath("(//a:blip)[1]", namespaces=_NS)
    stem = _words(imported.chunks["body:0028"].text)
    assert _sibling_text(_paragraph_of(blip), "preceding-sibling") == stem
    assert not any(label in "".join(root.itertext()) for label in _Q5_LABELS)
    assert all(
        asset.docx_shapes is None
        for asset in edited.document.assets
        if asset.asset_id == asset_id_for(_NEW_PICTURE)
    )


def test_removing_the_second_figure_too_leaves_no_group(imported: _Import) -> None:
    edited = _edited(imported, {_Q5_ANCHOR: _NEW_PICTURE, _Q6_ANCHOR: None})
    content = _word(edited)
    root = _word_xml(content)

    assert _groups(root) == []
    assert _picture_payloads(content) == [_NEW_PICTURE, imported.picture(_CHART_ANCHOR).payload]
    text = "".join(root.itertext())
    assert not any(label in text for label in (*_Q5_LABELS, *_Q6_LABELS))
    assert not any(marker in content for marker in (b"wordprocessingGroup", b"txbxContent"))
    assert all(asset.docx_shapes is None for asset in edited.document.assets)


def test_a_figure_the_retry_source_still_cites_is_not_written_back_either(
    imported: _Import,
) -> None:
    edited = _edited(imported, {_Q5_ANCHOR: _NEW_PICTURE, _Q6_ANCHOR: None}, kept_by_source=True)
    content = _word(edited)

    assert _groups(_word_xml(content)) == []
    assert _picture_payloads(content) == [_NEW_PICTURE, imported.picture(_CHART_ANCHOR).payload]
