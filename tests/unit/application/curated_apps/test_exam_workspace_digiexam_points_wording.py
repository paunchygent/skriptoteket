"""DigiExam import settles trailing points wording against the stored max_score (D8).

Synthetic prompts through the real IR-to-native mapping, plus the real .dxe
fixture: an equal number leaves the body, a differing number is recorded,
look-alike prose stays.
"""

import hashlib
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from skriptoteket.application.curated_apps.digiexam_source_parsing import parse_source_exam
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import ConversionHubUpload
from skriptoteket.domain.curated_apps.exam_workspace.digiexam_import import (
    build_native_exam_from_digiexam,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_image_readability import (
    PillowEmbeddedImageDecodability,
)

_FIXTURE = Path("tests/fixtures/exam_conversion/1772718003-test-samma-prov-i-digiexam.dxe")
_VOLT = (
    "Pelle gör en fin volt, Sara gör en ful. Sätt poäng på Sara och Pelles volter. "
    "Använd mellan 3 poäng och 5 poäng."
)


def _imported(prompt: tuple[str, ...], max_score: int | float | None) -> NativeExamItem:
    content = _FIXTURE.read_bytes()
    exam = parse_source_exam(
        upload=ConversionHubUpload(
            filename=_FIXTURE.name, file_bytes=content, content_type="application/octet-stream"
        ),
        image_decodability=PillowEmbeddedImageDecodability(),
    )
    source = replace(exam.items[0], prompt_html=None, prompt_lines=prompt, max_score=max_score)
    document = build_native_exam_from_digiexam(
        exam=replace(exam, items=(source,), manual_follow_ups=()),
        document_id=uuid4(),
        source_sha256=hashlib.sha256(content).hexdigest(),
    ).document
    return document.items[0]


def _body_text(item: NativeExamItem) -> str:
    return "\n".join(item.plain_text_lines())


def test_trailing_label_leaves_the_body_and_keeps_the_source_record() -> None:
    item = _imported(("Beskriv processen. (2 p)",), 2)

    assert _body_text(item) == "Beskriv processen."
    assert item.points == 2
    assert item.leftover_points_text is None
    assert item.import_record is not None
    assert item.import_record.original_wording.question_text.endswith("(2 p)")


def test_trailing_points_line_leaves_whole() -> None:
    item = _imported(("Vad är svaret?", "Poäng: 2 poäng"), 2)

    assert _body_text(item) == "Vad är svaret?"
    assert item.points == 2
    assert item.leftover_points_text is None
    assert item.import_record is not None
    assert item.import_record.original_wording.question_text.endswith("Poäng: 2 poäng")


def test_differing_number_keeps_the_text_and_records_it() -> None:
    item = _imported(("Beskriv processen. (2 p)",), 3)

    assert _body_text(item) == "Beskriv processen. (2 p)"
    assert item.points == 3
    assert item.leftover_points_text == "(2 p)"
    assert item.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert item.review.reasons == ()


def test_missing_score_keeps_the_text_and_records_nothing() -> None:
    item = _imported(("Beskriv processen. (2 p)",), None)

    assert _body_text(item) == "Beskriv processen. (2 p)"
    assert item.points is None
    assert item.leftover_points_text is None


def test_whole_stem_wording_stays_and_records_nothing() -> None:
    item = _imported(("(2 p)",), 2)

    assert _body_text(item) == "(2 p)"
    assert item.leftover_points_text is None


def test_volt_question_is_prose_for_every_score() -> None:
    for points in (5, 4):
        item = _imported((_VOLT,), points)

        assert _body_text(item) == _VOLT
        assert item.points == points
        assert item.leftover_points_text is None


def test_sentence_points_mention_stays() -> None:
    prompt = "Väljer eleven det får den 2 poäng."
    item = _imported((prompt,), 2)

    assert _body_text(item) == prompt
    assert item.leftover_points_text is None


def test_real_fixture_sentence_prompts_keep_their_text_and_record_nothing() -> None:
    content = _FIXTURE.read_bytes()
    exam = parse_source_exam(
        upload=ConversionHubUpload(
            filename=_FIXTURE.name, file_bytes=content, content_type="application/octet-stream"
        ),
        image_decodability=PillowEmbeddedImageDecodability(),
    )
    document = build_native_exam_from_digiexam(
        exam=exam,
        document_id=uuid4(),
        source_sha256=hashlib.sha256(content).hexdigest(),
    ).document

    mentioned = [item for item in document.items if _body_text(item).endswith("får den 2 poäng.")]
    assert mentioned
    for item in document.items:
        assert item.leftover_points_text is None
