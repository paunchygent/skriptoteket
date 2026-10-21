"""Recorded-response support shared by the Decisions item-labeler adapter tests.

The recordings hold historical first-pass outputs; ``replay`` serves them to the
current first-pass requests and rejects any other request.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import NotRequired, TypedDict
from uuid import uuid4

import httpx
from pydantic import JsonValue

from skriptoteket.infrastructure.llm.openai.decisions_item_labeler import (
    OpenAIDecisionsItemTypeLabeler,
    build_decisions_payload,
    split_items,
)
from skriptoteket.protocols.item_type_labeler import LabelingItem, LabelingRequest
from tests.unit.llm_door_fakes import fixture_caller

FIXTURES = Path("tests/fixtures/item_type_labeler")
CORPUS_24 = "corpus_exam_24_questions.json"
CORPUS_204 = "corpus_three_exams_204_questions.json"
ACCEPT_BOUNDARY = 0.95

Responder = Callable[[httpx.Request], httpx.Response]


class Probability(TypedDict):
    value: str
    probability: float


class Answer(TypedDict):
    """A recorded Decisions answer; a refusal carries only its type and name."""

    type: str
    name: str
    choice: NotRequired[str]
    probabilities: NotRequired[list[Probability]]
    confidence: NotRequired[float]


class Usage(TypedDict):
    input_tokens: int


class Body(TypedDict):
    model: str
    answers: NotRequired[list[Answer]]
    usage: Usage


class Sent(TypedDict):
    model: str
    input: str
    questions: list[dict[str, JsonValue]]


class Exchange(TypedDict):
    request: Sent
    status_code: int
    headers: dict[str, str]
    body: Body


class Item(TypedDict):
    item_id: str
    source_text: str


class Recording(TypedDict):
    items: list[Item]
    exchanges: list[Exchange]


class Unavailable(TypedDict):
    status_code: int
    headers: dict[str, str]
    body: JsonValue


def load(name: str) -> Recording:
    recording: Recording = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return recording


def request_for(fixture: Recording) -> LabelingRequest:
    return LabelingRequest(
        job_id=uuid4(),
        caller=fixture_caller(),
        items=tuple(
            LabelingItem(
                item_id=item["item_id"],
                source_text=item["source_text"],
            )
            for item in fixture["items"]
        ),
    )


def unavailable(status_code: int) -> Unavailable:
    path = FIXTURES / "decisions_unavailable_responses.json"
    responses: list[Unavailable] = json.loads(path.read_text(encoding="utf-8"))["responses"]
    return next(r for r in responses if r["status_code"] == status_code)


def recorded_response(
    recording: Exchange | Unavailable, status_code: int | None = None
) -> httpx.Response:
    status = recording["status_code"] if status_code is None else status_code
    body = recording["body"]
    if isinstance(body, str):
        return httpx.Response(status, headers=recording["headers"], text=body)
    return httpx.Response(status, headers=recording["headers"], json=body)


def chosen_probability(answer: Answer) -> float:
    by_value = {entry["value"]: entry["probability"] for entry in answer["probabilities"]}
    return float(by_value[answer["choice"]])


def escalated_answers(fixture: Recording) -> list[Answer]:
    """The recorded first-pass answers the label thresholds send to a second pass."""

    return [
        answer
        for exchange in fixture["exchanges"]
        for answer in exchange["body"]["answers"]
        if answer["type"] != "choice" or chosen_probability(answer) < ACCEPT_BOUNDARY
    ]


class RecordingSleeper:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def sleep(self, seconds: float) -> None:
        self.delays.append(seconds)


class Harness:
    def __init__(self, responder: Responder) -> None:
        self.requests: list[Sent] = []
        self.sleeper = RecordingSleeper()
        self._responder = responder

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/decisions"
        assert request.headers["Authorization"] == "Bearer fixture-key"
        sent: Sent = json.loads(request.content)
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


def replay(exchanges: list[Exchange], *, fixture: Recording | None = None) -> Responder:
    # Historical outputs exercise the current request/parser boundary only.
    # Their old request bodies are not evidence of requests made by this adapter.
    fixture = load(CORPUS_24) if fixture is None else fixture
    items = request_for(fixture).items
    first_pass: list[tuple[JsonValue, Exchange]] = []
    for chunk in split_items(items):
        exchange = next(
            exchange
            for exchange in exchanges
            if len(exchange["request"]["questions"]) == len(chunk)
        )
        first_pass.append((build_decisions_payload(chunk), exchange))

    def respond(request: httpx.Request) -> httpx.Response:
        sent = json.loads(request.content)
        matches = [exchange for payload, exchange in first_pass if payload == sent]
        assert len(matches) == 1, "unexpected current-source request"
        return recorded_response(matches[0])

    return respond


def sequence(*responders: Responder) -> Responder:
    remaining = list(responders)

    def respond(request: httpx.Request) -> httpx.Response:
        current = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        return current(request)

    return respond


def always(recording: Exchange | Unavailable, status_code: int | None = None) -> Responder:
    return lambda _request: recorded_response(recording, status_code)


def with_mutated_body(mutate: Callable[[Body], None]) -> Responder:
    exchange = copy.deepcopy(load(CORPUS_24)["exchanges"][0])
    mutate(exchange["body"])
    return replay([exchange])
