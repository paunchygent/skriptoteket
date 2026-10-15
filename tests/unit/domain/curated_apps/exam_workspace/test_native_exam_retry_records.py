"""Stored retry-record value validation, independent of source capture and rebuilding."""

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_records import (
    NativeExamRetryChunk,
    NativeExamRetryImage,
)

pytestmark = pytest.mark.unit

_ASSET_ID = "asset_0123456789abcdef"


def test_a_retry_image_offset_beyond_the_text_is_rejected():
    with pytest.raises(ValidationError):
        NativeExamRetryChunk(
            anchor="body:0001",
            kind="drawing",
            text="ab",
            marked_text="ab",
            images=(NativeExamRetryImage(asset_id=_ASSET_ID, offset=3, marked_offset=0),),
        )
    with pytest.raises(ValidationError):
        NativeExamRetryChunk(
            anchor="body:0001",
            kind="drawing",
            text="ab",
            marked_text="ab",
            images=(NativeExamRetryImage(asset_id=_ASSET_ID, offset=0, marked_offset=3),),
        )
