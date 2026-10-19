"""Typography proof on unmodified, recorded model replies and the real DOCX corpus."""

from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeTextSegment
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_json import (
    native_exam_document_json_bytes,
    parse_native_exam_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import FORMATTING_REASON
from tests.unit.application.curated_apps.handlers.docx_conversion_cache import (
    ConversionCache,
    conversion_cache_fixture,  # noqa: F401 - registers the `conversions` fixture
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    corpus_chunks,
    recorded_exams,
    recording,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.mark.parametrize("exam", recorded_exams())
async def test_recorded_corpus_has_no_unrecoverable_formatting_transfer(
    exam, conversions: ConversionCache
):
    outcome = (await conversions.converted(exam)).outcome
    document = outcome.update.document
    failures = [
        (item.printed_label, item.review.reasons)
        for item in document.items
        if FORMATTING_REASON in item.review.reasons
    ]
    assert failures == []
    assert parse_native_exam_document(native_exam_document_json_bytes(document)) == document


async def test_svenska_2_question_17_keeps_the_three_analysed_phrases_in_italics(
    conversions: ConversionCache,
):
    outcome = (await conversions.converted("svenska_2_kursavslutande_prov_med_facit")).outcome
    item = next(item for item in outcome.update.document.items if item.printed_label == "Fråga 17")
    italic = " ".join(
        segment.text
        for paragraph in item.body
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment) and "italic" in segment.marks
    )
    for phrase in ("tre korta svar", "på skolgården", "kan vila"):
        assert phrase in italic
    text = body_plain_text(item.body)
    assert text.count("[___]") == 3
    assert "är en NF" not in text and "är en PF" not in text and "är en VF" not in text


async def test_failed_reconstruction_uses_the_exact_swedish_review_reason():
    exam = "svenska_2_kursavslutande_prov_med_facit"
    reply = recording(exam, "docx_w1-02")
    items = reply["items"]
    assert isinstance(items, list)
    raw = next(
        item for item in items if isinstance(item, dict) and item.get("printed_label") == "Fråga 17"
    )
    raw["key_source"] = None
    body = raw["body"]
    assert isinstance(body, list)
    for paragraph in body:
        assert isinstance(paragraph, dict)
        segments = paragraph["segments"]
        assert isinstance(segments, list)
        for segment in segments:
            assert isinstance(segment, dict)
            if segment["kind"] == "text":
                text = segment["text"]
                assert isinstance(text, str)
                for phrase in ("tre korta svar", "på skolgården", "kan vila"):
                    text = text.replace(phrase, "ersatt fras")
                segment["text"] = text
            elif segment["kind"] == "gap":
                segment["accepted_values"] = []
    anchors = raw["source_anchors"]
    assert isinstance(anchors, list)
    chunks = tuple(c for c in corpus_chunks(exam) if c.anchor in anchors)
    state = DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename=f"{exam}.docx",
        source_sha256="a" * 64,
        chunks=chunks,
        questions=(tuple(c.anchor for c in chunks),),
    )
    admit_batch(
        {"title": None, "instructions": [], "answer_key_anchors": [], "items": [raw]}, state
    )
    item = state.accepted[0][0].item
    assert item.review.reasons == (FORMATTING_REASON,)
    assert any(
        "italic" in segment.marks
        for p in item.body
        for segment in p.segments
        if isinstance(segment, NativeTextSegment)
    )


async def test_unmarked_morpheme_alignment_goes_to_review_with_the_word_and_never_leaks_facit(
    conversions: ConversionCache,
):
    outcome = (
        await conversions.converted("svenska_2_grammatik_omprov_variant_1_med_facit")
    ).outcome
    item = next(item for item in outcome.update.document.items if item.printed_label == "Fråga 1")
    assert FORMATTING_REASON not in item.review.reasons
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert item.gaps == ()
    text = body_plain_text(item.body)
    assert "snöbollarnas" in text
    assert "a) snö + boll + ar + na + s" not in text
    assert "Svar:" not in text
    assert "(R)" not in text and "(A)" not in text and "(B)" not in text
