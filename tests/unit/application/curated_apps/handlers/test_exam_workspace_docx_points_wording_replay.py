"""Trailing points wording leaves Word item bodies once points are settled (D2, D7, D8).

Replays the three recorded exams whose item bodies keep printed points wording,
through the production DOCX pipeline: the wording whose number equals the item's
points leaves the body, the points and every source record stay, and no item
records a leftover candidate.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import (
    body_plain_text,
    body_text_lines,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import build_replay

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_ENGLISH = "bf26_english_1_unit_test_kap_1_2_med_facit"
_METODPROV = "metodprov_vetenskaplig_metod_med_facit"
_OMPROV_1 = "svenska_2_grammatik_omprov_variant_1_med_facit"
_OMPROV_2 = "svenska_2_grammatik_omprov_variant_2_med_facit"

_converted: dict[str, NativeExamDocument] = {}


async def _document(exam: str) -> NativeExamDocument:
    if exam not in _converted:
        replay = build_replay(exam)
        _converted[exam] = (await replay.pipeline.convert(job=replay.job())).result.document
    return _converted[exam]


def _first_paragraph_text(item) -> str:
    from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
        NativeTextSegment,
    )

    run: list[str] = []
    for segment in reversed(item.body[0].segments):
        if not isinstance(segment, NativeTextSegment):
            break
        run.append(segment.text)
    run.reverse()
    return "".join(run)


async def test_forced_provider_failure_strips_first_paragraph_labels() -> None:
    """Every batch fails, so items are built by source fallback with heading stems.

    A parenthesised label ending the first paragraph and equalling the item's
    points leaves (Q8, Q9); points, retry_source and import_record stay, and no
    item records a leftover candidate.
    """
    from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
        StructuredLLMBackendFailureCode,
        StructuredLLMProviderError,
    )
    from skriptoteket.domain.curated_apps.exam_workspace.points_wording import (
        body_without_trailing_points,
        trailing_points,
        with_settled_points_wording,
    )

    error = StructuredLLMProviderError(
        failure_code=StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR,
        message="boom",
        provider_id="replay-probe",
        status_code=400,
    )
    for exam in (_METODPROV, _ENGLISH):
        probe = build_replay(exam)
        await probe.pipeline.convert(job=probe.job())
        batches = {r.item_id for r in probe.provider.requests if r.item_id.startswith("docx_w")}
        assert batches
        replay = build_replay(exam, failures={batch: error for batch in batches})
        outcome = await replay.pipeline.convert(job=replay.job())
        document = outcome.result.document
        assert document.items
        for item in document.items:
            assert item.retry_source is not None
            assert item.import_record is not None
            assert body_without_trailing_points(item.body, item.points) == item.body
            assert with_settled_points_wording(item) == item
            if len(item.body) >= 2:
                found = trailing_points(_first_paragraph_text(item))
                assert not (
                    found is not None and not found.whole_line and found.value == item.points
                ), (exam, item.source_anchor, _first_paragraph_text(item)[-60:])
        leftovers = [
            (item.item_id, item.source_anchor)
            for item in document.items
            if item.leftover_points_text is not None
        ]
        assert leftovers == []


async def test_forced_provider_failure_keeps_two_concrete_first_paragraphs() -> None:
    from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
        StructuredLLMBackendFailureCode,
        StructuredLLMProviderError,
    )

    error = StructuredLLMProviderError(
        failure_code=StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR,
        message="boom",
        provider_id="replay-probe",
        status_code=400,
    )
    for exam, anchor, points, stripped in (
        (_METODPROV, "body:0037", 1, "5. Resor till skolan"),
        (
            _ENGLISH,
            "body:0059",
            3,
            "1. Select the word or phrase for each definition.",
        ),
    ):
        probe = build_replay(exam)
        await probe.pipeline.convert(job=probe.job())
        batches = {r.item_id for r in probe.provider.requests if r.item_id.startswith("docx_w")}
        replay = build_replay(exam, failures={batch: error for batch in batches})
        outcome = await replay.pipeline.convert(job=replay.job())
        item = next(i for i in outcome.result.document.items if i.source_anchor == anchor)
        assert item.points == points
        assert _first_paragraph_text(item) == stripped
        assert item.retry_source is not None
        assert item.import_record is not None


def _retry_text(item) -> str:
    assert item.retry_source is not None
    return "\n".join(chunk.text for chunk in item.retry_source.chunks)


async def test_english_lunch_menu_item_loses_its_points_label() -> None:
    document = await _document(_ENGLISH)
    item = next(item for item in document.items if item.item_id == "item_043")

    assert item.points == 1
    assert body_plain_text(item.body).endswith("lunch menu.")
    assert "(1 point)" not in body_plain_text(item.body)
    assert "(1 point)" in _retry_text(item)
    assert item.import_record is not None
    assert "(1 point)" in item.import_record.original_wording.question_text
    assert item.facit_text is None
    assert item.leftover_points_text is None


@pytest.mark.parametrize("exam", [_OMPROV_1, _OMPROV_2])
async def test_omprov_first_question_loses_its_points_line(exam: str) -> None:
    document = await _document(exam)
    item = next(item for item in document.items if item.sequence == 1)

    assert item.points == 6
    assert "Poäng: 6 poäng" not in body_text_lines(item.body)
    assert "Poäng: 6 poäng" in _retry_text(item)
    assert item.import_record is not None
    assert "Poäng: 6 poäng" in item.import_record.original_wording.question_text
    assert item.facit_text is not None
    assert "Svar:" in item.facit_text
    assert "Poäng: 6 poäng" not in item.facit_text
    assert item.leftover_points_text is None


@pytest.mark.parametrize("exam", [_ENGLISH, _OMPROV_1, _OMPROV_2])
async def test_no_replay_item_records_a_leftover_candidate(exam: str) -> None:
    document = await _document(exam)

    offenders = [
        (item.item_id, item.sequence, body_plain_text(item.body)[-80:])
        for item in document.items
        if item.leftover_points_text is not None
    ]

    assert offenders == []


def test_a_sentence_that_mentions_points_keeps_its_text_through_the_build() -> None:
    """Regression for 334354b9: a stem that mentions points mid-sentence is prose.

    "Väljer eleven det får den 2 poäng." ends in "2 poäng." but never matches
    the trailing-wording shapes, so the final gate leaves it and records nothing.
    """
    from uuid import uuid4

    from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import (
        assemble_build_result,
    )
    from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
    from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_item import (
        aligned_native_item,
    )
    from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk

    stem = "Väljer eleven det får den 2 poäng."
    chunk = DocxChunk(anchor="body:0001", kind="paragraph", text=stem, marked_text=stem)
    produced = ProducedItem.model_validate(
        {
            "source_anchors": ["body:0001"],
            "outcome": "converted",
            "review_reason": None,
            "kind": "free_text",
            "key_source": None,
            "facit_text": None,
            "printed_label": None,
            "body": [{"segments": [{"kind": "text", "text": stem, "accepted_values": []}]}],
            "points": 2,
            "choices": [],
            "match_left": [],
            "match_right": [],
            "match_pairs": [],
            "criteria": [],
        }
    )
    result = assemble_build_result(
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=(chunk,),
        accepted=(
            (aligned_native_item(produced, foreign_chunks=(), language="sv"), ("body:0001",)),
        ),
        review_reasons={},
        questions=(("body:0001",),),
    )

    (item,) = result.document.items
    assert body_plain_text(item.body) == stem
    assert item.points == 2
    assert item.leftover_points_text is None
