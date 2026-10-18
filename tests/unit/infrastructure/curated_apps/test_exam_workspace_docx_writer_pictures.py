"""Shared-picture round-trip tests for the exam workspace DOCX writer (W1-W2).

Instruction and item-body pictures are read back from the produced bytes, checking each
shared instruction keeps its text runs and payload in place, the body picture is
embedded, an oversized picture is clamped and a missing payload fails closed.
"""

import hashlib
import io
import zipfile
from dataclasses import dataclass
from uuid import uuid4

import pytest
from docx import Document
from docx.shared import Mm

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    IMAGE_SPACING,
    TEXT_WIDTH_MM,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_language_labels import (
    SWEDISH_EXAM_LABELS,
)
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
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    exam_workspace_docx_writer,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_docx_writer_test_support import (
    document_text,
    drawing_payload,
    heading_texts,
    only_paragraph,
    png,
    review_complete,
    run_shape,
)

ExamWorkspaceDocxWriter = exam_workspace_docx_writer.ExamWorkspaceDocxWriter

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


def _shared_asset(payload: bytes) -> tuple[str, NativeExamAsset]:
    digest = hashlib.sha256(payload).hexdigest()
    asset_id = f"asset_{digest[:16]}"
    return asset_id, NativeExamAsset(
        asset_id=asset_id,
        media_type="image/png",
        byte_length=len(payload),
        sha256=digest,
    )


@pytest.fixture
def shared_picture_document() -> SharedPictureDocument:
    """Global and parent instruction each carry a real PNG between two text runs."""
    global_payload = png((200, 20, 20, 255), (12, 6))
    parent_payload = png((20, 20, 200, 255), (16, 8))
    global_id, global_asset = _shared_asset(global_payload)
    parent_id, parent_asset = _shared_asset(parent_payload)
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


class TestPictures:
    def test_two_shared_instructions_round_trip_in_place_with_payloads(
        self, shared_picture_document: SharedPictureDocument
    ) -> None:
        fixture = shared_picture_document
        writer = ExamWorkspaceDocxWriter()
        content = writer.build_docx_bytes(fixture.document, assets_by_id=fixture.assets_by_id)
        writer.validate_docx_bytes(content, expected_item_count=len(fixture.document.items))

        parsed = Document(io.BytesIO(content))
        paragraphs = list(parsed.paragraphs)
        texts = [paragraph.text for paragraph in paragraphs]

        global_paragraph = only_paragraph(
            paragraphs, f"{_SHARED_GLOBAL_BEFORE}{_SHARED_GLOBAL_AFTER}"
        )
        assert run_shape(global_paragraph) == [
            _SHARED_GLOBAL_BEFORE,
            "image",
            _SHARED_GLOBAL_AFTER,
        ]
        assert (
            drawing_payload(parsed, global_paragraph)
            == fixture.assets_by_id[fixture.global_asset_id]
        )
        assert texts.count(global_paragraph.text) == 1

        parent_paragraph = only_paragraph(
            paragraphs, f"{_SHARED_PARENT_BEFORE}{_SHARED_PARENT_AFTER}"
        )
        assert run_shape(parent_paragraph) == [
            _SHARED_PARENT_BEFORE,
            "image",
            _SHARED_PARENT_AFTER,
        ]
        assert (
            drawing_payload(parsed, parent_paragraph)
            == fixture.assets_by_id[fixture.parent_asset_id]
        )
        assert texts.count(parent_paragraph.text) == 1
        first_heading_at = texts.index(heading_texts(parsed, "Heading 3")[0])
        assert texts.index(parent_paragraph.text) == first_heading_at - 1

        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            media_payloads = [
                archive.read(name) for name in archive.namelist() if name.startswith("word/media/")
            ]
        expected_digests = sorted(
            hashlib.sha256(payload).hexdigest() for payload in fixture.assets_by_id.values()
        )
        assert sorted(hashlib.sha256(payload).hexdigest() for payload in media_payloads) == (
            expected_digests
        )

        assert SWEDISH_EXAM_LABELS.answer_key not in heading_texts(parsed, "Heading 2")
        assert "Godtagbar förklaring." not in document_text(parsed)

    def test_item_body_picture_is_embedded(
        self, shared_picture_document: SharedPictureDocument
    ) -> None:
        fixture = shared_picture_document
        content = ExamWorkspaceDocxWriter().build_docx_bytes(
            fixture.document, assets_by_id=fixture.assets_by_id
        )

        parsed = Document(io.BytesIO(content))
        # The global instruction, item_001's body and the parent instruction each embed one.
        assert len(parsed.inline_shapes) == 3
        body_paragraph = only_paragraph(list(parsed.paragraphs), "Fråga 1.")
        assert run_shape(body_paragraph) == ["Fråga 1.", "image"]
        assert (
            drawing_payload(parsed, body_paragraph) == fixture.assets_by_id[fixture.global_asset_id]
        )

    def test_picture_wider_than_the_text_column_is_clamped(self) -> None:
        payload = png((10, 90, 10, 255), (4000, 40))
        asset_id, asset = _shared_asset(payload)
        item = make_free_text_item()
        item = NativeExamItem.model_validate(
            {
                **item.model_dump(),
                "body": [
                    {
                        "heading_level": None,
                        "segments": [
                            {"kind": "text", "text": "Se bilden", "marks": []},
                            {"kind": "asset", "asset_id": asset_id},
                        ],
                    }
                ],
            }
        )
        document = NativeExamDocument(
            document_id=uuid4(),
            revision=1,
            title="Bildprov",
            items=(item,),
            assets=(asset,),
            origin=NativeExamDocumentOrigin(kind="created"),
        )

        content = ExamWorkspaceDocxWriter().build_docx_bytes(
            document, assets_by_id={asset_id: payload}
        )
        parsed = Document(io.BytesIO(content))
        assert len(parsed.inline_shapes) == 1
        assert parsed.inline_shapes[0].width == Mm(TEXT_WIDTH_MM)

    def test_a_body_picture_paragraph_takes_the_template_image_spacing(
        self, shared_picture_document: SharedPictureDocument
    ) -> None:
        fixture = shared_picture_document
        content = ExamWorkspaceDocxWriter().build_docx_bytes(
            fixture.document, assets_by_id=fixture.assets_by_id
        )
        parsed = Document(io.BytesIO(content))
        body_paragraph = only_paragraph(list(parsed.paragraphs), "Fråga 1.")
        spacing = body_paragraph.paragraph_format

        assert spacing.space_before.mm == pytest.approx(IMAGE_SPACING.space_before_mm, abs=0.02)
        assert spacing.space_after.mm == pytest.approx(IMAGE_SPACING.space_after_mm, abs=0.02)

    def test_picture_without_payload_fails_closed(
        self, shared_picture_document: SharedPictureDocument
    ) -> None:
        fixture = shared_picture_document
        with pytest.raises(DomainError) as exc_info:
            ExamWorkspaceDocxWriter().build_docx_bytes(fixture.document)

        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
        assert exc_info.value.details["asset_ids"] == [fixture.global_asset_id]
