from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import pytest

from skriptoteket.infrastructure.llm.openai.decisions_item_labeler import (
    OpenAIDecisionsItemTypeLabeler,
)
from skriptoteket.protocols.item_type_labeler import (
    ItemTypeLabel,
    ItemTypeLabelerError,
    LabelingItem,
    LabelingRequest,
    LabelRoute,
    ThresholdPolicy,
)

pytestmark = pytest.mark.unit

FIXTURES = Path("tests/fixtures/item_type_labeler")
CORPUS_24 = "corpus_exam_24_questions.json"
CORPUS_204 = "corpus_three_exams_204_questions.json"

Responder = Callable[[httpx.Request], httpx.Response]


def _load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return data


def _request_for(fixture: dict[str, Any]) -> LabelingRequest:
    return LabelingRequest(
        job_id=uuid4(), items=tuple(LabelingItem(**item) for item in fixture["items"])
    )


def _unavailable(status_code: int) -> dict[str, Any]:
    responses = _load("decisions_unavailable_responses.json")["responses"]
    return next(r for r in responses if r["status_code"] == status_code)


def _recorded_response(recording: dict[str, Any], status_code: int | None = None) -> httpx.Response:
    status = recording["status_code"] if status_code is None else status_code
    body = recording["body"]
    if isinstance(body, str):
        return httpx.Response(status, headers=recording["headers"], text=body)
    return httpx.Response(status, headers=recording["headers"], json=body)


def _chosen_probability(answer: dict[str, Any]) -> float:
    by_value = {entry["value"]: entry["probability"] for entry in answer["probabilities"]}
    return float(by_value[answer["choice"]])


class RecordingSleeper:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def sleep(self, seconds: float) -> None:
        self.delays.append(seconds)


class Harness:
    def __init__(self, responder: Responder) -> None:
        self.requests: list[dict[str, Any]] = []
        self.sleeper = RecordingSleeper()
        self._responder = responder

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/decisions"
        assert request.headers["Authorization"] == "Bearer fixture-key"
        self.requests.append(json.loads(request.content))
        return self._responder(request)

    def labeler(
        self,
        *,
        api_key: str = "fixture-key",
        policy: ThresholdPolicy | None = None,
        max_attempts: int = 3,
    ) -> OpenAIDecisionsItemTypeLabeler:
        return OpenAIDecisionsItemTypeLabeler(
            client=httpx.AsyncClient(transport=httpx.MockTransport(self.handle)),
            base_url="https://example.test",
            api_key=api_key,
            timeout_seconds=30,
            sleeper=self.sleeper,
            policy=policy or ThresholdPolicy(),
            max_attempts=max_attempts,
        )


def _replay(exchanges: list[dict[str, Any]]) -> Responder:
    def respond(request: httpx.Request) -> httpx.Response:
        sent = json.loads(request.content)
        matches = [exchange for exchange in exchanges if exchange["request"] == sent]
        assert len(matches) == 1, "adapter did not rebuild a recorded request"
        return _recorded_response(matches[0])

    return respond


def _sequence(*responders: Responder) -> Responder:
    remaining = list(responders)

    def respond(request: httpx.Request) -> httpx.Response:
        current = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        return current(request)

    return respond


def _always(recording: dict[str, Any], status_code: int | None = None) -> Responder:
    return lambda _request: _recorded_response(recording, status_code)


def _with_mutated_body(mutate: Callable[[dict[str, Any]], None]) -> Responder:
    exchange = copy.deepcopy(_load(CORPUS_24)["exchanges"][0])
    mutate(exchange["body"])
    return _replay([exchange])


async def _label_24(responder: Responder, **labeler_options: Any) -> Any:
    harness = Harness(responder)
    return await harness.labeler(**labeler_options).label(request=_request_for(_load(CORPUS_24)))


async def _expect_error(responder: Responder, **labeler_options: Any) -> ItemTypeLabelerError:
    with pytest.raises(ItemTypeLabelerError) as caught:
        await _label_24(responder, **labeler_options)
    return caught.value


def _recorded_answers_24() -> list[dict[str, Any]]:
    answers: list[dict[str, Any]] = _load(CORPUS_24)["exchanges"][0]["body"]["answers"]
    return answers


async def test_threshold_routes_recorded_answers_at_the_095_boundary() -> None:
    fixture = _load(CORPUS_24)
    harness = Harness(_replay(fixture["exchanges"]))

    labeling = await harness.labeler().label(request=_request_for(fixture))

    answers = _recorded_answers_24()
    probabilities = [_chosen_probability(answer) for answer in answers]
    assert any(p == 0.95 for p in probabilities)
    assert any(0.94 <= p < 0.95 for p in probabilities)
    assert len(labeling.results) == len(answers) == len(fixture["items"])
    for result, answer, item in zip(labeling.results, answers, fixture["items"], strict=True):
        probability = _chosen_probability(answer)
        assert result.item_id == item["item_id"]
        assert result.label == ItemTypeLabel(answer["choice"])
        assert result.probability == probability
        assert result.threshold == 0.95
        expected = LabelRoute.ACCEPT if probability >= 0.95 else LabelRoute.ESCALATE
        assert result.route == expected
    assert any(r.probability == 0.95 and r.route == LabelRoute.ACCEPT for r in labeling.results)
    assert any(r.probability < 0.95 and r.route == LabelRoute.ESCALATE for r in labeling.results)


async def test_per_label_threshold_escalates_only_its_label() -> None:
    fixture = _load(CORPUS_24)
    answers = _recorded_answers_24()
    boundary_label = ItemTypeLabel(
        next(a["choice"] for a in answers if _chosen_probability(a) == 0.95)
    )
    policy = ThresholdPolicy(per_label={boundary_label: 0.96})
    harness = Harness(_replay(fixture["exchanges"]))

    labeling = await harness.labeler(policy=policy).label(request=_request_for(fixture))

    for result in labeling.results:
        if result.label == boundary_label:
            assert result.threshold == 0.96
            expected = LabelRoute.ACCEPT if result.probability >= 0.96 else LabelRoute.ESCALATE
        else:
            assert result.threshold == 0.95
            expected = LabelRoute.ACCEPT if result.probability >= 0.95 else LabelRoute.ESCALATE
        assert result.route == expected
    flipped = [r for r in labeling.results if r.label == boundary_label and r.probability == 0.95]
    assert flipped
    assert all(r.route == LabelRoute.ESCALATE for r in flipped)


async def test_204_items_split_into_two_recorded_requests_in_item_order() -> None:
    fixture = _load(CORPUS_204)
    harness = Harness(_replay(fixture["exchanges"]))
    request = _request_for(fixture)
    labeler = harness.labeler()

    labeling = await labeler.label(request=request)

    assert len(harness.requests) == 2
    assert sorted(len(sent["questions"]) for sent in harness.requests) == [4, 200]
    for sent in harness.requests:
        assert "### Question q1" in sent["input"]
    small = next(sent for sent in harness.requests if len(sent["questions"]) == 4)
    assert "### Question q5" not in small["input"]
    assert [r.item_id for r in labeling.results] == [i["item_id"] for i in fixture["items"]]
    recorded_tokens = sum(e["body"]["usage"]["input_tokens"] for e in fixture["exchanges"])
    assert labeling.usage.input_tokens == recorded_tokens
    assert labeling.usage.requests == 2
    assert labeling.usage.attempts == 2
    estimate = labeler.estimate_input_tokens(request=request)
    assert 0 < estimate
    assert recorded_tokens / 2 <= estimate <= recorded_tokens * 2


async def test_recorded_503_then_success_retries_once_after_base_delay() -> None:
    fixture = _load(CORPUS_24)
    harness = Harness(_sequence(_always(_unavailable(503)), _replay(fixture["exchanges"])))

    labeling = await harness.labeler().label(request=_request_for(fixture))

    assert len(labeling.results) == len(fixture["items"])
    assert labeling.usage.attempts == 2
    assert harness.sleeper.delays == [1.0]


async def test_recorded_504_retry_after_is_capped() -> None:
    fixture = _load(CORPUS_24)
    gateway_timeout = _unavailable(504)
    assert gateway_timeout["headers"]["retry-after"] == "120"
    harness = Harness(_sequence(_always(gateway_timeout), _replay(fixture["exchanges"])))

    labeling = await harness.labeler().label(request=_request_for(fixture))

    assert len(labeling.results) == len(fixture["items"])
    assert harness.sleeper.delays == [8.0]


async def test_persistent_503_raises_provider_unavailable_after_three_attempts() -> None:
    harness = Harness(_always(_unavailable(503)))

    with pytest.raises(ItemTypeLabelerError) as caught:
        await harness.labeler().label(request=_request_for(_load(CORPUS_24)))

    assert caught.value.code == "provider_unavailable"
    assert caught.value.status_code == 503
    assert len(harness.requests) == 3
    assert harness.sleeper.delays == [1.0, 2.0]


async def test_persistent_504_honours_max_attempts() -> None:
    harness = Harness(_always(_unavailable(504)))

    with pytest.raises(ItemTypeLabelerError) as caught:
        await harness.labeler(max_attempts=2).label(request=_request_for(_load(CORPUS_24)))

    assert caught.value.code == "provider_unavailable"
    assert caught.value.status_code == 504
    assert len(harness.requests) == 2


async def test_non_retryable_status_fails_without_retry() -> None:
    harness = Harness(_always(_unavailable(503), status_code=400))

    with pytest.raises(ItemTypeLabelerError) as caught:
        await harness.labeler().label(request=_request_for(_load(CORPUS_24)))

    assert caught.value.code == "http_error"
    assert caught.value.status_code == 400
    assert len(harness.requests) == 1
    assert harness.sleeper.delays == []


def _replace_choice(body: dict[str, Any]) -> None:
    body["answers"][0]["choice"] = "essay"


def _replace_probability_value(body: dict[str, Any]) -> None:
    body["answers"][0]["probabilities"][1]["value"] = "essay"


def _remove_answer(body: dict[str, Any]) -> None:
    del body["answers"][3]


def _duplicate_answer(body: dict[str, Any]) -> None:
    body["answers"].append(copy.deepcopy(body["answers"][3]))


def _remove_answers_key(body: dict[str, Any]) -> None:
    del body["answers"]


def _probability_above_one(body: dict[str, Any]) -> None:
    body["answers"][0]["probabilities"][0]["probability"] = 1.5


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (_replace_choice, "unknown_label"),
        (_replace_probability_value, "unknown_label"),
        (_remove_answer, "malformed_response"),
        (_duplicate_answer, "malformed_response"),
        (_remove_answers_key, "malformed_response"),
        (_probability_above_one, "malformed_response"),
    ],
)
async def test_mutated_recorded_body_is_rejected(
    mutate: Callable[[dict[str, Any]], None], code: str
) -> None:
    error = await _expect_error(_with_mutated_body(mutate))

    assert error.code == code


async def test_non_json_success_body_raises_invalid_json() -> None:
    gateway_page = _unavailable(504)["body"]
    error = await _expect_error(lambda _request: httpx.Response(200, text=gateway_page))

    assert error.code == "invalid_json"


async def test_refusal_escalates_only_the_refused_item() -> None:
    fixture = _load(CORPUS_24)
    baseline = await _label_24(_replay(fixture["exchanges"]))
    refused_index = 2

    def refuse(body: dict[str, Any]) -> None:
        name = body["answers"][refused_index]["name"]
        body["answers"][refused_index] = {"type": "refusal", "name": name}

    labeling = await _label_24(_with_mutated_body(refuse))

    refused = labeling.results[refused_index]
    assert refused.item_id == fixture["items"][refused_index]["item_id"]
    assert refused.label == ItemTypeLabel.UNRESOLVED
    assert refused.route == LabelRoute.ESCALATE
    assert refused.refused is True
    assert dict(refused.probabilities) == {}
    others = [r for i, r in enumerate(labeling.results) if i != refused_index]
    expected = [r for i, r in enumerate(baseline.results) if i != refused_index]
    assert others == expected


async def test_missing_api_key_fails_before_any_request() -> None:
    harness = Harness(_replay(_load(CORPUS_24)["exchanges"]))

    with pytest.raises(ItemTypeLabelerError) as caught:
        await harness.labeler(api_key="").label(request=_request_for(_load(CORPUS_24)))

    assert caught.value.code == "config_missing"
    assert harness.requests == []


async def test_empty_request_sends_nothing() -> None:
    harness = Harness(_replay(_load(CORPUS_24)["exchanges"]))

    labeling = await harness.labeler().label(request=LabelingRequest(job_id=uuid4(), items=()))

    assert labeling.results == ()
    assert harness.requests == []
