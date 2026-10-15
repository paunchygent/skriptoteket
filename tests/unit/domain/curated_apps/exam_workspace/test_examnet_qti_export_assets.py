"""Mapping tests for referenced assets in the native exam -> Exam.net QTI adapter."""

import hashlib

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.unit.domain.curated_apps.exam_workspace.examnet_qti_export_test_support import (
    ASSET_ID,
    ASSET_PAYLOAD,
    document_of,
    review_complete,
)


class TestAssetMapping:
    def _asset_document(self) -> NativeExamDocument:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.FREE_TEXT,
            body=(
                NativeParagraph(
                    segments=(
                        NativeTextSegment(text="Se bilden."),
                        NativeAssetSegment(asset_id=ASSET_ID),
                    )
                ),
            ),
            points=2,
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
            review=review_complete(),
        )
        asset = NativeExamAsset(
            asset_id=ASSET_ID,
            sha256=hashlib.sha256(ASSET_PAYLOAD).hexdigest(),
            media_type="image/png",
            byte_length=len(ASSET_PAYLOAD),
        )
        return document_of((item,), assets=(asset,))

    def test_referenced_asset_without_payload_raises(self) -> None:
        with pytest.raises(DomainError) as exc_info:
            native_exam_to_examnet_qti_items(self._asset_document())

        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
        assert exc_info.value.details["asset_id"] == ASSET_ID

    def test_referenced_asset_with_payload_maps_to_image_resource(self) -> None:
        (qti_item,) = native_exam_to_examnet_qti_items(
            self._asset_document(),
            assets_by_id={ASSET_ID: ASSET_PAYLOAD},
        )

        (image,) = qti_item.image_resources
        assert image.asset_id == "image_001"
        assert image.filename == "item_001-image-001.png"
        assert image.media_type == "image/png"
        assert image.payload == ASSET_PAYLOAD
        assert image.source_reference == ASSET_ID
        assert image.alt_text == "Bild 1"
