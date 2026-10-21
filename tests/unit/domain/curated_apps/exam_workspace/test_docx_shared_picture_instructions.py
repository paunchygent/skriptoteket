"""F2: a shared instruction's picture stays placed in the student-visible parent body.

Real DOCX chunks through real assembly, retry-source attachment and asset persistence: a
supported PNG beside "Betrakta diagrammet." governs two converted free-text questions, so
the parent's instruction body places exactly that picture at its exact source place. A
facit picture stays a source-only asset no student-visible body shows.
"""

from io import BytesIO
from uuid import uuid4

from PIL import Image

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import assemble_build_result
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_item import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk, DocxImage
from skriptoteket.domain.curated_apps.exam_workspace.docx_item_alignment import AlignedItem
from skriptoteket.domain.curated_apps.exam_workspace.examnet_pdf_export import (
    native_exam_to_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_source import (
    question_retry_source,
    with_retry_sources,
    with_source_assets,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import (
    body_asset_ids,
    body_text_lines,
)


def _png(color: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (8, 4), color).save(buffer, format="PNG")
    return buffer.getvalue()


_SHARED_PNG = _png("green")
_FACIT_PNG = _png("red")


def _chunk(anchor: str, text: str, payload: bytes | None = None) -> DocxChunk:
    images = (
        ()
        if payload is None
        else (
            DocxImage(
                payload=payload,
                media_type="image/png",
                offset=len(text),
                marked_offset=len(text),
            ),
        )
    )
    return DocxChunk(anchor, "paragraph", text, text, images)


def _converted(anchor: str, text: str) -> AlignedItem:
    return aligned_native_item(
        ProducedItem.model_validate(
            {
                "source_anchors": [anchor],
                "outcome": "converted",
                "review_reason": None,
                "kind": "free_text",
                "key_source": None,
                "facit_text": None,
                "body": [
                    {
                        "segments": [
                            {
                                "kind": "text",
                                "text": text,
                                "accepted_values": [],
                            }
                        ]
                    }
                ],
                "points": 1,
                "choices": [],
            }
        ),
        language="sv",
        foreign_chunks=(),
    )


def _assembled() -> tuple[NativeExamDocument, dict[str, bytes], str, str]:
    """The two converted questions with the shared and facit pictures, as a job builds them."""
    chunks = (
        _chunk("body:0001", "Fråga 1. Vad betyder alpha?"),
        _chunk("body:0002", "Fråga 2. Vad betyder beta?"),
        _chunk("body:0003", "Betrakta diagrammet.", _SHARED_PNG),
        _chunk("body:0004", "Facit: rätt svar är alpha.", _FACIT_PNG),
    )
    result = assemble_build_result(
        origin_kind="docx_import",
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        accepted=(
            (_converted("body:0001", "Vad betyder alpha?"), ("body:0001",)),
            (_converted("body:0002", "Vad betyder beta?"), ("body:0002",)),
        ),
        review_reasons={},
        key_anchors=frozenset({"body:0004"}),
        instructions=(
            ProducedMetadata(text="Betrakta diagrammet.", source_anchors=("body:0003",)),
        ),
        governed={"body:0003": frozenset({"body:0001", "body:0002"})},
        questions=(("body:0001",), ("body:0002",)),
    )
    sources = {
        anchor: question_retry_source(
            own_anchors=(anchor,),
            owned_context_anchors=(),
            key_anchors=("body:0004",),
            read_anchors=frozenset({"body:0003"}),
            chunks=chunks,
            label_kind=NativeExamItemKind.FREE_TEXT,
        )
        for anchor in ("body:0001", "body:0002")
    }
    document, assets_by_id = with_source_assets(
        document=with_retry_sources(result.document, sources),
        chunks=chunks,
        assets_by_id=result.assets_by_id,
    )
    return (
        document,
        dict(assets_by_id),
        DocxImage(payload=_SHARED_PNG, media_type="image/png").asset_id,
        DocxImage(payload=_FACIT_PNG, media_type="image/png").asset_id,
    )


def test_a_shared_instruction_picture_lands_once_in_the_parent_body():
    document, _, shared_id, _ = _assembled()

    (parent,) = document.parents
    assert len(parent.item_ids) == 2
    assert body_text_lines(parent.instruction) == ("Betrakta diagrammet.",)
    assert body_asset_ids(parent.instruction) == (shared_id,)
    assert shared_id in {asset.asset_id for asset in document.assets}
    assert document.instructions == ()


def test_a_facit_picture_stays_a_source_only_asset():
    document, assets_by_id, _, facit_id = _assembled()

    student_bodies = (
        *(item.body for item in document.items),
        document.instructions,
        *(parent.instruction for parent in document.parents),
    )
    assert facit_id not in {
        asset_id for body in student_bodies for asset_id in body_asset_ids(body)
    }
    assert facit_id in {asset.asset_id for asset in document.assets}
    assert facit_id in assets_by_id
    assert any(facit_id in item.source_asset_ids() for item in document.items)


def test_the_pdf_export_renders_the_shared_picture_with_its_wording():
    document, assets_by_id, shared_id, facit_id = _assembled()

    pdf = native_exam_to_pdf_document(document, assets_by_id=assets_by_id)

    assert pdf.status is DigiExamExamNetPdfStatus.SUCCESS
    assert "Betrakta diagrammet." in pdf.html
    assert f'src="assets/{shared_id}.png"' in pdf.html
    assert f"assets/{facit_id}.png" not in pdf.html


def test_global_pictured_heading_retains_original_wording_and_interior_position():
    text = "Läs diagrammet (2 p)"
    image = DocxImage(payload=_SHARED_PNG, media_type="image/png", offset=4, marked_offset=4)
    heading = DocxChunk("body:0001", "heading", text, text, (image,))
    metadata = ProducedMetadata(text="Läs diagrammet", source_anchors=(heading.anchor,))
    result = assemble_build_result(
        origin_kind="docx_import",
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=(_chunk("body:0000", "Fråga 1. Vad?"), heading),
        accepted=((_converted("body:0000", "Vad?"), ("body:0000",)),),
        review_reasons={},
        instructions=(metadata,),
    )
    assert body_text_lines(result.document.instructions) == (text,)
    paragraph = result.document.instructions[0]
    assert paragraph.segments[0].kind == "text"
    assert paragraph.segments[0].text == "Läs "
    assert paragraph.segments[1].kind == "asset"
    assert paragraph.segments[2].kind == "text"
    assert paragraph.segments[2].text == "diagrammet (2 p)"
