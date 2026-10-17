"""Contract fidelity at the real parser-to-native boundary, without AI or overlays."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_conversion_producers import parse_source_exam
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import ConversionHubUpload
from skriptoteket.domain.curated_apps.exam_workspace.digiexam_import import (
    build_native_exam_from_digiexam,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeTextSegment
from skriptoteket.domain.errors import DomainError, ErrorCode

_FIXTURES = Path("tests/fixtures/exam_conversion")


def _choice_text(choice):
    return "\n".join("".join(segment.text for segment in block.segments) for block in choice.body)


@pytest.mark.parametrize(
    "filename",
    [
        "1772718003-test-samma-prov-i-digiexam.dxe",
        "sanitized-embedded-image.dxe",
        "real_inputs/1776888013-ak7-lag-och-ratt.dxe",
    ],
)
def test_real_parser_output_preserves_question_semantics_and_wording(filename):
    fixture = _FIXTURES / filename
    content = fixture.read_bytes()
    exam = parse_source_exam(
        upload=ConversionHubUpload(
            filename=fixture.name, file_bytes=content, content_type="application/octet-stream"
        )
    )
    mapped = build_native_exam_from_digiexam(
        exam=exam, document_id=uuid4(), source_sha256=hashlib.sha256(content).hexdigest()
    )
    expected_kinds = {
        "open_ended": "free_text",
        "single_choice": "single_choice",
        "multiple_choice": "single_choice",
        "multiple_response": "multiple_response",
        "gap_fill": "gap_fill",
    }
    expected_origins = {
        "dxe_populated_key": "source_provided",
        "absent": "absent",
        "not_applicable": "not_applicable",
    }
    supported = [source for source in exam.items if source.item_type.value != "unknown"]
    assert len(mapped.document.items) == len(supported)
    for source, native in zip(supported, mapped.document.items, strict=True):
        assert native.kind.value == expected_kinds[source.item_type.value]
        assert native.points == source.max_score
        assert (
            native.answer_key.origin.value == expected_origins[source.answer_key.provenance.value]
        )
        assert [_choice_text(choice) for choice in native.choices] == [
            alternative.title for alternative in source.alternatives
        ]
        # Verify key identity by its displayed alternative, not by the mapper's ID recipe.
        choices = {choice.choice_id: _choice_text(choice) for choice in native.choices}
        assert [choices[key] for key in native.answer_key.correct_choice_ids] == [
            alternative.title
            for alternative in source.alternatives
            if alternative.id in source.answer_key.correct_alternative_ids
        ]
        assert [gap.accepted_values for gap in native.gaps] == [
            tuple(
                answer.value
                for answer in source.answer_key.correct_gap_answers
                if answer.guid == gap.guid
            )
            for gap in source.gaps
        ]
        followups = [
            follow.message
            for follow in exam.manual_follow_ups
            if follow.item_id in {source.item_id, "exam"}
        ]
        if followups:
            assert native.review.state.value == "review_required"
            assert all(message in native.review.reasons for message in followups)
        assert native.import_record is not None
        assert native.import_record.original_wording.question_text == "\n".join(source.prompt_lines)
        assert native.import_record.steps
        assert set(native.body_asset_ids()) <= set(mapped.assets_by_id)


@pytest.mark.parametrize("score", [0, 0.0, 0.5, 2, 2.5])
def test_real_fixture_score_mutation_preserves_finite_nonnegative_points(score):
    """Synthetic JSON mutation of the reviewer's real fixture, through production owners."""
    fixture = _FIXTURES / "1772718003-test-samma-prov-i-digiexam.dxe"
    payload = json.loads(fixture.read_bytes())
    payload["exams"][0]["questions"][0]["maxScore"] = score
    content = json.dumps(payload).encode()
    exam = parse_source_exam(
        upload=ConversionHubUpload(
            filename=fixture.name, file_bytes=content, content_type="application/octet-stream"
        )
    )
    document = build_native_exam_from_digiexam(
        exam=exam, document_id=uuid4(), source_sha256=hashlib.sha256(content).hexdigest()
    ).document
    assert exam.items[0].max_score == score
    assert document.items[0].points == score
    assert document.items[0].points is not None


@pytest.mark.parametrize(
    "score", [-1, -0.5, True, False, "0", "2.5", float("nan"), float("inf"), -float("inf"), None]
)
@pytest.mark.parametrize("question_index", [0, 3, 6])
def test_real_fixture_invalid_supplied_score_refuses_entire_import(score, question_index):
    fixture = _FIXTURES / "1772718003-test-samma-prov-i-digiexam.dxe"
    payload = json.loads(fixture.read_bytes())
    payload["exams"][0]["questions"][question_index]["maxScore"] = score
    content = json.dumps(payload).encode()
    with pytest.raises(DomainError) as exc_info:
        parse_source_exam(
            upload=ConversionHubUpload(
                filename=fixture.name,
                file_bytes=content,
                content_type="application/octet-stream",
            )
        )
    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    assert exc_info.value.details == {
        "reason_code": "invalid_digiexam_max_score",
        "question_number": question_index + 1,
    }
    assert "maxScore" in exc_info.value.message


def test_real_fixture_absent_score_stays_absent():
    fixture = _FIXTURES / "1772718003-test-samma-prov-i-digiexam.dxe"
    payload = json.loads(fixture.read_bytes())
    del payload["exams"][0]["questions"][0]["maxScore"]
    content = json.dumps(payload).encode()
    exam = parse_source_exam(
        upload=ConversionHubUpload(
            filename=fixture.name, file_bytes=content, content_type="application/octet-stream"
        )
    )
    document = build_native_exam_from_digiexam(
        exam=exam, document_id=uuid4(), source_sha256=hashlib.sha256(content).hexdigest()
    ).document
    assert exam.items[0].max_score is None
    assert document.items[0].points is None


def test_real_question_families_and_formatting_are_not_flattened():
    fixture = _FIXTURES / "1772718003-test-samma-prov-i-digiexam.dxe"
    content = fixture.read_bytes()
    exam = parse_source_exam(
        upload=ConversionHubUpload(
            filename=fixture.name, file_bytes=content, content_type="application/octet-stream"
        )
    )
    native = build_native_exam_from_digiexam(
        exam=exam, document_id=uuid4(), source_sha256=hashlib.sha256(content).hexdigest()
    ).document
    assert [item.kind.value for item in native.items] == [
        "free_text",
        "single_choice",
        "single_choice",
        "multiple_response",
        "multiple_response",
        "multiple_response",
        "gap_fill",
    ]
    assert native.items[0].answer_key.origin.value == "not_applicable"
    assert native.items[-1].gaps


def test_rich_source_runs_keep_their_order_and_native_marks():
    fixture = _FIXTURES / "1772718003-test-samma-prov-i-digiexam.dxe"
    content = fixture.read_bytes()
    exam = parse_source_exam(
        upload=ConversionHubUpload(
            filename=fixture.name, file_bytes=content, content_type="application/octet-stream"
        )
    )
    source = replace(
        exam.items[0],
        prompt_html=("<p>Före <strong>fet</strong> mellan <em>kursiv</em> efter.</p>"),
        prompt_lines=("Före fet mellan kursiv efter.",),
        embedded_assets=(),
        embedded_asset_references=(),
    )
    document = build_native_exam_from_digiexam(
        exam=replace(exam, items=(source,)),
        document_id=uuid4(),
        source_sha256=hashlib.sha256(content).hexdigest(),
    ).document
    segments = document.items[0].body[0].segments
    assert (
        "".join(segment.text for segment in segments if isinstance(segment, NativeTextSegment))
        == "Före fet mellan kursiv efter."
    )
    assert [
        (segment.text, segment.marks)
        for segment in segments
        if isinstance(segment, NativeTextSegment) and segment.marks
    ] == [
        ("fet", ("bold",)),
        ("kursiv", ("italic",)),
    ]


def test_source_image_and_gap_stay_between_their_surrounding_words():
    """Synthetic placement on the real embedded-image/gap IR, not a producer capture."""
    fixture = _FIXTURES / "sanitized-embedded-image.dxe"
    content = fixture.read_bytes()
    exam = parse_source_exam(
        upload=ConversionHubUpload(
            filename=fixture.name, file_bytes=content, content_type="application/octet-stream"
        )
    )
    source = replace(
        exam.items[0],
        prompt_html=(
            '<p>Före <img data-image-id="0" /> mellan '
            '<span class="dxWordGap" dx-wg-id="gap-1"></span> efter.</p>'
        ),
    )
    mapped = build_native_exam_from_digiexam(
        exam=replace(exam, items=(source,)),
        document_id=uuid4(),
        source_sha256=hashlib.sha256(content).hexdigest(),
    )
    segments = mapped.document.items[0].body[0].segments
    assert [segment.kind for segment in segments] == ["text", "asset", "text", "gap", "text"]
    assert [segment.text for segment in segments if isinstance(segment, NativeTextSegment)] == [
        "Före ",
        " mellan ",
        " efter.",
    ]
    assert len(mapped.assets_by_id) == len(mapped.document.assets) == 1
