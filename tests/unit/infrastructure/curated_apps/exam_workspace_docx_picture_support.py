"""Fixtures shared by the DOCX picture transform and raster normalization tests."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from uuid import uuid4

from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from PIL import Image

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_labeler_block_image import (  # noqa: E501
    DocxBlockImageRenderer,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_docx_writer_test_support import (
    png,
    review_complete,
)

# RGBA pixels whose alpha varies: fully transparent colours, a half-transparent colour and
# opaque colours. The hidden RGB values must survive beside the alpha value.
ALPHA_ROWS = [
    [(255, 0, 0, 0), (0, 255, 0, 0), (0, 0, 255, 128), (255, 255, 0, 255)],
    [(0, 0, 0, 0), (0, 0, 0, 128), (10, 20, 30, 0), (40, 50, 60, 255)],
]


def halves() -> bytes:
    """A 200x100 picture with a red left half and a blue right half."""
    image = Image.new("RGB", (200, 100), (0, 0, 255))
    image.paste((255, 0, 0), (0, 0, 100, 100))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (20, 10), (7, 8, 9)).save(buffer, format="JPEG")
    return buffer.getvalue()


def pixels(payload: bytes) -> list[tuple[int, int, int]]:
    with Image.open(io.BytesIO(payload)) as image:
        raw = image.convert("RGB").tobytes()
    return [(raw[index], raw[index + 1], raw[index + 2]) for index in range(0, len(raw), 3)]


def rgba_png(rows: list[list[tuple[int, int, int, int]]]) -> bytes:
    image = Image.new("RGBA", (len(rows[0]), len(rows)))
    image.putdata([pixel for row in rows for pixel in row])
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def rgba_pixels(payload: bytes) -> list[tuple[int, int, int, int]]:
    with Image.open(io.BytesIO(payload)) as image:
        assert "A" in image.getbands(), f"no alpha channel in mode {image.mode}"
        raw = image.convert("RGBA").tobytes()
    return [
        (raw[index], raw[index + 1], raw[index + 2], raw[index + 3])
        for index in range(0, len(raw), 4)
    ]


def document_with_picture(payload: bytes):
    document = Document()
    document.add_picture(io.BytesIO(payload))
    paragraph = document.element.body.findall(qn("w:p"))[-1]
    blip = next(paragraph.iter(qn("a:blip")))
    return document, blip, paragraph


def save_document(document) -> bytes:
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def chunk_document(document):
    return PythonDocxExamChunker().chunk(content=save_document(document)).chunks


def render_pixels(document, paragraph) -> list[tuple[int, int, int]]:
    payload = DocxBlockImageRenderer(document).render(paragraph, anchor="body:0001")
    return pixels(payload)


def set_src_rect(blip, **attributes: str) -> None:
    picture = next(blip.iterancestors(qn("pic:pic")))
    fill = picture.find(qn("pic:blipFill"))
    assert fill is not None
    rendered = " ".join(f'{name}="{value}"' for name, value in attributes.items())
    fill.insert(1, parse_xml(f"<a:srcRect {nsdecls('a')} {rendered}/>"))


_SHARED_GLOBAL_BEFORE = "Betrakta: "
_SHARED_GLOBAL_AFTER = " diagrammet."
_SHARED_PARENT_BEFORE = "Se figuren: "
_SHARED_PARENT_AFTER = " och svara."


@dataclass(frozen=True)
class SharedPictureDocument:
    """The accepted shared-picture document: two shared instructions and two free-text items."""

    document: NativeExamDocument
    global_asset_id: str
    parent_asset_id: str
    assets_by_id: dict[str, bytes]


def shared_asset(payload: bytes) -> tuple[str, NativeExamAsset]:
    digest = hashlib.sha256(payload).hexdigest()
    asset_id = f"asset_{digest[:16]}"
    return asset_id, NativeExamAsset(
        asset_id=asset_id,
        media_type="image/png",
        byte_length=len(payload),
        sha256=digest,
    )


def build_shared_picture_document() -> SharedPictureDocument:
    """Global and parent instruction each carry a real PNG between two text runs."""
    global_payload = png((200, 20, 20, 255), (12, 6))
    parent_payload = png((20, 20, 200, 255), (16, 8))
    global_id, global_asset = shared_asset(global_payload)
    parent_id, parent_asset = shared_asset(parent_payload)
    items = (
        NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.FREE_TEXT,
            writing_lines=8,
            body=(
                NativeParagraph(
                    heading_level=None,
                    segments=(
                        NativeTextSegment(text="Fråga 1.", marks=()),
                        NativeAssetSegment(asset_id=global_id),
                    ),
                ),
            ),
            points=1,
            criteria=(NativeExamCriterion(text="Godtagbar förklaring.", points=1),),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
            review=review_complete(),
        ),
        NativeExamItem(
            item_id="item_002",
            sequence=2,
            kind=NativeExamItemKind.FREE_TEXT,
            writing_lines=8,
            body=(
                NativeParagraph(
                    heading_level=None, segments=(NativeTextSegment(text="Fråga 2.", marks=()),)
                ),
            ),
            points=1,
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
            review=review_complete(),
        ),
    )
    document = NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Diagramprov",
        instructions=(
            NativeParagraph(
                heading_level=None,
                segments=(
                    NativeTextSegment(text=_SHARED_GLOBAL_BEFORE, marks=()),
                    NativeAssetSegment(asset_id=global_id),
                    NativeTextSegment(text=_SHARED_GLOBAL_AFTER, marks=()),
                ),
            ),
        ),
        items=items,
        parents=(
            NativeExamParent(
                parent_id="parent_001",
                place=0,
                instruction=(
                    NativeParagraph(
                        heading_level=None,
                        segments=(
                            NativeTextSegment(text=_SHARED_PARENT_BEFORE, marks=()),
                            NativeAssetSegment(asset_id=parent_id),
                            NativeTextSegment(text=_SHARED_PARENT_AFTER, marks=()),
                        ),
                    ),
                ),
                item_ids=tuple(item.item_id for item in items),
            ),
        ),
        assets=(global_asset, parent_asset),
        origin=NativeExamDocumentOrigin(kind="created"),
    )
    return SharedPictureDocument(
        document=document,
        global_asset_id=global_id,
        parent_asset_id=parent_id,
        assets_by_id={global_id: global_payload, parent_id: parent_payload},
    )
