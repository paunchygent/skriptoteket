"""A gap_fill reply that makes a gap of the material its line talks about comes back as review
required; a reply that keeps that material as text stays as converted (D43, user decision
2026-10-12).

``docx_build_v16_d43_gap_material`` holds four replies for one question, whose chunk sets four
phrases in italics: the low-25 live reply that keeps the material as text, the low-26 live reply
that returns outcome review, and two replies that make all four phrases gaps: the low-28 live
reply and the reply the second staging upload recorded in its captured document. It also holds
every converted gap_fill item that the eval runs low-23 to low-26 recorded for the eight corpus
exams.
"""

import json
import re
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
    NativeExamItem,
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
_SET_APART = re.compile(r"<i>(.*?)</i>", re.S)


def _scenario() -> dict[str, JsonValue]:
    scenario: dict[str, JsonValue] = json.loads((_ROOT / "scenario.json").read_text())
    return scenario


def _scenario_text(key: str) -> str:
    value = _scenario()[key]
    assert isinstance(value, str)
    return value


def _scenario_texts(key: str) -> list[str]:
    value = _scenario()[key]
    assert isinstance(value, list)
    return [str(entry) for entry in value]


_SOURCE = _scenario_text("source")
_QUESTION = tuple(_scenario_texts("anchors"))


@cache
def _chunks(exam: str) -> tuple[DocxChunk, ...]:
    return corpus_chunks(exam)


def _string(value: JsonValue) -> str:
    assert isinstance(value, str)
    return value


def _strings(value: JsonValue) -> list[str]:
    assert isinstance(value, list)
    return [_string(entry) for entry in value]


def _objects(value: JsonValue) -> list[dict[str, JsonValue]]:
    assert isinstance(value, list)
    objects: list[dict[str, JsonValue]] = []
    for entry in value:
        assert isinstance(entry, dict)
        objects.append(entry)
    return objects


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


def _text_segments(item: NativeExamItem) -> list[str]:
    return [s.text for p in item.body for s in p.segments if isinstance(s, NativeTextSegment)]


def _kept_material() -> list[str]:
    """The phrases the source sets apart that the reply which keeps them as text leaves printed."""
    state = _admitted(_reply(_scenario_text("material_kept_as_text")), _SOURCE, _QUESTION)
    ((item, _),) = state.accepted
    printed = " ".join(_text_segments(item))
    phrases = [
        phrase.strip()
        for chunk in _chunks(_SOURCE)
        if chunk.anchor in _QUESTION
        for phrase in _SET_APART.findall(chunk.marked_text)
    ]
    return [phrase for phrase in phrases if phrase in printed]


@pytest.mark.parametrize("name", _scenario_texts("material_made_gaps"))
def test_a_reply_that_makes_the_material_a_gap_comes_back_as_review_required(name: str):
    state = _admitted(_reply(name), _SOURCE, _QUESTION)

    ((item, anchors),) = state.accepted
    assert anchors == _QUESTION
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert item.review.parse_origin is NativeParseOrigin.DETERMINISTIC
    assert item.gaps == ()
    (reason,) = item.review.reasons
    material = _kept_material()
    assert material, "the replay that keeps the material as text names what it keeps"
    assert any(phrase in reason for phrase in material), "the reason names the phrase made a gap"
    text = {chunk.anchor: chunk.text for chunk in _chunks(_SOURCE)}
    assert _text_segments(item) == [text[a] for a in _QUESTION], "printed as in the source"
    assert [(e.code, e.anchors) for e in state.events] == [("gapped_material", _QUESTION)]


def test_a_reply_that_keeps_the_material_as_text_stays_as_converted():
    reply = _reply(_scenario_text("material_kept_as_text"))
    state = _admitted(reply, _SOURCE, _QUESTION)

    ((item, anchors),) = state.accepted
    assert anchors == _QUESTION
    assert item.review.state is NativeItemReviewState.REVIEW_COMPLETE
    produced = reply["items"]
    assert isinstance(produced, list)
    captured = produced[0]
    assert isinstance(captured, dict)
    segments = [
        s for paragraph in _objects(captured["body"]) for s in _objects(paragraph["segments"])
    ]
    captured_gaps = [tuple(_strings(s["accepted_values"])) for s in segments if s["kind"] == "gap"]
    captured_text = [_string(s["text"]) for s in segments if s["kind"] == "text"]
    assert item.kind.value == captured["kind"]
    assert [gap.accepted_values for gap in item.gaps] == captured_gaps
    assert _text_segments(item) == captured_text
    assert sum(isinstance(s, NativeGapSegment) for p in item.body for s in p.segments) == len(
        captured_gaps
    )
    assert state.events == []


def test_a_reply_that_cannot_tell_the_phrases_apart_stays_a_model_review():
    reply = _reply(_scenario_text("model_review"))
    state = _admitted(reply, _SOURCE, _QUESTION)

    produced = reply["items"]
    assert isinstance(produced, list)
    captured = produced[0]
    assert isinstance(captured, dict)
    explanation = captured["review_reason"]
    assert isinstance(explanation, str)
    ((item, _),) = state.accepted
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert item.gaps == ()
    (reason,) = item.review.reasons
    assert explanation in reason
    assert [e.code for e in state.events] == ["model_review"]


def _recorded_gap_fill() -> list[dict[str, JsonValue]]:
    entries: list[dict[str, JsonValue]] = json.loads(
        (_ROOT / "gap_fill_items_low23_to_low26.json").read_text()
    )
    return entries


@pytest.mark.parametrize(
    "entry",
    [
        pytest.param(entry, id=f"{entry['run']}-{position}")
        for position, entry in enumerate(_recorded_gap_fill())
    ],
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
