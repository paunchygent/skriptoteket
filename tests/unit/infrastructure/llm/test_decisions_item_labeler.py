from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import NotRequired, TypedDict
from uuid import uuid4

import httpx
import pytest
from dishka import Provider, Scope, from_context, make_async_container
from pydantic import JsonValue

from skriptoteket.config import Settings
from skriptoteket.di.item_type_labeler import ItemTypeLabelerProvider
from skriptoteket.infrastructure.llm.openai.decisions_item_labeler import (
    OpenAIDecisionsItemTypeLabeler,
    build_decisions_payload,
    split_items,
)
from skriptoteket.protocols.item_type_labeler import (
    ItemTypeLabel,
    ItemTypeLabelerError,
    ItemTypeLabeling,
    LabelingItem,
    LabelingRequest,
    LabelingUsage,
    LabelRoute,
    MeteredItemTypeLabelerProtocol,
)
from skriptoteket.protocols.sleeper import SleeperProtocol

pytestmark = pytest.mark.unit

FIXTURES = Path("tests/fixtures/item_type_labeler")
CORPUS_24 = "corpus_exam_24_questions.json"
CORPUS_204 = "corpus_three_exams_204_questions.json"

Responder = Callable[[httpx.Request], httpx.Response]


class _Probability(TypedDict):
    value: str
    probability: float


class _Answer(TypedDict):
    """A recorded Decisions answer; a refusal carries only its type and name."""

    type: str
    name: str
    choice: NotRequired[str]
    probabilities: NotRequired[list[_Probability]]
    confidence: NotRequired[float]


class _Usage(TypedDict):
    input_tokens: int


class _Body(TypedDict):
    model: str
    answers: NotRequired[list[_Answer]]
    usage: _Usage


class _Sent(TypedDict):
    model: str
    input: str
    questions: list[dict[str, JsonValue]]


class _Exchange(TypedDict):
    request: _Sent
    status_code: int
    headers: dict[str, str]
    body: _Body


class _Item(TypedDict):
    item_id: str
    source_text: str


class _Recording(TypedDict):
    items: list[_Item]
    exchanges: list[_Exchange]


class _Unavailable(TypedDict):
    status_code: int
    headers: dict[str, str]
    body: JsonValue


def _load(name: str) -> _Recording:
    recording: _Recording = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return recording


def _request_for(fixture: _Recording) -> LabelingRequest:
    return LabelingRequest(
        job_id=uuid4(),
        items=tuple(
            LabelingItem(
                item_id=item["item_id"],
                source_text=item["source_text"],
            )
            for item in fixture["items"]
        ),
    )


def _unavailable(status_code: int) -> _Unavailable:
    path = FIXTURES / "decisions_unavailable_responses.json"
    responses: list[_Unavailable] = json.loads(path.read_text(encoding="utf-8"))["responses"]
    return next(r for r in responses if r["status_code"] == status_code)


def _recorded_response(
    recording: _Exchange | _Unavailable, status_code: int | None = None
) -> httpx.Response:
    status = recording["status_code"] if status_code is None else status_code
    body = recording["body"]
    if isinstance(body, str):
        return httpx.Response(status, headers=recording["headers"], text=body)
    return httpx.Response(status, headers=recording["headers"], json=body)


def _chosen_probability(answer: _Answer) -> float:
    by_value = {entry["value"]: entry["probability"] for entry in answer["probabilities"]}
    return float(by_value[answer["choice"]])


class RecordingSleeper:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def sleep(self, seconds: float) -> None:
        self.delays.append(seconds)


class Harness:
    def __init__(self, responder: Responder) -> None:
        self.requests: list[_Sent] = []
        self.sleeper = RecordingSleeper()
        self._responder = responder

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/decisions"
        assert request.headers["Authorization"] == "Bearer fixture-key"
        sent: _Sent = json.loads(request.content)
        self.requests.append(sent)
        return self._responder(request)

    def labeler(
        self,
        *,
        api_key: str = "fixture-key",
        max_attempts: int = 3,
    ) -> OpenAIDecisionsItemTypeLabeler:
        return OpenAIDecisionsItemTypeLabeler(
            client=httpx.AsyncClient(transport=httpx.MockTransport(self.handle)),
            base_url="https://example.test",
            api_key=api_key,
            timeout_seconds=30,
            sleeper=self.sleeper,
            max_attempts=max_attempts,
        )


def _replay(exchanges: list[_Exchange], *, fixture: _Recording | None = None) -> Responder:
    # Historical outputs exercise the current request/parser boundary only.
    # Their old request bodies are not evidence of requests made by this adapter.
    fixture = _load(CORPUS_24) if fixture is None else fixture
    chunks = split_items(_request_for(fixture).items)
    expected = [
        (
            build_decisions_payload(chunk),
            next(
                exchange
                for exchange in exchanges
                if len(exchange["request"]["questions"]) == len(chunk)
            ),
        )
        for chunk in chunks
    ]

    def respond(request: httpx.Request) -> httpx.Response:
        sent = json.loads(request.content)
        matches = [exchange for payload, exchange in expected if payload == sent]
        assert len(matches) == 1, "unexpected current-source request"
        return _recorded_response(matches[0])

    return respond


def _sequence(*responders: Responder) -> Responder:
    remaining = list(responders)

    def respond(request: httpx.Request) -> httpx.Response:
        current = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        return current(request)

    return respond


def _always(recording: _Exchange | _Unavailable, status_code: int | None = None) -> Responder:
    return lambda _request: _recorded_response(recording, status_code)


def _with_mutated_body(mutate: Callable[[_Body], None]) -> Responder:
    exchange = copy.deepcopy(_load(CORPUS_24)["exchanges"][0])
    mutate(exchange["body"])
    return _replay([exchange])


async def _label_24(responder: Responder) -> ItemTypeLabeling:
    harness = Harness(responder)
    return await _first_pass(harness.labeler(), _request_for(_load(CORPUS_24)))


async def _first_pass(
    labeler: OpenAIDecisionsItemTypeLabeler, request: LabelingRequest
) -> ItemTypeLabeling:
    """Exercise first-pass HTTP/parser failures with first-pass-only recordings.

    Full inherited re-ask orchestration is covered in the second-pass file.
    """
    outcomes = [
        await labeler._label_chunk(build_decisions_payload(chunk), chunk)
        for chunk in split_items(request.items)
    ]
    return ItemTypeLabeling(
        results=tuple(result for results, _, _ in outcomes for result in results),
        usage=LabelingUsage(
            input_tokens=sum(tokens or 0 for _, tokens, _ in outcomes),
            requests=len(outcomes),
            attempts=sum(attempts for _, _, attempts in outcomes),
        ),
    )


async def _expect_error(responder: Responder) -> ItemTypeLabelerError:
    with pytest.raises(ItemTypeLabelerError) as caught:
        await _label_24(responder)
    return caught.value


def _recorded_answers_24() -> list[_Answer]:
    return _load(CORPUS_24)["exchanges"][0]["body"]["answers"]


async def test_threshold_routes_recorded_answers_at_the_095_boundary() -> None:
    fixture = _load(CORPUS_24)
    harness = Harness(_replay(fixture["exchanges"]))

    labeling = await _first_pass(harness.labeler(), _request_for(fixture))

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


@pytest.mark.parametrize("name", [CORPUS_24, CORPUS_204])
def test_request_input_carries_each_source_text_verbatim_and_nothing_else(name: str) -> None:
    fixture = _load(name)
    items = _request_for(fixture).items
    inputs = [build_decisions_payload(chunk)["input"] for chunk in split_items(items)]
    assert all(isinstance(rendered, str) for rendered in inputs)
    offset = 0
    for rendered, chunk in zip(inputs, split_items(items), strict=True):
        assert isinstance(rendered, str)
        for forbidden in (
            "Answer key",
            "[Governing instruction",
            "Section heading:",
            "Question as the student sees it:",
        ):
            assert forbidden not in rendered.split("\n\n### Question ", 1)[1]
        for index, item in enumerate(chunk):
            block = rendered.split(f"### Question q{index + 1}\n", 1)[1]
            followed = f"\n\n### Question q{index + 2}\n"
            assert block.split(followed, 1)[0] == item.source_text
        offset += len(chunk)
    assert offset == len(items)


class _LabelerInputs(Provider):
    client = from_context(provides=httpx.AsyncClient, scope=Scope.APP)
    sleeper = from_context(provides=SleeperProtocol, scope=Scope.APP)
    settings = from_context(provides=Settings, scope=Scope.APP)


async def test_environment_cannot_move_the_decided_threshold_or_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The wired labeler keeps the 0.95 boundary and its model whatever the environment says."""
    monkeypatch.setenv("LLM_ITEM_LABELER_ACCEPT_THRESHOLD", "0.5")
    monkeypatch.setenv("LLM_ITEM_LABELER_MODEL", "another-model")
    settings = Settings(
        _env_file=None,
        LLM_ANSWER_KEY_BASE_URL="https://example.test",
        OPENAI_LLM_ANSWER_KEY_API_KEY="fixture-key",
    )
    fixture = _load(CORPUS_24)
    harness = Harness(_replay(fixture["exchanges"]))
    container = make_async_container(
        ItemTypeLabelerProvider(),
        _LabelerInputs(),
        context={
            httpx.AsyncClient: httpx.AsyncClient(transport=httpx.MockTransport(harness.handle)),
            SleeperProtocol: harness.sleeper,
            Settings: settings,
        },
        # The leased request-scope labeler needs a database; only the adapter is wired here.
        skip_validation=True,
    )
    labeler = await container.get(MeteredItemTypeLabelerProtocol)

    labeling = await _first_pass(labeler, _request_for(fixture))
    await container.close()

    assert [sent["model"] for sent in harness.requests] == ["gpt-6-luna"]
    assert all(r.threshold == 0.95 for r in labeling.results)
    below = [r for r in labeling.results if r.probability < 0.95]
    assert below
    assert all(r.route == LabelRoute.ESCALATE for r in below)


async def test_204_items_split_into_two_recorded_requests_in_item_order() -> None:
    fixture = _load(CORPUS_204)
    harness = Harness(_replay(fixture["exchanges"], fixture=fixture))
    request = _request_for(fixture)
    labeler = harness.labeler()

    labeling = await _first_pass(labeler, request)

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


async def test_recorded_503_then_success_retries_once_after_base_delay() -> None:
    fixture = _load(CORPUS_24)
    harness = Harness(_sequence(_always(_unavailable(503)), _replay(fixture["exchanges"])))

    labeling = await _first_pass(harness.labeler(), _request_for(fixture))

    assert len(labeling.results) == len(fixture["items"])
    assert labeling.usage.attempts == 2
    assert harness.sleeper.delays == [1.0]


async def test_recorded_504_retry_after_is_capped() -> None:
    fixture = _load(CORPUS_24)
    gateway_timeout = _unavailable(504)
    assert gateway_timeout["headers"]["retry-after"] == "120"
    harness = Harness(_sequence(_always(gateway_timeout), _replay(fixture["exchanges"])))

    labeling = await _first_pass(harness.labeler(), _request_for(fixture))

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


def _replace_choice(body: _Body) -> None:
    body["answers"][0]["choice"] = "essay"


def _replace_probability_value(body: _Body) -> None:
    body["answers"][0]["probabilities"][1]["value"] = "essay"


def _remove_answer(body: _Body) -> None:
    del body["answers"][3]


def _duplicate_answer(body: _Body) -> None:
    body["answers"].append(copy.deepcopy(body["answers"][3]))


def _remove_answers_key(body: _Body) -> None:
    del body["answers"]


def _probability_above_one(body: _Body) -> None:
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
    mutate: Callable[[_Body], None], code: str
) -> None:
    error = await _expect_error(_with_mutated_body(mutate))

    assert error.code == code


async def test_non_json_success_body_raises_invalid_json() -> None:
    gateway_page = _unavailable(504)["body"]
    assert isinstance(gateway_page, str)
    error = await _expect_error(lambda _request: httpx.Response(200, text=gateway_page))

    assert error.code == "invalid_json"


async def test_refusal_escalates_only_the_refused_item() -> None:
    fixture = _load(CORPUS_24)
    baseline = await _label_24(_replay(fixture["exchanges"]))
    refused_index = 2

    def refuse(body: _Body) -> None:
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
