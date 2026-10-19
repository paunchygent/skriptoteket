"""Block-interaction tests for the Exam.net QTI item reader.

Purpose:
    Prove that `examnet_qti_block_item_reader` inverts the writer's choice,
    free-text and prompt-image layouts through `read_examnet_qti_item`.

Relationships:
    - Split from `test_examnet_qti_item_reader.py`; shared builders live in
      `examnet_qti_reader_test_support` and are imported, never copied.
"""

from __future__ import annotations

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    DEFAULT_WRITING_LINES,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiEvaluationMode,
    ExamNetQtiInteractionType,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    item_round_trip as _round_trip,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    make_asset as _asset,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    multiple_response_item as _multiple_response_item,
)
from tests.unit.domain.curated_apps.exam_workspace.examnet_qti_export_test_support import (
    review_complete,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
    make_single_choice_item,
    plain_body,
)

pytestmark = pytest.mark.unit

_ASSET_PNG = "asset_1111111111111111"
_ASSET_JPEG = "asset_2222222222222222"
_PNG = b"\x89PNG\r\n\x1a\nfirst picture"
_JPEG = b"\xff\xd8\xffsecond picture"


def test_multiple_response_uses_declaration_cardinality_not_max_choices() -> None:
    item = _multiple_response_item()

    exported, read = _round_trip(item)

    assert exported.interaction_type is ExamNetQtiInteractionType.MULTIPLE_RESPONSE
    assert read.interaction_type is ExamNetQtiInteractionType.MULTIPLE_RESPONSE
    assert read.correct_choice_identifiers == ("choice_001", "choice_003")


def test_a_zero_point_item_reads_max_score_none() -> None:
    item = NativeExamItem.model_validate({**dict(make_single_choice_item()), "points": 0})

    exported, read = _round_trip(item)

    assert exported.max_score == 0
    assert read.max_score == 0


def test_free_text_reads_a_one_row_mapping_as_its_criterion_points() -> None:
    item = make_free_text_item()

    exported, read = _round_trip(item)

    assert exported.free_text_criterion_points == 4
    assert read.free_text_criterion_points == 4
    assert read.evaluation_mode is ExamNetQtiEvaluationMode.AUTOMATIC
    assert read.max_score == 4


def test_free_text_reads_a_three_row_mapping_as_its_first_row() -> None:
    item = NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        body=plain_body("Bedöm svaret."),
        points=3,
        writing_lines=DEFAULT_WRITING_LINES,
        criteria=(
            NativeExamCriterion(text="Ett korrekt exempel.", points=1),
            NativeExamCriterion(text="En korrekt förklaring.", points=1),
            NativeExamCriterion(text="En rimlig slutsats.", points=1),
        ),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=review_complete(),
    )

    exported, read = _round_trip(item)

    assert exported.free_text_criterion_points == 1
    assert read.free_text_criterion_points == 1
    assert read.max_score == 3
    assert read.evaluation_mode is ExamNetQtiEvaluationMode.AUTOMATIC


def test_free_text_without_points_stays_manual_unkeyed() -> None:
    item = NativeExamItem.model_validate({**dict(make_free_text_item()), "points": None})

    exported, read = _round_trip(item)

    assert exported.evaluation_mode is ExamNetQtiEvaluationMode.MANUAL_UNKEYED
    assert read.evaluation_mode is ExamNetQtiEvaluationMode.MANUAL_UNKEYED
    assert read.free_text_criterion_points is None
    # The writer coerces the inadmissible absent score to "0", which reads back
    # as a stated zero (review 596c1654 F5); the real export route blocks such
    # items with the missing_points blocker instead.
    assert read.max_score == 0


def test_png_and_jpeg_prompt_images_round_trip_in_placement_order() -> None:
    item = NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        body=(
            NativeParagraph(
                heading_level=None,
                segments=(
                    NativeTextSegment(text="Före ", marks=()),
                    NativeAssetSegment(asset_id=_ASSET_PNG),
                    NativeTextSegment(text=" mellan ", marks=()),
                    NativeAssetSegment(asset_id=_ASSET_JPEG),
                    NativeTextSegment(text=" efter.", marks=()),
                ),
            ),
        ),
        points=2,
        writing_lines=DEFAULT_WRITING_LINES,
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=review_complete(),
    )
    image_paths = ("images/forsta.png", "images/andra.jpg")
    files = {
        f"items/{image_paths[0]}": _PNG,
        f"items/{image_paths[1]}": _JPEG,
    }

    exported, read = _round_trip(
        item,
        image_paths=image_paths,
        files=files,
        assets=(
            _asset(_ASSET_PNG, _PNG, "image/png"),
            _asset(_ASSET_JPEG, _JPEG, "image/jpeg"),
        ),
        payloads={_ASSET_PNG: _PNG, _ASSET_JPEG: _JPEG},
    )

    assert read.prompt_paragraphs == exported.prompt_paragraphs
    assert [image.media_type for image in read.image_resources] == [
        "image/png",
        "image/jpeg",
    ]
    assert [image.payload for image in read.image_resources] == [_PNG, _JPEG]
    assert [image.alt_text for image in read.image_resources] == [
        image.alt_text for image in exported.image_resources
    ]
    assert [image.filename for image in read.image_resources] == [
        "forsta.png",
        "andra.jpg",
    ]
