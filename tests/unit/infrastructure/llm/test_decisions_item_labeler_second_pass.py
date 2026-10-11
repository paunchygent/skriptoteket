from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Literal
from uuid import uuid4

import httpx
import pytest
from pydantic import BaseModel, JsonValue, TypeAdapter

from skriptoteket.infrastructure.llm.openai.decisions_item_labeler import (
    OpenAIDecisionsItemTypeLabeler,
)
from skriptoteket.protocols.item_type_labeler import (
    ItemTypeLabel,
    ItemTypeLabelerError,
    ItemTypeLabeling,
    LabelingItem,
    LabelingRequest,
    LabelRoute,
    ThresholdPolicy,
)

pytestmark = pytest.mark.unit

FIXTURES = Path("tests/fixtures/item_type_labeler")
SECOND_PASS = "corpus_exam_24_questions_second_pass.json"
CONTEXT_MARKER = "Source above the question (read-only context):"
QUESTION_MARKER = "Question as the student sees it:\n"

Responder = Callable[[httpx.Request], httpx.Response]
RAW_REQUEST = TypeAdapter(dict[str, JsonValue])


class RecordedChoice(BaseModel):
    value: ItemTypeLabel
    description: str


class RecordedQuestion(BaseModel):
    type: Literal["choice"]
    name: str
    instructions: str
    choices: list[RecordedChoice]


class RecordedRequest(BaseModel):
    model: str
    input: str
    questions: list[RecordedQuestion]


class RecordedProbability(BaseModel):
    value: ItemTypeLabel
    probability: float


class RecordedAnswer(BaseModel):
    type: Literal["choice"]
    name: str
    choice: ItemTypeLabel
    probabilities: list[RecordedProbability]
    confidence: float


class RecordedUsage(BaseModel):
    input_tokens: int


class RecordedBody(BaseModel):
    answers: list[RecordedAnswer]
    usage: RecordedUsage


class RecordedResponse(BaseModel):
    status_code: int
    headers: dict[str, str]
    body: dict[str, JsonValue] | str


class RecordedExchange(RecordedResponse):
    request: dict[str, JsonValue]

    def answered(self) -> RecordedBody:
        return RecordedBody.model_validate(self.body)


class SecondPassFixture(BaseModel):
    items: tuple[LabelingItem, ...]
    exchanges: list[RecordedExchange]


class UnavailableFixture(BaseModel):
    responses: list[RecordedResponse]


def _load(name: str) -> SecondPassFixture:
    return SecondPassFixture.model_validate_json((FIXTURES / name).read_bytes())


def _unavailable(status_code: int) -> RecordedResponse:
    fixture = UnavailableFixture.model_validate_json(
        (FIXTURES / "decisions_unavailable_responses.json").read_bytes()
    )
    return next(r for r in fixture.responses if r.status_code == status_code)


def _recorded_response(recording: RecordedResponse) -> httpx.Response:
    body = recording.body
    if isinstance(body, str):
        return httpx.Response(recording.status_code, headers=recording.headers, text=body)
    return httpx.Response(recording.status_code, headers=recording.headers, json=body)


def _chosen_probability(answer: RecordedAnswer) -> float:
    by_value = {entry.value: entry.probability for entry in answer.probabilities}
    return by_value[answer.choice]


class RecordingSleeper:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def sleep(self, seconds: float) -> None:
        self.delays.append(seconds)


class Harness:
    def __init__(self, responder: Responder) -> None:
        self.requests: list[RecordedRequest] = []
        self.sleeper = RecordingSleeper()
        self._responder = responder

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/decisions"
        assert request.headers["Authorization"] == "Bearer fixture-key"
        self.requests.append(RecordedRequest.model_validate_json(request.content))
        return self._responder(request)

    def labeler(self) -> OpenAIDecisionsItemTypeLabeler:
        return OpenAIDecisionsItemTypeLabeler(
            client=httpx.AsyncClient(transport=httpx.MockTransport(self.handle)),
            base_url="https://example.test",
            api_key="fixture-key",
            timeout_seconds=30,
            sleeper=self.sleeper,
            policy=ThresholdPolicy(),
        )


def _replay(exchanges: list[RecordedExchange]) -> Responder:
    def respond(request: httpx.Request) -> httpx.Response:
        sent = RAW_REQUEST.validate_json(request.content)
        matches = [exchange for exchange in exchanges if exchange.request == sent]
        assert len(matches) == 1, "adapter did not rebuild a recorded request"
        return _recorded_response(matches[0])

    return respond


def _item_index_of(request: RecordedRequest, fixture: SecondPassFixture) -> int:
    """The item a single-question second-pass request re-asks, found by its rendered question."""

    rendered = request.input
    matches = [
        index
        for index, item in enumerate(fixture.items)
        if QUESTION_MARKER + item.source_text in rendered
    ]
    assert len(matches) == 1, "second-pass request does not name exactly one item"
    return matches[0]


def _first_pass_answers(fixture: SecondPassFixture) -> list[RecordedAnswer]:
    return fixture.exchanges[0].answered().answers


def _second_pass_exchanges(fixture: SecondPassFixture) -> dict[int, RecordedExchange]:
    return {
        _item_index_of(request, fixture): exchange
        for exchange in fixture.exchanges
        if len((request := RecordedRequest.model_validate(exchange.request)).questions) == 1
    }


def _escalated_with_context(fixture: SecondPassFixture) -> set[int]:
    return {
        index
        for index, (answer, item) in enumerate(
            zip(_first_pass_answers(fixture), fixture.items, strict=True)
        )
        if _chosen_probability(answer) < 0.95 and item.expanded_context
    }


async def _label_all(fixture: SecondPassFixture) -> tuple[Harness, ItemTypeLabeling]:
    harness = Harness(_replay(fixture.exchanges))
    request = LabelingRequest(job_id=uuid4(), items=fixture.items)
    labeling = await harness.labeler().label(request=request)
    return harness, labeling


async def test_only_escalated_questions_with_context_are_re_asked_alone() -> None:
    fixture = _load(SECOND_PASS)

    harness, _ = await _label_all(fixture)

    assert len(harness.requests) == 1 + len(_second_pass_exchanges(fixture))
    batched = [sent for sent in harness.requests if len(sent.questions) > 1]
    single = [sent for sent in harness.requests if len(sent.questions) == 1]
    assert len(batched) == 1
    assert len(batched[0].questions) == len(fixture.items)
    assert CONTEXT_MARKER not in batched[0].input
    assert all(CONTEXT_MARKER in sent.input for sent in single)
    escalated = _escalated_with_context(fixture)
    re_asked = {_item_index_of(sent, fixture) for sent in single}
    assert re_asked == escalated
    assert len(single) == len(escalated)
    escalated_without_context = [
        index
        for index, answer in enumerate(_first_pass_answers(fixture))
        if _chosen_probability(answer) < 0.95 and not fixture.items[index].expanded_context
    ]
    assert not re_asked & set(escalated_without_context)


async def test_second_pass_result_replaces_first_pass_and_keeps_it() -> None:
    fixture = _load(SECOND_PASS)
    first_answers = _first_pass_answers(fixture)
    second = _second_pass_exchanges(fixture)

    _, labeling = await _label_all(fixture)

    assert [r.item_id for r in labeling.results] == [i.item_id for i in fixture.items]
    for index, result in enumerate(labeling.results):
        if index not in second:
            assert result.first_pass is None
            assert result.label == first_answers[index].choice
            assert result.probability == _chosen_probability(first_answers[index])
            continue
        first = result.first_pass
        assert first is not None
        assert first.item_id == result.item_id
        assert first.label == first_answers[index].choice
        assert first.probability == _chosen_probability(first_answers[index])
        assert first.route == LabelRoute.ESCALATE
        assert first.first_pass is None
        answer = second[index].answered().answers[0]
        probability = _chosen_probability(answer)
        assert result.label == answer.choice
        assert result.probability == probability
        expected = LabelRoute.ACCEPT if probability >= 0.95 else LabelRoute.ESCALATE
        assert result.route == expected


async def test_usage_sums_both_passes_and_estimate_covers_them() -> None:
    fixture = _load(SECOND_PASS)
    harness = Harness(_replay(fixture.exchanges))
    request = LabelingRequest(job_id=uuid4(), items=fixture.items)
    labeler = harness.labeler()

    labeling = await labeler.label(request=request)

    recorded = [e.answered().usage.input_tokens for e in fixture.exchanges]
    assert labeling.usage.input_tokens == sum(recorded)
    assert labeling.usage.requests == 1 + len(_second_pass_exchanges(fixture))
    assert labeling.usage.attempts == len(fixture.exchanges)
    estimate = labeler.estimate_input_tokens(request=request)
    assert estimate >= recorded[0]
    assert estimate > sum(recorded)


async def test_items_without_expanded_context_get_no_second_pass() -> None:
    fixture = _load(SECOND_PASS)
    harness = Harness(_replay(fixture.exchanges[:1]))
    items = tuple(replace(item, expanded_context=None) for item in fixture.items)

    labeling = await harness.labeler().label(request=LabelingRequest(job_id=uuid4(), items=items))

    assert len(harness.requests) == 1
    assert labeling.usage.requests == 1
    assert any(r.route == LabelRoute.ESCALATE for r in labeling.results)
    assert all(r.first_pass is None for r in labeling.results)


async def test_unavailable_second_pass_raises_after_successful_first_pass() -> None:
    fixture = _load(SECOND_PASS)
    replay = _replay(fixture.exchanges[:1])
    outage = _unavailable(503)

    def respond(request: httpx.Request) -> httpx.Response:
        if len(RecordedRequest.model_validate_json(request.content).questions) == 1:
            _replay(list(_second_pass_exchanges(fixture).values()))(request)
            return _recorded_response(outage)
        return replay(request)

    harness = Harness(respond)

    with pytest.raises(ItemTypeLabelerError) as caught:
        await harness.labeler().label(request=LabelingRequest(job_id=uuid4(), items=fixture.items))

    assert caught.value.code == "provider_unavailable"
    assert caught.value.status_code == 503
    assert len(harness.requests[0].questions) == len(fixture.items)
    assert len(harness.requests) == 1 + 3 * len(_escalated_with_context(fixture))
