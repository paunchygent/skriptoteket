"""A gap_fill reply that makes a gap of the material its line talks about comes back as review
required; a reply that keeps that material as text stays as converted (D43, user decision
2026-10-12).

``docx_build_v16_d43_gap_material`` holds three replies for one question, whose chunk sets four
phrases in italics: the low-25 live reply that keeps the material as text, the low-26 live reply
that returns outcome review, and the reply the second staging upload recorded in its captured
document, which makes all four phrases gaps. It also holds every converted gap_fill item that
the eval runs low-23 to low-26 recorded for the eight corpus exams.
"""

import json
from functools import cache
from uuid import uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_gap_material import (
    GAPPED_MATERIAL_REASON,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItemKind,
    NativeGapSegment,
    NativeItemReviewState,
    NativeParseOrigin,
    NativeTextSegment,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    FIXTURES,
    corpus_chunks,
)

pytestmark = pytest.mark.unit

_ROOT = FIXTURES / "docx_build_v16_d43_gap_material"
_EXAM = "svenska_2_kursavslutande_prov_med_facit"
_QUESTION = ("body:0085", "body:0086", "body:0087")


@cache
def _chunks(exam: str) -> tuple[DocxChunk, ...]:
    return corpus_chunks(exam)


def _reply(name: str) -> dict[str, JsonValue]:
    reply: dict[str, JsonValue] = json.loads((_ROOT / name).read_text())
    return reply


def _admitted(reply: dict[str, JsonValue], exam: str, question: tuple[str, ...]):
    """``reply`` admitted as the batch that owns ``question`` alone."""
    state = DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename=f"{exam}.docx",
        source_sha256="0" * 64,
        chunks=_chunks(exam),
        claimable=frozenset(question),
        questions=(question,),
    )
    admit_batch(reply, state)
    return state


def test_a_reply_that_makes_the_material_a_gap_comes_back_as_review_required():
    state = _admitted(_reply("staging_second_upload_q20.json"), _EXAM, _QUESTION)

    ((item, anchors),) = state.accepted
    assert anchors == _QUESTION
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert item.review.parse_origin is NativeParseOrigin.DETERMINISTIC
    assert item.gaps == ()
    (reason,) = item.review.reasons
    assert reason.startswith(GAPPED_MATERIAL_REASON)
    assert "”De väntar inte.”" in reason, "the reason names the phrase that became a gap"
    text = {chunk.anchor: chunk.text for chunk in _chunks(_EXAM)}
    shown = [s.text for p in item.body for s in p.segments if isinstance(s, NativeTextSegment)]
    assert shown == [text[a] for a in _QUESTION], "the teacher sees the question as printed"
    assert [(e.code, e.anchors) for e in state.events] == [("gapped_material", _QUESTION)]


def test_a_reply_that_keeps_the_material_as_text_stays_as_converted():
    state = _admitted(_reply("low25_docx_w2-08-01.json"), _EXAM, _QUESTION)

    ((item, anchors),) = state.accepted
    assert anchors == _QUESTION
    assert item.kind is NativeExamItemKind.GAP_FILL
    assert item.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert [gap.accepted_values for gap in item.gaps] == [("huvudsats",), ("före",)]
    segments = [s for p in item.body for s in p.segments]
    assert [s.text for s in segments if isinstance(s, NativeTextSegment)] == [
        "a) De väntar inte. är en ",
        "b) I bisatsen att de inte väntar står satsadverbialet ",
        " det finita verbet.",
    ]
    assert sum(isinstance(s, NativeGapSegment) for s in segments) == 2
    assert state.events == []


def test_a_reply_that_cannot_tell_the_phrases_apart_stays_a_model_review():
    state = _admitted(_reply("low26_docx_w2-09-01.json"), _EXAM, _QUESTION)

    ((item, _),) = state.accepted
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert item.review.reasons == (
        "AI-tolkningen markerade frågan för granskning: Det saknas tydliga svarsfält; det går "
        "inte att avgöra vilka kursiverade ord som ska vara luckor.",
    )
    assert [e.code for e in state.events] == ["model_review"]


def _recorded_gap_fill() -> list[dict[str, JsonValue]]:
    entries: list[dict[str, JsonValue]] = json.loads(
        (_ROOT / "gap_fill_items_low23_to_low26.json").read_text()
    )
    return entries


@pytest.mark.parametrize(
    "entry",
    _recorded_gap_fill(),
    ids=lambda entry: f"{entry['run']}-{entry['exam']}-{entry['reply']}",
)
def test_no_recorded_gap_fill_item_of_the_corpus_is_sent_to_review_for_gapped_material(entry):
    item = entry["item"]
    assert isinstance(item, dict)
    exam = entry["exam"]
    assert isinstance(exam, str)
    anchors = item["source_anchors"]
    assert isinstance(anchors, list)
    state = _admitted({"items": [item]}, exam, tuple(str(a) for a in anchors))

    assert "gapped_material" not in {e.code for e in state.events}
    reasons = {reason for admitted, _ in state.accepted for reason in admitted.review.reasons}
    assert not any(reason.startswith(GAPPED_MATERIAL_REASON) for reason in reasons)
