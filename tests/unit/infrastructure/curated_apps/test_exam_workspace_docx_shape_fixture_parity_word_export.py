"""Fixture parity, Word export: the export writes the figures' Word shapes back (D9), and a
picture the teacher replaces or removes takes its shapes with it (D10).

The shared build and its scripted model reply live in the parity test support module.
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass

import pytest
from docx import Document
from lxml import etree
from PIL import Image

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceExportTarget
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxImage,
    asset_id_for,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_records import (
    NativeExamRetryChunk,
    NativeExamRetryImage,
    NativeExamRetrySource,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_writer import (  # noqa: E501
    ExamWorkspaceDocxWriter,
)
from tests.unit.infrastructure.curated_apps import (
    exam_workspace_docx_shape_fixture_parity_test_support as parity_support,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_docx_shape_fixture_parity_test_support import (  # noqa: E501
    _CHART_ANCHOR,
    _NEW_PICTURE,
    _NS,
    _NS_R,
    _Q5_ANCHOR,
    _Q5_LABELS,
    _Q6_ANCHOR,
    _Q6_LABELS,
    _export,
    _Import,
    _words,
)

pytestmark = pytest.mark.unit

imported = parity_support.imported


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
