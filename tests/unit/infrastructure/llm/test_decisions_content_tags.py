"""Synthetic Decisions replies challenge the content-tag transport contract.

These replies prove parsing and request construction, not live model accuracy.
"""

from __future__ import annotations

import json
from dataclasses import replace
from uuid import uuid4

import httpx
import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    SourceImage,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import ExamContentItem
from skriptoteket.infrastructure.llm.openai.decisions_content_tags import (
    build_content_decisions_payload,
    parse_content_decisions_answers,
)
from skriptoteket.protocols.item_type_labeler import (
    ContentTagClassificationRequest,
    ItemTypeLabelerError,
    LabelingItem,
)
from tests.unit.infrastructure.llm.decisions_item_labeler_support import Harness

pytestmark = pytest.mark.unit

_CONTENT = (
    ExamContentItem(id="GY:SVESVE02:grammatik", text="Svenska språkets uppbyggnad."),
    ExamContentItem(id="GY:SVESVE02:litteratur", text="Skönlitterära verkningsmedel."),
)


def test_content_contract_is_independent_of_transport_and_keeps_refusal_identity() -> None:
    items = (LabelingItem("not-a-wire-id", "Fråga"),)
    payload = build_content_decisions_payload(items, _CONTENT, model="contract-test-model")
    assert payload["model"] == "contract-test-model"
    choices, tokens = parse_content_decisions_answers(
        {"answers": [{"name": "content_q1", "type": "refusal"}], "usage": {"input_tokens": True}},
        items,
        _CONTENT,
    )
    assert [(choice.item_id, choice.content_id, choice.probability) for choice in choices] == [
        ("not-a-wire-id", None, 0.0)
    ]
    assert tokens is None, "A boolean is not metered token usage"


def _request(count: int = 2, *, content=_CONTENT) -> ContentTagClassificationRequest:
    return ContentTagClassificationRequest(
        job_id=uuid4(),
        items=tuple(
            LabelingItem(item_id=f"teacher-question-{index}", source_text=f"Källtext {index}: åäö")
            for index in range(count)
        ),
        content_items=tuple(content),
    )


def _answer(question: dict, *, choice_index: int = 0) -> dict:
    choices = question["choices"]
    return {
        "type": "choice",
        "name": question["name"],
        "choice": choices[choice_index]["value"],
        "probabilities": [
            {
                "value": choice["value"],
                "probability": 0.95 if index == choice_index % len(choices) else 0.025,
            }
            for index, choice in enumerate(choices)
        ],
    }


@pytest.mark.asyncio
async def test_content_choices_keep_every_course_bullet_and_none_for_every_question() -> None:
    content = tuple(
        ExamContentItem(id=f"course:bullet-{i}", text=f"Innehåll {i}") for i in range(80)
    )

    def respond(request: httpx.Request) -> httpx.Response:
        sent = json.loads(request.content)
        assert len(sent["questions"]) == 2
        for question in sent["questions"]:
            assert len(question["choices"]) == 81, "Never silently truncate course content"
            descriptions = [choice["description"] for choice in question["choices"]]
            assert descriptions[:-1] == [item.text for item in content]
            assert "Inget av dessa" in descriptions[-1]
        assert "Källtext 0: åäö" in str(sent["input"])
        assert "Källtext 1: åäö" in str(sent["input"])
        assert "reasoning" not in sent
        return httpx.Response(200, json={"answers": [_answer(q) for q in sent["questions"]]})

    result = await Harness(respond).labeler().classify_content(request=_request(content=content))
    assert [choice.item_id for choice in result.results] == [
        "teacher-question-0",
        "teacher-question-1",
    ]
    assert {choice.content_id for choice in result.results} == {content[0].id}


@pytest.mark.asyncio
async def test_out_of_order_answers_keep_question_citations_and_none_stays_none() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        questions = json.loads(request.content)["questions"]
        return httpx.Response(
            200,
            json={
                "answers": [_answer(questions[1], choice_index=-1), _answer(questions[0])],
                "usage": {"input_tokens": 73},
            },
        )

    result = await Harness(respond).labeler().classify_content(request=_request())
    assert [(r.item_id, r.content_id) for r in result.results] == [
        ("teacher-question-0", _CONTENT[0].id),
        ("teacher-question-1", None),
    ]
    assert result.usage.input_tokens == 73


@pytest.mark.asyncio
async def test_201_questions_split_without_losing_sources_choices_or_usage() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        questions = json.loads(request.content)["questions"]
        return httpx.Response(
            200,
            json={
                "answers": [_answer(q) for q in questions],
                "usage": {"input_tokens": len(questions)},
            },
        )

    harness = Harness(respond)
    result = await harness.labeler().classify_content(request=_request(201))
    question_counts = []
    for sent in harness.requests:
        questions = sent["questions"]
        assert isinstance(questions, list)
        question_counts.append(len(questions))
    assert sorted(question_counts) == [1, 200]
    assert [r.item_id for r in result.results] == [f"teacher-question-{i}" for i in range(201)]
    assert result.usage.input_tokens == 201
    assert result.usage.requests == 2
    assert result.usage.attempts == 2
    for sent in harness.requests:
        for question in sent["questions"]:
            choices = question["choices"]
            assert isinstance(choices, list)
            assert len(choices) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("empty", ["questions", "content"])
async def test_empty_inputs_never_call_decisions(empty: str) -> None:
    def unexpected(_request: httpx.Request) -> httpx.Response:
        pytest.fail("An exam without questions or course content must not call the model")

    request = _request(0) if empty == "questions" else _request(content=())
    result = await Harness(unexpected).labeler().classify_content(request=request)
    assert result.results == ()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "defect",
    [
        "missing",
        "duplicate",
        "foreign",
        "unknown_choice",
        "missing_probability",
        "boolean",
        "negative",
        "above_one",
        "duplicate_probability",
        "not_top",
    ],
)
async def test_invalid_answers_fail_closed_instead_of_manufacturing_tags(defect: str) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        questions = json.loads(request.content)["questions"]
        answers = [_answer(q) for q in questions]
        if defect == "missing":
            answers.pop()
        elif defect == "duplicate":
            answers[1] = answers[0]
        elif defect == "foreign":
            answers[1]["name"] = "not-a-requested-question"
        elif defect == "unknown_choice":
            answers[0]["choice"] = "another-course:unknown-content"
        elif defect == "missing_probability":
            answers[0]["probabilities"] = answers[0]["probabilities"][1:]
        elif defect == "duplicate_probability":
            answers[0]["probabilities"].append(answers[0]["probabilities"][0])
        elif defect == "not_top":
            answers[0]["choice"] = questions[0]["choices"][-1]["value"]
        else:
            answers[0]["probabilities"][0]["probability"] = {
                "boolean": True,
                "negative": -0.1,
                "above_one": 1.01,
            }[defect]
        return httpx.Response(200, json={"answers": answers})

    with pytest.raises(ItemTypeLabelerError):
        await Harness(respond).labeler().classify_content(request=_request())


def test_image_budget_is_not_proportional_to_base64_encoded_file_size() -> None:
    def unexpected(_request: httpx.Request) -> httpx.Response:
        pytest.fail("Estimating a lease must not call the network")

    adapter = Harness(unexpected).labeler()
    request = _request(1)
    small = replace(
        request,
        items=(
            replace(
                request.items[0],
                images=(SourceImage(png=b"small-image", offset=0),),
            ),
        ),
    )
    large = replace(
        request,
        items=(
            replace(
                request.items[0],
                images=(SourceImage(png=b"large-image" * 100_000, offset=0),),
            ),
        ),
    )
    assert adapter.estimate_content_tokens(request=small) == adapter.estimate_content_tokens(
        request=large,
    )
    assert adapter.estimate_content_tokens(request=small) > adapter.estimate_content_tokens(
        request=request,
    )
